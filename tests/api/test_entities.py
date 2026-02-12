"""
SuomiSF API Entity Endpoint Tests

Parameterized tests for entity endpoints (works, editions, people, etc.)
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


def get_entity_params(entity: str, param_key: str = 'id') -> List[tuple]:
    """Get parameter sets for an entity type."""
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


# ---------------------------------------------------------------------------
# Works
# ---------------------------------------------------------------------------

class TestWorks(BaseAPITest):
    """Tests for /api/works/{id} endpoint."""

    @pytest.mark.parametrize('work_id', get_entity_params('works'))
    def test_get_work_returns_200(self, api_client, work_id):
        """GET /api/works/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/works/{work_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('work_id', get_entity_params('works'))
    def test_get_work_has_required_fields(self, api_client, work_id):
        """GET /api/works/{id} should return work with required fields."""
        response = api_client.get(f'/api/works/{work_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Work should have 'id' field"
        assert data['id'] == work_id

    def test_get_work_not_found(self, api_client):
        """GET /api/works/{id} should return 404 for invalid ID."""
        response = api_client.get('/api/works/999999999')
        response.assert_status(404)


# ---------------------------------------------------------------------------
# Editions
# ---------------------------------------------------------------------------

class TestEditions(BaseAPITest):
    """Tests for /api/editions/{id} endpoint."""

    @pytest.mark.parametrize('edition_id', get_entity_params('editions'))
    def test_get_edition_returns_200(self, api_client, edition_id):
        """GET /api/editions/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/editions/{edition_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('edition_id', get_entity_params('editions'))
    def test_get_edition_has_required_fields(self, api_client, edition_id):
        """GET /api/editions/{id} should return edition with required fields."""
        response = api_client.get(f'/api/editions/{edition_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Edition should have 'id' field"
        assert data['id'] == edition_id

    def test_get_edition_not_found(self, api_client):
        """GET /api/editions/{id} should return error for invalid ID."""
        response = api_client.get('/api/editions/999999999')
        assert response.status_code in [400, 404]


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------

class TestPeople(BaseAPITest):
    """Tests for /api/people/{id} endpoint."""

    @pytest.mark.parametrize('person_id', get_entity_params('people'))
    def test_get_person_returns_200(self, api_client, person_id):
        """GET /api/people/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/people/{person_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('person_id', get_entity_params('people'))
    def test_get_person_has_required_fields(self, api_client, person_id):
        """GET /api/people/{id} should return person with required fields."""
        response = api_client.get(f'/api/people/{person_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Person should have 'id' field"
        assert data['id'] == person_id

    def test_get_person_not_found(self, api_client):
        """GET /api/people/{id} should return error for invalid ID."""
        response = api_client.get('/api/people/999999999')
        assert response.status_code in [400, 404]


# ---------------------------------------------------------------------------
# Short Stories
# ---------------------------------------------------------------------------

class TestShorts(BaseAPITest):
    """Tests for /api/shorts/{id} endpoint."""

    @pytest.mark.parametrize('short_id', get_entity_params('shorts'))
    def test_get_short_returns_200(self, api_client, short_id):
        """GET /api/shorts/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/shorts/{short_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('short_id', get_entity_params('shorts'))
    def test_get_short_has_required_fields(self, api_client, short_id):
        """GET /api/shorts/{id} should return short with required fields."""
        response = api_client.get(f'/api/shorts/{short_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Short should have 'id' field"
        assert data['id'] == short_id

    @pytest.mark.xfail(reason="API bug: crashes on non-existent short ID")
    def test_get_short_not_found(self, api_client):
        """GET /api/shorts/{id} should return error for invalid ID."""
        response = api_client.get('/api/shorts/999999999')
        # API should return 400 or 404, but currently crashes
        assert response.status_code in [400, 404]


# ---------------------------------------------------------------------------
# Magazines
# ---------------------------------------------------------------------------

class TestMagazines(BaseAPITest):
    """Tests for /api/magazines/{id} endpoint."""

    @pytest.mark.parametrize('magazine_id', get_entity_params('magazines'))
    def test_get_magazine_returns_200(self, api_client, magazine_id):
        """GET /api/magazines/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/magazines/{magazine_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('magazine_id', get_entity_params('magazines'))
    def test_get_magazine_has_required_fields(self, api_client, magazine_id):
        """GET /api/magazines/{id} should return magazine with required fields."""
        response = api_client.get(f'/api/magazines/{magazine_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Magazine should have 'id' field"
        assert data['id'] == magazine_id


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

class TestIssues(BaseAPITest):
    """Tests for /api/issues/{id} endpoint."""

    @pytest.mark.parametrize('issue_id', get_entity_params('issues'))
    def test_get_issue_returns_200(self, api_client, issue_id):
        """GET /api/issues/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/issues/{issue_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('issue_id', get_entity_params('issues'))
    def test_get_issue_has_required_fields(self, api_client, issue_id):
        """GET /api/issues/{id} should return issue with required fields."""
        response = api_client.get(f'/api/issues/{issue_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Issue should have 'id' field"
        assert data['id'] == issue_id


# ---------------------------------------------------------------------------
# Awards
# ---------------------------------------------------------------------------

class TestAwards(BaseAPITest):
    """Tests for /api/awards/{id} endpoint."""

    @pytest.mark.parametrize('award_id', get_entity_params('awards'))
    def test_get_award_returns_200(self, api_client, award_id):
        """GET /api/awards/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/awards/{award_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('award_id', get_entity_params('awards'))
    def test_get_award_has_required_fields(self, api_client, award_id):
        """GET /api/awards/{id} should return award with required fields."""
        response = api_client.get(f'/api/awards/{award_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Award should have 'id' field"
        assert data['id'] == award_id


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

class TestTags(BaseAPITest):
    """Tests for /api/tags/{id} endpoint."""

    @pytest.mark.parametrize('tag_id', get_entity_params('tags'))
    def test_get_tag_returns_200(self, api_client, tag_id):
        """GET /api/tags/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/tags/{tag_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('tag_id', get_entity_params('tags'))
    def test_get_tag_has_required_fields(self, api_client, tag_id):
        """GET /api/tags/{id} should return tag with required fields."""
        response = api_client.get(f'/api/tags/{tag_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Tag should have 'id' field"
        assert data['id'] == tag_id


# ---------------------------------------------------------------------------
# Publishers
# ---------------------------------------------------------------------------

class TestPublishers(BaseAPITest):
    """Tests for /api/publishers/{id} endpoint."""

    @pytest.mark.parametrize('publisher_id', get_entity_params('publishers'))
    def test_get_publisher_returns_200(self, api_client, publisher_id):
        """GET /api/publishers/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/publishers/{publisher_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('publisher_id', get_entity_params('publishers'))
    def test_get_publisher_has_required_fields(self, api_client, publisher_id):
        """GET /api/publishers/{id} should return publisher with required fields."""
        response = api_client.get(f'/api/publishers/{publisher_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "Publisher should have 'id' field"
        assert data['id'] == publisher_id


# ---------------------------------------------------------------------------
# Book Series
# ---------------------------------------------------------------------------

class TestBookSeries(BaseAPITest):
    """Tests for /api/bookseries/{id} endpoint."""

    @pytest.mark.parametrize('bookseries_id', get_entity_params('bookseries'))
    def test_get_bookseries_returns_200(self, api_client, bookseries_id):
        """GET /api/bookseries/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/bookseries/{bookseries_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('bookseries_id', get_entity_params('bookseries'))
    def test_get_bookseries_has_required_fields(self, api_client, bookseries_id):
        """GET /api/bookseries/{id} should return bookseries with required fields."""
        response = api_client.get(f'/api/bookseries/{bookseries_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "BookSeries should have 'id' field"
        assert data['id'] == bookseries_id


# ---------------------------------------------------------------------------
# Publication Series
# ---------------------------------------------------------------------------

class TestPubSeries(BaseAPITest):
    """Tests for /api/pubseries/{id} endpoint."""

    @pytest.mark.parametrize('pubseries_id', get_entity_params('pubseries'))
    def test_get_pubseries_returns_200(self, api_client, pubseries_id):
        """GET /api/pubseries/{id} should return 200 for valid ID."""
        response = api_client.get(f'/api/pubseries/{pubseries_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('pubseries_id', get_entity_params('pubseries'))
    def test_get_pubseries_has_required_fields(self, api_client, pubseries_id):
        """GET /api/pubseries/{id} should return pubseries with required fields."""
        response = api_client.get(f'/api/pubseries/{pubseries_id}')
        response.assert_success()
        data = response.data
        assert 'id' in data, "PubSeries should have 'id' field"
        assert data['id'] == pubseries_id
