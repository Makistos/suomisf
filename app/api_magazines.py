""" API related functions for magazines.
"""

import json
from typing import Tuple
from flask import Response, request
from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_magazines import (add_magazine, delete_magazine, get_magazine_types, list_magazines,
                                get_magazine, update_magazine)
from app.types import HttpResponseCode
from app.api_jwt import jwt_admin_required

from app import app

###
# Magazine related functions


@ app.route('/api/magazines', methods=['get'])
def api_listmagazines() -> Response:
    """
    Retrieves a list of magazines from the API.

    Returns:
        Response: The response object containing the list of magazines.

    Tests:
        list_magazines: List existing magazines
    """

    return make_api_response(list_magazines())


@ app.route('/api/magazines/<magazineid>', methods=['get'])
def api_getmagazine(magazineid: str) -> Response:
    """
    Get a magazine by its ID.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Response: The response object containing the magazine data.

    Raises:
        ValueError: If the magazine ID is invalid.

    Tests:
        get_magazine: Get existing magazine
        get_magazine_invalid_id: Try id which is not a number
        get_magazine_unknown_id: Try id not existing in db
    """

    try:
        int_id = int(magazineid)
    except (ValueError, TypeError):
        app.logger.error(f'api_GetMagazine: Invalid id {magazineid}.')
        response = ResponseType(
            f'api_GetMagazine: Virheellinen tunniste {magazineid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_magazine(int_id))


@app.route('/api/magazines', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_magazinecreateupdate() -> Response:
    """
    Create or update a magazine.

    This function is responsible for handling the '/api/magazines' endpoint
    requests with both 'POST' and 'PUT' methods. It expects the request data
    to be in JSON format and performs input validation using the `bleach`
    library.

    Parameters:
    - None

    Returns:
    - A `Response` object representing the API response.

    Raises:
    - None

    Tests:
    - create_magazine: Create new magazine
    - update_magazine: Update existing magazine
    - update_magazine_invalid_type: Type is not 0 or 1
    - update_magazine_type_not_number: Type is not a number
    """
    retval = Response()

    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error(f'Invalid JSON: {request.data}.')
        response = ResponseType(
            f'Virheellinen JSON: {request.data}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    if request.method == 'POST':
        retval = make_api_response(add_magazine(params))
    elif request.method == 'PUT':
        retval = make_api_response(update_magazine(params))

    return retval


@app.route('/api/magazines/<magazineid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deletemagazine(magazineid: str) -> Response:
    """
    Delete a magazine.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        value.

    Raises:
        ValueError: If the magazine ID is invalid.

    Tests:
        delete_magazine: Delete existing magazine
        delete_magazine_unknown_id: Try id not existing in db
        delete_magazine_invalid_id: Try id which is not a number
    """
    try:
        int_id = int(magazineid)
    except (ValueError, TypeError):
        app.logger.error(f'Invalid id {magazineid}.')
        response = ResponseType(
            f'Virheellinen tunniste {magazineid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(delete_magazine(int_id))


@ app.route('/api/magazines/<magazineid>/publisher', methods=['get'])
def api_getmagazinepublisher(magazineid: str) -> Tuple[str, int]:
    """
    Get the publisher of a magazine.

    Args:
        magazineid (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazinePublisher(options)


@ app.route('/api/magazines/<magazineid>/tags', methods=['get'])
def api_getmagazinetags(magazineid: str) -> Tuple[str, int]:
    """
    Get the tags associated with a specific magazine.

    Args:
        magazineid (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        value.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazineTags(options)


@app.route('/api/magazinetypes', methods=['get'])
def api_getmagazinetypes() -> Response:
    """
    Get the magazine types.

    Returns:
        Response: The response object containing the magazine types.

    Tests:
        get_magazine_types: Get magazine types
    """
    return make_api_response(get_magazine_types())
