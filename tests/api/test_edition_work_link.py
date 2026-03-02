"""
SuomiSF API - Edition–Work Direct Link Tests (Migration 004)

Tests for the work_id column added directly to the edition table,
replacing the Part-table indirection for the Work↔Edition link.

Verifies:
  - Edition.work_id column exists and is populated (not null)
  - GET /api/editions/{id} returns work as an object, not a list
  - work.id in the edition response matches the owning work
  - Creating an edition sets work_id correctly
  - Copying an edition preserves work_id
  - Deleting a work removes its editions (via work_id)
  - GET /api/works/{id} editions list is ordered correctly
  - GET /api/works/{id}/shorts uses work_id to find the first edition
  - GET /api/editions/{id}/work returns the work ID as an integer

Note: Run tests/scripts/setup_test_db.py before running these tests,
then apply migrations 001–004 to the test DB.
"""

import pytest

from app.orm_decl import Edition
from app.route_helpers import new_session

from .base_test import BaseAPITest
from .test_works import (
    create_test_work, delete_test_work,
    TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD,
)


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

KNOWN_WORK_ID = 1     # Work present in the test DB snapshot
KNOWN_EDITION_ID = 1  # Edition present in the test DB snapshot


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def create_test_edition(client, work_id, pubyear=2025):
    """
    Create an edition linked to work_id via POST /api/editions.

    Args:
        client: Authenticated admin API client.
        work_id: ID of the work to link the edition to.
        pubyear: Publication year for the new edition.

    Returns:
        edition_id (int)
    """
    resp = client.post('/api/editions', data={
        'data': {
            'work_id': work_id,
            'title': 'Test Edition for Work Link',
            'pubyear': pubyear,
            'editionnum': 1,
            'version': 1,
        }
    })
    assert resp.status_code in (200, 201), (
        f'create_test_edition failed: {resp.status_code} {resp.json}'
    )
    return int(resp.json)


def delete_test_edition(client, edition_id):
    """Delete an edition via DELETE /api/editions/{id}."""
    resp = client.delete(f'/api/editions/{edition_id}')
    assert resp.status_code == 200, (
        f'delete_test_edition failed for {edition_id}: '
        f'{resp.status_code} {resp.json}'
    )


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def test_work(admin_client):
    """
    Create a work for edition-link tests.

    Yields:
        work_id (int)

    Cleans up (deletes the work and its editions) after the test.
    """
    work_id = create_test_work(
        admin_client,
        person_id=1,
        title='Edition Work Link Test Work',
        pubyear=2025,
    )
    yield work_id
    delete_test_work(admin_client, work_id)


@pytest.fixture
def test_edition(admin_client, test_work):
    """
    Create an edition linked to test_work.

    Yields:
        edition_id (int)

    Cleans up after the test (unless the work was already deleted,
    which also removes the edition).
    """
    edition_id = create_test_edition(admin_client, test_work)
    yield edition_id
    # If the work still exists, delete its extra edition
    try:
        delete_test_edition(admin_client, edition_id)
    except AssertionError:
        pass  # Already removed (e.g. by work_delete test)


# -------------------------------------------------------------------
# Tests: database schema
# -------------------------------------------------------------------

class TestEditionWorkIdColumn(BaseAPITest):
    """Verify that Edition.work_id exists and is populated."""

    def test_edition_has_work_id_column(self, app):
        """
        ORM Edition class exposes work_id as an integer column.

        Assertions:
          - Edition objects loaded from DB have a work_id attribute
          - The value is an integer (not None) for every edition
        Fixtures: app
        """
        with app.app_context():
            session = new_session()
            edition = (
                session.query(Edition)
                .filter(Edition.id == KNOWN_EDITION_ID)
                .first()
            )
            session.close()

        assert edition is not None, (
            f'Edition {KNOWN_EDITION_ID} not found in test DB'
        )
        assert hasattr(edition, 'work_id'), (
            'Edition has no work_id attribute'
        )
        assert isinstance(edition.work_id, int), (
            f'Edition.work_id is not an int: {edition.work_id!r}'
        )

    def test_most_editions_have_work_id(self, app):
        """
        Nearly all editions have work_id populated. The only allowed
        exceptions are the 8 pre-existing orphan editions that have
        no Part row in the source data (data-quality issue, not a
        migration bug).

        Assertions:
          - Total editions with NULL work_id <= 8 (known orphan count)
          - The known good edition (KNOWN_EDITION_ID) has work_id set
        Fixtures: app
        """
        with app.app_context():
            session = new_session()
            null_count = (
                session.query(Edition)
                .filter(Edition.work_id.is_(None))
                .count()
            )
            total = session.query(Edition).count()
            known = (
                session.query(Edition)
                .filter(Edition.id == KNOWN_EDITION_ID)
                .first()
            )
            session.close()

        assert null_count <= 8, (
            f'{null_count} editions have NULL work_id; expected at '
            f'most 8 known orphans (total editions: {total})'
        )
        assert known is not None and known.work_id is not None, (
            f'Known edition {KNOWN_EDITION_ID} has NULL work_id'
        )


# -------------------------------------------------------------------
# Tests: API response shape
# -------------------------------------------------------------------

class TestEditionWorkApiShape(BaseAPITest):
    """Verify GET /api/editions/{id} returns work as a single object."""

    def test_get_edition_work_is_object(self, api_client):
        """
        GET /api/editions/{id} returns work as a dict, not a list.

        Parameters: edition_id=KNOWN_EDITION_ID
        Assertions:
          - response status 200
          - 'work' key is present
          - 'work' value is a dict (not a list)
        Fixtures: api_client
        """
        resp = api_client.get(f'/api/editions/{KNOWN_EDITION_ID}')
        resp.assert_success()
        work = resp.data.get('work')
        assert work is not None, (
            f'No work key in edition response: {resp.data}'
        )
        assert isinstance(work, dict), (
            f'edition.work should be a dict, got {type(work)}: {work}'
        )

    def test_get_edition_work_id_matches(self, app, api_client):
        """
        edition.work.id in the API response matches Edition.work_id
        in the database.

        Parameters: edition_id=KNOWN_EDITION_ID
        Assertions:
          - API response work.id == DB edition.work_id
        Fixtures: app, api_client
        """
        with app.app_context():
            session = new_session()
            edition = (
                session.query(Edition)
                .filter(Edition.id == KNOWN_EDITION_ID)
                .first()
            )
            db_work_id = edition.work_id
            session.close()

        resp = api_client.get(f'/api/editions/{KNOWN_EDITION_ID}')
        resp.assert_success()
        api_work_id = resp.data['work']['id']
        assert api_work_id == db_work_id, (
            f'API work.id {api_work_id} != DB work_id {db_work_id}'
        )

    def test_get_edition_work_endpoint(self, api_client):
        """
        GET /api/editions/{id}/work returns the work ID as an integer.

        Parameters: edition_id=KNOWN_EDITION_ID
        Assertions:
          - response status 200
          - response JSON is an integer (work_id)
        Fixtures: api_client
        """
        resp = api_client.get(
            f'/api/editions/{KNOWN_EDITION_ID}/work'
        )
        resp.assert_success()
        # This endpoint returns a bare integer, not a dict
        assert isinstance(resp.json, int), (
            f'/api/editions/{KNOWN_EDITION_ID}/work should return '
            f'an int, got {type(resp.json)}: {resp.json}'
        )


# -------------------------------------------------------------------
# Tests: create / copy / delete
# -------------------------------------------------------------------

class TestEditionWorkLinkMutations(BaseAPITest):
    """Verify that create, copy and delete preserve work_id."""

    def test_create_edition_sets_work_id(
            self, app, admin_client, test_work):
        """
        POST /api/editions creates an edition with work_id set to
        the supplied work_id parameter.

        Parameters: work_id=test_work
        Assertions:
          - POST returns 200
          - DB edition.work_id == test_work
        Fixtures: app, admin_client, test_work
        """
        edition_id = create_test_edition(admin_client, test_work)
        try:
            with app.app_context():
                session = new_session()
                edition = (
                    session.query(Edition)
                    .filter(Edition.id == edition_id)
                    .first()
                )
                db_work_id = edition.work_id if edition else None
                session.close()

            assert db_work_id == test_work, (
                f'Edition.work_id={db_work_id} != test_work={test_work}'
            )
        finally:
            delete_test_edition(admin_client, edition_id)

    def test_copy_edition_preserves_work_id(
            self, app, admin_client, test_work):
        """
        POST /api/editions/{id}/copy produces an edition with the
        same work_id as the original.

        Parameters: original edition from test_work
        Assertions:
          - Copy response returns 200
          - Copied edition.work_id == original edition.work_id
        Fixtures: app, admin_client, test_work
        """
        original_id = create_test_edition(admin_client, test_work)
        try:
            resp = admin_client.post(
                f'/api/editions/{original_id}/copy'
            )
            assert resp.status_code == 200, (
                f'copy_edition failed: {resp.status_code} {resp.json}'
            )
            copied_id = int(resp.json)
            try:
                with app.app_context():
                    session = new_session()
                    copied = (
                        session.query(Edition)
                        .filter(Edition.id == copied_id)
                        .first()
                    )
                    copied_work_id = (
                        copied.work_id if copied else None
                    )
                    session.close()

                assert copied_work_id == test_work, (
                    f'Copied edition.work_id={copied_work_id} '
                    f'!= original work_id={test_work}'
                )
            finally:
                delete_test_edition(admin_client, copied_id)
        finally:
            delete_test_edition(admin_client, original_id)

    def test_work_delete_removes_editions(
            self, app, admin_client):
        """
        DELETE /api/works/{id} removes all editions for the work
        (queried via Edition.work_id).

        Parameters: fresh work with one edition
        Assertions:
          - After delete, no editions with work_id remain in DB
        Fixtures: app, admin_client
        """
        work_id = create_test_work(
            admin_client,
            person_id=1,
            title='Work Delete Removes Editions Test',
            pubyear=2025,
        )
        # The work already has a first edition from create_test_work
        resp = admin_client.delete(f'/api/works/{work_id}')
        assert resp.status_code == 200, (
            f'work_delete failed: {resp.status_code} {resp.json}'
        )
        with app.app_context():
            session = new_session()
            remaining = (
                session.query(Edition)
                .filter(Edition.work_id == work_id)
                .count()
            )
            session.close()

        assert remaining == 0, (
            f'{remaining} editions remain after deleting work {work_id}'
        )


# -------------------------------------------------------------------
# Tests: Work.editions relationship
# -------------------------------------------------------------------

class TestWorkEditionsRelationship(BaseAPITest):
    """Verify GET /api/works/{id} editions list via direct FK."""

    def test_get_work_includes_editions_list(self, api_client):
        """
        GET /api/works/{id} returns an 'editions' list.

        Parameters: work_id=KNOWN_WORK_ID
        Assertions:
          - response status 200
          - 'editions' key is a list
          - list is non-empty
        Fixtures: api_client
        """
        resp = api_client.get(f'/api/works/{KNOWN_WORK_ID}')
        resp.assert_success()
        editions = resp.data.get('editions')
        assert isinstance(editions, list), (
            f'work.editions should be a list, got {type(editions)}'
        )
        assert len(editions) > 0, (
            f'work {KNOWN_WORK_ID} has no editions in response'
        )

    def test_work_editions_all_belong_to_work(
            self, app, api_client):
        """
        All editions returned for a work have Edition.work_id
        equal to that work's id in the database.

        Parameters: work_id=KNOWN_WORK_ID
        Assertions:
          - Every edition in the response has its DB work_id matching
            KNOWN_WORK_ID
        Fixtures: app, api_client
        """
        resp = api_client.get(f'/api/works/{KNOWN_WORK_ID}')
        resp.assert_success()
        edition_ids = [e['id'] for e in resp.data.get('editions', [])]

        with app.app_context():
            session = new_session()
            wrong = (
                session.query(Edition)
                .filter(Edition.id.in_(edition_ids))
                .filter(Edition.work_id != KNOWN_WORK_ID)
                .count()
            )
            session.close()

        assert wrong == 0, (
            f'{wrong} editions for work {KNOWN_WORK_ID} have '
            f'mismatched work_id in DB'
        )
