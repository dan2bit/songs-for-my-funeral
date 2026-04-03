#!/usr/bin/env python3
"""
youtube_subscriptions_to_artists.py — Populator for artists.tsv YouTube Channel column

TWO-PHASE WORKFLOW (recommended):

  Phase 1 — fetch results from YouTube and cache locally (costs quota):

    python3 youtube_subscriptions_to_artists.py --fetch
    python3 youtube_subscriptions_to_artists.py --fetch --limit 10  # spread across days

    Searches YouTube by artist name for every blank entry in artists.tsv.
    Writes results to youtube_handle_candidates.tsv (artist, handle,
    channel_title, score). Safe to re-run — already-fetched artists are
    skipped unless --refetch is passed.

    Quota: ~101 units per artist (search.list + channels.list).
    With 65 blanks: ~6,565 units total. Use --limit to spread across days.

  Phase 2 — write from the cached file into artists.tsv (zero quota):

    python3 youtube_subscriptions_to_artists.py --write              # default threshold 0.8
    python3 youtube_subscriptions_to_artists.py --write --threshold 0.6
    python3 youtube_subscriptions_to_artists.py --write --threshold 0.0  # write everything

    Reads youtube_handle_candidates.tsv and patches artists.tsv for any
    artist whose score meets the threshold and whose YouTube Channel is
    still blank. Always review with: git diff live-shows/artists.tsv

LEGACY MODE (subscriptions list — limited utility):

    python3 youtube_subscriptions_to_artists.py --subscriptions --write-all

    Only matches artists you're already subscribed to on YouTube.
    Useful as a quick pass before --fetch, but leaves most blanks unfilled.

REQUIRES OAuth — same token.json / client_secrets.json used by
youtube_create_playlists.py. Run --auth-only once if not yet authenticated.
--write and --subscriptions --dry-run do not need auth.

CANDIDATE FILE: youtube_handle_candidates.tsv
    Columns: artist, handle, channel_title, score
    Gitignored (local working file). Edit manually to correct bad matches
    before running --write. Delete a row to skip that artist.

CONFIDENCE SCORES:
    1.0   Exact normalized name match
    0.8+  Strong token overlap — auto-written at default threshold
    0.55+ Partial match — in candidates file, skipped at default threshold
    <0.55 No confident match — not written to candidates file; listed at end

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

SCRIPT_DIR       = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

SCOPES           = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS   = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
TOKEN_FILE       = os.environ.get("YOUTUBE_TOKEN_FILE",     "token.json")
ARTISTS_TSV      = os.path.join(SCRIPT_DIR, "artists.tsv")
CANDIDATES_TSV   = os.path.join(SCRIPT_DIR, "youtube_handle_candidates.tsv")
CANDIDATE_FIELDS = ["artist", "handle", "channel_title", "score"]

DEFAULT_WRITE_THRESHOLD = 0.8
MIN_FETCH_THRESHOLD     = 0.55   # minimum score to include in candidates file at all

PAGE_DELAY = 0.3   # seconds between API calls


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


def load_candidates() -> dict[str, dict]:
    """Return {artist_name: row} from candidates TSV."""
    if not os.path.exists(CANDIDATES_TSV):
        return {}
    with open(CANDIDATES_TSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return {row["artist"]: row for row in reader}


def save_candidates(candidates: dict[str, dict]) -> None:
    with open(CANDIDATES_TSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CANDIDATE_FIELDS, delimiter="\t",
                           lineterminator="\n")
        w.writeheader()
        # Sort by score descending for human readability
        for row in sorted(candidates.values(), key=lambda r: -float(r["score"])):
            w.writerow(row)


# ── Fetch mode ────────────────────────────────────────────────────────────────

def search_handle_for_artist(youtube, artist_name: str) -> tuple[str, float, str]:
    """
    Search YouTube for the artist name. Returns (handle, score, channel_title).
    Returns ("", 0.0, "") if no result meets MIN_FETCH_THRESHOLD.
    Quota: ~101 units (search.list + channels.list).
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
            try:
                ch_resp = youtube.channels().list(part="snippet", id=channel_id).execute()
                ch_items = ch_resp.get("items", [])
                if ch_items:
                    custom = ch_items[0]["snippet"].get("customUrl", "")
                    best_handle = custom if custom.startswith("@") else f"@{custom}" if custom else f"https://www.youtube.com/channel/{channel_id}"
                else:
                    best_handle = f"https://www.youtube.com/channel/{channel_id}"
            except Exception:
                best_handle = f"https://www.youtube.com/channel/{channel_id}"

    if best_score >= MIN_FETCH_THRESHOLD:
        return best_handle, best_score, best_title
    return "", 0.0, ""


def run_fetch_mode(youtube, artists: list[dict], limit: int | None, refetch: bool) -> None:
    """
    Phase 1: search YouTube for blank artists and cache results locally.
    Does NOT write to artists.tsv. Use --write for that.
    """
    blanks = [
        row for row in artists
        if not row.get("YouTube Channel", "").strip()
    ]

    if not blanks:
        print("No blank YouTube Channel entries found — nothing to fetch.")
        return

    # Load existing candidates to skip already-fetched artists
    candidates = load_candidates()
    already_done = set(candidates.keys()) if not refetch else set()

    to_fetch = [row for row in blanks if row["Artist"] not in already_done]
    if limit:
        to_fetch = to_fetch[:limit]

    skipped_cached = len(blanks) - len([r for r in blanks if r["Artist"] not in already_done])
    print(f"{len(blanks)} blank entries total.")
    if skipped_cached:
        print(f"  {skipped_cached} already in candidates file — skipping (use --refetch to redo).")
    print(f"  Fetching {len(to_fetch)}" + (f" (--limit {limit})" if limit else "") + ".\n")

    no_match = []

    for idx, row in enumerate(to_fetch, 1):
        artist_name = row["Artist"]
        print(f"[{idx}/{len(to_fetch)}] {artist_name}")

        handle, score, channel_title = search_handle_for_artist(youtube, artist_name)
        time.sleep(PAGE_DELAY)

        if not handle:
            print(f"  → No confident match (score < {MIN_FETCH_THRESHOLD})\n")
            no_match.append(artist_name)
            continue

        flag = "✓" if score >= DEFAULT_WRITE_THRESHOLD else "?"
        print(f"  → {handle}  ({channel_title})  score {score:.2f} {flag}\n")

        candidates[artist_name] = {
            "artist":        artist_name,
            "handle":        handle,
            "channel_title": channel_title,
            "score":         f"{score:.4f}",
        }
        save_candidates(candidates)   # save after every artist

    print("=" * 60)
    total_in_file = len(candidates)
    high = sum(1 for c in candidates.values() if float(c["score"]) >= DEFAULT_WRITE_THRESHOLD)
    low  = total_in_file - high
    print(f"Candidates file: {total_in_file} entries "
          f"({high} high-confidence ≥{DEFAULT_WRITE_THRESHOLD}, {low} lower).")
    print(f"Written to: {CANDIDATES_TSV}")

    if no_match:
        print(f"\n{len(no_match)} artist(s) had no confident match — manual YouTube search needed:")
        for name in no_match:
            print(f"  {name}")

    remaining_unfetched = len(blanks) - len(already_done) - len(to_fetch)
    if remaining_unfetched > 0:
        print(f"\n{remaining_unfetched} blank entries not yet fetched. Run again to continue.")

    print(f"\nNext step: python3 youtube_subscriptions_to_artists.py --write")


# ── Write mode ────────────────────────────────────────────────────────────────

def run_write_mode(
    artists: list[dict],
    fieldnames: list[str],
    threshold: float,
    dry_run: bool,
) -> None:
    """
    Phase 2: read youtube_handle_candidates.tsv and write into artists.tsv.
    Zero quota cost.
    """
    candidates = load_candidates()
    if not candidates:
        sys.exit(
            f"No candidates file found at: {CANDIDATES_TSV}\n"
            "Run --fetch first to populate it."
        )

    print(f"Loaded {len(candidates)} candidates from {os.path.basename(CANDIDATES_TSV)}.")
    print(f"Write threshold: score >= {threshold}\n")

    written      = 0
    skipped_low  = []
    skipped_done = []

    # Build artist name → row index map
    artist_index = {row["Artist"]: i for i, row in enumerate(artists)}

    for artist_name, cand in sorted(candidates.items(), key=lambda x: -float(x[1]["score"])):
        score  = float(cand["score"])
        handle = cand["handle"]
        title  = cand["channel_title"]

        row_idx = artist_index.get(artist_name)
        if row_idx is None:
            print(f"  SKIP (not in artists.tsv): {artist_name}")
            continue

        row = artists[row_idx]
        if row.get("YouTube Channel", "").strip():
            skipped_done.append(artist_name)
            continue

        if score < threshold:
            skipped_low.append((artist_name, handle, score, title))
            continue

        flag = "✓" if score >= DEFAULT_WRITE_THRESHOLD else "?"
        if dry_run:
            print(f"  {score:.2f} {flag}  {artist_name:<40}  {handle}  ({title})  [would write]")
        else:
            artists[row_idx]["YouTube Channel"] = handle
            save_artists(artists, fieldnames)
            print(f"  {score:.2f} {flag}  {artist_name:<40}  {handle}  ({title})  ✓ written")
        written += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Results: {written} written, "
          f"{len(skipped_low)} below threshold, {len(skipped_done)} already filled.")

    if skipped_low:
        print(f"\nBelow threshold ({threshold}) — lower it with --threshold to include:")
        for name, handle, score, title in sorted(skipped_low, key=lambda x: -x[2]):
            print(f"  {score:.2f}  {name:<40}  {handle}  ({title})")

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
        if best_sub and best_score >= MIN_FETCH_THRESHOLD:
            matches.append({
                "artist":        artist_name,
                "channel_title": best_sub["title"],
                "handle":        handle_map.get(best_sub["channel_id"], ""),
                "score":         best_score,
                "row_idx":       i,
            })
    matches.sort(key=lambda m: -m["score"])
    return matches


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

    if not matches:
        print("No matches found above minimum threshold.")
        return

    print(f"\n{'Score':>6}  {'Artist':<40}  {'Subscribed Channel':<40}  Handle")
    print("-" * 120)
    for m in matches:
        flag = "✓" if m["score"] >= DEFAULT_WRITE_THRESHOLD else "?"
        print(f"  {m['score']:.2f} {flag}  {m['artist']:<40}  {m['channel_title']:<40}  {m['handle']}")
    auto = sum(1 for m in matches if m["score"] >= DEFAULT_WRITE_THRESHOLD)
    print(f"\n{auto} high-confidence, {len(matches)-auto} lower-confidence matches found.")

    if dry_run:
        print("\n[dry-run] No changes written.")
        return

    write_threshold = DEFAULT_WRITE_THRESHOLD if write_high else MIN_FETCH_THRESHOLD
    label = "high-confidence" if write_high else "all"
    print(f"\nWriting {label} matches (score >= {write_threshold})...")
    written = 0
    for m in matches:
        if m["score"] < write_threshold or not m["handle"]:
            continue
        row = artists[m["row_idx"]]
        if row.get("YouTube Channel", "").strip():
            continue
        row["YouTube Channel"] = m["handle"]
        save_artists(artists, fieldnames)
        print(f"  Written: {m['artist']} -> {m['handle']}")
        written += 1
    print(f"\n{written} handle(s) written to artists.tsv.")
    print("\nReview changes with: git diff live-shows/artists.tsv")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--fetch", action="store_true",
        help="Phase 1: search YouTube for blank artists and write results to "
             "youtube_handle_candidates.tsv. Costs quota (~101 units/artist). "
             "Skips artists already in the candidates file.",
    )
    mode.add_argument(
        "--write", action="store_true",
        help="Phase 2: read youtube_handle_candidates.tsv and write handles into "
             "artists.tsv. Zero quota cost. Use --threshold to control what gets written.",
    )
    mode.add_argument(
        "--subscriptions", action="store_true",
        help="Legacy: match against your YouTube subscriptions list. Only finds "
             "artists you're already subscribed to.",
    )
    mode.add_argument(
        "--auth-only", action="store_true",
        help="Authenticate and save token.json, then exit.",
    )

    # --fetch options
    parser.add_argument("--limit", type=int, metavar="N",
                        help="(--fetch) Process at most N artists per run.")
    parser.add_argument("--refetch", action="store_true",
                        help="(--fetch) Re-fetch artists already in the candidates file.")

    # --write options
    parser.add_argument("--threshold", type=float, default=DEFAULT_WRITE_THRESHOLD,
                        metavar="SCORE",
                        help=f"(--write) Minimum confidence score to write. "
                             f"Default: {DEFAULT_WRITE_THRESHOLD}. "
                             f"Range: 0.0–1.0.")
    parser.add_argument("--dry-run", action="store_true",
                        help="(--write / --subscriptions) Print what would be written "
                             "without writing anything.")

    # --subscriptions legacy options
    parser.add_argument("--write-high", action="store_true",
                        help="(--subscriptions) Write high-confidence matches only.")
    parser.add_argument("--write-all", action="store_true",
                        help="(--subscriptions) Write all matches above minimum threshold.")

    args = parser.parse_args()

    # --write and --subscriptions --dry-run don't need auth
    needs_auth = args.fetch or args.auth_only or (args.subscriptions and not args.dry_run)
    youtube = None
    if needs_auth:
        print("Authenticating with YouTube...")
        youtube = get_authenticated_service()
        print("Authenticated.")

    if args.auth_only:
        print("Auth complete. token.json saved.")
        return

    artists, fieldnames = load_artists()

    if args.fetch:
        run_fetch_mode(youtube, artists, limit=args.limit, refetch=args.refetch)

    elif args.write:
        run_write_mode(artists, fieldnames, threshold=args.threshold, dry_run=args.dry_run)

    elif args.subscriptions:
        if args.dry_run and youtube is None:
            # dry-run subscriptions still needs auth to fetch the list
            print("Authenticating with YouTube...")
            youtube = get_authenticated_service()
            print("Authenticated.")
        run_subscriptions_mode(
            youtube, artists, fieldnames,
            write_high=args.write_high,
            write_all=args.write_all,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
