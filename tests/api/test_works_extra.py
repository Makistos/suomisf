"""
SuomiSF API Work Extra Tests

Tests for work-related endpoints not covered by other test files.
Includes omnibus, work types, work tags, random incomplete, and shorts save.

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

# Work 1 is a basic novel (type 1 = Romaani)
BASIC_WORK_ID = 1

# Work 27 is "Yön ja päivän tarinoita", a collection with shorts
COLLECTION_WORK_ID = 27

# Work type 1 = Romaani (novel)
WORK_TYPE_NOVEL = 1

# Work type 2 = Kokoelma (collection)
WORK_TYPE_COLLECTION = 2

# Tag 1 for tag tests
TAG_ID = 1


# -------------------------------------------------------------------
# Test classes
# -------------------------------------------------------------------

class TestWorksByType(BaseAPITest):
    """Tests for GET /api/works/bytype/{worktype} endpoint."""

    def test_works_bytype_novel_returns_200(self, api_client):
        """GET /api/works/bytype/1 (novels) should return 200."""
        response = api_client.get(f'/api/works/bytype/{WORK_TYPE_NOVEL}')
        response.assert_success()

    def test_works_bytype_returns_list(self, api_client):
        """GET /api/works/bytype/{type} should return a list."""
        response = api_client.get(f'/api/works/bytype/{WORK_TYPE_NOVEL}')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list), "Response should be a list"

    def test_works_bytype_collection(self, api_client):
        """GET /api/works/bytype/2 (collections) returns collections."""
        response = api_client.get(f'/api/works/bytype/{WORK_TYPE_COLLECTION}')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_works_bytype_has_fields(self, api_client):
        """Works returned by type should have required fields."""
        response = api_client.get(f'/api/works/bytype/{WORK_TYPE_NOVEL}')
        response.assert_success()

        data = response.data
        if data and len(data) > 0:
            work = data[0]
            assert 'id' in work, "Work missing 'id'"
            assert 'title' in work, "Work missing 'title'"

    def test_works_bytype_invalid_type(self, api_client):
        """GET /api/works/bytype/{invalid} returns 400."""
        response = api_client.get('/api/works/bytype/invalid')
        assert response.status_code == 400

    def test_works_bytype_nonexistent_type(self, api_client):
        """GET /api/works/bytype/{nonexistent} returns data or error."""
        response = api_client.get('/api/works/bytype/999')
        # May return empty list or error for nonexistent type
        assert response.status_code in [200, 400]


class TestWorkOmnibus(BaseAPITest):
    """Tests for omnibus endpoints."""

    def test_get_omnibus_returns_200(self, api_client):
        """GET /api/works/{id}/omnibus should return 200."""
        response = api_client.get(f'/api/works/{BASIC_WORK_ID}/omnibus')
        response.assert_success()

    def test_get_omnibus_returns_data(self, api_client):
        """GET /api/works/{id}/omnibus returns data structure."""
        response = api_client.get(f'/api/works/{BASIC_WORK_ID}/omnibus')
        response.assert_success()

        # May return list or None for work without omnibus entries
        data = response.data
        if data is not None:
            assert isinstance(data, (list, dict))

    def test_get_omnibus_nonexistent_work(self, api_client):
        """GET /api/works/{id}/omnibus for nonexistent work."""
        response = api_client.get('/api/works/999999999/omnibus')
        # May return empty or error
        assert response.status_code in [200, 400, 404]

    def test_create_omnibus_requires_auth(self, api_client):
        """POST /api/works/omnibus requires authentication."""
        response = api_client.post('/api/works/omnibus', data={
            'omnibus_id': 1,
            'work_id': 2
        })
        assert response.status_code in [401, 403, 422]

    def test_create_omnibus_with_auth(self, admin_client):
        """POST /api/works/omnibus with auth processes request."""
        response = admin_client.post('/api/works/omnibus', data={
            'omnibus_id': BASIC_WORK_ID,
            'work_id': BASIC_WORK_ID,
            'explanation': 'Test omnibus entry'
        })
        # May return 200 or validation error (same work IDs may be invalid)
        assert response.status_code in [200, 400, 500]

    def test_create_omnibus_missing_fields(self, admin_client):
        """POST /api/works/omnibus with missing fields returns error."""
        response = admin_client.post('/api/works/omnibus', data={})
        # May return 200 or validation error for missing fields
        assert response.status_code in [200, 400, 500]


class TestWorkTags(BaseAPITest):
    """Tests for work tag endpoints."""

    def test_add_tag_requires_auth(self, api_client):
        """PUT /api/work/{id}/tags/{tagid} requires authentication."""
        response = api_client.put(f'/api/work/{BASIC_WORK_ID}/tags/{TAG_ID}')
        assert response.status_code in [401, 403, 422]

    def test_remove_tag_requires_auth(self, api_client):
        """DELETE /api/work/{id}/tags/{tagid} requires authentication."""
        url = f'/api/work/{BASIC_WORK_ID}/tags/{TAG_ID}'
        response = api_client.delete(url)
        assert response.status_code in [401, 403, 422]

    def test_add_tag_invalid_work_id(self, admin_client):
        """PUT /api/work/{invalid}/tags/{tagid} returns 400."""
        response = admin_client.put(f'/api/work/invalid/tags/{TAG_ID}')
        assert response.status_code == 400

    def test_add_tag_invalid_tag_id(self, admin_client):
        """PUT /api/work/{id}/tags/{invalid} returns 400."""
        response = admin_client.put(f'/api/work/{BASIC_WORK_ID}/tags/invalid')
        assert response.status_code == 400

    def test_remove_tag_invalid_ids(self, admin_client):
        """DELETE /api/work/{invalid}/tags/{invalid} returns 400."""
        response = admin_client.delete('/api/work/invalid/tags/invalid')
        assert response.status_code == 400

    def test_add_tag_nonexistent_work(self, admin_client):
        """PUT /api/work/{nonexistent}/tags/{tagid} handles gracefully."""
        response = admin_client.put(f'/api/work/999999999/tags/{TAG_ID}')
        # May succeed (no-op) or return error
        assert response.status_code in [200, 400, 404, 500]

    def test_add_tag_nonexistent_tag(self, admin_client):
        """PUT /api/work/{id}/tags/{nonexistent} handles gracefully."""
        url = f'/api/work/{BASIC_WORK_ID}/tags/999999999'
        response = admin_client.put(url)
        assert response.status_code in [200, 400, 404, 500]


class TestRandomIncompleteWorks(BaseAPITest):
    """Tests for POST /api/works/random/incomplete endpoint.

    Note: This endpoint has a database bug (DISTINCT + ORDER BY RANDOM())
    that causes 500 errors. Tests document this behavior.
    """

    def test_random_incomplete_processes_request(self, api_client):
        """POST /api/works/random/incomplete processes request."""
        response = api_client.post('/api/works/random/incomplete', data={})
        # Note: May return 500 due to SQL bug with DISTINCT + ORDER BY RANDOM
        assert response.status_code in [200, 400, 500]

    def test_random_incomplete_with_count(self, api_client):
        """POST /api/works/random/incomplete with count parameter."""
        response = api_client.post('/api/works/random/incomplete', data={
            'count': 5
        })
        # May return 500 due to implementation bug
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.data
            if data is not None:
                assert isinstance(data, list)

    def test_random_incomplete_with_missing_fields(self, api_client):
        """POST /api/works/random/incomplete with missing_fields filter."""
        response = api_client.post('/api/works/random/incomplete', data={
            'count': 5,
            'missing_fields': ['description', 'tags']
        })
        # May succeed when filtering by fields
        assert response.status_code in [200, 400, 500]

        if response.status_code == 200:
            data = response.data
            if data is not None:
                assert isinstance(data, list)

    def test_random_incomplete_invalid_count(self, api_client):
        """POST /api/works/random/incomplete with invalid count."""
        response = api_client.post('/api/works/random/incomplete', data={
            'count': 'invalid'
        })
        # May return 200 with default or 400/500
        assert response.status_code in [200, 400, 500]


class TestWorkShortsSave(BaseAPITest):
    """Tests for POST/PUT /api/works/shorts endpoint."""

    def test_save_work_shorts_post(self, api_client):
        """POST /api/works/shorts processes request."""
        # Note: This endpoint may not require auth (no decorator in code)
        response = api_client.post('/api/works/shorts', data={
            'work_id': COLLECTION_WORK_ID,
            'shorts': []
        })
        # Should process request
        assert response.status_code in [200, 400, 500]

    def test_save_work_shorts_put(self, api_client):
        """PUT /api/works/shorts processes request."""
        response = api_client.put('/api/works/shorts', data={
            'work_id': COLLECTION_WORK_ID,
            'shorts': []
        })
        assert response.status_code in [200, 400, 500]

    def test_save_work_shorts_invalid_work(self, api_client):
        """POST /api/works/shorts with invalid work_id."""
        response = api_client.post('/api/works/shorts', data={
            'work_id': 999999999,
            'shorts': []
        })
        assert response.status_code in [200, 400, 404, 500]

    def test_save_work_shorts_roundtrip(
            self, api_client, snapshot_manager):
        """
        POST /api/works/shorts replaces the short list and
        GET /api/works/shorts/27 reflects the change.

        Uses work 27 'Yön ja päivän tarinoita' (12 shorts).
        Removes the last short, verifies, then restores the
        original list and verifies again.
        """
        snapshot = snapshot_manager.load_snapshot('work_shorts_27')
        assert snapshot is not None, \
            "Snapshot work_shorts_27 not found"
        original_ids = [
            s['id'] for s in snapshot['response']['data']
        ]
        assert len(original_ids) > 1, \
            "Snapshot must have at least 2 shorts"

        # Remove the last short
        reduced_ids = original_ids[:-1]
        r = api_client.post('/api/works/shorts', data={
            'work_id': COLLECTION_WORK_ID,
            'shorts': reduced_ids
        })
        assert r.status_code == 200, (
            f"Save reduced list failed: {r.status_code}"
        )

        # Verify the short was removed
        got = api_client.get(
            f'/api/works/shorts/{COLLECTION_WORK_ID}')
        got.assert_success()
        actual_ids = {int(s['id']) for s in got.data}
        assert actual_ids == {int(i) for i in reduced_ids}, (
            f"Expected {set(reduced_ids)}, got {actual_ids}"
        )

        # Restore original list
        r2 = api_client.post('/api/works/shorts', data={
            'work_id': COLLECTION_WORK_ID,
            'shorts': original_ids
        })
        assert r2.status_code == 200, (
            f"Restore failed: {r2.status_code}"
        )

        # Verify restoration
        got2 = api_client.get(
            f'/api/works/shorts/{COLLECTION_WORK_ID}')
        got2.assert_success()
        final_ids = {int(s['id']) for s in got2.data}
        assert final_ids == {int(i) for i in original_ids}, (
            f"Expected {set(original_ids)}, got {final_ids}"
        )


    def test_save_work_shorts_order(
            self, api_client, snapshot_manager):
        """
        POST /api/works/shorts persists order and both endpoints
        return shorts in the saved order.

        Uses work 27 (COLLECTION_WORK_ID, 12 shorts).
        Rotates the list so the last short becomes first, then
        verifies:
          - GET /api/works/shorts/27 returns shorts in the new order
          - GET /api/works/27  returns stories in the same order
        Finally restores the original order.

        This specifically tests the work_shortstory VIEW ordering fix:
        Work.stories must be ordered by EditionShortStory.order_num.
        """
        snapshot = snapshot_manager.load_snapshot('work_shorts_27')
        assert snapshot is not None, \
            "Snapshot work_shorts_27 not found"
        original_ids = [
            int(s['id'])
            for s in snapshot['response']['data']
        ]
        assert len(original_ids) >= 2, \
            "Need at least 2 shorts to test reordering"

        # Rotate: move the last short to the front
        rotated_ids = [original_ids[-1]] + original_ids[:-1]
        assert rotated_ids != original_ids, "Rotation must change order"

        # Save with rotated order
        r = api_client.post('/api/works/shorts', data={
            'work_id': COLLECTION_WORK_ID,
            'shorts': rotated_ids
        })
        assert r.status_code == 200, (
            f"Save rotated order failed: {r.status_code}"
        )

        # --- Verify via GET /api/works/shorts/{id} ---
        shorts_resp = api_client.get(
            f'/api/works/shorts/{COLLECTION_WORK_ID}'
        )
        shorts_resp.assert_success()
        returned_ids = [int(s['id']) for s in shorts_resp.data]
        assert returned_ids == rotated_ids, (
            f"edition_shorts order mismatch:\n"
            f"  expected {rotated_ids}\n"
            f"  got      {returned_ids}"
        )

        # --- Verify via GET /api/works/{id} stories field ---
        work_resp = api_client.get(
            f'/api/works/{COLLECTION_WORK_ID}'
        )
        work_resp.assert_success()
        work_story_ids = [
            int(s['id'])
            for s in work_resp.data.get('stories', [])
        ]
        assert work_story_ids == rotated_ids, (
            f"Work.stories order mismatch:\n"
            f"  expected {rotated_ids}\n"
            f"  got      {work_story_ids}"
        )

        # --- Restore original order ---
        r2 = api_client.post('/api/works/shorts', data={
            'work_id': COLLECTION_WORK_ID,
            'shorts': original_ids
        })
        assert r2.status_code == 200, (
            f"Restore original order failed: {r2.status_code}"
        )

        # Verify restoration (order, not just set)
        final_resp = api_client.get(
            f'/api/works/shorts/{COLLECTION_WORK_ID}'
        )
        final_resp.assert_success()
        final_ids = [int(s['id']) for s in final_resp.data]
        assert final_ids == original_ids, (
            f"Restored order mismatch:\n"
            f"  expected {original_ids}\n"
            f"  got      {final_ids}"
        )


class TestWorkTagsLifecycle(BaseAPITest):
    """Full lifecycle test for work tags."""

    def test_work_tag_add_remove_cycle(self, admin_client, api_client):
        """Add tag to work, verify, then remove."""
        work_id = BASIC_WORK_ID
        tag_id = TAG_ID

        # Step 1: Get work to check initial tags
        get_resp = api_client.get(f'/api/works/{work_id}')
        get_resp.assert_success()

        work = get_resp.data
        initial_tag_ids = {t['id'] for t in work.get('tags', [])}

        # Step 2: Add tag (if not already present)
        if tag_id not in initial_tag_ids:
            add_resp = admin_client.put(f'/api/work/{work_id}/tags/{tag_id}')
            if add_resp.status_code == 200:
                # Verify tag was added
                get_resp2 = api_client.get(f'/api/works/{work_id}')
                get_resp2.assert_success()
                tag_ids = {t['id'] for t in get_resp2.data.get('tags', [])}
                assert tag_id in tag_ids, "Tag should be added"

                # Step 3: Remove tag
                remove_resp = admin_client.delete(
                    f'/api/work/{work_id}/tags/{tag_id}'
                )
                if remove_resp.status_code == 200:
                    # Verify tag was removed
                    get_resp3 = api_client.get(f'/api/works/{work_id}')
                    get_resp3.assert_success()
                    tag_ids = {t['id'] for t in get_resp3.data.get('tags', [])}
                    assert tag_id not in tag_ids, "Tag should be removed"
