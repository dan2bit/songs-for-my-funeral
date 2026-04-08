#!/usr/bin/env python3
"""
merge_notes_into_history.py
===========================
One-time script to merge notes_memories_draft.tsv into live_shows_history.tsv.

Run from the live-shows/ directory:
    python3 merge_notes_into_history.py

DESIGN
------
- Reads notes_memories_draft.tsv as the canonical source of truth.
- Matches each draft row to a history row by (Show Date, normalized Artist).
- Normalized matching strips trailing/leading whitespace and collapses Unicode
  apostrophes (', ') → straight apostrophe ('), and Unicode en/em dashes to
  ASCII — for comparison purposes only. Writes always use the canonical artist
  name already in the history file.
- OVERWRITES any history note that differs from the draft note (draft is canonical).
- Skips draft rows whose note is blank (nothing to write).
- Reports: updated rows, skipped-identical rows, skipped-blank-draft rows,
  unmatched draft keys, and new rows to insert manually.

SPECIAL CASES (handled automatically)
--------------------------------------
- 2023-05-20 | The Wood Brothers (draft) → 2023-05-20 | Shovels & Rope (history)
  Draft artist key was renamed; note belongs to the history headliner.
- 2024-07-18 | Mike Zito (draft) → 2024-07-18 | Tab Benoit & Anders Osborne  (history)
  Mike Zito was the supporting act; Tab Benoit is the history headliner.
- 2024-09-19 | Marcus King (draft, already correct after prior fix)
- 2023-09-26 | Wu-Tang Clan (draft, NEW — not currently in history as Wu-Tang Clan)
  The Nas row at this date already has a note in history; Wu-Tang Clan is a new
  entry. The script will report this as unmatched and you must insert it manually.

POST-MERGE CLEANUP
------------------
1. Delete this script (one-time use).
2. Deprecate notes_memories_draft.tsv — replace with a worklist of shows that
   still have a blank Notes / Memories column in history.
3. Update Task 3 in TASKS.md to mark complete.
"""

import csv
import os
import re
import sys
import unicodedata

DRAFT_FILE   = "notes_memories_draft.tsv"
HISTORY_FILE = "live_shows_history.tsv"
NOTES_COL    = "Notes / Memories"
DATE_COL     = "Show Date"
ARTIST_COL   = "Artist"

# Explicit artist key remaps: (draft_date, draft_artist_norm) -> history_artist_norm
# Used when the draft intentionally uses a different artist name than history.
ARTIST_REMAPS = {
    ("2023-05-20", "the wood brothers"):        "shovels  rope",       # & normalizes to space
    ("2024-07-18", "mike zito"):                "tab benoit  anders osborne",
}


def normalize(s):
    """Normalize an artist name for fuzzy matching only (never for output)."""
    s = s.strip()
    # Normalize Unicode apostrophes and quotes to straight apostrophe
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u0060", "'")
    # Normalize en/em dash to hyphen
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    # Normalize ampersand to space (& → space, then collapse)
    s = s.replace("&", " ")
    # Lowercase, collapse whitespace
    s = re.sub(r"\s+", " ", s.lower()).strip()
    return s


def load_draft(path):
    """Returns list of (date, artist_raw, note_raw) from draft TSV."""
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            date   = row.get(DATE_COL, "").strip()
            artist = row.get(ARTIST_COL, "").strip()
            note   = row.get(NOTES_COL, "").strip()
            if date:
                rows.append((date, artist, note))
    return rows


def load_history(path):
    """Returns (fieldnames, rows) from history TSV."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def build_history_index(rows):
    """Returns dict: (date, norm_artist) -> row_index in rows list."""
    index = {}
    for i, row in enumerate(rows):
        date   = row.get(DATE_COL, "").strip()
        artist = row.get(ARTIST_COL, "").strip()
        key    = (date, normalize(artist))
        index[key] = i
    return index


def main():
    for path in (DRAFT_FILE, HISTORY_FILE):
        if not os.path.exists(path):
            sys.exit(f"ERROR: {path} not found. Run from live-shows/ directory.")

    draft_rows = load_draft(DRAFT_FILE)
    fieldnames, hist_rows = load_history(HISTORY_FILE)

    if NOTES_COL not in fieldnames:
        sys.exit(f"ERROR: '{NOTES_COL}' column not found in {HISTORY_FILE}")

    hist_index = build_history_index(hist_rows)

    updated          = 0
    skipped_identical = 0
    skipped_blank    = 0
    unmatched        = []

    for draft_date, draft_artist, draft_note in draft_rows:
        # Skip 2026 rows — notes already exist in live_shows_2026.tsv
        if draft_date.startswith("2026"):
            continue

        # Skip blank draft notes — nothing to write
        if not draft_note:
            skipped_blank += 1
            print(f"  SKIP (blank draft note): {draft_date} | {draft_artist}")
            continue

        norm_key = (draft_date, normalize(draft_artist))

        # Apply explicit artist remap if needed
        lookup_key = ARTIST_REMAPS.get(norm_key, norm_key[1])
        lookup     = (draft_date, lookup_key) if lookup_key != norm_key[1] else norm_key

        row_idx = hist_index.get(lookup)
        if row_idx is None:
            # Also try direct norm_key in case remap not needed
            row_idx = hist_index.get(norm_key)

        if row_idx is None:
            unmatched.append((draft_date, draft_artist, draft_note))
            print(f"  NO MATCH: {draft_date} | {draft_artist}")
            continue

        hist_note = (hist_rows[row_idx].get(NOTES_COL) or "").strip()
        hist_artist = hist_rows[row_idx].get(ARTIST_COL, "").strip()

        if draft_note == hist_note:
            skipped_identical += 1
            # Silent for identical — would be too noisy
            continue

        # Draft differs from history — write draft (draft is canonical)
        hist_rows[row_idx][NOTES_COL] = draft_note
        updated += 1
        if hist_note:
            print(f"  OVERWRITE: {draft_date} | {hist_artist}")
            print(f"    was: {hist_note[:80]}{'...' if len(hist_note) > 80 else ''}")
            print(f"    now: {draft_note[:80]}{'...' if len(draft_note) > 80 else ''}")
        else:
            print(f"  + {draft_date} | {hist_artist}")

    # Write back
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(hist_rows)

    print(f"\n{'='*70}")
    print(f"Updated (wrote/overwrote):  {updated}")
    print(f"Skipped (identical):        {skipped_identical}")
    print(f"Skipped (blank draft note): {skipped_blank}")
    print(f"Unmatched draft keys:       {len(unmatched)}")

    if unmatched:
        print(f"\nUnmatched rows — requires manual insertion into history:")
        for d, a, n in unmatched:
            print(f"\n  {d} | {a}")
            print(f"  Note: {n}")

    print(f"\nDone. Review with: git diff {HISTORY_FILE}")


if __name__ == "__main__":
    main()
