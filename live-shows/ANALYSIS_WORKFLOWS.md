# Analysis Workflows — Live Show Archive

Three standing workflows for periodic show discovery and artist research.
These are independent of the email routines in `EMAIL_WORKFLOWS.md` — they
are triggered by calendar reminders, not inbox events.

---

## Workflow 1 — Bandsintown DC Recommends Refresh

**Cadence:** Monthly — 1st Tuesday of each month
**Trigger:** Recurring calendar event "🔄 Re-fetch Bandsintown DC Recommends page"
**Account:** rhbl (redhat.bootlegs@gmail.com)

### What to do

Use Claude in Chrome (logged in as rhbl) to fetch:

```
https://www.bandsintown.com/c/washington-dc?came_from=278&utm_medium=web&utm_source=city_page&utm_campaign=recommended_event&recommended_artists_filter=Recommended
```

Parse the page and save the full listing as:

```
live-shows/web-src/rhbl-bandsintown-dc-recommends.tsv
```

Schema: `Artist | Venue | Date | Event URL`

Then ask Claude to diff the new file against the previous version and surface
any artists not previously present. Flag by tier:

- **Strong** (artist seen before) — surface immediately for review
- **Medium** (artist in autograph books) — surface for review
- **Low** (artist not in either) — log only, no action needed

---

## Workflow 2 — HereForTheBands DC Region Refresh

**Cadence:** Monthly — 1st Tuesday of each month (same session as Workflow 1)
**Trigger:** Recurring calendar event "🔄 Re-fetch Bandsintown DC Recommends page"
**Account:** rhbl (redhat.bootlegs@gmail.com)

### What to do

Use Claude in Chrome (logged in as rhbl) to fetch:

```
https://www.hereforthebands.com/washington-dc
```

Parse the page and save the full listing as:

```
live-shows/web-src/rhbl-hereforthebands-dc.tsv
```

Schema: `Artist | Venue | Date | Venue URL`

Note: HFTB provides one URL per venue, not per event — all shows at the same
venue share the same URL.

Then diff against the previous version and flag new entries by tier (same
tiers as Workflow 1).

Note: The rhbl account receives venue newsletters directly from Rams Head On
Stage, Hamilton Live, and Wolf Trap — those gaps in HFTB coverage are handled
separately via email.

---

## Workflow 3 — Quarterly Artist Research: Festivals & Awards

**Cadence:** Quarterly — 1st Tuesday of January, April, July, and October
**Trigger:** Recurring calendar event "🔍 Quarterly Artist Research — Festivals & Awards"

### Purpose

Blues cruises, major festivals, and annual award nominees are curated signals
for discovering artists in the taste profile who aren't yet on the radar.
This workflow cross-references those external sources against `artists.tsv`
and feeds new discoveries into `new_artist_research.tsv`.

### Sources to check each quarter

**Awards** (check when newly published):

- **Blues Music Awards (BMA)** — Blues Foundation nominees and winners,
  published each spring (Jan/Feb).
  URL: https://blues.org/blues-music-awards/
- **Americana Music Association Awards** — nominees and winners published
  each fall (summer announcement).
  URL: https://americanamusic.org/ama-awards

**Festival lineups** (check when newly published):

- **Hardly Strictly Bluegrass** — San Francisco, free, early October;
  lineup announced ~August
- **Americanafest / AmericanaFest** — Nashville, September
- **Big Blues Bender** — Las Vegas, late September
  URL: https://bigbluesbender.com
- **Blues cruise lineups:**
  - Keeping the Blues Alive at Sea (Joe Bonamassa, annual, Caribbean)
  - Rock Legends Cruise (annual, Caribbean)
  - Legendary Rhythm & Blues Cruise (annual, Caribbean/Mexico)
- **Stagecoach** — Indio CA, April (country/Americana crossover)
- **Telluride Bluegrass Festival** — Colorado, June

### Process

1. For each source that has published new content since the last quarterly
   check, pull the current lineup or nominee list
2. Cross-reference each artist name against `artists.tsv`:
   - **Strong tier** (Times Seen ≥ 1) — flag immediately; may already be
     tracked for upcoming shows
   - **Medium tier** (in autograph books but not seen) — flag for review
   - **New name** (not in either) — research and add to
     `new_artist_research.tsv` if they fit the taste profile
3. For any Strong-tier discoveries playing DC/MD/VA in the near term,
   surface as a potential buy recommendation
4. For any Strong-tier new discoveries not yet followed, consider adding
   to Bandsintown and/or Seated follows

### Output

New artist discoveries go into `live-shows/new_artist_research.tsv`.
No separate output file — the workflow produces either TSV additions
or conversation-level recommendations.
