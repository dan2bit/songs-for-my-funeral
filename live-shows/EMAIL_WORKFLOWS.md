# Email Workflows — Live Show Archive

Three standing routines for processing emails from the **redhat.bootlegs@gmail.com** inbox.
None are automatic — you trigger each by starting a new conversation in this project
and telling me there's an email to process.

**Pre-requisite:** Subscribe redhat.bootlegs@gmail.com to venue and artist mailing lists
so that on-sale alerts, pre-sale codes, and newsletters arrive there directly. See the
list of suggested subscriptions at the bottom of this file.

---

## Gmail Label System

Two labels are in use on the redhat.bootlegs inbox:

**`processed`** — Applied manually by you after any email workflow completes. I always
include `-label:processed` in my search queries so previously handled emails are never
re-processed. At the end of each routine I will remind you to apply this label to the
email(s) that were processed.

**`ticket-alert`** — Applied manually (or via a Gmail filter) to incoming venue/artist
newsletter emails once mailing list subscriptions are in place. Routine 3 searches
`label:ticket-alert -label:processed` to find unprocessed on-sale alerts.

**What I cannot do:** I can read labels and search by them, but I cannot apply, remove,
or create labels, mark emails as read, or create Gmail filters. All label management
is manual.

**Search patterns used by each routine:**

| Routine | Search query |
|---------|-------------|
| 1 — Ticket purchase | `from:dan2bit subject:[artist] -label:processed` (forwarded confirmation) |
| 2 — Post-show notes | `from:dan2bit subject:[artist] notes -label:processed` |
| 3 — On-sale alert | `label:ticket-alert -label:processed` |

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
| Ram's Head On Stage | 1 hr before show | — | — |
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
```

Reminders: 24 hours (1440 min) and 3 hours (180 min) popup.

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
- `artists.tsv` — `Hat Autograph` set to `Y` if hat was signed (omit file if no change)
- `autograph_books_combined.tsv` — `RHBS Signed` / `APS Signed` set to `Yes`
  and/or `Hat Notes` updated if applicable (omit file if no change)

PR description summarises what changed so you can review the diff before merging.

**If the PR creation fails:** present each changed file in the conversation for
download and manual check-in.

**Final step:** Remind you to apply the `processed` label to the email.

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
- Check calendar for conflicts on the show date
- Present a tiered list of open-date recommendations with direct Ticketmaster/AXS
  search links — no calendar event created
- Include autograph book note if applicable

**Case B — Specific future on-sale time given** (pre-sale or general on-sale announced):
- Only act on **Strong tier** artists (previously seen) with a confirmed open date
- Check calendar for conflicts before proceeding
- Create an on-sale reminder calendar event (see Step 3 below)

For digest-style newsletters (multiple artists, no specific on-sale times), treat all
entries as Case A and present the tiered list. Do not create calendar events for
digest newsletters.

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

## Notes

**Inbox monitoring is not automatic.** I don't poll the inbox. You trigger these
routines by telling me "there's a ticket email", "I just sent my post-show notes",
or "there's an on-sale alert" in a new project conversation. I'll search the inbox
and take it from there.

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
- Ram's Head On Stage ✅
- State Theatre ✅
- Collective Encore ✅
- Ticketmaster newsletter (forwarded from dan2bit) ✅

**Venues (pending):**
- Wolf Trap — wolftrap.org (email alerts)
- 9:30 Club / Merriweather / other IMP venues — imppresents.com
- Strathmore — strathmore.org
- Kennedy Center — kennedy-center.org
- Pearl Street Warehouse — pearlstreetwarehouse.com
- Capital One Hall — capitalonehall.com
- The Fillmore Silver Spring — fillmoresilverspring.com

**Ticketing platforms:**
- AXS — axs.com (artist follows)
- Eventbrite — follow relevant organizers

**Artist fan clubs / newsletters** (see TASKS.md #13 — priority list to build out):
- Sign up via artist websites for fan pre-sale access, especially for high-demand shows
