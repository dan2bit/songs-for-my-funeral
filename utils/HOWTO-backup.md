# Backing up to the Dan-RIP thumb drive

The backup script mirrors two things to the thumb drive:

| Source | Destination on thumb |
|--------|----------------------|
| `~/github/hm/songs-for-my-funeral/` (repo clone) | `Dan-RIP/songs-for-my-funeral/` |
| Google Drive `songs for my funeral/` folder | `Dan-RIP/songs-for-my-funeral-gdrive/` |

It runs automatically every 30 minutes while `Dan-RIP` is mounted. If the drive isn't plugged in, it exits silently — no errors, no notifications.

Logs are written to `~/Library/Logs/funeral-backup.log`.

---

## One-time setup

Do this once on any machine where you want the automatic backup.

### 1. Make the script executable

```bash
chmod +x ~/github/hm/songs-for-my-funeral/backup-to-thumb.sh
```

### 2. Edit the plist with your actual username

Open `utils/com.dan2bit.funeral-backup.plist` in any text editor and replace both instances of `YOURUSERNAME` with your macOS username (the short name, e.g. `dan`).

You can find your username by running:
```bash
whoami
```

### 3. Install the plist as a launchd agent

```bash
cp ~/github/hm/songs-for-my-funeral/utils/com.dan2bit.funeral-backup.plist \
   ~/Library/LaunchAgents/

launchctl load ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

That's it. launchd will now run the backup every 30 minutes whenever you're logged in.

### 4. Test it immediately

Plug in `Dan-RIP`, then run:
```bash
bash ~/github/hm/songs-for-my-funeral/backup-to-thumb.sh
```

Check the log to confirm it worked:
```bash
tail ~/Library/Logs/funeral-backup.log
```

You should see something like:
```
[2026-03-16 01:30:00] --- backup started ---
[2026-03-16 01:30:00] Syncing repo: ...
[2026-03-16 01:30:02] Repo sync OK
[2026-03-16 01:30:02] Syncing GDrive: ...
[2026-03-16 01:30:08] GDrive sync OK
[2026-03-16 01:30:08] --- backup complete (no errors) ---
```

---

## Managing the agent

```bash
# Stop it (stops the running job, won't restart until next login)
launchctl unload ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist

# Start it again
launchctl load ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist

# Run it immediately (useful for testing)
launchctl start com.dan2bit.funeral-backup

# Check its status
launchctl list | grep funeral
```

---

## Changing the interval

Edit the plist and change the `StartInterval` value (in seconds):

| Interval | Seconds |
|----------|---------|
| 15 minutes | 900 |
| 30 minutes | 1800 |
| 1 hour | 3600 |

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
launchctl load   ~/Library/LaunchAgents/com.dan2bit.funeral-backup.plist
```

---

## What rsync does

`rsync -a --delete` makes the destination an exact mirror of the source:
- New or changed files are copied over
- Files deleted from the source are deleted from the destination
- File permissions and timestamps are preserved
- The `.git/` directory and `node_modules/` are excluded from the repo backup (they're large and reconstructable)

It's safe to unplug the drive mid-backup — rsync writes complete files, so you won't end up with half-written corrupted files.
