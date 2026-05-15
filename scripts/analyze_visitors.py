#!/usr/bin/env python3
"""Analyze nginx access logs for real human visitors.

Usage:
    python3 scripts/analyze_visitors.py [LOG_DIR] [--seed]

    Without --seed: prints a human-readable report (unchanged behaviour).
    With    --seed: also inserts one row per unique (IP, day) into
                    suomisf.pageview.  Requires DATABASE_URL in the
                    environment (or .env file) and
                    /var/lib/GeoIP/GeoLite2-Country.mmdb for country codes.

Visitors confirmed via CORS OPTIONS preflight are marked with *.
"""

import gzip
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

LOG_DIR = Path("/var/log/nginx")
DOMAIN = "sf-bibliografia.fi"
SCRAPER_REFERER = "135.181.155.80"  # raw-IP scraper cluster
GEOIP_DB = Path("/var/lib/GeoIP/GeoLite2-Country.mmdb")

# ip-api.com — used for the human-readable report only
GEOIP_URL = "http://ip-api.com/batch"
GEOIP_BATCH_SIZE = 100
GEOIP_REQUESTS_PER_MIN = 45

BOT_UA_RE = re.compile(
    r"bot|spider|crawler|zgrab|Censys|ClaudeBot|Applebot"
    r"|bingbot|Baiduspider|Amazonbot|OAI-Search|Najdu"
    r"|masscan|nikto|sqlmap|python-requests|libwww|curl",
    re.IGNORECASE,
)

# Standard nginx combined log format — path is now a named group
LOG_RE = re.compile(
    r'(?P<ip>\S+) \S+ \S+ \[(?P<time>[^\]]+)\] '
    r'"(?P<method>\S+) (?P<path>\S+) [^"]*" '
    r'\d+ \d+ '
    r'"(?P<referer>[^"]*)" '
    r'"(?P<ua>[^"]*)"'
)


def is_real_user(method: str, referer: str, ua: str) -> bool:
    if BOT_UA_RE.search(ua):
        return False
    if not ua or ua == "-":
        return False
    if method == "OPTIONS":
        return True
    if DOMAIN in referer and SCRAPER_REFERER not in referer:
        return True
    return False


def open_log(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", errors="replace")
    return open(path, errors="replace")


# ---------------------------------------------------------------------------
# Geolocation — ip-api.com for the report
# ---------------------------------------------------------------------------

def geolocate(ips: list[str]) -> dict[str, str]:
    geo: dict[str, str] = {}
    for i in range(0, len(ips), GEOIP_BATCH_SIZE):
        batch = ips[i:i + GEOIP_BATCH_SIZE]
        try:
            resp = requests.post(
                GEOIP_URL,
                json=batch,
                params={"fields": "query,country,city,org"},
                timeout=15,
            )
            if resp.ok:
                for entry in resp.json():
                    ip = entry.get("query", "")
                    country = entry.get("country", "?")
                    city = entry.get("city", "")
                    org = entry.get("org", "")
                    location = city if city else country
                    geo[ip] = f"{location}, {country} — {org}"
        except Exception as exc:
            print(f"GeoIP lookup failed: {exc}", file=sys.stderr)
            for ip in batch:
                geo.setdefault(ip, ip)
        if i + GEOIP_BATCH_SIZE < len(ips):
            time.sleep(60 / GEOIP_REQUESTS_PER_MIN)
    return geo


# ---------------------------------------------------------------------------
# Geolocation + UA parsing — for DB seeding
# ---------------------------------------------------------------------------

def load_geoip_reader():
    try:
        import geoip2.database
        return geoip2.database.Reader(str(GEOIP_DB))
    except Exception as exc:
        print(f"GeoIP DB unavailable ({exc}), country will be NULL.", file=sys.stderr)
        return None


def get_country(reader, ip: str) -> Optional[str]:
    if not reader:
        return None
    try:
        return reader.country(ip).country.iso_code
    except Exception:
        return None


def parse_ua(ua_string: str):
    try:
        from user_agents import parse as ua_parse  # type: ignore[import]
        ua = ua_parse(ua_string)
        major = ua.browser.version_string.split(".")[0]
        browser = f"{ua.browser.family} {major}"
        device_type = "mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "desktop"
        return browser, ua.os.family, device_type
    except Exception:
        return None, None, None


# ---------------------------------------------------------------------------
# DB seeding
# ---------------------------------------------------------------------------

def seed_db(
    rows: list[tuple],  # (ip, first_dt, first_ua)
    geoip_reader,
) -> None:
    """Insert one row per (IP, day) into suomisf.pageview."""
    from dotenv import load_dotenv
    load_dotenv(".env")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set — cannot seed.", file=sys.stderr)
        return

    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed — cannot seed.", file=sys.stderr)
        return

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    inserted = 0

    for ip, dt, ua in rows:
        country = get_country(geoip_reader, ip)
        browser, os_name, device_type = parse_ua(ua)
        cur.execute(
            """
            INSERT INTO suomisf.pageview
                (created_at, ip, path, user_agent, country, browser, os, device_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (dt, ip, "/", ua or None, country, browser, os_name, device_type),
        )
        inserted += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {inserted} rows into suomisf.pageview.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    seed = "--seed" in sys.argv
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    log_dir = Path(positional[0]) if positional else LOG_DIR

    # day -> {ip -> (first_dt, first_ua)}
    daily: dict[str, dict[str, tuple]] = defaultdict(dict)
    options_ips: set[str] = set()

    files = sorted(log_dir.glob("access.log*"))
    if not files:
        print(f"No access.log* files found in {log_dir}", file=sys.stderr)
        sys.exit(1)

    for f in files:
        print(f"Reading {f.name} ...", file=sys.stderr)
        with open_log(f) as fh:
            for line in fh:
                m = LOG_RE.match(line)
                if not m:
                    continue
                method = m.group("method")
                referer = m.group("referer")
                ua = m.group("ua")
                if not is_real_user(method, referer, ua):
                    continue
                try:
                    dt = datetime.strptime(m.group("time"), "%d/%b/%Y:%H:%M:%S %z")
                except ValueError:
                    continue
                ip = m.group("ip")
                day = dt.strftime("%Y-%m-%d")
                if ip not in daily[day]:
                    daily[day][ip] = (dt, ua)
                if method == "OPTIONS":
                    options_ips.add(ip)

    all_ips = sorted({ip for day_ips in daily.values() for ip in day_ips})
    if not all_ips:
        print("No real user visits found.")
        return

    # --- Human-readable report (unchanged) ----------------------------------
    print(f"Geolocating {len(all_ips)} unique IPs ...", file=sys.stderr)
    geo = geolocate(all_ips)

    print(f"\n{'=' * 70}")
    print("Real human visitors by day")
    print(f"{'=' * 70}\n")

    for day in sorted(daily):
        day_ips = daily[day]
        print(f"{day}  —  {len(day_ips)} unique visitor(s)")
        for ip in sorted(day_ips):
            marker = " *" if ip in options_ips else ""
            location = geo.get(ip, ip)
            print(f"  {ip:<18}  {location}{marker}")
        print()

    if options_ips:
        print("* confirmed interactive user (sent CORS OPTIONS preflight)")

    # --- DB seeding ---------------------------------------------------------
    if seed:
        rows = [
            (ip, dt, ua)
            for day_ips in daily.values()
            for ip, (dt, ua) in day_ips.items()
        ]
        print(f"\nSeeding {len(rows)} rows into the database ...", file=sys.stderr)
        geoip_reader = load_geoip_reader()
        seed_db(rows, geoip_reader)
        if geoip_reader:
            geoip_reader.close()


if __name__ == "__main__":
    main()
