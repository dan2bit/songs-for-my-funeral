#!/bin/bash
# backup-to-thumb.sh — rsync the repo and GDrive folder to the Dan-RIP thumb drive
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

# Source 2: the Google Drive folder (via Google Drive for Desktop)
GDRIVE_SRC="$HOME/Library/CloudStorage/GoogleDrive-redhat.bootlegs@gmail.com/My Drive/songs for my funeral/"
GDRIVE_DST="$THUMB/songs-for-my-funeral-slideshow/"

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
    "$REPO_SRC" "$REPO_DST" \
    >> "$LOGFILE" 2>&1 && log "Repo sync OK" || { log "ERROR: repo sync failed"; ERRORS=$((ERRORS+1)); }
else
  log "WARNING: repo source not found: $REPO_SRC"
fi

# GDrive folder → thumb drive
if [ -d "$GDRIVE_SRC" ]; then
  log "Syncing GDrive: $GDRIVE_SRC → $GDRIVE_DST"
  rsync -a --delete \
    --exclude='*.DS_Store' \
    "$GDRIVE_SRC" "$GDRIVE_DST" \
    >> "$LOGFILE" 2>&1 && log "GDrive sync OK" || { log "ERROR: GDrive sync failed"; ERRORS=$((ERRORS+1)); }
else
  log "WARNING: GDrive source not found: $GDRIVE_SRC"
fi

if [ "$ERRORS" -eq 0 ]; then
  log "--- backup complete (no errors) ---"
else
  log "--- backup complete with $ERRORS error(s) — check above ---"
fi
