"""
SuomiSF API Kirjasampo Tag Fetch Tests

Tests for GET /api/kirjasampo/tags endpoint.

Note: External HTTP calls are mocked so no network access is required.
Run tests/scripts/setup_test_db.py before running these tests.
"""

from unittest.mock import MagicMock, patch

import requests

from .base_test import BaseAPITest

VALID_URL = (
    "https://www.kirjasampo.fi/fi/kulsa/kauno%3Aateos_11973"
)

MINIMAL_HTML = b"""
<html>
<body>
<div class="kulsa-field">
  <h2 class="kulsa-field-label kulsa-field-label-genre">
    Kirjallisuudenlaji
  </h2>
  <div class="kulsa-field-items">
    <div class="kulsa-field-item even first">
      <a href="/fi/search/kulsa/obj1">maaginen realismi</a>
    </div>
    <div class="kulsa-field-item odd">
      <a href="/fi/search/kulsa/obj2">kehitysromaanit</a>
    </div>
  </div>
</div>
<div class="kulsa-field">
  <h2 class="kulsa-field-label kulsa-field-label-theme">
    Aiheet ja teemat
  </h2>
  <div class="kulsa-field-items">
    <div class="kulsa-field-item even first">
      <a href="/fi/search/kulsa/obj3">identiteetti</a>
    </div>
  </div>
</div>
</body>
</html>
"""


def _make_mock_response(content: bytes, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.content = content
    return mock


class TestKirjasampoTagsSuccess(BaseAPITest):
    """Tests for successful tag retrieval."""

    @patch("app.impl_kirjasampo.requests.get")
    def test_returns_200_for_valid_url(self, mock_get, api_client):
        """GET /api/kirjasampo/tags returns 200 for a valid URL."""
        mock_get.return_value = _make_mock_response(MINIMAL_HTML)
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(200)

    @patch("app.impl_kirjasampo.requests.get")
    def test_returns_dict_with_section_keys(self, mock_get, api_client):
        """Response is a dict keyed by section labels."""
        mock_get.return_value = _make_mock_response(MINIMAL_HTML)
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(200)
        data = response.data
        assert isinstance(data, dict), (
            "Response should be a dict"
        )
        assert "Kirjallisuudenlaji" in data
        assert "Aiheet ja teemat" in data

    @patch("app.impl_kirjasampo.requests.get")
    def test_section_values_are_lists_of_strings(
        self, mock_get, api_client
    ):
        """Each section value is a list of strings."""
        mock_get.return_value = _make_mock_response(MINIMAL_HTML)
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(200)
        data = response.data
        for label, tags in data.items():
            assert isinstance(tags, list), (
                f"Section '{label}' should be a list"
            )
            for tag in tags:
                assert isinstance(tag, str), (
                    f"Tag in '{label}' should be a string"
                )

    @patch("app.impl_kirjasampo.requests.get")
    def test_tag_values_are_correct(self, mock_get, api_client):
        """Parsed tag values match the mock HTML content."""
        mock_get.return_value = _make_mock_response(MINIMAL_HTML)
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(200)
        data = response.data
        assert "maaginen realismi" in data["Kirjallisuudenlaji"]
        assert "kehitysromaanit" in data["Kirjallisuudenlaji"]
        assert "identiteetti" in data["Aiheet ja teemat"]

    @patch("app.impl_kirjasampo.requests.get")
    def test_sections_without_links_are_omitted(
        self, mock_get, api_client
    ):
        """Sections that have no <a> tag items are not included."""
        html = b"""
        <html><body>
        <div class="kulsa-field">
          <h2 class="kulsa-field-label">EmptySection</h2>
          <div class="kulsa-field-items"></div>
        </div>
        <div class="kulsa-field">
          <h2 class="kulsa-field-label">RealSection</h2>
          <div class="kulsa-field-items">
            <div class="kulsa-field-item">
              <a href="/x">tagi</a>
            </div>
          </div>
        </div>
        </body></html>
        """
        mock_get.return_value = _make_mock_response(html)
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(200)
        data = response.data
        assert "EmptySection" not in data
        assert "RealSection" in data


class TestKirjasampoTagsErrors(BaseAPITest):
    """Tests for error cases."""

    def test_missing_url_returns_400(self, api_client):
        """GET /api/kirjasampo/tags without url returns 400."""
        response = api_client.get("/api/kirjasampo/tags")
        response.assert_status(400)

    def test_empty_url_returns_400(self, api_client):
        """GET /api/kirjasampo/tags with empty url returns 400."""
        response = api_client.get("/api/kirjasampo/tags?url=")
        response.assert_status(400)

    def test_non_kirjasampo_url_returns_400(self, api_client):
        """URL not on kirjasampo.fi is rejected with 400."""
        response = api_client.get(
            "/api/kirjasampo/tags?url=https://example.com/page"
        )
        response.assert_status(400)

    def test_invalid_url_scheme_returns_400(self, api_client):
        """Non-http(s) URL is rejected with 400."""
        response = api_client.get(
            "/api/kirjasampo/tags"
            "?url=ftp://www.kirjasampo.fi/fi/kulsa/x"
        )
        response.assert_status(400)

    def test_plaintext_non_url_returns_400(self, api_client):
        """Arbitrary string is rejected with 400."""
        response = api_client.get(
            "/api/kirjasampo/tags?url=not-a-url"
        )
        response.assert_status(400)

    @patch("app.impl_kirjasampo.requests.get")
    def test_remote_error_returns_500(self, mock_get, api_client):
        """Network error from requests results in 500."""
        mock_get.side_effect = requests.RequestException("timeout")
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(500)

    @patch("app.impl_kirjasampo.requests.get")
    def test_upstream_404_returns_500(self, mock_get, api_client):
        """kirjasampo.fi returning non-200 results in 500."""
        mock_get.return_value = _make_mock_response(b"", 404)
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(500)

    @patch("app.impl_kirjasampo.requests.get")
    def test_page_with_no_tags_returns_404(
        self, mock_get, api_client
    ):
        """Page that contains no kulsa-field sections returns 404."""
        mock_get.return_value = _make_mock_response(
            b"<html><body><p>Nothing here</p></body></html>"
        )
        response = api_client.get(
            f"/api/kirjasampo/tags?url={VALID_URL}"
        )
        response.assert_status(404)
