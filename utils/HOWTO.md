# Songs for my Funeral — Maintenance Notes

*For future me, when the playlist needs work.*

---

## Files in this folder

| File | What it is |
|------|------------|
| `liner-notes.html` | The main document. Open in a browser. |
| `talia-segal-first-there-is-goodbye-lyrics.html` | Standalone lyrics page, linked from track 24. |
| `covers/` | Album art, one jpg per track, named `NN-slug.jpg`. |
| `tracks.tsv` | **Single source of truth** for track order, filenames, transitions, and chapters. Edit this first for any structural change. |
| `assemble.sh` | ffmpeg script to build chapter mp3s and master file. Reads from `tracks.tsv`. |
| `reorder.sh` | Renames mp3 files on disk to match `tracks.tsv` after you've reordered. Dry-run by default; use `--apply` to execute. |
| `duration.sh` | Reports individual track durations and total runtime. Reads transitions from `tracks.tsv`. |
| `HOWTO.md` | This file. |
| `one-timers/check-sample-rates.sh` | Audits all 25 mp3s for sample rate, channels, and bitrate. Run if you add new tracks and want to confirm they're all 44100 Hz stereo before assembling. |
| `one-timers/fetch-covers.sh` | Downloads cover art from MusicBrainz / Cover Art Archive. Already run — covers are in `covers/`. Run again only if covers are lost or new tracks need art. |
| `01. Artist - Title.mp3` … | Source tracks, 25 of them. |
| `chapter-01-*.mp3` … | Built by assemble.sh. Rebuild any time tracks change. |
| `songs-for-my-funeral.mp3` | The master. Built by assemble.sh. |

**YouTube playlist:** https://www.youtube.com/playlist?list=PLJ7S-K0cjvGJHuI-kagxZUfN9fOaVV2ET

---

## tracks.tsv — the source of truth

`tracks.tsv` is a tab-separated file that drives `assemble.sh`, `reorder.sh`, and `duration.sh`. Edit it first whenever the playlist changes structurally.

**Columns:**

| Column | Values | Notes |
|--------|--------|-------|
| `num` | `01`–`25` | Track number, zero-padded. Must be unique and sequential. |
| `chapter` | `1`–`6` | Chapter number. All tracks in a chapter must be consecutive rows. |
| `filename` | e.g. `01. Artist - Title.mp3` | Exact filename on disk. |
| `transition_type` | `gap`, `xfade`, `end` | How this track connects to the next. |
| `transition_secs` | e.g. `1.5`, `2.0` | Duration of gap or crossfade in seconds. `0` or blank for `end`. |
| `chapter_break_after` | `yes` or blank | If `yes`, a 3.5s chapter gap is inserted after this track's transition. Always on the last track of each chapter. |

**Transition types:**
- `gap` — silence of `transition_secs` inserted after this track
- `xfade` — crossfade of `transition_secs` into the next track. Consecutive xfades are automatically chained into a single ffmpeg filter.
- `end` — last track in the playlist, no transition

**Chapter break notes:** The `chapter_break_after=yes` flag is separate from `transition_type`. A track can be `gap 2.0 yes` (2s gap, then 3.5s chapter break) or just `gap 3.5 yes` depending on how the chapter ends.

---

## Track inventory

| # | Title | Artist | Format | Chapter | Notes |
|---|-------|--------|--------|---------|-------|
| 01 | Ain't No Grave | Jamie Wilson | live | 1 | |
| 02 | Danny Boy | Sinéad O'Connor | live | 1 | A cappella, RTÉ Late Late Show 1993 |
| 03 | I'll Fly Away | Alison Krauss | studio | 1 | O Brother OST |
| 04 | Ain't Gonna Cry | Larkin Poe | live | 2 | BBC Radio 2 session |
| 05 | Wade in the Water | Sweet Honey in the Rock | live | 2 | No studio version exists |
| 06 | One More Day | The Wood Brothers | live | 2 | Verified live version from *Sky High* (Bandcamp, 323 kb/s). Opens on Jano Rix's snare — studio version opens on guitar. |
| 07 | You're Not Alone | Allison Russell | studio | 2 | ft. Brandi Carlile |
| 08 | Everlasting Arms | Playing for Change | studio | 2 | ft. Dr. John. Song by Luke Winslow-King, 2014; arr. Playing for Change. |
| 09 | Hold On | Alabama Shakes | live | 2 | |
| 10 | When I Go | Dave Carter & Tracy Grammer | live | 3 | St. John Pub, Portland, Dec 2001 |
| 11 | No Hard Feelings | The Avett Brothers | studio | 3 | |
| 12 | Sleeping in the Ground | Clapton & Winwood | live | 4 | Live from MSG |
| 13 | Up Above My Head | Tharpe & Knight | studio | 4 | Decca, 1947 |
| 14 | Gone at Last | Paul Simon & Phoebe Snow | studio | 4 | |
| 15 | Before I'm Old | Kingfish | studio | 4 | |
| 16 | Enjoy Yourself | The Specials | live | 4 | Archival ska club footage |
| 17 | One Last Drink | Enter the Haggis | studio | 4 | |
| 18 | I'll Fly Away | PHJB & Del McCoury Band | live | 5 | Letterman 2011. Trimmed: 23s from start, 19s from end |
| 19 | Lips As Cold As Diamond | Larkin Poe | studio | 5 | |
| 20 | Hallelujah | Sarah Rogo | live | 5 | Haus Music Production, LA, April 2020 |
| 21 | Since the Last Time | Lyle Lovett | live | 5 | SWR Studio 5, Baden-Baden, Nov 1992 |
| 22 | Bright Blue Rose | Mary Black | live | 5 | RTÉ Late Late Show 1991 |
| 23 | Take This Body Home | Rose Betts | live | 6 | |
| 24 | First There Is Goodbye | Talia Segal | studio | 6 | Lyrics need cleanup against recording |
| 25 | The Parting Glass | boygenius & Ye Vagabonds | studio | 6 | Released July 2023 |

**Chapters:**
1. I Am Where I'm Meant to Be (tracks 1–3)
2. You'll Be Okay (Grief Sucks) (tracks 4–9)
3. Don't Worry About Me (tracks 10–11)
4. You're Still in the Pink (tracks 12–17)
5. But Before We Part (tracks 18–22)
6. Go in Good Graces (tracks 23–25)

---

## Track URLs

| # | Title | Lyrics | Watch |
|---|-------|--------|-------|
| 01 | Ain't No Grave | [Genius](https://genius.com/Johnny-cash-aint-no-grave-gonna-hold-this-body-down-lyrics) | [YouTube](https://www.youtube.com/watch?v=YU9BObi1GVw) |
| 02 | Danny Boy | [Genius](https://genius.com/Sinead-oconnor-danny-boy-lyrics) | [YouTube](https://www.youtube.com/watch?v=PweUGhCZNiM) |
| 03 | I'll Fly Away | [Bluegrass Lyrics](https://www.bluegrasslyrics.com/song/ill-fly-away/) | [YouTube](https://www.youtube.com/watch?v=1BPoMIQHwpo) |
| 04 | Ain't Gonna Cry | [Genius](https://genius.com/Larkin-poe-aint-gonna-cry-lyrics) | [YouTube](https://www.youtube.com/watch?v=UN20shzRLdg) |
| 05 | Wade in the Water | [Genius](https://genius.com/The-staple-singers-wade-in-the-water-lyrics) | [YouTube](https://www.youtube.com/watch?v=RRpzEnq14Hs) |
| 06 | One More Day | [Genius](https://genius.com/The-wood-brothers-one-more-day-lyrics) | [YouTube](https://www.youtube.com/watch?v=oVZYCtuFVf8) |
| 07 | You're Not Alone | [Genius](https://genius.com/Allison-russell-youre-not-alone-lyrics) | [YouTube](https://www.youtube.com/watch?v=YHzPT6bCGoQ) |
| 08 | Everlasting Arms | [Wikipedia](https://en.wikipedia.org/wiki/Leaning_on_the_Everlasting_Arms) | [YouTube](https://www.youtube.com/watch?v=i9YvB9FmR3E) |
| 09 | Hold On | [Genius](https://genius.com/Alabama-shakes-hold-on-lyrics) | [YouTube](https://www.youtube.com/watch?v=Le-3MIBxQTw) |
| 10 | When I Go | [tracygrammer.com](https://www.tracygrammer.com/when-i-go.html) | [YouTube](https://www.youtube.com/watch?v=Imf2GYV0xNo) |
| 11 | No Hard Feelings | [Genius](https://genius.com/The-avett-brothers-no-hard-feelings-lyrics) | [YouTube](https://www.youtube.com/watch?v=tFGs7HP15d4) |
| 12 | Sleeping in the Ground | [Genius](https://genius.com/Eric-clapton-sleeping-in-the-ground-lyrics) | [YouTube](https://www.youtube.com/watch?v=29d5ATUk1oU) |
| 13 | Up Above My Head | [Genius](https://genius.com/Sister-rosetta-tharpe-up-above-my-head-lyrics) | [YouTube](https://www.youtube.com/watch?v=fFe-B2v_Yk8) |
| 14 | Gone at Last | [Genius](https://genius.com/Paul-simon-gone-at-last-lyrics) | [YouTube](https://www.youtube.com/watch?v=kDp9yeSypp8) |
| 15 | Before I'm Old | [Genius](https://genius.com/Christone-kingfish-ingram-before-im-old-lyrics) | [YouTube](https://www.youtube.com/watch?v=6KWBJkv-8kM) |
| 16 | Enjoy Yourself | [Genius](https://genius.com/The-specials-enjoy-yourself-its-later-than-you-think-lyrics) | [YouTube](https://www.youtube.com/watch?v=rA2-6ZlOXeg) |
| 17 | One Last Drink | [Bandcamp](https://enterthehaggis.bandcamp.com/track/one-last-drink-2) | [YouTube](https://www.youtube.com/watch?v=YgHQZGHzEIs) |
| 18 | I'll Fly Away | [Bluegrass Lyrics](https://www.bluegrasslyrics.com/song/ill-fly-away/) | [YouTube](https://www.youtube.com/watch?v=hBd0FdBt0jk) |
| 19 | Lips As Cold As Diamond | [Genius](https://genius.com/Larkin-poe-lips-as-cold-as-diamond-lyrics) | [YouTube](https://www.youtube.com/watch?v=3dLAnJHiB0A) |
| 20 | Hallelujah | [Genius](https://genius.com/Leonard-cohen-hallelujah-lyrics) | [YouTube](https://www.youtube.com/watch?v=VJB29vBmbZ8) |
| 21 | Since the Last Time | [Genius](https://genius.com/Lyle-lovett-since-the-last-time-lyrics) | [YouTube](https://www.youtube.com/watch?v=l-FFN7Y4-nY) |
| 22 | Bright Blue Rose | [mary-black.net](https://www.mary-black.net/song.php?id=224) | [YouTube](https://www.youtube.com/watch?v=ZSw0nfJhKvI) |
| 23 | Take This Body Home | [Genius](https://genius.com/Rose-betts-take-this-body-home-lyrics) | [YouTube](https://www.youtube.com/watch?v=ePe0ftecG04) |
| 24 | First There Is Goodbye | [Local](talia-segal-first-there-is-goodbye-lyrics.html) | [YouTube](https://www.youtube.com/watch?v=Hy3gHPyLYBc) |
| 25 | The Parting Glass | [Genius](https://genius.com/Traditional-transcriptions-the-parting-glass-lyrics) | [YouTube](https://www.youtube.com/watch?v=0doPriEMi2o) |

---

## Adding a new track (e.g. inserting a new track 14)

This involves: tracks.tsv, the mp3 file, cover art, liner-notes.html, and the YouTube playlist. The ffmpeg script no longer needs manual editing — it reads tracks.tsv.

### 1. Edit tracks.tsv first

Add the new row at the correct position. Renumber all rows after the insertion point (increment `num`). Update `transition_type`/`transition_secs` for the track immediately before the new one if its outgoing transition changes. Set `chapter_break_after=yes` on the last track of whichever chapter is affected.

### 2. Rename existing mp3 files with reorder.sh

```bash
bash reorder.sh          # dry run — shows what would be renamed, touches nothing
bash reorder.sh --apply  # actually renames files to match tracks.tsv
```

This handles the cascade renaming (old 14→15, 15→16 etc.) automatically. Also rename cover art files manually — reorder.sh only handles mp3s.

### 3. Add the new track's mp3

Name it following the existing convention:
```
14. Artist Name - Track Title.mp3
```
No special characters except hyphens and spaces. Accented characters (é, í) are fine — they're already in the filenames.

### 3. Add cover art

- Square jpg, ideally 500×500px or larger (displays at 150px but keep originals hi-res)
- Name it: `14-track-slug.jpg` (lowercase, hyphens, no apostrophes or special chars)
- Drop it in `covers/`

**Important:** any mp3 with embedded cover art (Bandcamp downloads often have this) will break the crossfade step if it's one of the tracks involved in a crossfade. Strip it first:

```bash
ffmpeg -y -i "NN. Artist - Title.mp3" \
  -map 0:a -q:a 0 "NN. Artist - Title_clean.mp3" \
  && mv "NN. Artist - Title_clean.mp3" "NN. Artist - Title.mp3"
```

The Wood Brothers track 06 already has its cover art stripped for this reason.

If you can't find cover art, use a YouTube thumbnail as fallback:
```bash
curl -o covers/14-track-slug.jpg "https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg"
```
hqdefault is 480×360 (4:3) — it will letterbox at 150px square. Crop to square first if that bothers you.

### 4. Update liner-notes.html for the new track

Copy the HTML block from a nearby track as a template. Each track block looks like:

```html
<div class="track">
  <div class="track-header">
    <div class="track-num">14</div>
    <div class="track-info"><div class="track-info-text">
      <h2>Track Title</h2>
      <div class="performer">Artist Name</div>
      <div class="credits">
        Written by … &nbsp;·&nbsp; from <em>Album</em> (Year) &nbsp;·&nbsp;
        <a href="https://genius.com/…-lyrics" target="_blank">Lyrics</a> &nbsp;·&nbsp;
        <a href="https://www.youtube.com/watch?v=VIDEO_ID" target="_blank">Watch</a> &nbsp;·&nbsp;
        <a href="14.%20Artist%20-%20Title.mp3" download="14-title-artist.mp3">Download</a>
      </div>
      <div class="tags"><span class="tag">live</span></div>
      <!-- If performer is deceased: -->
      <div class="posthumous">† Name, YYYY–YYYY</div>
    </div><img class="track-art" src="covers/14-track-slug.jpg" alt="album art"></div>
  </div>
  <div class="track-body">
    <p>Your liner note here.</p>
    <!-- Optional: -->
    <p class="posthumous">Footnote about recording provenance.</p>
    <p class="lyric-pull">lyric line here</p>
  </div>
</div>
```

**CSS classes to know:**
- `.tag` — small caps label. Options include: `live`, `studio`, `traditional`, `alleluia` (purple), `Irish`, etc. Add new ones freely.
- `.posthumous` — small caps, faded. Used both in the header (for the † line) and in the body (for recording footnotes).
- `.lyric-pull` — rust left-border block. Goes at the bottom of `.track-body`, after any `.posthumous` footnote.
- `.chapter-break` — section divider with title and epigraph. Goes *between* `</div></div>` (end of one track) and `<div class="track">` (start of next).

### 5. Update the download href

The `href` in the Download link uses URL-encoded spaces (`%20`). The `download` attribute is the suggested save-as filename — use the short slug format: `14-title-artist.mp3`.

```html
<a href="14.%20Artist%20-%20Title.mp3" download="14-title-artist.mp3">Download</a>
```

### 6. Update tracks.tsv for transitions

You already did this in step 1, but double-check:
- The new track's `transition_type` and `transition_secs` (what follows it)
- The previous track's `transition_type` and `transition_secs` (now flows into the new track)

Transition conventions:
- Live→live within chapter: `xfade`, `1.5` (or `2.0` if the mood shift is larger)
- Live→studio or studio→live: `gap`, `2.0`–`2.5`
- Studio→studio: `gap`, `1.5`
- Chapter break: last track of chapter gets `chapter_break_after=yes`; assemble.sh always uses 3.5s for chapter gaps

### 7. Update the colophon stats

At the bottom of `liner-notes.html`, update:
- Total tracks (currently 25)
- Runtime — run `bash duration.sh` to get the new total
- Live/studio split
- Vocal gender breakdown if it changes

### 8. Update the YouTube playlist

Add the new video to the playlist at the correct position, and remove any displaced video if the slot was previously occupied. Playlist: https://www.youtube.com/playlist?list=PLJ7S-K0cjvGJHuI-kagxZUfN9fOaVV2ET

---

## Swapping out a track (same slot, different song)

Simpler than inserting — no renumbering needed.

1. Update `tracks.tsv` — change the filename, transition_type/secs if the live/studio character changed
2. Replace the mp3 file (keep the same `NN.` prefix, or rename and update tracks.tsv to match)
3. Replace the cover art in `covers/`
4. Update the track block in `liner-notes.html` — h2, performer, credits, tags, posthumous, note text, lyric pull
5. Update the colophon stats if anything changed — live/studio split, vocal gender breakdown, runtime (`bash duration.sh`)
6. Update the YouTube playlist if the video changed. Playlist: https://www.youtube.com/playlist?list=PLJ7S-K0cjvGJHuI-kagxZUfN9fOaVV2ET
7. Re-run `assemble.sh`

---

## Rebuilding the audio files

```bash
# From the folder containing all mp3s, tracks.tsv, and assemble.sh:
chmod +x assemble.sh
./assemble.sh
```

assemble.sh reads `tracks.tsv` for track order, filenames, and transitions — no hardcoded values. To check durations without rebuilding:

```bash
bash duration.sh
```

This rebuilds all six chapter files and the master. Takes a few minutes.
Intermediate `_ch*` temp files are cleaned up automatically.
If the script fails mid-run, delete any stray `_xfade_ch*.mp3` files before retrying.

Chapter files are independent — if you only change tracks in chapter 4, you could manually edit the script to run just that chapter's section and rebuild the master. But running the full script is safer.

---

## Lyrics links

Track 24 (Talia Segal) links to the local `talia-segal-first-there-is-goodbye-lyrics.html` page — see below for cleanup notes. All other lyrics links have been verified.

If a Genius page doesn't exist, search Genius directly — the URL isn't always predictable. For cover songs in particular, lyrics are often filed under the original artist rather than the performing artist, and the page title may include a longer subtitle (e.g. "Enjoy Yourself (It's Later Than You Think)" rather than just "Enjoy Yourself"). If Genius genuinely has nothing, options are: find another lyrics site, link directly to the YouTube watch URL instead, or drop the Lyrics link and leave Watch · Download.

---

## Track 24 — Talia Segal lyrics

`talia-segal-first-there-is-goodbye-lyrics.html` contains a Happyscribe transcript that needs cleanup. Unclear lines are marked in faded italic with `[?]`. To clean up:

1. Open the YouTube video: `https://www.youtube.com/watch?v=Hy3gHPyLYBc`
2. Edit the `.line.unclear` spans in the HTML — remove the `unclear` class once you're confident in the text
3. When all lines are clean, delete the `<div class="draft-notice-wrap">…</div>` block at the top of the page

---

## Guitar Gods and Goddesses and Me — photo archive

This is the Facebook photo album of gig photos, mostly featuring the red trilby hat and musicians met after shows. It feeds the slideshow.

**Facebook album:** "Guitar Gods and Goddesses and Me" (~80 photos, Oct 2021–present)
- FB album (not public): https://www.facebook.com/media/set/?set=a.10159009137456887

**Archive location:** Google Photos, burner account `redhat.bootlegs@gmail.com`
- Google album (public): https://photos.app.goo.gl/McCzxX53Kh6bHKEy7

**How it got there:** Facebook's Transfer tool (Settings → Your Facebook Information → Transfer a copy → Google Photos) was used to export the album. Facebook re-creates it as an album in Google Photos, preserving photo captions in each photo's description metadata (visible via the ℹ info panel in Google Photos).

**Auto-refresh:** Set up to sync monthly for 3 years from date of setup (March 2026). New photos added to the Facebook album will appear in Google Photos within a month automatically. No action needed until **March 2029**, at which point the sync will expire and will need to be re-authorized via the same Facebook Transfer tool if the album is still in use.

**Captions:** Each photo's Facebook caption (artist, date, venue) lands in the Google Photos description field — *not* displayed prominently, but accessible via the ℹ info icon on each photo. Don't rely on Google Takeout to preserve these; captions survive the Facebook→Google Photos transfer but are lost if you re-export via Takeout.

**To extract captions for slideshow use:** The bulk extraction (Google Photos API script → spreadsheet of filename + caption + date) only needs to be done once for the initial slideshow build. For new photos added after that, just check the Google album directly — you're not going to dozens of shows a month, so manually copying a caption or two is fine. The Google album is public and bookmarked above, so you don't need to log in to check it.

---

## One-timer scripts (one-timers/)

These scripts solved specific problems during setup and are kept for reference in case they're needed again, but shouldn't be part of the normal maintenance workflow.

### check-sample-rates.sh

Audits all 25 mp3 files and reports sample rate (Hz), channels (stereo/mono), and bitrate. Flags anything that isn't 44100 Hz stereo, because mismatches cause ffmpeg to re-encode everything and can cause subtle artifacts in the assembled file.

All tracks were confirmed 44100 Hz stereo when this was first run. **Run it again** if you add a new track and aren't sure of its specs, before running `assemble.sh`.

```bash
bash one-timers/check-sample-rates.sh
```

If a track fails, resample it:
```bash
ffmpeg -y -i "NN. original-name.mp3" -ar 44100 -ac 2 -q:a 0 "NN. original-name.mp3.tmp" \
  && mv "NN. original-name.mp3.tmp" "NN. original-name.mp3"
```

### fetch-covers.sh

Downloads front cover art for each track from MusicBrainz and the Cover Art Archive. Skips files already present and over 10KB. Already run — all covers are in `covers/`.

**Run it again** only if:
- The `covers/` folder is lost and needs to be rebuilt
- A new track is added and you want to try auto-fetching its art before falling back to a YouTube thumbnail

```bash
bash one-timers/fetch-covers.sh
```

Requires `curl` and `python3`. Rate-limited to ~1 req/sec to respect MusicBrainz policy. Some tracks (Playing for Change, Jamie Wilson, Talia Segal, boygenius+Ye Vagabonds, Sarah Rogo) aren't in MusicBrainz and needed manual art — those aren't in the script.

## The red trilby hat

The hat is the physical object that connects the liner notes, the slideshow, and the Guitar Gods and Goddesses and Me photo album. It's a red trilby with signatures from female musicians collected at gigs since 2023. The two living female artists from the playlist who haven't signed yet are Brittany Howard and Allison Krauss.

**Full signatories list (maintained in Google Docs):** https://docs.google.com/document/d/1haKMpfwPWosdPnZXBAAlLUzj3926hoTEH7icg6gTRA8/edit?usp=sharing

Notable connections to the playlist: Allison Russell (track 07), both Larkin Poe sisters — Rebecca and Megan (tracks 04 and 19), Rose Baldino and Caroline Browning of Enter the Haggis (track 17), and Talia Segal (track 24, ✝ 2025).

The icon file (`red_hat_icon.png`) must be delivered as a ZIP to preserve the alpha channel — drag-and-drop flattens it to RGB and destroys the outline. The transparent PNG with outline intact is in `outputs/red_hat_icon.png`.

---

## Rebuilding the slideshow (slides-songs-for-my-funeral.pptx)

The slideshow is generated by `build-slides.js` using [PptxGenJS](https://gitbrent.github.io/PptxGenJS/). To rebuild after any change to track data, lyric pulls, format tags, or layout:

```bash
node build-slides.js
```

This writes `slides-songs-for-my-funeral.pptx` to the same directory. **Use PowerPoint to open it** — Google Slides mangles the font and layout.

### Directory layout expected by build-slides.js

```
your-folder/
├── build-slides.js
├── red_hat_icon.png        ← must be the RGBA version (deliver as ZIP to preserve alpha)
└── covers/
    ├── 01-aint-no-grave.jpg
    ├── 02-danny-boy.jpg
    └── ... (25 cover images)
```

### Node.js installation (macOS)

Node is not included with macOS. Install it from the command line:

```bash
sudo installer -pkg ~/Downloads/node-v22*.pkg -target /
```

Download the pkg first from [nodejs.org](https://nodejs.org) — choose the **macOS ARM64** installer. The GUI installer may fail silently; the command above works reliably.

Verify:
```bash
node --version   # should be v22 or higher
npm --version
```

Then install PptxGenJS locally in the project folder (only needed once):
```bash
cd path/to/songs\ for\ my\ funeral
npm install pptxgenjs
```

The script was built and tested with Node v22 and pptxgenjs v4.0.1.

---

## Color palette (liner-notes.html)

| Variable | Light | Dark | Used for |
|----------|-------|------|---------|
| `--ink` | `#1a1714` | `#e8e0d0` | Headings, track titles |
| `--paper` | `#f5f0e8` | `#1c1713` | Background |
| `--body` | `#3a3530` | `#ccc4b4` | Body paragraph text |
| `--rust` | `#8b4a2a` | `#c47a4a` | Links, lyric pull border, tags |
| `--fade` | `#706860` | `#9a9088` | Performer names, credits, footnotes |
| `--rule` | `#c8bfaa` | `#3a332c` | Horizontal rules, borders |

All pairs pass WCAG AA contrast (4.5:1) against their respective backgrounds.
Dark mode activates automatically via `prefers-color-scheme: dark`.
