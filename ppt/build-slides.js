const pptxgen = require("pptxgenjs");
const fs = require('fs');
const path = require('path');

// ⚠️  MUST BE RUN FROM THE REPO ROOT (songs-for-my-funeral/):
//     cd ~/github/hm/songs-for-my-funeral
//     node ppt/build-slides.js
//   OR simply:
//     ./run.sh slides
// Expects: red_hat_icon.png and covers/ in the repo root.

// ─────────────────────────────────────────────────────
// PALETTE  (dark mode, screen-first)
// ─────────────────────────────────────────────────────
const C = {
  bg:       "1C1713",
  ink:      "E8E0D0",
  body:     "CCC4B4",
  fade:     "9A9088",
  rust:     "C47A4A",
  rule:     "3A332C",
  chapterBg:"221E19",
  black:    "000000",
};

// ─────────────────────────────────────────────────────
// IMAGE LOADER
// Pre-encode all images as base64 data: strings at startup.
// This is the reliable approach with pptxgenjs — path: resolution
// is fragile across symlinks and working directories.
//
// - Placeholder PNGs: use __dirname (relative to this script in ppt/)
// - Hat icon + covers: use process.cwd() (must be repo root)
// ─────────────────────────────────────────────────────
function loadImage(filePath) {
  try {
    const buf = fs.readFileSync(filePath);
    const ext = path.extname(filePath).slice(1).toLowerCase();
    const mime = ext === 'jpg' ? 'jpeg' : ext;
    return `image/${mime};base64,${buf.toString('base64')}`;
  } catch (e) {
    return null;
  }
}

// Placeholders — resolve via __dirname so they work regardless of cwd
const PLACEHOLDER_LANDSCAPE = loadImage(path.join(__dirname, 'placeholder-landscape.png'));
const PLACEHOLDER_PORTRAIT  = loadImage(path.join(__dirname, 'placeholder-portrait.png'));

if (!PLACEHOLDER_LANDSCAPE) { console.error("ERROR: ppt/placeholder-landscape.png not found"); process.exit(1); }
if (!PLACEHOLDER_PORTRAIT)  { console.error("ERROR: ppt/placeholder-portrait.png not found");  process.exit(1); }

// Hat icon — must be in repo root (process.cwd())
const HAT_DATA = loadImage('red_hat_icon.png');
if (!HAT_DATA) { console.error("ERROR: red_hat_icon.png not found in repo root"); process.exit(1); }

// Cover images — pre-encode all at startup, log warnings for any missing
const tracks = [
  { num:  1, title: "Ain't No Grave",           performer: "Jamie Wilson",                         duration: 291, format: "live · traditional",              lyricPull: "Gabriel don't you blow that trumpet / until you hear from me.",                                                                      cover: "01-aint-no-grave.jpg" },
  { num:  2, title: "Danny Boy",                performer: "Sinéad O'Connor",                      duration: 288, format: "live · Irish",                     lyricPull: "And I shall hear, though soft you tread above me / And all my grave will warmer, sweeter be",                                       cover: "02-danny-boy.jpg" },
  { num:  3, title: "I'll Fly Away",            performer: "Alison Krauss",                        duration: 243, format: "studio · traditional",             lyricPull: "No more cold iron shackles on my feet / I'll fly away.",                                                                           cover: "03-ill-fly-away.jpg" },
  { num:  4, title: "Ain't Gonna Cry",          performer: "Larkin Poe",                           duration: 215, format: "live · BBC session",               lyricPull: "I don't know how to pray / I sing hallelujah anyway.",                                                                             cover: "04-aint-gonna-cry.jpg" },
  { num:  5, title: "Wade in the Water",        performer: "Sweet Honey in the Rock",              duration: 338, format: "live · a cappella",                lyricPull: "See those people dressed in black, they come a long way and they ain't turning back",                                              cover: "05-wade-in-the-water.jpg" },
  { num:  6, title: "One More Day",             performer: "The Wood Brothers",                    duration: 345, format: "live",                             lyricPull: "I heard you say / the world don't owe you a thing.",                                                                               cover: "06-one-more-day.jpg" },
  { num:  7, title: "You're Not Alone",         performer: "Allison Russell ft. Brandi Carlile",   duration: 308, format: "studio",                          lyricPull: "All the ones who came before you, their strength is yours now / You're not alone",                                                 cover: "07-youre-not-alone.jpg" },
  { num:  8, title: "Everlasting Arms",         performer: "Playing for Change ft. Dr. John",      duration: 295, format: "studio · Song Around the World",  lyricPull: "You can lean on me stranger, I believe you've carried too long / It's such a long, long way, back home",                          cover: "08-everlasting-arms.jpg" },
  { num:  9, title: "Hold On",                  performer: "Alabama Shakes",                       duration: 231, format: "live · live in studio",            lyricPull: "So, bless my heart and bless my mind / I got so much to do, I ain't got much time",                                              cover: "09-hold-on.jpg" },
  { num: 10, title: "When I Go",                performer: "Dave Carter & Tracy Grammer",          duration: 428, format: "live",                             lyricPull: "when I go, I will go like water / when I go, I will go like fire",                                                                 cover: "10-when-i-go.jpg" },
  { num: 11, title: "No Hard Feelings",         performer: "The Avett Brothers",                   duration: 324, format: "studio",                          lyricPull: "and it's ash and dust for cash and lust, and it's just hallelujah / and love in thoughts and love in the words",                  cover: "11-no-hard-feelings.jpg" },
  { num: 12, title: "Sleeping in the Ground",   performer: "Clapton & Winwood",                    duration: 290, format: "live",                             lyricPull: "The things you do to hurt me / don't seem to matter to me anymore",                                                               cover: "12-sleeping-in-the-ground.jpg" },
  { num: 13, title: "Up Above My Head",         performer: "Sister Rosetta Tharpe & Marie Knight", duration: 151, format: "studio · 1947",                   lyricPull: "You know all in my heart, music everywhere / All in my soul, it makes me whole.",                                                  cover: "13-up-above-my-head.jpg" },
  { num: 14, title: "Gone at Last",             performer: "Paul Simon & Phoebe Snow",             duration: 219, format: "studio",                          lyricPull: "Somebody will come and lift you higher / and your burdens will be shared",                                                          cover: "14-gone-at-last.jpg" },
  { num: 15, title: "Before I'm Old",           performer: "Christone 'Kingfish' Ingram",          duration: 255, format: "studio",                          lyricPull: "People say I got an old soul / and I ain't even twenty-one",                                                                        cover: "15-before-im-old.jpg" },
  { num: 16, title: "Enjoy Yourself",           performer: "The Specials",                         duration: 239, format: "live",                             lyricPull: "Enjoy yourself, enjoy yourself, it's later than you think.",                                                                      cover: "16-enjoy-yourself.jpg" },
  { num: 17, title: "One Last Drink",           performer: "Enter the Haggis",                     duration: 228, format: "studio · Celtic rock",             lyricPull: "I've had a life that's full, everyone's been good to me / so fire up that fiddle boy, and give me one last drink.",              cover: "17-one-last-drink.jpg" },
  { num: 18, title: "Five More Minutes",        performer: "The War & Treaty",                     duration: 314, format: "live · live in concert",           lyricPull: "We've got all night, so please forget / about tomorrow",                                                                          cover: "18-five-more-minutes.jpg" },
  { num: 19, title: "I'll Fly Away",            performer: "Preservation Hall Jazz Band\n& Del McCoury Band", duration: 228, format: "live · live in studio", lyricPull: "",                                                                                                                                cover: "19-ill-fly-away-phjb.jpg" },
  { num: 20, title: "Lips As Cold As Diamond",  performer: "Larkin Poe",                           duration: 222, format: "studio",                          lyricPull: "tonight I go to meet my maker / her sweet love will be my undertaker.",                                                            cover: "20-lips-as-cold.jpg" },
  { num: 21, title: "Hallelujah",               performer: "Sarah Rogo",                           duration: 266, format: "live · live in studio",            lyricPull: "I'll stand before the Lord of song / with nothing on my tongue but hallelujah",                                                  cover: "21-hallelujah.jpg" },
  { num: 22, title: "Since the Last Time",      performer: "Lyle Lovett",                          duration: 430, format: "live · alleluia",                  lyricPull: "I went to a funeral, Lord it made me happy / Seeing all those people I ain't seen since the last time somebody died.",           cover: "22-since-the-last-time.jpg" },
  { num: 23, title: "Bright Blue Rose",         performer: "Mary Black",                           duration: 232, format: "live · live in studio · Irish",    lyricPull: "One bright blue rose outlives all those, two thousand years and still it goes / to ponder his death and his life eternally.",   cover: "23-bright-blue-rose.jpg" },
  { num: 24, title: "Take This Body Home",      performer: "Rose Betts",                           duration: 219, format: "live · live session",              lyricPull: "May all your wounds find their healing / In the last and enduring sleep.",                                                        cover: "24-take-this-body-home.jpg" },
  { num: 25, title: "First There Is Goodbye",   performer: "Talia Segal",                          duration: 186, format: "studio",                          lyricPull: "we'll fill the empty spaces / with the ghost of you and I",                                                                        cover: "25-first-there-is-goodbye.jpg" },
  { num: 26, title: "The Parting Glass",        performer: "boygenius & Ye Vagabonds",             duration: 251, format: "studio · Irish",                   lyricPull: "But since it fell unto my lot, that I should rise and you should not / I gently rise and softly call, good night and joy be to you all.", cover: "26-the-parting-glass.jpg" },
];

// Pre-encode cover images
tracks.forEach(t => {
  t.coverData = loadImage(`covers/${t.cover}`);
  if (!t.coverData) console.warn(`  ⚠  cover missing: covers/${t.cover}`);
});

// ─────────────────────────────────────────────────────
// CHAPTER DATA
// ─────────────────────────────────────────────────────
const chapters = [
  { num: 1, title: "I Am Where I'm Meant to Be",  epigraph: "kneel and say an Ave there for me",                               tracks: [1,2,3]        },
  { num: 2, title: "You'll Be Okay (Grief Sucks)", epigraph: "I don't know how to pray / I say 'Alleluia' anyway",              tracks: [4,5,6,7,8,9]  },
  { num: 3, title: "Don't Worry About Me",          epigraph: "…straight to the light, / holding the love I've known in my life", tracks: [10,11]       },
  { num: 4, title: "You're Still in the Pink",      epigraph: "so fire up that fiddle boy, / and give me one last drink",        tracks: [12,13,14,15,16,17,18] },
  { num: 5, title: "But Before We Part",            epigraph: "preacher says he wants some more of that / alleluia",             tracks: [19,20,21,22,23] },
  { num: 6, title: "Go in Good Graces",             epigraph: "Good night and joy be to you all",                               tracks: [24,25,26]     },
];

// Timing helper
function timingNote(track) {
  const secs = track.duration;
  const mins = Math.floor(secs / 60);
  const s = secs % 60;
  return `${mins}:${String(s).padStart(2,'0')} · ${Math.floor(secs/8)} photos @ 8s each · range: ${Math.floor(secs/10)}–${Math.floor(secs/6)} photos (10s–6s per slide)`;
}

// ─────────────────────────────────────────────────────
// PRESENTATION SETUP
// ─────────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "Songs for my Funeral";
pres.author = "liner notes";

const W = 10;
const H = 5.625;

// ─────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────
function addRule(slide, x, y, w) {
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h: 0.02,
    fill: { color: C.rust },
    line: { color: C.rust, width: 0 },
  });
}

function addHatProminent(slide, y) {
  const SIZE = 1.1;
  slide.addImage({ data: HAT_DATA, x: (W - SIZE) / 2, y, w: SIZE, h: SIZE, altText: 'red trilby hat' });
}

function addHatWatermarkLandscape(slide) {
  const SIZE = 0.48;
  const FOOTER_H = 0.85;
  const photoH = H - FOOTER_H;
  slide.addImage({ data: HAT_DATA, x: (W - SIZE) / 2, y: photoH + (FOOTER_H - SIZE) / 2, w: SIZE, h: SIZE, transparency: 55, altText: 'red trilby hat' });
}

function addHatWatermarkPortrait(slide, sidebarX, sidebarW) {
  const SIZE = 0.42;
  slide.addImage({ data: HAT_DATA, x: sidebarX + sidebarW - SIZE - 0.12, y: 0.75 - SIZE / 2, w: SIZE, h: SIZE, transparency: 55, altText: 'red trilby hat' });
}

// ─────────────────────────────────────────────────────
// SLIDE 1: HEADER CARD
// ─────────────────────────────────────────────────────
{
  const slide = pres.addSlide();
  slide.background = { color: C.bg };
  addHatProminent(slide, 0.28);
  slide.addText("a liturgy from the church of music", {
    x: 0.5, y: 1.55, w: W - 1, h: 0.35,
    fontFace: "Georgia", fontSize: 14, italic: true,
    color: C.fade, align: "center", margin: 0, charSpacing: 2,
  });
  slide.addText("Songs for my Funeral", {
    x: 0.5, y: 1.95, w: W - 1, h: 1.1,
    fontFace: "Georgia", fontSize: 54, bold: false,
    color: C.ink, align: "center", margin: 0,
  });
  addRule(slide, 3.0, 3.15, 4.0);
  slide.addText("26 tracks  ·  assembled with love", {
    x: 0.5, y: 3.3, w: W - 1, h: 0.35,
    fontFace: "Georgia", fontSize: 13, italic: true,
    color: C.fade, align: "center", margin: 0, charSpacing: 1,
  });
}

// ─────────────────────────────────────────────────────
// CHAPTER + TRACK CARD FACTORY
// ─────────────────────────────────────────────────────
chapters.forEach(ch => {

  // ── CHAPTER CARD ──────────────────────────────────
  {
    const slide = pres.addSlide();
    slide.background = { color: C.chapterBg };
    addHatProminent(slide, 0.18);
    slide.addText(`Chapter ${ch.num}`, {
      x: 0.5, y: 1.3, w: W - 1, h: 0.4,
      fontFace: "Georgia", fontSize: 13,
      color: C.rust, align: "center", margin: 0, charSpacing: 4,
    });
    slide.addText(ch.title, {
      x: 0.5, y: 1.75, w: W - 1, h: 1.0,
      fontFace: "Georgia", fontSize: 40, bold: false,
      color: C.ink, align: "center", margin: 0,
    });
    addRule(slide, 3.5, 2.88, 3.0);
    slide.addText(ch.epigraph, {
      x: 1.5, y: 3.05, w: W - 3, h: 0.9,
      fontFace: "Georgia", fontSize: 16, italic: true,
      color: C.body, align: "center", margin: 0,
    });
    slide.addText(`Tracks ${ch.tracks.map(n => String(n).padStart(2,'0')).join("  ·  ")}`, {
      x: 0.5, y: H - 0.55, w: W - 1, h: 0.3,
      fontFace: "Georgia", fontSize: 11,
      color: C.fade, align: "center", margin: 0, charSpacing: 1,
    });
  }

  // ── TRACK CARDS ───────────────────────────────────
  ch.tracks.forEach(tNum => {
    const t = tracks[tNum - 1];

    // ── TRACK TITLE CARD ──
    {
      const slide = pres.addSlide();
      slide.background = { color: C.bg };

      const COV = 2.4;
      const covX = W - COV - 0.45;
      const covY = (H - COV) / 2;

      // Hat below cover art (if it fits)
      const hatSize = 0.7;
      const hatY = covY + COV + 0.14;
      if (hatY + hatSize <= H + 0.05) {
        slide.addImage({ data: HAT_DATA, x: covX + (COV - hatSize) / 2, y: hatY, w: hatSize, h: hatSize, altText: 'red trilby hat' });
      }

      slide.addText(String(t.num).padStart(2,'0'), {
        x: 0.5, y: 0.4, w: 1.2, h: 0.9,
        fontFace: "Georgia", fontSize: 48,
        color: C.rule, align: "left", margin: 0,
      });
      slide.addText(t.format.toUpperCase(), {
        x: W - 3.2, y: 0.45, w: 2.85, h: 0.4,
        fontFace: "Georgia", fontSize: 9,
        color: C.rust, align: "right", margin: 0, charSpacing: 2,
      });
      slide.addText(t.title, {
        x: 0.5, y: 1.4, w: W - 1, h: 1.2,
        fontFace: "Georgia", fontSize: t.num === 20 ? 38 : 44, bold: false,
        color: C.ink, align: "left", margin: 0,
      });
      slide.addText(t.performer, {
        x: 0.5, y: 2.65, w: W - 1, h: 0.45,
        fontFace: "Georgia", fontSize: 20, italic: true,
        color: C.body, align: "left", margin: 0,
      });

      // Cover art
      if (t.coverData) {
        slide.addImage({ data: t.coverData, x: covX, y: covY, w: COV, h: COV,
          sizing: { type: 'cover', w: COV, h: COV } });
      } else {
        slide.addShape(pres.shapes.RECTANGLE, {
          x: covX, y: covY, w: COV, h: COV,
          fill: { color: C.rule }, line: { color: C.rust, width: 1 },
        });
        slide.addText(`${String(t.num).padStart(2,'0')}\ncover missing`, {
          x: covX, y: covY + 0.8, w: COV, h: 0.8,
          fontFace: "Georgia", fontSize: 11, italic: true,
          color: C.fade, align: "center", margin: 0,
        });
      }

      addRule(slide, 0.5, 3.2, covX - 0.7);
      if (t.lyricPull) slide.addText(`"${t.lyricPull}"`, {
        x: 0.5, y: 3.38, w: covX - 0.75, h: 0.85,
        fontFace: "Georgia", fontSize: 15, italic: true,
        color: C.fade, align: "left", margin: 0,
      });
      slide.addText(`Chapter ${ch.num} — ${ch.title}`, {
        x: 0.5, y: H - 0.45, w: W - 1, h: 0.3,
        fontFace: "Georgia", fontSize: 10,
        color: C.rust, align: "center", margin: 0, charSpacing: 1,
      });
      slide.addNotes(`TIMING: ${timingNote(t)}\n\nChapter ${ch.num}: ${ch.title}`);
    }

    // ── PHOTO SLIDE: LANDSCAPE ──
    {
      const slide = pres.addSlide();
      slide.background = { color: C.bg };
      const FOOTER_H = 0.85;
      const photoH = H - FOOTER_H;

      slide.addImage({ data: PLACEHOLDER_LANDSCAPE, x: 0, y: 0, w: W, h: photoH,
        altText: 'landscape photo placeholder — right-click → Change Picture to replace' });

      slide.addShape(pres.shapes.RECTANGLE, {
        x: 0, y: photoH, w: W, h: FOOTER_H,
        fill: { color: "161210" }, line: { color: "161210", width: 0 },
      });
      addRule(slide, 0, photoH, W);
      slide.addText(`${String(t.num).padStart(2,'0')}  ${t.title}`, {
        x: 0.35, y: photoH + 0.1, w: 6, h: 0.35,
        fontFace: "Georgia", fontSize: 15,
        color: C.ink, align: "left", margin: 0,
      });
      slide.addText(t.performer.replace('\n',' '), {
        x: 0.35, y: photoH + 0.42, w: 6, h: 0.28,
        fontFace: "Georgia", fontSize: 11, italic: true,
        color: C.fade, align: "left", margin: 0,
      });
      slide.addText(`${ch.num} — ${ch.title}`, {
        x: 5.5, y: photoH + 0.22, w: 4.15, h: 0.3,
        fontFace: "Georgia", fontSize: 10,
        color: C.rust, align: "right", margin: 0, charSpacing: 1,
      });
      addHatWatermarkLandscape(slide);
      slide.addNotes(`LANDSCAPE PHOTO TEMPLATE — Track ${t.num}: ${t.title}\n${timingNote(t)}\nRight-click the placeholder image → Change Picture to replace it. Aspect ratio ~3:2 or 16:9 preferred.`);
    }

    // ── PHOTO SLIDE: PORTRAIT / SQUARE ──
    {
      const slide = pres.addSlide();
      slide.background = { color: C.bg };
      const SIDEBAR_X = 6.8;
      const SIDEBAR_W = W - SIDEBAR_X - 0.35;

      slide.addImage({ data: PLACEHOLDER_PORTRAIT, x: 0, y: 0, w: SIDEBAR_X - 0.15, h: H,
        altText: 'portrait/square photo placeholder — right-click → Change Picture to replace' });

      slide.addShape(pres.shapes.RECTANGLE, {
        x: SIDEBAR_X - 0.15, y: 0.35, w: 0.02, h: H - 0.7,
        fill: { color: C.rust }, line: { color: C.rust, width: 0 },
      });
      slide.addText(String(t.num).padStart(2,'0'), {
        x: SIDEBAR_X, y: 0.4, w: SIDEBAR_W, h: 0.7,
        fontFace: "Georgia", fontSize: 36,
        color: C.rule, align: "left", margin: 0,
      });
      slide.addText(t.title, {
        x: SIDEBAR_X, y: 1.1, w: SIDEBAR_W, h: 1.4,
        fontFace: "Georgia", fontSize: 20, bold: false,
        color: C.ink, align: "left", margin: 0,
      });
      slide.addText(t.performer.replace('\n',' '), {
        x: SIDEBAR_X, y: 2.55, w: SIDEBAR_W, h: 0.7,
        fontFace: "Georgia", fontSize: 12, italic: true,
        color: C.body, align: "left", margin: 0,
      });
      addRule(slide, SIDEBAR_X, 3.35, SIDEBAR_W);
      if (t.lyricPull) slide.addText(`"${t.lyricPull}"`, {
        x: SIDEBAR_X, y: 3.5, w: SIDEBAR_W, h: 1.4,
        fontFace: "Georgia", fontSize: 12, italic: true,
        color: C.fade, align: "left", margin: 0,
      });
      slide.addText(`${ch.num} — ${ch.title}`, {
        x: SIDEBAR_X, y: H - 0.4, w: SIDEBAR_W, h: 0.3,
        fontFace: "Georgia", fontSize: 10,
        color: C.rust, align: "left", margin: 0, charSpacing: 1,
      });
      addHatWatermarkPortrait(slide, SIDEBAR_X, SIDEBAR_W);
      slide.addNotes(`PORTRAIT/SQUARE PHOTO TEMPLATE — Track ${t.num}: ${t.title}\n${timingNote(t)}\nRight-click the placeholder image → Change Picture to replace it. Aspect ratio ~2:3 or 1:1 preferred.`);
    }
  });
});

// ─────────────────────────────────────────────────────
// WRITE FILE
// ─────────────────────────────────────────────────────
pres.writeFile({ fileName: "ppt/slides-songs-for-my-funeral.pptx" })
  .then(() => console.log("Done."))
  .catch(e => { console.error(e); process.exit(1); });
