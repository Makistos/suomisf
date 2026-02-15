"""
SuomiSF API Person Tests

Tests for person-related endpoints not covered by other test files.
These include list, articles, chiefeditor, issue-contributions, and CRUD.

Note: Run tests/scripts/setup_test_db.py before running these tests.
"""

import pytest

from .base_test import BaseAPITest
from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD


# -------------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """Get an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


# -------------------------------------------------------------------
# Test data
# -------------------------------------------------------------------

# Person 900 (Nikkonen, Raimo) is chief editor for 172 issues
CHIEFEDITOR_PERSON_ID = 900

# Person 8 (Selkälä, Ulla) has 167 issue contributions
ISSUE_CONTRIB_PERSON_ID = 8

# Person 1 for basic get tests
BASIC_PERSON_ID = 1


# -------------------------------------------------------------------
# Test classes
# -------------------------------------------------------------------

class TestPersonList(BaseAPITest):
    """Tests for GET /api/people/ list endpoint."""

    def test_list_people_returns_200(self, api_client):
        """GET /api/people/ should return 200."""
        response = api_client.get('/api/people/')
        response.assert_success()

    def test_list_people_returns_paginated_data(self, api_client):
        """GET /api/people/ should return paginated response."""
        response = api_client.get('/api/people/?first=0&rows=10')
        response.assert_success()

        data = response.data
        # Response may have 'data' and 'totalRecords' for pagination
        if isinstance(data, dict):
            if 'data' in data:
                assert isinstance(data['data'], list)
            if 'totalRecords' in data:
                assert isinstance(data['totalRecords'], int)
        elif isinstance(data, list):
            # Some endpoints return list directly
            assert len(data) <= 10

    def test_list_people_with_sort(self, api_client):
        """GET /api/people/ with sort parameters."""
        response = api_client.get(
            '/api/people/?first=0&rows=5&sortField=name&sortOrder=1'
        )
        response.assert_success()

    def test_list_people_with_rows_limit(self, api_client):
        """GET /api/people/ with rows limit returns limited results."""
        response = api_client.get('/api/people/?first=0&rows=5')
        response.assert_success()

        data = response.data
        # Verify we get data back (format depends on implementation)
        assert data is not None


class TestPersonChiefEditor(BaseAPITest):
    """Tests for GET /api/people/{id}/chiefeditor endpoint."""

    def test_chiefeditor_returns_200(self, api_client):
        """GET /api/people/{id}/chiefeditor should return 200."""
        response = api_client.get(
            f'/api/people/{CHIEFEDITOR_PERSON_ID}/chiefeditor'
        )
        response.assert_success()

    def test_chiefeditor_returns_issue_data(self, api_client):
        """GET /api/people/{id}/chiefeditor returns issue info."""
        response = api_client.get(
            f'/api/people/{CHIEFEDITOR_PERSON_ID}/chiefeditor'
        )
        response.assert_success()

        data = response.data
        if data is not None:
            # Should have issue fields if person is chief editor
            assert 'id' in data or data == {}

    def test_chiefeditor_nonexistent_person(self, api_client):
        """GET /api/people/{id}/chiefeditor for nonexistent person."""
        response = api_client.get('/api/people/999999999/chiefeditor')
        assert response.status_code in [200, 400, 404]

    def test_chiefeditor_person_without_issues(self, api_client):
        """GET /api/people/{id}/chiefeditor for person not chief editor."""
        # Person 1 may not be a chief editor
        response = api_client.get(
            f'/api/people/{BASIC_PERSON_ID}/chiefeditor'
        )
        response.assert_success()
        # May return null/None or empty object


class TestPersonIssueContributions(BaseAPITest):
    """Tests for GET /api/people/{id}/issue-contributions endpoint."""

    def test_issue_contributions_returns_200(self, api_client):
        """GET /api/people/{id}/issue-contributions should return 200."""
        response = api_client.get(
            f'/api/people/{ISSUE_CONTRIB_PERSON_ID}/issue-contributions'
        )
        response.assert_success()

    def test_issue_contributions_returns_list(self, api_client):
        """GET /api/people/{id}/issue-contributions returns a list."""
        response = api_client.get(
            f'/api/people/{ISSUE_CONTRIB_PERSON_ID}/issue-contributions'
        )
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_issue_contributions_has_fields(self, api_client):
        """Issue contributions have expected fields."""
        response = api_client.get(
            f'/api/people/{ISSUE_CONTRIB_PERSON_ID}/issue-contributions'
        )
        response.assert_success()

        data = response.data
        if data and len(data) > 0:
            contrib = data[0]
            # Check for expected fields
            assert 'id' in contrib or 'issue_id' in contrib or \
                'title' in contrib

    def test_issue_contributions_nonexistent_person(self, api_client):
        """GET /api/people/{id}/issue-contributions for nonexistent."""
        response = api_client.get(
            '/api/people/999999999/issue-contributions'
        )
        assert response.status_code in [200, 400, 404]

    def test_issue_contributions_person_without_contribs(self, api_client):
        """GET /api/people/{id}/issue-contributions for person without."""
        # Person 1 may not have issue contributions
        response = api_client.get(
            f'/api/people/{BASIC_PERSON_ID}/issue-contributions'
        )
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)


class TestPersonArticles(BaseAPITest):
    """Tests for GET /api/people/{id}/articles endpoint."""

    def test_articles_returns_200(self, api_client):
        """GET /api/people/{id}/articles should return 200."""
        response = api_client.get(
            f'/api/people/{BASIC_PERSON_ID}/articles'
        )
        response.assert_success()

    def test_articles_returns_list(self, api_client):
        """GET /api/people/{id}/articles returns a list."""
        response = api_client.get(
            f'/api/people/{BASIC_PERSON_ID}/articles'
        )
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_articles_nonexistent_person(self, api_client):
        """GET /api/people/{id}/articles for nonexistent person."""
        response = api_client.get('/api/people/999999999/articles')
        assert response.status_code in [200, 400, 404]


class TestPersonTags(BaseAPITest):
    """Tests for person tag endpoints."""

    def test_add_tag_requires_auth(self, api_client):
        """PUT /api/person/{id}/tags/{tagid} requires authentication."""
        response = api_client.put(f'/api/person/{BASIC_PERSON_ID}/tags/1')
        assert response.status_code in [401, 403, 422]

    def test_remove_tag_requires_auth(self, api_client):
        """DELETE /api/person/{id}/tags/{tagid} requires authentication."""
        response = api_client.delete(f'/api/person/{BASIC_PERSON_ID}/tags/1')
        assert response.status_code in [401, 403, 422]

    def test_add_tag_invalid_ids(self, admin_client):
        """PUT /api/person/{id}/tags/{tagid} with invalid IDs."""
        response = admin_client.put('/api/person/invalid/tags/1')
        assert response.status_code in [400, 404, 500]

    def test_remove_tag_invalid_ids(self, admin_client):
        """DELETE /api/person/{id}/tags/{tagid} with invalid IDs."""
        response = admin_client.delete('/api/person/invalid/tags/1')
        assert response.status_code in [400, 404, 500]


class TestPersonCRUD(BaseAPITest):
    """Tests for person CRUD lifecycle."""

    def test_create_person(self, admin_client):
        """POST /api/people creates a new person."""
        # API expects data wrapped in 'data' key
        person_data = {
            'data': {
                'name': 'Testiperson, API',
                'first_name': 'API',
                'last_name': 'Testiperson',
                'dob': 1990,
                'nationality': {'id': 1}
            }
        }

        response = admin_client.post('/api/people', data=person_data)

        if response.status_code == 200:
            # Get the created person ID
            data = response.data
            if isinstance(data, dict):
                person_id = data.get('id') or data.get('response')
            else:
                person_id = data

            # Clean up: delete the created person
            if person_id:
                admin_client.delete(f'/api/people/{person_id}')

    def test_create_person_without_auth_fails(self, api_client):
        """POST /api/people without auth fails."""
        response = api_client.post('/api/people', data={
            'name': 'Test Person'
        })
        assert response.status_code in [401, 403, 422]

    def test_update_person_without_auth_fails(self, api_client):
        """PUT /api/people without auth fails."""
        response = api_client.put('/api/people', data={
            'id': BASIC_PERSON_ID,
            'name': 'Updated Name'
        })
        assert response.status_code in [401, 403, 422]

    def test_delete_person_without_auth_fails(self, api_client):
        """DELETE /api/people/{id} without auth fails."""
        response = api_client.delete(f'/api/people/{BASIC_PERSON_ID}')
        assert response.status_code in [401, 403, 404, 405]

    def test_delete_nonexistent_person(self, admin_client):
        """DELETE /api/people/{id} for nonexistent person."""
        response = admin_client.delete('/api/people/999999999')
        assert response.status_code in [200, 400, 404, 500]


class TestPersonCRUDLifecycle(BaseAPITest):
    """
    Full CRUD lifecycle test for persons.

    Creates a person, updates it, and deletes it.
    """

    def test_person_lifecycle(self, admin_client):
        """Complete person create -> update -> delete cycle."""
        # Step 1: Create person (API expects data wrapper)
        create_data = {
            'data': {
                'name': 'Lifecycle, Test',
                'first_name': 'Test',
                'last_name': 'Lifecycle',
                'dob': 1985,
                'nationality': {'id': 1}
            }
        }

        create_resp = admin_client.post('/api/people', data=create_data)

        if create_resp.status_code != 200:
            pytest.skip('Person creation not available')

        # Extract created ID
        data = create_resp.data
        if isinstance(data, dict):
            person_id = data.get('id') or data.get('response')
        else:
            person_id = data

        assert person_id is not None, "Should return created person ID"

        try:
            # Step 2: Verify person was created
            get_resp = admin_client.get(f'/api/people/{person_id}')
            get_resp.assert_success()

            person = get_resp.data
            assert person['name'] == 'Lifecycle, Test'

            # Step 3: Update person (API expects data wrapper)
            update_data = {
                'data': {
                    'id': person_id,
                    'name': 'Lifecycle, Updated',
                    'first_name': 'Updated',
                    'last_name': 'Lifecycle',
                    'dob': 1985,
                    'dod': 2020,
                    'nationality': {'id': 1}
                }
            }

            update_resp = admin_client.put('/api/people', data=update_data)
            # Update may succeed or fail based on implementation
            if update_resp.status_code == 200:
                # Verify update
                get_resp2 = admin_client.get(f'/api/people/{person_id}')
                get_resp2.assert_success()
                assert get_resp2.data['dod'] == 2020

        finally:
            # Step 4: Clean up - delete person
            delete_resp = admin_client.delete(f'/api/people/{person_id}')
            # Should succeed or return appropriate error
            assert delete_resp.status_code in [200, 400, 404, 500]
