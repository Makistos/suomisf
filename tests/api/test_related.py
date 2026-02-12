"""
SuomiSF API Related/Nested Endpoint Tests

Parameterized tests for endpoints that fetch related data
(e.g., works by author, shorts in edition, awards for person).

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


def get_params(entity: str, param_key: str) -> List[tuple]:
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
# Works by Author
# ---------------------------------------------------------------------------

class TestWorksByAuthor(BaseAPITest):
    """Tests for /api/worksbyauthor/{authorid} endpoint."""

    @pytest.mark.parametrize('author_id', get_params('worksbyauthor', 'authorid'))
    def test_worksbyauthor_returns_200(self, api_client, author_id):
        """GET /api/worksbyauthor/{authorid} should return 200."""
        response = api_client.get(f'/api/worksbyauthor/{author_id}')
        response.assert_status(200)

    @pytest.mark.parametrize('author_id', get_params('worksbyauthor', 'authorid'))
    def test_worksbyauthor_returns_list(self, api_client, author_id):
        """GET /api/worksbyauthor/{authorid} should return a list."""
        response = api_client.get(f'/api/worksbyauthor/{author_id}')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Work Awards
# ---------------------------------------------------------------------------

class TestWorkAwards(BaseAPITest):
    """Tests for /api/works/{workid}/awards endpoint."""

    @pytest.mark.parametrize('work_id', get_params('work_awards', 'workid'))
    def test_work_awards_returns_200(self, api_client, work_id):
        """GET /api/works/{workid}/awards should return 200."""
        response = api_client.get(f'/api/works/{work_id}/awards')
        response.assert_status(200)

    @pytest.mark.parametrize('work_id', get_params('work_awards', 'workid'))
    def test_work_awards_returns_list(self, api_client, work_id):
        """GET /api/works/{workid}/awards should return a list."""
        response = api_client.get(f'/api/works/{work_id}/awards')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Person Shorts
# ---------------------------------------------------------------------------

class TestPersonShorts(BaseAPITest):
    """Tests for /api/people/{personid}/shorts endpoint."""

    @pytest.mark.parametrize('person_id', get_params('person_shorts', 'personid'))
    def test_person_shorts_returns_200(self, api_client, person_id):
        """GET /api/people/{personid}/shorts should return 200."""
        response = api_client.get(f'/api/people/{person_id}/shorts')
        response.assert_status(200)

    @pytest.mark.parametrize('person_id', get_params('person_shorts', 'personid'))
    def test_person_shorts_returns_list(self, api_client, person_id):
        """GET /api/people/{personid}/shorts should return a list."""
        response = api_client.get(f'/api/people/{person_id}/shorts')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Person Awarded
# ---------------------------------------------------------------------------

class TestPersonAwarded(BaseAPITest):
    """Tests for /api/people/{personid}/awarded endpoint."""

    @pytest.mark.parametrize('person_id', get_params('person_awarded', 'personid'))
    def test_person_awarded_returns_200(self, api_client, person_id):
        """GET /api/people/{personid}/awarded should return 200."""
        response = api_client.get(f'/api/people/{person_id}/awarded')
        response.assert_status(200)

    @pytest.mark.parametrize('person_id', get_params('person_awarded', 'personid'))
    def test_person_awarded_returns_list(self, api_client, person_id):
        """GET /api/people/{personid}/awarded should return a list."""
        response = api_client.get(f'/api/people/{person_id}/awarded')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Edition Shorts
# ---------------------------------------------------------------------------

class TestEditionShorts(BaseAPITest):
    """Tests for /api/editions/{editionid}/shorts endpoint."""

    @pytest.mark.parametrize('edition_id', get_params('edition_shorts', 'editionid'))
    def test_edition_shorts_returns_200(self, api_client, edition_id):
        """GET /api/editions/{editionid}/shorts should return 200."""
        response = api_client.get(f'/api/editions/{edition_id}/shorts')
        response.assert_status(200)

    @pytest.mark.parametrize('edition_id', get_params('edition_shorts', 'editionid'))
    def test_edition_shorts_returns_list(self, api_client, edition_id):
        """GET /api/editions/{editionid}/shorts should return a list."""
        response = api_client.get(f'/api/editions/{edition_id}/shorts')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Issue Shorts
# ---------------------------------------------------------------------------

class TestIssueShorts(BaseAPITest):
    """Tests for /api/issues/{issueid}/shorts endpoint."""

    @pytest.mark.parametrize('issue_id', get_params('issue_shorts', 'issueid'))
    def test_issue_shorts_returns_200(self, api_client, issue_id):
        """GET /api/issues/{issueid}/shorts should return 200."""
        response = api_client.get(f'/api/issues/{issue_id}/shorts')
        response.assert_status(200)

    @pytest.mark.parametrize('issue_id', get_params('issue_shorts', 'issueid'))
    def test_issue_shorts_returns_list(self, api_client, issue_id):
        """GET /api/issues/{issueid}/shorts should return a list."""
        response = api_client.get(f'/api/issues/{issue_id}/shorts')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Issue Articles
# ---------------------------------------------------------------------------

class TestIssueArticles(BaseAPITest):
    """Tests for /api/issues/{issueid}/articles endpoint."""

    @pytest.mark.parametrize('issue_id', get_params('issue_articles', 'issueid'))
    def test_issue_articles_returns_200(self, api_client, issue_id):
        """GET /api/issues/{issueid}/articles should return 200."""
        response = api_client.get(f'/api/issues/{issue_id}/articles')
        response.assert_status(200)

    @pytest.mark.parametrize('issue_id', get_params('issue_articles', 'issueid'))
    def test_issue_articles_returns_list(self, api_client, issue_id):
        """GET /api/issues/{issueid}/articles should return a list."""
        response = api_client.get(f'/api/issues/{issue_id}/articles')
        response.assert_success().assert_data_is_list()


# ---------------------------------------------------------------------------
# Latest Endpoints
# ---------------------------------------------------------------------------

class TestLatestWorks(BaseAPITest):
    """Tests for /api/latest/works/{count} endpoint."""

    @pytest.mark.parametrize('count', get_params('latest_works', 'count'))
    def test_latest_works_returns_200(self, api_client, count):
        """GET /api/latest/works/{count} should return 200."""
        response = api_client.get(f'/api/latest/works/{count}')
        response.assert_status(200)

    @pytest.mark.parametrize('count', get_params('latest_works', 'count'))
    def test_latest_works_returns_list(self, api_client, count):
        """GET /api/latest/works/{count} should return a list."""
        response = api_client.get(f'/api/latest/works/{count}')
        response.assert_success().assert_data_is_list()

    @pytest.mark.parametrize('count', get_params('latest_works', 'count'))
    def test_latest_works_respects_count(self, api_client, count):
        """GET /api/latest/works/{count} should return at most count items."""
        response = api_client.get(f'/api/latest/works/{count}')
        response.assert_success()
        assert len(response.data) <= count


class TestLatestEditions(BaseAPITest):
    """Tests for /api/latest/editions/{count} endpoint."""

    @pytest.mark.parametrize('count', get_params('latest_editions', 'count'))
    def test_latest_editions_returns_200(self, api_client, count):
        """GET /api/latest/editions/{count} should return 200."""
        response = api_client.get(f'/api/latest/editions/{count}')
        response.assert_status(200)

    @pytest.mark.parametrize('count', get_params('latest_editions', 'count'))
    def test_latest_editions_returns_list(self, api_client, count):
        """GET /api/latest/editions/{count} should return a list."""
        response = api_client.get(f'/api/latest/editions/{count}')
        response.assert_success().assert_data_is_list()


class TestLatestPeople(BaseAPITest):
    """Tests for /api/latest/people/{count} endpoint."""

    @pytest.mark.parametrize('count', get_params('latest_people', 'count'))
    def test_latest_people_returns_200(self, api_client, count):
        """GET /api/latest/people/{count} should return 200."""
        response = api_client.get(f'/api/latest/people/{count}')
        response.assert_status(200)

    @pytest.mark.parametrize('count', get_params('latest_people', 'count'))
    def test_latest_people_returns_list(self, api_client, count):
        """GET /api/latest/people/{count} should return a list."""
        response = api_client.get(f'/api/latest/people/{count}')
        response.assert_success().assert_data_is_list()


class TestLatestShorts(BaseAPITest):
    """Tests for /api/latest/shorts/{count} endpoint."""

    @pytest.mark.parametrize('count', get_params('latest_shorts', 'count'))
    def test_latest_shorts_returns_200(self, api_client, count):
        """GET /api/latest/shorts/{count} should return 200."""
        response = api_client.get(f'/api/latest/shorts/{count}')
        response.assert_status(200)

    @pytest.mark.parametrize('count', get_params('latest_shorts', 'count'))
    def test_latest_shorts_returns_list(self, api_client, count):
        """GET /api/latest/shorts/{count} should return a list."""
        response = api_client.get(f'/api/latest/shorts/{count}')
        response.assert_success().assert_data_is_list()
