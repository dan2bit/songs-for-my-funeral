#!/usr/bin/env python3
"""
youtube_create_playlists.py — Automated playlist assembler for @dan2bit bootleg channel

Creates YouTube playlists from youtube_videos.tsv by matching videos to a show's date,
orders them (headliner first, then supporting acts, each in setlist.fm order if available),
and writes the resulting playlist URLs back to the appropriate show tracking file.

REQUIRES OAuth (not just an API key) because playlist creation and description updates
are write operations. The scope https://www.googleapis.com/auth/youtube is required.

FIRST-TIME SETUP:
    1. Copy live-shows/.env.example to live-shows/.env
    2. Place client_secrets.json in the live-shows/ directory
       (download from Google Cloud Console → Credentials → OAuth 2.0 Client IDs)
    3. pip install google-api-python-client google-auth-oauthlib python-dotenv
    4. Run once: python3 youtube_create_playlists.py --auth-only
       This opens a browser, you approve access, token.json is cached for future runs.
    See utils/HOWTO.md → "YouTube API credentials" for full setup instructions.

USAGE:

  ── Creating playlists ─────────────────────────────────────────────

    # Create a playlist for a single show (primary workflow).
    # Show is looked up in live_shows_history.tsv OR live_shows_2026.tsv automatically.
    python3 youtube_create_playlists.py --new-show 2026-03-29
    python3 youtube_create_playlists.py --new-show 2026-03-29 --update-history

    # Create playlists for all attended shows since a date that have no playlist yet.
    # Skips any show whose Playlist URL column is already populated.
    python3 youtube_create_playlists.py --new-show since:2026-01-11 --update-history --dry-run
    python3 youtube_create_playlists.py --new-show since:2026-01-11 --update-history

    # Override the headliner if the date lookup is ambiguous (single-date mode only)
    python3 youtube_create_playlists.py --new-show 2026-03-29 --headliner "Selwyn Birchwood"

    # Dry run — shows what would be created without calling the API
    python3 youtube_create_playlists.py --new-show 2026-03-29 --dry-run

    # Process shows in the WORKLIST (backfill shows with videos in youtube_videos.tsv)
    python3 youtube_create_playlists.py --worklist --dry-run
    python3 youtube_create_playlists.py --worklist --update-history

    # Process a single show by date using youtube_videos.tsv
    python3 youtube_create_playlists.py --date 2022-12-16

  ── Fixing playlist descriptions ────────────────────────────────────

    # Find playlists with blank descriptions and add the headliner setlist.fm link.
    # Scans all channel playlists, matches back to history/2026, fills in descriptions.
    # ALWAYS use --dry-run first or --date to limit scope — avoids burning write quota.
    python3 youtube_create_playlists.py --fix-descriptions --dry-run
    python3 youtube_create_playlists.py --fix-descriptions --date 2023-06-11 2023-07-05

    # Custom description template (use {setlist_url} and/or {venue} as placeholders)
    # Default: "Select tracks from {setlist_url}"
    python3 youtube_create_playlists.py --fix-descriptions \\
        --description-template "Select tracks from my vantage point center-left: {setlist_url}"

OUTPUT LOG (always written, gitignored — lives in logs/ subdirectory):
    logs/playlist_creation_log.tsv — one row per show processed:
        Show Date, Artist, Playlist Title, Playlist URL, Video Count,
        Setlist URL Checked, Setlist Order Used, Videos Added (titles)

NAMING CONVENTION (matches existing channel playlists):
    "{Headliner} LIVE @ {Venue Short} ({City/State abbrev}) {M/D/YY}"
    e.g. "They Might Be Giants LIVE @ Lincoln Theatre (DC) 12/16/22"
    Override per-show with --title if needed.

ORDERING LOGIC:
    1. Fetch setlist.fm URL for the show (from live_shows_history.tsv or live_shows_2026.tsv)
    2. Parse song titles from setlist.fm HTML (via requests + BeautifulSoup)
    3. Match video titles against setlist songs using fuzzy title matching
    4. Unmatched videos for the headliner go after matched ones
    5. Supporting act videos follow in their own setlist order (if available)
    6. Within each group, unordered videos sort by upload date as fallback

VIDEO MATCHING (--new-show):
    Primary: videos uploaded on the show date via the channel uploads API
    (publishedAt == show date). Picks up brand-new private videos not yet
    in youtube_videos.tsv.
    Fallback: youtube_videos.tsv matched by show date in video description.
    This is the same reliable matching used by the correlator, avoids the
    cross-show contamination that description-scanning all uploads causes,
    and correctly handles all backfill cases since videos are already in
    youtube_videos.tsv by the time you're creating their playlist.

NOTE ON PRIVATE/DRAFT VIDEOS (--new-show):
    The YouTube Data API returns private videos when authenticated. Videos that are
    still processing or in a true draft state (never submitted) will NOT appear.
    Upload your videos first, then run --new-show. Private videos are fine.

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

# ── dependency check ──────────────────────────────────────────────────────────────────────────────
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

# ── constants ─────────────────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/youtube"]
CLIENT_SECRETS = os.environ.get("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")
TOKEN_FILE     = os.environ.get("YOUTUBE_TOKEN_FILE",     "token.json")
CHANNEL_HANDLE = "dan2bit"

# Input files (same directory)
VIDEOS_TSV     = "youtube_videos.tsv"
HISTORY_TSV    = "live_shows_history.tsv"
SHOWS_2026_TSV = "live_shows_2026.tsv"

# Log file — written to logs/ subdir which is gitignored
LOG_TSV        = os.path.join("logs", "playlist_creation_log.tsv")

# Default description template for --fix-descriptions
DEFAULT_DESCRIPTION_TEMPLATE = "Select tracks from {setlist_url}"

# Setlist.fm fetch headers (polite browser impersonation)
SETLIST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; dan2bit-playlist-tool/1.0)"
}
SETLIST_DELAY = 2.0  # seconds between setlist.fm requests

# ── WORKLIST ──────────────────────────────────────────────────────────────────────────────
# Backfill shows: videos are already in youtube_videos.tsv, no live API query needed.
# Process with: python3 youtube_create_playlists.py --worklist --update-history
# (Use --dry-run first to verify video matching looks correct.)
#
# 4 flagged shows held back for manual review (ambiguous video attribution):
#   2022-04-26  Daniel Donato        (only 1 video)
#   2023-09-09  DuPont Brass         (1 DuPont video mixed in Kingsley Flood show)
#   2023-10-15  LL Cool J            (6 of 7 videos are Queen Latifah)
#   2025-06-21  Buddy Guy            (2 Judith Hill videos likely from different show)
#
# Completed — playlists already exist in live_shows_history.tsv:
#   2021-07-11  Oliver Wood                    (PLJ7S-K0cjvGKpKDhWEMnm1AhMb5Hqd5g)
#   2021-10-16  Larkin Poe                     (PLJ7S-K0cjvGK28bYHf1SaivuMW6_vbtb4)
#   2022-09-17  Willie Nelson                  (PLJ7S-K0cjvGK...)
#   2022-11-17  Tab Benoit                     (PLJ7S-K0cjvGK...)
#   2022-11-30  Kate Davis                     (PLJ7S-K0cjvGLY-DcEWxAOKJUfpnxH0OjA, combined 3-show)
#   2022-12-14  Ana Popović                    (PLJ7S-K0cjvGK...)
#   2022-12-16  They Might Be Giants           (PLJ7S-K0cjvGL_4w7JPXDjdpVEyrdWMt7A)
#   2022-12-29  The Pietasters                 (PLJ7S-K0cjvGLSUDeAzh0kWdohvVdRgXwU)
#   2022-12-31  George Clinton & Parliament-Funkadelic
#   2023-01-28  Greensky Bluegrass             (PLJ7S-K0cjvGIwrytCDiiIwjYMp9Gu-dBU)
#   2023-02-16  Gaelic Storm                   (PLJ7S-K0cjvGJCuoPi7VNSx0axXv1HGFOu)
#   2023-02-23  Buffalo Nichols                (PLJ7S-K0cjvGL3d6OIv6ko926yd1i6phA_)
#   2023-03-09  Larkin Poe                     (PLJ7S-K0cjvGITKvXJ5BP8bv4CKMnRkdiG)
#   2023-06-15  Kate Davis                     (PLJ7S-K0cjvGLY-DcEWxAOKJUfpnxH0OjA, combined 3-show)
#   2023-06-20  Christone Kingfish Ingram      (PLJ7S-K0cjvGLFTXtHeMY5QzPncF8xiZP_, shared 2-show)
#   2023-06-28  Ally Venable Band
#   2023-09-02  Oh He Dead
#   2023-09-09  Kingsley Flood
#   2023-09-13  Sonny Landreth
#   2023-09-26  Nas
#   2023-11-26  The Lone Bellow                (PLJ7S-K0cjvGKRyNDy8v0VqJXIn3HkT39K)
#   2024-06-27  Christone Kingfish Ingram      (PLJ7S-K0cjvGLSwIQC01VwRxLlxqUnZBWz)
#   2024-09-28  Soul Coughing                  (PLJ7S-K0cjvGKJath7-jUYRE2EuuNFRgU7)
#   2024-10-03  The Lone Bellow                (PLJ7S-K0cjvGJBpcSRwOfciHwhbssMAyAR)
#   2024-11-20  Samantha Fish                  (PLJ7S-K0cjvGKgmK7pARDcQrZ9p3FoNcCe)
#   2025-04-11  The War and Treaty             (PLJ7S-K0cjvGJ0oxlwovpXG26gHAMR0ViG)
#   2025-06-10  Suzanne Vega                   (PLJ7S-K0cjvGK5nb1sCthFnLvqdYbJI_tD)
#   2025-07-17  Jax Hollow                     (PLJ7S-K0cjvGJqpoD9UT_BtMYghkC91Vqr)
#   2025-08-19  D.K. Harrell                   (PLJ7S-K0cjvGLG-WCQPCyCMvPy5mhfmOym)
#   2025-09-19  Alabama Shakes                 (PLJ7S-K0cjvGKuIHQkITzIRpAiSxah3hpx)
#   2025-09-24  Christone Kingfish Ingram      (PLJ7S-K0cjvGIRp58p0ZK_whWMsFRNnYmN)
#   2025-10-15  Jackie Venson                  (PLJ7S-K0cjvGKYTwXZMX8huYuTgbPF-_Qh)
#   2025-10-21  Tommy Emmanuel                 (PLJ7S-K0cjvGLOAzoPhVXBV1lHGD1YliMK)
#   2025-10-26  Ruthie Foster                  (PLJ7S-K0cjvGLZWb0lcUzPfC917AfzTCz0)
#   2025-11-08  North Mississippi Allstars     (PLJ7S-K0cjvGKXGlxcjXwWHadud4tZUOYn)
#   2021-11-18  Christone "Kingfish" Ingram (Sixth & I)
#   2025-06-19  Eric Gales
#   2025-07-21  Amythyst Kiah
#   2025-10-08  Judith Hill
#   2022-10-27  Enter the Haggis
#   2023-12-10  Allison Russell                (PLJ7S-K0cjvGKiu9D23lUv6bKPDFn4yeF0)
#   2024-12-07  New York's Finest              (PLJ7S-K0cjvGKiwUTspiwAj7wnnVWQgKpE)
#   2024-12-17  Tab Benoit                     (PLJ7S-K0cjvGKYz7J-iKrhJWbVvxkBCVbK)
#   2025-01-24  New York's Finest              (PLJ7S-K0cjvGL5ue9R0AwEi0lm4oDO9TJz)
#   2025-01-31  Vanessa Collier                (PLJ7S-K0cjvGInas_WA9iBbgWHQnn3BS5b)
#   2025-02-07  Yasmin Williams                (PLJ7S-K0cjvGITzWjn5xZ1ipXgr0iHKuRa)
#   2025-07-11  North Mississippi Allstars     (PLJ7S-K0cjvGKW6qYwcL6OAURkxZM2bBXg)
#   2025-07-13  J. P. Soars                    (PLJ7S-K0cjvGL98faCVXHXqwCbpeLztqWO)
WORKLIST = [
    # (show_date, headliner, title_override)
    # title_override=None means auto-generate from history venue + date
    ("2025-07-16", "Barenaked Ladies",                     None),
    ("2025-08-03", "Eric Johanson",                        None),
    ("2025-08-28", "Robert Randolph",                      None),
    ("2025-09-23", "Bywater Call",                         None),
    ("2025-12-20", "Maggie Rose",                          None),
]

# ── auth ──────────────────────────────────────────────────────────────────────────────
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

# ── data loading ────────────────────────────────────────────────────────────────────────────
def load_tsv(filename):
    with open(filename, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def load_videos():
    videos = load_tsv(VIDEOS_TSV)
    print(f"Loaded {len(videos)} videos from {VIDEOS_TSV}")
    return videos


def load_history():
    """
    Load show index from both live_shows_history.tsv and live_shows_2026.tsv.

    Returns (history_rows, index) where:
      - history_rows: raw rows from live_shows_history.tsv only (used for write-back)
      - index: dict keyed by (Show Date, Artist) covering both files.
        Rows from live_shows_2026.tsv are normalised so process_show sees the
        same field names regardless of source:
            Venue Name        → Venue
            Supporting Artist → Supporting Acts
        A "_source_file" key is added to each row so update_history_playlist_url
        knows which file to write back to.
    """
    history_rows = load_tsv(HISTORY_TSV)
    index = {}

    for r in history_rows:
        r["_source_file"] = HISTORY_TSV
        index[(r["Show Date"], r["Artist"])] = r

    if os.path.exists(SHOWS_2026_TSV):
        rows_2026 = load_tsv(SHOWS_2026_TSV)
        attended = [r for r in rows_2026 if r.get("Status", "") == "attended"]
        for r in attended:
            normalised = dict(r)
            normalised["Venue"]           = r.get("Venue Name", "")
            normalised["Supporting Acts"] = r.get("Supporting Artist", "")
            normalised["_source_file"]    = SHOWS_2026_TSV
            index[(r["Show Date"], r["Artist"])] = normalised
        print(f"Loaded {len(attended)} attended 2026 shows from {SHOWS_2026_TSV}")

    return history_rows, index


# ── date utilities ────────────────────────────────────────────────────────────────────────
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

# ── venue short name ─────────────────────────────────────────────────────────────────────────
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
    "Filene Center at Wolf Trap, Vienna, VA, USA":                  "Wolf Trap (VA)",
    # live_shows_2026.tsv uses short venue names directly
    "Rams Head On Stage":                                           "Ram's Head (MD)",
    "Hamilton Live":                                                "Hamilton Live (DC)",
    "The Birchmere":                                                "Birchmere (VA)",
    "Jammin' Java":                                                 "Jammin' Java (VA)",
    "Collective Encore":                                            "Collective Encore (MD)",
    "9:30 Club":                                                    "9:30 Club (DC)",
    "Wolf Trap Filene Center":                                      "Wolf Trap (VA)",
    "Warner Theatre":                                               "Warner Theatre (DC)",
}

def venue_short(venue_str):
    if venue_str in VENUE_SHORT:
        return VENUE_SHORT[venue_str]
    parts = venue_str.split(",")
    return parts[0].strip()

# ── playlist title generation ────────────────────────────────────────────────────────────────
def make_playlist_title(headliner, venue_str, date_str):
    name = re.sub(r'\s*"[^"]+"\s*', ' ', headliner).strip()
    return f"{name} LIVE @ {venue_short(venue_str)} {format_date_short(date_str)}"

# ── video matching ───────────────────────────────────────────────────────────────────────────
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

# ── setlist.fm ordering ───────────────────────────────────────────────────────────────────────
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

# ── YouTube API: channel uploads (upload-date match only) ───────────────────────────────
def fetch_uploads_by_date(youtube, date_str):
    """
    Fetch videos from the authenticated user's uploads playlist that were
    uploaded on date_str (YYYY-MM-DD). Includes private videos.
    Returns list of dicts: {video_id, title, description, published},
    or an empty list if no uploads match that date.

    Only used for brand-new shows where videos were uploaded the same day
    and may not yet be in youtube_videos.tsv. For all other cases the
    caller falls back to find_videos_for_date() against youtube_videos.tsv.
    """
    channels_resp = youtube.channels().list(
        part="contentDetails",
        mine=True
    ).execute()
    uploads_playlist_id = (
        channels_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    )

    videos = []
    page_token = None
    print(f"  Fetching uploads playlist for {date_str}...")
    while True:
        kwargs = dict(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
        )
        if page_token:
            kwargs["pageToken"] = page_token
        resp = youtube.playlistItems().list(**kwargs).execute()

        for item in resp.get("items", []):
            snippet = item["snippet"]
            published = snippet.get("publishedAt", "")[:10]
            if published == date_str:
                videos.append({
                    "video_id":    snippet["resourceId"]["videoId"],
                    "title":       snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "published":   published,
                })

        page_token = resp.get("nextPageToken")

        # Uploads playlist is reverse-chronological — stop once we've
        # passed the target date to avoid scanning the entire channel.
        if resp.get("items"):
            oldest_on_page = min(
                item["snippet"].get("publishedAt", "")[:10]
                for item in resp["items"]
            )
            if oldest_on_page < date_str:
                break

        if not page_token:
            break

    print(f"  Found {len(videos)} video(s) uploaded on {date_str}")
    return videos

# ── YouTube API: playlist operations ──────────────────────────────────────────────────
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

def fetch_all_channel_playlists(youtube):
    """Return list of dicts: {playlist_id, title, description, item_count}"""
    playlists = []
    page_token = None
    while True:
        kwargs = dict(part="snippet,contentDetails", mine=True, maxResults=50)
        if page_token:
            kwargs["pageToken"] = page_token
        resp = youtube.playlists().list(**kwargs).execute()
        for item in resp.get("items", []):
            playlists.append({
                "playlist_id":  item["id"],
                "title":        item["snippet"]["title"],
                "description":  item["snippet"].get("description", ""),
                "item_count":   item["contentDetails"]["itemCount"],
                "url":          f"https://www.youtube.com/playlist?list={item['id']}",
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return playlists

def update_playlist_description(youtube, playlist_id, title, new_description):
    youtube.playlists().update(
        part="snippet",
        body={
            "id": playlist_id,
            "snippet": {
                "title": title,
                "description": new_description,
            }
        }
    ).execute()

# ── show file write-back ─────────────────────────────────────────────────────────────────────────
def update_history_playlist_url(date_str, artist, playlist_url, show_row=None):
    """
    Write the playlist URL back to the appropriate source file.

    If show_row carries a "_source_file" key (set by load_history), that file
    is used directly. History rows write to live_shows_history.tsv (updating
    Match Type too); 2026 rows write to live_shows_2026.tsv.
    """
    source_file = (show_row or {}).get("_source_file") or HISTORY_TSV

    if source_file == HISTORY_TSV or not os.path.exists(SHOWS_2026_TSV):
        _write_playlist_url_to_file(HISTORY_TSV, date_str, artist, playlist_url,
                                    artist_col="Artist", date_col="Show Date",
                                    url_col="Playlist URL", match_type_col="Match Type")
    else:
        _write_playlist_url_to_file(SHOWS_2026_TSV, date_str, artist, playlist_url,
                                    artist_col="Artist", date_col="Show Date",
                                    url_col="Playlist URL", match_type_col=None)


def _write_playlist_url_to_file(filepath, date_str, artist, playlist_url,
                                 artist_col, date_col, url_col, match_type_col):
    rows = load_tsv(filepath)
    if not rows:
        print(f"  WARNING: {filepath} is empty")
        return
    fieldnames = list(rows[0].keys())
    updated = False
    for r in rows:
        if r.get(date_col) == date_str and r.get(artist_col) == artist:
            r[url_col] = playlist_url
            if match_type_col and match_type_col in r:
                r[match_type_col] = "Playlist (assembled)"
            updated = True
            break
    if updated:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t",
                                    extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(f"  Updated {filepath} with playlist URL")
    else:
        print(f"  WARNING: could not find {date_str} / {artist} in {filepath}")

# ── log ──────────────────────────────────────────────────────────────────────────────────
LOG_FIELDNAMES = ["Show Date", "Artist", "Playlist Title", "Playlist URL", "Video Count", "Setlist URL Checked", "Setlist Order Used", "Videos Added"]

def write_log_row(log_rows):
    os.makedirs(os.path.dirname(LOG_TSV), exist_ok=True)
    write_header = not os.path.exists(LOG_TSV)
    with open(LOG_TSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDNAMES, delimiter="\t")
        if write_header:
            writer.writeheader()
        for row in log_rows:
            writer.writerow(row)

# ── core per-show processing ────────────────────────────────────────────────────────────────
def process_show(youtube, date_str, headliner, title_override, videos, history_index,
                 dry_run=False, update_history=False, use_channel_uploads=False):
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing: {date_str} — {headliner}")

    show = history_index.get((date_str, headliner))
    if not show:
        matches = [(k, v) for k, v in history_index.items() if k[0] == date_str and headliner.lower()[:8] in k[1].lower()]
        if matches:
            show = matches[0][1]
            print(f"  Fuzzy match: {matches[0][0][1]}")
        else:
            print(f"  WARNING: show not found in history or 2026 file — proceeding without venue/setlist data")
            show = {}

    source_file = show.get("_source_file", HISTORY_TSV)
    print(f"  Source file: {source_file}")

    venue_str      = show.get("Venue", "")
    supporting_str = show.get("Supporting Acts", "")
    setlist_url    = show.get("Setlist.fm URL", "")

    # ── Video source resolution ───────────────────────────────────────────────────
    # For --new-show: try the channel uploads API first (catches brand-new
    # private videos not yet in youtube_videos.tsv). If nothing found on that
    # upload date, fall back to youtube_videos.tsv — the same reliable
    # description-date matching used by the correlator.
    #
    # Never do a full-channel description scan: that causes cross-show
    # contamination when videos from multiple shows are uploaded on the
    # same day and date strings appear as substrings of each other.
    date_vids = []
    if use_channel_uploads and youtube and not dry_run:
        # Check youtube_videos.tsv first — saves quota for shows already ingested.
        # Only fall back to the uploads API if the TSV has nothing for this date,
        # meaning the videos are brand-new and haven't been ingested yet.
        date_vids = find_videos_for_date(date_str, videos)
        if not date_vids:
            print(f"  No videos in youtube_videos.tsv for {date_str} — trying channel uploads API")
            date_vids = fetch_uploads_by_date(youtube, date_str)
        else:
            print(f"  Found {len(date_vids)} video(s) in youtube_videos.tsv — skipping uploads API")
    else:
        if use_channel_uploads and dry_run:
            print("  [DRY RUN] Would check youtube_videos.tsv first, then channel uploads API if needed")
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
            update_history_playlist_url(date_str, headliner, playlist_url, show_row=show)

    log_row = {
        "Show Date": date_str, "Artist": headliner, "Playlist Title": playlist_title,
        "Playlist URL": playlist_url, "Video Count": len(final_order),
        "Setlist URL Checked": setlist_url or "none", "Setlist Order Used": setlist_status,
        "Videos Added": " | ".join(v["title"] for v in final_order),
    }
    write_log_row([log_row])
    return playlist_url

# ── fix-descriptions mode ────────────────────────────────────────────────────────────────────
def run_fix_descriptions(youtube, history_index, description_template, date_filter=None, dry_run=False):
    """
    Find channel playlists with blank descriptions and fill them in using
    the setlist.fm URL from history or 2026 tracking file, formatted with
    description_template.

    Template placeholders:
        {setlist_url}  — the setlist.fm URL for the show
        {venue}        — short venue name

    NOTE: Always use --dry-run first or --date to limit scope. Fetching all
    channel playlists and updating descriptions uses write quota — running
    without a date filter on a large channel will exhaust quota quickly.
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fetching all channel playlists...")
    playlists = fetch_all_channel_playlists(youtube)
    print(f"  Found {len(playlists)} playlists on channel")

    url_to_history = {}
    for (date_str, artist), row in history_index.items():
        purl = row.get("Playlist URL", "")
        if purl and purl.startswith("https://www.youtube.com/playlist"):
            url_to_history[purl.strip()] = row

    updated = 0
    skipped_has_desc = 0
    skipped_no_match = 0
    skipped_no_setlist = 0

    for pl in playlists:
        if pl["description"].strip():
            skipped_has_desc += 1
            continue

        if date_filter:
            history_row = url_to_history.get(pl["url"])
            if not history_row or history_row.get("Show Date") not in date_filter:
                continue

        history_row = url_to_history.get(pl["url"])
        if not history_row:
            skipped_no_match += 1
            print(f"  SKIP (no history match): {pl['title']}")
            continue

        setlist_url = history_row.get("Setlist.fm URL", "").strip()
        if not setlist_url:
            skipped_no_setlist += 1
            print(f"  SKIP (no setlist URL): {pl['title']}")
            continue

        venue_str = history_row.get("Venue", "")
        new_desc = description_template.format(
            setlist_url=setlist_url,
            venue=venue_short(venue_str),
        )

        print(f"  {'[DRY RUN] ' if dry_run else ''}UPDATE: {pl['title']}")
        print(f"    → {new_desc}")

        if not dry_run:
            update_playlist_description(youtube, pl["playlist_id"], pl["title"], new_desc)
            time.sleep(0.5)

        updated += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Fix-descriptions summary:")
    print(f"  Updated:              {updated}")
    print(f"  Already had desc:     {skipped_has_desc}")
    print(f"  No history match:     {skipped_no_match}")
    print(f"  No setlist URL:       {skipped_no_setlist}")

# ── main ──────────────────────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create/manage YouTube playlists for @dan2bit shows")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--new-show",        metavar="DATE",
                            help=(
                                "Create playlist(s) for attended show(s). "
                                "Pass a single date (YYYY-MM-DD) to create one playlist, "
                                "or since:YYYY-MM-DD to create playlists for all attended shows "
                                "on or after that date whose Playlist URL is not yet populated. "
                                "Tries channel uploads API first (for brand-new private videos), "
                                "then falls back to youtube_videos.tsv."
                            ))
    mode_group.add_argument("--fix-descriptions", action="store_true",
                            help="Find playlists with blank descriptions and fill in setlist.fm link. Always use --dry-run first or --date to limit scope.")
    mode_group.add_argument("--worklist",         action="store_true",
                            help="Process shows in WORKLIST using youtube_videos.tsv (backfill mode).")
    mode_group.add_argument("--date",             nargs="+", metavar="DATE",
                            help="Process show(s) by date from youtube_videos.tsv.")

    parser.add_argument("--headliner",            metavar="NAME",
                        help="Override headliner name (single-date --new-show only).")
    parser.add_argument("--title",                metavar="TITLE",
                        help="Override playlist title instead of auto-generating.")
    parser.add_argument("--description-template", metavar="TEMPLATE",
                        default=DEFAULT_DESCRIPTION_TEMPLATE,
                        help=f"Template for --fix-descriptions. Placeholders: {{setlist_url}}, {{venue}}. "
                             f"Default: \"{DEFAULT_DESCRIPTION_TEMPLATE}\"")
    parser.add_argument("--update-history",       action="store_true",
                        help="Write created playlist URL back to the source show file (history or 2026).")
    parser.add_argument("--dry-run",              action="store_true",
                        help="Show what would happen without making any API calls.")
    parser.add_argument("--auth-only",            action="store_true",
                        help="Authenticate and save token.json, then exit.")

    args = parser.parse_args()

    # Auth
    youtube = None
    if not args.dry_run:
        print("Authenticating with YouTube...")
        youtube = get_authenticated_service()
        print("Authenticated.")
        if args.auth_only:
            print("Auth complete. token.json saved.")
            return

    # Load shared data
    videos = load_videos()
    history_rows, history_index = load_history()
    print(f"Loaded {len(history_rows)} history shows")

    # ── --fix-descriptions ───────────────────────────────────────────────────────────────────
    if args.fix_descriptions:
        if not youtube and not args.dry_run:
            sys.exit("--fix-descriptions requires authentication (no --dry-run override available without auth)")
        date_filter = set(args.date) if args.date else None
        run_fix_descriptions(
            youtube, history_index,
            description_template=args.description_template,
            date_filter=date_filter,
            dry_run=args.dry_run,
        )
        return

    # ── --new-show ───────────────────────────────────────────────────────────────────
    if args.new_show:
        new_show_arg = args.new_show

        # ── since:DATE range mode ─────────────────────────────────────────────────────────────
        if new_show_arg.startswith("since:"):
            since_date = new_show_arg[len("since:"):]
            try:
                datetime.strptime(since_date, "%Y-%m-%d")
            except ValueError:
                sys.exit(f"Invalid date in since: prefix — expected since:YYYY-MM-DD, got: {new_show_arg}")

            if args.headliner:
                sys.exit("--headliner cannot be used with since: range mode.")

            queue = sorted(
                [
                    (date_str, artist, show)
                    for (date_str, artist), show in history_index.items()
                    if date_str >= since_date and not (show.get("Playlist URL") or "").strip()
                ],
                key=lambda t: t[0],
            )

            if not queue:
                print(f"No shows without playlists found on or after {since_date}.")
                return

            print(f"\nShows to process ({len(queue)} total, since {since_date}):")
            for date_str, artist, _ in queue:
                print(f"  {date_str}  {artist}")

            results = []
            for date_str, artist, show in queue:
                url = process_show(
                    youtube, date_str, artist, args.title, videos, history_index,
                    dry_run=args.dry_run,
                    update_history=args.update_history,
                    use_channel_uploads=True,
                )
                results.append((date_str, artist, url))

            print(f"\n{'='*60}")
            print(f"{'DRY RUN ' if args.dry_run else ''}SUMMARY — {len(results)} show(s) processed")
            for date_str, artist, url in results:
                status = url or "skipped (no videos)"
                print(f"  {date_str}  {artist:<35}  {status}")
            print(f"\nLog written to: {LOG_TSV}")
            if args.update_history and not args.dry_run:
                print("Source files updated with playlist URLs")
            return

        # ── single date mode ─────────────────────────────────────────────────────────────────
        date_str = new_show_arg
        headliner = args.headliner
        if not headliner:
            matches = [(k, v) for k, v in history_index.items() if k[0] == date_str]
            if len(matches) == 1:
                headliner = matches[0][0][1]
                print(f"Found in history/2026: {date_str} — {headliner}")
            elif len(matches) > 1:
                print(f"Multiple shows on {date_str}:")
                for k, v in matches:
                    print(f"  {k[1]}")
                sys.exit("Use --headliner to specify which one.")
            else:
                sys.exit(
                    f"No show found for {date_str} in {HISTORY_TSV} or {SHOWS_2026_TSV}.\n"
                    f"Use --headliner to specify the artist, or add the show to the tracking file first."
                )

        url = process_show(
            youtube, date_str, headliner, args.title, videos, history_index,
            dry_run=args.dry_run,
            update_history=args.update_history,
            use_channel_uploads=True,
        )
        print(f"\nResult: {url or 'skipped'}")
        return

    # ── --worklist ─────────────────────────────────────────────────────────────────────────
    if args.worklist:
        if not WORKLIST:
            print("WORKLIST is empty — nothing to process.")
            print("Use --new-show DATE to create a playlist for a recent show.")
            return
        queue_tuples = [(d, a, t) for d, a, t in WORKLIST]
        print(f"Processing {len(queue_tuples)} shows from WORKLIST")

    # ── --date ─────────────────────────────────────────────────────────────────────────────
    elif args.date:
        worklist_index = {d: (d, a, t) for d, a, t in WORKLIST}
        queue_tuples = []
        for date_str in args.date:
            if date_str in worklist_index:
                queue_tuples.append(worklist_index[date_str])
            else:
                matches = [(k, v) for k, v in history_index.items() if k[0] == date_str]
                if matches:
                    artist = matches[0][0][1]
                    queue_tuples.append((date_str, artist, None))
                    print(f"  Found in history/2026: {date_str} — {artist}")
                else:
                    print(f"  WARNING: {date_str} not found in history, 2026 file, or worklist — skipping")
    else:
        parser.print_help()
        return

    results = []
    for date_str, headliner, title_override in queue_tuples:
        url = process_show(
            youtube, date_str, headliner, args.title or title_override, videos, history_index,
            dry_run=args.dry_run,
            update_history=args.update_history,
            use_channel_uploads=False,
        )
        results.append((date_str, headliner, url))

    print(f"\n{'='*60}")
    print(f"{'DRY RUN ' if args.dry_run else ''}SUMMARY — {len(results)} show(s) processed")
    for date_str, headliner, url in results:
        print(f"  {date_str}  {headliner:<35}  {url or 'skipped'}")
    print(f"\nLog written to: {LOG_TSV}")
    if args.update_history and not args.dry_run:
        print("Source files updated with playlist URLs")

if __name__ == "__main__":
    main()
