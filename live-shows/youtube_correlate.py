#!/usr/bin/env python3
"""
Correlates youtube_videos.tsv and youtube_playlists.tsv against show history files.

Naming conventions on @dan2bit channel:
  Videos:    "Sue Foley LIVE - Nothin' In Ramblin' (bootleg)"
             description: "(Memphis Minnie cover) from Hamilton Live (DC) on 03/11/26"
  Playlists: "Keb' Mo' LIVE solo - Maryland Hall, Annapolis 11/21/25"

Logic per show:
  1. PLAYLIST MATCH: Look for a playlist whose title contains the HEADLINER name + "LIVE"
     AND whose title contains a DATE VARIANT matching the show date (required).
     Venue-only matches are intentionally excluded to prevent wrong-year false positives.
     If found → use the playlist URL as the Playlist URL.
  2. VIDEO MATCH: If no playlist found, search for ANY video whose description contains
     a date string matching the show date (MM/DD/YY or MM/DD/YYYY). No artist filter —
     this covers multi-bill shows where supporting acts were filmed instead of the headliner.
  3. Output one row per show with: playlist URL (if found) OR video count.

Key improvements over v1:
  - Playlist matching requires DATE match (venue-only removed — caused year mismatches)
  - artist_in_title uses NOISE_WORDS to avoid generic false positives
  - find_videos uses date-only matching (no artist filter) to catch support act footage

Usage:
    python3 youtube_correlate.py

Input files (must be in same directory):
    youtube_videos.tsv
    youtube_playlists.tsv
    live_shows_history.tsv         — 2021-2025 history (Show Date, Artist, Supporting Acts, Venue, ...)
    live_shows_2026.tsv            — 2026 attended shows (Show Date, Artist, Venue Name, ...)

Output:
    history_youtube_correlation.tsv   — 2021-2025
    shows_2026_youtube_correlation.tsv — 2026 attended shows only
"""

import csv
import re
from datetime import datetime

def load_tsv(filename):
    with open(filename, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def normalize(s):
    return re.sub(r"[^\w\s]", "", s.lower()).strip()

# Words too generic to use as distinctive artist-name match tokens
NOISE_WORDS = {"band", "the", "and", "live", "feat", "featuring", "with"}

def artist_in_title(artist, title):
    """Check if headliner artist name appears in playlist title.
    Requires full normalized name match OR all distinctive words (>4 chars, not noise)."""
    artist_norm = normalize(artist)
    title_norm = normalize(title)
    if artist_norm in title_norm:
        return True
    words = [w for w in artist_norm.split() if len(w) > 4 and w not in NOISE_WORDS]
    if not words:
        return False
    return all(w in title_norm for w in words)

def date_variants(date_str):
    """
    Given YYYY-MM-DD, return date strings that might appear in a YouTube title.
    e.g. 2025-11-21 → ['11/21/25', '11/21/2025', '11/21/25', '11/21/2025']
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []
    yy = d.strftime("%y")
    yyyy = d.strftime("%Y")
    return [
        f"{d.month}/{d.day}/{yy}",
        f"{d.month}/{d.day}/{yyyy}",
        f"{d.strftime('%m')}/{d.strftime('%d')}/{yy}",
        f"{d.strftime('%m')}/{d.strftime('%d')}/{yyyy}",
    ]

def find_playlist(headliner, date_str, playlists):
    """
    Find a playlist matching this show.
    Rules:
      - Playlist title must contain the HEADLINER name
      - Playlist title must contain "LIVE"
      - Playlist title must contain a DATE VARIANT for the show date (required)
    Venue-only matches are intentionally excluded to prevent year mismatches.
    """
    date_vars = date_variants(date_str)
    if not date_vars:
        return None
    for pl in playlists:
        title = pl["title"]
        title_norm = normalize(title)
        if "live" not in title_norm:
            continue
        if not artist_in_title(headliner, title):
            continue
        if any(dv in title for dv in date_vars):
            return pl
    return None

def find_videos(date_str, videos):
    """
    Find ANY video whose description contains the show date.
    No artist filter — covers multi-bill shows and cases where supporting
    acts were filmed rather than (or in addition to) the headliner.
    """
    date_vars = date_variants(date_str)
    if not date_vars:
        return []
    matches = []
    for v in videos:
        desc = v.get("description", "")
        if any(dv in desc for dv in date_vars):
            matches.append(v)
    return matches

def normalize_shows(shows, artist_col, venue_col, date_col):
    out = []
    for s in shows:
        out.append({
            "Show Date":        s.get(date_col, ""),
            "Artist":           s.get(artist_col, ""),
            "Supporting Acts":  s.get("Supporting Acts", s.get("Supporting Artist", "")),
            "Venue":            s.get(venue_col, ""),
            "Setlist.fm URL":   s.get("Setlist.fm URL", ""),
            "Playlist URL":     s.get("Playlist URL", ""),
            "Notes / Memories": s.get("Notes / Memories", s.get("Notes", "")),
        })
    return out

def correlate(shows, videos, playlists):
    results = []
    playlist_hits = 0
    video_hits = 0
    for show in shows:
        headliner = show["Artist"]
        date_str  = show["Show Date"]
        venue     = show["Venue"]
        setlist   = show.get("Setlist.fm URL", "")

        playlist = find_playlist(headliner, date_str, playlists)
        vids = []
        if not playlist:
            vids = find_videos(date_str, videos)

        if playlist:
            playlist_hits += 1
            yt_url     = playlist["url"]
            match_type = f"Playlist ({playlist['item_count']} videos)"
            yt_title   = playlist["title"]
        elif vids:
            video_hits += 1
            yt_url     = ""
            match_type = f"{len(vids)} video(s) found"
            yt_title   = " | ".join(v["title"] for v in vids[:3])
            if len(vids) > 3:
                yt_title += f" ... (+{len(vids)-3} more)"
        else:
            yt_url     = ""
            match_type = "No match"
            yt_title   = ""

        results.append({
            "Show Date":        date_str,
            "Artist":           headliner,
            "Supporting Acts":  show.get("Supporting Acts", ""),
            "Venue":            venue,
            "Setlist.fm URL":   setlist,
            "Playlist URL":     yt_url,
            "Match Type":       match_type,
            "YT Title":         yt_title,
            "Notes / Memories": show.get("Notes / Memories", ""),
        })
    return results, playlist_hits, video_hits

def write_results(results, filename):
    fieldnames = [
        "Show Date", "Artist", "Supporting Acts", "Venue",
        "Setlist.fm URL", "Playlist URL", "Match Type", "YT Title", "Notes / Memories"
    ]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(results)
    print(f"  Output: {filename}")

def print_summary(label, results, playlist_hits, video_hits):
    total = len(results)
    print(f"\n{label} ({total} shows):")
    print(f"  Playlist matches:   {playlist_hits}")
    print(f"  Video-only matches: {video_hits}")
    print(f"  No match:           {total - playlist_hits - video_hits}")
    for r in results:
        if r["Match Type"] != "No match":
            print(f"  {r['Show Date']} | {r['Artist']}")
            print(f"    → {r['Match Type']}: {r['YT Title'][:80]}")

def main():
    import os
    videos    = load_tsv("youtube_videos.tsv")
    playlists = load_tsv("youtube_playlists.tsv")
    print(f"Loaded {len(videos)} videos, {len(playlists)} playlists")

    if os.path.exists("live_shows_history.tsv"):
        history_raw = load_tsv("live_shows_history.tsv")
        history = normalize_shows(history_raw, "Artist", "Venue", "Show Date")
        print(f"Loaded {len(history)} history shows (2021-2025)")
        results_h, ph, vh = correlate(history, videos, playlists)
        write_results(results_h, "history_youtube_correlation.tsv")
        print_summary("2021-2025 history", results_h, ph, vh)
    else:
        print("live_shows_history.tsv not found — skipping")

    if os.path.exists("live_shows_2026.tsv"):
        shows_2026_raw = load_tsv("live_shows_2026.tsv")
        attended = [s for s in shows_2026_raw if s.get("Status", "") == "attended"]
        shows_2026 = normalize_shows(attended, "Artist", "Venue Name", "Show Date")
        print(f"\nLoaded {len(shows_2026)} attended 2026 shows")
        results_26, ph, vh = correlate(shows_2026, videos, playlists)
        write_results(results_26, "shows_2026_youtube_correlation.tsv")
        print_summary("2026 attended shows", results_26, ph, vh)
    else:
        print("live_shows_2026.tsv not found — skipping")

if __name__ == "__main__":
    main()
