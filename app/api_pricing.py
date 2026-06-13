"""API endpoints for Antikvaari pricing."""

import json

from flask import Response, request

from app import app
from app.api_helpers import make_api_response
from app.api_jwt import jwt_admin_required
from app.impl import ResponseType
from app.impl_pricing import (
    antikvaari_fetch_products,
    antikvaari_price_delete,
    antikvaari_prices_save,
    antikvaari_prices_save_all,
    antikvaari_search,
    edition_prices_count,
    edition_prices_get,
    price_add_manual,
    price_sources_get,
    scrape_price_from_url,
    user_collection_stats,
    work_product_delete,
    work_products_get,
    work_products_save,
)
from app.types import HttpResponseCode


@app.route('/api/antikvaari/search', methods=['GET'])
@jwt_admin_required()  # type: ignore
def api_antikvaari_search() -> Response:
    """
    Search Antikvaari for products matching a query (admin only).

    URL: GET /api/antikvaari/search

    Authentication: Admin JWT required.

    Query parameters:
        q    (str): Search term (title, author, …).
        isbn (str): Optional ISBN filter.

    Response 200 — JSON array of product objects:
        [
          {
            "product_id":      "62a38f38eaa1ec176c40b868",
            "title":           "Pimeät valovuodet",
            "author":          "Lem Stanislaw",
            "year":            "1982",
            "binding":         "Sidottu",
            "url":             "https://www.antikvaari.fi/teos/…",
            "image":           "https://…",
            "available_count": 3
          },
          …
        ]

    Response 400 — Missing query parameter.
    Response 500 — Antikvaari request failed.
    """
    q = request.args.get('q', '').strip()
    if not q:
        return make_api_response(
            ResponseType("Pakollinen parametri 'q' puuttuu.", HttpResponseCode.BAD_REQUEST)
        )
    isbn = request.args.get('isbn', '').strip()
    return make_api_response(antikvaari_search(q, isbn))


@app.route('/api/work/<int:work_id>/antikvaari/products', methods=['GET'])
@jwt_admin_required()  # type: ignore
def api_work_antikvaari_products_get(work_id: int) -> Response:
    """
    Return Antikvaari product IDs linked to a work (admin only).

    URL: GET /api/work/<work_id>/antikvaari/products

    Authentication: Admin JWT required.

    Response 200 — JSON array:
        [
          {
            "id":                    1,
            "antikvaari_product_id": "62a38f38eaa1ec176c40b868",
            "added":                 "2024-11-15T12:00:00"
          },
          …
        ]

    Response 404 — Work not found.
    """
    return make_api_response(work_products_get(work_id))


@app.route('/api/work/<int:work_id>/antikvaari/products', methods=['POST'])
@jwt_admin_required()  # type: ignore
def api_work_antikvaari_products_save(work_id: int) -> Response:
    """
    Link Antikvaari product IDs to a work (admin only).

    Existing mappings are preserved — this is additive only.

    URL: POST /api/work/<work_id>/antikvaari/products

    Authentication: Admin JWT required.

    Request body — JSON array of product ID strings:
        ["62a38f38eaa1ec176c40b868", "62a65ff6eaa1ec176c63eb99"]

    Response 200 — JSON object:
        {"added": 2}

    Response 400 — Request body is not a valid JSON array.
    Response 404 — Work not found.
    Response 500 — Database error.
    """
    try:
        body = json.loads(request.data.decode('utf-8'))
        if not isinstance(body, list):
            raise ValueError('body must be a JSON array')
        products = [
            item if isinstance(item, dict) else {'product_id': item, 'url': None}
            for item in body
        ]
    except (ValueError, TypeError) as exc:
        return make_api_response(
            ResponseType(f'Virheellinen pyyntö: {exc}', HttpResponseCode.BAD_REQUEST)
        )
    return make_api_response(work_products_save(work_id, products))


@app.route('/api/work/<int:work_id>/antikvaari/products/<product_id>', methods=['DELETE'])
@jwt_admin_required()  # type: ignore
def api_work_antikvaari_product_delete(work_id: int, product_id: str) -> Response:
    """
    Remove an Antikvaari product link from a work (admin only).

    URL: DELETE /api/work/<work_id>/antikvaari/products/<product_id>

    Response 200 — {"deleted": "<product_id>"}
    Response 404 — Product not found.
    Response 500 — Database error.
    """
    return make_api_response(work_product_delete(work_id, product_id))


@app.route('/api/work/<int:work_id>/antikvaari/fetch', methods=['POST'])
@jwt_admin_required()  # type: ignore
def api_work_antikvaari_fetch(work_id: int) -> Response:
    """
    Scrape Antikvaari product pages and return price rows (admin only).

    Rows are returned for inspection; nothing is persisted. Use
    POST /api/edition/<edition_id>/antikvaari/prices to save selected rows.

    URL: POST /api/work/<work_id>/antikvaari/fetch

    Authentication: Admin JWT required.

    Request body — JSON object:
        {
          "product_urls":    ["https://www.antikvaari.fi/teos/…"],
          "target_condition": "K3"
        }

    Fields:
        product_urls (list[str]): Antikvaari product page URLs to scrape.
        target_condition (str):   Optional. Your copy's condition (e.g. "K3")
                                  used for match quality comparison.

    Response 200 — JSON array of price row dicts, one per physical book copy:
        [
          {
            "edition_id":                4987,
            "antikvaari_book_id":        "6197d6feb8b7303195c91487",
            "antikvaari_product_id":     "62a38f38eaa1ec176c40b868",
            "antikvaari_product_year":   1982,
            "antikvaari_product_binding": "Sidottu, kuvakansi",
            "antikvaari_product_version": 1,
            "date_listed":               "2021-11-19",
            "last_updated":              "2022-11-05T20:17:10",
            "condition":                 "K3",
            "is_library_discard":        false,
            "has_markings":              false,
            "missing_dust_cover":        false,
            "price":                     10.0,
            "match_quality":             "Perfect"
          },
          …
        ]

    Response 400 — Missing or invalid request body.
    Response 404 — Work not found.
    Response 500 — Fetch error.
    """
    try:
        body = json.loads(request.data.decode('utf-8'))
        product_urls = body.get('product_urls', [])
        if not isinstance(product_urls, list) or not product_urls:
            raise ValueError("'product_urls' must be a non-empty list")
    except (ValueError, TypeError) as exc:
        return make_api_response(
            ResponseType(f'Virheellinen pyyntö: {exc}', HttpResponseCode.BAD_REQUEST)
        )
    target_condition = body.get('target_condition') or None
    return make_api_response(
        antikvaari_fetch_products(product_urls, work_id, target_condition)
    )


@app.route('/api/edition/<int:edition_id>/antikvaari/prices', methods=['POST'])
@jwt_admin_required()  # type: ignore
def api_edition_antikvaari_prices_save(edition_id: int) -> Response:
    """
    Append scraped price rows for an edition (admin only).

    Each call always inserts new rows — prices are never updated or deleted.

    URL: POST /api/edition/<edition_id>/antikvaari/prices

    Authentication: Admin JWT required.

    Request body — JSON array of price row dicts (as returned by the fetch
    endpoint). Only rows whose edition_id matches the path parameter are saved.

    Response 200 — JSON object:
        {"saved": 3}

    Response 400 — Request body is not a valid JSON array.
    Response 404 — Edition not found.
    Response 500 — Database error.
    """
    try:
        rows = json.loads(request.data.decode('utf-8'))
        if not isinstance(rows, list):
            raise ValueError('body must be a JSON array')
    except (ValueError, TypeError) as exc:
        return make_api_response(
            ResponseType(f'Virheellinen pyyntö: {exc}', HttpResponseCode.BAD_REQUEST)
        )
    return make_api_response(antikvaari_prices_save(edition_id, rows))


@app.route('/api/edition/<int:edition_id>/antikvaari/prices/count', methods=['GET'])
def api_edition_antikvaari_prices_count(edition_id: int) -> Response:
    """
    Return the number of stored Antikvaari price rows for an edition.

    URL: GET /api/edition/<edition_id>/antikvaari/prices/count

    Response 200 — {"count": N}
    """
    return make_api_response(edition_prices_count(edition_id))


@app.route('/api/edition/<int:edition_id>/antikvaari/prices', methods=['GET'])
@jwt_admin_required()  # type: ignore
def api_edition_antikvaari_prices_get(edition_id: int) -> Response:
    """
    Return stored Antikvaari price rows for an edition (admin only).

    URL: GET /api/edition/<edition_id>/antikvaari/prices

    Authentication: Admin JWT required.

    Query parameters:
        target_condition (str): Optional. Your copy's condition (e.g. "K3")
                                used for match quality calculation.

    Response 200 — JSON array of stored price rows, each with match_quality.
    Response 404 — Edition not found.
    """
    target_condition = request.args.get('target_condition', '').strip() or None
    return make_api_response(edition_prices_get(edition_id, target_condition))


@app.route('/api/price-sources', methods=['GET'])
@jwt_admin_required()  # type: ignore
def api_price_sources_get() -> Response:
    """Return all price sources for use in dropdowns."""
    return make_api_response(price_sources_get())


@app.route('/api/edition/<int:edition_id>/prices/manual', methods=['POST'])
@jwt_admin_required()  # type: ignore
def api_edition_price_add_manual(edition_id: int) -> Response:
    """Insert a manually entered price row for an edition."""
    data = request.get_json(force=True) or {}
    return make_api_response(price_add_manual(edition_id, data))


@app.route('/api/prices/scrape-url', methods=['POST'])
@jwt_admin_required()  # type: ignore
def api_prices_scrape_url() -> Response:
    """Scrape price fields from a supported second-hand bookshop URL."""
    data = request.get_json(force=True) or {}
    url = (data.get('url') or '').strip()
    if not url:
        from app.impl import ResponseType
        from app.types import HttpResponseCode
        return make_api_response(ResponseType('url required', HttpResponseCode.BAD_REQUEST))
    return make_api_response(scrape_price_from_url(url))


@app.route('/api/antikvaari/prices/<int:price_id>', methods=['DELETE'])
@jwt_admin_required()  # type: ignore
def api_antikvaari_price_delete(price_id: int) -> Response:
    """
    Delete a single stored Antikvaari price row (admin only).

    URL: DELETE /api/antikvaari/prices/<price_id>

    Authentication: Admin JWT required.

    Response 200 — {"deleted": <price_id>}
    Response 404 — Price not found.
    Response 500 — Database error.
    """
    return make_api_response(antikvaari_price_delete(price_id))


@app.route('/api/work/<int:work_id>/antikvaari/prices', methods=['POST'])
@jwt_admin_required()  # type: ignore
def api_work_antikvaari_prices_save(work_id: int) -> Response:
    """
    Save all fetched price rows for a work (admin only).

    Accepts rows as returned by the fetch endpoint and saves them grouped by
    edition_id. Rows with no edition_id are silently skipped. Change detection
    applies: unchanged rows are not re-inserted.

    URL: POST /api/work/<work_id>/antikvaari/prices

    Authentication: Admin JWT required.

    Request body — JSON array of price row dicts (as returned by the fetch endpoint).

    Response 200 — JSON object:
        {"saved": 5, "skipped": 2}

    Response 400 — Request body is not a valid JSON array.
    Response 500 — Database error.
    """
    try:
        rows = json.loads(request.data.decode('utf-8'))
        if not isinstance(rows, list):
            raise ValueError('body must be a JSON array')
    except (ValueError, TypeError) as exc:
        return make_api_response(
            ResponseType(f'Virheellinen pyyntö: {exc}', HttpResponseCode.BAD_REQUEST)
        )
    return make_api_response(antikvaari_prices_save_all(work_id, rows))


@app.route('/api/user/<int:user_id>/collection/stats', methods=['GET'])
def api_user_collection_stats(user_id: int) -> Response:
    """
    Return Antikvaari pricing statistics for all editions owned by a user.

    URL: GET /api/user/<user_id>/collection/stats

    Response 200 — JSON object:
        {
          "total_owned": 42,
          "priced_count": 28,
          "total_value": 385.50,
          "quality_distribution": {
            "Perfect": 15, "Good": 8, "Decent": 3, "Poor": 2, "not_priced": 14
          },
          "top_expensive": [
            {"edition_id": 123, "work_id": 45, "title": "...", "author_str": "...",
             "pubyear": 1975, "version": null, "price": 45.00,
             "match_quality": "Perfect", "condition": "K3"},
            ...
          ]
        }
    """
    return make_api_response(user_collection_stats(user_id))
