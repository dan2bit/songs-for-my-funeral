#!/usr/bin/env python3
"""
Populates the YouTube Channel and Spotify URL columns in artists.tsv.

For each artist with a blank YouTube Channel or Spotify URL, the script:

  YouTube:
    Calls the YouTube Data API v3 search.list endpoint with type=channel.
    Uses the top result's customUrl (the @handle) if available, falling back to
    the channel's canonical URL. Only writes a value if the result looks like a
    genuine match (name similarity check).

  Spotify:
    Calls the Spotify Web API search endpoint with type=artist.
    Uses the top result's external_urls.spotify value.
    Only writes a value if the returned artist name is a close match.

The script reads and writes artists.tsv in-place, preserving any values that
are already filled in (i.e. it is safe to re-run after manual corrections).

Usage:
    python3 artists_youtube_spotify.py [--dry-run] [--only-youtube] [--only-spotify]

    --dry-run       Print proposed changes without writing to artists.tsv
    --only-youtube  Only run the YouTube pass
    --only-spotify  Only run the Spotify pass
    --artist NAME   Only process a single artist (useful for spot-checks)

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

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
DOTENV_PATH = os.path.join(SCRIPT_DIR, ".env")
ARTISTS_TSV = os.path.join(SCRIPT_DIR, "artists.tsv")

YT_SEARCH_URL     = "https://www.googleapis.com/youtube/v3/search"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_SEARCH_URL = "https://api.spotify.com/v1/search"

# Seconds to wait between API calls to stay well under quota limits
YT_DELAY      = 0.5
SPOTIFY_DELAY = 0.3

# Minimum name similarity ratio (0–1) to accept a result as a genuine match
MATCH_THRESHOLD = 0.6

# ── Name normalisation & similarity ──────────────────────────────────────────

def _norm(s: str) -> str:
    """Lowercase, strip accents, remove punctuation/articles for comparison."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")  # strip accents
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    # strip leading "the " for matching purposes
    s = re.sub(r"^the\s+", "", s).strip()
    return s


def _similarity(a: str, b: str) -> float:
    """Simple token-overlap similarity (Jaccard on word sets)."""
    wa = set(_norm(a).split())
    wb = set(_norm(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def is_match(query_name: str, result_name: str) -> bool:
    sim = _similarity(query_name, result_name)
    # Also accept if the normalised query is a substring of the result or vice-versa
    qn = _norm(query_name)
    rn = _norm(result_name)
    substring_match = qn in rn or rn in qn
    return sim >= MATCH_THRESHOLD or substring_match

# ── YouTube ───────────────────────────────────────────────────────────────────

def yt_search_channel(artist: str, api_key: str) -> str | None:
    """
    Search YouTube for a channel matching `artist`.
    Returns the @handle (e.g. "@vanessacolliermusic") if found and plausible,
    otherwise the channel URL, otherwise None.
    """
    params = {
        "part":       "snippet",
        "q":          artist,
        "type":       "channel",
        "maxResults": 3,
        "key":        api_key,
    }
    try:
        resp = requests.get(YT_SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    [YT ERROR] {artist}: {e}", file=sys.stderr)
        return None

    items = resp.json().get("items", [])
    for item in items:
        title       = item["snippet"]["channelTitle"]
        channel_id  = item["snippet"]["channelId"]
        custom_url  = item["snippet"].get("customUrl", "")  # @handle if set
        if not is_match(artist, title):
            continue
        if custom_url:
            handle = custom_url if custom_url.startswith("@") else f"@{custom_url}"
            return handle
        return f"https://www.youtube.com/channel/{channel_id}"

    return None

# ── Spotify ───────────────────────────────────────────────────────────────────

_spotify_token_cache: dict = {}


def _get_spotify_token(client_id: str, client_secret: str) -> str:
    """Fetch (or return cached) Spotify client credentials token."""
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
    """
    Search Spotify for an artist matching `artist`.
    Returns the Spotify artist URL if found and plausible, otherwise None.
    """
    try:
        token = _get_spotify_token(client_id, client_secret)
    except requests.RequestException as e:
        print(f"    [SPOTIFY TOKEN ERROR] {e}", file=sys.stderr)
        return None

    params = {
        "q":     artist,
        "type":  "artist",
        "limit": 3,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            SPOTIFY_SEARCH_URL, params=params, headers=headers, timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    [SPOTIFY ERROR] {artist}: {e}", file=sys.stderr)
        return None

    items = resp.json().get("artists", {}).get("items", [])
    for item in items:
        name = item.get("name", "")
        url  = item.get("external_urls", {}).get("spotify", "")
        if not url:
            continue
        if not is_match(artist, name):
            continue
        return url

    return None

# ── TSV helpers ───────────────────────────────────────────────────────────────

def load_artists(path: str) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def save_artists(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                           lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
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
    yt_key          = os.getenv("YOUTUBE_API_KEY", "")
    spotify_id      = os.getenv("SPOTIFY_CLIENT_ID", "")
    spotify_secret  = os.getenv("SPOTIFY_CLIENT_SECRET", "")

    do_youtube = not args.only_spotify
    do_spotify = not args.only_youtube

    if do_youtube and not yt_key:
        print("WARNING: YOUTUBE_API_KEY not set — skipping YouTube pass.", file=sys.stderr)
        do_youtube = False
    if do_spotify and (not spotify_id or not spotify_secret):
        print("WARNING: SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set — skipping Spotify pass.",
              file=sys.stderr)
        do_spotify = False

    rows = load_artists(ARTISTS_TSV)
    if not rows:
        print("artists.tsv is empty or missing.", file=sys.stderr)
        sys.exit(1)

    fieldnames = list(rows[0].keys())

    # Ensure columns exist
    for col in ("YouTube Channel", "Spotify URL"):
        if col not in fieldnames:
            fieldnames.append(col)
            for row in rows:
                row.setdefault(col, "")

    artist_filter = args.artist.lower() if args.artist else None

    yt_filled      = 0
    spotify_filled = 0
    yt_skipped     = 0
    spotify_skipped = 0

    for row in rows:
        name = row["Artist"]

        if artist_filter and artist_filter not in name.lower():
            continue

        # ── YouTube ──────────────────────────────────────────────────────────
        if do_youtube:
            existing_yt = row.get("YouTube Channel", "").strip()
            if existing_yt:
                yt_skipped += 1
            else:
                print(f"  [YT]  Searching: {name}")
                handle = yt_search_channel(name, yt_key)
                time.sleep(YT_DELAY)
                if handle:
                    print(f"        → {handle}")
                    if not args.dry_run:
                        row["YouTube Channel"] = handle
                    yt_filled += 1
                else:
                    print(f"        → no match found")

        # ── Spotify ──────────────────────────────────────────────────────────
        if do_spotify:
            existing_sp = row.get("Spotify URL", "").strip()
            if existing_sp:
                spotify_skipped += 1
            else:
                print(f"  [SP]  Searching: {name}")
                url = spotify_search_artist(name, spotify_id, spotify_secret)
                time.sleep(SPOTIFY_DELAY)
                if url:
                    print(f"        → {url}")
                    if not args.dry_run:
                        row["Spotify URL"] = url
                    spotify_filled += 1
                else:
                    print(f"        → no match found")

    # ── Write ─────────────────────────────────────────────────────────────────
    if not args.dry_run:
        save_artists(ARTISTS_TSV, rows, fieldnames)
        print(f"\nWrote {ARTISTS_TSV}")
    else:
        print("\n[dry-run] No changes written.")

    print(f"\nSummary:")
    if do_youtube:
        print(f"  YouTube:  {yt_filled} filled, {yt_skipped} already had a value")
    if do_spotify:
        print(f"  Spotify:  {spotify_filled} filled, {spotify_skipped} already had a value")


if __name__ == "__main__":
    main()
