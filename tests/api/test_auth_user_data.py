"""
Authorization of admin-only writes and of users' own data.

Five endpoints once had their auth decorator above @app.route, which made
Flask register the undecorated function, so anyone could call them; and
/api/works/shorts had no check at all. User-data endpoints (wishlist,
ownership, read status) only checked that *someone* was logged in, not that
the user id in the request was the caller's own.

Rules pinned here:
  - no token -> 401
  - admin-only endpoint called by a regular user -> 403
  - a regular user acting on another user's id -> 403
  - a regular user acting on their own id -> allowed

Uses the raw Flask test `client` with Bearer headers, as
test_pricing_auth.py does (see its docstring for why).
"""
import pytest

from app.orm_decl import User
from app.route_helpers import new_session

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'
SECOND_USER_NAME = 'Test User 2'
SECOND_USER_PASSWORD = 'testpassword456'

EDITION_ID = 86
WORK_ID = 1


def _login(client, name, password):
    resp = client.post('/api/login', json={'username': name, 'password': password})
    assert resp.status_code == 200, resp.get_json()
    return {'Authorization': f"Bearer {resp.get_json()['access_token']}"}


def _user_id(name):
    session = new_session()
    try:
        return session.query(User).filter_by(name=name).one().id
    finally:
        session.close()


@pytest.fixture(scope='module')
def second_user_id(app):
    """A second non-admin user (created once, idempotent)."""
    session = new_session()
    try:
        user = session.query(User).filter_by(name=SECOND_USER_NAME).first()
        if user is None:
            user = User(name=SECOND_USER_NAME,
                        email='test-user-2@example.invalid', is_admin=False)
            user.set_password(SECOND_USER_PASSWORD)
            session.add(user)
            session.commit()
        return user.id
    finally:
        session.close()


@pytest.fixture
def user_id(app):
    return _user_id(TEST_USER_NAME)


@pytest.fixture
def user_headers(client):
    return _login(client, TEST_USER_NAME, TEST_USER_PASSWORD)


@pytest.fixture
def admin_headers(client):
    return _login(client, TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)


ADMIN_ONLY = [
    ('put', '/api/awards/works/awards'),
    ('put', '/api/awards/people/awards'),
    ('post', '/api/awarded'),
    ('put', '/api/works/shorts'),
    ('post', '/api/works/shorts'),
]

USER_DATA = [
    ('put', f'/api/editions/{EDITION_ID}/wishlist/{{uid}}'),
    ('delete', f'/api/editions/{EDITION_ID}/wishlist/{{uid}}'),
    ('delete', f'/api/works/{WORK_ID}/read/{{uid}}'),
    ('delete', f'/api/editions/{EDITION_ID}/owner/{{uid}}'),
]


@pytest.mark.parametrize('method,url', ADMIN_ONLY + USER_DATA + [
    ('post', '/api/works/read'),
    ('post', '/api/editions/owner'),
    ('put', '/api/editions/owner'),
])
def test_no_token_is_401(client, method, url):
    response = getattr(client, method)(url.format(uid=1), json={})
    assert response.status_code == 401


@pytest.mark.parametrize('method,url', ADMIN_ONLY)
def test_admin_only_refuses_regular_user(client, user_headers, method, url):
    response = getattr(client, method)(url, json={}, headers=user_headers)
    assert response.status_code == 403


@pytest.mark.parametrize('method,url', USER_DATA)
def test_other_users_data_is_403(client, user_headers, second_user_id, method, url):
    response = getattr(client, method)(url.format(uid=second_user_id),
                                       headers=user_headers)
    assert response.status_code == 403


def test_read_status_for_other_user_is_403(client, user_headers, second_user_id):
    response = client.post('/api/works/read', headers=user_headers,
                           json={'work_id': WORK_ID, 'user_id': second_user_id})
    assert response.status_code == 403


@pytest.mark.parametrize('method', ['post', 'put'])
def test_ownership_for_other_user_is_403(client, user_headers, second_user_id, method):
    response = getattr(client, method)(
        '/api/editions/owner', headers=user_headers,
        json={'editionid': EDITION_ID, 'edition_id': EDITION_ID,
              'userid': second_user_id, 'user_id': second_user_id,
              'condition': 1})
    assert response.status_code == 403


def test_own_wishlist_add_and_remove(client, user_headers, user_id):
    url = f'/api/editions/{EDITION_ID}/wishlist/{user_id}'
    try:
        assert client.put(url, headers=user_headers).status_code == 200
        status = client.get(url, headers=user_headers)
        assert status.status_code == 200
    finally:
        assert client.delete(url, headers=user_headers).status_code == 200


def test_own_read_status_set_and_remove(client, user_headers, user_id):
    try:
        response = client.post('/api/works/read', headers=user_headers,
                               json={'work_id': WORK_ID, 'user_id': user_id,
                                     'opinion': 1})
        assert response.status_code == 200
    finally:
        response = client.delete(f'/api/works/{WORK_ID}/read/{user_id}',
                                 headers=user_headers)
        assert response.status_code == 200


def test_admin_may_act_on_other_users_data(client, admin_headers, second_user_id):
    url = f'/api/editions/{EDITION_ID}/wishlist/{second_user_id}'
    try:
        assert client.put(url, headers=admin_headers).status_code == 200
    finally:
        assert client.delete(url, headers=admin_headers).status_code == 200


def test_edition_wishlist_list_works(client):
    """GET /api/editions/<id>/wishlist used to fail with 500."""
    response = client.get(f'/api/editions/{EDITION_ID}/wishlist')
    assert response.status_code == 200
    assert isinstance(response.get_json(), list)
