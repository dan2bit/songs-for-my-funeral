#!/usr/bin/env python3
"""
Correlates youtube_videos.tsv and youtube_playlists.tsv against show history files.

Naming conventions on @dan2bit channel:
  Videos:    "Sue Foley LIVE - Nothin' In Ramblin' (bootleg)"
             description: "(Memphis Minnie cover) from Hamilton Live (DC) on 03/11/26"
  Playlists: "Keb' Mo' LIVE solo - Maryland Hall, Annapolis 11/21/25"

Logic per show:
  1. Look for a playlist whose title contains the artist name + "LIVE"
     and whose title contains a date or venue fragment matching the show.
     If found → use the playlist URL as the Playlist URL.
  2. If no playlist → count individual videos whose description contains
     a date string matching the show date (MM/DD/YY or MM/DD/YYYY).
  3. Output one row per show with: playlist URL (if found) OR video count.

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

def artist_in_title(artist, title):
    """Check if artist name (or key part of it) appears in title."""
    artist_norm = normalize(artist)
    title_norm = normalize(title)
    if artist_norm in title_norm:
        return True
    # Try each word of the artist name that's long enough to be distinctive
    words = [w for w in artist_norm.split() if len(w) > 4]
    return all(w in title_norm for w in words) if words else False

def date_variants(date_str):
    """
    Given YYYY-MM-DD, return list of date strings that might appear
    in a YouTube title or description.
    e.g. 2025-11-21 → ['11/21/25', '11/21/2025', '112125', '11-21-25']
    """
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []
    yy = d.strftime("%y")
    yyyy = d.strftime("%Y")
    mm = d.strftime("%m")
    dd = d.strftime("%d")
    return [
        f"{mm}/{dd}/{yy}",
        f"{mm}/{dd}/{yyyy}",
        f"{d.month}/{d.day}/{yy}",
        f"{d.month}/{d.day}/{yyyy}",
    ]

def venue_fragment(venue):
    """Extract a short venue keyword from the full venue string."""
    parts = venue.split(",")
    name = parts[0].strip().lower()
    name = re.sub(r"^the\s+", "", name)
    words = name.split()[:2]
    return " ".join(words)

def find_playlist(artist, date_str, venue, playlists):
    date_vars = date_variants(date_str)
    vfrag = venue_fragment(venue)
    best = None
    for pl in playlists:
        title = pl["title"]
        title_norm = normalize(title)
        if not artist_in_title(artist, title):
            continue
        if "live" not in title_norm:
            continue
        date_match = any(dv in title for dv in date_vars)
        venue_match = vfrag and vfrag in title_norm
        if date_match or venue_match:
            best = pl
            break
    return best

def find_videos(artist, date_str, videos):
    date_vars = date_variants(date_str)
    matches = []
    for v in videos:
        if not artist_in_title(artist, v["title"]):
            continue
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
        artist   = show["Artist"]
        date_str = show["Show Date"]
        venue    = show["Venue"]
        setlist  = show.get("Setlist.fm URL", "")
        pl_url_existing = show.get("Playlist URL", "")

        playlist = find_playlist(artist, date_str, venue, playlists)
        vids = []
        if not playlist:
            vids = find_videos(artist, date_str, videos)

        if playlist:
            playlist_hits += 1
            yt_result  = playlist["url"]
            match_type = f"Playlist ({playlist['item_count']} videos)"
            yt_title   = playlist["title"]
        elif vids:
            video_hits += 1
            yt_result  = ""
            match_type = f"{len(vids)} video(s) found"
            yt_title   = " | ".join(v["title"] for v in vids[:3])
            if len(vids) > 3:
                yt_title += f" ... (+{len(vids)-3} more)"
        else:
            yt_result  = ""
            match_type = "No match"
            yt_title   = ""

        results.append({
            "Show Date":        date_str,
            "Artist":           artist,
            "Supporting Acts":  show.get("Supporting Acts", ""),
            "Venue":            venue,
            "Setlist.fm URL":   setlist,
            "Playlist URL":     yt_result if yt_result else pl_url_existing,
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