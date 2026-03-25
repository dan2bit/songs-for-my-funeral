#!/usr/bin/env python3
"""
bandsintown_check.py — Check Bandsintown for upcoming shows matching your
venue list and/or seen-before artist list.

USAGE
-----
  # Mode 1 — Given an artist, check all venues on your venue list:
  python3 bandsintown_check.py --artist "Kingfish"

  # Mode 2 — Given a venue, check all seen-before artists at that venue:
  python3 bandsintown_check.py --venue "The Birchmere"

  # Mode 3 — Full scan: all seen-before artists × all venues:
  python3 bandsintown_check.py --scan

OPTIONS
-------
  --artist ARTIST      Artist name (partial match OK)
  --venue VENUE        Venue name (partial match OK against venues.tsv)
  --scan               Scan all artists × all venues
  --days N             Only show events in the next N days (default: 365)
  --app-id ID          Bandsintown app_id string (default: js_bandsintown)
  --delay SECS         Seconds between API calls in scan mode (default: 0.5)
  --no-verify          Disable SSL certificate verification (see SSL note below)

DATA FILES (same directory as this script)
-----------
  live_shows_history.tsv   — seen-before artist list
  venues.tsv               — venue list with city/region
  live_shows_2026.tsv      — upcoming ticketed shows

OUTPUT
------
  Matching upcoming events are printed to stdout:

    ✓ HAVE TICKET  2026-07-11  Shovels & Rope @ The Birchmere (Alexandria, VA)
    → BUY TICKETS  2026-08-15  Larkin Poe @ The Birchmere (Alexandria, VA)
                   https://www.bandsintown.com/t/...

APP_ID NOTE
-----------
  Bandsintown now validates app_id against registered applications and will
  return HTTP 403 for arbitrary strings. The default app_id "js_bandsintown"
  is the ID used by Bandsintown's own embeddable JavaScript widget and works
  for public read-only access. If this ever stops working, register a free
  app at https://corp.bandsintown.com/data-applications-terms and pass your
  key via --app-id.

SSL CERTIFICATE NOTE
--------------------
  If you see: [SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate

  This script automatically uses certifi's CA bundle when available, which
  fixes the most common macOS Homebrew Python SSL issue. If you don't have
  certifi, install it:
    python3 -m pip install certifi

  If that still doesn't work, use the quick workaround (fine for this
  read-only script):
    python3 bandsintown_check.py --no-verify --artist "Larkin Poe"

NOTES ON THE BANDSINTOWN PUBLIC API
------------------------------------
  - Base URL: https://rest.bandsintown.com/artists/{name}/events
  - Query params: app_id (required), date=upcoming
  - Returns JSON array of events with venue, datetime, offers
  - No venue search endpoint — venue matching is done client-side
  - Artist name is URL-encoded; special chars and spaces work fine
  - Response is [] for unknown artists, "warn" string for 404-ish cases
  - Ticket links come from offers[].url where offers[].type == "Tickets"
  - Rate limit: undocumented; 0.5s delay is conservative for scan mode
"""

import argparse
import csv
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

# ── config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
HISTORY_TSV  = os.path.join(SCRIPT_DIR, "live_shows_history.tsv")
VENUES_TSV   = os.path.join(SCRIPT_DIR, "venues.tsv")
UPCOMING_TSV = os.path.join(SCRIPT_DIR, "live_shows_2026.tsv")

BIT_BASE      = "https://rest.bandsintown.com/artists/{name}/events"
# "js_bandsintown" is the app_id used by Bandsintown's own JS widget;
# it works for public read-only access without registration.
DEFAULT_APPID = "js_bandsintown"

# Similarity threshold for venue name fuzzy matching (0.0–1.0)
VENUE_MATCH_THRESHOLD = 0.55


# ── data loading ──────────────────────────────────────────────────────────────
def load_tsv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def get_seen_artists(history_rows):
    """Return sorted unique artist names from history."""
    artists = set()
    for r in history_rows:
        name = r.get("Artist", "").strip()
        if name:
            artists.add(name)
    return sorted(artists)


def get_venues(venue_rows):
    """
    Return list of dicts with name, city, region extracted from address.
    Address format: "123 Street, City, ST ZIPCODE" or "..., City, State, USA"
    """
    venues = []
    for r in venue_rows:
        name = r.get("Venue Name", "").strip()
        addr = r.get("Address", "").strip()
        city, region = parse_city_region(addr)
        venues.append({"name": name, "city": city, "region": region})
    return venues


def parse_city_region(address):
    """
    Parse city and region (state abbrev) out of an address string.
    Handles:
      "3701 Mount Vernon Ave, Alexandria, VA 22305"
      "815 V St NW, Washington, DC 20001"
      "1551 Trap Rd, Vienna, VA 22182"
    """
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 3:
        city = parts[-2].strip()
        # Last part might be "VA 22305" or just "VA" — grab first token
        region_part = parts[-1].strip()
        region = region_part.split()[0] if region_part else ""
        return city, region
    elif len(parts) == 2:
        return parts[-1].strip(), ""
    return "", ""


def get_ticketed_shows(upcoming_rows):
    """
    Return a dict of (artist_normalized, venue_name_normalized) → date string
    for shows with Status == "upcoming" (i.e. ticket already purchased).
    """
    ticketed = {}
    for r in upcoming_rows:
        status = r.get("Status", "").strip().lower()
        if status == "upcoming":
            artist = normalize(r.get("Artist", ""))
            venue  = normalize(r.get("Venue Name", ""))
            date   = r.get("Show Date", "").strip()
            if artist and venue:
                ticketed[(artist, venue)] = date
    return ticketed


# ── normalization + matching ───────────────────────────────────────────────────
def normalize(s):
    """Lowercase, strip, collapse whitespace."""
    return " ".join(s.lower().split())


def similarity(a, b):
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def venue_matches(bit_venue_name, bit_city, our_venues, threshold=VENUE_MATCH_THRESHOLD):
    """
    Return matching our_venues entries for a BIT event's venue name + city.
    Matches on:
      - Normalized substring containment (either direction)
      - Or fuzzy similarity >= threshold
    City must roughly agree (unless one is blank).
    Returns list of matching venue dicts (usually 0 or 1).
    """
    matches = []
    bn = normalize(bit_venue_name)
    bc = normalize(bit_city)
    for v in our_venues:
        vn = normalize(v["name"])
        vc = normalize(v["city"])

        # City must roughly agree (unless one is blank)
        if bc and vc and bc != vc:
            if bc not in vc and vc not in bc:
                continue

        # Name match: substring or fuzzy
        if bn in vn or vn in bn or similarity(bn, vn) >= threshold:
            matches.append(v)
    return matches


def artist_matches_query(artist_name, query):
    """True if query (lowercased) is a substring of the artist name."""
    return query.lower() in artist_name.lower()


def venue_matches_query(venue_name, query):
    """True if query (lowercased) is a substring of the venue name."""
    return query.lower() in venue_name.lower()


# ── SSL context ────────────────────────────────────────────────────────────────
def make_ssl_context(verify=True):
    """
    Build an SSL context for urllib.

    When verify=True (default), tries to load the certifi CA bundle first —
    this fixes the common Homebrew Python 3.14 on macOS issue where the
    bundled OpenSSL doesn't have current CA certificates. Falls back to
    the default system context if certifi isn't installed.

    When verify=False, returns an unverified context (--no-verify flag).
    """
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    # Try certifi first — fixes Homebrew Python SSL issues on macOS
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        return ctx
    except ImportError:
        pass

    # Fall back to default context (uses system certs)
    return ssl.create_default_context()


# ── Bandsintown API ───────────────────────────────────────────────────────────
def fetch_artist_events(artist_name, app_id, ssl_context, date_param="upcoming"):
    """
    Fetch upcoming events for an artist from Bandsintown public API.
    Returns list of event dicts, or [] on error / unknown artist.
    """
    encoded = urllib.parse.quote(artist_name, safe="")
    url = (
        f"{BIT_BASE.format(name=encoded)}"
        f"?app_id={urllib.parse.quote(app_id)}"
        f"&date={date_param}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"{app_id}/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
            raw = resp.read().decode("utf-8")
    except ssl.SSLCertVerificationError:
        print(
            f"\n  [SSL error]\n"
            f"  Install certifi to fix this permanently:\n"
            f"    python3 -m pip install certifi\n"
            f"  Or use --no-verify as a quick workaround.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(
                f"\n  [403 Forbidden for {artist_name!r}]\n"
                f"  The app_id {app_id!r} is being rejected by Bandsintown.\n"
                f"  Try the default: python3 bandsintown_check.py --app-id js_bandsintown\n"
                f"  Or register a free app at https://corp.bandsintown.com/data-applications-terms\n",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"  [API error for {artist_name!r}]: HTTP {e.code}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [API error for {artist_name!r}]: {e}", file=sys.stderr)
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    # BIT returns the string "warn" (not JSON array) for unknown artists
    if not isinstance(data, list):
        return []

    return data


def event_ticket_url(event):
    """Return the first available ticket URL from an event's offers, or None."""
    for offer in event.get("offers", []):
        if offer.get("type") == "Tickets" and offer.get("status") == "available":
            return offer.get("url")
    # Fall back to any offer URL
    for offer in event.get("offers", []):
        if offer.get("url"):
            return offer.get("url")
    return None


def event_date(event):
    """Parse event datetime string to date object, or None."""
    dt_str = event.get("datetime", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str[:19], fmt).date()
        except ValueError:
            continue
    return None


# ── result formatting ─────────────────────────────────────────────────────────
def print_result(event, artist_name, matched_venue, ticket_status):
    """
    Print a single result line.
    ticket_status: "have_ticket" | "available" | "none"
    """
    dt       = event_date(event)
    date_str = dt.isoformat() if dt else "????-??-??"
    venue    = event.get("venue", {})
    city     = venue.get("city", "")
    region   = venue.get("region", "")
    location = f"{city}, {region}" if region else city

    if ticket_status == "have_ticket":
        prefix = "✓ HAVE TICKET"
    elif ticket_status == "available":
        prefix = "→ BUY TICKETS"
    else:
        prefix = "  (no tickets)"

    print(f"  {prefix}  {date_str}  {artist_name} @ {matched_venue['name']} ({location})")

    if ticket_status == "available":
        url = event_ticket_url(event)
        if url:
            print(f"                 {url}")

    if ticket_status == "none":
        bit_url = event.get("url", "")
        if bit_url:
            print(f"                 {bit_url}")


# ── core matching logic ────────────────────────────────────────────────────────
def check_events_against_venues(artist_name, events, our_venues, ticketed, cutoff_date, ssl_context):
    """
    Filter a list of BIT events to those at our venues, within cutoff date,
    and print results. Returns count of matches.
    """
    count = 0
    for event in events:
        dt = event_date(event)
        if dt is None or dt > cutoff_date:
            continue

        bit_venue = event.get("venue", {})
        bvn = bit_venue.get("name", "")
        bvc = bit_venue.get("city", "")
        matched = venue_matches(bvn, bvc, our_venues)
        if not matched:
            continue

        mv   = matched[0]
        akey = normalize(artist_name)
        vnk  = normalize(mv["name"])

        if (akey, vnk) in ticketed:
            status = "have_ticket"
        elif event_ticket_url(event):
            status = "available"
        else:
            status = "none"

        print_result(event, artist_name, mv, status)
        count += 1
    return count


# ── modes ─────────────────────────────────────────────────────────────────────
def mode_artist(query, our_venues, ticketed, cutoff, app_id, ssl_context):
    """Mode 1: given an artist query, check all venues."""
    print(f"\n── Artist search: {query!r} ──────────────────────────────────────")
    history    = load_tsv(HISTORY_TSV)
    artists    = get_seen_artists(history)
    candidates = [a for a in artists if artist_matches_query(a, query)]

    if not candidates:
        candidates = [query]
        print(f"  (not in seen-before list; searching BIT directly for {query!r})")

    total = 0
    for artist in candidates:
        print(f"\n  Fetching events for: {artist}")
        events = fetch_artist_events(artist, app_id, ssl_context)
        n = check_events_against_venues(artist, events, our_venues, ticketed, cutoff, ssl_context)
        if n == 0:
            print("  (no upcoming matches at your venues)")
        total += n
    return total


def mode_venue(query, our_venues, ticketed, cutoff, app_id, ssl_context, delay):
    """Mode 2: given a venue query, check all seen-before artists."""
    print(f"\n── Venue search: {query!r} ───────────────────────────────────────")
    matched_venues = [v for v in our_venues if venue_matches_query(v["name"], query)]
    if not matched_venues:
        print(f"  No venue matching {query!r} found in venues.tsv")
        return 0

    for mv in matched_venues:
        print(f"  Checking venue: {mv['name']} ({mv['city']}, {mv['region']})")

    history = load_tsv(HISTORY_TSV)
    artists = get_seen_artists(history)

    total = 0
    for i, artist in enumerate(artists):
        if i > 0 and delay > 0:
            time.sleep(delay)
        events = fetch_artist_events(artist, app_id, ssl_context)
        n = check_events_against_venues(artist, events, matched_venues, ticketed, cutoff, ssl_context)
        total += n

    if total == 0:
        print("\n  No upcoming matches found at this venue for any seen-before artist.")
    return total


def mode_scan(our_venues, ticketed, cutoff, app_id, ssl_context, delay):
    """Mode 3: all seen-before artists × all venues."""
    print("\n── Full scan: all artists × all venues ──────────────────────────")
    history = load_tsv(HISTORY_TSV)
    artists = get_seen_artists(history)
    print(f"  {len(artists)} artists × {len(our_venues)} venues")

    total = 0
    for i, artist in enumerate(artists):
        if i > 0 and delay > 0:
            time.sleep(delay)
        events = fetch_artist_events(artist, app_id, ssl_context)
        if not events:
            continue
        n = check_events_against_venues(artist, events, our_venues, ticketed, cutoff, ssl_context)
        total += n

    if total == 0:
        print("\n  No upcoming matches found.")
    else:
        print(f"\n  Total matches: {total}")
    return total


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Check Bandsintown for upcoming shows matching your venue + artist lists"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--artist", metavar="ARTIST",
                       help="Search for a specific artist at all your venues")
    group.add_argument("--venue",  metavar="VENUE",
                       help="Search for all seen-before artists at a specific venue")
    group.add_argument("--scan",   action="store_true",
                       help="Full scan: all artists × all venues")
    parser.add_argument("--days",      type=int,   default=365,
                        help="Only show events within this many days (default: 365)")
    parser.add_argument("--app-id",    default=DEFAULT_APPID,
                        help=f"Bandsintown app_id (default: {DEFAULT_APPID})")
    parser.add_argument("--delay",     type=float, default=0.5,
                        help="Seconds between API calls in venue/scan mode (default: 0.5)")
    parser.add_argument("--no-verify", action="store_true",
                        help="Disable SSL certificate verification (workaround for SSL errors)")
    args = parser.parse_args()

    if args.no_verify:
        print("  [warning] SSL certificate verification disabled (--no-verify)", file=sys.stderr)

    ssl_context = make_ssl_context(verify=not args.no_verify)
    cutoff      = datetime.now(timezone.utc).date() + timedelta(days=args.days)

    venue_rows    = load_tsv(VENUES_TSV)
    upcoming_rows = load_tsv(UPCOMING_TSV)
    our_venues    = get_venues(venue_rows)
    ticketed      = get_ticketed_shows(upcoming_rows)

    print(f"Loaded {len(our_venues)} venues, {len(ticketed)} ticketed upcoming shows")
    print(f"Checking events through {cutoff.isoformat()}")

    if args.artist:
        mode_artist(args.artist, our_venues, ticketed, cutoff, args.app_id, ssl_context)
    elif args.venue:
        mode_venue(args.venue, our_venues, ticketed, cutoff, args.app_id, ssl_context, args.delay)
    elif args.scan:
        mode_scan(our_venues, ticketed, cutoff, args.app_id, ssl_context, args.delay)


if __name__ == "__main__":
    main()
