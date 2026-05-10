"""API endpoints for kirjasampo.fi integration."""

import json

from flask import Response, request

from app import app
from app.api_helpers import make_api_response
from app.api_jwt import jwt_admin_required
from app.impl import ResponseType
from app.impl_kirjasampo import (
    get_import_mappings,
    kirjasampo_tags,
    work_import_tags,
)
from app.types import HttpResponseCode


@app.route("/api/kirjasampo/tags", methods=["GET"])
def api_kirjasampo_tags() -> Response:
    """
    Fetch all tags from a kirjasampo.fi work page.

    URL: GET /api/kirjasampo/tags

    Authentication: None required.

    Query parameters:
        url (str): Full URL of the kirjasampo.fi work page.

    Response 200 — JSON object mapping section label to tag list:
        {
          "Kirjallisuudenlaji": ["filosofiset romaanit", ...],
          "Aiheet ja teemat": ["elämän tarkoitus", ...],
          "Henkilöt, toimijat": ["kirjastonhoitajat", ...],
          "Päähenkilöt": ["Tamura, Kafka"],
          "Konkreettiset tapahtumapaikat": ["Japani", ...],
          "Alkukieli": ["japani"],
          ...
        }

    Response 400 — Missing or invalid URL parameter.
    Response 404 — Page found but contains no tag sections.
    Response 500 — Remote fetch failed or unexpected error.

    Example:
        GET /api/kirjasampo/tags?url=https://www.kirjasampo.fi/fi/
            kulsa/kauno%3Aateos_11973
    """
    url = request.args.get("url", "").strip()
    if not url:
        return make_api_response(
            ResponseType(
                "Pakollinen parametri 'url' puuttuu.",
                HttpResponseCode.BAD_REQUEST,
            )
        )
    return make_api_response(kirjasampo_tags(url))


@app.route("/api/work/<int:work_id>/tags/import", methods=["POST"])
@jwt_admin_required()  # type: ignore
def api_work_import_tags(work_id: int) -> Response:
    """
    Import a list of tags into a work (admin only).

    URL: POST /api/work/<work_id>/tags/import

    Authentication: Admin JWT required.

    Path parameters:
        work_id (int): ID of the work to add tags to.

    Request body — JSON array of tag import items:
        [
          {
            "name":   "maaginen realismi",
            "id":     null,
            "action": "add"
          },
          {
            "name":   "kehitysromaanit",
            "id":     42,
            "action": "replace"
          },
          {
            "name":   "japaninkielinen kirjallisuus",
            "id":     null,
            "action": "omit"
          },
          {
            "name":   "rakkauskertomukset",
            "id":     null,
            "action": null
          }
        ]

    Fields per item:
        name (str):       Tag name as it appears in the external source.
        id (int | null):  ID of an existing local tag. Required for
                          action "replace".
        action (str | null): One of "add", "replace", "omit", or
                          null/omitted to auto-resolve from stored
                          mappings (defaults to "add" for unknown names).

    Actions:
        add     Look up or create a tag by name, add it to the work.
                Clears any stored replace/omit mapping for this name.
        replace Use the existing tag identified by id instead of name.
                Stores the mapping so future imports without an explicit
                action apply it automatically.
                Clears any stored omit mapping for this name.
        omit    Do not add a tag for this name to the work.
                Stores the decision so future imports skip it
                automatically. Un-omit by sending with "add" or
                "replace".

    Response 200 — JSON array with one result object per input item:
        [
          {
            "name":             "maaginen realismi",
            "effective_action": "add",
            "tag_id":           123,
            "status":           "added"
          },
          ...
        ]

    Status values:
        added           Tag was added to the work.
        already_present Tag was already on the work (no duplicate added).
        omitted         Tag was skipped per the omit action.
        error           Item could not be processed (see "error" field).

    Response 400 — Work not found or request body is not valid JSON.
    Response 401/403 — Authentication required.
    Response 500 — Database error.
    """
    try:
        items = json.loads(request.data.decode("utf-8"))
        if not isinstance(items, list):
            raise ValueError("body must be a JSON array")
    except (ValueError, TypeError) as exc:
        return make_api_response(
            ResponseType(
                f"Virheellinen pyyntö: {exc}",
                HttpResponseCode.BAD_REQUEST,
            )
        )

    return make_api_response(work_import_tags(work_id, items))


@app.route("/api/tags/import/mappings", methods=["GET"])
@jwt_admin_required()  # type: ignore
def api_get_import_mappings() -> Response:
    """
    Return all stored tag import replace and omit mappings (admin only).

    URL: GET /api/tags/import/mappings

    Authentication: Admin JWT required.

    Response 200 — JSON object:
        {
          "replace": [
            {
              "name":     "kehitysromaanit",
              "tag_id":   42,
              "tag_name": "coming-of-age novels"
            },
            ...
          ],
          "omit": [
            "japaninkielinen kirjallisuus",
            ...
          ]
        }

    Response 500 — Database error.
    """
    return make_api_response(get_import_mappings())
