"""
SuomiSF API Kirjasampo Integration Tests

Tests for:
  GET  /api/kirjasampo/tags
  POST /api/work/<work_id>/tags/import
  GET  /api/tags/import/mappings

External HTTP calls are mocked so no network access is required.
Run tests/scripts/setup_test_db.py before running these tests.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from .base_test import BaseAPITest
from .test_works import (
    TEST_ADMIN_NAME,
    TEST_ADMIN_PASSWORD,
    create_test_work,
    delete_test_work,
)

# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

VALID_URL = "https://www.kirjasampo.fi/fi/kulsa/kauno%3Aateos_11973"

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

# person_id=1 is assumed to exist in the test DB
EXISTING_PERSON_ID = 1


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _make_mock_response(content: bytes, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.content = content
    return mock


def _import_url(work_id: int) -> str:
    return f"/api/work/{work_id}/tags/import"


def _post_import(client, work_id: int, items) -> object:
    return client.post(_import_url(work_id), data=items)


def _create_tag(admin_client, name: str) -> int:
    """Create a tag and return its id."""
    resp = admin_client.post(
        "/api/tags",
        data={"data": {"name": name}},
    )
    assert resp.status_code == 201, (
        f"Failed to create tag '{name}': {resp.json}"
    )
    return int(resp.data["id"])


# -------------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """Return an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def test_work(admin_client):
    """Create a fresh work; delete it after the test."""
    work_id = create_test_work(admin_client, EXISTING_PERSON_ID,
                               title="Kirjasampo Import Test Work")
    yield work_id
    delete_test_work(admin_client, work_id)


# ===================================================================
# GET /api/kirjasampo/tags
# ===================================================================

class TestKirjasampoTagsSuccess(BaseAPITest):
    """Tests for successful tag retrieval from kirjasampo.fi."""

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
        assert isinstance(data, dict), "Response should be a dict"
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
        for label, tags in response.data.items():
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
        """Sections that have no <a> items are not included."""
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
        assert "EmptySection" not in response.data
        assert "RealSection" in response.data


class TestKirjasampoTagsErrors(BaseAPITest):
    """Tests for error cases of the kirjasampo tag fetch endpoint."""

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


# ===================================================================
# POST /api/work/<work_id>/tags/import
# ===================================================================

class TestWorkTagImportSuccess(BaseAPITest):
    """Tests for successful tag import into a work."""

    def test_add_action_returns_200(
        self, admin_client, test_work
    ):
        """POST with action=add returns 200."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-add-basic", "id": None, "action": "add"},
        ])
        resp.assert_status(200)

    def test_add_action_creates_tag_and_reports_added(
        self, admin_client, test_work
    ):
        """action=add creates the tag if new and reports status added."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-add-new-tag", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        results = resp.data
        assert isinstance(results, list)
        result = results[0]
        assert result["name"] == "ki-add-new-tag"
        assert result["effective_action"] == "add"
        assert isinstance(result["tag_id"], int)
        assert result["status"] == "added"

    def test_add_action_reuses_existing_tag(
        self, admin_client, test_work
    ):
        """action=add for a name that already exists reuses that tag."""
        tag_id = _create_tag(admin_client, "ki-reuse-existing")
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-reuse-existing", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        result = resp.data[0]
        assert result["tag_id"] == tag_id
        assert result["status"] == "added"

    def test_already_present_not_duplicated(
        self, admin_client, test_work
    ):
        """Importing the same tag twice reports already_present."""
        _post_import(admin_client, test_work, [
            {"name": "ki-dup-tag", "id": None, "action": "add"},
        ])
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-dup-tag", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "already_present"

    def test_replace_action_uses_mapped_tag(
        self, admin_client, test_work
    ):
        """action=replace adds the tag identified by id, not by name."""
        tag_id = _create_tag(admin_client, "ki-replace-target")
        resp = _post_import(admin_client, test_work, [
            {
                "name": "ki-replace-source",
                "id": tag_id,
                "action": "replace",
            },
        ])
        resp.assert_status(200)
        result = resp.data[0]
        assert result["effective_action"] == "replace"
        assert result["tag_id"] == tag_id
        assert result["status"] == "added"

    def test_omit_action_skips_tag(
        self, admin_client, test_work
    ):
        """action=omit reports omitted and does not add to work."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-omit-tag", "id": None, "action": "omit"},
        ])
        resp.assert_status(200)
        result = resp.data[0]
        assert result["effective_action"] == "omit"
        assert result["tag_id"] is None
        assert result["status"] == "omitted"

    def test_null_action_defaults_to_add(
        self, admin_client, test_work
    ):
        """No action specified for unknown name defaults to add."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-no-action-tag", "id": None, "action": None},
        ])
        resp.assert_status(200)
        assert resp.data[0]["effective_action"] == "add"
        assert resp.data[0]["status"] == "added"

    def test_auto_resolves_omit_from_mapping(
        self, admin_client, test_work
    ):
        """Name previously omitted is auto-omitted when action absent."""
        # Store the omit mapping
        _post_import(admin_client, test_work, [
            {"name": "ki-auto-omit", "id": None, "action": "omit"},
        ])
        # New import without explicit action — should auto-omit
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-auto-omit", "id": None, "action": None},
        ])
        resp.assert_status(200)
        assert resp.data[0]["effective_action"] == "omit"
        assert resp.data[0]["status"] == "omitted"

    def test_auto_resolves_replace_from_mapping(
        self, admin_client, test_work
    ):
        """Name with stored replace mapping is auto-replaced."""
        tag_id = _create_tag(admin_client, "ki-auto-replace-target")
        _post_import(admin_client, test_work, [
            {
                "name": "ki-auto-replace-src",
                "id": tag_id,
                "action": "replace",
            },
        ])
        # Second work — same name, no action
        work2 = create_test_work(
            admin_client, EXISTING_PERSON_ID,
            title="Kirjasampo Import Test Work 2"
        )
        try:
            resp = _post_import(admin_client, work2, [
                {"name": "ki-auto-replace-src",
                 "id": None, "action": None},
            ])
            resp.assert_status(200)
            result = resp.data[0]
            assert result["effective_action"] == "replace"
            assert result["tag_id"] == tag_id
        finally:
            delete_test_work(admin_client, work2)

    def test_add_clears_omit_mapping(
        self, admin_client, test_work
    ):
        """action=add for a previously omitted name removes the omit."""
        _post_import(admin_client, test_work, [
            {"name": "ki-clear-omit", "id": None, "action": "omit"},
        ])
        # Re-import with add — should clear the omit
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-clear-omit", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["effective_action"] == "add"
        assert resp.data[0]["status"] == "added"
        # Now auto-resolve should not omit
        work2 = create_test_work(
            admin_client, EXISTING_PERSON_ID,
            title="Kirjasampo Import Test Work 3"
        )
        try:
            resp2 = _post_import(admin_client, work2, [
                {"name": "ki-clear-omit", "id": None, "action": None},
            ])
            assert resp2.data[0]["effective_action"] == "add"
        finally:
            delete_test_work(admin_client, work2)

    def test_multiple_items_processed(
        self, admin_client, test_work
    ):
        """Multiple items in one request all appear in the response."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-multi-1", "id": None, "action": "add"},
            {"name": "ki-multi-2", "id": None, "action": "omit"},
        ])
        resp.assert_status(200)
        assert len(resp.data) == 2
        statuses = {r["name"]: r["status"] for r in resp.data}
        assert statuses["ki-multi-1"] == "added"
        assert statuses["ki-multi-2"] == "omitted"


class TestWorkTagImportErrors(BaseAPITest):
    """Tests for error cases of the tag import endpoint."""

    def test_nonexistent_work_returns_400(self, admin_client):
        """Import into a non-existent work returns 400."""
        resp = _post_import(admin_client, 999999999, [
            {"name": "any-tag", "id": None, "action": "add"},
        ])
        resp.assert_status(400)

    def test_empty_body_returns_400(self, admin_client, test_work):
        """Empty body returns 400."""
        resp = _post_import(admin_client, test_work, None)
        resp.assert_status(400)

    def test_non_array_json_returns_400(
        self, admin_client, test_work
    ):
        """JSON object (not array) body returns 400."""
        resp = _post_import(
            admin_client, test_work,
            {"name": "tag", "action": "add"},
        )
        resp.assert_status(400)

    def test_replace_without_id_returns_error_item(
        self, admin_client, test_work
    ):
        """action=replace with null id returns an error entry."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-err-replace", "id": None, "action": "replace"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "error"

    def test_replace_nonexistent_id_returns_error_item(
        self, admin_client, test_work
    ):
        """action=replace with a non-existent tag id returns error."""
        resp = _post_import(admin_client, test_work, [
            {
                "name": "ki-bad-id",
                "id": 999999999,
                "action": "replace",
            },
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "error"

    def test_invalid_action_returns_error_item(
        self, admin_client, test_work
    ):
        """An unknown action value returns an error entry."""
        resp = _post_import(admin_client, test_work, [
            {"name": "ki-bad-action", "id": None,
             "action": "invalidaction"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "error"

    def test_requires_admin_auth(self, api_client):
        """Unauthenticated POST returns 401 or 403."""
        resp = _post_import(api_client, 1, [
            {"name": "any-tag", "id": None, "action": "add"},
        ])
        assert resp.status_code in (401, 403)


# ===================================================================
# GET /api/tags/import/mappings
# ===================================================================

class TestGetImportMappings(BaseAPITest):
    """Tests for the stored tag import mappings endpoint."""

    def test_returns_200_for_admin(self, admin_client):
        """GET /api/tags/import/mappings returns 200 for admin."""
        resp = admin_client.get("/api/tags/import/mappings")
        resp.assert_status(200)

    def test_response_has_replace_and_omit_keys(self, admin_client):
        """Response contains 'replace' and 'omit' keys."""
        resp = admin_client.get("/api/tags/import/mappings")
        resp.assert_status(200)
        data = resp.data
        assert "replace" in data
        assert "omit" in data
        assert isinstance(data["replace"], list)
        assert isinstance(data["omit"], list)

    def test_replace_entries_have_required_fields(
        self, admin_client, test_work
    ):
        """Each replace entry has name, tag_id, and tag_name."""
        tag_id = _create_tag(admin_client, "ki-map-replace-tgt")
        _post_import(admin_client, test_work, [
            {
                "name": "ki-map-replace-src",
                "id": tag_id,
                "action": "replace",
            },
        ])
        resp = admin_client.get("/api/tags/import/mappings")
        resp.assert_status(200)
        entries = {
            e["name"]: e for e in resp.data["replace"]
        }
        assert "ki-map-replace-src" in entries
        entry = entries["ki-map-replace-src"]
        assert entry["tag_id"] == tag_id
        assert isinstance(entry["tag_name"], str)

    def test_omit_entries_appear_in_mapping(
        self, admin_client, test_work
    ):
        """Names omitted during import appear in the omit list."""
        _post_import(admin_client, test_work, [
            {
                "name": "ki-map-omit-name",
                "id": None,
                "action": "omit",
            },
        ])
        resp = admin_client.get("/api/tags/import/mappings")
        resp.assert_status(200)
        assert "ki-map-omit-name" in resp.data["omit"]

    def test_requires_admin_auth(self, api_client):
        """Unauthenticated GET returns 401 or 403."""
        resp = api_client.get("/api/tags/import/mappings")
        assert resp.status_code in (401, 403)
