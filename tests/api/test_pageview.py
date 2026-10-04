"""
Visitor analytics: the page-view beacon and the admin statistics built on
it (coverage plan step B5).

ip-api.com is replaced by a fake that counts its calls. Test visits use
addresses from 203.0.113.0/24 (reserved for documentation), and every row
they create is deleted afterwards.
"""
import pytest
from sqlalchemy import text

import app.api_pageview as pageview
from app.route_helpers import new_session

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'

IP = '203.0.113.7'
OTHER_IP = '203.0.113.8'
FIREFOX = ('Mozilla/5.0 (X11; Linux x86_64; rv:131.0) '
           'Gecko/20100101 Firefox/131.0')


def _rows(ip):
    session = new_session()
    try:
        return session.execute(
            text('SELECT path, city, country, browser, os, device_type '
                 'FROM suomisf.pageview WHERE ip = :ip ORDER BY id'),
            {'ip': ip}).fetchall()
    finally:
        session.close()


def _clean():
    session = new_session()
    try:
        for table in ('pageview', 'ip_location'):
            session.execute(text(f'DELETE FROM suomisf.{table} WHERE ip IN (:a, :b)'),
                            {'a': IP, 'b': OTHER_IP})
        session.commit()
    finally:
        session.close()


class FakeIpApi:
    def __init__(self):
        self.calls = []

    def post(self, url, json=None, **kwargs):
        self.calls.append(json)
        ip = json[0]
        return _FakeResponse([{'query': ip, 'countryCode': 'FI',
                               'city': 'Tampere', 'org': 'Test Operator Oy'}])


class _FakeResponse:
    ok = True

    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


@pytest.fixture
def ip_api(app, monkeypatch):
    fake = FakeIpApi()
    monkeypatch.setattr(pageview._requests, 'post', fake.post)
    _clean()
    yield fake
    _clean()


def _visit(client, path, ua=FIREFOX, forwarded=f'{IP}, 10.0.0.1'):
    # An empty User-Agent must be sent explicitly: the test client would
    # otherwise send its own "Werkzeug/..." one.
    headers = {'X-Forwarded-For': forwarded, 'User-Agent': ua or ''}
    response = client.post('/api/p', json={'path': path}, headers=headers)
    assert response.status_code == 204
    return response


def test_pageview_is_logged_with_location(client, ip_api):
    _visit(client, '/works/1')
    rows = _rows(IP)
    assert len(rows) == 1
    row = rows[0]
    assert (row.path, row.city, row.country) == ('/works/1', 'Tampere', 'FI')
    assert row.browser.startswith('Firefox') and row.device_type == 'desktop'


def test_location_is_looked_up_once_per_ip(client, ip_api):
    _visit(client, '/works/1')
    _visit(client, '/people/1')
    assert len(_rows(IP)) == 2
    assert ip_api.calls == [[IP]]


@pytest.mark.parametrize('path,ua', [
    ('/works/1', 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'),
    ('/works/1', 'Mozilla/5.0 (X11; Linux x86_64) HeadlessChrome/120.0 Safari/537.36'),
    ('/works/1', None),
    ('/wp-login.php', FIREFOX),
    ('', FIREFOX),
])
def test_bots_and_unknown_paths_are_not_logged(client, ip_api, path, ua):
    _visit(client, path, ua=ua)
    assert _rows(IP) == []
    assert ip_api.calls == []


# ---------------------------------------------------------------------------
# Admin statistics
# ---------------------------------------------------------------------------

def _headers(client, name, password):
    resp = client.post('/api/login', json={'username': name, 'password': password})
    return {'Authorization': f"Bearer {resp.get_json()['access_token']}"}


STATS = ['/api/stats/site/daily', '/api/stats/site/locations',
         '/api/stats/site/log', '/api/stats/site/breakdown']


@pytest.mark.parametrize('path', STATS)
def test_stats_are_admin_only(client, path):
    assert client.get(path).status_code == 401
    user = _headers(client, TEST_USER_NAME, TEST_USER_PASSWORD)
    assert client.get(path, headers=user).status_code == 403


def test_stats_include_a_logged_visit(client, ip_api):
    _visit(client, '/works/1')
    _visit(client, '/people/1', forwarded=OTHER_IP)
    admin = _headers(client, TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)

    for path in STATS:
        response = client.get(f'{path}?days=1', headers=admin)
        assert response.status_code == 200, (path, response.get_json())

    log = client.get(f'/api/stats/site/log?days=1&ip={IP}', headers=admin).get_json()
    assert log['total'] == 1
    assert [r['path'] for r in log['rows']] == ['/works/1']

    by_operator = client.get('/api/stats/site/log?days=1&operator=Test%20Operator',
                             headers=admin).get_json()
    assert by_operator['total'] == 2

    breakdown = client.get('/api/stats/site/breakdown?days=1', headers=admin).get_json()
    assert 'Firefox' in str(breakdown)


def test_stats_log_bad_paging_falls_back(client, ip_api):
    admin = _headers(client, TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    response = client.get('/api/stats/site/log?page=x&per_page=y', headers=admin)
    assert response.status_code == 200
