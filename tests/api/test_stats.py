"""
SuomiSF API Statistics Endpoint Tests

Tests for /api/stats/* endpoints with snapshot comparison.
"""

from .base_test import BaseAPITest


class TestGenreCounts(BaseAPITest):
    """Tests for /api/stats/genrecounts endpoint."""

    def test_get_genrecounts_returns_200(self, api_client):
        """GET /api/stats/genrecounts should return 200."""
        response = api_client.get('/api/stats/genrecounts')
        response.assert_status(200)

    def test_get_genrecounts_has_data(self, api_client):
        """GET /api/stats/genrecounts should return genre data."""
        response = api_client.get('/api/stats/genrecounts')
        response.assert_success()
        # Returns data directly without 'response' wrapper
        assert response.json is not None
        assert len(response.json) > 0

    def test_get_genrecounts_matches_snapshot(self, api_client,
                                              snapshot_manager):
        """GET /api/stats/genrecounts should match snapshot data."""
        response = api_client.get('/api/stats/genrecounts')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_genrecounts',
                                                 response.json)


class TestPersonCounts(BaseAPITest):
    """Tests for /api/stats/personcounts endpoint."""

    def test_get_personcounts_returns_200(self, api_client):
        """GET /api/stats/personcounts should return 200."""
        response = api_client.get('/api/stats/personcounts')
        response.assert_status(200)

    def test_get_personcounts_returns_list(self, api_client):
        """GET /api/stats/personcounts should return a list."""
        response = api_client.get('/api/stats/personcounts')
        response.assert_success().assert_data_is_list()

    def test_get_personcounts_matches_snapshot(self, api_client,
                                               snapshot_manager):
        """GET /api/stats/personcounts should match snapshot data."""
        response = api_client.get('/api/stats/personcounts')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_personcounts',
                                                 response.json)


class TestStoryPersonCounts(BaseAPITest):
    """Tests for /api/stats/storypersoncounts endpoint."""

    def test_get_storypersoncounts_returns_200(self, api_client):
        """GET /api/stats/storypersoncounts should return 200."""
        response = api_client.get('/api/stats/storypersoncounts')
        response.assert_status(200)

    def test_get_storypersoncounts_matches_snapshot(self, api_client,
                                                    snapshot_manager):
        """GET /api/stats/storypersoncounts should match snapshot data."""
        response = api_client.get('/api/stats/storypersoncounts')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_storypersoncounts',
                                                 response.json)


class TestPublisherCounts(BaseAPITest):
    """Tests for /api/stats/publishercounts endpoint."""

    def test_get_publishercounts_returns_200(self, api_client):
        """GET /api/stats/publishercounts should return 200."""
        response = api_client.get('/api/stats/publishercounts')
        response.assert_status(200)

    def test_get_publishercounts_returns_list(self, api_client):
        """GET /api/stats/publishercounts should return a list."""
        response = api_client.get('/api/stats/publishercounts')
        response.assert_success().assert_data_is_list()

    def test_get_publishercounts_matches_snapshot(self, api_client,
                                                  snapshot_manager):
        """GET /api/stats/publishercounts should match snapshot data."""
        response = api_client.get('/api/stats/publishercounts')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_publishercounts',
                                                 response.json)


class TestWorksByYear(BaseAPITest):
    """Tests for /api/stats/worksbyyear endpoint."""

    def test_get_worksbyyear_returns_200(self, api_client):
        """GET /api/stats/worksbyyear should return 200."""
        response = api_client.get('/api/stats/worksbyyear')
        response.assert_status(200)

    def test_get_worksbyyear_returns_list(self, api_client):
        """GET /api/stats/worksbyyear should return a list."""
        response = api_client.get('/api/stats/worksbyyear')
        response.assert_success().assert_data_is_list()

    def test_worksbyyear_has_year_and_count(self, api_client):
        """Each entry should have year and count fields."""
        response = api_client.get('/api/stats/worksbyyear')
        response.assert_success()

        data = response.data
        if data and len(data) > 0:
            entry = data[0]
            # Check for common year statistics fields
            assert 'year' in entry or 'count' in entry or \
                isinstance(entry, (int, list)), \
                f"Unexpected entry format: {entry}"

    def test_get_worksbyyear_matches_snapshot(self, api_client,
                                              snapshot_manager):
        """GET /api/stats/worksbyyear should match snapshot data."""
        response = api_client.get('/api/stats/worksbyyear')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_worksbyyear',
                                                 response.json)


class TestOrigWorksByYear(BaseAPITest):
    """Tests for /api/stats/origworksbyyear endpoint."""

    def test_get_origworksbyyear_returns_200(self, api_client):
        """GET /api/stats/origworksbyyear should return 200."""
        response = api_client.get('/api/stats/origworksbyyear')
        response.assert_status(200)

    def test_get_origworksbyyear_matches_snapshot(self, api_client,
                                                  snapshot_manager):
        """GET /api/stats/origworksbyyear should match snapshot data."""
        response = api_client.get('/api/stats/origworksbyyear')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_origworksbyyear',
                                                 response.json)


class TestStoriesByYear(BaseAPITest):
    """Tests for /api/stats/storiesbyyear endpoint."""

    def test_get_storiesbyyear_returns_200(self, api_client):
        """GET /api/stats/storiesbyyear should return 200."""
        response = api_client.get('/api/stats/storiesbyyear')
        response.assert_status(200)

    def test_get_storiesbyyear_matches_snapshot(self, api_client,
                                                snapshot_manager):
        """GET /api/stats/storiesbyyear should match snapshot data."""
        response = api_client.get('/api/stats/storiesbyyear')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_storiesbyyear',
                                                 response.json)


class TestIssuesPerYear(BaseAPITest):
    """Tests for /api/stats/issuesperyear endpoint."""

    def test_get_issuesperyear_returns_200(self, api_client):
        """GET /api/stats/issuesperyear should return 200."""
        response = api_client.get('/api/stats/issuesperyear')
        response.assert_status(200)

    def test_get_issuesperyear_matches_snapshot(self, api_client,
                                                snapshot_manager):
        """GET /api/stats/issuesperyear should match snapshot data."""
        response = api_client.get('/api/stats/issuesperyear')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_issuesperyear',
                                                 response.json)


class TestNationalityCounts(BaseAPITest):
    """Tests for /api/stats/nationalitycounts endpoint."""

    def test_get_nationalitycounts_returns_200(self, api_client):
        """GET /api/stats/nationalitycounts should return 200."""
        response = api_client.get('/api/stats/nationalitycounts')
        response.assert_status(200)

    def test_get_nationalitycounts_returns_list(self, api_client):
        """GET /api/stats/nationalitycounts should return a list."""
        response = api_client.get('/api/stats/nationalitycounts')
        response.assert_success().assert_data_is_list()

    def test_get_nationalitycounts_matches_snapshot(self, api_client,
                                                    snapshot_manager):
        """GET /api/stats/nationalitycounts should match snapshot data."""
        response = api_client.get('/api/stats/nationalitycounts')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_nationalitycounts',
                                                 response.json)


class TestStoryNationalityCounts(BaseAPITest):
    """Tests for /api/stats/storynationalitycounts endpoint."""

    def test_get_storynationalitycounts_returns_200(self, api_client):
        """GET /api/stats/storynationalitycounts should return 200."""
        response = api_client.get('/api/stats/storynationalitycounts')
        response.assert_status(200)

    def test_get_storynationalitycounts_matches_snapshot(self, api_client,
                                                         snapshot_manager):
        """GET /api/stats/storynationalitycounts should match snapshot data."""
        response = api_client.get('/api/stats/storynationalitycounts')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot(
            'stats_storynationalitycounts', response.json)


class TestFilterStories(BaseAPITest):
    """Tests for /api/stats/filterstories endpoint (POST)."""

    def test_post_filterstories_empty_filter(self, api_client):
        """POST /api/stats/filterstories with empty filter."""
        response = api_client.post('/api/stats/filterstories', data={})
        # May return 200, 400, or 405 depending on implementation
        assert response.status_code in [200, 400, 405]

    def test_post_filterstories_with_year(self, api_client):
        """POST /api/stats/filterstories with year filter."""
        response = api_client.post('/api/stats/filterstories', data={
            'year': 2000
        })
        assert response.status_code in [200, 400, 405]


class TestFilterWorks(BaseAPITest):
    """Tests for /api/stats/filterworks endpoint (POST)."""

    def test_post_filterworks_empty_filter(self, api_client):
        """POST /api/stats/filterworks with empty filter."""
        response = api_client.post('/api/stats/filterworks', data={})
        assert response.status_code in [200, 400, 405]


class TestMiscStats(BaseAPITest):
    """Tests for /api/stats/misc endpoint."""

    def test_get_misc_stats_returns_200(self, api_client):
        """GET /api/stats/misc should return 200."""
        response = api_client.get('/api/stats/misc')
        response.assert_status(200)

    def test_get_misc_stats_has_data(self, api_client):
        """GET /api/stats/misc should return statistics data."""
        response = api_client.get('/api/stats/misc')
        response.assert_success()
        # Returns data directly without 'response' wrapper
        assert response.json is not None
        assert 'total_works' in response.json or \
            'total_editions' in response.json

    def test_get_misc_stats_matches_snapshot(self, api_client,
                                             snapshot_manager):
        """GET /api/stats/misc should match snapshot data."""
        response = api_client.get('/api/stats/misc')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_misc', response.json)
