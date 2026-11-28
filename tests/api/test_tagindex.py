"""
SuomiSF API: the light tag list (GET /api/tagindex)

The new tag list page (docs/ui-redesign/pages/tags.md in the frontend)
shows one group a tab, big groups a letter at a time, with counts and no
works. Expected values come from SQL on the test database.
"""

from sqlalchemy import text

from app.route_helpers import new_session

AIHE = 1
ALAGENRE = 2
COUNT_SQL = (
    '(SELECT count(*) FROM suomisf.worktag x WHERE x.tag_id = t.id) + '
    '(SELECT count(*) FROM suomisf.storytag x WHERE x.tag_id = t.id) + '
    '(SELECT count(*) FROM suomisf.articletag x WHERE x.tag_id = t.id)')


def _rows(sql, **params):
    session = new_session()
    try:
        return session.execute(text(sql), params).all()
    finally:
        session.close()


def _get(client, query=''):
    response = client.get(f'/api/tagindex{query}')
    response.assert_status(200)
    return response.data


class TestTagIndex:
    """Groups, letters, search, sorting and counts."""

    def test_a_group_lists_its_used_tags_by_name_with_counts(
            self, api_client):
        data = _get(api_client, f'?type={ALAGENRE}')
        expected = _rows(
            f'SELECT t.id, {COUNT_SQL} AS n FROM suomisf.tag t WHERE '
            f't.type_id = {ALAGENRE} AND {COUNT_SQL} > 0 ORDER BY t.name')
        assert [t['id'] for t in data['tags']] == [r.id for r in expected]
        assert [t['count'] for t in data['tags']] == [r.n for r in expected]
        tag = data['tags'][0]
        assert set(tag) == {'id', 'name', 'count'}
        assert 'works' not in data

    def test_group_counts_for_the_tabs(self, api_client):
        types = {t['id']: t for t in _get(api_client)['types']}
        assert [t for t in types] == [2, 3, 1, 4, 5, 6, 7]
        assert types[ALAGENRE]['name'] == 'Alagenre'
        # A tag without a type counts as Aihe, as on the current page.
        expected = _rows(
            f'SELECT count(*) FROM suomisf.tag t WHERE '
            f'coalesce(t.type_id, {AIHE}) = {AIHE} AND {COUNT_SQL} > 0')[0][0]
        assert types[AIHE]['count'] == expected

    def test_default_group_is_alagenre(self, api_client):
        assert _get(api_client)['tags'] == \
            _get(api_client, f'?type={ALAGENRE}')['tags']

    def test_letter(self, api_client):
        tags = _get(api_client, f'?type={AIHE}&letter=a')['tags']
        assert tags and all(t['name'][0].upper() == 'A' for t in tags)
        finnish = _get(api_client, f'?type={AIHE}&letter=%C3%84')['tags']
        assert all(t['name'][0].upper() == 'Ä' for t in finnish)

    def test_other_initials(self, api_client):
        # "0" stands for any name that doesn't start with A-Ö (1800-luku).
        tags = _get(api_client, '?type=6&letter=0')['tags']
        assert tags
        assert all(t['name'][0].upper() not in
                   'ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ' for t in tags)

    def test_search_ignores_the_letter_and_counts_per_group(
            self, api_client):
        data = _get(api_client, f'?type={AIHE}&letter=B&q=aika')
        assert data['tags']
        assert all('aika' in t['name'].lower() for t in data['tags'])
        expected = _rows(
            f"SELECT coalesce(t.type_id, {AIHE}) AS g, count(*) AS n "
            f"FROM suomisf.tag t WHERE t.name ILIKE '%aika%' AND "
            f"{COUNT_SQL} > 0 GROUP BY 1")
        counts = {t['id']: t['count'] for t in data['types']}
        for row in expected:
            assert counts[row.g] == row.n

    def test_sort_by_count(self, api_client):
        tags = _get(api_client, f'?type={AIHE}&letter=A&sort=count')['tags']
        counts = [t['count'] for t in tags]
        assert counts == sorted(counts, reverse=True)

    def test_unused_tags_only_when_asked(self, api_client):
        unused = _rows(f'SELECT t.id, coalesce(t.type_id, {AIHE}) AS g '
                       f'FROM suomisf.tag t WHERE {COUNT_SQL} = 0')
        if not unused:
            return
        tag_id, group = unused[0]
        listed = [t['id'] for t in _get(api_client, f'?type={group}')['tags']]
        assert tag_id not in listed
        data = _get(api_client, f'?type={group}&unused=1')
        tag = next(t for t in data['tags'] if t['id'] == tag_id)
        assert tag['count'] == 0

    def test_bad_parameters(self, api_client):
        for query in ('?type=x', '?type=99', '?letter=ab', '?sort=random'):
            response = api_client.get(f'/api/tagindex{query}')
            assert response.status_code == 400, query
