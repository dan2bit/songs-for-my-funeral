#!/bin/bash
# run.sh — build and sync outputs to Google Drive
#
# Usage:
#   ./run.sh assemble       # run assemble.sh, copy outputs to Drive
#   ./run.sh slides         # run build-slides.js, copy pptx to Drive
#   ./run.sh all            # run both
#
# Auto-detects whether Google Drive is mounted and falls back
# to a local ./output/ copy if Drive is unavailable.
#
# Run from the repo root: ~/projects/songs-for-my-funeral/

set -e

# ─────────────────────────────────────────────────────
# CONFIG — edit these paths to match your machine
# ─────────────────────────────────────────────────────

GDRIVE_ROOT="$HOME/Google Drive/My Drive/songs for my funeral"
GDRIVE_OUTPUT="$GDRIVE_ROOT/output"
GDRIVE_ROOT_PPTX="$GDRIVE_ROOT/slides-songs-for-my-funeral.pptx"

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TRACKS_DIR="$REPO_ROOT/tracks"       # symlink or real dir of mp3s
OUTPUT_DIR="$REPO_ROOT/output"       # symlink or local fallback
PPT_OUTPUT="$REPO_ROOT/ppt/slides-songs-for-my-funeral.pptx"

# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────

drive_available() {
  [ -d "$GDRIVE_ROOT" ]
}

status() { echo "▶ $*"; }
ok()     { echo "  ✓ $*"; }
warn()   { echo "  ⚠ $*"; }

# ─────────────────────────────────────────────────────
# ASSEMBLE
# ─────────────────────────────────────────────────────

run_assemble() {
  status "Running assemble.sh from $TRACKS_DIR ..."

  if [ ! -d "$TRACKS_DIR" ]; then
    echo "ERROR: tracks/ directory not found at $TRACKS_DIR"
    echo "       Make sure your symlink or folder exists."
    exit 1
  fi

  if [ ! -f "$TRACKS_DIR/tracks.tsv" ]; then
    echo "ERROR: tracks.tsv not found in $TRACKS_DIR"
    echo "       Expected at: $TRACKS_DIR/tracks.tsv"
    exit 1
  fi

  # Run assemble.sh from the tracks directory
  cd "$TRACKS_DIR"
  bash "$REPO_ROOT/utils/assemble.sh"
  cd "$REPO_ROOT"

  # Collect assembled outputs (chapter-*.mp3 and songs-for-my-funeral.mp3)
  ASSEMBLED_FILES=("$TRACKS_DIR"/chapter-*.mp3 "$TRACKS_DIR/songs-for-my-funeral.mp3")

  if drive_available; then
    status "Google Drive is available — copying outputs to Drive ..."
    mkdir -p "$GDRIVE_OUTPUT"
    for f in "${ASSEMBLED_FILES[@]}"; do
      [ -f "$f" ] || continue
      cp "$f" "$GDRIVE_OUTPUT/"
      ok "Copied $(basename "$f") → Drive/output/"
    done
    # Also move them out of tracks/ into output/ if output is not a symlink to Drive
    if [ ! -L "$OUTPUT_DIR" ]; then
      mkdir -p "$OUTPUT_DIR"
      for f in "${ASSEMBLED_FILES[@]}"; do
        [ -f "$f" ] || continue
        mv "$f" "$OUTPUT_DIR/"
        ok "Moved $(basename "$f") → output/"
      done
    fi
  else
    warn "Google Drive not found at: $GDRIVE_ROOT"
    warn "Saving outputs to local output/ instead."
    mkdir -p "$OUTPUT_DIR"
    for f in "${ASSEMBLED_FILES[@]}"; do
      [ -f "$f" ] || continue
      mv "$f" "$OUTPUT_DIR/"
      ok "Saved $(basename "$f") → output/"
    done
    warn "Remember to sync output/ to Google Drive when it reconnects."
  fi

  ok "assemble complete."
}

# ─────────────────────────────────────────────────────
# BUILD SLIDES
# ─────────────────────────────────────────────────────

run_slides() {
  status "Running build-slides.js ..."

  # build-slides.js must run from repo root (needs red_hat_icon.png and covers/)
  cd "$REPO_ROOT"

  if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found. Run from repo root."
    exit 1
  fi

  if [ ! -d "node_modules" ]; then
    status "node_modules not found — running npm install first ..."
    npm install
  fi

  node ppt/build-slides.js

  if [ ! -f "$PPT_OUTPUT" ]; then
    echo "ERROR: Expected output not found: $PPT_OUTPUT"
    exit 1
  fi

  if drive_available; then
    status "Google Drive is available — copying pptx to Drive ..."
    cp "$PPT_OUTPUT" "$GDRIVE_ROOT_PPTX"
    ok "Copied slides-songs-for-my-funeral.pptx → Drive root"
  else
    warn "Google Drive not found at: $GDRIVE_ROOT"
    warn "pptx saved locally at: $PPT_OUTPUT"
    warn "Remember to copy it to Google Drive when it reconnects."
  fi

  ok "slides build complete."
}

# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

case "${1:-}" in
  assemble)
    run_assemble
    ;;
  slides)
    run_slides
    ;;
  all)
    run_assemble
    echo ""
    run_slides
    ;;
  *)
    echo "Usage: $0 {assemble|slides|all}"
    echo ""
    echo "  assemble   Run assemble.sh and copy chapter/master mp3s to Google Drive"
    echo "  slides     Run build-slides.js and copy pptx to Google Drive"
    echo "  all        Run both"
    exit 1
    ;;
esac

echo ""
echo "Done."
