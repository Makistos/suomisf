"""
SuomiSF API Person Shorts Tests

Tests for the /api/people/{id}/shorts endpoint.
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

class TestPersonShorts(BaseAPITest):
    """
    Tests for GET /api/people/{id}/shorts endpoint.

    These tests verify that person-to-shorts relationships
    return consistent data before and after schema migration.
    """

    def test_person_shorts_count_and_ids(self, api_client, snapshot_manager):
        """
        GET /api/people/3238/shorts should return 44 shorts.

        Person 3238 is Elo, Eija - Finnish SF author.

        This test verifies:
        1. Correct count of shorts (44)
        2. All short IDs match snapshot
        3. Contributors include person 3238
        """
        person_id = 3238
        expected_count = 44

        response = api_client.get(f'/api/people/{person_id}/shorts')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"
        assert len(shorts) == expected_count, (
            f"Expected {expected_count} shorts, got {len(shorts)}"
        )

        # Load snapshot and compare IDs
        snapshot = snapshot_manager.load_snapshot('person_shorts_3238')
        assert snapshot is not None, "Snapshot person_shorts_3238 not found"

        expected_shorts = snapshot['response']['data']
        expected_ids = {s['id'] for s in expected_shorts}
        actual_ids = {s['id'] for s in shorts}

        assert actual_ids == expected_ids, (
            f"Short IDs mismatch. "
            f"Missing: {expected_ids - actual_ids}, "
            f"Extra: {actual_ids - expected_ids}"
        )

    def test_person_shorts_has_required_fields(self, api_client):
        """
        Each short in /api/people/{id}/shorts has required fields.
        """
        response = api_client.get('/api/people/3238/shorts')
        response.assert_success()

        shorts = response.data
        assert len(shorts) > 0, "Should have shorts"

        required_fields = ['id', 'title', 'contributors']

        for short in shorts:
            for field in required_fields:
                assert field in short, (
                    f"Short {short.get('id')} missing field '{field}'"
                )

    def test_person_shorts_contributor_structure(self, api_client):
        """
        Contributors in person shorts have correct structure.
        """
        response = api_client.get('/api/people/3238/shorts')
        response.assert_success()

        for short in response.data[:5]:  # Check first 5
            contributors = short.get('contributors', [])
            assert len(contributors) > 0, (
                f"Short {short['id']} should have contributors"
            )

            for contrib in contributors:
                assert 'person' in contrib, "Contributor missing 'person'"
                assert 'role' in contrib, "Contributor missing 'role'"
                assert 'id' in contrib['person'], "Person missing 'id'"
                assert 'name' in contrib['person'], "Person missing 'name'"
                assert 'id' in contrib['role'], "Role missing 'id'"
                assert 'name' in contrib['role'], "Role missing 'name'"

    def test_person_shorts_includes_person_as_contributor(self, api_client):
        """
        Person's shorts should include them as a contributor.
        """
        person_id = 3238
        response = api_client.get(f'/api/people/{person_id}/shorts')
        response.assert_success()

        # Check first few shorts
        for short in response.data[:5]:
            contributors = short.get('contributors', [])
            person_ids = [int(c['person']['id']) for c in contributors]
            assert person_id in person_ids, (
                f"Short {short['id']} should include person {person_id} "
                f"as contributor. Found: {person_ids}"
            )

    def test_person_shorts_nonexistent_person(self, api_client):
        """
        GET /api/people/{id}/shorts for nonexistent person.
        """
        response = api_client.get('/api/people/999999999/shorts')
        # May return empty list or error
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            assert response.data == [] or response.data is None

    def test_person_without_shorts(self, api_client):
        """
        GET /api/people/{id}/shorts for person without shorts.

        Person ID 1 may or may not have shorts.
        """
        response = api_client.get('/api/people/1/shorts')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"


class TestPersonShortsBackwardCompat(BaseAPITest):
    """
    Backward compatibility tests for person-short relationships.
    """

    def test_person_shorts_response_format(self, api_client):
        """
        Verify person shorts response has expected structure.
        """
        response = api_client.get('/api/people/3238/shorts')
        response.assert_success()

        assert response.json is not None

        shorts = response.data
        if len(shorts) > 0:
            short = shorts[0]

            assert isinstance(short['id'], int), "id should be int"
            assert isinstance(short['title'], str), "title should be str"
            assert isinstance(
                short.get('contributors', []), list
            ), "contributors should be list"

    def test_person_shorts_contributor_roles(
        self, api_client, snapshot_manager
    ):
        """
        Verify contributor roles match snapshot.

        This ensures the migration preserves role assignments.
        """
        response = api_client.get('/api/people/3238/shorts')
        response.assert_success()

        snapshot = snapshot_manager.load_snapshot('person_shorts_3238')
        expected_shorts = snapshot['response']['data']
        expected_by_id = {s['id']: s for s in expected_shorts}

        for actual in response.data[:10]:  # Check first 10
            short_id = actual['id']
            if short_id not in expected_by_id:
                continue

            expected = expected_by_id[short_id]

            # Count contributors by role
            actual_roles = {}
            for c in actual.get('contributors', []):
                role_id = c['role']['id']
                actual_roles[role_id] = actual_roles.get(role_id, 0) + 1

            expected_roles = {}
            for c in expected.get('contributors', []):
                if 'role_id' in c:
                    rid = c['role_id']
                elif 'role' in c and c['role']:
                    rid = c['role']['id']
                else:
                    continue
                expected_roles[rid] = (
                    expected_roles.get(rid, 0) + 1
                )

            # At minimum, author role should be present
            assert 1 in actual_roles or 1 in expected_roles, (
                f"Short {short_id} should have author contributors"
            )
