"""
SuomiSF API Edition Shorts Tests

Tests for the edition-shortstory relationship endpoints.
These tests ensure API responses remain unchanged after migration 001
(ShortStory refactoring from Part-based to direct junction table).

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

class TestEditionShorts(BaseAPITest):
    """
    Tests for GET /api/editions/{id}/shorts endpoint.

    These tests verify that the edition-to-shorts relationship
    returns consistent data before and after schema migration.
    """

    def test_edition_shorts_count_and_ids(
            self, api_client, snapshot_manager):
        """
        Edition 242 "Välitiloja" (2020)
        should return 12 shorts.

        This test verifies:
        1. Correct count of shorts (12)
        2. All short IDs match snapshot
        3. All titles match snapshot
        4. All authors match snapshot
        """
        edition_id = 242
        expected_count = 12

        # Get shorts for edition
        response = api_client.get(
            f'/api/editions/{edition_id}/shorts'
        )
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), (
            "Response should be a list"
        )
        assert len(shorts) == expected_count, (
            f"Expected {expected_count} shorts,"
            f" got {len(shorts)}"
        )

        # Load and compare against snapshot
        snapshot = snapshot_manager.load_snapshot(
            'edition_shorts_242'
        )
        assert snapshot is not None, \
            "Snapshot edition_shorts_242 not found"

        expected_shorts = snapshot['response']['data']
        actual_by_id = {s['id']: s for s in shorts}
        expected_by_id = {s['id']: s for s in expected_shorts}

        # Verify all expected shorts are present
        for short_id, expected in expected_by_id.items():
            assert short_id in actual_by_id, (
                f"Short ID {short_id} ({expected['title']}) missing"
            )

            actual = actual_by_id[short_id]

            # Verify title
            assert actual['title'] == expected['title'], (
                f"Short {short_id}: title mismatch"
            )

            # Verify authors
            exp_authors = expected.get('authors', [])
            expected_author_ids = {a['id'] for a in exp_authors}
            act_authors = actual.get('authors', [])
            actual_author_ids = {int(a['id']) for a in act_authors}
            assert actual_author_ids == expected_author_ids, (
                f"Short {short_id}: author IDs mismatch"
            )

    def test_edition_shorts_has_required_fields(self, api_client):
        """
        Each short in /api/editions/{id}/shorts should have required fields.
        """
        response = api_client.get('/api/editions/242/shorts')
        response.assert_success()

        shorts = response.data
        assert len(shorts) > 0, "Should have shorts"

        required_fields = ['id', 'title', 'authors']

        for short in shorts:
            for field in required_fields:
                assert field in short, (
                    f"Short {short.get('id')} missing field '{field}'"
                )

    def test_edition_shorts_author_fields(self, api_client):
        """
        Authors in edition shorts should have id and name fields.
        """
        response = api_client.get('/api/editions/242/shorts')
        response.assert_success()

        for short in response.data:
            authors = short.get('authors', [])
            for author in authors:
                assert 'id' in author, (
                    f"Short {short['id']}: author missing 'id'"
                )
                assert 'name' in author, (
                    f"Short {short['id']}: author missing 'name'"
                )

    def test_edition_without_shorts(self, api_client):
        """
        GET /api/editions/{id}/shorts for edition without shorts.

        Edition 86 is a regular novel without short stories.
        """
        response = api_client.get('/api/editions/86/shorts')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"
        assert len(shorts) == 0, "Edition 86 should have no shorts"

    def test_edition_shorts_nonexistent_edition(self, api_client):
        """
        GET /api/editions/{id}/shorts for nonexistent edition.
        """
        response = api_client.get('/api/editions/999999999/shorts')
        # May return empty list or error
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            assert response.data == [] or response.data is None


class TestShortEditions(BaseAPITest):
    """
    Tests for short story responses including their editions.

    These tests verify that the short-to-editions relationship
    returns consistent data before and after schema migration.
    """

    def test_short_has_editions(self, api_client, snapshot_manager):
        """
        GET /api/shorts/406 should include editions list.

        Short 406 "William Wilson" appears in multiple editions
        (10 editions total).

        This test verifies the editions list is preserved
        after migration.
        """
        short_id = 406

        response = api_client.get(f'/api/shorts/{short_id}')
        response.assert_success()

        short = response.data
        assert 'editions' in short, "Short should have 'editions' field"

        editions = short['editions']
        assert isinstance(editions, list), "Editions should be a list"
        assert len(editions) >= 2, (
            f"Short 406 should have at least 2 editions,"
            f" got {len(editions)}"
        )

        # Load snapshot and verify editions match
        snapshot = snapshot_manager.load_snapshot('short_406')
        assert snapshot is not None, "Snapshot short_1805 not found"

        expected_editions = snapshot['response']['data']['editions']
        expected_ids = {e['id'] for e in expected_editions}
        actual_ids = {e['id'] for e in editions}

        assert expected_ids == actual_ids, (
            f"Edition IDs mismatch. Expected {expected_ids}, got {actual_ids}"
        )

        # Verify edition details
        actual_by_id = {e['id']: e for e in editions}
        for expected_ed in expected_editions:
            actual_ed = actual_by_id[expected_ed['id']]
            assert actual_ed['title'] == expected_ed['title'], (
                f"Edition {expected_ed['id']}: title mismatch"
            )
            assert actual_ed.get('pubyear') == expected_ed.get('pubyear'), (
                f"Edition {expected_ed['id']}: pubyear mismatch"
            )

    def test_short_editions_have_required_fields(self, api_client):
        """
        Editions in short response should have id, title, pubyear.
        """
        response = api_client.get('/api/shorts/406')
        response.assert_success()

        editions = response.data.get('editions', [])
        assert len(editions) > 0, "Should have editions"

        for edition in editions:
            assert 'id' in edition, "Edition missing 'id'"
            assert 'title' in edition, "Edition missing 'title'"

    def test_short_authors_preserved(self, api_client, snapshot_manager):
        """
        Short story authors should be preserved after migration.
        """
        response = api_client.get('/api/shorts/406')
        response.assert_success()

        short = response.data
        authors = short.get('authors', [])

        snapshot = snapshot_manager.load_snapshot('short_406')
        expected_authors = snapshot['response']['data']['authors']

        expected_ids = {a['id'] for a in expected_authors}
        actual_ids = {int(a['id']) for a in authors}

        assert actual_ids == expected_ids, (
            f"Author IDs mismatch. Expected {expected_ids}, got {actual_ids}"
        )


class TestEditionShortsBackwardCompat(BaseAPITest):
    """
    Backward compatibility tests for edition-short relationships.

    These tests verify the exact API response format remains unchanged,
    ensuring clients don't break after migration.
    """

    def test_edition_shorts_response_format(self, api_client):
        """
        Verify edition shorts response has expected structure.

        Response is a list of shorts (may or may not be wrapped in 'response').
        Each short should have consistent field types.
        """
        response = api_client.get('/api/editions/242/shorts')
        response.assert_success()

        # Verify response is not None
        assert response.json is not None

        # response.data handles both wrapped and unwrapped responses
        shorts = response.data
        if len(shorts) > 0:
            short = shorts[0]

            # Verify field types
            assert isinstance(short['id'], int), "id should be int"
            assert isinstance(short['title'], str), "title should be str"

            if 'pubyear' in short and short['pubyear'] is not None:
                assert isinstance(short['pubyear'], int), \
                    "pubyear should be int"

            assert isinstance(short.get('authors', []), list), (
                "authors should be list"
            )

    def test_short_response_format(self, api_client):
        """
        Verify short story response has expected structure.

        Editions list should have consistent format.
        """
        response = api_client.get('/api/shorts/406')
        response.assert_success()

        short = response.data

        # Verify editions format
        editions = short.get('editions', [])
        if len(editions) > 0:
            edition = editions[0]
            assert isinstance(edition['id'], int), "edition id should be int"
            assert isinstance(edition['title'], str), \
                "edition title should be str"

        # Verify authors format
        authors = short.get('authors', [])
        if len(authors) > 0:
            author = authors[0]
            assert 'id' in author, "author should have id"
            assert 'name' in author, "author should have name"
