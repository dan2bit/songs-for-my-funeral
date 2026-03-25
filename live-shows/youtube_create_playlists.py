#!/usr/bin/env python3
"""
youtube_create_playlists.py — Automated playlist assembler for @dan2bit bootleg channel

Creates YouTube playlists from youtube_videos.tsv by matching videos to a show's date,
orders them (headliner first, then supporting acts, each in setlist.fm order if available),
and writes the resulting playlist URLs back to live_shows_history.tsv.

REQUIRES OAuth (not just an API key) because playlist creation is a write operation.

FIRST-TIME SETUP:
    1. Copy live-shows/.env.example to live-shows/.env
    2. Place client_secrets.json in the live-shows/ directory
       (download from Google Cloud Console → Credentials → OAuth 2.0 Client IDs)
    3. pip install google-api-python-client google-auth-oauthlib python-dotenv
    4. Run once: python3 youtube_create_playlists.py --auth-only
       This opens a browser, you approve access, token.json is cached for future runs.
    See utils/HOWTO.md → "YouTube API credentials" for full setup instructions.

USAGE:
    # Dry run — shows what would be created without calling the API
    python3 youtube_create_playlists.py --dry-run

    # Process a single show by date (YYYY-MM-DD)
    python3 youtube_create_playlists.py --date 2022-12-16

    # Process a list of dates
    python3 youtube_create_playlists.py --date 2022-12-16 2023-06-15 2023-11-26

    # Process all shows in the worklist (WORKLIST at bottom of file)
    python3 youtube_create_playlists.py --worklist

    # Update live_shows_history.tsv with playlist URLs after creating playlists
    python3 youtube_create_playlists.py --worklist --update-history

OUTPUT LOG (always written regardless of flags):
    playlist_creation_log.tsv — one row per show processed:
        Show Date, Artist, Playlist Title, Playlist URL, Video Count,
        Setlist URL Checked, Setlist Order Used, Videos Added (titles)

NAMING CONVENTION (matches existing channel playlists):
    "{Headliner} LIVE @ {Venue Short} ({City/State abbrev}) {M/D/YY}"
    e.g. "They Might Be Giants LIVE @ Lincoln Theatre (DC) 12/16/22"
    Override per-show in WORKLIST if needed.

ORDERING LOGIC:
    1. Fetch setlist.fm URL for the show (from live_shows_history.tsv)
    2. Parse song titles from setlist.fm HTML (via requests + BeautifulSoup)
    3. Match video titles against setlist songs using fuzzy title matching
    4. Unmatched videos for the headliner go after matched ones
    5. Supporting act videos follow in their own setlist order (if available)
    6. Within each group, unordered videos sort by upload date as fallback

NOTE: setlist.fm is fetched live. If it blocks or returns no songs, ordering falls
back to upload-date order and the log records "no setlist data" for that URL.
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime

# ── dependency check ──────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit(
        "Missing dependency: python-dotenv\n"
        "Run: pip install python-dotenv"
    )

try:
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    sys.exit(
        "Missing dependencies. Run:\n"
        "  pip install google-api-python-client google-auth-oauthlib\n"
    )

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit(
        "Missing dependencies for setlist.fm fetching. Run:\n"
        "  pip install requests beautifulsoup4\n"
    )

# Load .env from the same directory as this script
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── constants ─────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
TOKEN_FILE     = os.environ.get("YOUTUBE_TOKEN_FILE",     "token.json")
CHANNEL_HANDLE = "dan2bit"

# Input files (same directory)
VIDEOS_TSV   = "youtube_videos.tsv"
HISTORY_TSV  = "live_shows_history.tsv"
LOG_TSV      = "playlist_creation_log.tsv"

# Setlist.fm fetch headers (polite browser impersonation)
SETLIST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; dan2bit-playlist-tool/1.0)"
}
SETLIST_DELAY = 2.0  # seconds between setlist.fm requests

# ── WORKLIST ──────────────────────────────────────────────────────────────────
# Edit this list to control which shows get playlists assembled.
# Each entry: (show_date, headliner, title_override_or_None)
# title_override: set a custom playlist title string; None = auto-generate.
#
# Removed — playlists already exist in live_shows_history.tsv:
#   2021-10-16  Larkin Poe           (PLJ7S-K0cjvGK28bYHf1SaivuMW6_vbtb4, incl. fan videos)
#   2022-11-30  Kate Davis           (combined 3-show playlist PLJ7S-K0cjvGLY-DcEWxAOKJUfpnxH0OjA)
#   2022-12-16  They Might Be Giants (PLJ7S-K0cjvGL_4w7JPXDjdpVEyrdWMt7A)
#   2022-12-29  The Pietasters       (PLJ7S-K0cjvGLSUDeAzh0kWdohvVdRgXwU)
#   2023-01-28  Greensky Bluegrass   (PLJ7S-K0cjvGIwrytCDiiIwjYMp9Gu-dBU)
#   2023-02-16  Gaelic Storm         (PLJ7S-K0cjvGJCuoPi7VNSx0axXv1HGFOu)
#   2023-02-23  Buffalo Nichols      (PLJ7S-K0cjvGL3d6OIv6ko926yd1i6phA_)
#   2023-03-09  Larkin Poe           (PLJ7S-K0cjvGITKvXJ5BP8bv4CKMnRkdiG)
#   2023-06-15  Kate Davis           (combined 3-show playlist PLJ7S-K0cjvGLY-DcEWxAOKJUfpnxH0OjA)
#   2023-06-20  Christone Kingfish Ingram (shared 2-show playlist PLJ7S-K0cjvGLFTXtHeMY5QzPncF8xiZP_)
#   2023-11-26  The Lone Bellow      (PLJ7S-K0cjvGKRyNDy8v0VqJXIn3HkT39K)
#   2024-06-27  Christone Kingfish Ingram (PLJ7S-K0cjvGLSwIQC01VwRxLlxqUnZBWz)
#   2024-09-28  Soul Coughing        (PLJ7S-K0cjvGKJath7-jUYRE2EuuNFRgU7)
#   2024-10-03  The Lone Bellow      (PLJ7S-K0cjvGJBpcSRwOfciHwhbssMAyAR)
#   2024-11-20  Samantha Fish        (PLJ7S-K0cjvGJ4Z5BOVXjoqZtOfng90wNV)
#   2025-04-11  The War and Treaty   (PLJ7S-K0cjvGJ0oxlwovpXG26gHAMR0ViG)
#   2025-06-10  Suzanne Vega         (PLJ7S-K0cjvGK5nb1sCthFnLvqdYbJI_tD)
#   2025-07-17  Jax Hollow           (PLJ7S-K0cjvGJqpoD9UT_BtMYghkC91Vqr)
#   2025-08-19  D.K. Harrell         (PLJ7S-K0cjvGLG-WCQPCyCMvPy5mhfmOym)
#   2025-09-19  Alabama Shakes       (PLJ7S-K0cjvGKuIHQkITzIRpAiSxah3hpx)
#   2025-09-24  Christone Kingfish Ingram (PLJ7S-K0cjvGIRp58p0ZK_whWMsFRNnYmN)
#   2025-10-15  Jackie Venson        (PLJ7S-K0cjvGKYTwXZMX8huYuTgbPF-_Qh)
#   2025-10-21  Tommy Emmanuel       (PLJ7S-K0cjvGLOAzoPhVXBV1lHGD1YliMK)
#   2025-10-26  Ruthie Foster        (PLJ7S-K0cjvGLZWb0lcUzPfC917AfzTCz0)
#   2025-11-08  North Mississippi Allstars (PLJ7S-K0cjvGKXGlxcjXwWHadud4tZUOYn)
WORKLIST = [
    ("2021-11-18", "Christone \"Kingfish\" Ingram", None),  # Sixth & I
    ("2025-06-19", "Eric Gales",                    None),
    ("2025-07-21", "Amythyst Kiah",                 None),
    ("2025-10-08", "Judith Hill",                   None),
    ("2022-10-27", "Enter the Haggis",              None),
]

# ── auth ──────────────────────────────────────────────────────────────────────
def get_authenticated_service():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    client_secrets_path = os.path.join(script_dir, CLIENT_SECRETS)
    token_path = os.path.join(script_dir, TOKEN_FILE)

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_path):
                sys.exit(
                    f"OAuth credentials file not found: {client_secrets_path}\n"
                    "Download it from Google Cloud Console → Credentials → OAuth 2.0 Client IDs.\n"
                    "See utils/HOWTO.md → \"YouTube API credentials\" for instructions."
                )
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)

# ── data loading ──────────────────────────────────────────────────────────────
def load_tsv(filename):
    with open(filename, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))

def load_videos():
    videos = load_tsv(VIDEOS_TSV)
    print(f"Loaded {len(videos)} videos from {VIDEOS_TSV}")
    return videos

def load_history():
    rows = load_tsv(HISTORY_TSV)
    index = {}
    for r in rows:
        index[(r["Show Date"], r["Artist"])] = r
    return rows, index

# ── date utilities ────────────────────────────────────────────────────────────
def date_variants(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return []
    return [
        f"{d.month}/{d.day}/{d.strftime('%y')}",
        f"{d.month}/{d.day}/{d.year}",
        f"{d.strftime('%m')}/{d.strftime('%d')}/{d.strftime('%y')}",
        f"{d.strftime('%m')}/{d.strftime('%d')}/{d.year}",
    ]

def format_date_short(date_str):
    """YYYY-MM-DD → M/D/YY"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.month}/{d.day}/{d.strftime('%y')}"

# ── venue short name ──────────────────────────────────────────────────────────
VENUE_SHORT = {
    "Lincoln Theatre, Washington, DC, USA":                         "Lincoln Theatre (DC)",
    "The Hamilton Live, Washington, DC, USA":                       "Hamilton Live (DC)",
    "9:30 Club, Washington, DC, USA":                               "9:30 Club (DC)",
    "The Anthem, Washington, DC, USA":                              "The Anthem (DC)",
    "The Birchmere, Alexandria, VA, USA":                           "Birchmere (VA)",
    "Rams Head On Stage, Annapolis, MD, USA":                       "Ram's Head (MD)",
    "Wolf Trap Farm Park (Filene Center), Vienna, VA, USA":         "Wolf Trap (VA)",
    "Wolf Trap Farm Park (The Barns), Vienna, VA, USA":             "Wolf Trap Barns (VA)",
    "The Fillmore Silver Spring, Silver Spring, MD, USA":           "Fillmore Silver Spring (MD)",
    "Warner Theatre, Washington, DC, USA":                          "Warner Theatre (DC)",
    "The Collective Encore, Columbia, MD, USA":                     "Collective Encore (MD)",
    "Pearl Street Warehouse, Washington, DC, USA":                  "Pearl Street Warehouse (DC)",
    "Jammin Java, Vienna, VA, USA":                                 "Jammin' Java (VA)",
    "Songbyrd Music House, Washington, DC, USA":                    "Songbyrd (DC)",
    "The Atlantis, Washington, DC, USA":                            "The Atlantis (DC)",
    "Capital One Hall, Tysons Corner, VA, USA":                     "Capital One Hall (VA)",
    "The Vault at Capital One Hall, Tysons Corner, VA, USA":        "The Vault (VA)",
    "The State Theatre, Falls Church, VA, USA":                     "State Theatre (VA)",
    "The 8x10, Baltimore, MD, USA":                                 "The 8x10 (Baltimore)",
    "The Music Center at Strathmore, North Bethesda, MD, USA":      "Strathmore (MD)",
    "AMP by Strathmore, North Bethesda, MD, USA":                   "Strathmore AMP (MD)",
    "Black Cat (Mainstage), Washington, DC, USA":                   "Black Cat (DC)",
    "Merriweather Post Pavilion, Columbia, MD, USA":                "Merriweather (MD)",
    "The Clarice Smith Performing Arts Center, College Park, MD, USA": "Clarice Smith (MD)",
    "Maryland Hall for the Creative Arts, Annapolis, MD, USA":      "Maryland Hall (MD)",
    "Maryland Theatre, Hagerstown, MD, USA":                        "Maryland Theatre (MD)",
    "Publick Playhouse, Landover, MD, USA":                         "Publick Playhouse (MD)",
    "The Howard Theatre, Washington, DC, USA":                      "Howard Theatre (DC)",
    "JV's Live Music Room, Falls Church, VA, USA":                  "JV's (VA)",
    "JV's Restaurant, Falls Church, VA, USA":                       "JV's (VA)",
    "Richmond Music Hall, Richmond, VA, USA":                       "Richmond Music Hall (VA)",
    "Union Stage, Washington, DC, USA":                             "Union Stage (DC)",
    "City Winery, Washington, DC, USA":                             "City Winery (DC)",
    "The Barns at Wolf Trap":                                       "Wolf Trap Barns (VA)",
    "DC9, Washington, DC, USA":                                     "DC9 (DC)",
    "Color Burst Park, Columbia, MD, USA":                          "Color Burst Park (MD)",
    "Bethesda Theater, Bethesda, MD, USA":                          "Bethesda Theatre (MD)",
    "Hub City Vinyl, Hagerstown, MD, USA":                          "Hub City Vinyl (MD)",
    "Columbia Art Center, Columbia, MD, USA":                       "Columbia Art Center (MD)",
    "Sixth & I Historic Synagogue, Washington, DC, USA":            "Sixth & I (DC)",
}

def venue_short(venue_str):
    if venue_str in VENUE_SHORT:
        return VENUE_SHORT[venue_str]
    parts = venue_str.split(",")
    return parts[0].strip()

# ── playlist title generation ─────────────────────────────────────────────────
def make_playlist_title(headliner, venue_str, date_str):
    name = re.sub(r'\s*"[^"]+"\s*', ' ', headliner).strip()
    return f"{name} LIVE @ {venue_short(venue_str)} {format_date_short(date_str)}"

# ── video matching ────────────────────────────────────────────────────────────
def find_videos_for_date(date_str, videos):
    dvs = date_variants(date_str)
    return [v for v in videos if any(dv in v.get("description", "") for dv in dvs)]

def normalize_title(s):
    return re.sub(r"[^\w\s]", "", s.lower()).strip()

def artist_words(artist):
    noise = {"band", "the", "and", "live", "feat", "featuring", "with", "ingram"}
    words = normalize_title(artist).split()
    return [w for w in words if len(w) > 3 and w not in noise]

def video_is_for_artist(video_title, artist):
    vt = normalize_title(video_title)
    for w in artist_words(artist):
        if w in vt:
            return True
    return False

def partition_videos(show_date, headliner, supporting_acts_str, all_date_videos):
    acts = [a.strip() for a in re.split(r"[/&]", supporting_acts_str) if a.strip()] if supporting_acts_str else []
    headliner_vids = []
    support_vids = {act: [] for act in acts}
    unattributed = []
    for v in all_date_videos:
        title = v["title"]
        if video_is_for_artist(title, headliner):
            headliner_vids.append(v)
        else:
            matched_act = None
            for act in acts:
                if video_is_for_artist(title, act):
                    matched_act = act
                    break
            if matched_act:
                support_vids[matched_act].append(v)
            else:
                unattributed.append(v)
    return headliner_vids, support_vids, unattributed

# ── setlist.fm ordering ───────────────────────────────────────────────────────
def fetch_setlist_songs(setlist_url):
    if not setlist_url:
        return [], "no setlist URL"
    try:
        resp = requests.get(setlist_url, headers=SETLIST_HEADERS, timeout=10)
        time.sleep(SETLIST_DELAY)
        if resp.status_code != 200:
            return [], f"HTTP {resp.status_code}"
        soup = BeautifulSoup(resp.text, "html.parser")
        songs = []
        for tag in soup.find_all(class_="songLabel"):
            t = tag.get_text(strip=True)
            if t:
                songs.append(t)
        if not songs:
            return [], "fetched but no songs found"
        return songs, f"ok ({len(songs)} songs)"
    except Exception as e:
        return [], f"fetch error: {e}"

def order_by_setlist(videos, songs):
    if not songs:
        return sorted(videos, key=lambda v: v.get("published", ""))

    def best_match(video_title, songs):
        vt = normalize_title(video_title)
        vt = re.sub(r"\bbootleg\b", "", vt)
        vt = re.sub(r"\blive\b", "", vt)
        vt = vt.strip()
        best_idx = None
        best_score = 0
        for i, song in enumerate(songs):
            sn = normalize_title(song)
            vwords = set(vt.split())
            swords = set(sn.split())
            shared = len(vwords & swords)
            if shared > best_score and shared >= 1:
                best_score = shared
                best_idx = i
        return best_idx

    placed = {}
    unmatched = []
    for v in videos:
        idx = best_match(v["title"], songs)
        if idx is not None and idx not in placed:
            placed[idx] = v
        else:
            unmatched.append(v)
    ordered = [placed[i] for i in sorted(placed.keys())]
    ordered += sorted(unmatched, key=lambda v: v.get("published", ""))
    return ordered

# ── YouTube API write operations ──────────────────────────────────────────────
def create_playlist(youtube, title, description=""):
    resp = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": "public"},
        }
    ).execute()
    return resp["id"], f"https://www.youtube.com/playlist?list={resp['id']}"

def add_video_to_playlist(youtube, playlist_id, video_id, position):
    youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}, "position": position}}
    ).execute()

# ── history update ─────────────────────────────────────────────────────────────
def update_history_playlist_url(date_str, artist, playlist_url):
    rows = load_tsv(HISTORY_TSV)
    fieldnames = list(rows[0].keys()) if rows else []
    updated = False
    for r in rows:
        if r["Show Date"] == date_str and r["Artist"] == artist:
            r["Playlist URL"] = playlist_url
            r["Match Type"] = "Playlist (assembled)"
            updated = True
            break
    if updated:
        with open(HISTORY_TSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Updated {HISTORY_TSV} with playlist URL")
    else:
        print(f"  WARNING: could not find {date_str} / {artist} in {HISTORY_TSV}")

# ── log ───────────────────────────────────────────────────────────────────────
LOG_FIELDNAMES = ["Show Date", "Artist", "Playlist Title", "Playlist URL", "Video Count", "Setlist URL Checked", "Setlist Order Used", "Videos Added"]

def write_log_row(log_rows):
    write_header = not os.path.exists(LOG_TSV)
    with open(LOG_TSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES, delimiter="\t")
        if write_header:
            writer.writeheader()
        for row in log_rows:
            writer.writerow(row)

# ── core per-show processing ──────────────────────────────────────────────────
def process_show(youtube, date_str, headliner, title_override, videos, history_index, dry_run=False, update_history=False):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {date_str} — {headliner}")
    show = history_index.get((date_str, headliner))
    if not show:
        matches = [(k, v) for k, v in history_index.items() if k[0] == date_str and headliner.lower()[:8] in k[1].lower()]
        if matches:
            show = matches[0][1]
            print(f"  Fuzzy match: {matches[0][0][1]}")
        else:
            print(f"  WARNING: show not found in history — skipping")
            return None
    venue_str      = show.get("Venue", "")
    supporting_str = show.get("Supporting Acts", "")
    setlist_url    = show.get("Setlist.fm URL", "")
    date_vids = find_videos_for_date(date_str, videos)
    if not date_vids:
        print(f"  No videos found for {date_str} — skipping")
        return None
    print(f"  Found {len(date_vids)} video(s) for this date")
    headliner_vids, support_vids, unattributed = partition_videos(date_str, headliner, supporting_str, date_vids)
    print(f"  Headliner: {len(headliner_vids)} | Support: {sum(len(v) for v in support_vids.values())} | Unattributed: {len(unattributed)}")
    headliner_vids += unattributed
    setlist_songs, setlist_status = fetch_setlist_songs(setlist_url)
    print(f"  Setlist.fm ({setlist_url or 'none'}): {setlist_status}")
    headliner_vids = order_by_setlist(headliner_vids, setlist_songs)
    ordered_support = []
    for act, act_vids in support_vids.items():
        if act_vids:
            act_sorted = sorted(act_vids, key=lambda v: v.get("published", ""))
            ordered_support.extend(act_sorted)
            print(f"  Supporting act '{act}': {len(act_vids)} video(s) (upload order)")
    final_order = headliner_vids + ordered_support
    playlist_title = title_override or make_playlist_title(headliner, venue_str, date_str)
    print(f"  Playlist title: {playlist_title}")
    for i, v in enumerate(final_order, 1):
        print(f"    {i:2}. {v['title'][:80]}")
    playlist_url = "[dry run — no playlist created]"
    if not dry_run:
        print("  Creating playlist...")
        playlist_id, playlist_url = create_playlist(youtube, playlist_title)
        print(f"  Playlist created: {playlist_url}")
        for pos, v in enumerate(final_order):
            add_video_to_playlist(youtube, playlist_id, v["video_id"], pos)
            time.sleep(0.3)
        print(f"  Added {len(final_order)} videos")
        if update_history:
            update_history_playlist_url(date_str, headliner, playlist_url)
    log_row = {
        "Show Date": date_str, "Artist": headliner, "Playlist Title": playlist_title,
        "Playlist URL": playlist_url, "Video Count": len(final_order),
        "Setlist URL Checked": setlist_url or "none", "Setlist Order Used": setlist_status,
        "Videos Added": " | ".join(v["title"] for v in final_order),
    }
    write_log_row([log_row])
    return playlist_url

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create YouTube playlists for @dan2bit shows")
    parser.add_argument("--auth-only",      action="store_true")
    parser.add_argument("--dry-run",        action="store_true")
    parser.add_argument("--worklist",       action="store_true")
    parser.add_argument("--date",           nargs="+")
    parser.add_argument("--update-history", action="store_true")
    args = parser.parse_args()
    youtube = None
    if not args.dry_run:
        print("Authenticating with YouTube...")
        youtube = get_authenticated_service()
        print("Authenticated.")
        if args.auth_only:
            print("Auth complete. token.json saved.")
            return
    videos = load_videos()
    history_rows, history_index = load_history()
    print(f"Loaded {len(history_rows)} history shows")
    queue = []
    if args.worklist:
        queue = [(d, a, t) for d, a, t in WORKLIST]
        print(f"Processing {len(queue)} shows from WORKLIST")
    elif args.date:
        worklist_index = {d: (d, a, t) for d, a, t in WORKLIST}
        for date_str in args.date:
            if date_str in worklist_index:
                queue.append(worklist_index[date_str])
            else:
                matches = [(k, v) for k, v in history_index.items() if k[0] == date_str]
                if matches:
                    artist = matches[0][0][1]
                    queue.append((date_str, artist, None))
                    print(f"  Found in history: {date_str} — {artist}")
                else:
                    print(f"  WARNING: {date_str} not found in history or worklist — skipping")
    else:
        parser.print_help()
        return
    results = []
    for date_str, headliner, title_override in queue:
        url = process_show(youtube, date_str, headliner, title_override, videos, history_index, dry_run=args.dry_run, update_history=args.update_history)
        results.append((date_str, headliner, url))
    print(f"\n{'='*60}")
    print(f"{'DRY RUN ' if args.dry_run else ''}SUMMARY — {len(results)} show(s) processed")
    for date_str, headliner, url in results:
        print(f"  {date_str}  {headliner:<35}  {url or 'skipped'}")
    print(f"\nLog written to: {LOG_TSV}")
    if args.update_history and not args.dry_run:
        print(f"History updated: {HISTORY_TSV}")

if __name__ == "__main__":
    main()
