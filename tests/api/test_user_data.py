"""
Users' own data: ownership, read status, wishlist, and the admin price
tools that feed collection value (coverage plan step B1).

Each test runs a whole flow through the API as the user it belongs to and
removes what it created, also when an assertion fails, so later snapshot
tests see an unchanged database.

Uses the raw Flask test `client` with Bearer headers, as
test_pricing_auth.py does (see its docstring for why).
"""
import pytest

from app.orm_decl import (AntikvaariExcludedBook, AntikvaariPrice,
                          AntikvaariWorkProduct, BookCondition, Edition, User,
                          UserBook, UserWork, Work)
from app.route_helpers import new_session

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'

EDITION_ID = 86
WORK_ID = 1
TEST_PRODUCT_ID = 'b1-test-product-0001'
TEST_BOOK_IDS = ['b1-test-book-0001', 'b1-test-book-0002']


def _login(client, name, password):
    resp = client.post('/api/login', json={'username': name, 'password': password})
    assert resp.status_code == 200, resp.get_json()
    return {'Authorization': f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def user_id(app):
    session = new_session()
    try:
        return session.query(User).filter_by(name=TEST_USER_NAME).one().id
    finally:
        session.close()


@pytest.fixture
def user_headers(client):
    return _login(client, TEST_USER_NAME, TEST_USER_PASSWORD)


@pytest.fixture
def admin_headers(client):
    return _login(client, TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)


@pytest.fixture
def clean_userbook(user_id):
    """Make sure the test user has no row for EDITION_ID before and after."""
    def clean():
        session = new_session()
        try:
            session.query(UserBook).filter_by(user_id=user_id,
                                              edition_id=EDITION_ID).delete()
            session.commit()
        finally:
            session.close()
    clean()
    yield
    clean()


@pytest.fixture
def clean_userwork(user_id):
    def clean():
        session = new_session()
        try:
            session.query(UserWork).filter_by(user_id=user_id, work_id=WORK_ID).delete()
            session.commit()
        finally:
            session.close()
    clean()
    yield
    clean()


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def test_ownership_flow(client, user_headers, user_id, clean_userbook):
    """Add -> read -> owned list -> update condition -> stats -> remove."""
    resp = client.post('/api/editions/owner', headers=user_headers,
                       json={'editionid': EDITION_ID, 'userid': user_id, 'condition': 2})
    assert resp.status_code == 200, resp.get_json()

    resp = client.get(f'/api/editions/{EDITION_ID}/owner/{user_id}', headers=user_headers)
    assert resp.status_code == 200
    assert resp.get_json()['condition']['id'] == 2

    owned = client.get(f'/api/editions/owned/{user_id}')
    assert owned.status_code == 200
    assert EDITION_ID in [e['edition_id'] for e in owned.get_json()]

    # The frontend sends the condition by its value, as PUT does here.
    session = new_session()
    try:
        value = session.query(BookCondition).filter_by(id=3).one().value
    finally:
        session.close()
    resp = client.put('/api/editions/owner', headers=user_headers,
                      json={'edition_id': EDITION_ID, 'user_id': user_id,
                            'condition': {'value': value}, 'description': 'b1 test copy'})
    assert resp.status_code == 200, resp.get_json()
    owner = client.get(f'/api/editions/{EDITION_ID}/owner/{user_id}',
                       headers=user_headers).get_json()
    assert owner['condition']['value'] == value
    assert owner['description'] == 'b1 test copy'

    stats = client.get(f'/api/user/{user_id}/collection/stats')
    assert stats.status_code == 200
    assert isinstance(stats.get_json(), dict)

    resp = client.delete(f'/api/editions/{EDITION_ID}/owner/{user_id}', headers=user_headers)
    assert resp.status_code == 200
    owned = client.get(f'/api/editions/owned/{user_id}')
    assert EDITION_ID not in [e['edition_id'] for e in owned.get_json()]


def test_owned_edition_cannot_be_wishlisted(client, user_headers, user_id, clean_userbook):
    """Owning and wishlisting share one row per user and edition."""
    client.post('/api/editions/owner', headers=user_headers,
                json={'editionid': EDITION_ID, 'userid': user_id, 'condition': 2})
    resp = client.put(f'/api/editions/{EDITION_ID}/wishlist/{user_id}', headers=user_headers)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

def test_wishlist_flow(client, user_headers, user_id, clean_userbook):
    """Add -> status -> user's wishlist -> edition's wishlist -> remove."""
    status_url = f'/api/editions/{EDITION_ID}/wishlist/{user_id}'
    assert client.put(status_url, headers=user_headers).status_code == 200
    # adding again is a no-op
    assert client.put(status_url, headers=user_headers).status_code == 200

    status = client.get(status_url)
    assert status.status_code == 200
    assert status.get_json() == {'wishlisted': True}

    wishlist = client.get(f'/api/editions/wishlist/{user_id}')
    assert wishlist.status_code == 200
    assert EDITION_ID in [e['edition_id'] for e in wishlist.get_json()]

    on_edition = client.get(f'/api/editions/{EDITION_ID}/wishlist')
    assert on_edition.status_code == 200
    assert user_id in [row['user']['id'] for row in on_edition.get_json()]

    assert client.delete(status_url, headers=user_headers).status_code == 200
    assert client.get(status_url).get_json() == {'wishlisted': False}
    wishlist = client.get(f'/api/editions/wishlist/{user_id}')
    assert EDITION_ID not in [e['edition_id'] for e in wishlist.get_json()]


# ---------------------------------------------------------------------------
# Read status
# ---------------------------------------------------------------------------

def test_read_status_flow(client, user_headers, user_id, clean_userwork):
    """Mark read -> list -> change opinion -> stats -> unmark."""
    resp = client.post('/api/works/read', headers=user_headers,
                       json={'work_id': WORK_ID, 'user_id': user_id, 'opinion': 1})
    assert resp.status_code == 200, resp.get_json()

    read = client.get(f'/api/works/read/{user_id}')
    assert read.status_code == 200
    rows = {r['work_id']: r for r in read.get_json()}
    assert rows[WORK_ID]['opinion'] == 1

    resp = client.put('/api/works/read', headers=user_headers,
                      json={'work_id': WORK_ID, 'user_id': user_id, 'opinion': -1})
    assert resp.status_code == 200
    rows = {r['work_id']: r for r in client.get(f'/api/works/read/{user_id}').get_json()}
    assert rows[WORK_ID]['opinion'] == -1

    stats = client.get(f'/api/user/{user_id}/read/stats')
    assert stats.status_code == 200

    resp = client.delete(f'/api/works/{WORK_ID}/read/{user_id}', headers=user_headers)
    assert resp.status_code == 200
    rows = {r['work_id'] for r in client.get(f'/api/works/read/{user_id}').get_json()}
    assert WORK_ID not in rows


def test_read_status_rejects_bad_opinion(client, user_headers, user_id, clean_userwork):
    resp = client.post('/api/works/read', headers=user_headers,
                       json={'work_id': WORK_ID, 'user_id': user_id, 'opinion': 5})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Admin price tools
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_price_rows(app):
    def clean():
        session = new_session()
        try:
            session.query(AntikvaariWorkProduct).filter_by(
                antikvaari_product_id=TEST_PRODUCT_ID).delete()
            session.query(AntikvaariPrice).filter(
                AntikvaariPrice.antikvaari_book_id.in_(TEST_BOOK_IDS)).delete()
            session.query(AntikvaariExcludedBook).filter(
                AntikvaariExcludedBook.antikvaari_book_id.in_(TEST_BOOK_IDS)).delete()
            session.commit()
        finally:
            session.close()
    clean()
    yield
    clean()


def test_work_products_link_list_and_delete(client, admin_headers, clean_price_rows):
    url = f'/api/work/{WORK_ID}/antikvaari/products'
    resp = client.post(url, headers=admin_headers, json=[TEST_PRODUCT_ID])
    assert resp.status_code == 200
    assert resp.get_json() == {'added': 1}

    # additive: linking the same product again adds nothing
    resp = client.post(url, headers=admin_headers, json=[TEST_PRODUCT_ID])
    assert resp.get_json() == {'added': 0}

    listed = client.get(url, headers=admin_headers)
    assert listed.status_code == 200
    assert TEST_PRODUCT_ID in str(listed.get_json())

    resp = client.delete(f'{url}/{TEST_PRODUCT_ID}', headers=admin_headers)
    assert resp.status_code == 200
    assert TEST_PRODUCT_ID not in str(client.get(url, headers=admin_headers).get_json())


def test_work_products_rejects_non_list(client, admin_headers):
    resp = client.post(f'/api/work/{WORK_ID}/antikvaari/products',
                       headers=admin_headers, json={'product_id': TEST_PRODUCT_ID})
    assert resp.status_code == 400


def test_work_products_missing_work_is_404(client, admin_headers, clean_price_rows):
    resp = client.post('/api/work/999999999/antikvaari/products',
                       headers=admin_headers, json=[TEST_PRODUCT_ID])
    assert resp.status_code == 404


def _edition_matching_row(work_id, book_id, **extra):
    """A price row whose year/painos/laitos match one of the work's editions."""
    session = new_session()
    try:
        edition = (session.query(Edition).join(Work)
                   .filter(Work.id == work_id).order_by(Edition.id).first())
        row = {
            'antikvaari_book_id': book_id,
            'antikvaari_product_id': TEST_PRODUCT_ID,
            'antikvaari_product_year': edition.pubyear,
            'antikvaari_product_version': edition.editionnum or 1,
            'antikvaari_product_laitos': edition.version or 1,
            'condition': 'K3',
            'price': 12.5,
            'seller': 'b1 test seller',
        }
        row.update(extra)
        return edition.id, row
    finally:
        session.close()


def test_prices_save_all_saves_skips_and_excludes(client, admin_headers, clean_price_rows):
    url = f'/api/work/{WORK_ID}/antikvaari/prices'
    edition_id, row = _edition_matching_row(WORK_ID, TEST_BOOK_IDS[0])

    resp = client.post(url, headers=admin_headers, json=[row])
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body['saved'] == 1, body
    assert body['rows'][0]['edition_id'] == edition_id

    # the same row again is unchanged and not re-inserted
    body = client.post(url, headers=admin_headers, json=[row]).get_json()
    assert body['saved'] == 0 and body['skipped'] == 1

    # a copy the admin excluded goes to the exclusion table instead
    _, excluded = _edition_matching_row(WORK_ID, TEST_BOOK_IDS[1], user_excluded=True)
    body = client.post(url, headers=admin_headers, json=[excluded]).get_json()
    assert body['saved'] == 0
    assert body['rows'][0]['reason'] == 'excluded'
    session = new_session()
    try:
        assert session.query(AntikvaariExcludedBook).filter_by(
            antikvaari_book_id=TEST_BOOK_IDS[1]).count() == 1
    finally:
        session.close()


def test_prices_save_all_rejects_non_list(client, admin_headers):
    resp = client.post(f'/api/work/{WORK_ID}/antikvaari/prices',
                       headers=admin_headers, json={'rows': []})
    assert resp.status_code == 400


def test_work_edition_prices_for_owner(client, user_headers, user_id):
    resp = client.get(f'/api/user/{user_id}/work/{WORK_ID}/edition-prices',
                      headers=user_headers)
    assert resp.status_code == 200
