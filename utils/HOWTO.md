# Songs for my Funeral — Maintenance Notes

*For future me, when the playlist needs work.*

---

## YouTube API credentials

The live-shows scripts use two separate Google credentials that must be kept **out of git**. The `.gitignore` excludes them, but you need to recreate them locally after a fresh clone or if they're ever deleted.

### What you need and where it lives

| File | Used by | How to get it |
|------|---------|---------------|
| `live-shows/.env` | both scripts | copy `.env.example`, fill in values |
| `live-shows/client_secrets.json` | `youtube_create_playlists.py` only | download from Google Cloud Console |
| `live-shows/token.json` | `youtube_create_playlists.py` only | auto-generated on first auth run |

### Step 0 — Set up the Python virtual environment (first time only)

The scripts require a few Python packages. Because macOS Homebrew Python 3.14+ refuses system-wide pip installs, use a virtual environment instead. This only needs to be done once per machine, after cloning.

```bash
cd ~/github/hm/songs-for-my-funeral/live-shows
python3 -m venv .venv
source .venv/bin/activate
pip install python-dotenv google-api-python-client google-auth-oauthlib requests beautifulsoup4
```

The `.venv/` folder is gitignored. **Every time you open a new terminal to run these scripts**, activate the venv first:

```bash
source ~/github/hm/songs-for-my-funeral/live-shows/.venv/bin/activate
```

Your prompt will show `(.venv)` when it's active. You only need to `pip install` once — after that, just activate and run.

### Step 1 — Create the .env file

```bash
cd ~/github/hm/songs-for-my-funeral/live-shows
cp .env.example .env
```

Then open `.env` and fill in `YOUTUBE_API_KEY` (see Step 2). Leave the other two lines at their defaults.

### Step 2 — Get or recreate the YouTube Data API key

This key is read-only and used only by `youtube_fetch.py`.

1. Go to https://console.cloud.google.com/apis/credentials?project=dan2bit-youtub-channel
2. If a key named something like "YouTube Data API key" already exists, click it to view and copy the key value
3. If no key exists (or you want a fresh one): click **+ Create Credentials** → **API key** → copy it
4. Paste the key into `live-shows/.env` as the value for `YOUTUBE_API_KEY`

Optionally restrict the key: click the key → **API restrictions** → restrict to **YouTube Data API v3**. This limits blast radius if it ever leaks.

### Step 3 — Get or recreate client_secrets.json (OAuth)

This file is used by `youtube_create_playlists.py` for write access (creating playlists).

1. Go to https://console.cloud.google.com/apis/credentials?project=dan2bit-youtub-channel
2. Under **OAuth 2.0 Client IDs**, find the Desktop client (probably named something like "Desktop client 1" or "dan2bit playlist tool")
3. Click the download icon (↓) on the right side of that row
4. Save the downloaded file as `client_secrets.json` in `live-shows/`

If no OAuth client exists, create one: **+ Create Credentials** → **OAuth client ID** → Application type: **Desktop app** → name it anything → click **Create** → download the JSON.

If prompted to configure a consent screen first: go to https://console.cloud.google.com/apis/auth/consent?project=dan2bit-youtub-channel, fill in App name and your email, click through Scopes without adding anything, save. Then come back and create the OAuth client ID.

### Step 3a — Add yourself as a test user (required for OAuth)

Because the app is in "Testing" mode, Google will block the auth flow with a 403 unless your account is explicitly listed as a test user.

1. Go to https://console.cloud.google.com/auth/audience?project=dan2bit-youtub-channel
2. Under **Test users**, click **+ Add Users**
3. Enter `dan2bit@gmail.com` and save (this is the account that owns the YouTube channel)

You only need to do this once. If you ever see a 403 "access blocked" error during `--auth-only`, come back here and verify the account is still listed.

### Step 4 — Generate token.json (first run only)

`token.json` is auto-generated the first time you authenticate. You don't create it manually.

```bash
cd ~/github/hm/songs-for-my-funeral/live-shows
source .venv/bin/activate
python3 youtube_create_playlists.py --auth-only
```

This opens a browser window. **Sign in as `dan2bit@gmail.com`** — that is the account that owns the bootleg YouTube channel. Signing in with any other account will produce a `401 youtubeSignupRequired` error when you try to create playlists.

Once authorized, `token.json` is written to `live-shows/`. Subsequent runs reuse it silently (it auto-refreshes).

**If you see `401 Unauthorized / youtubeSignupRequired`** when running without `--dry-run`:
```bash
rm ~/github/hm/songs-for-my-funeral/live-shows/token.json
python3 youtube_create_playlists.py --auth-only   # re-authorize as dan2bit@gmail.com
```

### Verify everything is working

```bash
cd ~/github/hm/songs-for-my-funeral/live-shows
source .venv/bin/activate

# Test the API key (youtube_fetch.py)
python3 youtube_fetch.py

# Test OAuth with a date that already has a playlist — confirms auth without creating a duplicate
python3 youtube_create_playlists.py --dry-run --date 2023-03-07
```

### After a fresh clone

```bash
cd ~/github/hm/songs-for-my-funeral/live-shows
python3 -m venv .venv
source .venv/bin/activate
pip install python-dotenv google-api-python-client google-auth-oauthlib requests beautifulsoup4
cp .env.example .env
# Fill in YOUTUBE_API_KEY in .env
# Download client_secrets.json from Google Cloud Console
# Verify dan2bit@gmail.com is listed at https://console.cloud.google.com/auth/audience?project=dan2bit-youtub-channel
python3 youtube_create_playlists.py --auth-only   # sign in as dan2bit@gmail.com
```

---

## Project layout

### Repository (`~/github/hm/songs-for-my-funeral/`)

This is where all code, scripts, and text assets live. Clone once and keep it here.

```
songs-for-my-funeral/
├── index.html                          ← public website (GitHub Pages)
├── talia-segal-first-there-is-goodbye-lyrics.html
├── red_hat_icon.ico / .png / _tiny.png
├── package.json                        ← Node dependencies (pptxgenjs)
├── run.sh                              ← build + sync script (see below)
├── covers/                             ← album art, one jpg per track
├── tracks/                             ← symlink → Google Drive/tracks/
│   ├── tracks.tsv                      ← source of truth for track order/transitions
│   └── 01. Artist - Title.mp3 … (26 tracks)
├── output/                             ← symlink → Google Drive/output/
│   ├── chapter-01-*.mp3 … (6 chapters)
│   └── songs-for-my-funeral.mp3
├── photos/                             ← placeholder for slideshow photos
├── website/                            ← placeholder for website mirror/backup
├── ppt/
│   ├── build-slides.js                 ← generates the PPTX
│   └── HOWTO-slideshow.md
└── utils/
    ├── HOWTO.md                        ← this file
    ├── assemble.sh                     ← ffmpeg assembly script
    ├── duration.sh                     ← reports track/chapter/total runtime
    ├── reorder.pl                      ← renames mp3s + covers after reordering
    └── one-timers/
        ├── check-sample-rates.sh
        └── fetch-covers.sh
```

### Google Drive (`~/Library/CloudStorage/GoogleDrive-redhat.bootlegs@gmail.com/My Drive/songs for my funeral/`)

Holds the large binary files that don't belong in git:

```
songs for my funeral/
├── covers/                             ← mirrors repo covers/ (source of truth is repo)
├── tracks/                             ← 26 source mp3s + tracks.tsv (source of truth)
├── output/                             ← assembled chapter + master mp3s (source of truth)
├── photos/                             ← slideshow photos (source of truth)
├── website/                            ← website mirror/backup
├── misc/                               ← youtubelinks.txt, First There Is Goodbye.txt
├── one-timers/                         ← check-sample-rates.sh, fetch-covers.sh
└── slides-songs-for-my-funeral.pptx   ← generated PPTX (source of truth)
```

`tracks/` and `output/` in the repo are symlinks into Google Drive, so scripts that write there go directly to Drive when it's mounted.

### Ownership model

| Asset | Source of truth | In git? |
|---|---|---|
| Code and scripts | repo | ✅ |
| Cover art JPGs | repo (`covers/`) | ✅ |
| `index.html`, HTML pages | repo | ✅ |
| `tracks.tsv` | repo (`tracks/`) | ✅ |
| `package.json` | repo | ✅ |
| Individual track mp3s | Drive (`tracks/`) | ❌ gitignored |
| Assembled output mp3s | Drive (`output/`) | ❌ gitignored |
| PPTX slideshow | Drive root | ❌ gitignored |
| Slideshow photos | Drive (`photos/`) | ❌ |
| `.env` | local only | ❌ gitignored |
| `client_secrets.json` | local only | ❌ gitignored |
| `token.json` | local only | ❌ gitignored |
| `.venv/` | local only | ❌ gitignored |

---

## run.sh — build and sync

`run.sh` in the repo root is the main entry point for rebuilding outputs. Run it from the repo root:

```bash
./run.sh assemble   # run assemble.sh, copy chapter + master mp3s to Drive/output/
./run.sh slides     # run build-slides.js, copy pptx to Drive root
./run.sh all        # both
```

**If Google Drive is mounted:** outputs are copied directly to Drive after building.

**If Google Drive is disconnected:** the script warns you and saves outputs locally to `output/` or `ppt/`. Copy them to Drive manually when it reconnects.

The Drive path is hardcoded in `run.sh`:
```
~/Library/CloudStorage/GoogleDrive-redhat.bootlegs@gmail.com/My Drive/songs for my funeral
```
If this ever changes (e.g. after reinstalling Drive for Desktop or switching accounts), update `GDRIVE_ROOT` near the top of `run.sh`.

---

## tracks.tsv — the source of truth

`tracks/tracks.tsv` is a tab-separated file that drives `assemble.sh`, `reorder.pl`, and `duration.sh`. It lives in `tracks/` alongside the mp3s because `assemble.sh` reads it from whatever directory it's run in. Edit it first whenever the playlist changes structurally.

**Columns:**

| Column | Values | Notes |
|--------|--------|-------|
| `num` | `01`–`26` | Track number, zero-padded. Must be unique and sequential. |
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
| 18 | Five More Minutes | The War & Treaty | live | 4 | |
| 19 | I'll Fly Away | PHJB & Del McCoury Band | live | 5 | Letterman 2011. Trimmed: 23s from start, 19s from end |
| 20 | Lips As Cold As Diamond | Larkin Poe | studio | 5 | |
| 21 | Hallelujah | Sarah Rogo | live | 5 | Haus Music Production, LA, April 2020 |
| 22 | Since the Last Time | Lyle Lovett | live | 5 | SWR Studio 5, Baden-Baden, Nov 1992 |
| 23 | Bright Blue Rose | Mary Black | live | 5 | RTÉ Late Late Show 1991 |
| 24 | Take This Body Home | Rose Betts | live | 6 | |
| 25 | First There Is Goodbye | Talia Segal | studio | 6 | Lyrics need cleanup against recording |
| 26 | The Parting Glass | boygenius & Ye Vagabonds | studio | 6 | Released July 2023 |

**Chapters:**
1. I Am Where I'm Meant to Be (tracks 1–3)
2. You'll Be Okay (Grief Sucks) (tracks 4–9)
3. Don't Worry About Me (tracks 10–11)
4. You're Still in the Pink (tracks 12–18)
5. But Before We Part (tracks 19–23)
6. Go in Good Graces (tracks 24–26)

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
| 18 | Five More Minutes | [Genius](https://genius.com/The-war-and-treaty-five-more-minutes-lyrics) | [YouTube](https://www.youtube.com/watch?v=5K9kiQkYWqY) |
| 19 | I'll Fly Away | [Bluegrass Lyrics](https://www.bluegrasslyrics.com/song/ill-fly-away/) | [YouTube](https://www.youtube.com/watch?v=hBd0FdBt0jk) |
| 20 | Lips As Cold As Diamond | [Genius](https://genius.com/Larkin-poe-lips-as-cold-as-diamond-lyrics) | [YouTube](https://www.youtube.com/watch?v=3dLAnJHiB0A) |
| 21 | Hallelujah | [Genius](https://genius.com/Leonard-cohen-hallelujah-lyrics) | [YouTube](https://www.youtube.com/watch?v=VJB29vBmbZ8) |
| 22 | Since the Last Time | [Genius](https://genius.com/Lyle-lovett-since-the-last-time-lyrics) | [YouTube](https://www.youtube.com/watch?v=l-FFN7Y4-nY) |
| 23 | Bright Blue Rose | [mary-black.net](https://www.mary-black.net/song.php?id=224) | [YouTube](https://www.youtube.com/watch?v=ZSw0nfJhKvI) |
| 24 | Take This Body Home | [Genius](https://genius.com/Rose-betts-take-this-body-home-lyrics) | [YouTube](https://www.youtube.com/watch?v=ePe0ftecG04) |
| 25 | First There Is Goodbye | [Local](talia-segal-first-there-is-goodbye-lyrics.html) | [YouTube](https://www.youtube.com/watch?v=Hy3gHPyLYBc) |
| 26 | The Parting Glass | [Genius](https://genius.com/Traditional-transcriptions-the-parting-glass-lyrics) | [YouTube](https://www.youtube.com/watch?v=0doPriEMi2o) |

---

## Adding a new track (e.g. inserting a new track 14)

This involves: tracks.tsv, the mp3 file, cover art, index.html, and the YouTube playlist. The ffmpeg script no longer needs manual editing — it reads tracks.tsv.

### 1. Edit tracks.tsv first

Add the new row at the correct position in `tracks/tracks.tsv`. Renumber all rows after the insertion point (increment `num`). Update `transition_type`/`transition_secs` for the track immediately before the new one if its outgoing transition changes. Set `chapter_break_after=yes` on the last track of whichever chapter is affected.

### 2. Rename existing mp3 and cover files with reorder.pl

```bash
cd ~/github/hm/songs-for-my-funeral
perl utils/reorder.pl          # dry run — shows what would be renamed, touches nothing
perl utils/reorder.pl --apply  # actually renames files to match tracks.tsv
```

This handles the cascade renaming (old 14→15, 15→16 etc.) automatically for both mp3s and cover art.

**Order of operations matters:** run reorder.pl *after* adding the new track's mp3 to disk but *before* running assemble.sh. The script keys on track name (not number), so it correctly finds files regardless of whether the tsv filename column has been updated yet.

### 3. Add the new track's mp3

Drop it in `tracks/` (which is a symlink to Drive). Name it following the existing convention:
```
14. Artist Name - Track Title.mp3
```
No special characters except hyphens and spaces. Accented characters (é, í) are fine — they're already in the filenames.

### 4. Add cover art

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

### 5. Update index.html for the new track

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
        <a href="https://www.youtube.com/watch?v=VIDEO_ID" target="_blank">Watch</a>
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

Note: `index.html` is the public website — it has no Download links (mp3s are not in the repo). Don't add them here.

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

At the bottom of `index.html`, update:
- Total tracks (currently 26)
- Runtime — run `bash utils/duration.sh` from the repo root to get the new total
- Live/studio split
- Vocal gender breakdown if it changes

### 8. Rebuild the audio

```bash
./run.sh assemble
```

### 9. Rebuild the slideshow

```bash
./run.sh slides
```

### 10. Update the YouTube playlist

Add the new video to the playlist at the correct position, and remove any displaced video if the slot was previously occupied. Playlist: https://www.youtube.com/playlist?list=PLJ7S-K0cjvGJHuI-kagxZUfN9fOaVV2ET

### 11. Commit and push

```bash
cd ~/github/hm/songs-for-my-funeral
git add covers/14-track-slug.jpg tracks/tracks.tsv index.html
git commit -m "Add track 14: Artist - Title"
git push
```

---

## Swapping out a track (same slot, different song)

Simpler than inserting — no renumbering needed.

1. Update `tracks/tracks.tsv` — change the filename, transition_type/secs if the live/studio character changed
2. Replace the mp3 file in `tracks/` (keep the same `NN.` prefix, or rename and update tracks.tsv to match)
3. Replace the cover art in `covers/`
4. Update the track block in `index.html` — h2, performer, credits, tags, posthumous, note text, lyric pull
5. Update the colophon stats if anything changed — live/studio split, vocal gender breakdown, runtime (`bash utils/duration.sh`)
6. Update the YouTube playlist if the video changed. Playlist: https://www.youtube.com/playlist?list=PLJ7S-K0cjvGJHuI-kagxZUfN9fOaVV2ET
7. Run `./run.sh assemble` and `./run.sh slides`
8. Commit and push

---

## Rebuilding the audio files

```bash
./run.sh assemble
```

This runs `utils/assemble.sh` from the `tracks/` directory (where the mp3s and tracks.tsv live), then copies the assembled chapter and master mp3s to Drive's `output/` folder.

To check durations without rebuilding:

```bash
cd ~/github/hm/songs-for-my-funeral/tracks
bash ../utils/duration.sh
```

assemble.sh reads `tracks.tsv` for track order, filenames, and transitions. The chapter and master *expected* durations used for the ✓/⚠ check are hardcoded in assemble.sh — update them manually when tracks are added or removed.

This rebuilds all six chapter files and the master. Takes a few minutes.
Intermediate `_ch*` temp files are cleaned up automatically.
If the script fails mid-run, delete any stray `_xfade_ch*.mp3` files from `tracks/` before retrying.

Chapter files are independent — if you only change tracks in chapter 4, you could manually edit the script to run just that chapter's section and rebuild the master. But running the full script is safer.

The ✓ check allows ~10s of drift per chapter — small overages are normal due to ffmpeg's crossfade and gap rounding. If a chapter shows ⚠, first verify the track count is correct, then update the expected value in assemble.sh to match actual output.

---

## Rebuilding the slideshow (slides-songs-for-my-funeral.pptx)

```bash
./run.sh slides
```

This runs `ppt/build-slides.js` from the repo root (it needs `red_hat_icon.png` and `covers/` there), then copies the output PPTX to Drive's root folder.

**Use PowerPoint to open the PPTX** — Google Slides mangles the font and layout.

See `ppt/HOWTO-slideshow.md` for full slideshow documentation.

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

Then install dependencies (only needed once, from repo root):
```bash
cd ~/github/hm/songs-for-my-funeral
npm install
```

The script was built and tested with Node v22 and pptxgenjs v4.0.1. `run.sh` will auto-run `npm install` if `node_modules/` is missing.

---

## Lyrics links

Track 25 (Talia Segal) links to the local `talia-segal-first-there-is-goodbye-lyrics.html` page. All lyrics links have been verified.

If a Genius page doesn't exist, search Genius directly — the URL isn't always predictable. For cover songs in particular, lyrics are often filed under the original artist rather than the performing artist, and the page title may include a longer subtitle (e.g. "Enjoy Yourself (It's Later Than You Think)" rather than just "Enjoy Yourself"). If Genius genuinely has nothing, options are: find another lyrics site, link directly to the YouTube watch URL instead, or drop the Lyrics link and leave Watch only.

---

## Track 25 — Talia Segal lyrics

`talia-segal-first-there-is-goodbye-lyrics.html` is a complete, clean transcript verified against the recording. No outstanding issues.

---

## Public website

The liner notes are hosted at:

**https://dan2bit.github.io/songs-for-my-funeral/index.html**

`index.html` is the public version — it has no Download links (mp3s are not in the repo). The YouTube playlist link is in the header.

The GitHub repo also contains `talia-segal-first-there-is-goodbye-lyrics.html`, `red_hat_icon.png`, `red_hat_icon.ico`, `red_hat_icon_tiny.png`, and the `covers/` folder. The mp3s, PPTX, and any private liner-notes are kept in Google Drive only.

To update the public site after editing `index.html`: commit and push. GitHub Pages deploys automatically.

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

**Photos on Drive:** Slideshow photos (selected/cropped from the Google Photos album) live in `Drive/photos/`.

---

## One-timer scripts (utils/one-timers/)

These scripts solved specific problems during setup and are kept for reference in case they're needed again, but shouldn't be part of the normal maintenance workflow.

### check-sample-rates.sh

Audits all mp3 files and reports sample rate (Hz), channels (stereo/mono), and bitrate. Flags anything that isn't 44100 Hz stereo, because mismatches cause ffmpeg to re-encode everything and can cause subtle artifacts in the assembled file.

All tracks were confirmed 44100 Hz stereo when this was first run. **Run it again** if you add a new track and aren't sure of its specs, before running `assemble.sh`.

```bash
cd ~/github/hm/songs-for-my-funeral/tracks
bash ../utils/one-timers/check-sample-rates.sh
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
cd ~/github/hm/songs-for-my-funeral
bash utils/one-timers/fetch-covers.sh
```

Requires `curl` and `python3`. Rate-limited to ~1 req/sec to respect MusicBrainz policy. Some tracks (Playing for Change, Jamie Wilson, Talia Segal, boygenius+Ye Vagabonds, Sarah Rogo) aren't in MusicBrainz and needed manual art — those aren't in the script.

---

## The red trilby hat

The hat is the physical object that connects the liner notes, the slideshow, and the Guitar Gods and Goddesses and Me photo album. It's a red trilby with signatures from female musicians collected at gigs since 2023. The two living female artists from the playlist who haven't signed yet are Brittany Howard and Allison Krauss.

**Full signatories list (maintained in Google Docs):** https://docs.google.com/document/d/1haKMpfwPWosdPnZXBAAlLUzj3926hoTEH7icg6gTRA8/edit?usp=sharing

Notable connections to the playlist: Allison Russell (track 07), both Larkin Poe sisters — Rebecca and Megan (tracks 04 and 20), Rose Baldino and Caroline Browning of Enter the Haggis (track 17), and Talia Segal (track 25, ✝ 2025).

The icon file (`red_hat_icon.png`) must be delivered as a ZIP to preserve the alpha channel — drag-and-drop flattens it to RGB and destroys the outline. The transparent PNG with outline intact is in the repo root.

---

## Color palette (index.html)

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
