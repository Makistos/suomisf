"""API endpoints for maintaining work link sources (admin only).

A work link's source is its description ("Kansalliskirjasto",
"Wikipedia", ...). These endpoints list the sources and fix mistyped
ones by renaming, combining or deleting them.
"""

import json

from flask import Response, request

from app import app
from app.api_helpers import make_api_response
from app.api_jwt import jwt_admin_required
from app.impl import ResponseType
from app.impl_links import (worklink_source_delete, worklink_source_links,
                            worklink_sources, worklink_sources_merge)
from app.types import HttpResponseCode


def _json_body() -> dict | None:
    try:
        body = json.loads(request.data.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return None
    return body if isinstance(body, dict) else None


def _bad_request(msg: str) -> Response:
    return make_api_response(
        ResponseType(msg, HttpResponseCode.BAD_REQUEST.value))


@app.route('/api/worklinks/sources', methods=['get'])
@jwt_admin_required()  # type: ignore
def api_worklink_sources() -> Response:
    """
    List the distinct work link sources.

    URL: GET /api/worklinks/sources

    Authentication: Admin JWT required.

    Response 200 — most used first; links without a source have
    "source": null:
        [{"source": "Kansalliskirjasto", "count": 1968, "works": 1950}, ...]
    """
    return make_api_response(worklink_sources())


@app.route('/api/worklinks/sources/links', methods=['get'])
@jwt_admin_required()  # type: ignore
def api_worklink_source_links() -> Response:
    """
    List the work links that have a source.

    URL: GET /api/worklinks/sources/links?source=<source>

    Authentication: Admin JWT required.

    Query parameters:
        source (str): The source; empty or missing for links without one.

    Response 200:
        [{"id": 1, "link": "https://...", "work_id": 2,
          "work_title": "..."}, ...]
    """
    return make_api_response(
        worklink_source_links(request.args.get('source')))


@app.route('/api/worklinks/sources/merge', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_worklink_sources_merge() -> Response:
    """
    Rename a source, or combine several sources into one.

    URL: POST /api/worklinks/sources/merge

    Authentication: Admin JWT required.

    Request body:
        {"sources": ["Kansallikirjasto", "Kansalliskirjasato"],
         "target": "Kansalliskirjasto"}

        sources: sources to replace (null for links without a source).
        target: the source they all get; may be one of sources or a new
                name.

    Response 200: {"updated": <number of links changed>}
    Response 400: missing sources or target.
    """
    body = _json_body()
    if body is None:
        return _bad_request('Virheellinen pyyntö.')
    sources = body.get('sources')
    target = body.get('target')
    if not isinstance(sources, list) or not isinstance(target, str) or \
            not all(s is None or isinstance(s, str) for s in sources):
        return _bad_request('sources (lista) ja target (merkkijono) '
                            'vaaditaan.')
    return make_api_response(worklink_sources_merge(sources, target))


@app.route('/api/worklinks/sources/delete', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_worklink_source_delete() -> Response:
    """
    Delete every work link that has a source.

    URL: POST /api/worklinks/sources/delete

    Authentication: Admin JWT required.

    Request body: {"source": "URS_Maailmanloppu.pdf"} (null for links
    without a source).

    Response 200: {"deleted": <number of links deleted>}
    """
    body = _json_body()
    if body is None or 'source' not in body:
        return _bad_request('source vaaditaan.')
    return make_api_response(worklink_source_delete(body['source']))
