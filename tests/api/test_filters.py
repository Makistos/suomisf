"""
SuomiSF API Filter and Search Endpoint Tests

Parameterized tests for filter and search endpoints
using test_parameters.json configuration.

Note: Pytest fixtures (api_client) are injected at runtime.
Type checkers may show "unknown type" warnings - these are expected.
"""

import json
import os
from typing import Any, Dict, List

import pytest

from .base_test import BaseAPITest


# Load test parameters
PARAMS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'fixtures',
    'test_parameters.json'
)


def load_test_parameters() -> Dict[str, Any]:
    """Load test parameters from JSON file."""
    with open(PARAMS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_filter_params(entity: str, param_key: str = 'pattern') -> List[tuple]:
    """Get parameter sets for a filter endpoint."""
    params = load_test_parameters()
    if entity not in params:
        return []

    entity_config = params[entity]
    result = []
    for p in entity_config.get('parameters', []):
        value = p.get(param_key)
        if value is not None:
            note = p.get('note', '')
            result.append(pytest.param(value, id=note or str(value)))
    return result


def get_search_params(entity: str) -> List[tuple]:
    """Get parameter sets for a search endpoint (POST data)."""
    params = load_test_parameters()
    if entity not in params:
        return []

    entity_config = params[entity]
    result = []
    for p in entity_config.get('parameters', []):
        data = p.get('data')
        if data is not None:
            note = p.get('note', '')
            result.append(pytest.param(data, id=note or str(data)))
    return result


# ---------------------------------------------------------------------------
# Filter People
# ---------------------------------------------------------------------------

class TestFilterPeople(BaseAPITest):
    """Tests for /api/filter/people/{pattern} endpoint."""

    @pytest.mark.parametrize('pattern', get_filter_params('filter_people'))
    def test_filter_people_returns_200(self, api_client, pattern):
        """GET /api/filter/people/{pattern} should return 200."""
        response = api_client.get(f'/api/filter/people/{pattern}')
        response.assert_status(200)

    @pytest.mark.parametrize('pattern', get_filter_params('filter_people'))
    def test_filter_people_returns_list(self, api_client, pattern):
        """GET /api/filter/people/{pattern} should return a list."""
        response = api_client.get(f'/api/filter/people/{pattern}')
        response.assert_success().assert_data_is_list()

    def test_filter_people_pattern_too_short(self, api_client):
        """GET /api/filter/people/{pattern} should reject short patterns."""
        response = api_client.get('/api/filter/people/a')
        response.assert_status(400)


# ---------------------------------------------------------------------------
# Filter Tags
# ---------------------------------------------------------------------------

class TestFilterTags(BaseAPITest):
    """Tests for /api/filter/tags/{pattern} endpoint."""

    @pytest.mark.parametrize('pattern', get_filter_params('filter_tags'))
    def test_filter_tags_returns_200(self, api_client, pattern):
        """GET /api/filter/tags/{pattern} should return 200."""
        response = api_client.get(f'/api/filter/tags/{pattern}')
        response.assert_status(200)

    @pytest.mark.parametrize('pattern', get_filter_params('filter_tags'))
    def test_filter_tags_returns_list(self, api_client, pattern):
        """GET /api/filter/tags/{pattern} should return a list."""
        response = api_client.get(f'/api/filter/tags/{pattern}')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Filter Publishers
# ---------------------------------------------------------------------------

class TestFilterPublishers(BaseAPITest):
    """Tests for /api/filter/publishers/{pattern} endpoint."""

    @pytest.mark.parametrize('pattern', get_filter_params('filter_publishers'))
    def test_filter_publishers_returns_200(self, api_client, pattern):
        """GET /api/filter/publishers/{pattern} should return 200."""
        response = api_client.get(f'/api/filter/publishers/{pattern}')
        response.assert_status(200)

    @pytest.mark.parametrize('pattern', get_filter_params('filter_publishers'))
    def test_filter_publishers_returns_list(self, api_client, pattern):
        """GET /api/filter/publishers/{pattern} should return a list."""
        response = api_client.get(f'/api/filter/publishers/{pattern}')
        response.assert_success().assert_data_is_list()

    def test_filter_publishers_pattern_too_short(self, api_client):
        """GET /api/filter/publishers/{pattern} should reject short patterns."""
        response = api_client.get('/api/filter/publishers/a')
        response.assert_status(400)


# ---------------------------------------------------------------------------
# Filter Book Series
# ---------------------------------------------------------------------------

class TestFilterBookSeries(BaseAPITest):
    """Tests for /api/filter/bookseries/{pattern} endpoint."""

    @pytest.mark.parametrize('pattern', get_filter_params('filter_bookseries'))
    def test_filter_bookseries_returns_200(self, api_client, pattern):
        """GET /api/filter/bookseries/{pattern} should return 200."""
        response = api_client.get(f'/api/filter/bookseries/{pattern}')
        response.assert_status(200)

    @pytest.mark.parametrize('pattern', get_filter_params('filter_bookseries'))
    def test_filter_bookseries_returns_list(self, api_client, pattern):
        """GET /api/filter/bookseries/{pattern} should return a list."""
        response = api_client.get(f'/api/filter/bookseries/{pattern}')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Filter Publication Series
# ---------------------------------------------------------------------------

class TestFilterPubSeries(BaseAPITest):
    """Tests for /api/filter/pubseries/{pattern} endpoint."""

    @pytest.mark.parametrize('pattern', get_filter_params('filter_pubseries'))
    def test_filter_pubseries_returns_200(self, api_client, pattern):
        """GET /api/filter/pubseries/{pattern} should return 200."""
        response = api_client.get(f'/api/filter/pubseries/{pattern}')
        response.assert_status(200)

    @pytest.mark.parametrize('pattern', get_filter_params('filter_pubseries'))
    def test_filter_pubseries_returns_list(self, api_client, pattern):
        """GET /api/filter/pubseries/{pattern} should return a list."""
        response = api_client.get(f'/api/filter/pubseries/{pattern}')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Filter Link Names
# ---------------------------------------------------------------------------

class TestFilterLinkNames(BaseAPITest):
    """Tests for /api/filter/linknames/{link_type} endpoint.

    Returns the unique link descriptions for a given owner type, used as
    autocomplete options for the link description field.
    """

    # Types that are expected to have link data in the golden test database.
    TYPES_WITH_DATA = ['person', 'work', 'publisher']
    # Supported types that may legitimately be empty in the test database.
    OTHER_VALID_TYPES = ['bookseries', 'pubseries', 'edition', 'article',
                         'award']
    ALL_VALID_TYPES = TYPES_WITH_DATA + OTHER_VALID_TYPES

    @pytest.mark.parametrize('link_type', ALL_VALID_TYPES)
    def test_filter_linknames_returns_200(self, api_client, link_type):
        """GET /api/filter/linknames/{link_type} should return 200."""
        response = api_client.get(f'/api/filter/linknames/{link_type}')
        response.assert_status(200)

    @pytest.mark.parametrize('link_type', ALL_VALID_TYPES)
    def test_filter_linknames_returns_list(self, api_client, link_type):
        """GET /api/filter/linknames/{link_type} should return a list."""
        response = api_client.get(f'/api/filter/linknames/{link_type}')
        response.assert_success().assert_data_is_list()

    @pytest.mark.parametrize('link_type', ALL_VALID_TYPES)
    def test_filter_linknames_returns_strings(self, api_client, link_type):
        """Every returned description should be a plain string."""
        response = api_client.get(f'/api/filter/linknames/{link_type}')
        response.assert_success()
        assert all(isinstance(item, str) for item in response.data), \
            f"Expected list of strings, got {response.data}"

    @pytest.mark.parametrize('link_type', ALL_VALID_TYPES)
    def test_filter_linknames_returns_unique_values(self, api_client,
                                                    link_type):
        """The returned descriptions should be unique."""
        response = api_client.get(f'/api/filter/linknames/{link_type}')
        response.assert_success()
        assert len(response.data) == len(set(response.data)), \
            f"Expected unique descriptions, got duplicates in {response.data}"

    @pytest.mark.parametrize('link_type', TYPES_WITH_DATA)
    def test_filter_linknames_has_data(self, api_client, link_type):
        """Types with seeded links should return a non-empty list."""
        response = api_client.get(f'/api/filter/linknames/{link_type}')
        response.assert_success().assert_data_min_length(1)

    def test_filter_linknames_is_scoped_to_type(self, api_client):
        """Descriptions should be scoped to the requested type, so different
        types can return different sets of descriptions."""
        person = api_client.get('/api/filter/linknames/person')
        work = api_client.get('/api/filter/linknames/work')
        person.assert_success()
        work.assert_success()
        # The endpoint queries only the requested type's table, so the two
        # result sets are computed independently.
        assert person.data != work.data

    def test_filter_linknames_unknown_type_returns_400(self, api_client):
        """An unknown link type should be rejected with a 400."""
        response = api_client.get('/api/filter/linknames/notatype')
        response.assert_status(400)


# ---------------------------------------------------------------------------
# Works by Initial
# ---------------------------------------------------------------------------

class TestWorksByInitial(BaseAPITest):
    """Tests for /api/worksbyinitial/{letter} endpoint."""

    @pytest.mark.parametrize('letter', get_filter_params('worksbyinitial', 'letter'))
    def test_worksbyinitial_returns_200(self, api_client, letter):
        """GET /api/worksbyinitial/{letter} should return 200."""
        response = api_client.get(f'/api/worksbyinitial/{letter}')
        response.assert_status(200)

    @pytest.mark.parametrize('letter', get_filter_params('worksbyinitial', 'letter'))
    def test_worksbyinitial_returns_list(self, api_client, letter):
        """GET /api/worksbyinitial/{letter} should return a list."""
        response = api_client.get(f'/api/worksbyinitial/{letter}')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Search Works (POST)
# ---------------------------------------------------------------------------

class TestSearchWorks(BaseAPITest):
    """Tests for /api/searchworks endpoint (POST)."""

    @pytest.mark.parametrize('search_data', get_search_params('search_works'))
    def test_searchworks_returns_200(self, api_client, search_data):
        """POST /api/searchworks should return 200."""
        response = api_client.post('/api/searchworks', data=search_data)
        response.assert_status(200)

    @pytest.mark.parametrize('search_data', get_search_params('search_works'))
    def test_searchworks_returns_list(self, api_client, search_data):
        """POST /api/searchworks should return a list."""
        response = api_client.post('/api/searchworks', data=search_data)
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Search Shorts (POST)
# ---------------------------------------------------------------------------

class TestSearchShorts(BaseAPITest):
    """Tests for /api/searchshorts endpoint (POST)."""

    @pytest.mark.parametrize('search_data', get_search_params('search_shorts'))
    def test_searchshorts_returns_200(self, api_client, search_data):
        """POST /api/searchshorts should return 200."""
        response = api_client.post('/api/searchshorts', data=search_data)
        response.assert_status(200)

    @pytest.mark.parametrize('search_data', get_search_params('search_shorts'))
    def test_searchshorts_returns_list(self, api_client, search_data):
        """POST /api/searchshorts should return a list."""
        response = api_client.post('/api/searchshorts', data=search_data)
        response.assert_success().assert_data_is_list()


# Note: FilterStories and FilterWorks tests are in test_stats.py
