"""
SuomiSF API Person Image Tests

Tests for POST /api/person/<personid>/images endpoint.

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

# Person 1 is assumed to exist in the test DB
EXISTING_PERSON_ID = 1

NONEXISTENT_PERSON_ID = 999999999

IMAGE_SRC = 'https://example.com/image.jpg'
IMAGE_ATTR = 'Example attribution'
IMAGE_LICENSE = 'CC BY 4.0'


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

class TestPersonImageAdd(BaseAPITest):
    """Tests for POST /api/person/<personid>/images."""

    def test_add_image_returns_201(self, admin_client):
        """POST /api/person/<id>/images returns 201 on success."""
        response = admin_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={
                'src': IMAGE_SRC,
                'attr': IMAGE_ATTR,
                'license': IMAGE_LICENSE,
            }
        )
        response.assert_status(201)

    def test_add_image_returns_new_id(self, admin_client):
        """POST /api/person/<id>/images returns the new image id."""
        response = admin_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={'src': IMAGE_SRC}
        )
        response.assert_status(201)
        data = response.data
        assert data is not None
        image_id = int(data)
        assert image_id > 0

    def test_add_image_optional_fields_omitted(self, admin_client):
        """POST without attr and license still succeeds."""
        response = admin_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={'src': IMAGE_SRC}
        )
        response.assert_status(201)

    def test_add_multiple_images_same_person(self, admin_client):
        """Multiple images can be added for the same person."""
        resp1 = admin_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={'src': IMAGE_SRC + '?v=1'}
        )
        resp2 = admin_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={'src': IMAGE_SRC + '?v=2'}
        )
        resp1.assert_status(201)
        resp2.assert_status(201)
        id1 = int(resp1.data)
        id2 = int(resp2.data)
        assert id1 != id2

    def test_add_image_missing_src_returns_400(self, admin_client):
        """POST without src returns 400."""
        response = admin_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={'attr': IMAGE_ATTR}
        )
        response.assert_status(400)

    def test_add_image_nonexistent_person_returns_400(
            self, admin_client):
        """POST for non-existent person returns 400."""
        response = admin_client.post(
            f'/api/person/{NONEXISTENT_PERSON_ID}/images',
            data={'src': IMAGE_SRC}
        )
        response.assert_status(400)

    def test_add_image_invalid_person_id_returns_400(
            self, admin_client):
        """POST with non-integer person id returns 400."""
        response = admin_client.post(
            '/api/person/notanid/images',
            data={'src': IMAGE_SRC}
        )
        response.assert_status(400)

    def test_add_image_requires_auth(self, api_client):
        """POST /api/person/<id>/images requires authentication."""
        response = api_client.post(
            f'/api/person/{EXISTING_PERSON_ID}/images',
            data={'src': IMAGE_SRC}
        )
        assert response.status_code in [401, 403]
