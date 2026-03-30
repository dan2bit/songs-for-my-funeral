# songs-for-my-funeral — Archive Task List

Collaborative task list for the live show archive project. Update status as tasks complete.

---

## 🔧 Ready to Run (quota reset needed)

### 1. ~~Create ZZ Ward 2026 playlist~~ ✅ COMPLETE

Playlist created manually. URL committed to `live_shows_2026.tsv`.

---

### 2. Create remaining WORKLIST backfill playlists (partial — quota hit after Nas)

Run got through 2023-09-26 Nas before exhausting quota. The 12 shows processed so far
have playlists; the remaining 11 still need to be created on the next quota reset.

```bash
cd live-shows
source .venv/bin/activate

# Preview first
python3 youtube_create_playlists.py --worklist --dry-run

# Then create
python3 youtube_create_playlists.py --worklist --update-history
```

After completion: `live_shows_history.tsv` will be updated with remaining playlist URLs.
The WORKLIST in `youtube_create_playlists.py` should then be cleared and entries moved to the "Completed" comment block.

**Remaining WORKLIST shows (11):**
| Date | Artist |
|------|--------|
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

25 shows have no playlist URL and no matching videos in `youtube_videos.tsv` using exact date matching. Use the audit script to scan with a loose +30-day window and fuzzy artist-name title matching.

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
| 2021-11-18 | Christone 'Kingfish' Ingram |
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

After task #2 completes all remaining playlists, run `youtube_fetch.py` to re-ingest the channel and populate the new playlist URLs into `youtube_videos.tsv` video descriptions.

```bash
cd live-shows
source .venv/bin/activate
python3 youtube_fetch.py --since 2021-07-01
```

Then run `youtube_correlate.py --merge --sync-artists` to push any new URL correlations back into the history files and keep `artists.tsv` current.

---

### 8. ~~Venues TSV parking update~~ ✅ COMPLETE

`venues.tsv` now has a `Parking Cost` column. Ram's Head = $9.45, Hamilton Live = $13.00,
Warner Theatre = $13.00 (same lot). All 2026 attended shows corrected accordingly.

---

### 9. Design and implement rolling migration + archive architecture

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

### 10. Define HFTB monitoring cadence and recommendation tiers

HereForTheBands.com (HFTB) is the primary source for DC/MD/VA show discovery. Define a repeatable process for checking it and acting on potential buys.

**Known HFTB limitations:**
- Hamilton Live, Ram's Head On Stage, and Wolf Trap Filene are not covered

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

### 11. Subscribe redhat.bootlegs to venue and artist mailing lists

**Pre-requisite for Routine 3** (pre-sale / on-sale email processing).

See `EMAIL_WORKFLOWS.md` for the current subscription status. Venue subscriptions are
largely in place; pending venues and artist newsletters still need attention.

Seated.com ticket alert emails are now being forwarded to the inbox — see task #14 for
the follow-up artist-follows audit on that service.

Artist newsletter subscriptions are tracked separately — see task #13.

---

### 12. Build pre-sale / on-sale notification email processing routine

Routine 3 is now documented in `EMAIL_WORKFLOWS.md`. The design is settled:

- **Already on sale (digest newsletters):** Present tiered Strong/Medium recommendations
  for open dates with direct search links — no calendar event created
- **Specific future on-sale time (Strong tier, open date only):** Create a `🎟 ON SALE:`
  calendar event starting 5 min before on-sale, 15 min duration, with 24hr + 5min reminders
- **Title format:** `🎟 ON SALE: [Artist]`
- **No TSV row** created — that's Routine 1's job after purchase
- **Pre-sale codes** and expiry windows go in the event description
- **Autograph book check** same as Routine 1

This task is complete as a design — implement and test against the first on-sale
email that arrives after mailing list subscriptions (task #11) are in place.

---

### 13. Subscribe to artist newsletters for Strong tier favorites

Venue newsletters catch what's playing nearby, but artist newsletters are the best
source for pre-sale codes and early access — especially for high-demand or smaller
shows that sell out quickly.

**Next steps:**
- Identify your top Strong-tier artists (seen multiple times, likely to see again):
  candidates from `artists.tsv` with `Times Seen >= 2` or particularly high priority
- Sign up redhat.bootlegs@gmail.com via each artist's website or fan club
- Apply the `ticket-alert` label (or create a Gmail filter) for each mailing list sender

**Priority candidates to consider** (seen 2+ times):
Allison Russell, Daniel Donato, Enter the Haggis, Eric Gales, Kingsley Flood,
Keb' Mo', Larkin Poe, Oh He Dead, Sue Foley, Tab Benoit, Trombone Shorty,
Vanessa Collier, ZZ Ward, The Lone Bellow, Suzanne Vega

---

### 14. Audit artist follows on Seated.com

Seated.com ticket alert emails (rare) are now being forwarded to the redhat.bootlegs
inbox and will flow into Routine 3 like other ticket-alert emails.

**Next steps:**
- Log into Seated.com and review which artists you currently follow
- Cross-reference against `artists.tsv` Strong tier (Times Seen >= 1) to identify gaps
- Add any missing Strong-tier artists
- Remove any artists you're no longer interested in seeing
- Ensure the forwarding rule stays active so alerts reach the inbox

---

### 15. Evaluate artist-follow alert services: Bandsintown and Songkick

Currently following too many artists on the dan2bit Bandsintown account, making email
alerts noisy and hard to act on. Songkick is the primary Bandsintown alternative and
has a similar artist-follow / email alert model, with potentially stronger small-venue
coverage. Both should be evaluated together before acting on either.

**Note on Spotify concert alerts:** Not worth pursuing. Alerts are keyed to listening
history rather than a curated follow list, and they arrive too late to be useful as
purchase triggers — the latency problem alone disqualifies it for this workflow.

**Questions to resolve before acting:**

- **Bandsintown:** Is the noise problem better solved by pruning the dan2bit follow list
  rather than creating a new account? Does Bandsintown allow multiple accounts (one per
  email address)?
- **Songkick:** Does it surface DC/MD/VA shows at smaller venues (Collective Encore,
  Hamilton Live, Ram's Head) that aren't already caught by venue newsletters or Seated?
  Would following Strong-tier artists there add signal or just duplicate existing sources?
- **Both:** What's the right follow list scope for either service — likely Strong tier
  only (artists seen before), not the full autograph book population
- **Account strategy:** If creating a new account on either service, use redhat.bootlegs
  so alerts flow directly into Routine 3 without forwarding friction

**Decision criteria:** Only set up or restructure an account if it would surface shows
not already caught by venue newsletters, Seated, or artist direct subscriptions — and
only if the follow list can be kept narrow enough to stay actionable.
