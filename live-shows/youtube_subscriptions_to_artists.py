#!/usr/bin/env python3
"""
youtube_subscriptions_to_artists.py — One-time populator for artists.tsv YouTube Channel column

Fetches the subscriptions list for the authenticated YouTube account (@dan2bit),
matches each subscribed channel's name against artists in artists.tsv using
name-similarity logic, and fills in blank YouTube Channel cells with the
channel's @handle.

This is intentionally a one-time / occasional script. Once artists.tsv is
populated you don't need to run it again unless you've added new artists.

QUOTA COST: Very cheap.
    subscriptions.list  — 1 unit per page (~50 subs/page)
    channels.list       — 1 unit per batch of 50 channel IDs
    Typical total: 15–20 units for a full subscriptions list.

REQUIRES OAuth — same token.json / client_secrets.json used by
youtube_create_playlists.py. Run --auth-only once if not yet authenticated.

USAGE:
    # Preview all matches without writing anything (always do this first)
    python3 youtube_subscriptions_to_artists.py --dry-run

    # Auto-write high-confidence matches (score >= 0.8), print lower ones for review
    python3 youtube_subscriptions_to_artists.py --write-high

    # Write all matches above the minimum threshold (review via git diff afterward)
    python3 youtube_subscriptions_to_artists.py --write-all

    # First-time auth only (opens browser, saves token.json)
    python3 youtube_subscriptions_to_artists.py --auth-only

OUTPUT:
    Prints a confidence-sorted table of all matches found.
    With --write-high or --write-all, patches artists.tsv in-place and
    prints every row it writes. Save progress is written after each update
    so a mid-run interruption loses nothing.

CONFIDENCE SCORES:
    1.0   Exact normalized match (e.g. "Shawn James" == "Shawn James")
    0.8+  Strong token overlap — auto-written with --write-high
    0.55+ Partial match — printed for review, written with --write-all
    <0.55 No match — ignored

KNOWN LIMITATIONS:
    - Only matches artists with a blank YouTube Channel in artists.tsv.
      Artists already filled are always skipped (safe to re-run).
    - Subscription channel names sometimes differ from artist names
      (e.g. "Selwyn Birchwood - Official" vs "Selwyn Birchwood"). The
      similarity matcher handles most of these but edge cases may need
      manual follow-up.
    - You must be subscribed to the channel for it to appear here.

ENVIRONMENT / FILES (same directory as this script):
    client_secrets.json  — OAuth client secret (gitignored, from Google Cloud)
    token.json           — cached OAuth token (gitignored, auto-created on auth)
    artists.tsv          — read and written in-place
    .env                 — optional; CLIENT_SECRETS / TOKEN_FILE overrides
"""

import argparse
import csv
import io
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

SCOPES          = ["https://www.googleapis.com/auth/youtube.readonly"]
CLIENT_SECRETS  = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
TOKEN_FILE      = os.environ.get("YOUTUBE_TOKEN_FILE",     "token.json")
ARTISTS_TSV     = os.path.join(SCRIPT_DIR, "artists.tsv")

# Similarity thresholds
HIGH_THRESHOLD  = 0.8   # auto-write with --write-high
MIN_THRESHOLD   = 0.55  # minimum to report at all

# Politeness delay between API pages
PAGE_DELAY = 0.3   # seconds


# ── OAuth ─────────────────────────────────────────────────────────────────────

def get_authenticated_service():
    """Identical OAuth flow to youtube_create_playlists.py."""
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
                    "Download from Google Cloud Console → Credentials → OAuth 2.0 Client IDs.\n"
                    "See utils/HOWTO.md → \"YouTube API credentials\" for instructions."
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
    # Strip common channel-name suffixes that don't appear in artist names
    s = re.sub(r"\s*(official|music|band|tv|channel|records|vevo)\s*$", "", s).strip()
    return s


def _tokens(s: str) -> set:
    """Meaningful (>2 char) tokens, dropping noise words."""
    NOISE = {"and", "the", "feat", "with", "live", "official", "music"}
    return {w for w in _norm(s).split() if len(w) > 2 and w not in NOISE}


def similarity(a: str, b: str) -> float:
    """Jaccard similarity on token sets, with exact-match bonus."""
    if _norm(a) == _norm(b):
        return 1.0
    wa, wb = _tokens(a), _tokens(b)
    if not wa or not wb:
        return 0.0
    jaccard = len(wa & wb) / len(wa | wb)
    # Substring bonus: if the shorter normalised name is contained in the longer
    an, bn = _norm(a), _norm(b)
    shorter, longer = (an, bn) if len(an) <= len(bn) else (bn, an)
    if len(shorter) > 5 and shorter in longer:
        jaccard = max(jaccard, 0.75)
    return jaccard


# ── YouTube API ───────────────────────────────────────────────────────────────

def fetch_subscriptions(youtube) -> list[dict]:
    """
    Return all subscribed channels as list of:
        {channel_id, title}
    Uses subscriptions.list(mine=True), paginated.
    Quota: 1 unit per page (50 subs/page).
    """
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
    """
    Given a list of channel IDs, return {channel_id: @handle}.
    Uses channels.list in batches of 50.
    Quota: 1 unit per batch.
    Falls back to https://www.youtube.com/channel/{id} if no customUrl.
    """
    handle_map = {}

    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i + 50]
        resp = youtube.channels().list(
            part="snippet",
            id=",".join(batch),
        ).execute()

        for item in resp.get("items", []):
            cid    = item["id"]
            custom = item["snippet"].get("customUrl", "")
            if custom:
                handle = custom if custom.startswith("@") else f"@{custom}"
            else:
                handle = f"https://www.youtube.com/channel/{cid}"
            handle_map[cid] = handle

        time.sleep(PAGE_DELAY)

    return handle_map


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


# ── Matching ──────────────────────────────────────────────────────────────────

def match_subscriptions_to_artists(
    subs: list[dict],
    handle_map: dict[str, str],
    artists: list[dict],
) -> list[dict]:
    """
    For each artist with a blank YouTube Channel, find the best-matching
    subscription channel by name similarity.

    Returns a list of match dicts sorted by score descending:
        {artist, channel_title, handle, score, row_idx}
    """
    # Only consider artists with blank YouTube Channel
    candidates = [
        (i, row) for i, row in enumerate(artists)
        if not row.get("YouTube Channel", "").strip()
    ]

    matches = []
    for i, row in candidates:
        artist_name = row["Artist"]
        best_score  = 0.0
        best_sub    = None

        for sub in subs:
            score = similarity(artist_name, sub["title"])
            if score > best_score:
                best_score = score
                best_sub   = sub

        if best_sub and best_score >= MIN_THRESHOLD:
            handle = handle_map.get(best_sub["channel_id"], "")
            matches.append({
                "artist":        artist_name,
                "channel_title": best_sub["title"],
                "handle":        handle,
                "score":         best_score,
                "row_idx":       i,
            })

    matches.sort(key=lambda m: -m["score"])
    return matches


# ── Output & writing ──────────────────────────────────────────────────────────

def print_matches(matches: list[dict], high_threshold: float) -> None:
    if not matches:
        print("No matches found above minimum threshold.")
        return

    print(f"\n{'Score':>6}  {'Artist':<40}  {'Subscribed Channel':<40}  Handle")
    print("-" * 120)
    for m in matches:
        flag = "✓" if m["score"] >= high_threshold else "?"
        print(
            f"  {m['score']:.2f} {flag}  "
            f"{m['artist']:<40}  "
            f"{m['channel_title']:<40}  "
            f"{m['handle']}"
        )
    auto  = sum(1 for m in matches if m["score"] >= high_threshold)
    print(f"\n{auto} high-confidence (≥{high_threshold}), "
          f"{len(matches) - auto} lower-confidence matches found.")


def apply_matches(
    matches: list[dict],
    artists: list[dict],
    fieldnames: list[str],
    min_score: float,
    dry_run: bool,
) -> int:
    """Write matching handles into artists rows. Returns count written."""
    written = 0
    for m in matches:
        if m["score"] < min_score:
            continue
        if not m["handle"]:
            print(f"  SKIP (no handle resolved): {m['artist']}")
            continue

        row = artists[m["row_idx"]]
        if row.get("YouTube Channel", "").strip():
            # Already filled between fetch and write (shouldn't happen but be safe)
            print(f"  SKIP (already filled): {m['artist']} -> {row['YouTube Channel']}")
            continue

        if dry_run:
            print(f"  [dry-run] would write: {m['artist']} -> {m['handle']}")
        else:
            row["YouTube Channel"] = m["handle"]
            save_artists(artists, fieldnames)   # save after every write
            print(f"  Written: {m['artist']} -> {m['handle']}")
        written += 1

    return written


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true",
        help="Print all matches with confidence scores without writing anything. "
             "Always do this first.",
    )
    mode.add_argument(
        "--write-high", action="store_true",
        help=f"Auto-write matches with score >= {HIGH_THRESHOLD}. "
             "Print lower-confidence matches for manual review.",
    )
    mode.add_argument(
        "--write-all", action="store_true",
        help=f"Write all matches with score >= {MIN_THRESHOLD}. "
             "Review changes with: git diff live-shows/artists.tsv",
    )
    mode.add_argument(
        "--auth-only", action="store_true",
        help="Authenticate and save token.json, then exit.",
    )

    args = parser.parse_args()

    # Default to --dry-run if no mode specified
    if not any([args.dry_run, args.write_high, args.write_all, args.auth_only]):
        print("No mode specified — defaulting to --dry-run. "
              "Use --write-high or --write-all to apply changes.\n")
        args.dry_run = True

    # Auth
    print("Authenticating with YouTube...")
    youtube = get_authenticated_service()
    print("Authenticated.")

    if args.auth_only:
        print("Auth complete. token.json saved.")
        return

    # Fetch subscriptions
    subs = fetch_subscriptions(youtube)
    if not subs:
        print("No subscriptions found — nothing to match.")
        return

    # Resolve @handles for all subscribed channels in batches
    print(f"\nResolving @handles for {len(subs)} channels...")
    channel_ids = [s["channel_id"] for s in subs]
    handle_map  = fetch_handles(youtube, channel_ids)
    print(f"Resolved {len(handle_map)} handles.")

    # Load artists.tsv
    artists, fieldnames = load_artists()
    blank_count = sum(1 for r in artists if not r.get("YouTube Channel", "").strip())
    print(f"\nLoaded {len(artists)} artists, {blank_count} with blank YouTube Channel.\n")

    # Match
    matches = match_subscriptions_to_artists(subs, handle_map, artists)
    print_matches(matches, HIGH_THRESHOLD)

    # Apply
    if args.dry_run:
        print("\n[dry-run] No changes written.")
        return

    write_threshold = HIGH_THRESHOLD if args.write_high else MIN_THRESHOLD
    label = "high-confidence" if args.write_high else "all"
    print(f"\nWriting {label} matches (score >= {write_threshold})...")
    written = apply_matches(matches, artists, fieldnames,
                            min_score=write_threshold, dry_run=False)
    print(f"\n{written} handle(s) written to artists.tsv.")

    if args.write_high:
        lower = [m for m in matches if m["score"] < HIGH_THRESHOLD]
        if lower:
            print(f"\n{len(lower)} lower-confidence match(es) not auto-written "
                  "(review above and add manually if correct):")
            for m in lower:
                print(f"  {m['score']:.2f}  {m['artist']:<40}  {m['handle']}")

    print("\nReview changes with: git diff live-shows/artists.tsv")


if __name__ == "__main__":
    main()
