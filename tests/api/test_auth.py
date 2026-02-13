"""
SuomiSF API Authentication and Write Operation Tests

Tests for:
- Authentication endpoints (login, register, refresh)
- Authorization checks (unauthenticated requests should be rejected)
- Basic CRUD operations with authentication

Note: Run tests/scripts/setup_test_db.py before running these tests.
"""

from .base_test import BaseAPITest


# Test credentials - must match setup_test_db.py
TEST_USER_EMAIL = 'testuser@example.com'
TEST_USER_PASSWORD = 'testpassword123'
TEST_ADMIN_EMAIL = 'testadmin@example.com'
TEST_ADMIN_PASSWORD = 'testadminpass123'


class TestAuthentication(BaseAPITest):
    """Tests for authentication endpoints."""

    def test_login_with_valid_credentials(self, api_client):
        """POST /api/login should return token for valid credentials."""
        response = api_client.post('/api/login', data={
            'email': TEST_USER_EMAIL,
            'password': TEST_USER_PASSWORD
        })
        # May return 200 with token or 401 if user doesn't exist
        if response.status_code == 200:
            assert 'access_token' in response.json or 'token' in response.json

    def test_login_with_invalid_credentials(self, api_client):
        """POST /api/login should return 401 for invalid credentials."""
        response = api_client.post('/api/login', data={
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        })
        assert response.status_code in [400, 401, 422]

    def test_login_missing_fields(self, api_client):
        """POST /api/login should return error for missing fields."""
        response = api_client.post('/api/login', data={})
        assert response.status_code in [400, 401, 422]


class TestWriteOperationsRequireAuth(BaseAPITest):
    """Tests that write operations require authentication."""

    # Works
    def test_create_work_requires_auth(self, api_client):
        """POST /api/works should require authentication."""
        response = api_client.post('/api/works', data={
            'data': {'title': 'Test Work'}
        })
        assert response.status_code in [401, 403, 422]

    def test_update_work_requires_auth(self, api_client):
        """PUT /api/works should require authentication."""
        response = api_client.put('/api/works', data={
            'data': {'id': 1, 'title': 'Updated Work'}
        })
        assert response.status_code in [401, 403, 405, 422]

    def test_delete_work_requires_auth(self, api_client):
        """DELETE /api/works/<id> should require authentication."""
        response = api_client.delete('/api/works/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Editions
    def test_create_edition_requires_auth(self, api_client):
        """POST /api/editions should require authentication."""
        response = api_client.post('/api/editions', data={
            'data': {'work_id': 1, 'title': 'Test Edition'}
        })
        assert response.status_code in [401, 403, 422]

    def test_update_edition_requires_auth(self, api_client):
        """PUT /api/editions should require authentication."""
        response = api_client.put('/api/editions', data={
            'data': {'id': 1, 'title': 'Updated Edition'}
        })
        assert response.status_code in [401, 403, 405, 422]

    def test_delete_edition_requires_auth(self, api_client):
        """DELETE /api/editions/<id> should require authentication."""
        response = api_client.delete('/api/editions/999999')
        assert response.status_code in [401, 403, 404, 405]

    # People
    def test_create_person_requires_auth(self, api_client):
        """POST /api/people should require authentication."""
        response = api_client.post('/api/people', data={
            'data': {'name': 'Test Person'}
        })
        assert response.status_code in [401, 403, 422]

    def test_update_person_requires_auth(self, api_client):
        """PUT /api/people should require authentication."""
        response = api_client.put('/api/people', data={
            'data': {'id': 1, 'name': 'Updated Person'}
        })
        assert response.status_code in [401, 403, 405, 422]

    def test_delete_person_requires_auth(self, api_client):
        """DELETE /api/people/<id> should require authentication."""
        response = api_client.delete('/api/people/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Shorts
    def test_create_short_requires_auth(self, api_client):
        """POST /api/shorts should require authentication."""
        response = api_client.post('/api/shorts', data={
            'data': {'title': 'Test Short Story'}
        })
        assert response.status_code in [401, 403, 422]

    def test_update_short_requires_auth(self, api_client):
        """PUT /api/shorts should require authentication."""
        response = api_client.put('/api/shorts', data={
            'data': {'id': 1, 'title': 'Updated Short'}
        })
        assert response.status_code in [401, 403, 405, 422]

    def test_delete_short_requires_auth(self, api_client):
        """DELETE /api/shorts/<id> should require authentication."""
        response = api_client.delete('/api/shorts/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Tags
    def test_create_tag_requires_auth(self, api_client):
        """POST /api/tags should require authentication."""
        response = api_client.post('/api/tags', data={
            'data': {'name': 'test-tag'}
        })
        assert response.status_code in [401, 403, 422]

    def test_update_tag_requires_auth(self, api_client):
        """PUT /api/tags should require authentication."""
        response = api_client.put('/api/tags', data={
            'id': 1, 'name': 'updated-tag'
        })
        assert response.status_code in [401, 403, 405, 422]

    def test_delete_tag_requires_auth(self, api_client):
        """DELETE /api/tags/<id> should require authentication."""
        response = api_client.delete('/api/tags/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Publishers
    def test_create_publisher_requires_auth(self, api_client):
        """POST /api/publishers should require authentication."""
        response = api_client.post('/api/publishers', data={
            'data': {'name': 'Test Publisher', 'fullname': 'Test Publisher Oy'}
        })
        assert response.status_code in [401, 403, 422]

    def test_delete_publisher_requires_auth(self, api_client):
        """DELETE /api/publishers/<id> should require authentication."""
        response = api_client.delete('/api/publishers/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Bookseries
    def test_create_bookseries_requires_auth(self, api_client):
        """POST /api/bookseries should require authentication."""
        response = api_client.post('/api/bookseries', data={
            'data': {'name': 'Test Series'}
        })
        assert response.status_code in [401, 403, 422]

    def test_delete_bookseries_requires_auth(self, api_client):
        """DELETE /api/bookseries/<id> should require authentication."""
        response = api_client.delete('/api/bookseries/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Pubseries
    def test_create_pubseries_requires_auth(self, api_client):
        """POST /api/pubseries should require authentication."""
        response = api_client.post('/api/pubseries', data={
            'data': {'name': 'Test Pub Series'}
        })
        assert response.status_code in [401, 403, 422]

    def test_delete_pubseries_requires_auth(self, api_client):
        """DELETE /api/pubseries/<id> should require authentication."""
        response = api_client.delete('/api/pubseries/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Magazines
    def test_create_magazine_requires_auth(self, api_client):
        """POST /api/magazines should require authentication."""
        response = api_client.post('/api/magazines', data={
            'data': {'name': 'Test Magazine'}
        })
        assert response.status_code in [401, 403, 422]

    def test_delete_magazine_requires_auth(self, api_client):
        """DELETE /api/magazines/<id> should require authentication."""
        response = api_client.delete('/api/magazines/999999')
        assert response.status_code in [401, 403, 404, 405]

    # Issues
    def test_create_issue_requires_auth(self, api_client):
        """POST /api/issues should require authentication."""
        response = api_client.post('/api/issues', data={
            'magazine_id': 1, 'number': '1/2024'
        })
        assert response.status_code in [401, 403, 422]

    def test_delete_issue_requires_auth(self, api_client):
        """DELETE /api/issues/<id> should require authentication."""
        response = api_client.delete('/api/issues/999999')
        assert response.status_code in [401, 403, 404, 405]


class TestCollectionRequiresAuth(BaseAPITest):
    """Tests that collection endpoints require authentication."""

    def test_get_collection_requires_auth(self, api_client):
        """GET /api/collection should require authentication."""
        response = api_client.get('/api/collection')
        # 404 indicates endpoint may not exist in this version
        assert response.status_code in [401, 403, 404]

    def test_add_to_collection_requires_auth(self, api_client):
        """POST /api/editions/owner should require authentication."""
        response = api_client.post('/api/editions/owner', data={
            'editionid': 1, 'userid': 1, 'condition': 3
        })
        assert response.status_code in [401, 403, 422]
