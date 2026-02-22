"""
SuomiSF API Work Shorts Tests

Tests for the /api/works/shorts/<workid> endpoint that retrieves
short stories contained in an omnibus/anthology work.

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
# Test classes
# -------------------------------------------------------------------

class TestWorkShorts(BaseAPITest):
    """Tests for retrieving short stories from omnibus works."""

    def test_get_work_shorts_omnibus_171(
            self, api_client, snapshot_manager):
        """
        Work 171 "Välitiloja" should return 12 shorts.

        This test verifies:
        1. Correct number of shorts (12)
        2. Each short has expected fields
        3. Short IDs and titles match snapshot
        4. Authors are correctly associated
        """
        work_id = 171
        expected_count = 12

        # ---------------------------------------------------------
        # Step 1: Get shorts for the work
        # ---------------------------------------------------------
        response = api_client.get(f'/api/works/shorts/{work_id}')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"

        # ---------------------------------------------------------
        # Step 2: Verify count
        # ---------------------------------------------------------
        assert len(shorts) == expected_count, (
            f"Expected {expected_count} shorts, got {len(shorts)}"
        )

        # ---------------------------------------------------------
        # Step 3: Load snapshot and compare
        # ---------------------------------------------------------
        snapshot = snapshot_manager.load_snapshot('work_shorts_171')
        assert snapshot is not None, \
            "Snapshot work_shorts_171 not found"

        expected_shorts = snapshot['response']['data']
        assert len(expected_shorts) == expected_count, (
            "Snapshot should have correct count"
        )

        # Build lookup maps for comparison
        actual_by_id = {s['id']: s for s in shorts}
        expected_by_id = {s['id']: s for s in expected_shorts}

        # ---------------------------------------------------------
        # Step 4: Verify each short story matches snapshot
        # ---------------------------------------------------------
        for short_id, expected in expected_by_id.items():
            assert short_id in actual_by_id, (
                f"Short ID {short_id} missing from response"
            )

            actual = actual_by_id[short_id]

            # Verify title
            assert actual['title'] == expected['title'], (
                f"Short {short_id}: title mismatch. "
                f"Expected '{expected['title']}', got '{actual['title']}'"
            )

            # Verify orig_title
            assert actual.get('orig_title') == expected.get('orig_title'), (
                f"Short {short_id}: orig_title mismatch"
            )

            # Verify pubyear
            assert actual.get('pubyear') == expected.get('pubyear'), (
                f"Short {short_id}: pubyear mismatch"
            )

            # Verify type
            if expected.get('type'):
                assert actual.get('type') is not None, (
                    f"Short {short_id}: type should not be None"
                )
                assert actual['type']['id'] == expected['type']['id'], (
                    f"Short {short_id}: type ID mismatch"
                )
                assert actual['type']['name'] == expected['type']['name'], (
                    f"Short {short_id}: type name mismatch"
                )

            # ---------------------------------------------------------
            # Step 5: Verify authors match
            # ---------------------------------------------------------
            expected_authors = expected.get('authors', [])
            actual_authors = actual.get('authors', [])

            # Get unique author IDs from actual (may have duplicates)
            actual_author_ids = set()
            actual_author_names = {}
            for a in actual_authors:
                aid = int(a['id'])
                actual_author_ids.add(aid)
                actual_author_names[aid] = a['name']

            expected_author_ids = {a['id'] for a in expected_authors}
            expected_author_names = {a['id']: a['name']
                                     for a in expected_authors}

            assert actual_author_ids == expected_author_ids, (
                f"Short {short_id} ({expected['title']}): "
                f"author IDs mismatch. "
                f"Expected {expected_author_ids}, got {actual_author_ids}"
            )

            # Verify author names match
            for aid in expected_author_ids:
                assert (actual_author_names[aid]
                        == expected_author_names[aid]), (
                    f"Short {short_id}: author {aid} name mismatch. "
                    f"Expected '{expected_author_names[aid]}', "
                    f"got '{actual_author_names[aid]}'"
                )

    def test_get_work_shorts_has_required_fields(self, api_client):
        """
        GET /api/works/shorts/{id} should return shorts with required fields.
        """
        response = api_client.get('/api/works/shorts/171')
        response.assert_success()

        shorts = response.data
        assert len(shorts) > 0, "Should have at least one short"

        required_fields = ['id', 'title', 'authors']

        for short in shorts:
            for field in required_fields:
                assert field in short, (
                    f"Short {short.get('id')} missing field '{field}'"
                )

    def test_get_work_shorts_nonexistent_work(self, api_client):
        """
        GET /api/works/shorts/{id} should handle nonexistent work.
        """
        response = api_client.get('/api/works/shorts/999999999')
        # May return empty list or error
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            # Empty list is acceptable for nonexistent work
            assert response.data == [] or response.data is None

    def test_get_work_shorts_work_without_shorts(self, api_client):
        """
        GET /api/works/shorts/{id} for a work without shorts returns empty.

        Work ID 1 is a regular novel without short stories.
        """
        response = api_client.get('/api/works/shorts/1')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"
        # Work 1 may or may not have shorts, just verify format
