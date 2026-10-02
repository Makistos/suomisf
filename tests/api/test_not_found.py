"""
SuomiSF API not-found contract.

A record named in the URL that doesn't exist answers 404; a malformed id
answers 400. The frontend's error page relies on this to tell "no such
record" apart from a server failure, so every entity endpoint is pinned
here rather than with permissive status lists in the per-entity files.
"""

import pytest

from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD

MISSING_ID = 999999999

GET_ENDPOINTS = [
    'awards', 'bookseries', 'editions', 'issues', 'magazines', 'people',
    'publishers', 'pubseries', 'shorts', 'tags', 'tags/form', 'users',
    'works',
]

DELETE_ENDPOINTS = ['bookseries', 'editions', 'people', 'shorts', 'tags']


@pytest.fixture
def admin_client(api_client):
    """Get an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.mark.parametrize('endpoint', GET_ENDPOINTS)
def test_get_missing_record_returns_404(api_client, endpoint):
    response = api_client.get(f'/api/{endpoint}/{MISSING_ID}')
    assert response.status_code == 404
    assert response.json is not None and response.json.get('msg')


@pytest.mark.parametrize('endpoint', ['people', 'tags', 'users'])
def test_get_malformed_id_returns_400(api_client, endpoint):
    response = api_client.get(f'/api/{endpoint}/abc')
    assert response.status_code == 400


@pytest.mark.parametrize('endpoint', DELETE_ENDPOINTS)
def test_delete_missing_record_returns_404(admin_client, endpoint):
    response = admin_client.delete(f'/api/{endpoint}/{MISSING_ID}')
    assert response.status_code == 404
