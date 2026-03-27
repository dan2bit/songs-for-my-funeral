#!/usr/bin/env python3
"""
Populates the YouTube Channel and Spotify URL columns in artists.tsv.

For each artist with a blank YouTube Channel or Spotify URL, the script:

  YouTube:
    1. Calls search.list (type=channel) to find candidate channels.
    2. For each candidate that passes the name-similarity check, calls
       channels.list to retrieve the channel's customUrl (@handle).
       Falls back to https://www.youtube.com/@<customUrl> or the channel URL
       if no handle is available.
    Writes nothing if no result passes the similarity check.

  Spotify:
    Calls the Spotify Web API search endpoint with type=artist.
    Uses the top result's external_urls.spotify value.
    Writes nothing if no result passes the similarity check.

Progress is saved to artists.tsv after every successful API write, so if the
script is interrupted (e.g. by a YouTube quota limit) results already found
are not lost. Re-running the script safely skips any row that already has a value.

Usage:
    python3 artists_youtube_spotify.py [--dry-run] [--only-youtube] [--only-spotify]
                                       [--artist NAME]

    --dry-run       Print proposed changes without writing to artists.tsv
    --only-youtube  Only run the YouTube pass
    --only-spotify  Only run the Spotify pass
    --artist NAME   Only process this artist (case-insensitive substring match)

Environment variables (from .env in the same directory):
    YOUTUBE_API_KEY          YouTube Data API v3 key (read-only)
    SPOTIFY_CLIENT_ID        Spotify app client ID
    SPOTIFY_CLIENT_SECRET    Spotify app client secret

Requires:
    pip install python-dotenv requests
"""

import argparse
import csv
import os
import re
import sys
import time
import unicodedata

import requests
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH  = os.path.join(SCRIPT_DIR, ".env")
ARTISTS_TSV  = os.path.join(SCRIPT_DIR, "artists.tsv")

YT_SEARCH_URL   = "https://www.googleapis.com/youtube/v3/search"
YT_CHANNEL_URL  = "https://www.googleapis.com/youtube/v3/channels"
SPOTIFY_TOKEN_URL  = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"

# Seconds to wait between API calls
YT_DELAY      = 0.6   # search.list + channels.list = 2 calls per artist; be conservative
SPOTIFY_DELAY = 0.3

# Minimum Jaccard similarity to accept a result as a genuine match
MATCH_THRESHOLD = 0.55

# ── Name normalisation & similarity ──────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase, strip accents, remove punctuation, drop leading 'the'."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"^the\s+", "", s).strip()
    return s


def _tokens(s: str) -> set:
    """Return meaningful (>2 char) tokens, dropping noise words."""
    NOISE = {"and", "the", "feat", "with", "band", "live"}
    return {w for w in _norm(s).split() if len(w) > 2 and w not in NOISE}


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity on token sets."""
    wa, wb = _tokens(a), _tokens(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def is_match(query: str, result: str) -> bool:
    """
    True if query and result look like the same artist.

    Rules (any one is sufficient):
    - Jaccard similarity >= MATCH_THRESHOLD
    - Normalised query is a substring of normalised result (or vice-versa),
      BUT only if the query has at least 2 tokens OR is >5 chars,
      to avoid "Live" or "Beck" matching everything.
    """
    sim = _similarity(query, result)
    if sim >= MATCH_THRESHOLD:
        return True
    qn, rn = _norm(query), _norm(result)
    # Substring check with guard against very short names swallowing everything
    if len(qn) > 5 or len(_tokens(query)) >= 2:
        if qn in rn or rn in qn:
            return True
    return False

# ── YouTube ───────────────────────────────────────────────────────────────────

class YouTubeQuotaError(Exception):
    pass


def _yt_get(url: str, params: dict) -> dict:
    """Make a YouTube API GET, raising YouTubeQuotaError on quota exhaustion."""
    try:
        resp = requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        raise requests.RequestException(str(e))

    if resp.status_code == 403:
        data = resp.json()
        errors = data.get("error", {}).get("errors", [])
        if any(e.get("reason") == "quotaExceeded" for e in errors):
            raise YouTubeQuotaError("YouTube API quota exceeded.")
        resp.raise_for_status()

    resp.raise_for_status()
    return resp.json()


def yt_get_handle(channel_id: str, api_key: str) -> str:
    """
    Given a channel ID, return the @handle via channels.list.
    Returns "@handle" if customUrl is set, otherwise the channel URL.
    """
    data = _yt_get(YT_CHANNEL_URL, {
        "part":  "snippet",
        "id":    channel_id,
        "key":   api_key,
    })
    items = data.get("items", [])
    if not items:
        return f"https://www.youtube.com/channel/{channel_id}"
    custom = items[0]["snippet"].get("customUrl", "")
    if custom:
        handle = custom if custom.startswith("@") else f"@{custom}"
        return handle
    return f"https://www.youtube.com/channel/{channel_id}"


def yt_search_channel(artist: str, api_key: str) -> str | None:
    """
    Search YouTube for a channel matching `artist`.
    Returns the @handle or channel URL if a plausible match is found,
    otherwise None.
    Raises YouTubeQuotaError if the quota is exhausted.
    """
    data = _yt_get(YT_SEARCH_URL, {
        "part":       "snippet",
        "q":          artist,
        "type":       "channel",
        "maxResults": 3,
        "key":        api_key,
    })

    items = data.get("items", [])
    if not items:
        print(f"        → YouTube: no results returned")
        return None

    for item in items:
        title      = item["snippet"]["channelTitle"]
        channel_id = item["snippet"]["channelId"]
        match      = is_match(artist, title)
        print(f"        → YouTube candidate: \"{title}\" (match={match})")
        if not match:
            continue
        # Second call to get the @handle
        time.sleep(YT_DELAY)
        return yt_get_handle(channel_id, api_key)

    return None

# ── Spotify ───────────────────────────────────────────────────────────────────

_spotify_token_cache: dict = {}


def _get_spotify_token(client_id: str, client_secret: str) -> str:
    if _spotify_token_cache.get("token"):
        return _spotify_token_cache["token"]
    resp = requests.post(
        SPOTIFY_TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    _spotify_token_cache["token"] = token
    return token


def spotify_search_artist(artist: str, client_id: str, client_secret: str) -> str | None:
    try:
        token = _get_spotify_token(client_id, client_secret)
    except requests.RequestException as e:
        print(f"    [SPOTIFY TOKEN ERROR] {e}", file=sys.stderr)
        return None

    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            SPOTIFY_SEARCH_URL,
            params={"q": artist, "type": "artist", "limit": 3},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    [SPOTIFY ERROR] {artist}: {e}", file=sys.stderr)
        return None

    items = resp.json().get("artists", {}).get("items", [])
    if not items:
        print(f"        → Spotify: no results returned")
        return None

    for item in items:
        name  = item.get("name", "")
        url   = item.get("external_urls", {}).get("spotify", "")
        match = is_match(artist, name)
        print(f"        → Spotify candidate: \"{name}\" (match={match})")
        if not url or not match:
            continue
        return url

    return None

# ── TSV helpers ───────────────────────────────────────────────────────────────

def load_artists(path: str) -> tuple[list[dict], list[str]]:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    return rows, fieldnames


def save_artists(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                           lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--dry-run",      action="store_true",
                        help="Print changes without writing to artists.tsv")
    parser.add_argument("--only-youtube", action="store_true",
                        help="Skip the Spotify pass")
    parser.add_argument("--only-spotify", action="store_true",
                        help="Skip the YouTube pass")
    parser.add_argument("--artist",       metavar="NAME",
                        help="Only process this artist (case-insensitive substring match)")
    args = parser.parse_args()

    load_dotenv(DOTENV_PATH)
    yt_key         = os.getenv("YOUTUBE_API_KEY", "")
    spotify_id     = os.getenv("SPOTIFY_CLIENT_ID", "")
    spotify_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    do_youtube = not args.only_spotify
    do_spotify = not args.only_youtube

    if do_youtube and not yt_key:
        print("WARNING: YOUTUBE_API_KEY not set — skipping YouTube pass.", file=sys.stderr)
        do_youtube = False
    if do_spotify and (not spotify_id or not spotify_secret):
        print("WARNING: SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set — skipping Spotify pass.",
              file=sys.stderr)
        do_spotify = False

    rows, fieldnames = load_artists(ARTISTS_TSV)
    if not rows:
        print("artists.tsv is empty or missing.", file=sys.stderr)
        sys.exit(1)

    # Ensure columns exist in fieldnames and rows
    for col in ("YouTube Channel", "Spotify URL"):
        if col not in fieldnames:
            fieldnames.append(col)
        for row in rows:
            row.setdefault(col, "")

    artist_filter  = args.artist.lower() if args.artist else None
    yt_filled      = 0
    spotify_filled = 0
    yt_skipped     = 0
    spotify_skipped = 0
    quota_hit      = False

    for row in rows:
        name = row["Artist"]

        if artist_filter and artist_filter not in name.lower():
            continue

        # ── YouTube ──────────────────────────────────────────────────────────
        if do_youtube and not quota_hit:
            existing_yt = row.get("YouTube Channel", "").strip()
            if existing_yt:
                yt_skipped += 1
            else:
                print(f"\n[YT]  {name}")
                try:
                    handle = yt_search_channel(name, yt_key)
                    time.sleep(YT_DELAY)
                    if handle:
                        print(f"        → writing: {handle}")
                        if not args.dry_run:
                            row["YouTube Channel"] = handle
                            save_artists(ARTISTS_TSV, rows, fieldnames)
                        yt_filled += 1
                    else:
                        print(f"        → no match — leaving blank")
                except YouTubeQuotaError:
                    print(
                        "\n*** YouTube API quota exceeded. ***\n"
                        "Progress saved. Re-run tomorrow (quota resets at midnight Pacific)\n"
                        "or use --only-spotify to continue with Spotify in the meantime.",
                        file=sys.stderr,
                    )
                    quota_hit = True
                    if not args.dry_run:
                        save_artists(ARTISTS_TSV, rows, fieldnames)
                except requests.RequestException as e:
                    print(f"        → [YT ERROR] {e}", file=sys.stderr)

        # ── Spotify ──────────────────────────────────────────────────────────
        if do_spotify:
            existing_sp = row.get("Spotify URL", "").strip()
            if existing_sp:
                spotify_skipped += 1
            else:
                print(f"\n[SP]  {name}")
                url = spotify_search_artist(name, spotify_id, spotify_secret)
                time.sleep(SPOTIFY_DELAY)
                if url:
                    print(f"        → writing: {url}")
                    if not args.dry_run:
                        row["Spotify URL"] = url
                        save_artists(ARTISTS_TSV, rows, fieldnames)
                    spotify_filled += 1
                else:
                    print(f"        → no match — leaving blank")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print(f"Summary:")
    if do_youtube:
        label = " (quota hit — incomplete)" if quota_hit else ""
        print(f"  YouTube:  {yt_filled} filled, {yt_skipped} already had a value{label}")
    if do_spotify:
        print(f"  Spotify:  {spotify_filled} filled, {spotify_skipped} already had a value")
    if args.dry_run:
        print("  [dry-run] No changes written.")


if __name__ == "__main__":
    main()
