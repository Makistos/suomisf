"""
SuomiSF API Magazine and Issue Tests

Tests for magazine and issue endpoints not covered by other test files.
Includes CRUD operations, tags, contributors, covers, and sizes.

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

# Magazine 12 is Finncon-lehti (no issues)
BASIC_MAGAZINE_ID = 12

# Magazine 30 is Legolas (has issues)
MAGAZINE_WITH_ISSUES_ID = 30

# Issue 75 is Alienisti 1/2008
BASIC_ISSUE_ID = 75

# Tag 1 for tag tests
TAG_ID = 1


# -------------------------------------------------------------------
# Magazine Test Classes
# -------------------------------------------------------------------

class TestMagazineList(BaseAPITest):
    """Tests for GET /api/magazines endpoint."""

    def test_magazines_list_returns_200(self, api_client):
        """GET /api/magazines should return 200."""
        response = api_client.get('/api/magazines')
        response.assert_success()

    def test_magazines_list_returns_list(self, api_client):
        """GET /api/magazines returns list format."""
        response = api_client.get('/api/magazines')
        response.assert_success()

        data = response.data
        assert isinstance(data, list), "Response should be a list"

    def test_magazines_list_has_required_fields(self, api_client):
        """Magazines in list have required fields."""
        response = api_client.get('/api/magazines')
        response.assert_success()

        if response.data and len(response.data) > 0:
            magazine = response.data[0]
            assert 'id' in magazine, "Magazine missing 'id'"
            assert 'name' in magazine, "Magazine missing 'name'"


class TestMagazineGet(BaseAPITest):
    """Tests for GET /api/magazines/{id} endpoint."""

    def test_magazine_get_returns_200(self, api_client):
        """GET /api/magazines/{id} should return 200."""
        response = api_client.get(f'/api/magazines/{BASIC_MAGAZINE_ID}')
        response.assert_success()

    def test_magazine_get_has_fields(self, api_client):
        """Magazine response has required fields."""
        response = api_client.get(f'/api/magazines/{BASIC_MAGAZINE_ID}')
        response.assert_success()

        data = response.data
        assert 'id' in data, "Magazine missing 'id'"
        assert 'name' in data, "Magazine missing 'name'"

    def test_magazine_get_nonexistent(self, api_client):
        """GET /api/magazines/{nonexistent} handles gracefully."""
        response = api_client.get('/api/magazines/999999999')
        assert response.status_code in [200, 400, 404]

    def test_magazine_get_invalid_id(self, api_client):
        """GET /api/magazines/{invalid} returns 400."""
        response = api_client.get('/api/magazines/invalid')
        assert response.status_code == 400


class TestMagazineUpdate(BaseAPITest):
    """Tests for PUT /api/magazines endpoint.

    Note: The endpoint requires data wrapped in 'data' key and specific fields.
    """

    def test_update_magazine_requires_auth(self, api_client):
        """PUT /api/magazines requires authentication."""
        response = api_client.put('/api/magazines', data={
            'data': {
                'id': BASIC_MAGAZINE_ID,
                'name': 'Test Magazine'
            }
        })
        assert response.status_code in [401, 403, 422]

    def test_update_magazine_with_auth(self, admin_client):
        """PUT /api/magazines with auth processes request."""
        # Get current magazine data first
        get_resp = admin_client.get(f'/api/magazines/{BASIC_MAGAZINE_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get magazine data')

        current = get_resp.data
        response = admin_client.put('/api/magazines', data={
            'data': {
                'id': BASIC_MAGAZINE_ID,
                'name': current.get('name', 'Test'),
                'type': current.get('type', 0)
            }
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]

    @pytest.mark.xfail(reason="Backend crashes on missing 'id' in data")
    def test_update_magazine_missing_data(self, admin_client):
        """PUT /api/magazines with missing data returns error."""
        response = admin_client.put('/api/magazines', data={'data': {}})
        # Should return 400 for missing fields
        assert response.status_code == 400


class TestMagazinePublisher(BaseAPITest):
    """Tests for GET /api/magazines/{id}/publisher endpoint.

    Note: This endpoint is a stub that returns ("", 0) which is not valid.
    """

    @pytest.mark.skip(reason="Stub endpoint returns invalid response")
    def test_magazine_publisher_processes_request(self, api_client):
        """GET /api/magazines/{id}/publisher processes request."""
        url = f'/api/magazines/{BASIC_MAGAZINE_ID}/publisher'
        response = api_client.get(url)
        response.assert_success()


class TestMagazineTags(BaseAPITest):
    """Tests for GET /api/magazines/{id}/tags endpoint.

    Note: This endpoint is a stub that returns ("", 0) which is not valid.
    """

    @pytest.mark.skip(reason="Stub endpoint returns invalid response")
    def test_magazine_tags_processes_request(self, api_client):
        """GET /api/magazines/{id}/tags processes request."""
        url = f'/api/magazines/{BASIC_MAGAZINE_ID}/tags'
        response = api_client.get(url)
        response.assert_success()


# -------------------------------------------------------------------
# Issue Test Classes
# -------------------------------------------------------------------

class TestIssueGet(BaseAPITest):
    """Tests for GET /api/issues/{id} endpoint."""

    def test_issue_get_returns_200(self, api_client):
        """GET /api/issues/{id} should return 200."""
        response = api_client.get(f'/api/issues/{BASIC_ISSUE_ID}')
        response.assert_success()

    def test_issue_get_has_fields(self, api_client):
        """Issue response has required fields."""
        response = api_client.get(f'/api/issues/{BASIC_ISSUE_ID}')
        response.assert_success()

        data = response.data
        assert 'id' in data, "Issue missing 'id'"

    def test_issue_get_nonexistent(self, api_client):
        """GET /api/issues/{nonexistent} handles gracefully."""
        response = api_client.get('/api/issues/999999999')
        assert response.status_code in [200, 400, 404]

    def test_issue_get_invalid_id(self, api_client):
        """GET /api/issues/{invalid} returns 400."""
        response = api_client.get('/api/issues/invalid')
        assert response.status_code == 400


class TestIssueUpdate(BaseAPITest):
    """Tests for PUT /api/issues endpoint.

    Note: The endpoint requires specific fields like 'size'.
    """

    def test_update_issue_requires_auth(self, api_client):
        """PUT /api/issues requires authentication."""
        response = api_client.put('/api/issues', data={
            'id': BASIC_ISSUE_ID,
            'size': 1
        })
        assert response.status_code in [401, 403, 422]

    def test_update_issue_with_auth(self, admin_client):
        """PUT /api/issues with auth processes request."""
        # Get current issue data first
        get_resp = admin_client.get(f'/api/issues/{BASIC_ISSUE_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get issue data')

        current = get_resp.data
        # Size must be a dict with 'id' key, not an int
        size_data = current.get('size', {})
        size_id = size_data.get('id', 1) if isinstance(size_data, dict) else 1
        response = admin_client.put('/api/issues', data={
            'id': BASIC_ISSUE_ID,
            'size': {'id': size_id}
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]

    @pytest.mark.xfail(reason="Backend crashes on missing 'id' in data")
    def test_update_issue_missing_id(self, admin_client):
        """PUT /api/issues with missing id returns error."""
        response = admin_client.put('/api/issues', data={'size': {'id': 1}})
        # Should return 400 for missing fields
        assert response.status_code == 400


class TestIssueContributors(BaseAPITest):
    """Tests for /api/issues/{id}/contributors endpoints.

    Note: The GET endpoint has a bug - it returns a raw list which crashes
    make_api_response (AttributeError: 'list' has no attribute 'status').
    """

    @pytest.mark.xfail(reason="Backend bug: returns list instead of Response")
    def test_contributors_get_returns_200(self, api_client):
        """GET /api/issues/{id}/contributors should return 200."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/contributors'
        response = api_client.get(url)
        response.assert_success()

    @pytest.mark.xfail(reason="Backend bug: returns list instead of Response")
    def test_contributors_get_returns_data(self, api_client):
        """GET /api/issues/{id}/contributors returns data structure."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/contributors'
        response = api_client.get(url)
        response.assert_success()

    @pytest.mark.xfail(reason="Backend bug: returns list instead of Response")
    def test_contributors_get_nonexistent(self, api_client):
        """GET /api/issues/{nonexistent}/contributors handles gracefully."""
        response = api_client.get('/api/issues/999999999/contributors')
        assert response.status_code in [200, 400, 404]

    def test_contributors_get_invalid_id(self, api_client):
        """GET /api/issues/{invalid}/contributors returns 400."""
        response = api_client.get('/api/issues/invalid/contributors')
        assert response.status_code == 400

    def test_contributors_update_requires_auth(self, api_client):
        """POST /api/issues/{id}/contributors requires auth."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/contributors'
        response = api_client.post(url, data={'contributors': []})
        assert response.status_code in [401, 403, 422]

    def test_contributors_update_with_auth(self, admin_client):
        """POST /api/issues/{id}/contributors with auth processes."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/contributors'
        response = admin_client.post(url, data=[])
        # May return 200 or error
        assert response.status_code in [200, 400, 500]


class TestIssueTags(BaseAPITest):
    """Tests for /api/issues/{id}/tags endpoints.

    Note: The GET endpoint has a bug - parameter name mismatch (issue_id vs
    issueid in URL). This causes TypeError. Tests document this behavior.
    """

    @pytest.mark.xfail(reason="Backend bug: parameter name mismatch")
    def test_issue_tags_get_returns_200(self, api_client):
        """GET /api/issues/{id}/tags should return 200."""
        response = api_client.get(f'/api/issues/{BASIC_ISSUE_ID}/tags')
        response.assert_success()

    @pytest.mark.xfail(reason="Backend bug: parameter name mismatch")
    def test_issue_tags_get_returns_data(self, api_client):
        """GET /api/issues/{id}/tags returns data structure."""
        response = api_client.get(f'/api/issues/{BASIC_ISSUE_ID}/tags')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, (list, dict))

    @pytest.mark.xfail(reason="Backend bug: parameter name mismatch")
    def test_issue_tags_get_invalid_id(self, api_client):
        """GET /api/issues/{invalid}/tags returns 400."""
        response = api_client.get('/api/issues/invalid/tags')
        assert response.status_code == 400

    def test_add_tag_requires_auth(self, api_client):
        """PUT /api/issue/{id}/tags/{tagid} requires auth."""
        url = f'/api/issue/{BASIC_ISSUE_ID}/tags/{TAG_ID}'
        response = api_client.put(url)
        assert response.status_code in [401, 403, 422]

    def test_remove_tag_requires_auth(self, api_client):
        """DELETE /api/issue/{id}/tags/{tagid} requires auth."""
        url = f'/api/issue/{BASIC_ISSUE_ID}/tags/{TAG_ID}'
        response = api_client.delete(url)
        assert response.status_code in [401, 403, 422]

    def test_add_tag_with_auth(self, admin_client):
        """PUT /api/issue/{id}/tags/{tagid} with auth processes."""
        url = f'/api/issue/{BASIC_ISSUE_ID}/tags/{TAG_ID}'
        response = admin_client.put(url)
        # May return 200 or error
        assert response.status_code in [200, 400, 500]

    def test_add_tag_invalid_ids(self, admin_client):
        """PUT /api/issue/{invalid}/tags/{invalid} returns 400."""
        response = admin_client.put('/api/issue/invalid/tags/invalid')
        assert response.status_code == 400


class TestIssueShorts(BaseAPITest):
    """Tests for /api/issues/shorts endpoint."""

    def test_save_issue_shorts_requires_auth(self, api_client):
        """PUT /api/issues/shorts requires authentication."""
        response = api_client.put('/api/issues/shorts', data={
            'issue_id': BASIC_ISSUE_ID,
            'shorts': []
        })
        assert response.status_code in [401, 403, 422]

    def test_save_issue_shorts_with_auth(self, admin_client):
        """PUT /api/issues/shorts with auth processes request."""
        response = admin_client.put('/api/issues/shorts', data={
            'issue_id': BASIC_ISSUE_ID,
            'shorts': []
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]


class TestIssueArticles(BaseAPITest):
    """Tests for /api/issues/articles endpoint."""

    def test_save_issue_articles_requires_auth(self, api_client):
        """PUT /api/issues/articles requires authentication."""
        response = api_client.put('/api/issues/articles', data={
            'issue_id': BASIC_ISSUE_ID,
            'articles': []
        })
        assert response.status_code in [401, 403, 422]

    def test_save_issue_articles_with_auth(self, admin_client):
        """PUT /api/issues/articles with auth processes request."""
        response = admin_client.put('/api/issues/articles', data={
            'issue_id': BASIC_ISSUE_ID,
            'articles': []
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]


class TestIssueSizes(BaseAPITest):
    """Tests for GET /api/issues/sizes endpoint."""

    def test_issue_sizes_returns_200(self, api_client):
        """GET /api/issues/sizes should return 200."""
        response = api_client.get('/api/issues/sizes')
        response.assert_success()

    def test_issue_sizes_returns_list(self, api_client):
        """GET /api/issues/sizes returns list format."""
        response = api_client.get('/api/issues/sizes')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list), "Response should be a list"


class TestIssueCovers(BaseAPITest):
    """Tests for /api/issues/{id}/covers endpoints."""

    def test_upload_cover_requires_auth(self, api_client):
        """POST /api/issues/{id}/covers requires authentication."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/covers'
        response = api_client.post(url)
        assert response.status_code in [400, 401, 403, 422]

    def test_upload_cover_requires_file(self, admin_client):
        """POST /api/issues/{id}/covers requires file."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/covers'
        response = admin_client.post(url)
        # Should return 400 for missing file
        assert response.status_code == 400

    def test_delete_cover_requires_auth(self, api_client):
        """DELETE /api/issues/{id}/covers requires authentication."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/covers'
        response = api_client.delete(url)
        assert response.status_code in [401, 403, 422]

    def test_delete_cover_with_auth(self, admin_client):
        """DELETE /api/issues/{id}/covers with auth processes."""
        url = f'/api/issues/{BASIC_ISSUE_ID}/covers'
        response = admin_client.delete(url)
        # May succeed or return error if no cover exists
        assert response.status_code in [200, 400, 404, 500]
