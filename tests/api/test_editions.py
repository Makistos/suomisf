"""
SuomiSF API Editions CRUD Tests

Tests for edition lifecycle:
- Creating work auto-creates first edition
- Editing editions
- Adding additional editions
- Deleting editions (except last one)
- Edition cleanup when work is deleted

Note: Run tests/scripts/setup_test_db.py before running these tests.
"""

import pytest

from .base_test import BaseAPITest
from .test_works import (
    create_test_work, delete_test_work,
    TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD
)


# -------------------------------------------------------------------
# Reusable helper functions for edition operations
# -------------------------------------------------------------------

def create_test_edition(admin_client, work_id, title='Test Edition',
                        pubyear=2025, editionnum=1, publisher_id=1):
    """
    Create a test edition via the API.

    Args:
        admin_client: Authenticated API client with admin privileges
        work_id: ID of work to attach edition to
        title: Edition title
        pubyear: Publication year
        editionnum: Edition number (1 = first edition, etc.)
        publisher_id: ID of publisher

    Returns:
        int: The created edition ID

    Raises:
        AssertionError: If edition creation fails
    """
    edition_data = {
        'data': {
            'work_id': work_id,
            'title': title,
            'pubyear': pubyear,
            'editionnum': editionnum,
            'publisher': {'id': publisher_id}
        }
    }

    response = admin_client.post('/api/editions', data=edition_data)

    assert response.status_code == 201, (
        f"Failed to create edition. Status: {response.status_code}. "
        f"Response: {response.json}"
    )

    edition_id = int(response.data)
    assert edition_id > 0, "Should return valid edition ID"

    return edition_id


def update_test_edition(admin_client, edition_id, **fields):
    """
    Update a test edition via the API.

    Args:
        admin_client: Authenticated API client with admin privileges
        edition_id: ID of edition to update
        **fields: Fields to update (title, pubyear, subtitle, etc.)

    Returns:
        APIResponse: The update response

    Raises:
        AssertionError: If edition update fails
    """
    # First get current edition data (editionnum is required for update)
    get_resp = admin_client.get(f'/api/editions/{edition_id}')
    get_resp.assert_success()
    current = get_resp.data

    # Build update data with required fields
    edition_data = {
        'data': {
            'id': edition_id,
            'editionnum': current.get('editionnum', 1),
            **fields
        }
    }

    response = admin_client.put('/api/editions', data=edition_data)

    assert response.status_code == 200, (
        f"Failed to update edition {edition_id}. "
        f"Status: {response.status_code}. Response: {response.json}"
    )

    return response


def delete_test_edition(admin_client, edition_id):
    """
    Delete a test edition via the API.

    Args:
        admin_client: Authenticated API client with admin privileges
        edition_id: ID of edition to delete

    Returns:
        APIResponse: The delete response

    Raises:
        AssertionError: If edition deletion fails
    """
    response = admin_client.delete(f'/api/editions/{edition_id}')

    assert response.status_code == 200, (
        f"Failed to delete edition {edition_id}. "
        f"Status: {response.status_code}. Response: {response.json}"
    )

    return response


def get_work_editions(admin_client, work_id):
    """
    Get all editions for a work.

    Args:
        admin_client: API client (authenticated or not)
        work_id: ID of work

    Returns:
        list: List of editions for the work
    """
    response = admin_client.get(f'/api/works/{work_id}')
    response.assert_success()
    return response.data.get('editions', [])


# -------------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """Get an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def existing_person_id(app):
    """Get an existing person ID to use as author."""
    from app import db
    from app.orm_decl import Person

    with app.app_context():
        person = db.session.query(Person).first()
        return person.id if person else 1


@pytest.fixture
def existing_publisher_id(app):
    """Get an existing publisher ID."""
    from app import db
    from app.orm_decl import Publisher

    with app.app_context():
        publisher = db.session.query(Publisher).first()
        return publisher.id if publisher else 1


# -------------------------------------------------------------------
# Test classes
# -------------------------------------------------------------------

class TestEditionsCRUD(BaseAPITest):
    """Tests for the complete edition CRUD lifecycle."""

    def test_edition_full_lifecycle(self, admin_client, existing_person_id,
                                    existing_publisher_id):
        """
        Test complete edition lifecycle.

        This test:
        1. Creates a new work (which auto-creates first edition)
        2. Verifies the work has exactly one edition
        3. Edits the first edition
        4. Verifies the edit was persisted
        5. Adds a second edition to the work
        6. Verifies the work now has two editions
        7. Edits the second edition
        8. Verifies the second edit was persisted
        9. Deletes the first edition
        10. Verifies the work now has exactly one edition
        11. Tries to delete the last edition (documents current behavior)
        12. Deletes the work and verifies cleanup
        """

        # ---------------------------------------------------------
        # Step 1: Create a new work (auto-creates first edition)
        # ---------------------------------------------------------
        work_id = create_test_work(
            admin_client,
            existing_person_id,
            title='Test Work for Edition Tests',
            pubyear=2025
        )

        try:
            # ---------------------------------------------------------
            # Step 2: Verify work has exactly one edition
            # ---------------------------------------------------------
            editions = get_work_editions(admin_client, work_id)
            assert len(editions) == 1, (
                f"New work should have exactly 1 edition, got {len(editions)}"
            )

            first_edition_id = editions[0]['id']
            assert first_edition_id > 0, "First edition should have valid ID"

            # ---------------------------------------------------------
            # Step 3: Edit the first edition
            # ---------------------------------------------------------
            update_test_edition(
                admin_client,
                first_edition_id,
                title='Updated First Edition Title',
                subtitle='A Test Subtitle',
                pubyear=2024
            )

            # ---------------------------------------------------------
            # Step 4: Verify the edit was persisted
            # ---------------------------------------------------------
            edition_resp = admin_client.get(
                f'/api/editions/{first_edition_id}'
            )
            edition_resp.assert_success()
            edition_data = edition_resp.data

            assert edition_data['title'] == 'Updated First Edition Title', (
                f"Title not updated. Got: {edition_data.get('title')}"
            )
            assert edition_data.get('subtitle') == 'A Test Subtitle', (
                f"Subtitle not updated. Got: {edition_data.get('subtitle')}"
            )
            assert edition_data['pubyear'] == 2024, (
                f"Pubyear not updated. Got: {edition_data.get('pubyear')}"
            )

            # ---------------------------------------------------------
            # Step 5: Add a second edition to the work
            # ---------------------------------------------------------
            second_edition_id = create_test_edition(
                admin_client,
                work_id,
                title='Second Edition',
                pubyear=2026,
                editionnum=2,
                publisher_id=existing_publisher_id
            )

            # ---------------------------------------------------------
            # Step 6: Verify work now has two editions
            # ---------------------------------------------------------
            editions = get_work_editions(admin_client, work_id)
            assert len(editions) == 2, (
                f"Work should have 2 editions, got {len(editions)}"
            )

            edition_ids = [e['id'] for e in editions]
            assert first_edition_id in edition_ids, (
                "First edition should still exist"
            )
            assert second_edition_id in edition_ids, (
                "Second edition should exist"
            )

            # ---------------------------------------------------------
            # Step 7: Edit the second edition
            # ---------------------------------------------------------
            update_test_edition(
                admin_client,
                second_edition_id,
                title='Updated Second Edition Title',
                pages=300
            )

            # ---------------------------------------------------------
            # Step 8: Verify the second edit was persisted
            # ---------------------------------------------------------
            edition_resp = admin_client.get(
                f'/api/editions/{second_edition_id}'
            )
            edition_resp.assert_success()
            edition_data = edition_resp.data

            assert edition_data['title'] == 'Updated Second Edition Title', (
                f"Title not updated. Got: {edition_data.get('title')}"
            )
            assert edition_data.get('pages') == 300, (
                f"Pages not updated. Got: {edition_data.get('pages')}"
            )

            # ---------------------------------------------------------
            # Step 9: Delete the first edition
            # ---------------------------------------------------------
            delete_test_edition(admin_client, first_edition_id)

            # ---------------------------------------------------------
            # Step 10: Verify work now has exactly one edition
            # ---------------------------------------------------------
            editions = get_work_editions(admin_client, work_id)
            assert len(editions) == 1, (
                f"Work should have 1 edition after delete, got {len(editions)}"
            )
            assert editions[0]['id'] == second_edition_id, (
                "Remaining edition should be the second one"
            )

            # Verify first edition no longer exists
            deleted_resp = admin_client.get(
                f'/api/editions/{first_edition_id}'
            )
            assert deleted_resp.status_code in [400, 404], (
                f"Deleted edition should return 400/404, "
                f"got {deleted_resp.status_code}"
            )

            # ---------------------------------------------------------
            # Step 11: Try to delete the last edition (should fail)
            # Per README, works must have at least one edition.
            # ---------------------------------------------------------
            last_edition_delete = admin_client.delete(
                f'/api/editions/{second_edition_id}'
            )

            # API should prevent deletion of last edition
            assert last_edition_delete.status_code == 400, (
                f"Expected 400 when deleting last edition, "
                f"got {last_edition_delete.status_code}"
            )

            # Verify edition still exists
            editions = get_work_editions(admin_client, work_id)
            assert len(editions) == 1, (
                "Work should still have 1 edition after failed delete"
            )

        finally:
            # ---------------------------------------------------------
            # Step 12: Delete the work (cleanup)
            # ---------------------------------------------------------
            try:
                delete_test_work(admin_client, work_id)
            except AssertionError:
                pass  # Work may not exist if test failed early


class TestEditionsCreateValidation(BaseAPITest):
    """Tests for edition creation validation."""

    def test_create_edition_without_work_id_fails(self, admin_client):
        """POST /api/editions should fail without work_id."""
        edition_data = {
            'data': {
                'title': 'Test Edition',
                'pubyear': 2025
            }
        }

        response = admin_client.post('/api/editions', data=edition_data)
        assert response.status_code == 400, (
            f"Expected 400 Bad Request, got {response.status_code}"
        )

    def test_create_edition_with_invalid_work_id_fails(self, admin_client):
        """POST /api/editions should fail with nonexistent work_id."""
        edition_data = {
            'data': {
                'work_id': 999999999,
                'title': 'Test Edition',
                'pubyear': 2025
            }
        }

        response = admin_client.post('/api/editions', data=edition_data)
        assert response.status_code == 400, (
            f"Expected 400 Bad Request, got {response.status_code}"
        )

    def test_create_edition_without_auth_fails(self, api_client):
        """POST /api/editions should require authentication."""
        edition_data = {
            'data': {
                'work_id': 1,
                'title': 'Test Edition',
                'pubyear': 2025
            }
        }

        response = api_client.post('/api/editions', data=edition_data)
        assert response.status_code in [401, 403, 422], (
            f"Expected 401/403/422, got {response.status_code}"
        )


class TestEditionsRead(BaseAPITest):
    """Tests for reading editions."""

    def test_get_existing_edition(self, api_client):
        """GET /api/editions/{id} should return edition data for valid ID."""
        response = api_client.get('/api/editions/1')
        response.assert_success()

        data = response.data
        assert 'id' in data
        assert data['id'] == 1

    def test_get_nonexistent_edition(self, api_client):
        """GET /api/editions/{id} should return error for invalid ID."""
        response = api_client.get('/api/editions/999999999')
        assert response.status_code in [400, 404]

    def test_get_edition_has_expected_fields(self, api_client):
        """GET /api/editions/{id} should have expected fields."""
        response = api_client.get('/api/editions/1')
        response.assert_success()

        data = response.data
        expected_fields = ['id', 'title', 'pubyear', 'work']

        for field in expected_fields:
            assert field in data, f"Edition missing field '{field}'"


class TestEditionsDelete(BaseAPITest):
    """Tests for deleting editions."""

    def test_delete_edition_without_auth_fails(self, api_client):
        """DELETE /api/editions/{id} should require authentication."""
        response = api_client.delete('/api/editions/999999')
        assert response.status_code in [401, 403, 404, 405]

    def test_delete_nonexistent_edition(self, admin_client):
        """DELETE /api/editions/{id} should handle nonexistent edition."""
        response = admin_client.delete('/api/editions/999999999')
        assert response.status_code in [400, 404, 500]
