# Email Workflows — Live Show Archive

Two standing routines for processing emails from the **redhat.bootlegs@gmail.com** inbox.
Neither is automatic — you trigger each by starting a new conversation in this project
and telling me there's an email to process (or by forwarding the email to the inbox and
asking me to handle it).

---

## Routine 1 — New Ticket Purchase Email

**Trigger:** A ticket confirmation arrives in the redhat.bootlegs inbox (Ticketmaster,
AXS, Eventbrite, See Tickets/Eventim, box office receipt image, etc.)

### What I do

**Step 1 — Parse the email**

Extract:
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

---

## Routine 2 — Post-Show Notes Email

**Trigger:** You send an email to (or forward to) redhat.bootlegs@gmail.com after
attending a show. The email should include:

- Spending: food & bev, parking, merch amounts
- Setlist.fm URL for the show
- Autograph note (if you got one — book vs. hat, who signed)
- Any show notes or memories worth recording
- Artist interaction type (Autograph, Photo, Both, or none)

**Subject line convention:** Use the artist name (e.g. "Danielle Nicole 3/20/26 notes")
so I can find the matching calendar event and TSV row easily.

### What I do

**Step 1 — Find the matching show**

Search the calendar for the event and read the existing `live_shows_2026.tsv` row.

**Step 2 — Update the calendar event**

Append spending and setlist info to the existing event description:

```
Spending: Food/Bev $X · Parking $X · Merch $X
Setlist: [setlist.fm URL]
[Notes / memories if notable]
```

**Step 3 — Update autograph books (if applicable)**

If the email mentions getting an autograph in a book (RHBS or APS):

1. Read `autograph_books_combined.tsv` from Drive
   (Drive ID: `1ENPcmHxrbdMfJNuDlqy-RRBHkGm8Onyy`)
2. Find the artist row
3. Set the appropriate `RHBS Signed` or `APS Signed` column to `Yes`
4. Add any notes to the `APS Autograph Notes` / `Hat Notes` column if relevant

Hat autographs are tracked in `artists.tsv` (`Hat Autograph` column) — update
that too if a hat was signed.

**Step 4 — Open a PR with all file changes**

Create a branch named `post-show/[artist-slug]-[YYYY-MM-DD]` and open a PR to
`main` containing:

- `live_shows_2026.tsv` — row updated: `Status` → `attended`, spending filled,
  `Setlist.fm URL` filled, `Notes / Memories` filled, `Artist Interaction` filled
- `artists.tsv` — `Hat Autograph` set to `Y` if hat was signed (omit file if no change)
- `autograph_books_combined.tsv` — `RHBS Signed` / `APS Signed` set to `Yes`
  if book was signed (omit file if no change)

PR description summarises what changed so you can review the diff before merging.

**If the PR creation fails:** present each changed file in the conversation for
download and manual check-in.

---

## Notes

**Inbox monitoring is not automatic.** I don't poll the inbox. You trigger these
routines by telling me "there's a ticket email" or "I just sent my post-show notes"
in a new project conversation. I'll search the inbox and take it from there.

**Google Calendar MCP fails on Android.** Calendar operations only work reliably
on macOS desktop. If calendar steps fail, switch to desktop before retrying.

**YouTube pipeline is separate.** Neither routine touches `youtube_fetch.py`,
`youtube_correlate.py`, or `youtube_create_playlists.py`. Those run on your own
schedule after video uploads — see TASKS.md.
