""" API functions related to publishers. """
import json
import bleach
from flask.wrappers import Response
from flask import request
from app.api_jwt import jwt_admin_required, optional_user_id
from app.impl import ResponseType
from app.impl_publishers import (publisher_add, publisher_delete,
                                 publisher_update,
                                 list_publishers, get_publisher,
                                 filter_publishers)
from app.api_helpers import make_api_response
from app.impl_publisherindex import publisher_index
from app.impl_publisherpage import publisher_editions, publisher_summary
from app.types import HttpResponseCode

from app import app


@app.route('/api/publishers', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_publishercreateupdate() -> Response:
    """
    Create or update a publisher.

    This function is responsible for handling the '/api/publishers/' endpoint
    requests with both 'POST' and 'PUT' methods. It expects the request data to
    be in JSON format and performs input validation using the `bleach` library.

    Parameters:
    - None

    Returns:
    - A `Response` object representing the API response.

    Raises:
    - None

    Tests:
        publisher_create: Create a new publisher
        publisher_similar_name: Create a new publisher with same name as
                                an existing publisher
        publisher_similar_fullname: Create a new publisher with same fullname
                                    as an existing publisher
        publisher_missing_name: Create a new publisher with missing name
        publisher_update: Update an existing publisher
        publisher_update_missing_id: Update a publisher with missing ID
    """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    if request.method == 'POST':
        retval = make_api_response(publisher_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(publisher_update(params))

    return retval


@app.route('/api/publishers', methods=['get'])
def api_listpublishers() -> Response:
    """
    This function is a route handler for the '/api/publishers' endpoint. It
    accepts GET requests and returns a tuple containing the response data and
    the HTTP status code.

    Parameters:
        None

    Returns:
        A tuple containing the response data and the HTTP status code.

    Tests:
        publisher_list_all: Get all publishers
    """
    return make_api_response(list_publishers())


@app.route('/api/publisherindex', methods=['get'])
def api_publisherindex() -> Response:
    """
    The light publisher list for the new list page: every publisher with
    its edition count, year span and magazines (with issue counts), not
    every edition as GET /api/publishers returns.

    Returns:
        {"total": int, "publishers": [...]}
    """
    return make_api_response(publisher_index())


@app.route('/api/publishers/<publisherid>/summary', methods=['get'])
def api_publishersummary(publisherid: str) -> Response:
    """
    The new publisher page's facts, series (with edition counts and years)
    and magazines (with issue counts and years).
    """
    # A logged-in user also gets how many of its printings they own; an
    # expired token gets 401 so the frontend renews it.
    return make_api_response(publisher_summary(publisherid,
                                               optional_user_id()))


@app.route('/api/publishers/<publisherid>/editions', methods=['get'])
def api_publishereditions(publisherid: str) -> Response:
    """
    One page of the publisher's editions for the new publisher page.

    Query parameters (all optional): q, year_min, year_max,
    sort (oldest|newest|title|author), page, rows (50|100|200).
    A logged-in user gets their own owned and wishlisted marks; an expired
    token gets 401 so the frontend renews it.
    """
    return make_api_response(publisher_editions(
        publisherid, request.args.to_dict(), optional_user_id()))


@app.route('/api/publishers/<publisherid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deletepublisher(publisherid: str) -> Response:
    """
    Delete a publisher.

    Parameters:
        publisherId (str): The ID of the publisher to be deleted.

    Returns:
        Response: The API response.

    Tests:
        publisher_delete: Delete an existing publisher
        publisher_invalid_id: Try to delete a publisher with invalid id
    """
    try:
        int_id = int(publisherid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {publisherid}.')
        response = ResponseType(
            f'Virheellinen tunniste {publisherid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(publisher_delete(int_id))


@app.route('/api/publishers/<publisherid>', methods=['get'])
def api_getpublisher(publisherid: str) -> Response:
    """
    Retrieves a publisher from the API based on the provided publisher ID.

    Parameters:
        publisherid (str): The ID of the publisher to retrieve.

    Returns:
        ResponseType: The response object containing the publisher data or an
        error message.

    Tests:
        publisher_get: Get an existing publisher
        publisher_invalid_id: Try to get a publisher with invalid id
    """
    try:
        int_id = int(publisherid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {publisherid}.')
        response = ResponseType(
            f'Virheellinen tunniste {publisherid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_publisher(int_id))


@app.route('/api/filter/publishers/<pattern>', methods=['get'])
def api_filterpublishers(pattern: str) -> Response:
    """
    Filter publishers based on a given pattern.

    Args:
        pattern (str): The pattern to filter publishers.

    Returns:
        Response: The response containing the filtered publishers.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    retval = filter_publishers(pattern)
    return make_api_response(retval)
