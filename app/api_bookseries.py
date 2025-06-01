"""
API related functions for book series.
This module provides API endpoints for managing book series, including
listing, creating, updating, deleting, and filtering book series.
It includes route handlers for various HTTP methods and integrates with
the application's implementation layer to perform the necessary operations.
It also includes error handling and response formatting for API responses.
This module is part of the application's API and is used to interact with
the book series data in a structured manner.
"""

from jsonschema import validate
from app import app
from app.api_jwt import jwt_admin_required
from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_bookseries import (list_bookseries, bookseries_create,
                                 bookseries_update, bookseries_delete,
                                 get_bookseries, filter_bookseries)
from app.model import BookseriesSchema
from app.types import HttpResponseCode
import json
import jsonschema
import bleach
from flask import Response, request


@app.route('/api/bookseries', methods=['get'])
def api_listbookseries() -> Response:
    """
    This function is a route handler for the '/api/bookseries' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the list of book series.
    """
    return make_api_response(list_bookseries())


@app.route('/api/bookseries', methods=['post', 'put'])
@jwt_admin_required()   # type: ignore
def api_bookseriescreateupdate() -> Response:
    """
    Create or update a book series.

    This function is responsible for handling the '/api/bookseries' endpoint
    with both 'POST' and 'PUT' methods. It expects a JSON payload containing
    the book series data.

    Parameters:
        None

    Returns:
        Response: The API response containing the result of the operation.

    Raises:
        None
    """
    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error('api_bookseriescreateupdate: Invalid JSON.')
        response = ResponseType(
            'api_bookseriescreateupdate: Virheelliset parametrit.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    try:
        validate(instance=params, schema=BookseriesSchema)
    except jsonschema.exceptions.ValidationError:
        app.logger.error('api_bookseriescreateupdate: Invalid JSON.')
        response = ResponseType(
            'api_bookseriescreateupdate: Virheelliset parametrit.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    if request.method == 'POST':
        retval = make_api_response(bookseries_create(params))
    elif request.method == 'PUT':
        retval = make_api_response(bookseries_update(params))
    else:
        app.logger.error(
            f'api_bookseriescreateupdate: Invalid method {request.method}.')
        response = ResponseType(
            'api_bookseriescreateupdate: Virheellinen metodin kutsu.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return retval


@app.route('/api/bookseries/<bookseriesid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_bookseriesdelete(bookseriesid: str) -> Response:
    """
    Delete a book series by its ID.

    Args:
        bookseriesId (str): The ID of the book series to be deleted.

    Returns:
        Response: The API response indicating the success or failure of the
                  deletion.
    """
    return make_api_response(bookseries_delete(bookseriesid))


@app.route('/api/bookseries/<bookseriesid>', methods=['get'])
def api_getbookseries(bookseriesid: str) -> Response:
    """
    Get a book series by its ID.

    Args:
        bookseriesId (str): The ID of the book series.

    Returns:
        Response: The response object containing the book series data.

    Raises:
        TypeError: If the book series ID is not a valid integer.
        ValueError: If the book series ID is not a valid integer.

    Example:
        >>> api_GetBookseries('123')
        <Response [200]>
    """

    try:
        int_id = int(bookseriesid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getbookseries: Invalid id {bookseriesid}.')
        response = ResponseType(
           f'api_getbookseries: Virheellinen tunniste {bookseriesid}.',
           status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_bookseries(int_id))


@app.route('/api/filter/bookseries/<pattern>', methods=['get'])
def api_filterbookseries(pattern: str) -> Response:
    """
    Filters book series based on a given pattern.

    Args:
        pattern (str): The pattern to filter the book series.

    Returns:
        Response: The response object containing the filtered book series.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterBookseries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    retval = filter_bookseries(pattern)
    return make_api_response(retval)
