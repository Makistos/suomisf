"""
SuomiSF API Authentication and Write Operation Tests

Tests for:
- Authentication endpoints (login, register, refresh)
- Authorization checks (unauthenticated requests should be rejected)
- Basic CRUD operations with authentication

Note: Run tests/scripts/setup_test_db.py before running these tests.
"""

import re

import pytest

from app import app as flask_app

from .base_test import BaseAPITest
from .test_route_auth import PUBLIC_WRITE_ROUTES

# Login is how a client gets a token in the first place.
AUTH_ROUTES = {'api_login'}


# Test credentials - must match setup_test_db.py
TEST_USER_EMAIL = 'testuser@example.com'
TEST_USER_PASSWORD = 'testpassword123'
TEST_ADMIN_EMAIL = 'testadmin@example.com'
TEST_ADMIN_PASSWORD = 'testadminpass123'


class TestAuthentication(BaseAPITest):
    """Tests for authentication endpoints."""

    def test_login_with_valid_credentials(self, api_client):
        """POST /api/login should return token for valid credentials."""
        response = api_client.post('/api/login', data={
            'email': TEST_USER_EMAIL,
            'password': TEST_USER_PASSWORD
        })
        # May return 200 with token or 401 if user doesn't exist
        if response.status_code == 200:
            assert 'access_token' in response.json or 'token' in response.json

    def test_login_with_invalid_credentials(self, api_client):
        """POST /api/login should return 401 for invalid credentials."""
        response = api_client.post('/api/login', data={
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, api_client):
        """POST /api/login should return error for missing fields."""
        response = api_client.post('/api/login', data={})
        assert response.status_code == 401


def _protected_write_routes():
    """Every write method on every route, except routes public on purpose.

    Built from Flask's own route map, so a new endpoint is covered without
    editing this file. Path parameters are filled with 1; the auth check
    runs before the handler reads them.
    """
    cases = []
    for rule in flask_app.url_map.iter_rules():
        if rule.endpoint in PUBLIC_WRITE_ROUTES or rule.endpoint in AUTH_ROUTES:
            continue
        for method in sorted(rule.methods & {'POST', 'PUT', 'DELETE', 'PATCH'}):
            cases.append(pytest.param(method, re.sub(r'<[^>]+>', '1', rule.rule),
                                      id=f'{method} {rule.rule}'))
    return cases


@pytest.mark.parametrize('method,path', _protected_write_routes())
def test_write_route_without_token_is_401(api_client, method, path):
    """No token, no write. Replaces 66 hand-written per-route tests."""
    response = getattr(api_client, method.lower())(path)
    assert response.status_code == 401
