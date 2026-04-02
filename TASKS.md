# Songs for my Funeral — Tasks

*Open items for the funeral playlist project.*

---

## 1. Refresh Guitar Gods & Goddesses Facebook → Google Photos export

The Facebook Transfer tool sync was set up in March 2026 and runs monthly for 3 years (expires March 2029). However a manual refresh of the full album export may be needed if new photos have been added since the last sync or if the sync needs to be re-verified.

**How to refresh:**
1. Go to Facebook → Settings → Your Facebook Information → Transfer a copy of your information
2. Select Photos and Videos → Google Photos
3. Choose the "Guitar Gods and Goddesses and Me" album
4. Authorize and transfer

**Google Photos album (public):** https://photos.app.goo.gl/McCzxX53Kh6bHKEy7  
**Facebook album:** https://www.facebook.com/media/set/?set=a.10159009137456887  
**Next required re-authorization:** March 2029

---

## ~~2. Restyle liner notes — keep chapter metadata visually connected~~ ✓ DONE

Implemented Option D: sticky chapter banner using `position: sticky` + IntersectionObserver. Each chapter's break and tracks are wrapped in `.chapter-section`. The sticky label appears only after scrolling past the chapter break, shares the tinted `--chapter-bg` background with the break itself, and reads e.g. `Chapter 2: You'll Be Okay (Grief Sucks) - 6 tracks`. Committed to `index.html` April 2026.

---

## 3. Curate & import historical and family photos

Import personal and family photos into the same Google Photos account (`redhat.bootlegs@gmail.com`) as the Guitar Gods album, in separate albums. These will feed the slideshow alongside the gig photos.

**Destination:** Google Photos, `redhat.bootlegs@gmail.com`  
**Structure:** separate albums from Guitar Gods & Goddesses and Me — e.g. one album per era or category  
**Note:** captions entered in Google Photos survive within the account but are lost on Takeout export — caption as you go.

---

## 4. Begin seeding actual photos into the slide deck

Replace the placeholder photo templates in `slides-songs-for-my-funeral.pptx` with real photos. This is a one-way door — once photos are in, future changes to the slide template (layout, fonts, hat watermark position, chapter references) become significantly harder to apply without re-doing the photo work.

**Recommended order of operations:**
1. Complete tasks 2 and 3 first — finalize the template and have the full photo library ready
2. Work track by track, landscape vs. portrait template as appropriate
3. Keep a copy of the blank template (`build-slides.js` + `node build-slides.js`) for reference in case layout changes are still needed

**Photo sources once ready:**
- Guitar Gods & Goddesses and Me (Google Photos, public album)
- Historical/family photos (task 3)
