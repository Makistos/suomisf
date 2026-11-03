"""
SuomiSF API Kirjasampo Integration Tests

Tests for:
  GET  /api/kirjasampo/tags
  GET  /api/work/<work_id>/tags/import/preview
  POST /api/work/<work_id>/tags/import
  GET  /api/tags/import/mappings

External HTTP calls are mocked so no network access is required.
Run tests/scripts/setup_test_db.py before running these tests.
"""

from typing import Optional
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

# Sections as the preview sees them: skipped sections, a film list,
# qualifiers, a name repeated in a second section.
PREVIEW_HTML = """
<html><body>
<div class="kulsa-field"><h2 class="kulsa-field-label">Tekijä</h2>
  <div class="kulsa-field-item"><a href="/a">Auel, Jean M.</a></div>
</div>
<div class="kulsa-field"><h2 class="kulsa-field-label">Aiheet ja teemat</h2>
  <div class="kulsa-field-item"><a href="/1">ki-prev-new (luokka)</a></div>
  <div class="kulsa-field-item"><a href="/2">KI-Prev-Match</a></div>
  <div class="kulsa-field-item"><a href="/3">ki-prev-omit</a></div>
  <div class="kulsa-field-item"><a href="/4">ki-prev-replace</a></div>
  <div class="kulsa-field-item"><a href="/5">ki-prev-onwork</a></div>
</div>
<div class="kulsa-field">
  <h2 class="kulsa-field-label">Kirjastonhoitaja suosittelee</h2>
  <div class="kulsa-field-item"><a href="/6">ki-prev-recommended</a></div>
</div>
<div class="kulsa-field">
  <h2 class="kulsa-field-label">Lisätietoa verkossa</h2>
  <div class="kulsa-field-item"><a href="/11">Wikipedia</a></div>
</div>
<div class="kulsa-field"><h2 class="kulsa-field-label">Palkinto</h2>
  <div class="kulsa-field-item"><a href="/10">Finlandia-palkinto</a></div>
</div>
<div class="kulsa-field"><h2 class="kulsa-field-label">Elokuvat</h2>
  <div class="kulsa-field-item"><a href="/7">Luolakarhut (1986)</a></div>
  <div class="kulsa-field-item"><a href="/8">Toinen elokuva (1990)</a></div>
</div>
<div class="kulsa-field"><h2 class="kulsa-field-label">Henkilöt, toimijat</h2>
  <div class="kulsa-field-item"><a href="/9">ki-prev-new</a></div>
</div>
</body></html>
""".encode("utf-8")

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


def _preview_url(work_id: int) -> str:
    return f"/api/work/{work_id}/tags/import/preview"


def _preview_items(data) -> dict:
    """Preview items by section, then by name."""
    return {
        g["section"]: {i["name"]: i for i in g["items"]} for g in data
    }


def _tag_type_id(admin_client, tag_id: int) -> int:
    from app.route_helpers import new_session
    from app.orm_decl import Tag
    return new_session().query(Tag).get(tag_id).type_id


def _kirjasampo_imported(admin_client, work_id: int):
    resp = admin_client.get(f"/api/works/{work_id}")
    resp.assert_status(200)
    return resp.data["kirjasampo_imported"]


def _create_tag(
    admin_client, name: str, cleanup_tags: Optional[list] = None
) -> int:
    """Create a tag and return its id. If cleanup_tags is given, the
    new id is tracked for teardown deletion (see the cleanup_tags
    fixture)."""
    resp = admin_client.post(
        "/api/tags",
        data={"data": {"name": name}},
    )
    assert resp.status_code == 201, (
        f"Failed to create tag '{name}': {resp.json}"
    )
    tag_id = int(resp.data["id"])
    if cleanup_tags is not None:
        cleanup_tags.append(tag_id)
    return tag_id


# -------------------------------------------------------------------
# Shared fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """Return an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def created_work(admin_client):
    """Create a fresh work; delete it after the test."""
    work_id = create_test_work(admin_client, EXISTING_PERSON_ID,
                               title="Kirjasampo Import Test Work")
    yield work_id
    delete_test_work(admin_client, work_id)


@pytest.fixture
def linked_work(admin_client, created_work):
    """created_work with a Kirjasampo link."""
    from app.route_helpers import new_session
    from app.orm_decl import WorkLink

    session = new_session()
    link = WorkLink(work_id=created_work, link=VALID_URL,
                    description="Kirjasampo")
    session.add(link)
    session.commit()
    yield created_work
    session = new_session()
    session.query(WorkLink).filter(
        WorkLink.work_id == created_work).delete(synchronize_session=False)
    session.commit()


@pytest.fixture(autouse=True)
def cleanup_tags():
    """Track tag ids created during a test and delete them (plus any
    remaining worktag/tag_import_replace references) directly after
    the test.

    Goes straight through the DB rather than DELETE /api/tags/<id>,
    which refuses to delete a tag still attached to a work - these are
    throwaway import-test tags, not something exercising that rule,
    and by teardown time created_work's own cleanup may or may not have
    already removed the link depending on fixture ordering.

    Also sweeps tag_import_replace/tag_import_omit rows left behind
    under this file's "ki-*" test-name convention: replace/omit
    mappings are keyed by the external name, not the tag's id, so a
    fresh id-based cleanup wouldn't catch e.g. the "ki-clear-omit"
    omit-then-add sequence's leftover omit row on its own.
    """
    from app.route_helpers import new_session
    from app.orm_decl import Tag, WorkTag, TagImportReplace, TagImportOmit

    created_ids: list = []
    yield created_ids
    session = new_session()
    session.query(TagImportReplace).filter(
        TagImportReplace.name.like('ki-%')).delete(
            synchronize_session=False)
    session.query(TagImportOmit).filter(
        TagImportOmit.name.like('ki-%')).delete(synchronize_session=False)
    if created_ids:
        session.query(WorkTag).filter(
            WorkTag.tag_id.in_(created_ids)).delete(
                synchronize_session=False)
        session.query(TagImportReplace).filter(
            TagImportReplace.tag_id.in_(created_ids)).delete(
                synchronize_session=False)
        session.query(Tag).filter(
            Tag.id.in_(created_ids)).delete(synchronize_session=False)
    session.commit()


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
        self, admin_client, created_work, cleanup_tags
    ):
        """POST with action=add returns 200."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-add-basic", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        cleanup_tags.append(resp.data[0]["tag_id"])

    def test_add_action_creates_tag_and_reports_added(
        self, admin_client, created_work, cleanup_tags
    ):
        """action=add creates the tag if new and reports status added."""
        resp = _post_import(admin_client, created_work, [
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
        cleanup_tags.append(result["tag_id"])

    def test_add_action_reuses_existing_tag(
        self, admin_client, created_work, cleanup_tags
    ):
        """action=add for a name that already exists reuses that tag."""
        tag_id = _create_tag(
            admin_client, "ki-reuse-existing", cleanup_tags)
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-reuse-existing", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        result = resp.data[0]
        assert result["tag_id"] == tag_id
        assert result["status"] == "added"

    def test_already_present_not_duplicated(
        self, admin_client, created_work, cleanup_tags
    ):
        """Importing the same tag twice reports already_present."""
        first = _post_import(admin_client, created_work, [
            {"name": "ki-dup-tag", "id": None, "action": "add"},
        ])
        cleanup_tags.append(first.data[0]["tag_id"])
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-dup-tag", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "already_present"

    def test_replace_action_uses_mapped_tag(
        self, admin_client, created_work, cleanup_tags
    ):
        """action=replace adds the tag identified by id, not by name."""
        tag_id = _create_tag(
            admin_client, "ki-replace-target", cleanup_tags)
        resp = _post_import(admin_client, created_work, [
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
        self, admin_client, created_work
    ):
        """action=omit reports omitted and does not add to work."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-omit-tag", "id": None, "action": "omit"},
        ])
        resp.assert_status(200)
        result = resp.data[0]
        assert result["effective_action"] == "omit"
        assert result["tag_id"] is None
        assert result["status"] == "omitted"

    def test_null_action_defaults_to_add(
        self, admin_client, created_work, cleanup_tags
    ):
        """No action specified for unknown name defaults to add."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-no-action-tag", "id": None, "action": None},
        ])
        resp.assert_status(200)
        assert resp.data[0]["effective_action"] == "add"
        assert resp.data[0]["status"] == "added"
        cleanup_tags.append(resp.data[0]["tag_id"])

    def test_auto_resolves_omit_from_mapping(
        self, admin_client, created_work
    ):
        """Name previously omitted is auto-omitted when action absent."""
        # Store the omit mapping
        _post_import(admin_client, created_work, [
            {"name": "ki-auto-omit", "id": None, "action": "omit"},
        ])
        # New import without explicit action — should auto-omit
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-auto-omit", "id": None, "action": None},
        ])
        resp.assert_status(200)
        assert resp.data[0]["effective_action"] == "omit"
        assert resp.data[0]["status"] == "omitted"

    def test_auto_resolves_replace_from_mapping(
        self, admin_client, created_work, cleanup_tags
    ):
        """Name with stored replace mapping is auto-replaced."""
        tag_id = _create_tag(
            admin_client, "ki-auto-replace-target", cleanup_tags)
        _post_import(admin_client, created_work, [
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
        self, admin_client, created_work, cleanup_tags
    ):
        """action=add for a previously omitted name removes the omit."""
        _post_import(admin_client, created_work, [
            {"name": "ki-clear-omit", "id": None, "action": "omit"},
        ])
        # Re-import with add — should clear the omit
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-clear-omit", "id": None, "action": "add"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["effective_action"] == "add"
        assert resp.data[0]["status"] == "added"
        cleanup_tags.append(resp.data[0]["tag_id"])
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
        self, admin_client, created_work, cleanup_tags
    ):
        """Multiple items in one request all appear in the response."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-multi-1", "id": None, "action": "add"},
            {"name": "ki-multi-2", "id": None, "action": "omit"},
        ])
        resp.assert_status(200)
        assert len(resp.data) == 2
        statuses = {r["name"]: r["status"] for r in resp.data}
        assert statuses["ki-multi-1"] == "added"
        assert statuses["ki-multi-2"] == "omitted"
        added = next(
            r for r in resp.data if r["name"] == "ki-multi-1")
        cleanup_tags.append(added["tag_id"])


class TestWorkTagImportErrors(BaseAPITest):
    """Tests for error cases of the tag import endpoint."""

    def test_nonexistent_work_returns_400(self, admin_client):
        """Import into a non-existent work returns 400."""
        resp = _post_import(admin_client, 999999999, [
            {"name": "any-tag", "id": None, "action": "add"},
        ])
        resp.assert_status(400)

    def test_empty_body_returns_400(self, admin_client, created_work):
        """Empty body returns 400."""
        resp = _post_import(admin_client, created_work, None)
        resp.assert_status(400)

    def test_non_array_json_returns_400(
        self, admin_client, created_work
    ):
        """JSON object (not array) body returns 400."""
        resp = _post_import(
            admin_client, created_work,
            {"name": "tag", "action": "add"},
        )
        resp.assert_status(400)

    def test_replace_without_id_returns_error_item(
        self, admin_client, created_work
    ):
        """action=replace with null id returns an error entry."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-err-replace", "id": None, "action": "replace"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "error"

    def test_replace_nonexistent_id_returns_error_item(
        self, admin_client, created_work
    ):
        """action=replace with a non-existent tag id returns error."""
        resp = _post_import(admin_client, created_work, [
            {
                "name": "ki-bad-id",
                "id": 999999999,
                "action": "replace",
            },
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "error"

    def test_invalid_action_returns_error_item(
        self, admin_client, created_work
    ):
        """An unknown action value returns an error entry."""
        resp = _post_import(admin_client, created_work, [
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

    def test_response_has_replace_and_omit_keys(self, admin_client):
        """GET /api/tags/import/mappings returns 200 for admin.

        Also checks:
        - Response contains 'replace' and 'omit' keys.
        """
        resp = admin_client.get("/api/tags/import/mappings")
        resp.assert_status(200)
        resp.assert_status(200)
        data = resp.data
        assert "replace" in data
        assert "omit" in data
        assert isinstance(data["replace"], list)
        assert isinstance(data["omit"], list)

    def test_replace_entries_have_required_fields(
        self, admin_client, created_work, cleanup_tags
    ):
        """Each replace entry has name, tag_id, and tag_name."""
        tag_id = _create_tag(
            admin_client, "ki-map-replace-tgt", cleanup_tags)
        _post_import(admin_client, created_work, [
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
        self, admin_client, created_work
    ):
        """Names omitted during import appear in the omit list."""
        _post_import(admin_client, created_work, [
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


# ===================================================================
# GET /api/work/<work_id>/tags/import/preview
# ===================================================================

class TestWorkTagImportPreview(BaseAPITest):
    """Tests for the import preview."""

    @patch("app.impl_kirjasampo.requests.get")
    def test_applies_import_rules_in_page_order(
        self, mock_get, admin_client, linked_work
    ):
        """Skipped sections are left out, films become "elokuva" and
        qualifiers are stripped; sections keep page order."""
        mock_get.return_value = _make_mock_response(PREVIEW_HTML)
        resp = admin_client.get(_preview_url(linked_work))
        resp.assert_status(200)
        assert mock_get.call_args.args[0] == VALID_URL
        assert [g["section"] for g in resp.data] == [
            "Aiheet ja teemat", "Elokuvat", "Henkilöt, toimijat"]
        items = _preview_items(resp.data)
        assert list(items["Aiheet ja teemat"]) == [
            "ki-prev-new", "ki-prev-match", "ki-prev-omit",
            "ki-prev-replace", "ki-prev-onwork"]
        assert items["Aiheet ja teemat"]["ki-prev-new"]["raw_name"] == (
            "ki-prev-new (luokka)")
        assert list(items["Elokuvat"]) == ["elokuva"]
        # The same name in another section is listed there too.
        assert list(items["Henkilöt, toimijat"]) == ["ki-prev-new"]

    @patch("app.impl_kirjasampo.requests.get")
    def test_reports_mappings_matches_and_tags_on_work(
        self, mock_get, admin_client, linked_work, cleanup_tags
    ):
        """Each item tells its stored mapping, the existing tag it
        matches and whether the work has it already."""
        match_id = _create_tag(admin_client, "ki-PREV-match", cleanup_tags)
        target_id = _create_tag(
            admin_client, "ki-prev-replace-target", cleanup_tags)
        resp = _post_import(admin_client, linked_work, [
            {"name": "ki-prev-omit", "action": "omit"},
            {"name": "ki-prev-replace", "id": target_id,
             "action": "replace"},
            {"name": "ki-prev-onwork", "action": "add"},
        ])
        resp.assert_status(200)
        onwork_id = resp.data[2]["tag_id"]
        cleanup_tags.append(onwork_id)

        mock_get.return_value = _make_mock_response(PREVIEW_HTML)
        resp = admin_client.get(_preview_url(linked_work))
        resp.assert_status(200)
        items = _preview_items(resp.data)["Aiheet ja teemat"]

        new = items["ki-prev-new"]
        assert new["mapping"] is None
        assert new["match"] is None
        assert new["on_work"] is False

        match = items["ki-prev-match"]
        assert match["match"]["id"] == match_id
        assert match["match"]["type"]["id"] == 1
        assert match["on_work"] is False

        assert items["ki-prev-omit"]["mapping"] == {"action": "omit"}

        replace = items["ki-prev-replace"]
        assert replace["mapping"]["action"] == "replace"
        assert replace["mapping"]["tag"]["id"] == target_id
        # The replace target was added to the work.
        assert replace["on_work"] is True

        onwork = items["ki-prev-onwork"]
        assert onwork["match"]["id"] == onwork_id
        assert onwork["on_work"] is True

    @patch("app.impl_kirjasampo.requests.get")
    def test_page_without_tags_gives_empty_list(
        self, mock_get, admin_client, linked_work
    ):
        """A Kirjasampo page with no tags is an empty preview."""
        mock_get.return_value = _make_mock_response(
            b"<html><body><p>Ei tunnisteita</p></body></html>")
        resp = admin_client.get(_preview_url(linked_work))
        resp.assert_status(200)
        assert resp.data == []

    @patch("app.impl_kirjasampo.requests.get")
    def test_dead_kirjasampo_page_is_an_error(
        self, mock_get, admin_client, linked_work
    ):
        """A missing Kirjasampo page is an error, not an empty preview."""
        mock_get.return_value = _make_mock_response(b"", status_code=404)
        resp = admin_client.get(_preview_url(linked_work))
        resp.assert_status(500)

    def test_work_without_kirjasampo_link_returns_400(
        self, admin_client, created_work
    ):
        """The preview needs the work's Kirjasampo link."""
        resp = admin_client.get(_preview_url(created_work))
        resp.assert_status(400)

    def test_requires_admin_auth(self, api_client):
        """Unauthenticated GET returns 401 or 403."""
        resp = api_client.get(_preview_url(1))
        assert resp.status_code in (401, 403)


# ===================================================================
# POST /api/work/<work_id>/tags/import — types, matching, import date
# ===================================================================

class TestWorkTagImportTypesAndDate(BaseAPITest):
    """Tag types of new tags, exact name matching and the import date."""

    def test_type_id_is_used_for_new_tags(
        self, admin_client, created_work, cleanup_tags
    ):
        """A new tag gets the type the item names."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-type-new", "action": "add", "type_id": 5},
        ])
        resp.assert_status(200)
        tag_id = resp.data[0]["tag_id"]
        cleanup_tags.append(tag_id)
        assert resp.data[0]["status"] == "added"
        assert _tag_type_id(admin_client, tag_id) == 5

    def test_new_tags_default_to_aihe(
        self, admin_client, created_work, cleanup_tags
    ):
        """Without type_id a new tag is an Aihe."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-type-default", "action": "add"},
        ])
        resp.assert_status(200)
        tag_id = resp.data[0]["tag_id"]
        cleanup_tags.append(tag_id)
        assert _tag_type_id(admin_client, tag_id) == 1

    def test_existing_tag_keeps_its_type(
        self, admin_client, created_work, cleanup_tags
    ):
        """type_id never retypes an existing tag."""
        tag_id = _create_tag(admin_client, "ki-type-existing", cleanup_tags)
        before = _tag_type_id(admin_client, tag_id)
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-type-existing", "action": "add", "type_id": 5},
        ])
        resp.assert_status(200)
        assert resp.data[0]["tag_id"] == tag_id
        assert _tag_type_id(admin_client, tag_id) == before

    @pytest.mark.parametrize("bad_type", [9999, "abc"])
    def test_unknown_type_id_is_an_error_item(
        self, admin_client, created_work, bad_type
    ):
        """An unknown type_id fails that item only."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-type-bad", "action": "add", "type_id": bad_type},
        ])
        resp.assert_status(200)
        assert resp.data[0]["status"] == "error"
        assert "tag_id" not in resp.data[0]

    def test_names_match_exactly(
        self, admin_client, created_work, cleanup_tags
    ):
        """_ and % in a name aren't wildcards: a near-miss name creates
        a new tag instead of reusing another one."""
        other_id = _create_tag(admin_client, "ki-exactxname", cleanup_tags)
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-exact_name", "action": "add"},
            {"name": "ki-exact%", "action": "add"},
        ])
        resp.assert_status(200)
        ids = [r["tag_id"] for r in resp.data]
        cleanup_tags.extend(ids)
        assert other_id not in ids
        assert ids[0] != ids[1]

    def test_names_match_ignoring_case(
        self, admin_client, created_work, cleanup_tags
    ):
        """An existing tag is reused whatever its case."""
        tag_id = _create_tag(admin_client, "KI-Case-Tag", cleanup_tags)
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-case-tag", "action": "add"},
        ])
        resp.assert_status(200)
        assert resp.data[0]["tag_id"] == tag_id

    def test_empty_list_records_import_date(
        self, admin_client, created_work
    ):
        """Saving with nothing to import still marks the work imported."""
        assert _kirjasampo_imported(admin_client, created_work) is None
        resp = _post_import(admin_client, created_work, [])
        resp.assert_status(200)
        assert resp.data == []
        assert _kirjasampo_imported(admin_client, created_work) is not None

    def test_omit_only_records_import_date(
        self, admin_client, created_work
    ):
        """Skipping every tag still marks the work imported."""
        resp = _post_import(admin_client, created_work, [
            {"name": "ki-date-omit", "action": "omit"},
        ])
        resp.assert_status(200)
        assert _kirjasampo_imported(admin_client, created_work) is not None
