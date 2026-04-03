#!/usr/bin/env python3
"""
youtube_subscriptions_to_artists.py — Populator for artists.tsv YouTube Channel column

Two modes for finding YouTube channel handles for artists with blank entries:

  --search   (recommended for filling blanks)
             Uses YouTube search.list to look up each blank artist by name.
             Works regardless of whether you're subscribed to the channel.
             Quota: 100 units per artist searched. Use --limit to cap spend.

             Example — fill all blanks, 10 at a time across quota days:
                 python3 youtube_subscriptions_to_artists.py --search --limit 10 --dry-run
                 python3 youtube_subscriptions_to_artists.py --search --limit 10

  --subscriptions  (legacy — only useful if you're subscribed to the channel)
             Fetches your subscriptions list and fuzzy-matches channel names
             against artist names. Only finds artists you're already subscribed
             to, so it leaves most blanks unfilled.

QUOTA COSTS:
    --search:         ~101 units per artist (search.list + channels.list)
    --subscriptions:  ~15-20 units total for the full list

REQUIRES OAuth — same token.json / client_secrets.json used by
youtube_create_playlists.py. Run --auth-only once if not yet authenticated.

USAGE:

    # Always dry-run first
    python3 youtube_subscriptions_to_artists.py --search --dry-run
    python3 youtube_subscriptions_to_artists.py --search --limit 20 --dry-run

    # Apply, processing up to N artists per run (default: all blanks)
    python3 youtube_subscriptions_to_artists.py --search --limit 10

    # Legacy subscriptions mode
    python3 youtube_subscriptions_to_artists.py --subscriptions --write-all

    # First-time auth only (opens browser, saves token.json)
    python3 youtube_subscriptions_to_artists.py --auth-only

OUTPUT:
    Prints results for each artist searched: handle found, confidence, and
    whether it was written. With --dry-run, nothing is written.
    Save is written after each artist so a quota-interrupted run loses nothing.

CONFIDENCE (--search mode):
    1.0   Top result channel title exactly matches the artist name (normalized)
    0.8+  Strong token overlap — written automatically
    0.55+ Partial match — printed but skipped unless --write-low is also passed
    <0.55 No confident match — skipped, printed for manual follow-up

CONFIDENCE (--subscriptions mode):
    Same thresholds, matched against your subscription list channel titles.

ENVIRONMENT / FILES (same directory as this script):
    client_secrets.json  — OAuth client secret (gitignored, from Google Cloud)
    token.json           — cached OAuth token (gitignored, auto-created on auth)
    artists.tsv          — read and written in-place
    .env                 — optional; CLIENT_SECRETS / TOKEN_FILE overrides
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("Missing dependency: python-dotenv\nRun: pip install python-dotenv")

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    sys.exit(
        "Missing dependencies. Run:\n"
        "  pip install google-api-python-client google-auth-oauthlib\n"
    )

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

SCOPES         = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
TOKEN_FILE     = os.environ.get("YOUTUBE_TOKEN_FILE",     "token.json")
ARTISTS_TSV    = os.path.join(SCRIPT_DIR, "artists.tsv")

HIGH_THRESHOLD = 0.8    # auto-write
LOW_THRESHOLD  = 0.55   # report but skip unless --write-low

PAGE_DELAY     = 0.3    # seconds between API calls


# ── OAuth ─────────────────────────────────────────────────────────────────────

def get_authenticated_service():
    client_secrets_path = os.path.join(SCRIPT_DIR, CLIENT_SECRETS)
    token_path          = os.path.join(SCRIPT_DIR, TOKEN_FILE)

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_path):
                sys.exit(
                    f"OAuth credentials file not found: {client_secrets_path}\n"
                    "Download from Google Cloud Console → Credentials → OAuth 2.0 Client IDs."
                )
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


# ── Name normalisation & similarity ──────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase, strip accents, remove punctuation, drop leading 'the'."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"^the\s+", "", s).strip()
    s = re.sub(r"\s*(official|music|band|tv|channel|records|vevo)\s*$", "", s).strip()
    return s


def _tokens(s: str) -> set:
    NOISE = {"and", "the", "feat", "with", "live", "official", "music"}
    return {w for w in _norm(s).split() if len(w) > 2 and w not in NOISE}


def similarity(a: str, b: str) -> float:
    if _norm(a) == _norm(b):
        return 1.0
    wa, wb = _tokens(a), _tokens(b)
    if not wa or not wb:
        return 0.0
    jaccard = len(wa & wb) / len(wa | wb)
    an, bn = _norm(a), _norm(b)
    shorter, longer = (an, bn) if len(an) <= len(bn) else (bn, an)
    if len(shorter) > 5 and shorter in longer:
        jaccard = max(jaccard, 0.75)
    return jaccard


# ── TSV helpers ───────────────────────────────────────────────────────────────

def load_artists() -> tuple[list[dict], list[str]]:
    with open(ARTISTS_TSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    return rows, fieldnames


def save_artists(rows: list[dict], fieldnames: list[str]) -> None:
    with open(ARTISTS_TSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                           lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ── Search mode ───────────────────────────────────────────────────────────────

def search_handle_for_artist(youtube, artist_name: str) -> tuple[str, float, str]:
    """
    Search YouTube for the artist name and return (handle, score, channel_title).

    Uses search.list(type=channel, q=artist_name, maxResults=5) — 100 quota units.
    Then channels.list to resolve the @handle — 1 quota unit.

    Scores the top 5 results by name similarity; picks the best.
    Returns ("", 0.0, "") if no result exceeds LOW_THRESHOLD.
    """
    try:
        resp = youtube.search().list(
            part="snippet",
            q=artist_name,
            type="channel",
            maxResults=5,
        ).execute()
    except Exception as e:
        print(f"  ERROR searching for '{artist_name}': {e}")
        return "", 0.0, ""

    best_handle = ""
    best_score  = 0.0
    best_title  = ""

    for item in resp.get("items", []):
        channel_id    = item["snippet"]["channelId"]
        channel_title = item["snippet"]["title"]
        score         = similarity(artist_name, channel_title)

        if score > best_score:
            best_score = score
            best_title = channel_title
            # Resolve @handle
            try:
                ch_resp = youtube.channels().list(
                    part="snippet",
                    id=channel_id,
                ).execute()
                ch_items = ch_resp.get("items", [])
                if ch_items:
                    custom = ch_items[0]["snippet"].get("customUrl", "")
                    if custom:
                        best_handle = custom if custom.startswith("@") else f"@{custom}"
                    else:
                        best_handle = f"https://www.youtube.com/channel/{channel_id}"
                else:
                    best_handle = f"https://www.youtube.com/channel/{channel_id}"
            except Exception:
                best_handle = f"https://www.youtube.com/channel/{channel_id}"

    if best_score >= LOW_THRESHOLD:
        return best_handle, best_score, best_title
    return "", 0.0, ""


def run_search_mode(
    youtube,
    artists: list[dict],
    fieldnames: list[str],
    limit: int | None,
    dry_run: bool,
    write_low: bool,
) -> None:
    blanks = [
        (i, row) for i, row in enumerate(artists)
        if not row.get("YouTube Channel", "").strip()
    ]

    if not blanks:
        print("No blank YouTube Channel entries found — nothing to do.")
        return

    total      = len(blanks)
    to_process = blanks[:limit] if limit else blanks
    print(f"{total} blank entries total. Processing {len(to_process)}"
          + (f" (--limit {limit})" if limit else "") + ".\n")

    write_threshold = LOW_THRESHOLD if write_low else HIGH_THRESHOLD
    written      = 0
    skipped_low  = []
    skipped_none = []

    for idx, (row_idx, row) in enumerate(to_process, 1):
        artist_name = row["Artist"]
        print(f"[{idx}/{len(to_process)}] {artist_name}")

        handle, score, channel_title = search_handle_for_artist(youtube, artist_name)
        time.sleep(PAGE_DELAY)

        if not handle:
            print(f"  → No confident match found\n")
            skipped_none.append(artist_name)
            continue

        flag = "✓" if score >= HIGH_THRESHOLD else "?"
        print(f"  → {handle}  ({channel_title})  score {score:.2f} {flag}")

        if score < write_threshold:
            print(f"  → Skipping (below write threshold {write_threshold:.2f}) — check manually\n")
            skipped_low.append((artist_name, handle, score, channel_title))
            continue

        if dry_run:
            print(f"  → [dry-run] would write\n")
            written += 1
        else:
            artists[row_idx]["YouTube Channel"] = handle
            save_artists(artists, fieldnames)
            print(f"  → Written\n")
            written += 1

    # Summary
    print("=" * 60)
    print(f"{'[DRY RUN] ' if dry_run else ''}Results: "
          f"{written} written, "
          f"{len(skipped_low)} low-confidence skipped, "
          f"{len(skipped_none)} no match.")

    if skipped_low:
        print(f"\nLow-confidence matches — review and add manually if correct:")
        for name, handle, score, title in skipped_low:
            print(f"  {score:.2f}  {name:<40}  {handle}  ({title})")

    if skipped_none:
        print(f"\nNo match found — may need manual YouTube search:")
        for name in skipped_none:
            print(f"  {name}")

    remaining = total - written if not dry_run else total
    if limit and remaining > 0:
        print(f"\n{remaining} blank entries remain. Run again to continue.")

    if not dry_run and written:
        print("\nReview changes with: git diff live-shows/artists.tsv")


# ── Subscriptions mode (legacy) ───────────────────────────────────────────────

def fetch_subscriptions(youtube) -> list[dict]:
    subs = []
    page_token = None
    print("Fetching subscriptions...")
    while True:
        kwargs = dict(part="snippet", mine=True, maxResults=50)
        if page_token:
            kwargs["pageToken"] = page_token
        resp = youtube.subscriptions().list(**kwargs).execute()
        for item in resp.get("items", []):
            subs.append({
                "channel_id": item["snippet"]["resourceId"]["channelId"],
                "title":      item["snippet"]["title"],
            })
        page_token = resp.get("nextPageToken")
        print(f"  Fetched {len(subs)} subscriptions so far...")
        if not page_token:
            break
        time.sleep(PAGE_DELAY)
    print(f"Total subscriptions: {len(subs)}")
    return subs


def fetch_handles(youtube, channel_ids: list[str]) -> dict[str, str]:
    handle_map = {}
    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        resp = youtube.channels().list(part="snippet", id=",".join(batch)).execute()
        for item in resp.get("items", []):
            cid    = item["id"]
            custom = item["snippet"].get("customUrl", "")
            handle = custom if custom.startswith("@") else f"@{custom}" if custom else f"https://www.youtube.com/channel/{cid}"
            handle_map[cid] = handle
        time.sleep(PAGE_DELAY)
    return handle_map


def match_subscriptions_to_artists(subs, handle_map, artists):
    candidates = [(i, row) for i, row in enumerate(artists)
                  if not row.get("YouTube Channel", "").strip()]
    matches = []
    for i, row in candidates:
        artist_name = row["Artist"]
        best_score, best_sub = 0.0, None
        for sub in subs:
            score = similarity(artist_name, sub["title"])
            if score > best_score:
                best_score, best_sub = score, sub
        if best_sub and best_score >= LOW_THRESHOLD:
            matches.append({
                "artist":        artist_name,
                "channel_title": best_sub["title"],
                "handle":        handle_map.get(best_sub["channel_id"], ""),
                "score":         best_score,
                "row_idx":       i,
            })
    matches.sort(key=lambda m: -m["score"])
    return matches


def print_matches(matches, high_threshold):
    if not matches:
        print("No matches found above minimum threshold.")
        return
    print(f"\n{'Score':>6}  {'Artist':<40}  {'Subscribed Channel':<40}  Handle")
    print("-" * 120)
    for m in matches:
        flag = "✓" if m["score"] >= high_threshold else "?"
        print(f"  {m['score']:.2f} {flag}  {m['artist']:<40}  {m['channel_title']:<40}  {m['handle']}")
    auto = sum(1 for m in matches if m["score"] >= high_threshold)
    print(f"\n{auto} high-confidence (≥{high_threshold}), {len(matches)-auto} lower-confidence matches found.")


def apply_matches(matches, artists, fieldnames, min_score, dry_run):
    written = 0
    for m in matches:
        if m["score"] < min_score:
            continue
        if not m["handle"]:
            print(f"  SKIP (no handle resolved): {m['artist']}")
            continue
        row = artists[m["row_idx"]]
        if row.get("YouTube Channel", "").strip():
            print(f"  SKIP (already filled): {m['artist']} -> {row['YouTube Channel']}")
            continue
        if dry_run:
            print(f"  [dry-run] would write: {m['artist']} -> {m['handle']}")
        else:
            row["YouTube Channel"] = m["handle"]
            save_artists(artists, fieldnames)
            print(f"  Written: {m['artist']} -> {m['handle']}")
        written += 1
    return written


def run_subscriptions_mode(youtube, artists, fieldnames, write_high, write_all, dry_run):
    subs = fetch_subscriptions(youtube)
    if not subs:
        print("No subscriptions found — nothing to match.")
        return
    print(f"\nResolving @handles for {len(subs)} channels...")
    handle_map = fetch_handles(youtube, [s["channel_id"] for s in subs])
    print(f"Resolved {len(handle_map)} handles.")
    blank_count = sum(1 for r in artists if not r.get("YouTube Channel", "").strip())
    print(f"\nLoaded {len(artists)} artists, {blank_count} with blank YouTube Channel.\n")
    matches = match_subscriptions_to_artists(subs, handle_map, artists)
    print_matches(matches, HIGH_THRESHOLD)
    if dry_run:
        print("\n[dry-run] No changes written.")
        return
    write_threshold = HIGH_THRESHOLD if write_high else LOW_THRESHOLD
    label = "high-confidence" if write_high else "all"
    print(f"\nWriting {label} matches (score >= {write_threshold})...")
    written = apply_matches(matches, artists, fieldnames, min_score=write_threshold, dry_run=False)
    print(f"\n{written} handle(s) written to artists.tsv.")
    if write_high:
        lower = [m for m in matches if m["score"] < HIGH_THRESHOLD]
        if lower:
            print(f"\n{len(lower)} lower-confidence match(es) not auto-written:")
            for m in lower:
                print(f"  {m['score']:.2f}  {m['artist']:<40}  {m['handle']}")
    print("\nReview changes with: git diff live-shows/artists.tsv")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--search", action="store_true",
        help="Search YouTube by artist name to find handles. Works without subscription. "
             "~101 quota units per artist — use --limit to control spend.",
    )
    mode.add_argument(
        "--subscriptions", action="store_true",
        help="Match against your subscriptions list (legacy — only finds artists "
             "you're already subscribed to).",
    )
    mode.add_argument(
        "--auth-only", action="store_true",
        help="Authenticate and save token.json, then exit.",
    )

    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be written without writing anything.")
    parser.add_argument("--limit", type=int, metavar="N",
                        help="(--search only) Process at most N blank artists per run.")
    parser.add_argument("--write-low", action="store_true",
                        help="(--search only) Also write low-confidence matches (score >= 0.55). "
                             "Default: only write high-confidence (score >= 0.8).")
    parser.add_argument("--write-high", action="store_true",
                        help="(--subscriptions only) Write high-confidence matches only.")
    parser.add_argument("--write-all", action="store_true",
                        help="(--subscriptions only) Write all matches above minimum threshold.")

    args = parser.parse_args()

    print("Authenticating with YouTube...")
    youtube = get_authenticated_service()
    print("Authenticated.")

    if args.auth_only:
        print("Auth complete. token.json saved.")
        return

    artists, fieldnames = load_artists()

    if args.search:
        run_search_mode(
            youtube, artists, fieldnames,
            limit=args.limit,
            dry_run=args.dry_run,
            write_low=args.write_low,
        )
    elif args.subscriptions:
        run_subscriptions_mode(
            youtube, artists, fieldnames,
            write_high=args.write_high,
            write_all=args.write_all,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
