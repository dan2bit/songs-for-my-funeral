#!/usr/bin/env python3
"""
youtube_audit_blanks.py — Audit show history rows with no playlist URL and no
video match, looking for candidate videos in youtube_videos.tsv using a loose
date window + fuzzy artist-name title match.

No API calls. No writes. Read-only eyeball-test tool.

USAGE:
    # Scan all blank-playlist shows that have no match in youtube_videos.tsv
    python3 youtube_audit_blanks.py

    # Scan a specific show date
    python3 youtube_audit_blanks.py --date 2022-08-16

    # Widen or narrow the upload window (default: +30 days after show)
    python3 youtube_audit_blanks.py --window 60

    # Write results to a TSV file instead of stdout
    python3 youtube_audit_blanks.py --output audit_results.tsv

INPUT FILES (same directory):
    live_shows_history.tsv  — authoritative show attendance record
    youtube_videos.tsv      — ingested channel video metadata

OUTPUT COLUMNS (TSV):
    Show Date, Artist, Days After Show, Video Published, Video Title, Video URL

The output is intentionally verbose so you can eyeball each candidate and
decide whether it's a real match. No changes are made to any file.

MATCHING LOGIC:
    Date window:  video published date must be in range (show_date, show_date + window]
                  (strictly future — same-day uploads are excluded as per upload practice)
    Title match:  at least one "significant" word from the artist name appears in the
                  video title (case-insensitive). Noise words are filtered out.
                  "Significant" means len > 3 and not in the noise set.
                  If the artist name yields NO significant words (e.g. "Nas"), ALL
                  videos in the date window are returned as candidates.
"""

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timedelta

# ── constants ─────────────────────────────────────────────────────────────────
HISTORY_TSV   = "live_shows_history.tsv"
VIDEOS_TSV    = "youtube_videos.tsv"
DEFAULT_WINDOW = 30  # days after show date

# Words that appear too frequently in video titles to be useful discriminators
NOISE_WORDS = {
    "band", "the", "and", "live", "feat", "featuring", "with", "ingram",
    "blues", "music", "show", "bootleg", "official", "video", "full",
}

# ── helpers ───────────────────────────────────────────────────────────────────
def load_tsv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def normalize(s):
    return re.sub(r"[^\w\s]", "", s.lower()).strip()


def significant_words(artist):
    """Return non-noise words from artist name that are long enough to discriminate."""
    words = normalize(artist).split()
    return [w for w in words if len(w) > 3 and w not in NOISE_WORDS]


def title_matches_artist(video_title, artist):
    """True if any significant artist word appears in the normalized video title."""
    vt = normalize(video_title)
    sig = significant_words(artist)
    if not sig:
        # Artist name has no significant words (e.g. "Nas") — match everything
        return True
    return any(w in vt for w in sig)


def parse_date(s):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


# ── core scan ─────────────────────────────────────────────────────────────────
def scan(target_dates=None, window_days=DEFAULT_WINDOW):
    """
    Returns list of result dicts, one per candidate video found.
    target_dates: set of YYYY-MM-DD strings to restrict scan, or None for all.
    """
    history = load_tsv(HISTORY_TSV)
    videos  = load_tsv(VIDEOS_TSV)

    # Build index of videos by published date for fast lookup
    # videos_by_date: date -> list of video dicts
    videos_by_date = {}
    for v in videos:
        pub = parse_date(v.get("published", ""))
        if pub:
            videos_by_date.setdefault(pub, []).append(v)

    # Identify blank-playlist rows to scan
    blanks = [
        r for r in history
        if not (r.get("Playlist URL") or "").strip()
    ]
    if target_dates:
        blanks = [r for r in blanks if r.get("Show Date") in target_dates]

    results = []
    for row in blanks:
        show_date = parse_date(row.get("Show Date", ""))
        artist    = row.get("Artist", "").strip()
        if not show_date or not artist:
            continue

        # Collect all videos published in (show_date, show_date + window]
        candidates = []
        for offset in range(1, window_days + 1):
            check_date = show_date + timedelta(days=offset)
            for v in videos_by_date.get(check_date, []):
                if title_matches_artist(v.get("title", ""), artist):
                    candidates.append((offset, check_date, v))

        for days_after, pub_date, v in candidates:
            results.append({
                "Show Date":      row["Show Date"],
                "Artist":         artist,
                "Days After Show": days_after,
                "Video Published": str(pub_date),
                "Video Title":    v.get("title", ""),
                "Video URL":      v.get("url", ""),
            })

    return results


# ── output ────────────────────────────────────────────────────────────────────
FIELDNAMES = ["Show Date", "Artist", "Days After Show", "Video Published",
              "Video Title", "Video URL"]


def write_tsv(results, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        writer.writerows(results)
    print(f"Written {len(results)} rows to {path}")


def print_results(results):
    if not results:
        print("No candidates found.")
        return

    current_show = None
    for r in results:
        show_key = (r["Show Date"], r["Artist"])
        if show_key != current_show:
            current_show = show_key
            print(f"\n{'─'*70}")
            print(f"  {r['Show Date']}  {r['Artist']}")
        print(f"    +{r['Days After Show']:>3}d  [{r['Video Published']}]  {r['Video Title'][:60]}")
        print(f"           {r['Video URL']}")

    # Summary
    shows = {(r["Show Date"], r["Artist"]) for r in results}
    print(f"\n{'='*70}")
    print(f"  {len(shows)} show(s) with candidates  |  {len(results)} total video(s)")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Audit blank-playlist shows for candidate videos in youtube_videos.tsv"
    )
    parser.add_argument(
        "--date", nargs="+", metavar="YYYY-MM-DD",
        help="Restrict scan to specific show date(s)"
    )
    parser.add_argument(
        "--window", type=int, default=DEFAULT_WINDOW,
        help=f"Days after show date to scan (default: {DEFAULT_WINDOW})"
    )
    parser.add_argument(
        "--output", metavar="FILE",
        help="Write results to this TSV file instead of stdout"
    )
    parser.add_argument(
        "--all-blanks", action="store_true",
        help="Scan all blank-playlist rows (default: only rows with Match Type 'No match')"
    )
    args = parser.parse_args()

    # Change to script directory so relative TSV paths resolve correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    target_dates = set(args.date) if args.date else None

    print(f"Scanning with +{args.window}-day upload window...")
    if target_dates:
        print(f"  Restricted to: {sorted(target_dates)}")

    results = scan(target_dates=target_dates, window_days=args.window)

    if args.output:
        write_tsv(results, args.output)
    else:
        print_results(results)


if __name__ == "__main__":
    main()
