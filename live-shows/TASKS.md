# songs-for-my-funeral — Archive Task List

Collaborative task list for the live show archive project. Update status as tasks complete.

---

## 🎟 Standing Checks — Every Inbox Session

### A. Hub City Vinyl — ticket availability monitoring

Check these two Eventbrite pages at the start of every inbox processing session for LOW TICKET ALERT or SOLD OUT status. Alert Dan immediately if either condition is met.

| Show | Date | Eventbrite URL |
|------|------|----------------|
| Carolyn Wonderland | Sep 24, 2026 | https://www.eventbrite.com/e/carolyn-wonderland-tickets-1983173922588 |
| JD Simo & Luther Dickinson | Aug 6, 2026 | https://www.eventbrite.com/e/bluesamericana-with-jd-simo-luther-dickinson-tickets-1970731399667 |

Also watch for Hub City Vinyl emails arriving at redhat.bootlegs@gmail.com mentioning these shows.

**Decision context:**
- Carolyn Wonderland (Sep 24) — Strong buy candidate; also watching for a closer DC/MD show in September. If a closer show is found, compare and buy the better option.
- JD Simo & Luther Dickinson (Aug 6) — Medium consideration; Hub City is a distance stretch

### B. Potential shows list

See `live-shows/live_shows_potential.tsv` for the full list of uncommitted shows with ticket links, pricing, and notes. Update this file when shows are purchased, cancelled, or dropped. Fields: Artist, Support, Date, Day, Venue, Venue City, Tier, Ticket Service, Purchase URL, Event URL, Face Price (est.), Fees Notes, Availability Notes, Notes.

**Current entries (as of 2026-04-03):**

| Artist | Date | Venue | Tier | Status |
|--------|------|-------|------|--------|
| Lucinda Williams | May 25, 2026 | 9:30 Club, DC | Strong | Pending buy |
| Lucinda Williams | May 26, 2026 | 9:30 Club, DC | Strong | Pending buy (alt date) |
| Taj Mahal & Phantom Blues Band | Jul 12, 2026 | Birchmere, Alexandria | Strong | Pending buy |
| JD Simo & Luther Dickinson | Aug 6, 2026 | Hub City Vinyl, Hagerstown | Medium | Monitoring |
| Carolyn Wonderland | Sep 24, 2026 | Hub City Vinyl, Hagerstown | Strong | Monitoring — watching for closer show |

---

## 🔍 Research / Eyeball Tasks (anytime — no quota cost)

### 1. Add 5 Hub City artists to new_artist_research.tsv

These artists appeared on the Hub City Vinyl 2026 calendar and are worth tracking for future shows closer to home. Dan won't travel to Hub City for them but wants them in the research file.

- Quinn Sullivan (Apr 23) — Blues-rock, Buddy Guy protégé
- Indigenous ft. Mato Nanji (May 17) — Native American blues-rock, Grammy-nominated
- Davy Knowles (Sep 17) — Isle of Man blues guitarist, backed Peter Green's Splinter Group
- Matt Schofield (Aug 13) — British blues-rock guitarist, well-regarded in the blues world
- The Nighthawks with Daryl Davis (Oct 25) — DC blues institution

### 2. Upload found videos to YouTube for 11 no-playlist shows — 📅 manual

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

## ✅ Completed

### 3. ~~Merge `notes_memories_draft.tsv` into history~~ — DONE 2026-04-08

Notes from `notes_memories_draft.tsv` merged into `live_shows_history.tsv` via
`merge_notes_into_history.py` (PR #18, merged 2026-04-08). Script moved to `archive/`.
`notes_memories_draft.tsv` deleted.

Corrections applied during merge:
- Wu-Tang Clan / Nas headliner swap corrected in history
- `2023-05-20` artist key corrected (The Wood Brothers → Shovels & Rope)
- `2024-07-18` artist key corrected (Mike Zito → Tab Benoit & Anders Osborne)
- 11 rows overwritten where draft had additions or corrections vs. history

**Next:** Generate a worklist of history rows still missing Notes / Memories.

---

## 🔄 Ongoing / Maintenance

### 4. Design and implement rolling migration + archive architecture

⚠️ **Must be designed before the first 2027 ticket purchase.**

The goal is to reframe `live_shows_2026.tsv` as a **rolling "upcoming + recently attended" window**. Attended rows migrate out on a quarterly-ish cadence once settled — playlist URL populated, notes written. The current file always stays lean.

This task has three distinct architectural problems to solve together:

**Problem 1 — Spending data doesn't belong in the history file**

Spending columns (Food & Bev, Parking, Merch, Artist Interaction) are present in `live_shows_2026.tsv` but not in `live_shows_history.tsv`. The data is worth preserving for budgeting across quarters and years, but it doesn't belong in the attendance record. The right answer is a separate `spending.tsv` (keyed by Show Date + Artist) that can be queried independently. Migration needs to extract spending into this file rather than either dropping it or bloating history.

**Problem 2 — `live_shows_history.tsv` is already too large to manage via MCP**

The file is ~95KB and already at the limit for reliable GitHub MCP pushes. Quarterly batch appends will make this worse. Options to consider: split into per-year archive files (e.g. `history/2021.tsv`, `history/2022.tsv`, ...) that are never modified once closed; or keep a single flat file but accept that it's always committed manually. Scripts that currently read history need to handle a multi-file layout if that path is chosen. The correlation and playlist scripts are the main consumers.

**Problem 3 — Filename and workflow coupling**

Scripts and the email ticket workflow currently hardcode `live_shows_2026.tsv`. Rename to `live_shows_current.tsv` so no script update is needed at rollover — the old year file just gets archived as `live_shows_2026.tsv` (read-only snapshot) and `live_shows_current.tsv` carries on.

**Other questions to resolve during design:**

- Migration trigger: manual on demand vs. a `--migrate` flag on `youtube_correlate.py` that sweeps rows older than ~90 days with `Status=attended`
- What counts as "settled enough to migrate": `Status=attended` + `Playlist URL` filled or confirmed blank
- `--sync-artists` should run as part of any migration

---

### 5. Define HFTB monitoring cadence and recommendation tiers

HereForTheBands.com (HFTB) is the primary source for DC/MD/VA show discovery. Define a repeatable process for checking it and acting on potential buys.

**Known HFTB limitations:**
- Hamilton Live, Rams Head On Stage, and Wolf Trap Filene are not covered

**Recommendation tiers (already established):**
- **Strong** — artist seen before at any venue
- **Medium** — artist in autograph books at a previously attended venue
- **Low** — artist in books at a new or distant venue

**Questions to resolve:**
- How often should HFTB be checked? (Weekly? After payday? Before each show?)
- Should there be a calendar reminder to trigger the check?
- Is there an existing script for parsing HFTB, and if so what does it output?
- Should recommendations be presented as a tiered list in conversation, or logged to a file?
- What's the action threshold — Strong always buy, Medium research first, Low ignore unless something stands out?

---

### 6. Mine festival and award lineups for new artist discovery

A complement to HFTB (task #5) and Gnoosic exploration. Blues cruises, major festivals,
and annual award nominees are rich sources for discovering artists in your taste profile
who aren't yet on your radar. Priority and scope are similar to task #5 — periodic
research rather than a one-time pass.

**Primary sources to monitor:**

- **Blues Music Awards (BMA)** — Blues Foundation annual nominees and winners.
  Published each spring. Cross-reference nominee lists against `artists.tsv` to flag
  Strong-tier artists and identify new names worth researching.
  URL: https://blues.org/blues-music-awards/

- **Americana Music Association Awards** — Nominees and winners published each fall.
  Americana/roots overlap is significant with your taste profile.
  URL: https://americanamusic.org/ama-awards

- **Blues Cruises** — Lineup announcements are a curated signal: booking agents for
  these events target proven draw artists in the blues/roots space.
  - Joe Bonamassa's Keeping the Blues Alive at Sea (annual, Caribbean)
  - Rock Legends Cruise (annual, Caribbean)
  - Legendary Rhythm & Blues Cruise (annual, Caribbean/Mexico)

- **Big Blues Bender** — Annual Las Vegas festival, late September. One of the largest
  dedicated blues festivals in the USA. Strong artist concentration across blues
  subgenres. URL: https://bigbluesbender.com

- **Notable Americana festivals** — Lineups tend to surface the same artist pool
  you care about before they come to your area:
  - Hardly Strictly Bluegrass (San Francisco, free, early October)
  - Americanafest / AmericanaFest (Nashville, September)
  - Stagecoach (Indio CA, April — country/Americana)
  - Telluride Bluegrass Festival (Colorado, June)

**Workflow:**

1. Pull the current year's BMA nominees and AMA nominees lists
2. Cross-reference against `artists.tsv` (Strong tier = seen before; Medium = in autograph books)
3. Flag new names not yet in either — research via `new_artist_research.tsv` format
4. Check blues cruise and festival lineups for the same cross-reference
5. For any Strong-tier new discoveries, consider adding to Seated/Bandsintown follows

**Questions to resolve:**
- Should this run on a defined cadence (e.g. after BMA nominees announced in Jan/Feb,
  after AMA nominees in summer)? Or ad hoc when conversation warrants?
- Should output be appended to `new_artist_research.tsv` or kept as a separate file?
- Is there overlap with the Gnoosic excursion results that should be reconciled?

---

### 7. Review pre-pandemic show history for potential inclusion

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
