# Email Workflows — Live Show Archive

Four standing routines for processing emails from the **redhat.bootlegs@gmail.com** inbox.
None are automatic — you trigger each by starting a new conversation in this project
and telling me there's an email to process.

**Pre-requisite:** Subscribe redhat.bootlegs@gmail.com to venue and artist mailing lists
so that on-sale alerts, pre-sale codes, and newsletters arrive there directly. See the
list of suggested subscriptions at the bottom of this file.

---

## Gmail Label System

Three labels are in use on the redhat.bootlegs inbox:

**`processed`** — Applied manually by you after any email workflow completes. I always
include `-label:processed` in my search queries so previously handled emails are never
re-processed. At the end of each routine I will remind you to apply this label to the
email(s) that were processed.

**`ticket-alert`** — Applied manually (or via a Gmail filter) to incoming venue/artist
newsletter emails once mailing list subscriptions are in place. Routine 3 searches
`label:ticket-alert -label:processed` to find unprocessed on-sale alerts.

**`artist-mail`** — Applied manually (or via Gmail filter) to emails from artist
newsletter subscriptions. Routine 4 searches `label:artist-mail -label:processed`
to find unprocessed artist mail. The primary things to mine are: tour announcements,
artist pre-sale codes, and new music releases.

**What I cannot do:** I can read labels and search by them, but I cannot apply, remove,
or create labels, mark emails as read, or create Gmail filters. All label management
is manual.

**Search patterns used by each routine:**

| Routine | Search query |
|---------|-------------|
| 1 — Ticket purchase | `from:dan2bit subject:[artist] -label:processed` (forwarded confirmation) |
| 2 — Post-show notes | `from:dan2bit subject:[artist] notes -label:processed` |
| 3 — On-sale alert | `label:ticket-alert -label:processed` |
| 4 — Artist newsletter | `label:artist-mail -label:processed` |

---

## Calendar Availability Rule

**A date is unavailable if it has a timed show event OR an all-day `NO SHOWS` block.**

When checking whether a date is open — for conflict checking in Routine 1, for
recommendations in Routine 3, or for any direct availability question — always query
the calendar for both timed events and all-day events on that date. Treat either of
the following as unavailable:

- A timed event (any show already booked)
- An all-day event titled **NO SHOWS** (a personal block marking a date off-limits
  for any reason — travel, prior commitment, recovery day, etc.)

Do not recommend a ticket purchase or create a show event on a date blocked by either.

---

## artists.tsv Counting Policy

**Times Seen counts every appearance — headliner and supporting act alike.**

When updating `artists.tsv` after a show, count the show for every artist in
`artists.tsv` who was in the room, regardless of whether they headlined or opened.
This applies to:

- The headliner
- Any named supporting act who is already in `artists.tsv`
- Any named supporting act who reaches their **second** appearance across all shows
  (see New Entry Rule below)

**First Seen / Most Recent Seen** use the same inclusive logic: if an artist's earliest
appearance was as a support act, that date is their First Seen. Most Recent Seen is
updated whenever they appear, in any role.

**New Entry Rule — support acts:** A supporting artist who is not yet in `artists.tsv`
gets a new row added **only when their second appearance is recorded.** One-off openers
do not get entries. The first time you see someone only as a support act, make a note
in the post-show email if they seem worth tracking; on their second appearance, add the
row at that time and backfill the first date. Carly Harvey is the reference example:
three support appearances across Ana Popović and Selwyn Birchwood shows, added on
reaching that threshold.

**History file is the source of truth.** When in doubt about counts or dates, audit
`live_shows_history.tsv` and `live_shows_2026.tsv` together rather than relying on
the current `artists.tsv` values.

---

## Routine 1 — New Ticket Purchase Email

**Trigger:** A ticket confirmation forwarded from dan2bit@gmail.com arrives in the
redhat.bootlegs inbox (Ticketmaster, AXS, Eventbrite, See Tickets/Eventim, box office
receipt image, etc.)

### What I do

**Step 1 — Find and parse the email**

Search `from:dan2bit -label:processed` filtered to recent messages, identify the
ticket confirmation, and extract:
- Artist and supporting act(s)
- Show date, doors time, show time
- Venue name and full address
- Seat info / GA status
- Ticket access method (AXS app, Ticketmaster app, paper, mobile barcode, etc.)
- Ticket quantity
- Face value per ticket
- Fees (itemized if available)
- Total cost
- Purchase date
- Any order reference numbers, promo codes, or special notes

**Step 2 — Apply venue defaults**

Default times and details if not explicit in the email:

| Venue | Doors | Show | Notes |
|-------|-------|------|-------|
| The Birchmere | 5:00 PM | 7:30 PM | GA; seating begins 6:30 PM; always free parking |
| Hamilton Live | 6:30 PM | 8:00 PM | $13 parking |
| Rams Head On Stage | 1 hr before show | — | — |
| Wolf Trap Filene Center | — | — | Use ticket for times |
| Wolf Trap Barns | — | — | Use ticket for times |

"An Evening With" billing means no supporting act. VIP tickets get `(VIP)` appended
to the calendar event title as a reminder to watch for access instructions.

**Step 3 — Check autograph books**

Look up the headliner in `autograph_books_combined.tsv`
(Google Drive ID: `1ENPcmHxrbdMfJNuDlqy-RRBHkGm8Onyy`).

- If artist is in **RHBS**: prepend `📚 BRING RHBS — [Artist] p.[N]` to the calendar event description
- If artist is in **APS**: prepend `📚 BRING APS — [Artist] p.[N]`
- If in both: list both books
- If not in either: no prefix

**Step 4 — Create calendar event**

Calendar: `redhat.bootlegs@gmail.com` — Dan Concert Calendar

Event title format: `[Artist]` (add `(VIP)` if VIP ticket)

Description format:
```
📚 BRING RHBS — [Artist] p.[N]          ← only if in autograph book

[Order # / Ref] ([Ticketer])
Ticket access: [method]
Payment: [card/method] · Face $X.XX · Fees $X.XX · Total $X.XX
[Supporting act line if applicable]
[Any special notes: promo code, resale note, upgrade available, etc.]

[Seat / GA info]
Doors: [time] · Show: [time]

💸 High ticket cost — cool it on merch tonight   ← only if total ≥ $100, NOT a VIP ticket, and NOT Wolf Trap Filene Center
```

Reminders: 24 hours (1440 min) and 3 hours (180 min) popup.

**Merch caution rule:** If the ticket total is ≥ $100 and the ticket is **not** a VIP
package, append `💸 High ticket cost — cool it on merch tonight` to the event
description. Two exceptions — do **not** add this note for:
- **VIP tickets** — the premium is expected and factored in at purchase time
- **Wolf Trap Filene Center** — venue/lawn context makes merch spend a different calculus

**Step 5 — Commit new row to `live_shows_2026.tsv`**

Insert the new row in date order and commit directly to `main` via the GitHub MCP.

Row format (25 columns):

```
Show ID | Artist | Supporting Artist | Show Date | Doors Time | Start Time |
Venue Name | Venue Address | Venue Event URL | Seat Info / GA | Ticket Access |
Ticket Quantity | Face Value (per ticket) | Fees | Total Cost | Purchase Date |
Setlist.fm URL | Personal Rating | Status | Food & Bev | Parking | Merch |
Artist Interaction | Playlist URL | Notes / Memories
```

- `Show ID` = same as Show Date (YYYY-MM-DD)
- `Status` = `upcoming`
- Spending columns (Food & Bev, Parking, Merch, Artist Interaction) = blank
- `Setlist.fm URL` = blank
- `Notes / Memories` = any pre-show notes from the ticket (order #, seat notes, etc.)

**If the commit fails:** present the full updated `live_shows_2026.tsv` in the
conversation for download and manual check-in.

**Final step:** Remind you to apply the `processed` label to the email.

---

## Routine 2 — Post-Show Notes Email

**Trigger:** You send an email to (or forward to) redhat.bootlegs@gmail.com after
attending a show. The email should include:

- Spending: food & bev, parking, merch amounts
- Setlist.fm URL for the show
- Autograph note (if you got one — book vs. hat, who signed, and if a supporting act member)
- Any show notes or memories worth recording
- Artist interaction type (Autograph, Photo, Both, or none)

**Subject line convention:** Use the artist name (e.g. "Danielle Nicole 3/20/26 notes")
so I can find the matching calendar event and TSV row easily.

### What I do

**Step 1 — Find the matching email and show**

Search `from:dan2bit subject:[artist] notes -label:processed`, read the email, then
find the matching calendar event and `live_shows_2026.tsv` row.

**Step 2 — Update the calendar event**

Append spending and setlist info to the existing event description:

```
Spending: Food/Bev $X · Parking $X · Merch $X
Setlist: [setlist.fm URL]
[Notes / memories if notable]
```

**Step 3 — Update autograph records (if applicable)**

If the email mentions getting a **book autograph** (RHBS or APS):

1. Read `autograph_books_combined.tsv` from Drive
   (Drive ID: `1ENPcmHxrbdMfJNuDlqy-RRBHkGm8Onyy`)
2. Find the artist row
3. Set the appropriate `RHBS Signed` or `APS Signed` column to `Yes`
4. Add any notes to the `APS Autograph Notes` column if relevant

If the email mentions a **hat autograph**:

1. Update `artists.tsv` — set `Hat Autograph` to `Y` for the signing artist
2. Update `autograph_books_combined.tsv` — add signer name, show, and date to the
   `Hat Notes` column for that artist row
3. **Remind you to manually append the entry to the hat autograph Google Doc**
   (https://docs.google.com/document/d/1haKMpfwPWosdPnZXBAAlLUzj3926hoTEH7icg6gTRA8/edit)
   — no write connector is available for Google Docs, so this step is always manual.
   Format to use: `**[Name]** [*of/w/ Act*] @ [Venue short name] [M/D/YY]`

Note: hat signers are often supporting act members or band members rather than the
headliner. The email should make clear who signed and in what capacity.

**Step 4 — Open a PR with all file changes**

Create a branch named `post-show/[artist-slug]-[YYYY-MM-DD]` and open a PR to
`main` containing:

- `live_shows_2026.tsv` — row updated: `Status` → `attended`, spending filled,
  `Setlist.fm URL` filled, `Notes / Memories` filled, `Artist Interaction` filled
- `artists.tsv` — always included; apply counting policy below
- `autograph_books_combined.tsv` — `RHBS Signed` / `APS Signed` set to `Yes`
  and/or `Hat Notes` updated if applicable (omit file if no change)

PR description summarises what changed so you can review the diff before merging.

**If the PR creation fails:** present each changed file in the conversation for
download and manual check-in.

**Final step:** Remind you to apply the `processed` label to the email.

### artists.tsv update rules for Routine 2

Apply the following every time a post-show PR is built. `artists.tsv` is **always**
included in the PR — never committed separately.

**For the headliner:**
- Increment `Times Seen` by 1
- Update `Most Recent Seen` to the show date
- `First Seen` only changes if this show predates the current value (rare)

**For each named supporting act listed in the show's `Supporting Artist` field:**

1. **Already in `artists.tsv`:** increment their `Times Seen` by 1, update
   `Most Recent Seen`. Update `First Seen` if this show predates their current value.

2. **Not yet in `artists.tsv` — first time seeing them:** do not add a row yet.
   Note in the PR description that this artist appeared as support for the first time.
   No action in the file until their second appearance.

3. **Not yet in `artists.tsv` — second or subsequent time seeing them:** add a new
   row now. `Times Seen` = total number of times seen across all shows (headliner and
   support combined). `First Seen` = their earliest appearance date. `Most Recent Seen`
   = their most recent appearance date (blank if only one appearance, which cannot
   apply here since this is at least their second). Fill `YouTube Channel` and
   `Spotify URL` if known; leave blank otherwise.

**Hat Autograph / Book Autograph columns** are updated separately per the autograph
rules above and are not affected by the counting policy change.

---

## Routine 3 — Pre-Sale / On-Sale Notification Email

**Trigger:** An on-sale alert, pre-sale announcement, or venue/artist newsletter
tagged `ticket-alert` arrives in the redhat.bootlegs inbox.

### What I do

**Step 1 — Find and parse the email**

Search `label:ticket-alert -label:processed`, read each unprocessed alert, and
classify each artist mention as one of two cases:

**Case A — Tickets already on sale** (no specific future on-sale time given):
- Filter to artists on the Strong or Medium tiers (seen before, or in autograph books)
- Check calendar for conflicts on the show date (apply Calendar Availability Rule above)
- Present a tiered list of open-date recommendations with direct Ticketmaster/AXS
  search links — no calendar event created
- Include autograph book note if applicable

**Case B — Specific future on-sale time given** (pre-sale or general on-sale announced):
- Only act on **Strong tier** artists (previously seen) with a confirmed open date
- Check calendar for conflicts before proceeding (apply Calendar Availability Rule above)
- Create an on-sale reminder calendar event (see Step 3 below)

For digest-style newsletters (multiple artists, no specific on-sale times), treat all
entries as Case A and present the tiered list. Do not create calendar events for
digest newsletters.

**Non-Ticketmaster forwarded emails:** If the email is tagged `ticket-alert` but was
forwarded from `dan2bit@gmail.com` (rather than arriving directly from a ticketing
platform), it means the subscription is still pointed at the dan2bit address and needs
to be re-targeted. After processing the content as normal, scan the email body for a
subscription management link — typically labeled "Update Profile", "Manage
Preferences", "Update email address", or similar, often in the footer. Present that
link so you can re-subscribe under `redhat.bootlegs@gmail.com`. Common providers:
- **Constant Contact** — "Update Profile" link in footer; allows direct email change
- **Mailchimp** — "Update your preferences" link in footer; may or may not allow email
  change depending on list settings. If the email field is locked, a fresh signup at
  the venue's website under `redhat.bootlegs@gmail.com` is required instead.
- Venue box office systems vary — note the sender address if no management link is found

**IMP newsletter special rule:** When processing an IMP newsletter (9:30 Club,
The Anthem, Lincoln Theatre, The Atlantis, Merriweather), apply the standard tiering
above and additionally flag any **The Atlantis** show featuring a local DC artist as a
gift card opportunity — even for artists below the Strong/Medium threshold. There is a
$35.50 IMP gift card credit available, redeemable in person at any IMP box office
(The Anthem has the longest hours and is the closest). Atlantis shows are low-cost
enough that the gift card can cover them outright, making this a "take a chance"
budget for supporting the local DC scene.

**Step 2 — Check autograph books**

Same lookup as Routine 1 — note book reminder in any recommendation or calendar
event description.

**Step 3 — Create on-sale reminder event (Case B only)**

Calendar: `redhat.bootlegs@gmail.com` — Dan Concert Calendar

Event title format: `🎟 ON SALE: [Artist]`

Timing:
- **Start:** 5 minutes before the on-sale/pre-sale time
- **Duration:** 15 minutes

Description format:
```
📚 BRING RHBS — [Artist] p.[N]          ← only if in autograph book

[Artist] tickets on sale [date] at [time]
Buy here: [ticket URL]

Pre-sale code: [CODE]                   ← only if present
Pre-sale window: [start] – [end]        ← only if known
[Venue] · [Show date if known]
[Any pricing or seat tier notes]
```

Reminders:
- 24 hours before (1440 min) — advance notice to plan
- 5 minutes before (5 min) — fires right as you're sitting down to buy

**No TSV row is created** — that comes when the ticket is actually purchased
and processed via Routine 1.

**Final step:** Remind you to apply the `processed` label to the email.

---

## Routine 4 — Artist Newsletter Email

**Trigger:** An email from an artist mailing list subscription arrives in the
redhat.bootlegs inbox tagged `artist-mail`.

### Subscribed artists (as of 2026-03-30)

| Artist | Notes |
|--------|-------|
| Allison Russell | |
| Amythyst Kiah | |
| Albert Castiglia | |
| Buffalo Nichols | |
| Bywater Call | |
| Daniel Donato | |
| Ghalia Volt | |
| Jackie Venson | |
| Judith Hill | |
| Larkin Poe | |
| Lone Bellow, The | |
| Mike Zito | |
| Robert Randolph | |
| Ruthie Foster | |
| Samantha Fish | |
| Shemekia Copeland | |
| Southern Avenue | |
| Sue Foley | |
| Taj Farrant | |
| Tal Wilkenfeld | |
| Trombone Shorty & Orleans Avenue | |
| Vanessa Collier | |
| War and Treaty, The | |

**Not subscribed — known reasons:**
- Enter the Haggis — defunct; follow Haggis X-1 and House of Hamill instead
- Eric Gales, Selwyn Birchwood, Valerie June, Ana Popović — no email list found
- Kingsley Flood, Oh He Dead — too small/hyperlocal; shows already caught by venue newsletters
- Ally Venable — uses Patreon instead of email list

### What I do

**Step 1 — Find and read the emails**

Search `label:artist-mail -label:processed`, read each unprocessed email.

**⚠️ Gmail Promotions tab:** Artist welcome emails and newsletters sometimes land in
the **Promotions** tab rather than Primary, bypassing the `artist-mail` label filter.
When running Routine 4, also check `in:promotions -label:processed` for any unlabeled
newsletters from subscribed artists. Move any found to Primary and apply the
`artist-mail` label before processing. This cannot be done by Claude — it requires
manual action in Gmail.

**Step 2 — Classify and act on content**

For each email, look for three things:

**Tour announcements / new show dates:**
- Check if any announced show is in the DC/MD/VA area (or a driveable venue you've
  attended before)
- Check calendar for conflicts on the show date (apply Calendar Availability Rule)
- If open date + Strong tier artist + DC/MD/VA venue: present as a buy recommendation
  with the ticket link
- If specific on-sale time is given: create a `🎟 ON SALE:` calendar event exactly
  as in Routine 3 Step 3

**Pre-sale codes:**
- If a pre-sale code is included for a show on an open date: create a `🎟 ON SALE:`
  calendar event with the code prominently in the description
- If no show date is yet announced alongside the code: note the code and artist in
  the response so you can act when the date is confirmed

**New music releases:**
- Note the release (title, format, release date) in the response
- No calendar event or TSV action needed — just surfacing the information

**Step 3 — Autograph book check**

For any DC/MD/VA show recommendation, check `autograph_books_combined.tsv` and
include the book reminder in the recommendation exactly as in Routine 1.

**Final step:** Remind you to apply the `processed` label to each email processed.

---

## Notes

**Inbox monitoring is not automatic.** I don't poll the inbox. You trigger these
routines by telling me "there's a ticket email", "I just sent my post-show notes",
"there's an on-sale alert", or "process my artist mail" in a new project conversation.
I'll search the inbox and take it from there.

**Hat autograph gdoc is the completeness authority.** The Google Doc at the link
above is more carefully maintained for hat autographs than the TSV files. If there
is a discrepancy between the gdoc and the TSV, the gdoc wins for the list of signers;
the TSV files win for show dates. No write connector exists for Google Docs — all
gdoc updates are manual.

**Google Calendar MCP fails on Android.** Calendar operations only work reliably
on macOS desktop. If calendar steps fail, switch to desktop before retrying.

**YouTube pipeline is separate.** Neither routine touches `youtube_fetch.py`,
`youtube_correlate.py`, or `youtube_create_playlists.py`. Those run on your own
schedule after video uploads — see TASKS.md.

---

## Pre-Requisite: Mailing List Subscriptions

Subscribe **redhat.bootlegs@gmail.com** to the following so that on-sale alerts
and pre-sale codes arrive in the inbox for Routine 3 to process. Apply the
`ticket-alert` label (manually or via a Gmail filter on the sender address) as
each subscription is set up.

**Venues (subscribed ✅):**
- The Birchmere ✅
- Hamilton Live ✅
- Rams Head On Stage ✅
- State Theatre ✅
- Collective Encore ✅
- Ticketmaster newsletter (forwarded from dan2bit) ✅
  Union Stage Presents (Pearl Street, Jammin Java, Howard Theatre, Union Stage) ✅
- Wolf Trap — wolftrap.org (email alerts) ✅
- 9:30 Club / Merriweather / other IMP venues — imppresents.com ✅
- Bethesda Theater — bethesdatheater.com ✅ (re-targeted 4/1/26 via Constant Contact)

**Venues (pending — fresh signup needed under redhat.bootlegs):**
- Hub City Vinyl (Hagerstown) — liveathubcityvinyl.com (Mailchimp; email change not supported, requires new signup)
- Strathmore — strathmore.org
- Capital One Hall — capitalonehall.com
- The Fillmore Silver Spring — fillmoresilverspring.com

**Ticketing platforms:**
- AXS — axs.com (artist follows)
- Eventbrite — follow relevant organizers

**Bandsintown** — redhat.bootlegs account (fresh start; dan2bit account to be retired).
  Artist follow list managed via `worklist_bandsintown.tsv` and `follows_master.tsv`.
  BIT sends email alerts for followed artists directly to the registered account email,
  making redhat.bootlegs the correct home for this. ~120 artists per the worklist.

**Artist newsletters** — see Routine 4 subscriber list above. ✅ Complete as of 2026-03-30.
