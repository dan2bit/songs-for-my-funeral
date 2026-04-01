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

## 2. Restyle liner notes — keep chapter metadata visually connected

Currently the chapter break (title, rule, epigraph) sits as a free-standing block between tracks. The goal is to make the chapter context feel more attached — so that when you're reading a track note, the chapter it belongs to is visually present or clearly associated rather than something you scroll past.

**Options to explore:**
- Sticky or persistent chapter label in the margin or header while scrolling through a chapter's tracks
- Small chapter indicator on each track header (e.g. a faint chapter name or number above the track number)
- Visual treatment that carries the chapter color/style into the track blocks themselves
- Chapter nav anchors at the top of the page

**Constraint:** changes should be CSS/HTML only, no JavaScript required. The private `liner-notes.html` is the canonical source; `index.html` (public) is derived from it.
