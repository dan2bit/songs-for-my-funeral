#!/bin/bash
# backup-to-thumb.sh — rsync the repo and GDrive folders to the Dan-RIP thumb drive
#
# Designed to be run by launchd every 30 minutes (see utils/HOWTO-backup.md).
# Safe to run manually too: ./backup-to-thumb.sh
#
# Silently exits if the thumb drive isn't mounted — no errors, no noise.
# Logs to ~/Library/Logs/funeral-backup.log

set -euo pipefail

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────

THUMB="/Volumes/Dan-RIP"
LOGFILE="$HOME/Library/Logs/funeral-backup.log"

# Source 1: the repo clone
REPO_SRC="$HOME/github/hm/songs-for-my-funeral/"
REPO_DST="$THUMB/songs-for-my-funeral-website/"

# Source 2: the Google Drive "songs for my funeral" folder
GDRIVE_SRC="$HOME/Library/CloudStorage/GoogleDrive-redhat.bootlegs@gmail.com/My Drive/songs for my funeral/"
GDRIVE_DST="$THUMB/songs-for-my-funeral-slideshow/"

# Source 3: the Google Drive "in case of emergency" folder
ICE_SRC="$HOME/Library/CloudStorage/GoogleDrive-redhat.bootlegs@gmail.com/My Drive/in case of emergency/"
ICE_DST="$THUMB/in case of emergency/"

# ─────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOGFILE"
}

# ─────────────────────────────────────────────────────
# BAIL OUT SILENTLY IF DRIVE NOT MOUNTED
# ─────────────────────────────────────────────────────

if [ ! -d "$THUMB" ]; then
  # Drive not mounted — normal, not an error. Exit quietly.
  exit 0
fi

# ─────────────────────────────────────────────────────
# RUN BACKUPS
# ─────────────────────────────────────────────────────

log "--- backup started ---"
ERRORS=0

# Repo clone → thumb drive
if [ -d "$REPO_SRC" ]; then
  log "Syncing repo: $REPO_SRC → $REPO_DST"
  rsync -a --delete \
    --exclude='.git/' \
    --exclude='node_modules/' \
    --exclude='*.DS_Store' \
    --exclude='~$*' \
    "$REPO_SRC" "$REPO_DST" \
    >> "$LOGFILE" 2>&1 && log "Repo sync OK" || { log "ERROR: repo sync failed"; ERRORS=$((ERRORS+1)); }
else
  log "WARNING: repo source not found: $REPO_SRC"
fi

# GDrive "songs for my funeral" folder → thumb drive
if [ -d "$GDRIVE_SRC" ]; then
  log "Syncing GDrive (slideshow): $GDRIVE_SRC → $GDRIVE_DST"
  rsync -a --delete \
    --exclude='*.DS_Store' \
    --exclude='~$*' \
    --exclude='*.gdoc' \
    --exclude='*.gsheet' \
    --exclude='*.gslides' \
    --exclude='*.gform' \
    --exclude='*.gdraw' \
    "$GDRIVE_SRC" "$GDRIVE_DST" \
    >> "$LOGFILE" 2>&1 && log "GDrive slideshow sync OK" || { log "ERROR: GDrive slideshow sync failed"; ERRORS=$((ERRORS+1)); }
else
  log "WARNING: GDrive slideshow source not found: $GDRIVE_SRC"
fi

# GDrive "in case of emergency" folder → thumb drive
# Note: .gdoc/.gsheet/.gslides etc. are excluded — they are pointer stubs, not real files.
# The actual documents live in Google Drive's cloud and are not backed up here.
if [ -d "$ICE_SRC" ]; then
  log "Syncing GDrive (in case of emergency): $ICE_SRC → $ICE_DST"
  rsync -a --delete \
    --exclude='*.DS_Store' \
    --exclude='~$*' \
    --exclude='*.gdoc' \
    --exclude='*.gsheet' \
    --exclude='*.gslides' \
    --exclude='*.gform' \
    --exclude='*.gdraw' \
    "$ICE_SRC" "$ICE_DST" \
    >> "$LOGFILE" 2>&1 && log "GDrive ICE sync OK" || { log "ERROR: GDrive ICE sync failed"; ERRORS=$((ERRORS+1)); }
else
  log "WARNING: GDrive ICE source not found: $ICE_SRC"
fi

if [ "$ERRORS" -eq 0 ]; then
  log "--- backup complete (no errors) ---"
else
  log "--- backup complete with $ERRORS error(s) — check above ---"
fi
