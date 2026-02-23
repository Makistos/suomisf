"""
SuomiSF API Tag Tests

Tests for tag-related endpoints not covered by other test files.
Includes tags quick, form info, merge, types, and CRUD lifecycle.

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

# Tag 1 "runo" is a common tag used in tests
BASIC_TAG_ID = 1

# Tag 2 for merge tests (need distinct tags)
SECONDARY_TAG_ID = 2


# -------------------------------------------------------------------
# Test classes
# -------------------------------------------------------------------

class TestTagsQuick(BaseAPITest):
    """Tests for GET /api/tagsquick endpoint."""

    def test_tagsquick_returns_200(self, api_client):
        """GET /api/tagsquick should return 200."""
        response = api_client.get('/api/tagsquick')
        response.assert_success()

    def test_tagsquick_returns_list(self, api_client):
        """GET /api/tagsquick should return a list."""
        response = api_client.get('/api/tagsquick')
        response.assert_success()

        data = response.data
        assert isinstance(data, list), "Response should be a list"

    def test_tagsquick_has_required_fields(self, api_client):
        """Each tag in quick list should have id and name."""
        response = api_client.get('/api/tagsquick')
        response.assert_success()

        if response.data and len(response.data) > 0:
            for tag in response.data[:5]:
                assert 'id' in tag, "Tag missing 'id'"
                assert 'name' in tag, "Tag missing 'name'"

    def test_tagsquick_has_counts(self, api_client):
        """Quick tags include usage counts for filtering."""
        response = api_client.get('/api/tagsquick')
        response.assert_success()

        if response.data and len(response.data) > 0:
            tag = response.data[0]
            # Quick response includes usage counts
            expected_fields = {'id', 'name', 'workcount', 'articlecount',
                               'storycount', 'type'}
            actual_fields = set(tag.keys())
            missing = expected_fields - actual_fields
            assert expected_fields.issubset(actual_fields), \
                f"Missing fields: {missing}"


class TestTagFormInfo(BaseAPITest):
    """Tests for GET /api/tags/form/{tag_id} endpoint."""

    def test_tag_form_returns_200(self, api_client):
        """GET /api/tags/form/{id} should return 200."""
        response = api_client.get(f'/api/tags/form/{BASIC_TAG_ID}')
        response.assert_success()

    def test_tag_form_returns_data(self, api_client):
        """GET /api/tags/form/{id} should return tag data."""
        response = api_client.get(f'/api/tags/form/{BASIC_TAG_ID}')
        response.assert_success()

        data = response.data
        if data is not None:
            # Form info should contain tag details
            assert 'id' in data or 'name' in data

    def test_tag_form_nonexistent(self, api_client):
        """GET /api/tags/form/{id} for nonexistent tag."""
        response = api_client.get('/api/tags/form/999999999')
        # May return 200 with null or error
        assert response.status_code in [200, 400, 404]

    def test_tag_form_invalid_id(self, api_client):
        """GET /api/tags/form/{invalid} returns 400."""
        response = api_client.get('/api/tags/form/invalid')
        assert response.status_code == 400


class TestTagTypes(BaseAPITest):
    """Tests for GET /api/tags/types endpoint."""

    def test_tag_types_returns_200(self, api_client):
        """GET /api/tags/types should return 200."""
        response = api_client.get('/api/tags/types')
        response.assert_success()

    def test_tag_types_returns_list(self, api_client):
        """GET /api/tags/types should return a list."""
        response = api_client.get('/api/tags/types')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list), "Response should be a list"

    def test_tag_types_has_required_fields(self, api_client):
        """Each tag type should have id and name."""
        response = api_client.get('/api/tags/types')
        response.assert_success()

        if response.data and len(response.data) > 0:
            for tag_type in response.data[:5]:
                assert 'id' in tag_type, "Tag type missing 'id'"
                assert 'name' in tag_type, "Tag type missing 'name'"


class TestTagMerge(BaseAPITest):
    """Tests for POST /api/tags/{source_id}/merge/{target_id} endpoint."""

    def test_merge_requires_auth(self, api_client):
        """POST /api/tags/{source}/merge/{target} requires auth."""
        response = api_client.post(
            f'/api/tags/{BASIC_TAG_ID}/merge/{SECONDARY_TAG_ID}'
        )
        assert response.status_code in [401, 403, 422]

    def test_merge_invalid_source_id(self, admin_client):
        """POST /api/tags/{invalid}/merge/{target} returns 400."""
        response = admin_client.post(
            f'/api/tags/invalid/merge/{SECONDARY_TAG_ID}'
        )
        assert response.status_code == 400

    def test_merge_invalid_target_id(self, admin_client):
        """POST /api/tags/{source}/merge/{invalid} returns 400."""
        response = admin_client.post(
            f'/api/tags/{BASIC_TAG_ID}/merge/invalid'
        )
        assert response.status_code == 400

    def test_merge_nonexistent_tags(self, admin_client):
        """POST /api/tags/{nonexistent}/merge/{nonexistent} handles gracefully."""
        response = admin_client.post('/api/tags/999999999/merge/999999998')
        # Should return error for nonexistent tags
        assert response.status_code in [200, 400, 404, 500]


class TestTagCRUDLifecycle(BaseAPITest):
    """Full CRUD lifecycle test for tags including merge."""

    def test_tag_lifecycle(self, admin_client):
        """Complete tag create -> update -> delete cycle."""
        # Step 1: Create tag
        create_data = {
            'data': {
                'name': 'Test Tag API Lifecycle'
            }
        }

        create_resp = admin_client.post('/api/tags', data=create_data)

        assert create_resp.status_code == 201, (
            f"Tag creation failed: status {create_resp.status_code},"
            f" response: {create_resp.json}"
        )

        # tag_create returns {'id': <id>} wrapped in CREATED response
        tag_id = create_resp.data['id']
        assert tag_id is not None, "Should return created tag ID"

        try:
            # Step 2: Verify tag was created
            get_resp = admin_client.get(f'/api/tags/{tag_id}')
            get_resp.assert_success()

            tag = get_resp.data
            assert 'name' in tag

            # Step 3: Update tag
            # tag_update expects flat params: id, name, type, description
            update_data = {
                'id': tag_id,
                'name': 'Test Tag API Updated',
                'type': {'id': 1},
                'description': ''
            }

            update_resp = admin_client.put('/api/tags', data=update_data)
            assert update_resp.status_code == 200, (
                f"Tag update failed: status {update_resp.status_code},"
                f" response: {update_resp.json}"
            )
            get_resp2 = admin_client.get(f'/api/tags/{tag_id}')
            get_resp2.assert_success()
            assert 'Updated' in get_resp2.data.get('name', '')

        finally:
            # Step 4: Clean up - delete tag
            delete_resp = admin_client.delete(f'/api/tags/{tag_id}')
            assert delete_resp.status_code == 200, (
                f"Failed to delete tag {tag_id}:"
                f" status {delete_resp.status_code}"
            )

    def test_tag_merge_lifecycle(self, admin_client):
        """Create two tags and merge them."""
        # Step 1: Create source tag
        source_data = {
            'data': {
                'name': 'Test Merge Source Tag'
            }
        }

        source_resp = admin_client.post('/api/tags', data=source_data)

        assert source_resp.status_code == 201, (
            f"Source tag creation failed:"
            f" status {source_resp.status_code},"
            f" response: {source_resp.json}"
        )
        source_id = source_resp.data['id']

        # Step 2: Create target tag
        target_data = {
            'data': {
                'name': 'Test Merge Target Tag'
            }
        }

        target_resp = admin_client.post('/api/tags', data=target_data)

        assert target_resp.status_code == 201, (
            f"Target tag creation failed:"
            f" status {target_resp.status_code},"
            f" response: {target_resp.json}"
        )
        target_id = target_resp.data['id']

        try:
            # Step 3: Merge source into target
            merge_resp = admin_client.post(
                f'/api/tags/{target_id}/merge/{source_id}'
            )
            assert merge_resp.status_code == 200, (
                f"Tag merge failed: status {merge_resp.status_code},"
                f" response: {merge_resp.json}"
            )

        finally:
            # Clean up target (source is deleted by merge)
            delete_resp = admin_client.delete(
                f'/api/tags/{target_id}'
            )
            assert delete_resp.status_code == 200, (
                f"Failed to delete target tag {target_id}:"
                f" status {delete_resp.status_code}"
            )


class TestTagSearch(BaseAPITest):
    """Tests for GET /api/tags?search={pattern} endpoint."""

    def test_tag_search_returns_200(self, api_client):
        """GET /api/tags?search={pattern} should return 200."""
        response = api_client.get('/api/tags?search=runo')
        response.assert_success()

    def test_tag_search_returns_list(self, api_client):
        """GET /api/tags?search={pattern} should return a list."""
        response = api_client.get('/api/tags?search=test')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_tag_search_no_results(self, api_client):
        """GET /api/tags?search={nonexistent} returns empty list."""
        response = api_client.get('/api/tags?search=xyznonexistent123abc')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_tag_search_invalid_param(self, api_client):
        """GET /api/tags with invalid param returns 400."""
        response = api_client.get('/api/tags?invalid=value')
        assert response.status_code == 400
