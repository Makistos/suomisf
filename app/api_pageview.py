"""Pageview logging endpoint."""
from typing import Optional

from flask import request
from flask.wrappers import Response
from sqlalchemy import text

from app import app
from app.route_helpers import new_session

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

try:
    import geoip2.database
    _geoip = geoip2.database.Reader('/var/lib/GeoIP/GeoLite2-Country.mmdb')
    _HAS_GEOIP = True
except Exception:
    _geoip = None
    _HAS_GEOIP = False


def _parse_ua(ua_string: str):
    if not _ua_parse or not ua_string:
        return None, None, None
    ua = _ua_parse(ua_string)
    major = ua.browser.version_string.split('.')[0]
    browser = f"{ua.browser.family} {major}"
    device_type = 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'desktop'
    return browser, ua.os.family, device_type


def _get_country(ip: str) -> Optional[str]:
    if not _HAS_GEOIP:
        return None
    try:
        return _geoip.country(ip).country.iso_code  # type: ignore[union-attr]
    except Exception:
        return None


def _is_valid_path(path: str) -> bool:
    return path in VALID_PATHS or any(path.startswith(p) for p in VALID_PREFIXES)


@app.route('/api/pageview', methods=['POST'])
def api_pageview() -> Response:
    try:
        data = request.get_json(silent=True) or {}
        path = data.get('path', '')
        if not path or not _is_valid_path(path):
            return Response('', status=204)

        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        if ',' in ip:
            ip = ip.split(',')[0].strip()

        ua_string = request.headers.get('User-Agent', '')
        browser, os_name, device_type = _parse_ua(ua_string)
        country = _get_country(ip)

        session = new_session()
        session.execute(
            text("""
                INSERT INTO suomisf.pageview
                    (ip, path, user_agent, country, browser, os, device_type)
                VALUES
                    (:ip, :path, :ua, :country, :browser, :os, :device_type)
            """),
            {
                'ip': ip, 'path': path, 'ua': ua_string or None,
                'country': country, 'browser': browser,
                'os': os_name, 'device_type': device_type,
            }
        )
        session.commit()
        session.close()
    except Exception:
        pass  # Never fail the client on analytics errors

    return Response('', status=204)
