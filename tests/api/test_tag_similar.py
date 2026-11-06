"""
SuomiSF API tag similarity tests

GET /api/tags/similar and POST /api/tags/similar/{dismiss,restore}, which
read and decide the pairs scripts/tag_similarity.py writes.
"""

import pytest
from sqlalchemy import text

from app.route_helpers import new_session

from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD

TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'
NAMES = ('zz similar test a', 'zz similar test b', 'zz similar test c',
         'zz similar test d')


def _clean(session):
    # Pairs go with the tags (ON DELETE CASCADE); work links don't.
    session.execute(text(
        'DELETE FROM worktag WHERE tag_id IN '
        '(SELECT id FROM tag WHERE name IN :names)').bindparams(names=NAMES))
    session.execute(text('DELETE FROM tag WHERE name IN :names')
                    .bindparams(names=NAMES))
    session.commit()


@pytest.fixture
def pair(app):  # pylint: disable=unused-argument
    """Tags a, b and c; a - b a duplicate pair, a - c a related one, b - c
    a dismissed related one. Yields the ids."""
    session = new_session()
    _clean(session)
    ids = [session.execute(text(
        'INSERT INTO tag (name, type_id) VALUES (:n, 1) RETURNING id'),
        {'n': n}).scalar() for n in NAMES[:3]]
    a, b, c = ids
    session.execute(text("""
        INSERT INTO tag_similarity
            (tag_a, tag_b, kind, reason, name_score, containment, shared,
             status)
        VALUES (:a, :b, 'duplicate', 'baseform', 0.97, NULL, 0, 'new'),
               (:a, :c, 'related', 'usage', NULL, 0.95, 4, 'new'),
               (:b, :c, 'related', 'name', 0.92, NULL, 0, 'dismissed')"""),
        {'a': a, 'b': b, 'c': c})
    session.execute(text(
        'INSERT INTO worktag (work_id, tag_id) '
        'SELECT id, :a FROM work ORDER BY id LIMIT 2'), {'a': a})
    session.commit()
    yield a, b, c
    _clean(session)
    session.close()


@pytest.fixture
def admin_client(api_client):
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


def _ours(data, ids):
    return [p for p in data['pairs'] if p['tag_a']['id'] in ids]


def test_lists_new_pairs_with_tags_and_scores(admin_client, pair):
    a, b, c = pair
    resp = admin_client.get('/api/tags/similar')
    assert resp.status_code == 200
    assert resp.data['updated'] is not None
    # Every view's count, whichever view is asked for; the test DB has
    # other pairs too, so compare with them removed.
    counts = resp.data['counts']
    assert set(counts) == {'duplicate', 'related', 'dismissed'}
    assert counts['duplicate'] >= 1 and counts['related'] >= 1 \
        and counts['dismissed'] >= 1
    assert admin_client.get('/api/tags/similar?status=dismissed') \
        .data['counts'] == counts
    ours = _ours(resp.data, pair)
    assert [(p['tag_a']['id'], p['tag_b']['id'], p['kind']) for p in ours] \
        == [(a, b, 'duplicate'), (a, c, 'related')]
    dup = ours[0]
    assert dup['tag_a'] == {'id': a, 'name': NAMES[0],
                            'type': dup['tag_a']['type'], 'uses': 2}
    assert dup['tag_a']['type']['id'] == 1
    assert dup['tag_b']['uses'] == 0
    assert (dup['reason'], dup['name_score'], dup['status']) == \
        ('baseform', pytest.approx(0.97), 'new')
    assert (ours[1]['containment'], ours[1]['shared']) == \
        (pytest.approx(0.95), 4)


def test_filters_by_kind_and_status(admin_client, pair):
    _, b, c = pair
    dups = _ours(admin_client.get('/api/tags/similar?kind=duplicate').data,
                 pair)
    assert [p['tag_b']['id'] for p in dups] == [b]
    dismissed = _ours(
        admin_client.get('/api/tags/similar?status=dismissed').data, pair)
    assert [(p['tag_a']['id'], p['tag_b']['id']) for p in dismissed] \
        == [(b, c)]


@pytest.mark.parametrize('query', ['kind=other', 'status=done'])
def test_rejects_unknown_kind_or_status(admin_client, query):
    assert admin_client.get(f'/api/tags/similar?{query}').status_code == 400


def test_dismiss_and_restore(admin_client, pair):
    a, b, _ = pair
    # Either order names the same pair.
    before = admin_client.get('/api/tags/similar').data['counts']
    resp = admin_client.post('/api/tags/similar/dismiss',
                             data={'tag_a': b, 'tag_b': a})
    assert resp.status_code == 200
    assert resp.data == {'tag_a': a, 'tag_b': b, 'status': 'dismissed'}
    after = admin_client.get('/api/tags/similar').data['counts']
    assert (after['duplicate'], after['dismissed']) == \
        (before['duplicate'] - 1, before['dismissed'] + 1)
    dismissed = _ours(
        admin_client.get('/api/tags/similar?status=dismissed').data, pair)
    dup = next(p for p in dismissed if p['tag_b']['id'] == b)
    assert dup['decided_by'] == TEST_ADMIN_NAME
    assert dup['decided_at'] is not None
    assert b not in [p['tag_b']['id'] for p in _ours(
        admin_client.get('/api/tags/similar').data, pair)]

    resp = admin_client.post('/api/tags/similar/restore',
                             data={'tag_a': a, 'tag_b': b})
    assert resp.status_code == 200
    assert b in [p['tag_b']['id'] for p in _ours(
        admin_client.get('/api/tags/similar').data, pair)]


def test_merge_removes_the_pair(admin_client, pair):
    a, b, _ = pair
    assert admin_client.post(f'/api/tags/{a}/merge/{b}').status_code == 200
    data = admin_client.get('/api/tags/similar').data
    assert not [p for p in data['pairs'] if b in (p['tag_a']['id'],
                                                  p['tag_b']['id'])]


@pytest.mark.parametrize('body', [{}, {'tag_a': 'x', 'tag_b': 1}, [1, 2]])
def test_decide_rejects_bad_bodies(admin_client, body):
    resp = admin_client.post('/api/tags/similar/dismiss', data=body)
    assert resp.status_code == 400


def test_decide_unknown_pair(admin_client, pair):
    a, _, _ = pair
    resp = admin_client.post('/api/tags/similar/dismiss',
                             data={'tag_a': a, 'tag_b': 999999999})
    assert resp.status_code == 404
    resp = admin_client.post('/api/tags/similar/dismiss',
                             data={'tag_a': a, 'tag_b': a})
    assert resp.status_code == 400


@pytest.mark.parametrize('method, path', [
    ('get', '/api/tags/similar'),
    ('post', '/api/tags/similar/dismiss'),
    ('post', '/api/tags/similar/restore'),
])
def test_admin_only(api_client, method, path):
    api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
    resp = getattr(api_client, method)(path)
    assert resp.status_code == 403


def test_similar_to_a_tag_is_public_and_skips_dismissed(api_client, pair):
    a, b, c = pair
    resp = api_client.get(f'/api/tags/{a}/similar')
    assert resp.status_code == 200
    assert [(t['id'], t['kind'], t['reason']) for t in resp.data] == \
        [(b, 'duplicate', 'baseform'), (c, 'related', 'usage')]
    assert resp.data[0]['name'] == NAMES[1]
    assert resp.data[0]['type']['id'] == 1
    # b - c is dismissed, so c only lists a.
    assert [t['id'] for t in api_client.get(f'/api/tags/{c}/similar').data] \
        == [a]


def test_similar_to_a_tag_invalid_id(api_client):
    assert api_client.get('/api/tags/x/similar').status_code == 400
    assert api_client.get('/api/tags/999999999/similar').data == []


def test_add_links_tags_by_hand_and_dismiss_removes_it(admin_client, pair):
    a, b, c = pair
    # b - c was dismissed; adding it makes it a manual pair again.
    resp = admin_client.post('/api/tags/similar/add',
                             data={'tag_a': c, 'tag_b': b})
    assert resp.status_code == 200
    assert resp.data == {'tag_a': b, 'tag_b': c}
    similar = admin_client.get(f'/api/tags/{c}/similar').data
    assert [(t['id'], t['kind'], t['reason']) for t in similar] == \
        [(b, 'related', 'manual'), (a, 'related', 'usage')]
    listed = _ours(admin_client.get('/api/tags/similar?kind=related').data,
                   pair)
    manual = next(p for p in listed if p['tag_a']['id'] == b)
    assert manual['decided_by'] == TEST_ADMIN_NAME

    # Removing a manual pair deletes it rather than dismissing it.
    resp = admin_client.post('/api/tags/similar/dismiss',
                             data={'tag_a': b, 'tag_b': c})
    assert resp.data['status'] == 'removed'
    assert [t['id'] for t in admin_client.get(
        f'/api/tags/{c}/similar').data] == [a]
    assert not [p for p in _ours(admin_client.get(
        '/api/tags/similar?status=dismissed').data, pair)
        if p['tag_b']['id'] == c and p['tag_a']['id'] == b]


def test_add_leaves_a_suggested_pair_alone(admin_client, pair):
    a, b, _ = pair
    assert admin_client.post('/api/tags/similar/add',
                             data={'tag_a': a, 'tag_b': b}).status_code == 200
    dup = admin_client.get(f'/api/tags/{a}/similar').data[0]
    assert (dup['id'], dup['kind'], dup['reason']) == \
        (b, 'duplicate', 'baseform')


def test_add_rejects_bad_pairs(admin_client, pair):
    a, _, _ = pair
    assert admin_client.post('/api/tags/similar/add',
                             data={'tag_a': a, 'tag_b': a}).status_code == 400
    assert admin_client.post('/api/tags/similar/add',
                             data={'tag_a': a, 'tag_b': 999999999}
                             ).status_code == 404
    assert admin_client.post('/api/tags/similar/add',
                             data={'tag_a': 'x'}).status_code == 400


def test_add_is_admin_only(api_client):
    api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
    assert api_client.post('/api/tags/similar/add',
                           data={'tag_a': 1, 'tag_b': 2}).status_code == 403


def test_kind_set_by_hand(admin_client, pair):
    a, b, _ = pair
    resp = admin_client.post('/api/tags/similar/kind',
                             data={'tag_a': b, 'tag_b': a, 'kind': 'related'})
    assert resp.status_code == 200
    assert resp.data == {'tag_a': a, 'tag_b': b, 'kind': 'related'}
    related = _ours(admin_client.get('/api/tags/similar?kind=related').data,
                    pair)
    moved = next(p for p in related if p['tag_b']['id'] == b)
    # The reason stays; who changed it is recorded.
    assert (moved['reason'], moved['decided_by']) == \
        ('baseform', TEST_ADMIN_NAME)
    assert not [p for p in _ours(admin_client.get(
        '/api/tags/similar?kind=duplicate').data, pair)
        if p['tag_b']['id'] == b]
    session = new_session()
    assert session.execute(text(
        'SELECT kind_fixed FROM tag_similarity WHERE tag_a = :a '
        'AND tag_b = :b'), {'a': a, 'b': b}).scalar() is True
    session.close()


@pytest.mark.parametrize('body, status', [
    ({'tag_a': 1, 'tag_b': 2, 'kind': 'other'}, 400),
    ({'tag_a': 1, 'tag_b': 2}, 400),
    ({'tag_a': 'x', 'tag_b': 2, 'kind': 'related'}, 400),
    ({'tag_a': 999999998, 'tag_b': 999999999, 'kind': 'related'}, 404),
])
def test_kind_rejects_bad_requests(admin_client, body, status):
    assert admin_client.post('/api/tags/similar/kind',
                             data=body).status_code == status


def test_kind_is_admin_only(api_client):
    api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
    assert api_client.post('/api/tags/similar/kind', data={
        'tag_a': 1, 'tag_b': 2, 'kind': 'related'}).status_code == 403


def test_check_marks_a_pair(admin_client, pair):
    a, b, _ = pair
    resp = admin_client.post('/api/tags/similar/check',
                             data={'tag_a': b, 'tag_b': a, 'checked': True})
    assert resp.status_code == 200
    assert resp.data == {'tag_a': a, 'tag_b': b, 'checked': True}
    dup = next(p for p in _ours(admin_client.get(
        '/api/tags/similar?kind=duplicate').data, pair)
        if p['tag_b']['id'] == b)
    assert (dup['checked'], dup['decided_by']) == (True, TEST_ADMIN_NAME)
    admin_client.post('/api/tags/similar/check',
                      data={'tag_a': a, 'tag_b': b, 'checked': False})
    dup = next(p for p in _ours(admin_client.get(
        '/api/tags/similar?kind=duplicate').data, pair)
        if p['tag_b']['id'] == b)
    assert dup['checked'] is False


@pytest.mark.parametrize('body, status', [
    ({'tag_a': 1, 'tag_b': 2}, 400),
    ({'tag_a': 1, 'tag_b': 2, 'checked': 'yes'}, 400),
    ({'tag_a': 999999998, 'tag_b': 999999999, 'checked': True}, 404),
])
def test_check_rejects_bad_requests(admin_client, body, status):
    assert admin_client.post('/api/tags/similar/check',
                             data=body).status_code == status


def test_check_is_admin_only(api_client):
    api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
    assert api_client.post('/api/tags/similar/check', data={
        'tag_a': 1, 'tag_b': 2, 'checked': True}).status_code == 403


def test_merge_keeps_both_tags_similar_tags(admin_client, pair):
    """b is merged into c. a - b (duplicate) and a - c (related, new) meet:
    b's has no decision either, so c's stays. b - d moves to c - d, kept
    by the job; b - c itself goes."""
    a, b, c = pair
    session = new_session()
    d = session.execute(text(
        'INSERT INTO tag (name, type_id) VALUES (:n, 1) RETURNING id'),
        {'n': NAMES[3]}).scalar()
    session.execute(text(
        'INSERT INTO tag_similarity (tag_a, tag_b, kind, reason, status, '
        'checked) VALUES (:b, :d, \'related\', \'name\', \'new\', true)'),
        {'b': b, 'd': d})
    session.commit()

    assert admin_client.post(f'/api/tags/{c}/merge/{b}').status_code == 200
    rows = {(r.tag_a, r.tag_b): r for r in session.execute(text(
        'SELECT tag_a, tag_b, kind, reason, status, checked, kind_fixed '
        'FROM tag_similarity WHERE tag_a = ANY(:ids) AND tag_b = ANY(:ids)'),
        {'ids': [a, b, c, d]})}
    session.close()
    assert set(rows) == {(a, c), (min(c, d), max(c, d))}
    assert (rows[a, c].reason, rows[a, c].kind_fixed) == ('usage', False)
    moved = rows[min(c, d), max(c, d)]
    assert (moved.reason, moved.checked, moved.kind_fixed) == \
        ('name', True, True)


def test_merge_keeps_the_decided_pair(admin_client, pair):
    """b - c is dismissed; merging b into a meets a - c (undecided), so the
    dismissal wins."""
    a, b, c = pair
    assert admin_client.post(f'/api/tags/{a}/merge/{b}').status_code == 200
    session = new_session()
    row = session.execute(text(
        'SELECT reason, status FROM tag_similarity '
        'WHERE tag_a = :a AND tag_b = :c'), {'a': a, 'c': c}).one()
    session.close()
    assert (row.reason, row.status) == ('name', 'dismissed')
