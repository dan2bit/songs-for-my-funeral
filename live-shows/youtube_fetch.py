#!/usr/bin/env python3
"""
dan2bit YouTube channel metadata fetcher
Pulls all videos and playlists and outputs TSVs for correlation with show history.

Usage:
    pip install google-api-python-client
    python3 youtube_fetch.py

Output files:
    youtube_videos.tsv    — all uploads with title, date, duration, URL
    youtube_playlists.tsv — all playlists with title, date, item count, URL

NOTE: API_KEY must be set before running. Do not commit a live key to this repo.
"""

import csv
import sys
from googleapiclient.discovery import build

API_KEY    = "YOUR_API_KEY_HERE"  # Replace with your key; do not commit live keys
CHANNEL_HANDLE = "dan2bit"

def get_channel_id(youtube):
    resp = youtube.channels().list(
        part="id,contentDetails",
        forHandle=CHANNEL_HANDLE
    ).execute()
    items = resp.get("items", [])
    if not items:
        sys.exit(f"Channel @{CHANNEL_HANDLE} not found.")
    channel = items[0]
    channel_id = channel["id"]
    uploads_playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"Channel ID: {channel_id}")
    print(f"Uploads playlist ID: {uploads_playlist_id}")
    return channel_id, uploads_playlist_id

def fetch_all_videos(youtube, uploads_playlist_id):
    videos = []
    page_token = None
    while True:
        resp = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=page_token
        ).execute()
        for item in resp.get("items", []):
            snippet = item["snippet"]
            video_id = item["contentDetails"]["videoId"]
            videos.append({
                "video_id":    video_id,
                "title":       snippet.get("title", ""),
                "published":   snippet.get("publishedAt", "")[:10],
                "description": snippet.get("description", "").replace("\n", " ")[:200],
                "url":         f"https://www.youtube.com/watch?v={video_id}",
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
        print(f"  Fetched {len(videos)} videos so far...")
    return videos

def enrich_videos_with_duration(youtube, videos):
    enriched = []
    for i in range(0, len(videos), 50):
        batch = videos[i:i+50]
        ids = ",".join(v["video_id"] for v in batch)
        resp = youtube.videos().list(
            part="contentDetails",
            id=ids
        ).execute()
        duration_map = {}
        for item in resp.get("items", []):
            dur = item["contentDetails"]["duration"]
            duration_map[item["id"]] = parse_duration(dur)
        for v in batch:
            v["duration"] = duration_map.get(v["video_id"], "")
            enriched.append(v)
    return enriched

def parse_duration(iso_duration):
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration)
    if not match:
        return ""
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0)
    s = int(match.group(3) or 0)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def fetch_all_playlists(youtube, channel_id):
    playlists = []
    page_token = None
    while True:
        resp = youtube.playlists().list(
            part="snippet,contentDetails",
            channelId=channel_id,
            maxResults=50,
            pageToken=page_token
        ).execute()
        for item in resp.get("items", []):
            snippet = item["snippet"]
            playlist_id = item["id"]
            playlists.append({
                "playlist_id":  playlist_id,
                "title":        snippet.get("title", ""),
                "published":    snippet.get("publishedAt", "")[:10],
                "description":  snippet.get("description", "").replace("\n", " ")[:200],
                "item_count":   item["contentDetails"]["itemCount"],
                "url":          f"https://www.youtube.com/playlist?list={playlist_id}",
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return playlists

def write_tsv(rows, fieldnames, filename):
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {filename}")

def main():
    youtube = build("youtube", "v3", developerKey=API_KEY)

    print("Fetching channel info...")
    channel_id, uploads_playlist_id = get_channel_id(youtube)

    print("Fetching all videos...")
    videos = fetch_all_videos(youtube, uploads_playlist_id)
    print(f"Found {len(videos)} videos. Fetching durations...")
    videos = enrich_videos_with_duration(youtube, videos)
    videos.sort(key=lambda v: v["published"])
    write_tsv(videos,
              ["published", "title", "duration", "url", "description", "video_id"],
              "youtube_videos.tsv")

    print("Fetching all playlists...")
    playlists = fetch_all_playlists(youtube, channel_id)
    playlists.sort(key=lambda p: p["published"])
    write_tsv(playlists,
              ["published", "title", "item_count", "url", "description", "playlist_id"],
              "youtube_playlists.tsv")

    print("\nDone! Next step: run youtube_correlate.py to match against your show history.")

if __name__ == "__main__":
    main()