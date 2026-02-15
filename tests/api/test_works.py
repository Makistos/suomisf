"""
SuomiSF API Works CRUD Tests

Tests for the complete work lifecycle:
- Count existing works
- Create a new work
- Verify creation
- Update the work
- Verify updates
- Delete the work
- Verify count returns to original

Note: Run tests/scripts/setup_test_db.py before running these tests.
"""

import pytest

from .base_test import BaseAPITest


# Test credentials - must match setup_test_db.py
TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'


# -------------------------------------------------------------------
# Reusable helper functions for work creation/deletion
# -------------------------------------------------------------------

def create_test_work(admin_client, person_id, genre_id=None,
                     title='Test Work', orig_title=None, pubyear=2025):
    """
    Create a test work via the API.

    Args:
        admin_client: Authenticated API client with admin privileges
        person_id: ID of person to use as author
        genre_id: Optional genre ID
        title: Work title
        orig_title: Original title (defaults to title)
        pubyear: Publication year

    Returns:
        int: The created work ID

    Raises:
        AssertionError: If work creation fails
    """
    work_data = {
        'data': {
            'title': title,
            'orig_title': orig_title or title,
            'pubyear': pubyear,
            'work_type': {'id': 1},  # Romaani
            'contributions': [
                {
                    'person': {'id': person_id},
                    'role': {'id': 1}  # Kirjoittaja (Author)
                }
            ],
        }
    }

    if genre_id:
        work_data['data']['genres'] = [{'id': genre_id}]

    response = admin_client.post('/api/works', data=work_data)

    assert response.status_code == 201, (
        f"Failed to create work. Status: {response.status_code}. "
        f"Response: {response.json}"
    )

    work_id = int(response.data)
    assert work_id > 0, "Should return valid work ID"

    return work_id


def delete_test_work(admin_client, work_id):
    """
    Delete a test work via the API.

    Args:
        admin_client: Authenticated API client with admin privileges
        work_id: ID of work to delete

    Returns:
        bool: True if deletion was successful

    Raises:
        AssertionError: If work deletion fails
    """
    response = admin_client.delete(f'/api/works/{work_id}')

    assert response.status_code == 200, (
        f"Failed to delete work {work_id}. Status: {response.status_code}. "
        f"Response: {response.json}"
    )

    return True


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
def existing_genre_id(app):
    """Get an existing genre ID."""
    from app import db
    from app.orm_decl import Genre

    with app.app_context():
        genre = db.session.query(Genre).first()
        return genre.id if genre else 1


@pytest.fixture
def test_work(admin_client, existing_person_id, existing_genre_id):
    """
    Create a test work and clean it up after the test.

    Yields the work ID for use in tests.
    """
    work_id = create_test_work(
        admin_client,
        existing_person_id,
        genre_id=existing_genre_id,
        title='Test Work - Fixture'
    )

    yield work_id

    # Cleanup: delete the work after test
    try:
        delete_test_work(admin_client, work_id)
    except AssertionError:
        pass  # Work may already be deleted by the test


# -------------------------------------------------------------------
# Test classes
# -------------------------------------------------------------------

class TestWorksCRUD(BaseAPITest):
    """Tests for the complete work CRUD lifecycle."""

    @pytest.fixture
    def work_count(self, app):
        """Get the current count of works in the database."""
        from app import db
        from app.orm_decl import Work

        with app.app_context():
            count = db.session.query(Work).count()
        return count

    def test_work_crud_lifecycle(self, admin_client, work_count,
                                 existing_person_id,
                                 existing_genre_id, app):
        """
        Test complete work lifecycle: create, read, update, delete.

        This test:
        1. Saves the initial work count
        2. Creates a new work with minimal required fields
        3. Verifies the work was created with correct data
        4. Updates the work with additional/changed information
        5. Verifies the updates were applied correctly
        6. Deletes the work
        7. Verifies the work count is back to the original
        """
        from app import db
        from app.orm_decl import Work

        initial_count = work_count

        # -----------------------------------------------------------
        # Step 1: Create a new work
        # -----------------------------------------------------------
        created_work_id = create_test_work(
            admin_client,
            existing_person_id,
            genre_id=existing_genre_id,
            title='Test Work Title - CRUD Test',
            orig_title='Original Test Title',
            pubyear=2025
        )

        # -----------------------------------------------------------
        # Step 2: Verify the work was created correctly
        # -----------------------------------------------------------
        get_response = admin_client.get(f'/api/works/{created_work_id}')
        get_response.assert_success()

        work_data = get_response.data
        assert work_data['id'] == created_work_id
        assert work_data['title'] == 'Test Work Title - CRUD Test'
        assert work_data['orig_title'] == 'Original Test Title'
        assert work_data['pubyear'] == 2025

        # Verify work count increased
        with app.app_context():
            new_count = db.session.query(Work).count()
        assert new_count == initial_count + 1, (
            f"Work count should have increased by 1. "
            f"Was {initial_count}, now {new_count}"
        )

        # -----------------------------------------------------------
        # Step 3: Update the work
        # -----------------------------------------------------------
        update_work_data = {
            'data': {
                'id': created_work_id,
                'title': 'Updated Test Work Title',
                'orig_title': 'Updated Original Title',
                'pubyear': 2024,
                'subtitle': 'A Test Subtitle',
                'description': 'This is a test description for the work.',
                'misc': 'Some miscellaneous notes'
            }
        }

        update_response = admin_client.put('/api/works', data=update_work_data)

        # Check update was successful
        assert update_response.status_code == 200, (
            f"Expected 200 OK, got {update_response.status_code}. "
            f"Response: {update_response.json}"
        )

        # -----------------------------------------------------------
        # Step 4: Verify the updates were applied
        # -----------------------------------------------------------
        verify_response = admin_client.get(f'/api/works/{created_work_id}')
        verify_response.assert_success()

        updated_data = verify_response.data
        assert updated_data['id'] == created_work_id
        assert updated_data['title'] == 'Updated Test Work Title', \
            f"Title not updated. Got: {updated_data['title']}"
        assert updated_data['orig_title'] == 'Updated Original Title', \
            f"Orig title not updated. Got: {updated_data['orig_title']}"
        assert updated_data['pubyear'] == 2024, \
            f"Pubyear not updated. Got: {updated_data['pubyear']}"
        assert updated_data['subtitle'] == 'A Test Subtitle', \
            f"Subtitle not updated. Got: {updated_data.get('subtitle')}"
        expected_desc = 'This is a test description for the work.'
        assert updated_data['description'] == expected_desc, (
            f"Description not updated. Got: {updated_data.get('description')}"
        )
        assert updated_data['misc'] == 'Some miscellaneous notes', \
            f"Misc not updated. Got: {updated_data.get('misc')}"

        # -----------------------------------------------------------
        # Step 5: Delete the work
        # -----------------------------------------------------------
        delete_test_work(admin_client, created_work_id)

        # -----------------------------------------------------------
        # Step 6: Verify the work is deleted and count is restored
        # -----------------------------------------------------------
        # Try to get the deleted work - should fail
        deleted_resp = admin_client.get(f'/api/works/{created_work_id}')
        assert deleted_resp.status_code in [400, 404], (
            f"Expected 400 or 404 for deleted work, "
            f"got {deleted_resp.status_code}"
        )

        # Verify work count is back to original
        with app.app_context():
            final_count = db.session.query(Work).count()
        assert final_count == initial_count, (
            f"Work count should be back to {initial_count}, "
            f"but is {final_count}"
        )


class TestWorksCreateValidation(BaseAPITest):
    """Tests for work creation validation."""

    def test_create_work_without_title_fails(self, admin_client):
        """POST /api/works should fail without title."""
        work_data = {
            'data': {
                'title': '',
                'contributions': [
                    {'person': {'id': 1}, 'role': {'id': 1}}
                ]
            }
        }

        response = admin_client.post('/api/works', data=work_data)
        assert response.status_code == 400, \
            f"Expected 400 Bad Request, got {response.status_code}"

    def test_create_work_without_author_fails(self, admin_client):
        """POST /api/works should fail without author/editor."""
        work_data = {
            'data': {
                'title': 'Test Work Without Author',
                'contributions': []
            }
        }

        response = admin_client.post('/api/works', data=work_data)
        assert response.status_code == 400, \
            f"Expected 400 Bad Request, got {response.status_code}"

    def test_create_work_without_auth_fails(self, api_client):
        """POST /api/works should require authentication."""
        work_data = {
            'data': {
                'title': 'Test Work',
                'contributions': [
                    {'person': {'id': 1}, 'role': {'id': 1}}
                ]
            }
        }

        response = api_client.post('/api/works', data=work_data)
        assert response.status_code in [401, 403, 422], \
            f"Expected 401/403/422, got {response.status_code}"


class TestWorksRead(BaseAPITest):
    """Tests for reading works."""

    def test_get_existing_work(self, api_client):
        """GET /api/works/{id} should return work data for valid ID."""
        response = api_client.get('/api/works/1')
        response.assert_success()

        data = response.data
        assert 'id' in data
        assert 'title' in data
        assert data['id'] == 1

    def test_get_nonexistent_work(self, api_client):
        """GET /api/works/{id} should return error for invalid ID."""
        response = api_client.get('/api/works/999999999')
        assert response.status_code in [400, 404]

    def test_get_work_has_expected_fields(self, api_client):
        """GET /api/works/{id} should return work with expected fields."""
        response = api_client.get('/api/works/1')
        response.assert_success()

        data = response.data
        expected_fields = ['id', 'title', 'orig_title', 'pubyear',
                           'editions', 'contributions']

        for field in expected_fields:
            assert field in data, f"Work missing field '{field}'"


class TestWorksDelete(BaseAPITest):
    """Tests for deleting works."""

    def test_delete_work_without_auth_fails(self, api_client):
        """DELETE /api/works/{id} should require authentication."""
        response = api_client.delete('/api/works/999999')
        assert response.status_code in [401, 403, 404, 405]

    def test_delete_nonexistent_work(self, admin_client):
        """DELETE /api/works/{id} should handle nonexistent work."""
        response = admin_client.delete('/api/works/999999999')
        # Could be 400 (bad request), 404 (not found), or 500
        assert response.status_code in [400, 404, 500]
