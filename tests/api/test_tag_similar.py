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
NAMES = ('zz similar test a', 'zz similar test b', 'zz similar test c')


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
        {'n': n}).scalar() for n in NAMES]
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
    resp = admin_client.post('/api/tags/similar/dismiss',
                             data={'tag_a': b, 'tag_b': a})
    assert resp.status_code == 200
    assert resp.data == {'tag_a': a, 'tag_b': b, 'status': 'dismissed'}
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
