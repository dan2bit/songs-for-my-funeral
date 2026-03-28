# songs-for-my-funeral — Archive Task List

Collaborative task list for the live show archive project. Update status as tasks complete.

---

## ✅ Completed (this session)

- Matched 9 playlist URLs from `youtube_playlists.tsv` into `live_shows_history.tsv`
- Populated WORKLIST in `youtube_create_playlists.py` with 22 backfill shows
- Fixed `live_shows_2026.tsv`: dropped duplicate `Notes` column, fixed column shift on upcoming rows
- Added 27 YouTube channel handles to `artists.tsv` from `youtube_videos.tsv` cross-ref
- Fixed quota burn bug in `youtube_create_playlists.py` (`--new-show` now checks `youtube_videos.tsv` before calling uploads API)
- Added `youtube_audit_blanks.py` for loose-match scan of no-video blank shows
- Committed `live_shows_history.tsv` playlist URL updates (Daniel Donato, DuPont Brass, LL Cool J, Buddy Guy 2025, + 9 from playlist cross-ref)
- Merged PR #7 (`youtube_fetch.py --since`)

---

## 🔧 Ready to Run (quota reset needed)

### 1. Create ZZ Ward 2026 playlist

The dry run output was confirmed correct. Blocked only by YouTube API quota reset (resets daily at midnight Pacific).

```bash
cd live-shows
source .venv/bin/activate
python3 youtube_create_playlists.py --new-show 2026-03-21 --update-history
```

After completion: `live_shows_2026.tsv` will be updated with the playlist URL automatically.

---

### 2. Create 22 WORKLIST backfill playlists

Videos are already in `youtube_videos.tsv` — no uploads API calls needed.
Run dry run first to verify video matching, then run for real.

```bash
cd live-shows
source .venv/bin/activate

# Preview first
python3 youtube_create_playlists.py --worklist --dry-run

# Then create
python3 youtube_create_playlists.py --worklist --update-history
```

After completion: `live_shows_history.tsv` will be updated with all 22 playlist URLs automatically.
The WORKLIST in `youtube_create_playlists.py` should then be cleared and entries moved to the "Completed" comment block.

**WORKLIST shows (22):**
| Date | Artist |
|------|--------|
| 2021-07-11 | Oliver Wood |
| 2022-09-17 | Willie Nelson |
| 2022-11-17 | Tab Benoit |
| 2022-12-14 | Ana Popović |
| 2022-12-31 | George Clinton & Parliament-Funkadelic |
| 2023-06-28 | Ally Venable Band |
| 2023-09-02 | Oh He Dead |
| 2023-09-09 | Kingsley Flood |
| 2023-09-13 | Sonny Landreth |
| 2023-09-26 | Nas |
| 2023-12-10 | Allison Russell |
| 2024-12-07 | New York's Finest |
| 2024-12-17 | Tab Benoit |
| 2025-01-24 | New York's Finest |
| 2025-01-31 | Vanessa Collier |
| 2025-02-07 | Yasmin Williams |
| 2025-07-11 | North Mississippi Allstars |
| 2025-07-13 | J. P. Soars |
| 2025-07-16 | Barenaked Ladies |
| 2025-08-03 | Eric Johanson |
| 2025-08-28 | Robert Randolph |
| 2025-09-23 | Bywater Call |
| 2025-12-20 | Maggie Rose |

---

## 🔍 Research / Eyeball Tasks

### 3. Audit 25 no-video blank shows

25 shows have no playlist URL and no matching videos in `youtube_videos.tsv` using exact date matching. Use the new audit script to scan with a loose +30-day window and fuzzy artist-name title matching.

```bash
cd live-shows
source .venv/bin/activate

# Print to terminal
python3 youtube_audit_blanks.py

# Or save to TSV for easier review
python3 youtube_audit_blanks.py --output audit_blanks.tsv
```

**The 25 shows:**
| Date | Artist |
|------|--------|
| 2021-09-23 | The Avett Brothers |
| 2021-09-24 | Kingsley Flood |
| 2021-10-22 | Rival Sons |
| 2021-11-18 | Christone "Kingfish" Ingram |
| 2022-01-21 | Keb' Mo' |
| 2022-01-28 | Lucky Chops |
| 2022-02-18 | Tedeschi Trucks Band |
| 2022-02-27 | Lyle Lovett |
| 2022-07-16 | Daniel Donato |
| 2022-08-16 | Roger Waters |
| 2022-10-22 | ZZ Top |
| 2022-10-24 | Violent Femmes |
| 2023-06-18 | Trombone Shorty & Orleans Avenue |
| 2024-06-01 | Bonnie Raitt |
| 2024-06-16 | Shaw Davis & The Black Ties |
| 2024-10-14 | David Moore |
| 2024-10-17 | Ana Popovic |
| 2024-11-17 | Lindsay Lou |
| 2024-12-06 | Oh He Dead |
| 2025-06-07 | Selwyn Birchwood |
| 2025-06-15 | Sue Foley |
| 2025-07-24 | Trombone Shorty & Orleans Avenue |
| 2025-08-10 | AJR |
| 2025-10-17 | New York's Finest |
| 2025-12-04 | The Wood Brothers |

After reviewing output: for any confirmed matches, manually add the single video URL or playlist URL to `live_shows_history.tsv` in the `Playlist URL` column.

---

### 4. Fill blank playlist descriptions

Playlists created by the script have no descriptions. This one-time run fills them with the setlist.fm URL using the default "Select tracks from {setlist_url}" template. Requires OAuth (YouTube write scope).

```bash
cd live-shows
source .venv/bin/activate

# Preview first
python3 youtube_create_playlists.py --fix-descriptions --dry-run

# Then apply
python3 youtube_create_playlists.py --fix-descriptions
```

Note: only fills descriptions for playlists that (a) have a blank description and (b) have a matching row in history/2026 with a setlist.fm URL. Playlists without a setlist URL are skipped and logged.

---

### 5. Find remaining blank artist YouTube handles

~67 artists in `artists.tsv` still have no `YouTube Channel` value. The handles sourced from `youtube_videos.tsv` have been applied; the remainder need manual lookup.

**Next steps:**
- Run `youtube_subscriptions_to_artists.py` to pull any handles from your YouTube subscriptions that might map to artists in `artists.tsv`
- Manually look up remaining artists on YouTube and fill in `artists.tsv`

```bash
cd live-shows
source .venv/bin/activate
python3 youtube_subscriptions_to_artists.py
```

---

## 📋 Manual / Pending Approval

### 6. Merge `notes_memories_draft.tsv` into history

A staging file of show notes/memories exists at `live-shows/notes_memories_draft.tsv`. These have not been merged into `live_shows_history.tsv` pending explicit approval.

**Next steps:** Review `notes_memories_draft.tsv`, then give the go-ahead to merge into history in a dedicated session (context window concern — the history file is large).

---

## 🔄 Ongoing / Maintenance

### 7. `live_shows_history.tsv` re-ingest after WORKLIST runs

After task #2 creates the 22 WORKLIST playlists, run `youtube_fetch.py` to re-ingest the channel and populate the new playlist URLs into `youtube_videos.tsv` video descriptions.

```bash
cd live-shows
source .venv/bin/activate
python3 youtube_fetch.py --since 2021-07-01
```

Then run `youtube_correlate.py --merge` to push any new URL correlations back into the history files.

---

### 8. `artists.tsv` — `Most Recent Seen` column drift

The `Most Recent Seen` column is manually maintained. As 2026 attended shows accumulate, it will drift out of date. Consider writing a sync script that derives `Times Seen`, `First Seen`, and `Most Recent Seen` directly from `live_shows_history.tsv` + `live_shows_2026.tsv` rather than maintaining them by hand.

No script exists yet. Would need to be written.

---

### 9. Venues TSV parking update

A parking cost update to `venues.tsv` was in-progress at the end of a previous session. Completion status unclear — worth checking the file.

**Next step:** Open `live-shows/venues.tsv` and verify parking entries are current.

---

## ⚠️ Known Issues

### 10. `Christone "Kingfish" Ingram` quoting inconsistency

The artist name uses inconsistent double-quote escaping across TSV files:
- Sometimes `"Christone ""Kingfish"" Ingram"` (correct TSV escaping)
- Sometimes `Christone "Kingfish" Ingram` (unescaped, breaks TSV parsing)

This can cause artist lookup mismatches in scripts. Worth a find-and-replace cleanup pass across all TSV files.

---

### 4 Flagged shows — held for manual review

These shows have videos in `youtube_videos.tsv` but were not added to the WORKLIST due to ambiguous video attribution. Decide what to do with each:

| Date | Artist | Issue |
|------|--------|-------|
| 2022-04-26 | Daniel Donato | Only 1 video — single URL already set in Playlist URL |
| 2023-09-09 | DuPont Brass | Only 1 DuPont video, mixed in with Kingsley Flood show — single URL already set |
| 2023-10-15 | LL Cool J | 6 of 7 videos are Queen Latifah — playlist URL already set |
| 2025-06-21 | Buddy Guy | Playlist created manually; 2 Judith Hill videos from a different show were excluded |
