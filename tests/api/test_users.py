"""
SuomiSF API User Tests

Tests for user endpoints including user stats/genres.

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


@pytest.fixture
def valid_user_id(api_client):
    """Get a valid user ID from the users list."""
    response = api_client.get('/api/users')
    if response.status_code == 200 and response.data:
        return response.data[0]['id']
    pytest.skip('No users found in database')


# -------------------------------------------------------------------
# User List Tests
# -------------------------------------------------------------------

class TestUserList(BaseAPITest):
    """Tests for GET /api/users endpoint."""

    def test_users_list_returns_200(self, api_client):
        """GET /api/users should return 200."""
        response = api_client.get('/api/users')
        response.assert_success()

    def test_users_list_returns_list(self, api_client):
        """GET /api/users returns list format."""
        response = api_client.get('/api/users')
        response.assert_success()

        data = response.data
        assert isinstance(data, list), \
            "Response should be a list"

    def test_users_list_has_required_fields(self, api_client):
        """Users in list have required fields."""
        response = api_client.get('/api/users')
        response.assert_success()

        if response.data and len(response.data) > 0:
            user = response.data[0]
            assert 'id' in user, "User missing 'id'"
            assert 'name' in user, "User missing 'name'"


# -------------------------------------------------------------------
# User Get Tests
# -------------------------------------------------------------------

class TestUserGet(BaseAPITest):
    """Tests for GET /api/users/{id} endpoint."""

    def test_user_get_returns_200(
            self, api_client, valid_user_id):
        """GET /api/users/{id} should return 200."""
        response = api_client.get(
            f'/api/users/{valid_user_id}')
        response.assert_success()

    def test_user_get_has_fields(
            self, api_client, valid_user_id):
        """User response has required fields."""
        response = api_client.get(
            f'/api/users/{valid_user_id}')
        response.assert_success()

        data = response.data
        assert 'id' in data, "User missing 'id'"
        assert 'name' in data, "User missing 'name'"

    def test_user_get_nonexistent(self, api_client):
        """GET /api/users/{nonexistent} returns error."""
        response = api_client.get('/api/users/999999999')
        assert response.status_code == 500

    def test_user_get_invalid_id(self, api_client):
        """GET /api/users/{invalid} returns 400."""
        response = api_client.get('/api/users/invalid')
        assert response.status_code == 400


# -------------------------------------------------------------------
# User Stats Genres Tests
# -------------------------------------------------------------------

class TestUserStatsGenres(BaseAPITest):
    """Tests for GET /api/users/{id}/stats/genres endpoint.

    Returns genre counts for books owned by the user.
    Each genre entry has: id, name, abbr, count.
    """

    def test_user_genres_returns_200(
            self, api_client, valid_user_id):
        """GET /api/users/{id}/stats/genres returns 200."""
        url = f'/api/users/{valid_user_id}/stats/genres'
        response = api_client.get(url)
        response.assert_success()

    def test_user_genres_returns_list(
            self, api_client, valid_user_id):
        """GET /api/users/{id}/stats/genres returns list."""
        url = f'/api/users/{valid_user_id}/stats/genres'
        response = api_client.get(url)
        response.assert_success()

        data = response.data
        assert isinstance(data, list), \
            "Response should be a list"

    def test_user_genres_item_has_fields(
            self, api_client, valid_user_id):
        """Genre items have required fields."""
        url = f'/api/users/{valid_user_id}/stats/genres'
        response = api_client.get(url)
        response.assert_success()

        if response.data and len(response.data) > 0:
            genre = response.data[0]
            assert 'id' in genre, \
                "Genre missing 'id'"
            assert 'name' in genre, \
                "Genre missing 'name'"
            assert 'abbr' in genre, \
                "Genre missing 'abbr'"
            assert 'count' in genre, \
                "Genre missing 'count'"

    def test_user_genres_count_is_positive(
            self, api_client, valid_user_id):
        """Genre counts should be positive integers."""
        url = f'/api/users/{valid_user_id}/stats/genres'
        response = api_client.get(url)
        response.assert_success()

        if response.data and len(response.data) > 0:
            for genre in response.data:
                assert isinstance(genre['count'], int), \
                    "Count should be an integer"
                assert genre['count'] > 0, \
                    "Count should be positive"

    def test_user_genres_nonexistent_user(
            self, api_client):
        """GET genres for non-existent user returns
        200 with empty list."""
        url = '/api/users/999999999/stats/genres'
        response = api_client.get(url)
        response.assert_success()

        data = response.data
        assert isinstance(data, list), \
            "Response should be a list"
        assert len(data) == 0, \
            "Non-existent user should have no genres"

    def test_user_genres_invalid_id(self, api_client):
        """GET genres with invalid user ID returns 500."""
        url = '/api/users/invalid/stats/genres'
        response = api_client.get(url)
        assert response.status_code == 500
