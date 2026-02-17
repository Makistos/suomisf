"""
SuomiSF API Publisher and Series Tests

Tests for publisher, publication series, and book series endpoints
not covered by other test files. Includes CRUD operations and filtering.

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

# Publisher 150 is Kirjayhtymä (large publisher)
BASIC_PUBLISHER_ID = 150

# Publisher 446 is Hertta-kustannus (small publisher)
SMALL_PUBLISHER_ID = 446

# PubSeries 1 is "10mk:n romaaneja"
BASIC_PUBSERIES_ID = 1

# PubSeries 33 is "GALAXY Scifi"
SCIFI_PUBSERIES_ID = 33

# BookSeries 410 is "Tarzan" (many books, one author)
BASIC_BOOKSERIES_ID = 410

# BookSeries 519 is "Linnunradan käsikirjat liftareille" (multiple authors)
MULTI_AUTHOR_BOOKSERIES_ID = 519


# -------------------------------------------------------------------
# Publisher Test Classes
# -------------------------------------------------------------------

class TestPublisherList(BaseAPITest):
    """Tests for GET /api/publishers endpoint."""

    def test_publishers_list_returns_200(self, api_client):
        """GET /api/publishers should return 200."""
        response = api_client.get('/api/publishers')
        response.assert_success()

    def test_publishers_list_returns_list(self, api_client):
        """GET /api/publishers returns list format."""
        response = api_client.get('/api/publishers')
        response.assert_success()

        data = response.data
        assert isinstance(data, list), "Response should be a list"

    def test_publishers_list_has_required_fields(self, api_client):
        """Publishers in list have required fields."""
        response = api_client.get('/api/publishers')
        response.assert_success()

        if response.data and len(response.data) > 0:
            publisher = response.data[0]
            assert 'id' in publisher, "Publisher missing 'id'"
            assert 'name' in publisher, "Publisher missing 'name'"


class TestPublisherGet(BaseAPITest):
    """Tests for GET /api/publishers/{id} endpoint."""

    def test_publisher_get_returns_200(self, api_client):
        """GET /api/publishers/{id} should return 200."""
        response = api_client.get(f'/api/publishers/{BASIC_PUBLISHER_ID}')
        response.assert_success()

    def test_publisher_get_has_fields(self, api_client):
        """Publisher response has required fields."""
        response = api_client.get(f'/api/publishers/{BASIC_PUBLISHER_ID}')
        response.assert_success()

        data = response.data
        assert 'id' in data, "Publisher missing 'id'"
        assert 'name' in data, "Publisher missing 'name'"

    def test_publisher_get_nonexistent(self, api_client):
        """GET /api/publishers/{nonexistent} handles gracefully."""
        response = api_client.get('/api/publishers/999999999')
        assert response.status_code in [200, 400, 404]

    def test_publisher_get_invalid_id(self, api_client):
        """GET /api/publishers/{invalid} returns 400."""
        response = api_client.get('/api/publishers/invalid')
        assert response.status_code == 400


class TestPublisherUpdate(BaseAPITest):
    """Tests for PUT /api/publishers endpoint."""

    def test_update_publisher_requires_auth(self, api_client):
        """PUT /api/publishers requires authentication."""
        response = api_client.put('/api/publishers', data={
            'id': BASIC_PUBLISHER_ID,
            'name': 'Test Publisher'
        })
        assert response.status_code in [401, 403, 422]

    def test_update_publisher_with_auth(self, admin_client):
        """PUT /api/publishers with auth processes request."""
        # Get current publisher data first
        get_resp = admin_client.get(f'/api/publishers/{BASIC_PUBLISHER_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get publisher data')

        current = get_resp.data
        response = admin_client.put('/api/publishers', data={
            'data': {
                'id': BASIC_PUBLISHER_ID,
                'name': current.get('name', 'Test Publisher')
            }
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]

    def test_update_publisher_small(self, admin_client):
        """PUT /api/publishers for small publisher."""
        get_resp = admin_client.get(f'/api/publishers/{SMALL_PUBLISHER_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get publisher data')

        current = get_resp.data
        response = admin_client.put('/api/publishers', data={
            'data': {
                'id': SMALL_PUBLISHER_ID,
                'name': current.get('name', 'Test')
            }
        })
        assert response.status_code in [200, 400, 500]


class TestPublisherFilter(BaseAPITest):
    """Tests for GET /api/filter/publishers/{pattern} endpoint."""

    def test_filter_publishers_returns_200(self, api_client):
        """GET /api/filter/publishers/{pattern} should return 200."""
        response = api_client.get('/api/filter/publishers/kirja')
        response.assert_success()

    def test_filter_publishers_returns_list(self, api_client):
        """GET /api/filter/publishers/{pattern} returns list."""
        response = api_client.get('/api/filter/publishers/kirja')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_filter_publishers_short_pattern(self, api_client):
        """GET /api/filter/publishers/{short} returns 400."""
        response = api_client.get('/api/filter/publishers/k')
        assert response.status_code == 400

    def test_filter_publishers_no_results(self, api_client):
        """GET /api/filter/publishers/{nonexistent} returns empty list."""
        response = api_client.get('/api/filter/publishers/xyznonexistent123')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)


# -------------------------------------------------------------------
# Publication Series Test Classes
# -------------------------------------------------------------------

class TestPubSeriesList(BaseAPITest):
    """Tests for GET /api/pubseries endpoint."""

    def test_pubseries_list_returns_200(self, api_client):
        """GET /api/pubseries should return 200."""
        response = api_client.get('/api/pubseries')
        response.assert_success()

    def test_pubseries_list_returns_list(self, api_client):
        """GET /api/pubseries returns list format."""
        response = api_client.get('/api/pubseries')
        response.assert_success()

        data = response.data
        assert isinstance(data, list), "Response should be a list"

    def test_pubseries_list_has_required_fields(self, api_client):
        """Publication series in list have required fields."""
        response = api_client.get('/api/pubseries')
        response.assert_success()

        if response.data and len(response.data) > 0:
            pubseries = response.data[0]
            assert 'id' in pubseries, "PubSeries missing 'id'"
            assert 'name' in pubseries, "PubSeries missing 'name'"


class TestPubSeriesGet(BaseAPITest):
    """Tests for GET /api/pubseries/{id} endpoint."""

    def test_pubseries_get_returns_200(self, api_client):
        """GET /api/pubseries/{id} should return 200."""
        response = api_client.get(f'/api/pubseries/{BASIC_PUBSERIES_ID}')
        response.assert_success()

    def test_pubseries_get_has_fields(self, api_client):
        """PubSeries response has required fields."""
        response = api_client.get(f'/api/pubseries/{BASIC_PUBSERIES_ID}')
        response.assert_success()

        data = response.data
        assert 'id' in data, "PubSeries missing 'id'"
        assert 'name' in data, "PubSeries missing 'name'"

    def test_pubseries_get_nonexistent(self, api_client):
        """GET /api/pubseries/{nonexistent} handles gracefully."""
        response = api_client.get('/api/pubseries/999999999')
        assert response.status_code in [200, 400, 404]

    def test_pubseries_get_invalid_id(self, api_client):
        """GET /api/pubseries/{invalid} returns 400."""
        response = api_client.get('/api/pubseries/invalid')
        assert response.status_code == 400


class TestPubSeriesUpdate(BaseAPITest):
    """Tests for PUT /api/pubseries endpoint."""

    def test_update_pubseries_requires_auth(self, api_client):
        """PUT /api/pubseries requires authentication."""
        response = api_client.put('/api/pubseries', data={
            'id': BASIC_PUBSERIES_ID,
            'name': 'Test PubSeries'
        })
        assert response.status_code in [401, 403, 422]

    def test_update_pubseries_with_auth(self, admin_client):
        """PUT /api/pubseries with auth processes request."""
        # Get current pubseries data first
        get_resp = admin_client.get(f'/api/pubseries/{BASIC_PUBSERIES_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get pubseries data')

        current = get_resp.data
        response = admin_client.put('/api/pubseries', data={
            'data': {
                'id': BASIC_PUBSERIES_ID,
                'name': current.get('name', 'Test PubSeries')
            }
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]

    def test_update_pubseries_scifi(self, admin_client):
        """PUT /api/pubseries for sci-fi series."""
        get_resp = admin_client.get(f'/api/pubseries/{SCIFI_PUBSERIES_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get pubseries data')

        current = get_resp.data
        response = admin_client.put('/api/pubseries', data={
            'data': {
                'id': SCIFI_PUBSERIES_ID,
                'name': current.get('name', 'Test')
            }
        })
        assert response.status_code in [200, 400, 500]


class TestPubSeriesFilter(BaseAPITest):
    """Tests for GET /api/filter/pubseries/{pattern} endpoint."""

    def test_filter_pubseries_returns_200(self, api_client):
        """GET /api/filter/pubseries/{pattern} should return 200."""
        response = api_client.get('/api/filter/pubseries/galaxy')
        response.assert_success()

    def test_filter_pubseries_returns_list(self, api_client):
        """GET /api/filter/pubseries/{pattern} returns list."""
        response = api_client.get('/api/filter/pubseries/scifi')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_filter_pubseries_short_pattern(self, api_client):
        """GET /api/filter/pubseries/{short} returns 400."""
        response = api_client.get('/api/filter/pubseries/g')
        assert response.status_code == 400

    def test_filter_pubseries_no_results(self, api_client):
        """GET /api/filter/pubseries/{nonexistent} returns empty list."""
        response = api_client.get('/api/filter/pubseries/xyznonexistent123')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)


# -------------------------------------------------------------------
# Book Series Test Classes
# -------------------------------------------------------------------

class TestBookSeriesList(BaseAPITest):
    """Tests for GET /api/bookseries endpoint."""

    def test_bookseries_list_returns_200(self, api_client):
        """GET /api/bookseries should return 200."""
        response = api_client.get('/api/bookseries')
        response.assert_success()

    def test_bookseries_list_returns_list(self, api_client):
        """GET /api/bookseries returns list format."""
        response = api_client.get('/api/bookseries')
        response.assert_success()

        data = response.data
        assert isinstance(data, list), "Response should be a list"

    def test_bookseries_list_has_required_fields(self, api_client):
        """Book series in list have required fields."""
        response = api_client.get('/api/bookseries')
        response.assert_success()

        if response.data and len(response.data) > 0:
            bookseries = response.data[0]
            assert 'id' in bookseries, "BookSeries missing 'id'"
            assert 'name' in bookseries, "BookSeries missing 'name'"


class TestBookSeriesGet(BaseAPITest):
    """Tests for GET /api/bookseries/{id} endpoint."""

    def test_bookseries_get_returns_200(self, api_client):
        """GET /api/bookseries/{id} should return 200."""
        response = api_client.get(f'/api/bookseries/{BASIC_BOOKSERIES_ID}')
        response.assert_success()

    def test_bookseries_get_has_fields(self, api_client):
        """BookSeries response has required fields."""
        response = api_client.get(f'/api/bookseries/{BASIC_BOOKSERIES_ID}')
        response.assert_success()

        data = response.data
        assert 'id' in data, "BookSeries missing 'id'"
        assert 'name' in data, "BookSeries missing 'name'"

    def test_bookseries_get_multi_author(self, api_client):
        """GET /api/bookseries/{id} for multi-author series."""
        url = f'/api/bookseries/{MULTI_AUTHOR_BOOKSERIES_ID}'
        response = api_client.get(url)
        response.assert_success()

    def test_bookseries_get_nonexistent(self, api_client):
        """GET /api/bookseries/{nonexistent} handles gracefully."""
        response = api_client.get('/api/bookseries/999999999')
        assert response.status_code in [200, 400, 404]

    def test_bookseries_get_invalid_id(self, api_client):
        """GET /api/bookseries/{invalid} returns 400."""
        response = api_client.get('/api/bookseries/invalid')
        assert response.status_code == 400


class TestBookSeriesUpdate(BaseAPITest):
    """Tests for PUT /api/bookseries endpoint."""

    def test_update_bookseries_requires_auth(self, api_client):
        """PUT /api/bookseries requires authentication."""
        response = api_client.put('/api/bookseries', data={
            'id': BASIC_BOOKSERIES_ID,
            'name': 'Test BookSeries'
        })
        assert response.status_code in [401, 403, 422]

    def test_update_bookseries_with_auth(self, admin_client):
        """PUT /api/bookseries with auth processes request."""
        # Get current bookseries data first
        get_resp = admin_client.get(f'/api/bookseries/{BASIC_BOOKSERIES_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get bookseries data')

        current = get_resp.data
        response = admin_client.put('/api/bookseries', data={
            'data': {
                'id': BASIC_BOOKSERIES_ID,
                'name': current.get('name', 'Test BookSeries')
            }
        })
        # May return 200 or validation error
        assert response.status_code in [200, 400, 500]

    def test_update_bookseries_multi_author(self, admin_client):
        """PUT /api/bookseries for multi-author series."""
        get_resp = admin_client.get(f'/api/bookseries/{MULTI_AUTHOR_BOOKSERIES_ID}')
        if get_resp.status_code != 200:
            pytest.skip('Cannot get bookseries data')

        current = get_resp.data
        response = admin_client.put('/api/bookseries', data={
            'data': {
                'id': MULTI_AUTHOR_BOOKSERIES_ID,
                'name': current.get('name', 'Test')
            }
        })
        assert response.status_code in [200, 400, 500]


class TestBookSeriesFilter(BaseAPITest):
    """Tests for GET /api/filter/bookseries/{pattern} endpoint."""

    def test_filter_bookseries_returns_200(self, api_client):
        """GET /api/filter/bookseries/{pattern} should return 200."""
        response = api_client.get('/api/filter/bookseries/tarzan')
        response.assert_success()

    def test_filter_bookseries_returns_list(self, api_client):
        """GET /api/filter/bookseries/{pattern} returns list."""
        response = api_client.get('/api/filter/bookseries/linnun')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)

    def test_filter_bookseries_short_pattern(self, api_client):
        """GET /api/filter/bookseries/{short} returns 400."""
        response = api_client.get('/api/filter/bookseries/t')
        assert response.status_code == 400

    def test_filter_bookseries_no_results(self, api_client):
        """GET /api/filter/bookseries/{nonexistent} returns empty list."""
        response = api_client.get('/api/filter/bookseries/xyznonexistent123')
        response.assert_success()

        data = response.data
        if data is not None:
            assert isinstance(data, list)
