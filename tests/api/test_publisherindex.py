"""
SuomiSF API: the light publisher list (GET /api/publisherindex)

The new publisher list page (docs/ui-redesign/pages/publishers.md in the
frontend) needs each publisher's edition count, year span and magazines,
not every edition as GET /api/publishers returns for the current page.
Expected values come from SQL on the test database, so the tests follow
the data.
"""

from sqlalchemy import text

from app.route_helpers import new_session

WSOY = 387
HSFS = 85  # Helsingin Science Fiction Seura ry: publishes Tähtivaeltaja
AIKAKONE = 6  # Aikakone ry: no books, publishes Aikakone


def _rows(sql, **params):
    session = new_session()
    try:
        return session.execute(text(sql), params).all()
    finally:
        session.close()


def _get(client):
    response = client.get('/api/publisherindex')
    response.assert_status(200)
    return response.data


def _by_id(data):
    return {p['id']: p for p in data['publishers']}


class TestPublisherIndex:
    def test_every_publisher_once(self, api_client):
        data = _get(api_client)
        total = _rows('SELECT count(*) FROM suomisf.publisher')[0][0]
        assert data['total'] == total
        assert len(data['publishers']) == total
        assert len(_by_id(data)) == total

    def test_counts_and_years_match_the_editions(self, api_client):
        expected = {r[0]: (r[1], r[2], r[3]) for r in _rows(
            'SELECT publisher_id, count(*), min(pubyear), max(pubyear) '
            'FROM suomisf.edition WHERE publisher_id IS NOT NULL '
            'GROUP BY publisher_id')}
        for pid, p in _by_id(_get(api_client)).items():
            n, first, last = expected.get(pid, (0, None, None))
            assert (p['editions'], p['first_year'], p['last_year']) == \
                (n, first, last), pid

    def test_row_payload(self, api_client):
        wsoy = _by_id(_get(api_client))[WSOY]
        assert wsoy['name'] == 'WSOY'
        assert wsoy['fullname'] == 'Werner Söderström Oy'
        assert wsoy['editions'] > 2000
        assert wsoy['first_year'] < 1900
        assert wsoy['magazines'] == []
        # light: no edition list
        assert 'editions_list' not in wsoy and not isinstance(
            wsoy['editions'], list)

    def test_magazines_with_issue_counts(self, api_client):
        rows = _by_id(_get(api_client))
        hsfs = rows[HSFS]
        names = [m['name'] for m in hsfs['magazines']]
        assert 'Tähtivaeltaja' in names
        aikakone = rows[AIKAKONE]
        assert aikakone['editions'] == 0
        assert aikakone['first_year'] is None
        issues = _rows(
            'SELECT count(*) FROM suomisf.issue i JOIN suomisf.magazine m '
            "ON m.id = i.magazine_id WHERE m.name = 'Aikakone'")[0][0]
        assert aikakone['magazines'] == [
            {'id': aikakone['magazines'][0]['id'], 'name': 'Aikakone',
             'issues': issues}]

    def test_ordered_by_name(self, api_client):
        names = [p['name'] for p in _get(api_client)['publishers']]
        expected = [r[0] for r in _rows(
            'SELECT name FROM suomisf.publisher ORDER BY name, id')]
        assert names == expected
