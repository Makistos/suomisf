"""
Tests for Antikvaari price authorship.

Covers: the user who adds a price row is recorded, is exposed via the GET
endpoint as added_by_name, and PUT/DELETE on a single price row are
restricted to admins or that row's original adder — deliberately narrower
than the edition-ownership model used for viewing/adding prices (an edition
can have several co-owners, each adding their own price entries, and one
owner shouldn't be able to edit or delete another owner's entry).

Uses the raw Flask test `client` fixture with manually attached Bearer
headers, rather than conftest.py's APITestClient — importing that class via
`from tests.conftest import APITestClient` re-executes conftest.py's
module-level DATABASE_URL setup a second time (tests/ has no __init__.py, so
that import resolves to a separate module object from the one pytest's own
conftest loader already ran), clobbering the credentialed test DB URL with
the placeholder one back to before app/__init__.py's dotenv override ran.

Direct DB setup/teardown goes through app.route_helpers.new_session(), the
same session factory the app itself uses.

Note: Run tests/scripts/setup_test_db.py before running these tests.
"""
import pytest

from app.orm_decl import AntikvaariPrice, PriceSource, User, UserBook
from app.route_helpers import new_session

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'
TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'

# A second, distinct non-admin identity — conftest's create_test_users() only
# provisions one non-admin user, but denial tests need someone who is neither
# the adder nor an admin.
SECOND_USER_NAME = 'Test User 2'
SECOND_USER_PASSWORD = 'testpassword456'

# Edition 1 exists in every clone of the live DB (see test_editions_extra.py).
TEST_EDITION_ID = 1


def _login(client, name, password):
    resp = client.post('/api/login',
                       json={'username': name, 'password': password})
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def _add_price(client, headers, edition_id, source_id, price=9.99):
    resp = client.post(f'/api/edition/{edition_id}/prices/manual', headers=headers,
                       json={'source_id': source_id, 'condition': 'K3', 'price': price})
    assert resp.status_code == 200, resp.get_json()
    return resp


def _get_prices(client, headers, edition_id):
    resp = client.get(f'/api/edition/{edition_id}/antikvaari/prices', headers=headers)
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def second_user_id(app):
    """A second, distinct non-admin test user (created once, kept idempotent)."""
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
def owner_headers(client):
    """'Test User', who owns TEST_EDITION_ID for the duration of a test."""
    return _login(client, TEST_USER_NAME, TEST_USER_PASSWORD)


@pytest.fixture
def other_headers(client, second_user_id):
    """A second non-admin user unrelated to TEST_EDITION_ID or its prices."""
    return _login(client, SECOND_USER_NAME, SECOND_USER_PASSWORD)


@pytest.fixture
def admin_headers(client):
    return _login(client, TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)


@pytest.fixture
def owned_edition(app):
    """Give 'Test User' ownership of TEST_EDITION_ID for the duration of a test."""
    session = new_session()
    try:
        user = session.query(User).filter_by(name=TEST_USER_NAME).first()
        existing = session.query(UserBook).filter_by(
            user_id=user.id, edition_id=TEST_EDITION_ID).first()
        if existing:
            yield TEST_EDITION_ID
            return
        session.add(UserBook(user_id=user.id, edition_id=TEST_EDITION_ID))
        session.commit()
        yield TEST_EDITION_ID
        session.query(UserBook).filter_by(
            user_id=user.id, edition_id=TEST_EDITION_ID).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def price_source_id(app):
    session = new_session()
    try:
        source = session.query(PriceSource).first()
        assert source, 'No price sources in test DB'
        return source.id
    finally:
        session.close()


@pytest.fixture
def added_price_id(client, owner_headers, admin_headers, owned_edition, price_source_id):
    """A fresh price row added via the API by 'Test User', the edition's owner."""
    _add_price(client, owner_headers, owned_edition, price_source_id, price=9.99)
    rows = _get_prices(client, admin_headers, owned_edition)
    price_id = max(row['id'] for row in rows)
    yield price_id
    session = new_session()
    try:
        session.query(AntikvaariPrice).filter_by(id=price_id).delete()
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Recording who added a price
# ---------------------------------------------------------------------------

class TestPriceAuthorRecorded:

    def test_manual_add_records_adder(self, client, owner_headers, admin_headers,
                                       owned_edition, price_source_id):
        _add_price(client, owner_headers, owned_edition, price_source_id, price=7.5)
        rows = _get_prices(client, admin_headers, owned_edition)
        row = max(rows, key=lambda r: r['id'])
        session = new_session()
        try:
            user = session.query(User).filter_by(name=TEST_USER_NAME).first()
            assert row['user_id'] == user.id
            assert row['added_by_name'] == TEST_USER_NAME
        finally:
            session.query(AntikvaariPrice).filter_by(id=row['id']).delete()
            session.commit()
            session.close()

    def test_legacy_rows_show_no_adder(self, client, admin_headers):
        """Rows predating this feature (user_id NULL) report no adder."""
        session = new_session()
        try:
            row = session.query(AntikvaariPrice).filter(
                AntikvaariPrice.user_id.is_(None)).first()
            if row is None:
                pytest.skip('no legacy (user_id NULL) price rows in test DB')
            edition_id, price_id = row.edition_id, row.id
        finally:
            session.close()
        rows = _get_prices(client, admin_headers, edition_id)
        matching = next(r for r in rows if r['id'] == price_id)
        assert matching['user_id'] is None
        assert matching['added_by_name'] is None


# ---------------------------------------------------------------------------
# PUT / DELETE authorization: admin, or the original adder, only
# ---------------------------------------------------------------------------

class TestPriceAuthorAuthorization:

    def test_adder_can_update_own_price(self, client, owner_headers, added_price_id,
                                        price_source_id):
        resp = client.put(f'/api/antikvaari/prices/{added_price_id}', headers=owner_headers,
                          json={'source_id': price_source_id, 'condition': 'K2', 'price': 11.0})
        assert resp.status_code == 200, resp.get_json()

    def test_adder_can_delete_own_price(self, client, owner_headers, added_price_id):
        resp = client.delete(f'/api/antikvaari/prices/{added_price_id}', headers=owner_headers)
        assert resp.status_code == 200, resp.get_json()

    def test_other_user_cannot_update(self, client, other_headers, added_price_id,
                                      price_source_id):
        resp = client.put(f'/api/antikvaari/prices/{added_price_id}', headers=other_headers,
                          json={'source_id': price_source_id, 'condition': 'K2', 'price': 11.0})
        assert resp.status_code == 403

    def test_other_user_cannot_delete(self, client, other_headers, added_price_id):
        resp = client.delete(f'/api/antikvaari/prices/{added_price_id}', headers=other_headers)
        assert resp.status_code == 403

    def test_admin_can_update_others_price(self, client, admin_headers, added_price_id,
                                           price_source_id):
        resp = client.put(f'/api/antikvaari/prices/{added_price_id}', headers=admin_headers,
                          json={'source_id': price_source_id, 'condition': 'K1', 'price': 20.0})
        assert resp.status_code == 200, resp.get_json()

    def test_admin_can_delete_others_price(self, client, admin_headers, added_price_id):
        resp = client.delete(f'/api/antikvaari/prices/{added_price_id}', headers=admin_headers)
        assert resp.status_code == 200, resp.get_json()

    def test_update_does_not_change_recorded_adder(self, client, admin_headers, added_price_id,
                                                    price_source_id):
        resp = client.put(f'/api/antikvaari/prices/{added_price_id}', headers=admin_headers,
                          json={'source_id': price_source_id, 'condition': 'K1', 'price': 99.0})
        assert resp.status_code == 200, resp.get_json()
        session = new_session()
        try:
            row = session.query(AntikvaariPrice).filter_by(id=added_price_id).first()
            user = session.query(User).filter_by(name=TEST_USER_NAME).first()
            assert row.user_id == user.id
        finally:
            session.close()
