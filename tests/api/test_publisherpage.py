"""
SuomiSF API: the new publisher page (GET /api/publishers/<id>/summary and
GET /api/publishers/<id>/editions)

The new publisher page (docs/ui-redesign/pages/publishers.md in the
frontend) shows the publisher's facts, series and magazines, and its
editions one page at a time, oldest first by default. GET
/api/publishers/<id> keeps returning every edition for the current page.
Expected values come from SQL on the test database.
"""

from datetime import timedelta

from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app import app
from app.route_helpers import new_session

WSOY = 387
HSFS = 85  # Helsingin Science Fiction Seura ry: publishes Tähtivaeltaja
LE_GUIN_FIRST = 4573  # Pimeyden vasen käsi, WSOY 1976 (Hain-sarja)
EARTHSEA_FIRST = 4565  # Maameren velho, WSOY 1976 (Maameren tarinat 1)
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'


def _rows(sql, **params):
    session = new_session()
    try:
        return session.execute(text(sql), params).all()
    finally:
        session.close()


def _scalar(sql, **params):
    return _rows(sql, **params)[0][0]


def _get(client, path):
    response = client.get(path)
    response.assert_status(200)
    return response.data


def _editions(client, query='', pub=WSOY):
    return _get(client, f'/api/publishers/{pub}/editions{query}')


class TestPublisherSummary:
    def test_facts(self, api_client):
        data = _get(api_client, f'/api/publishers/{WSOY}/summary')
        n, works, first, last = _rows(
            'SELECT count(*), count(DISTINCT work_id), min(pubyear), '
            'max(pubyear) FROM suomisf.edition WHERE publisher_id = :p',
            p=WSOY)[0]
        assert data['name'] == 'WSOY'
        assert data['fullname'] == 'Werner Söderström Oy'
        assert (data['editions'], data['works'], data['first_year'],
                data['last_year']) == (n, works, first, last)
        assert 'description' in data and 'links' in data

    def test_series_with_counts_and_years(self, api_client):
        data = _get(api_client, f'/api/publishers/{WSOY}/summary')
        expected = _scalar('SELECT count(*) FROM suomisf.pubseries '
                           'WHERE publisher_id = :p', p=WSOY)
        assert len(data['series']) == expected
        counts = {r[0]: (r[1], r[2], r[3]) for r in _rows(
            'SELECT ps.id, count(e.id), min(e.pubyear), max(e.pubyear) '
            'FROM suomisf.pubseries ps LEFT JOIN suomisf.edition e '
            'ON e.pubseries_id = ps.id WHERE ps.publisher_id = :p '
            'GROUP BY ps.id', p=WSOY)}
        for s in data['series']:
            assert (s['editions'], s['first_year'], s['last_year']) == \
                counts[s['id']], s['name']

    def test_genres_count_works_not_editions(self, api_client):
        """Owner, 2026-11-27: the breakdown counts works, not editions."""
        data = _get(api_client, f'/api/publishers/{WSOY}/summary')
        expected = [(r[0], r[1], r[2]) for r in _rows(
            'SELECT g.abbr, g.name, count(DISTINCT e.work_id) AS n '
            'FROM suomisf.edition e JOIN suomisf.workgenre wg '
            'ON wg.work_id = e.work_id JOIN suomisf.genre g '
            'ON g.id = wg.genre_id WHERE e.publisher_id = :p '
            'GROUP BY g.abbr, g.name ORDER BY n DESC, g.name', p=WSOY)]
        assert [(g['abbr'], g['name'], g['works']) for g in data['genres']] \
            == expected
        editions = _rows(
            'SELECT count(*) FROM suomisf.edition e JOIN suomisf.workgenre '
            'wg ON wg.work_id = e.work_id JOIN suomisf.genre g ON '
            'g.id = wg.genre_id WHERE e.publisher_id = :p AND g.abbr = :a',
            p=WSOY, a=expected[0][0])[0][0]
        # Hobitti's 28 reprints count once
        assert expected[0][2] < editions

    def test_magazines_with_years_and_issues(self, api_client):
        data = _get(api_client, f'/api/publishers/{HSFS}/summary')
        mag = next(m for m in data['magazines']
                   if m['name'] == 'Tähtivaeltaja')
        n, first, last = _rows(
            'SELECT count(*), min(year), max(year) FROM suomisf.issue '
            'WHERE magazine_id = :m', m=mag['id'])[0]
        assert (mag['issues'], mag['first_year'], mag['last_year']) == \
            (n, first, last)
        assert 'type' in mag
        assert _get(api_client,
                    f'/api/publishers/{WSOY}/summary')['magazines'] == []

    def test_unknown_and_bad_ids(self, api_client):
        api_client.get('/api/publishers/999999/summary').assert_status(404)
        api_client.get('/api/publishers/x/summary').assert_status(400)


class TestPublisherEditions:
    def test_first_page_oldest_first(self, api_client):
        data = _editions(api_client)
        total = _scalar('SELECT count(*) FROM suomisf.edition '
                        'WHERE publisher_id = :p', p=WSOY)
        assert data['total'] == total
        assert (data['page'], data['rows']) == (1, 100)
        assert len(data['editions']) == 100
        years = [e['pubyear'] for e in data['editions']]
        assert years == sorted(years)
        assert years[0] == _scalar('SELECT min(pubyear) FROM suomisf.edition'
                                   ' WHERE publisher_id = :p', p=WSOY)

    def test_pages_do_not_overlap_and_end_empty(self, api_client):
        one = {e['id'] for e in _editions(api_client)['editions']}
        two = {e['id'] for e in _editions(api_client, '?page=2')['editions']}
        assert one and two and not one & two
        last = -(-_editions(api_client)['total'] // 200)
        assert _editions(api_client,
                         f'?rows=200&page={last + 1}')['editions'] == []

    def test_row_payload(self, api_client):
        data = _editions(api_client, '?year_min=1976&year_max=1976&rows=200')
        row = next(e for e in data['editions'] if e['id'] == LE_GUIN_FIRST)
        assert row['title'] == 'Pimeyden vasen käsi'
        assert row['pubyear'] == 1976
        assert (row['version'], row['editionnum']) == (1, 1)
        assert row['work']['orig_title'] == 'The Left Hand of Darkness'
        assert row['work']['pubyear'] == 1969
        assert row['work']['authors'][0]['alt_name'] == 'Ursula K. Le Guin'
        assert {g['abbr'] for g in row['work']['genres']} == {'SF'}
        assert [t['alt_name'] for t in row['translators']] == \
            ['Kalevi Nyytäjä']
        assert row['pubseries']['name'] == 'Sci-fi -sarja'
        # the work's book series (owner, 2026-11-27: the list lacked it)
        assert row['work']['bookseries']['name'] == 'Hain-sarja'
        assert row['work']['bookseries']['partof'] is None
        earthsea = next(e for e in data['editions']
                        if e['id'] == EARTHSEA_FIRST)
        assert earthsea['work']['bookseries']['name'] == 'Maameren tarinat'
        assert earthsea['work']['bookseriesnum'] == '1'
        assert 'pubseriesnum' in row
        assert row['cover'] is None or row['cover']['thumb_src']
        assert row['owned'] is False and row['wishlisted'] is False

    def test_year_range(self, api_client):
        data = _editions(api_client, '?year_min=1976&year_max=1977&rows=200')
        assert data['total'] == _scalar(
            'SELECT count(*) FROM suomisf.edition WHERE publisher_id = :p '
            'AND pubyear BETWEEN 1976 AND 1977', p=WSOY)
        assert all(1976 <= e['pubyear'] <= 1977 for e in data['editions'])

    def test_first_editions_only(self, api_client):
        """suomisf-ui#89: only the work's first Finnish edition, laitos 1 (or
        none) and printing 1; a 2. laitos is left out too."""
        data = _editions(api_client, '?first=1&year_min=1976&year_max=1976'
                         '&rows=200')
        assert data['total'] == _scalar(
            'SELECT count(*) FROM suomisf.edition WHERE publisher_id = :p '
            'AND pubyear = 1976 AND coalesce(version, 1) = 1 '
            'AND editionnum = 1', p=WSOY)
        assert all((e['version'] or 1) == 1 and e['editionnum'] == 1
                   for e in data['editions'])
        ids = [e['id'] for e in data['editions']]
        assert LE_GUIN_FIRST in ids
        every = _editions(api_client, '?year_min=1976&year_max=1976&rows=200')
        assert data['total'] < every['total']
        api_client.get(f'/api/publishers/{WSOY}/editions?first=x') \
            .assert_status(400)

    def test_text_matches_author_or_title(self, api_client):
        by_author = _editions(api_client, '?q=le+guin&rows=200')
        assert LE_GUIN_FIRST in [e['id'] for e in by_author['editions']]
        assert all('Le Guin' in e['work']['author_str']
                   for e in by_author['editions'])
        by_title = _editions(api_client, '?q=pimeyden&rows=200')
        assert LE_GUIN_FIRST in [e['id'] for e in by_title['editions']]
        by_orig = _editions(api_client, '?q=left+hand&rows=200')
        assert LE_GUIN_FIRST in [e['id'] for e in by_orig['editions']]

    def test_sorts(self, api_client):
        newest = [e['pubyear'] for e in
                  _editions(api_client, '?sort=newest')['editions']]
        assert newest == sorted(newest, reverse=True)
        # by the title the row shows: a printing with an empty title sorts
        # by its work's (edition 8833, Ensimmäinen persoona, sorted first)
        titles = _editions(api_client, '?sort=title&rows=50')['editions']
        expected = [r[0] for r in _rows(
            "SELECT e.id FROM suomisf.edition e JOIN suomisf.work w "
            "ON w.id = e.work_id WHERE e.publisher_id = :p ORDER BY "
            "coalesce(nullif(trim(e.title), ''), w.title), e.pubyear, e.id "
            "LIMIT 50", p=WSOY)]
        assert [e['id'] for e in titles] == expected
        authors = _editions(api_client, '?sort=author&rows=50')['editions']
        expected = [r[0] for r in _rows(
            'SELECT e.id FROM suomisf.edition e JOIN suomisf.work w '
            'ON w.id = e.work_id WHERE e.publisher_id = :p '
            'ORDER BY w.author_str, e.pubyear, e.title, e.id LIMIT 50',
            p=WSOY)]
        assert [e['id'] for e in authors] == expected

    def test_own_marks_for_the_user_only(self, api_client):
        user_id = _scalar('SELECT id FROM suomisf.user WHERE name = :n',
                          n=TEST_USER_NAME)
        session = new_session()
        try:
            session.execute(text(
                'INSERT INTO suomisf.userbook (edition_id, user_id, '
                'condition_id) VALUES (:e, :u, 2)'),
                {'e': LE_GUIN_FIRST, 'u': user_id})
            session.commit()
            query = '?year_min=1976&year_max=1976&rows=200'
            anon = next(e for e in _editions(api_client, query)['editions']
                        if e['id'] == LE_GUIN_FIRST)
            assert anon['owned'] is False
            api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
            mine = next(e for e in _editions(api_client, query)['editions']
                        if e['id'] == LE_GUIN_FIRST)
            assert (mine['owned'], mine['wishlisted']) == (True, False)
        finally:
            session.execute(text(
                'DELETE FROM suomisf.userbook WHERE user_id = :u AND '
                'edition_id = :e'), {'e': LE_GUIN_FIRST, 'u': user_id})
            session.commit()
            session.close()

    def test_own_counts_follow_the_filters(self, api_client):
        """Owner, 2026-11-27: above the list, how many of the printings the
        filters select the reader owns and wishes for (all pages)."""
        assert _editions(api_client)['own'] is None
        assert 'own' not in _get(api_client,
                                 f'/api/publishers/{WSOY}/summary')
        user_id = _scalar('SELECT id FROM suomisf.user WHERE name = :n',
                          n=TEST_USER_NAME)
        other = _scalar('SELECT id FROM suomisf.edition WHERE '
                        'publisher_id <> :p LIMIT 1', p=WSOY)
        later = _scalar('SELECT id FROM suomisf.edition WHERE '
                        'publisher_id = :p AND pubyear = 2002 LIMIT 1',
                        p=WSOY)
        rows = [(LE_GUIN_FIRST, 1), (EARTHSEA_FIRST, 6), (later, 3),
                (other, 2)]
        session = new_session()
        try:
            for edition, condition in rows:
                session.execute(text(
                    'INSERT INTO suomisf.userbook (edition_id, user_id, '
                    'condition_id) VALUES (:e, :u, :c)'),
                    {'e': edition, 'u': user_id, 'c': condition})
            session.commit()
            api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)

            def owned(where: str) -> int:
                return _scalar(
                    'SELECT count(*) FROM suomisf.userbook ub JOIN '
                    'suomisf.edition e ON e.id = ub.edition_id WHERE '
                    'ub.user_id = :u AND e.publisher_id = :p AND '
                    f'ub.condition_id BETWEEN 1 AND 5 {where}',
                    u=user_id, p=WSOY)
            # every printing, though page 1 holds only the oldest 100
            assert _editions(api_client)['own'] == \
                {'editions': owned(''), 'wishlisted': 1}
            # the 1976 filter: Le Guin's printing owned, Earthsea wished;
            # the 2002 one and the other publisher's don't count
            assert _editions(api_client, '?year_min=1976&year_max=1976')[
                'own'] == {'editions': owned('AND e.pubyear = 1976'),
                           'wishlisted': 1}
            assert _editions(api_client, '?q=pimeyden')['own'] == \
                {'editions': 1, 'wishlisted': 0}
        finally:
            session.execute(text(
                'DELETE FROM suomisf.userbook WHERE user_id = :u AND '
                'edition_id IN :ids'),
                {'u': user_id, 'ids': tuple(e for e, _ in rows)})
            session.commit()
            session.close()

    def test_an_expired_token_asks_for_a_new_one(self, api_client):
        with app.app_context():
            token = create_access_token(
                identity='1', expires_delta=timedelta(seconds=-10))
        response = api_client.get(
            f'/api/publishers/{WSOY}/editions',
            headers={'Authorization': f'Bearer {token}'})
        response.assert_status(401)
        assert 'Token has expired' in response.json['msg']

    def test_bad_parameters(self, api_client):
        for query in ('?rows=7', '?page=0', '?sort=x', '?year_min=x'):
            api_client.get(f'/api/publishers/{WSOY}/editions{query}') \
                .assert_status(400)
        api_client.get('/api/publishers/999999/editions').assert_status(404)
