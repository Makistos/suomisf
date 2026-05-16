"""Pageview logging and visitor statistics endpoints."""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from flask import abort, request
from flask.wrappers import Response
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import app
from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.route_helpers import new_session

BOT_UA_RE = re.compile(
    r'bot|spider|crawler|zgrab|Censys|Applebot|Bytespider'
    r'|bingbot|Baiduspider|Amazonbot|OAI-Search|Googlebot'
    r'|masscan|nikto|sqlmap|python-requests|libwww|curl'
    r'|facebookexternalhit|Twitterbot|Slackbot|LinkedInBot'
    r'|Dataprovider|SemrushBot|AhrefsBot|DotBot|MJ12bot'
    r'|PetalBot|YandexBot|archive\.org_bot',
    re.IGNORECASE,
)

VALID_PATHS = {
    '/', '/awards', '/bookindex', '/faq', '/shortstoryindex',
    '/people', '/magazines', '/bookseries', '/pubseries', '/publishers',
    '/tags', '/login', '/changes', '/latest', '/nonfiction', '/stats',
    '/home-alt',
}
VALID_PREFIXES = (
    '/awards/', '/people/', '/magazines/', '/issues/', '/articles/', '/works/',
    '/editions/', '/bookseries/', '/pubseries/', '/publishers/', '/shorts/',
    '/tags/', '/users/',
)

_ua_parse = None
try:
    from user_agents import parse as _ua_parse  # type: ignore[import]
except ImportError:
    pass

_requests = None
try:
    import requests as _requests  # type: ignore[import]
except ImportError:
    pass

# Prefer City DB (has city + country); fall back to Country DB.
_geoip = None
_geoip_has_city = False
try:
    import geoip2.database
    try:
        _geoip = geoip2.database.Reader('/var/lib/GeoIP/GeoLite2-City.mmdb')
        _geoip_has_city = True
    except Exception:
        _geoip = geoip2.database.Reader('/var/lib/GeoIP/GeoLite2-Country.mmdb')
except Exception:
    pass


def _parse_ua(ua_string: str):
    if not _ua_parse or not ua_string:
        return None, None, None
    ua = _ua_parse(ua_string)
    major = ua.browser.version_string.split('.')[0]
    browser = f"{ua.browser.family} {major}"
    device_type = 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'desktop'
    return browser, ua.os.family, device_type


def _lookup_geoip(ip: str) -> Tuple[Optional[str], Optional[str]]:
    """Try local GeoIP database. Returns (city, country_iso) or (None, None)."""
    if not _geoip:
        return None, None
    try:
        if _geoip_has_city:
            r = _geoip.city(ip)  # type: ignore[union-attr]
            return r.city.name, r.country.iso_code
        else:
            r = _geoip.country(ip)  # type: ignore[union-attr]
            return None, r.country.iso_code
    except Exception:
        return None, None


def _lookup_ipapi(ip: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Call ip-api.com for a single IP. Returns (city, country_iso, operator) or (None, None, None)."""
    if not _requests:
        return None, None, None
    try:
        resp = _requests.post(
            'http://ip-api.com/batch',
            json=[ip],
            params={'fields': 'query,countryCode,city,org'},
            timeout=5,
        )
        if resp.ok:
            entry = resp.json()[0]
            city = entry.get('city') or None
            country = entry.get('countryCode') or None
            operator = entry.get('org') or None
            return city, country, operator
    except Exception:
        pass
    return None, None, None


def _get_location(ip: str, session: Session) -> Tuple[Optional[str], Optional[str]]:
    """Return (city, country_iso) for an IP.

    Checks the ip_location DB cache first. For new IPs, always calls ip-api.com
    to capture the operator name (GeoIP2 doesn't provide it). GeoIP2 city/country
    take precedence when available; ip-api.com values are used as fallback.
    """
    row = session.execute(
        text("SELECT city, country FROM suomisf.ip_location WHERE ip = :ip"),
        {'ip': ip},
    ).fetchone()
    if row is not None:
        return row.city, row.country

    city, country = _lookup_geoip(ip)
    ip_city, ip_country, operator = _lookup_ipapi(ip)
    if city is None:
        city = ip_city
    if country is None:
        country = ip_country

    session.execute(
        text("""
            INSERT INTO suomisf.ip_location (ip, city, country, operator)
            VALUES (:ip, :city, :country, :operator)
            ON CONFLICT (ip) DO NOTHING
        """),
        {'ip': ip, 'city': city, 'country': country, 'operator': operator},
    )
    return city, country


def _is_valid_path(path: str) -> bool:
    return path in VALID_PATHS or any(path.startswith(p) for p in VALID_PREFIXES)


def _cutoff(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


@app.route('/api/pageview', methods=['POST'])
def api_pageview() -> Response:
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path', '')
        if not path or not _is_valid_path(path):
            app.logger.info(f"No path: {data}")
            return Response('', status=204)

        ua_string = request.headers.get('User-Agent', '')
        if not ua_string or BOT_UA_RE.search(ua_string):
            return Response('', status=204)

        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        if ',' in ip:
            ip = ip.split(',')[0].strip()
        browser, os_name, device_type = _parse_ua(ua_string)

        session = new_session()
        city, country = _get_location(ip, session)

        session.execute(
            text("""
                INSERT INTO suomisf.pageview
                    (ip, path, user_agent, city, country, browser, os, device_type)
                VALUES
                    (:ip, :path, :ua, :city, :country, :browser, :os, :device_type)
            """),
            {
                'ip': ip, 'path': path, 'ua': ua_string or None,
                'city': city, 'country': country, 'browser': browser,
                'os': os_name, 'device_type': device_type,
            }
        )
        session.commit()
        session.close()
    except Exception as e:
        app.logger.exception(e)

    return Response('', status=204)


def _require_admin() -> None:
    if not get_jwt().get('is_administrator', False):
        abort(403)


def _days_param(default: int = 30) -> int:
    try:
        return min(int(request.args.get('days', default)), 365)
    except (ValueError, TypeError):
        return default


@app.route('/api/stats/visitors/daily', methods=['GET'])
@jwt_required()
def api_stats_visitors_daily() -> Response:
    _require_admin()
    days = _days_param(30)
    session = new_session()
    rows = session.execute(
        text("""
            SELECT DATE(created_at AT TIME ZONE 'Europe/Helsinki') AS date,
                   COUNT(DISTINCT ip) AS visitors,
                   COUNT(*) AS pageviews
            FROM suomisf.pageview
            WHERE created_at >= :cutoff
            GROUP BY 1 ORDER BY 1
        """),
        {'cutoff': _cutoff(days)},
    ).fetchall()
    session.close()
    return make_api_response(ResponseType(
        [{'date': str(r.date), 'visitors': r.visitors, 'pageviews': r.pageviews} for r in rows],
        200,
    ))


@app.route('/api/stats/visitors/locations', methods=['GET'])
@jwt_required()
def api_stats_visitors_locations() -> Response:
    _require_admin()
    days = _days_param(90)
    session = new_session()
    rows = session.execute(
        text("""
            SELECT COALESCE(city, country, '?') AS location,
                   COUNT(DISTINCT ip) AS visitors
            FROM suomisf.pageview
            WHERE created_at >= :cutoff
            GROUP BY 1 ORDER BY visitors DESC LIMIT 20
        """),
        {'cutoff': _cutoff(days)},
    ).fetchall()
    session.close()
    return make_api_response(ResponseType(
        [{'location': r.location, 'visitors': r.visitors} for r in rows],
        200,
    ))


@app.route('/api/stats/visitors/breakdown', methods=['GET'])
@jwt_required()
def api_stats_visitors_breakdown() -> Response:
    _require_admin()
    days = _days_param(90)
    session = new_session()

    def _col(column: str) -> list:
        rows = session.execute(
            text(f"""
                SELECT COALESCE({column}, '?') AS label, COUNT(*) AS count
                FROM suomisf.pageview
                WHERE created_at >= :cutoff
                  AND {column} IS NOT NULL
                GROUP BY 1 ORDER BY count DESC LIMIT 10
            """),
            {'cutoff': _cutoff(days)},
        ).fetchall()
        return [{'label': r.label, 'count': r.count} for r in rows]

    result = {
        'browsers': _col('browser'),
        'os': _col('os'),
        'devices': _col('device_type'),
    }
    session.close()
    return make_api_response(ResponseType(result, 200))
