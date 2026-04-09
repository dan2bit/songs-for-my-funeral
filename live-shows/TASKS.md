# songs-for-my-funeral — Archive Task List

Collaborative task list for the live show archive project. Update status as tasks complete.

---

## 🎟 Standing Checks — Every Inbox Session

### A. Potential shows monitoring

At the start of every inbox processing session, open `live-shows/live_shows_potential.tsv`
and apply the following checks to any row that has a value in the `Watching For` column:

**If `Watching For` = `low ticket / sold out`** (applies to any `Buy` row):
- Check the ticket URL in `Purchase URL` for current availability
- Also watch for venue/artist emails arriving at redhat.bootlegs@gmail.com mentioning
  the show
- Alert Dan immediately if low ticket warning or sold-out status is detected

**If `Watching For` contains `closer` (applies to `Pass` or `Buy` rows):**
- Scan new emails and newsletters in this session for announcements of a show by
  the same artist at a DC/MD/VA venue, or any venue closer/more convenient than the
  one in the file
- If a closer show is found, surface it as a buy recommendation and note the
  trade-off vs. the existing entry

Current rows with `Watching For` values (update this list as rows are added/resolved):

| Artist | Decision | Watching For | Ticket URL |
|--------|----------|--------------|------------|
| Black Pistol Fire | Buy (paper @ Glen Hansard) | low ticket / sold out | https://www.ticketmaster.com/black-pistol-fire-tickets/artist/1657222 |
| Lucinda Williams | Buy (paper @ Glen Hansard) | low ticket / sold out | https://www.ticketmaster.com/lucinda-williams-and-her-band-washington-district-of-columbia-05-25-2026/event/1500646CCE06CBF2 |
| Taj Mahal | Buy (paper @ Lyle Lovett) | low ticket / sold out | https://www.ticketmaster.com/event/15006470A6EE71A1?brand=birchmere |
| Carolyn Wonderland | Buy | closer DC/MD show | https://www.eventbrite.com/e/carolyn-wonderland-tickets-1983173922588 |
| Christone 'Kingfish' Ingram | Pass | closer headliner show | https://www.ticketmaster.com/christone-kingfish-ingram-harrisburg-pennsylvania-05-21-2026/event/02006453C19ACCCD |
| JD Simo & Luther Dickinson | Pass | closer show | https://www.eventbrite.com/e/bluesamericana-with-jd-simo-luther-dickinson-tickets-1970731399667 |

### B. Potential shows list

See `live-shows/live_shows_potential.tsv` for the full list of uncommitted shows with
ticket links, pricing, and notes. The `Watching For` column is the authoritative source
for what needs monitoring — the table above is kept in sync with it.

**Schema:** Artist | Support | Date | Decision | Watching For | Venue | Venue City | Tier |
Ticket Service | Purchase URL | Event URL | Face Price | Fees Notes | Availability Notes |
Prev Show (2026) | Next Show (2026) | Notes

**Decision values:** `Buy`, `Buy (paper @ [show])`, `Pass`, blank (undecided)
**Watching For values:** `low ticket / sold out`, `closer [description]`, or blank

---

## 🔍 Research / Eyeball Tasks (anytime — no quota cost)

### 1. Upload found videos to YouTube for 11 no-playlist shows — 📅 manual

These shows have no playlist and no confirmed reason for absence. Videos may exist in Google Photos or elsewhere — upload to the channel, then run `youtube_fetch.py --force --since <date>` and `youtube_correlate.py --merge` to pick them up.

**Shows to check and upload (11):**

| Date | Artist |
|------|--------|
| 2021-10-22 | Rival Sons |
| 2021-11-18 | Christone 'Kingfish' Ingram |
| 2022-01-21 | Keb' Mo' |
| 2022-02-18 | Tedeschi Trucks Band |
| 2022-02-27 | Lyle Lovett |
| 2022-07-16 | Daniel Donato |
| 2022-08-16 | Roger Waters |
| 2022-10-24 | Violent Femmes |
| 2024-12-05 | Oh He Dead |
| 2025-07-24 | Trombone Shorty & Orleans Avenue |
| 2025-10-17 | New York's Finest |

After uploading for a given show:
```bash
python3 youtube_fetch.py --force --since <show-date>
python3 youtube_correlate.py --merge
python3 youtube_create_playlists.py --worklist --update-history  # after adding to WORKLIST
```

---

## 🔄 Ongoing / Maintenance

### 2. Design and implement rolling migration + archive architecture

⚠️ **Must be designed before the first 2027 ticket purchase.**

The goal is to reframe `live_shows_2026.tsv` as a **rolling "upcoming + recently attended" window**. Attended rows migrate out on a quarterly-ish cadence once settled — playlist URL populated, notes written. The current file always stays lean.

This task has three distinct architectural problems to solve together:

**Problem 1 — Spending data doesn't belong in the history file**

Spending columns (Food & Bev, Parking, Merch, Artist Interaction) are present in `live_shows_2026.tsv` but not in `live_shows_history.tsv`. The data is worth preserving for budgeting across quarters and years, but it doesn't belong in the attendance record. The right answer is a separate `spending.tsv` (keyed by Show Date + Artist) that can be queried independently. Migration needs to extract spending into this file rather than either dropping it or bloating history.

**Update:** `spending.tsv` has been created and seeded with 2026 Q1 data. Routine 2 now appends to it after every attended show. At rollover, spending columns can simply be dropped from the archived year file — `spending.tsv` is the sole authority.

**Problem 2 — `live_shows_history.tsv` is already too large to manage via MCP**

The file is ~95KB and already at the limit for reliable GitHub MCP pushes. Quarterly batch appends will make this worse. Options to consider: split into per-year archive files (e.g. `history/2021.tsv`, `history/2022.tsv`, ...) that are never modified once closed; or keep a single flat file but accept that it's always committed manually. Scripts that currently read history need to handle a multi-file layout if that path is chosen. The correlation and playlist scripts are the main consumers.

**Problem 3 — Filename and workflow coupling**

Scripts and the email ticket workflow currently hardcode `live_shows_2026.tsv`. Rename to `live_shows_current.tsv` so no script update is needed at rollover — the old year file just gets archived as `live_shows_2026.tsv` (read-only snapshot) and `live_shows_current.tsv` carries on.

**Other questions to resolve during design:**

- Migration trigger: manual on demand vs. a `--migrate` flag on `youtube_correlate.py` that sweeps rows older than ~90 days with `Status=attended`
- What counts as "settled enough to migrate": `Status=attended` + `Playlist URL` filled or confirmed blank
- `--sync-artists` should run as part of any migration

---

### 3. Review pre-pandemic show history for potential inclusion

`live_shows_history.tsv` currently starts with 2021-07-11 (first post-pandemic show).
There are approximately 22 shows from 2002–2019 that have never been included. Record
keeping pre-pandemic was sparse and inconsistent, so this long tail is incomplete by
nature.

**Context:** The gap was discovered when Billy Strings was found in Seated.com follows
but not in `artists.tsv` — his first appearance was as a supporting act at a 2019-02-02
Greensky Bluegrass show at The Anthem, which predates the history file. This raised the
question of whether backfilling the pre-pandemic shows would be worth doing given the
data quality limitations.

**Questions to decide:**

- Is a sparse, incomplete pre-pandemic record worse than no record at all, or does
  any data beat no data for the purposes of `artists.tsv` counts and first-seen dates?
- If added, should pre-pandemic shows live in the same `live_shows_history.tsv` file,
  or a separate `live_shows_pre_2021.tsv` to keep the quality distinction clear?
- What sources exist to reconstruct the pre-pandemic list? (email receipts, setlist.fm
  history, memory, photos, etc.)
- Should `artists.tsv` Times Seen / First Seen be updated retroactively for any artists
  who appear in the pre-pandemic shows? This could meaningfully change first-seen dates
  and counts for artists like Greensky Bluegrass, Trombone Shorty, Keb' Mo', etc.
- Are there any artists who would cross the "second appearance" threshold for a new
  `artists.tsv` entry if pre-pandemic data were included (e.g. Billy Strings)?

---

### 4. Sync Facebook concert photo album to rhbl Google Photos

Show photos posted to Facebook need to be downloaded and re-uploaded to the rhbl
Google Photos account so they exist in a non-Facebook-dependent archive alongside
the YouTube playlists.

**What to do:**
1. Download concert photos from the Facebook album (manual — Facebook does not allow
   automated export)
2. Upload to Google Photos under the rhbl account (redhat.bootlegs@gmail.com)
3. Organize into per-show albums matching the YouTube playlist naming convention
   where possible

**Notes:**
- Facebook album is the current source of record for show photos
- Goal is to have photos and video playlists co-located under the same Google account
- This is a one-time bulk sync followed by keeping in sync after each show
- No tooling exists for this yet — manual process or explore Google Photos upload
  options
