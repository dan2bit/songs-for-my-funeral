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
    python3 youtube_correlate.py [--merge] [--sync-artists]

    --merge         After writing correlation TSVs, also patch any newly found playlist URLs
                    back into live_shows_history.tsv and live_shows_2026.tsv.
                    Only fills blank Playlist URL cells — never overwrites an existing URL.

    --sync-artists  After processing attended shows, update artists.tsv:
                      - If an artist is not yet in artists.tsv, add a new row.
                      - If already present, increment Times Seen and update Most Recent Seen
                        if the show date is newer.
                    Can be used with or without --merge. Always does a dry-run preview
                    first and asks for confirmation before writing.

    --dry-run       Preview all changes without writing anything (applies to both
                    --merge and --sync-artists).

Input files (must be in same directory):
    youtube_videos.tsv
    youtube_playlists.tsv
    live_shows_history.tsv         — 2021-2025 history (Show Date, Artist, Supporting Acts, Venue, ...)
    live_shows_2026.tsv            — 2026 attended shows (Show Date, Artist, Venue Name, ...)

Output:
    history_youtube_correlation.tsv    — 2021-2025
    shows_2026_youtube_correlation.tsv — 2026 attended shows only
    (with --merge) live_shows_history.tsv and live_shows_2026.tsv are patched in-place
    (with --sync-artists) artists.tsv is updated in-place
"""

import argparse
import csv
import os
import re
from datetime import datetime


# ── Artist name normalization ─────────────────────────────────────────────────
# Maps incoming artist name variants (e.g. from Spotify/YouTube API responses)
# to the canonical form used in artists.tsv and live_shows_history.tsv.
# Apply normalize_artist_name() to any artist name read from an external source
# before comparing or writing it to a TSV file.

ARTIST_NAME_ALIASES = {
    # Double-quote variants → canonical single-tick form
    'Christone "Kingfish" Ingram':     "Christone 'Kingfish' Ingram",
    'Christone ""Kingfish"" Ingram':   "Christone 'Kingfish' Ingram",
    # Shorthand forms that appear in autograph book index
    "Christone Ingram":                "Christone 'Kingfish' Ingram",
    "Kingfish Ingram":                 "Christone 'Kingfish' Ingram",
    "Kingfish":                        "Christone 'Kingfish' Ingram",
}


def normalize_artist_name(name: str) -> str:
    """Return the canonical artist name, resolving known aliases."""
    return ARTIST_NAME_ALIASES.get(name, name)


# ── TSV helpers ───────────────────────────────────────────────────────────────

def load_tsv(filename):
    with open(filename, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def write_tsv(rows, fieldnames, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _cell(row, key):
    """Safely read a TSV cell — returns empty string for missing or None values."""
    return (row.get(key) or "").strip()


# ── Matching helpers ──────────────────────────────────────────────────────────

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
        desc = v.get("description", "") or ""
        if any(dv in desc for dv in date_vars):
            matches.append(v)
    return matches


# ── Show normalisation ────────────────────────────────────────────────────────

def normalize_shows(shows, artist_col, venue_col, date_col):
    out = []
    for s in shows:
        out.append({
            "Show Date":        s.get(date_col, ""),
            "Artist":           normalize_artist_name(s.get(artist_col, "")),
            "Supporting Acts":  s.get("Supporting Acts", s.get("Supporting Artist", "")),
            "Venue":            s.get(venue_col, ""),
            "Setlist.fm URL":   s.get("Setlist.fm URL", ""),
            "Playlist URL":     s.get("Playlist URL", ""),
            "Notes / Memories": s.get("Notes / Memories", s.get("Notes", "")),
        })
    return out


# ── Core correlate ────────────────────────────────────────────────────────────

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


# ── Output helpers ────────────────────────────────────────────────────────────

def write_results(results, filename):
    fieldnames = [
        "Show Date", "Artist", "Supporting Acts", "Venue",
        "Setlist.fm URL", "Playlist URL", "Match Type", "YT Title", "Notes / Memories"
    ]
    write_tsv(results, fieldnames, filename)
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


# ── Merge back into source files ──────────────────────────────────────────────

def merge_into_history(corr_results, source_file):
    """
    Patch playlist URLs found by the correlator back into a source show file.

    Rules:
      - Only writes a URL when the correlation result has a playlist URL (not video-only).
      - Never overwrites a cell that already has a URL.
      - Matches rows by (Show Date, Artist) — case-sensitive, same as the source file.
      - Writes the file back in-place, preserving all columns and their order.

    Returns the number of rows updated.
    """
    if not os.path.exists(source_file):
        return 0

    # Build lookup: (date, artist) → playlist_url from correlation results
    # Only include rows where correlation actually found a playlist
    corr_map = {}
    for r in corr_results:
        url = _cell(r, "Playlist URL")
        if url:
            corr_map[(_cell(r, "Show Date"), _cell(r, "Artist"))] = url

    if not corr_map:
        return 0

    # Read source file, preserving all columns
    with open(source_file, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    # Ensure Playlist URL column exists
    if "Playlist URL" not in fieldnames:
        print(f"  WARNING: 'Playlist URL' column not found in {source_file} — skipping merge")
        return 0

    updated = 0
    for row in rows:
        date         = _cell(row, "Show Date")
        artist       = normalize_artist_name(_cell(row, "Artist"))
        existing_url = _cell(row, "Playlist URL")
        new_url      = corr_map.get((date, artist), "")

        if new_url and not existing_url:
            row["Playlist URL"] = new_url
            updated += 1
            print(f"    + {date} | {artist}")
            print(f"        {new_url}")

    if updated:
        write_tsv(rows, fieldnames, source_file)
        print(f"  Wrote {updated} URL(s) → {source_file}")
    else:
        print(f"  No new URLs to write → {source_file}")

    return updated


# ── artists.tsv sync ──────────────────────────────────────────────────────────

ARTISTS_TSV = "artists.tsv"
ARTISTS_FIELDNAMES = [
    "Artist", "Times Seen", "First Seen", "Most Recent Seen",
    "YouTube Channel", "Spotify URL", "Photo", "Book Autograph",
    "Hat Autograph", "VIP Ticket",
]


def sync_artists(all_attended_shows, dry_run=False):
    """
    Update artists.tsv from the full set of attended shows across all source files.

    For each attended show's headliner:
      - If not in artists.tsv: add a new row with Times Seen=1, First Seen and
        Most Recent Seen both set to the show date. All other columns left blank.
      - If already present: increment Times Seen by the number of newly seen shows,
        update Most Recent Seen if a newer show date exists, update First Seen if
        an older show date exists (handles shows added out of order).

    Computes the full correct state by scanning ALL attended shows, not just new
    ones — so it is safe to run repeatedly and will converge to the correct counts.

    Prints a summary of all changes. With dry_run=True, prints but does not write.
    Returns the number of rows added or updated.
    """
    if not os.path.exists(ARTISTS_TSV):
        print(f"  WARNING: {ARTISTS_TSV} not found — skipping artist sync")
        return 0

    # Load current artists.tsv
    with open(ARTISTS_TSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = list(reader.fieldnames or ARTISTS_FIELDNAMES)
        artists = list(reader)

    # Build index: artist name → row
    artist_index = {normalize_artist_name(r["Artist"]): r for r in artists}

    # Aggregate all attended shows: artist → sorted list of dates
    from collections import defaultdict
    show_dates_by_artist = defaultdict(set)
    for show in all_attended_shows:
        artist = normalize_artist_name(show["Artist"])
        date   = show["Show Date"]
        if artist and date:
            show_dates_by_artist[artist].add(date)

    new_rows = []
    updated_rows = []

    for artist, dates in sorted(show_dates_by_artist.items()):
        dates = sorted(dates)
        first_seen  = dates[0]
        most_recent = dates[-1]
        times_seen  = len(dates)

        if artist not in artist_index:
            # New artist — add row
            new_row = {fn: "" for fn in fieldnames}
            new_row["Artist"]          = artist
            new_row["Times Seen"]      = str(times_seen)
            new_row["First Seen"]      = first_seen
            new_row["Most Recent Seen"] = most_recent
            new_rows.append(new_row)
            print(f"  ADD  {artist}  (Times Seen={times_seen}, First={first_seen}, Recent={most_recent})")
        else:
            row = artist_index[artist]
            current_seen      = int(row.get("Times Seen", "0") or "0")
            current_first     = row.get("First Seen", "").strip()
            current_recent    = row.get("Most Recent Seen", "").strip()

            # Compute what the values should be
            new_first  = min(filter(None, [first_seen, current_first])) if current_first else first_seen
            new_recent = max(filter(None, [most_recent, current_recent])) if current_recent else most_recent
            new_seen   = times_seen  # authoritative count from source files

            changes = []
            if new_seen != current_seen:
                changes.append(f"Times Seen {current_seen}→{new_seen}")
            if new_first != current_first:
                changes.append(f"First Seen {current_first!r}→{new_first!r}")
            if new_recent != current_recent:
                changes.append(f"Most Recent Seen {current_recent!r}→{new_recent!r}")

            if changes:
                row["Times Seen"]       = str(new_seen)
                row["First Seen"]       = new_first
                row["Most Recent Seen"] = new_recent
                updated_rows.append(artist)
                print(f"  UPD  {artist}  ({', '.join(changes)})")

    total_changes = len(new_rows) + len(updated_rows)
    if total_changes == 0:
        print("  artists.tsv is already up to date — no changes needed.")
        return 0

    print(f"\n  {len(new_rows)} new artist(s), {len(updated_rows)} updated.")

    if dry_run:
        print("  [dry-run] No changes written.")
        return total_changes

    # Append new rows and write back
    artists.extend(new_rows)
    # Re-sort by artist name for tidy output
    artists.sort(key=lambda r: r.get("Artist", "").lower())
    write_tsv(artists, fieldnames, ARTISTS_TSV)
    print(f"  Written → {ARTISTS_TSV}")
    return total_changes


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help=(
            "After writing correlation TSVs, patch newly found playlist URLs back into "
            "live_shows_history.tsv and live_shows_2026.tsv. "
            "Only fills blank Playlist URL cells — never overwrites an existing URL."
        ),
    )
    parser.add_argument(
        "--sync-artists",
        action="store_true",
        help=(
            "Update artists.tsv from attended shows: add new artist rows and update "
            "Times Seen / First Seen / Most Recent Seen for existing ones. "
            "Computes correct counts from all source files, safe to re-run."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all changes without writing anything.",
    )
    args = parser.parse_args()

    videos    = load_tsv("youtube_videos.tsv")
    playlists = load_tsv("youtube_playlists.tsv")
    print(f"Loaded {len(videos)} videos, {len(playlists)} playlists")

    all_results_history  = []
    all_results_2026     = []
    all_attended_shows   = []   # collected for --sync-artists

    # ── History file ──────────────────────────────────────────────────────────
    if os.path.exists("live_shows_history.tsv"):
        history_raw = load_tsv("live_shows_history.tsv")
        history = normalize_shows(history_raw, "Artist", "Venue", "Show Date")
        print(f"Loaded {len(history)} history shows (2021-2025)")
        results_h, ph, vh = correlate(history, videos, playlists)
        write_results(results_h, "history_youtube_correlation.tsv")
        print_summary("2021-2025 history", results_h, ph, vh)
        all_results_history = results_h
        all_attended_shows.extend(history)
    else:
        print("live_shows_history.tsv not found — skipping")

    # ── 2026 file ─────────────────────────────────────────────────────────────
    if os.path.exists("live_shows_2026.tsv"):
        shows_2026_raw = load_tsv("live_shows_2026.tsv")
        attended = [s for s in shows_2026_raw if s.get("Status", "") == "attended"]
        shows_2026 = normalize_shows(attended, "Artist", "Venue Name", "Show Date")
        print(f"\nLoaded {len(shows_2026)} attended 2026 shows")
        results_26, ph, vh = correlate(shows_2026, videos, playlists)
        write_results(results_26, "shows_2026_youtube_correlation.tsv")
        print_summary("2026 attended shows", results_26, ph, vh)
        all_results_2026 = results_26
        all_attended_shows.extend(shows_2026)
    else:
        print("live_shows_2026.tsv not found — skipping")

    # ── Optional merge ────────────────────────────────────────────────────────
    if args.merge:
        print("\n── Merging playlist URLs into source files ──────────────────────────────────")

        if all_results_history:
            print("\nlive_shows_history.tsv:")
            if not args.dry_run:
                merge_into_history(all_results_history, "live_shows_history.tsv")
            else:
                print("  [dry-run] skipping write")

        if all_results_2026:
            print("\nlive_shows_2026.tsv:")
            if not args.dry_run:
                merge_into_history(all_results_2026, "live_shows_2026.tsv")
            else:
                print("  [dry-run] skipping write")

        if not args.dry_run:
            print("\nMerge complete. Review changes with: git diff live_shows_history.tsv live_shows_2026.tsv")

    # ── Optional artists sync ─────────────────────────────────────────────────
    if args.sync_artists:
        print("\n── Syncing artists.tsv ──────────────────────────────────────────────────────")
        sync_artists(all_attended_shows, dry_run=args.dry_run)
        if not args.dry_run:
            print("Review changes with: git diff artists.tsv")


if __name__ == "__main__":
    main()
