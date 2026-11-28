"""
SuomiSF API: the paged book index (GET /api/bookindex)

The new book index page (docs/ui-redesign/pages/book-index.md in the
frontend) lists every work, filtered, sorted and paged on the server, with
a light row payload. POST /api/searchworks stays as it is for the current
page.
"""

from datetime import timedelta

from flask_jwt_extended import create_access_token
from sqlalchemy import text

from app import app
from app.route_helpers import new_session

LE_GUIN_WORK = 3984  # Pimeyden vasen käsi: 3 printings, first WSOY 1976
LE_GUIN_FIRST = 4573  # its first printing
STOKER_WORK = 1332  # Kammoittava kreivi: three laitos, three translations
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'


def _scalar(sql, **params):
    session = new_session()
    try:
        return session.execute(text(sql), params).scalar()
    finally:
        session.close()


def _ids(sql, **params):
    session = new_session()
    try:
        return [r[0] for r in session.execute(text(sql), params)]
    finally:
        session.close()


def _get(client, query=''):
    response = client.get(f'/api/bookindex{query}')
    response.assert_status(200)
    return response.data


class TestBookIndexPaging:
    """Totals, pages and the row payload."""

    def test_no_filters_lists_every_work_one_page_at_a_time(self, api_client):
        data = _get(api_client)
        total = _scalar('SELECT count(*) FROM suomisf.work')
        assert data['total'] == total
        assert data['page'] == 1
        assert data['rows'] == 50
        assert len(data['works']) == 50
        second = _get(api_client, '?page=2')['works']
        assert {w['id'] for w in second}.isdisjoint(
            {w['id'] for w in data['works']})

    def test_rows_per_page(self, api_client):
        assert len(_get(api_client, '?rows=100')['works']) == 100
        assert len(_get(api_client, '?rows=200')['works']) == 200

    def test_last_page_is_partial_and_past_it_is_empty(self, api_client):
        total = _get(api_client)['total']
        last = (total + 49) // 50
        assert len(_get(api_client, f'?page={last}')['works']) == \
            total - (last - 1) * 50
        assert _get(api_client, f'?page={last + 1}')['works'] == []

    def test_row_payload(self, api_client):
        data = _get(api_client, '?author=Le+Guin&title=Pimeyden')
        row = next(w for w in data['works'] if w['id'] == LE_GUIN_WORK)
        assert row['title'] == 'Pimeyden vasen käsi'
        assert row['orig_title'] == 'The Left Hand of Darkness'
        assert row['pubyear'] == 1969
        assert row['type'] == 1
        assert row['printings'] == 3
        assert row['first_edition']['pubyear'] == 1976
        assert row['first_edition']['publisher']['name'] == 'WSOY'
        assert row['authors'][0]['alt_name'] == 'Ursula K. Le Guin'
        assert {g['abbr'] for g in row['genres']} == {'SF'}
        assert row['bookseries']['name'] == 'Hain-sarja'
        # The list is text only (owner, 2026-11-26): no cover to load.
        assert 'cover' not in row

    def test_row_has_what_the_old_list_showed(self, api_client):
        """Translator, publisher's series, every printing, subtitle."""
        row = next(w for w in _get(api_client, '?author=Le+Guin&rows=200')
                   ['works'] if w['id'] == LE_GUIN_WORK)
        assert [t['alt_name'] for t in row['translators']] == \
            ['Kalevi Nyytäjä']
        assert row['first_edition']['id'] == LE_GUIN_FIRST
        assert row['first_edition']['pubseries']['name'] == 'Sci-fi -sarja'
        assert [(e['pubyear'], e['editionnum']) for e in row['editions']] == \
            [(1976, 1), (1986, 2), (1992, 3)]
        assert all(e['owned'] is False and e['wishlisted'] is False
                   for e in row['editions'])
        assert 'subtitle' in row
        assert row['real_authors'] == []
        assert row['bookseries']['partof'] is None

    def test_each_printing_has_its_own_translators_and_publisher(
            self, api_client):
        """Stoker's Dracula: each laitos was translated anew."""
        row = next(w for w in _get(
            api_client, '?author=Stoker&title=Kammoittava')['works']
            if w['id'] == STOKER_WORK)
        by_version = {}
        for e in row['editions']:
            by_version.setdefault(e['version'] or 1, e)
        names = {v: [t['alt_name'] for t in e['translators']]
                 for v, e in by_version.items()}
        assert names[1] == ['Risto Kalliomaa']
        assert names[2] == ['Jarkko Laine']
        assert sorted(names[3]) == ['Ari Sainio', 'Johan Werkmäster']
        assert by_version[2]['publisher']['name'] == 'Otava'
        assert by_version[1]['title'] == 'Kammoittava kreivi'
        # by laitos, then printing: the 2017 3. laitos comes last
        assert [e['version'] or 1 for e in row['editions']] == \
            sorted(e['version'] or 1 for e in row['editions'])
        assert all({'title', 'translators', 'publisher', 'pubseries'}
                   <= set(e) for e in row['editions'])

    def test_real_writers_behind_a_shared_pen_name(self, api_client):
        work_id = _scalar(
            'SELECT wc.work_id FROM suomisf.workcontributor wc '
            'WHERE wc.role_id = 1 AND wc.real_person_id IS NOT NULL '
            'ORDER BY wc.work_id LIMIT 1')
        title = _scalar('SELECT title FROM suomisf.work WHERE id = :w',
                        w=work_id)
        data = _get(api_client, '?title=' + title.split()[0] + '&rows=200')
        row = next(w for w in data['works'] if w['id'] == work_id)
        assert row['real_authors']
        assert {'id', 'name', 'alt_name'} <= set(row['real_authors'][0])


class TestBookIndexOwnMarks:
    """A logged-in user sees their own owned and wishlisted printings."""

    def test_owned_and_wishlisted_for_the_user_only(self, api_client):
        user_id = _scalar("SELECT id FROM suomisf.user WHERE name = :n",
                          n=TEST_USER_NAME)
        second = _scalar('SELECT id FROM suomisf.edition WHERE work_id = :w '
                         'AND editionnum = 2', w=LE_GUIN_WORK)
        session = new_session()
        try:
            session.execute(text(
                'INSERT INTO suomisf.userbook (edition_id, user_id, '
                'condition_id) VALUES (:a, :u, 1), (:b, :u, 6)'),
                {'a': LE_GUIN_FIRST, 'b': second, 'u': user_id})
            session.commit()
            query = '?author=Le+Guin&title=Pimeyden'
            anon = next(w for w in _get(api_client, query)['works']
                        if w['id'] == LE_GUIN_WORK)
            assert not any(e['owned'] or e['wishlisted']
                           for e in anon['editions'])
            api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
            mine = next(w for w in _get(api_client, query)['works']
                        if w['id'] == LE_GUIN_WORK)
            marks = {e['id']: (e['owned'], e['wishlisted'])
                     for e in mine['editions']}
            assert marks[LE_GUIN_FIRST] == (True, False)
            assert marks[second] == (False, True)
        finally:
            session.execute(text(
                'DELETE FROM suomisf.userbook WHERE user_id = :u AND '
                'edition_id IN (:a, :b)'),
                {'a': LE_GUIN_FIRST, 'b': second, 'u': user_id})
            session.commit()
            session.close()

    def test_a_bad_token_is_treated_as_a_visitor(self, api_client):
        response = api_client.get(
            '/api/bookindex?author=Le+Guin',
            headers={'Authorization': 'Bearer not-a-token'})
        response.assert_status(200)

    def test_an_expired_token_asks_for_a_new_one(self, api_client):
        """
        Access tokens last a minute. An expired one must answer 401 "Token
        has expired", as every other endpoint does, so the frontend renews
        it and asks again; answering as a visitor hid the user's marks.
        """
        with app.app_context():
            token = create_access_token(
                identity='1', expires_delta=timedelta(seconds=-10))
        response = api_client.get(
            '/api/bookindex?author=Le+Guin',
            headers={'Authorization': f'Bearer {token}'})
        response.assert_status(401)
        assert 'Token has expired' in response.json['msg']


class TestBookIndexFilters:
    """Each filter alone, and combined."""

    def test_author_prefix_on_name_or_alt_name(self, api_client):
        data = _get(api_client, '?author=Le+Guin&rows=200')
        expected = _scalar(
            "SELECT count(DISTINCT wc.work_id) FROM suomisf.workcontributor wc"
            " JOIN suomisf.person p ON p.id IN (wc.person_id, "
            "wc.real_person_id) WHERE wc.role_id = 1 AND "
            "(p.name ILIKE 'Le Guin%' OR p.alt_name ILIKE 'Le Guin%')")
        assert data['total'] == expected > 0

    def test_title_and_original_title(self, api_client):
        data = _get(api_client, '?title=vasen')
        assert any(w['id'] == LE_GUIN_WORK for w in data['works'])
        data = _get(api_client, '?orig_title=Left+Hand')
        assert any(w['id'] == LE_GUIN_WORK for w in data['works'])

    def test_author_initial(self, api_client):
        data = _get(api_client, '?initial=L&rows=200')
        assert data['total'] == _scalar(
            "SELECT count(*) FROM suomisf.work "
            "WHERE upper(left(author_str, 1)) = 'L'")
        assert all(w['author_str'].upper().startswith('L')
                   for w in data['works'])

    def test_finnish_initials(self, api_client):
        data = _get(api_client, '?initial=%C3%84')  # Ä
        assert all(w['author_str'].upper().startswith('Ä')
                   for w in data['works'])

    def test_types_several(self, api_client):
        data = _get(api_client, '?type=2,6&rows=200')
        assert data['total'] == _scalar(
            'SELECT count(*) FROM suomisf.work WHERE type IN (2, 6)')
        assert {w['type'] for w in data['works']} <= {2, 6}

    def test_genres_several_by_abbreviation(self, api_client):
        data = _get(api_client, '?genre=K,Utopia&rows=200')
        assert data['total'] == _scalar(
            "SELECT count(DISTINCT wg.work_id) FROM suomisf.workgenre wg "
            "JOIN suomisf.genre g ON g.id = wg.genre_id "
            "WHERE g.abbr IN ('K', 'Utopia')")
        for w in data['works']:
            assert {g['abbr'] for g in w['genres']} & {'K', 'Utopia'}

    def test_original_year_range(self, api_client):
        data = _get(api_client, '?origyear_min=1960&origyear_max=1969')
        assert data['total'] == _scalar(
            'SELECT count(*) FROM suomisf.work '
            'WHERE pubyear BETWEEN 1960 AND 1969')
        assert all(1960 <= w['pubyear'] <= 1969 for w in data['works'])

    def test_printing_year_range_any_printing(self, api_client):
        data = _get(api_client, '?printyear_min=2020')
        assert data['total'] == _scalar(
            'SELECT count(DISTINCT work_id) FROM suomisf.edition '
            'WHERE pubyear >= 2020')

    def test_nationality(self, api_client):
        nat = _scalar("SELECT nationality_id FROM suomisf.person "
                      "WHERE alt_name = 'Ursula K. Le Guin'")
        data = _get(api_client, f'?nationality={nat}&author=Le+Guin')
        assert data['total'] > 0
        none = _get(api_client, '?nationality=999999&author=Le+Guin')
        assert none['total'] == 0

    def test_filters_combine(self, api_client):
        data = _get(api_client, '?author=Le+Guin&type=1&genre=SF')
        assert data['total'] > 0
        for w in data['works']:
            assert w['type'] == 1
            assert 'SF' in {g['abbr'] for g in w['genres']}


class TestBookIndexTag:
    """The tag page's works list: one tag, or with its similar tags."""

    KYBERPUNK = 303

    def test_tag(self, api_client):
        data = _get(api_client, f'?tag={self.KYBERPUNK}&rows=200')
        expected = set(_ids('SELECT work_id FROM suomisf.worktag '
                            'WHERE tag_id = :t', t=self.KYBERPUNK))
        assert data['total'] == len(expected) > 0
        assert {w['id'] for w in data['works']} == expected
        assert 'matched_tags' not in data['works'][0]
        assert _stats(api_client, f'?tag={self.KYBERPUNK}')['total'] == \
            len(expected)

    def test_with_similar_tags_each_row_says_which(self, api_client):
        similar = _ids(
            "SELECT CASE WHEN tag_a = :t THEN tag_b ELSE tag_a END FROM "
            "suomisf.tag_similarity WHERE (tag_a = :t OR tag_b = :t) "
            "AND status = 'new'", t=self.KYBERPUNK)
        tags = [self.KYBERPUNK] + similar
        expected = set(_ids('SELECT work_id FROM suomisf.worktag '
                            'WHERE tag_id = ANY(:t)', t=tags))
        data = _get(api_client,
                    f'?tag={self.KYBERPUNK}&tag_similar=1&rows=200')
        assert data['total'] == len(expected)
        for w in data['works']:
            ids = [t['id'] for t in w['matched_tags']]
            assert ids and set(ids) <= set(tags)
            if self.KYBERPUNK in ids:
                assert ids[0] == self.KYBERPUNK
        if similar:
            assert any(self.KYBERPUNK not in
                       [t['id'] for t in w['matched_tags']]
                       for w in data['works'])

    def test_bad_tag(self, api_client):
        assert api_client.get('/api/bookindex?tag=x').status_code == 400


class TestBookIndexSorting:
    """Sort orders, empty values last."""

    def test_default_is_author_then_title(self, api_client):
        # The database's Finnish collation decides the order.
        works = _get(api_client, '?initial=K')['works']
        expected = [r for r in _ids(
            "SELECT id FROM suomisf.work WHERE upper(left(author_str, 1)) "
            "= 'K' ORDER BY author_str, title, id LIMIT 50")]
        assert [w['id'] for w in works] == expected

    def test_title(self, api_client):
        works = _get(api_client, '?author=Le+Guin&sort=title')['works']
        first = _scalar(
            "SELECT w.id FROM suomisf.work w WHERE w.id IN (SELECT "
            "wc.work_id FROM suomisf.workcontributor wc JOIN suomisf.person "
            "p ON p.id IN (wc.person_id, wc.real_person_id) WHERE "
            "wc.role_id = 1 AND (p.name ILIKE 'Le Guin%' OR p.alt_name "
            "ILIKE 'Le Guin%')) ORDER BY w.title, w.id LIMIT 1")
        assert works[0]['id'] == first

    def test_year_oldest_and_newest_first_with_empty_years_last(
            self, api_client):
        oldest = _get(api_client, '?sort=year')['works']
        years = [w['pubyear'] for w in oldest]
        assert years == sorted(years)
        newest = _get(api_client, '?sort=newest')['works']
        years = [w['pubyear'] for w in newest]
        assert years == sorted(years, reverse=True)
        total = _get(api_client)['total']
        last_page = (total + 49) // 50
        tail = _get(api_client, f'?sort=newest&page={last_page}')['works']
        if _scalar('SELECT count(*) FROM suomisf.work '
                   'WHERE pubyear IS NULL'):
            assert tail[-1]['pubyear'] is None


class TestBookIndexErrors:
    """Bad parameters are 400, not a server error."""

    def test_bad_parameters(self, api_client):
        for query in ('?rows=7', '?page=0', '?page=x', '?sort=random',
                      '?origyear_min=abc', '?printyear_max=x',
                      '?type=a', '?nationality=x', '?initial=LL'):
            response = api_client.get(f'/api/bookindex{query}')
            assert response.status_code == 400, query


def _stats(client, query=''):
    response = client.get(f'/api/bookindex/stats{query}')
    response.assert_status(200)
    return response.data


class TestBookIndexStats:
    """Statistics for a whole search (GET /api/bookindex/stats)."""

    def test_total_follows_the_filters(self, api_client):
        assert _stats(api_client)['total'] == _get(api_client)['total']
        for query in ('?author=Le+Guin', '?type=4', '?genre=K,Utopia',
                      '?initial=L&printyear_min=2000'):
            assert _stats(api_client, query)['total'] == \
                _get(api_client, query)['total'], query

    def test_genres_count_works_most_first(self, api_client):
        genres = _stats(api_client, '?author=Le+Guin')['genres']
        expected = _scalar(
            "SELECT count(DISTINCT wg.work_id) FROM suomisf.workgenre wg "
            "JOIN suomisf.genre g ON g.id = wg.genre_id WHERE g.abbr = 'SF' "
            "AND wg.work_id IN (SELECT wc.work_id FROM "
            "suomisf.workcontributor wc JOIN suomisf.person p ON p.id IN "
            "(wc.person_id, wc.real_person_id) WHERE wc.role_id = 1 AND "
            "(p.name ILIKE 'Le Guin%' OR p.alt_name ILIKE 'Le Guin%'))")
        sf = next(g for g in genres if g['abbr'] == 'SF')
        assert sf['works'] == expected > 0
        assert sf['name']
        counts = [g['works'] for g in genres]
        assert counts == sorted(counts, reverse=True)

    def test_tags_count_works_most_first(self, api_client):
        tags = _stats(api_client, '?type=4')['tags']
        assert tags, 'non-fiction has tags in the test data'
        top = tags[0]
        assert top['works'] == _scalar(
            'SELECT count(*) FROM suomisf.worktag wt JOIN suomisf.work w '
            'ON w.id = wt.work_id WHERE w.type = 4 AND wt.tag_id = :tag',
            tag=top['id'])
        assert top['name']
        counts = [t['works'] for t in tags]
        assert counts == sorted(counts, reverse=True)
        assert _stats(api_client, '?type=4')['tag_count'] == _scalar(
            'SELECT count(DISTINCT wt.tag_id) FROM suomisf.worktag wt JOIN '
            'suomisf.work w ON w.id = wt.work_id WHERE w.type = 4')

    def test_nothing_found(self, api_client):
        data = _stats(api_client, '?author=zzzzzz')
        assert data == {'total': 0, 'genres': [], 'tags': [],
                        'tag_count': 0}

    def test_at_most_fifty_tags_and_how_many_in_all(self, api_client):
        data = _stats(api_client)
        assert len(data['tags']) == 50
        assert data['tag_count'] == _scalar(
            'SELECT count(DISTINCT tag_id) FROM suomisf.worktag') > 50

    def test_paging_and_sort_are_ignored_but_still_checked(
            self, api_client):
        assert _stats(api_client, '?page=3&rows=200&sort=title')['total'] \
            == _get(api_client)['total']
        for query in ('?type=a', '?initial=LL', '?origyear_min=x'):
            response = api_client.get(f'/api/bookindex/stats{query}')
            assert response.status_code == 400, query
