# Backing up to the Dan-RIP thumb drive

The backup script mirrors three things to the thumb drive:

| Source | Destination on thumb |
|--------|----------------------|
| `~/github/hm/songs-for-my-funeral/` (repo clone) | `Dan-RIP/songs-for-my-funeral-website/` |
| Google Drive `songs for my funeral/` folder | `Dan-RIP/songs-for-my-funeral-slideshow/` |
| Google Drive `in case of emergency/` folder | `Dan-RIP/in case of emergency/` |

The folder names are intentional — if someone picks up the drive without any context, `songs-for-my-funeral-slideshow/` is immediately obvious as the thing to open.

It runs automatically every 30 minutes while `Dan-RIP` is mounted. If the drive isn't plugged in, it exits silently — no errors, no notifications.

Logs are written to `~/Library/Logs/funeral-backup.log`.

---

## One-time setup

Do this once on any machine where you want the automatic backup.

### 1. Make the script executable

```bash
chmod +x ~/github/hm/songs-for-my-funeral/backup-to-thumb.sh
```

### 2. Install the plist and substitute your username in one step

```bash
cp ~/github/hm/songs-for-my-funeral/utils/com.dan2bit.funeral-backup.plist \
   ~/Library/LaunchAgents/

sed -i '' "s/YOURUSERNAME/$(whoami)/g" \
   ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

Verify the substitution worked:
```bash
grep dan ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```
You should see your actual username, not `YOURUSERNAME`.

### 3. Load the agent

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

If that fails with `Bootstrap failed: 5: Input/output error`, there is likely a stale entry from a previous install or OS upgrade. Clear it first, then retry:

```bash
launchctl bootout gui/$(id -u)/com.dan2bit.funeral-backup
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

### 4. Test it immediately

Plug in `Dan-RIP`, then run:
```bash
launchctl kickstart gui/$(id -u)/com.dan2bit.funeral-backup
sleep 10
tail ~/Library/Logs/funeral-backup.log
```

You should see something like:
```
[2026-03-24 01:30:00] --- backup started ---
[2026-03-24 01:30:00] Syncing repo: ...
[2026-03-24 01:30:02] Repo sync OK
[2026-03-24 01:30:02] Syncing GDrive (slideshow): ...
[2026-03-24 01:30:08] GDrive slideshow sync OK
[2026-03-24 01:30:08] Syncing GDrive (in case of emergency): ...
[2026-03-24 01:30:09] GDrive ICE sync OK
[2026-03-24 01:30:09] --- backup complete (no errors) ---
```

---

## Managing the agent

```bash
# Check if it's running
launchctl list | grep funeral

# Stop and unregister
launchctl bootout gui/$(id -u)/com.dan2bit.funeral-backup

# Re-register and start
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist

# Run it immediately (useful for testing, once registered)
launchctl kickstart gui/$(id -u)/com.dan2bit.funeral-backup
```

---

## After a macOS upgrade

If the agent stops working after an OS update, the most likely cause is a stale launchd entry. Fix:

```bash
launchctl bootout gui/$(id -u)/com.dan2bit.funeral-backup
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

Verify it took:
```bash
launchctl list | grep funeral
```

Also make sure `/bin/bash` still has Full Disk Access in System Settings → Privacy & Security → Full Disk Access. This permission can be lost after a major OS upgrade.

---

## Changing the interval

Edit the installed plist and change the `StartInterval` value (in seconds):

| Interval | Seconds |
|----------|---------|
| 15 minutes | 900 |
| 30 minutes | 1800 |
| 1 hour | 3600 |

After editing, reload:
```bash
launchctl bootout gui/$(id -u)/com.dan2bit.funeral-backup
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

---

## What rsync does

`rsync -a --delete` makes the destination an exact mirror of the source:
- New or changed files are copied over
- Files deleted from the source are deleted from the destination
- File permissions and timestamps are preserved
- The `.git/` directory and `node_modules/` are excluded from the repo backup (they're large and reconstructable)
- Google Workspace stub files (`.gdoc`, `.gsheet`, `.gslides`, etc.) are excluded from the GDrive syncs — these are pointer stubs with no actual content; the real documents live only in Google's cloud

It's safe to unplug the drive mid-backup — rsync writes complete files, so you won't end up with half-written corrupted files.
