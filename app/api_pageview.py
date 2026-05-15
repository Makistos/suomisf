"""Pageview logging and visitor statistics endpoints."""
from typing import Optional

from flask import abort, request
from flask.wrappers import Response
from flask_jwt_extended import get_jwt, jwt_required
from sqlalchemy import text

from app import app
from app.api_helpers import make_api_response
from app.impl import ResponseType
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
            app.logger.info(f"No path: {data}")
            return Response('', status=204)

        app.logger.info(f"Saving location: {data}")
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
            WHERE created_at >= NOW() - INTERVAL '1 day' * :days
            GROUP BY 1 ORDER BY 1
        """),
        {'days': days},
    ).fetchall()
    session.close()
    return make_api_response(ResponseType(
        [{'date': str(r.date), 'visitors': r.visitors, 'pageviews': r.pageviews} for r in rows],
        200,
    ))


@app.route('/api/stats/visitors/countries', methods=['GET'])
@jwt_required()
def api_stats_visitors_countries() -> Response:
    _require_admin()
    days = _days_param(90)
    session = new_session()
    rows = session.execute(
        text("""
            SELECT COALESCE(country, '?') AS country,
                   COUNT(DISTINCT ip) AS visitors
            FROM suomisf.pageview
            WHERE created_at >= NOW() - INTERVAL '1 day' * :days
            GROUP BY 1 ORDER BY visitors DESC LIMIT 20
        """),
        {'days': days},
    ).fetchall()
    session.close()
    return make_api_response(ResponseType(
        [{'country': r.country, 'visitors': r.visitors} for r in rows],
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
                WHERE created_at >= NOW() - INTERVAL '1 day' * :days
                  AND {column} IS NOT NULL
                GROUP BY 1 ORDER BY count DESC LIMIT 10
            """),
            {'days': days},
        ).fetchall()
        return [{'label': r.label, 'count': r.count} for r in rows]

    result = {
        'browsers': _col('browser'),
        'os': _col('os'),
        'devices': _col('device_type'),
    }
    session.close()
    return make_api_response(ResponseType(result, 200))
