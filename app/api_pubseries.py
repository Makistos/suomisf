""" API related functions to pubseries. """
import json
import bleach
from flask import Response, request
from app.api_helpers import make_api_response
from app.api_jwt import jwt_admin_required
from app.impl import ResponseType
from app.impl_pubseries import (list_pubseries, get_pubseries,
                                filter_pubseries, pubseries_create,
                                pubseries_delete, pubseries_update)

from app import app
from app.types import HttpResponseCode

###
# Pubseries related functions


@app.route('/api/pubseries', methods=['get'])
def api_listpubseries() -> Response:
    """
    This function is a route handler for the '/api/pubseries' endpoint. It
    accepts GET requests and returns a tuple containing a string and an
    integer. The string is the response body, and the integer is the HTTP
    status code.

    Parameters:
    - None

    Returns:
    - A tuple containing a string and an integer.
    """
    return make_api_response(list_pubseries())


@ app.route('/api/pubseries/<pubseriesid>', methods=['get'])
def api_getpubseries(pubseriesid: str) -> Response:
    """
    Retrieves a pubseries with the specified ID from the API.

    Args:
        pubseriesId (str): The ID of the pubseries to retrieve.

    Returns:
        Response: The response object containing the retrieved pubseries.

    Raises:
        ValueError: If the pubseries ID is invalid.

    """
    try:
        int_id = int(pubseriesid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {pubseriesid}.')
        response = ResponseType(
            f'Virheellinen tunniste {pubseriesid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_pubseries(int_id))


@app.route('/api/filter/pubseries/<pattern>', methods=['get'])
def api_filterpubseries(pattern: str) -> Response:
    """
    This function is a Flask route that filters publications based on a given
    pattern. It takes a string parameter `pattern` which is used to filter the
    publications. The function returns a Flask Response object.
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_pubseries(pattern)
    return make_api_response(retval)


@app.route('/api/pubseries', methods=['put', 'post'])
@ jwt_admin_required()  # type: ignore
def api_createupdatepubseries() -> Response:
    """
    This function is a route handler for the '/api/pubseries' endpoint. It
    accepts PUT and POST requests and returns a tuple containing a string and
    an integer. The string is the response body, and the integer is the HTTP
    status code.

    Parameters:
    - None

    Returns:
    - A tuple containing a string and a Http response code.
    """
    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error('Invalid JSON.')
        response = ResponseType(
            'Virheelliset parametrit.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    if request.method == 'POST':
        retval = make_api_response(pubseries_create(params))
    else:
        retval = make_api_response(pubseries_update(params))

    return retval


@app.route('/api/pubseries/<pubseriesid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deletepubseries(pubseriesid: str) -> Response:
    """
    This function is a route handler for the '/api/pubseries/<pubseriesid>'
    endpoint. It accepts DELETE requests and returns a tuple containing a
    string and an integer. The string is the response body, and the integer is
    the HTTP status code.

    Parameters:
    - None

    Returns:
    - A tuple containing a string and an integer.
    """
    try:
        int_id = int(pubseriesid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {pubseriesid}.')
        response = ResponseType(
            f'Virheellinen tunniste {pubseriesid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = make_api_response(
        pubseries_delete(int_id))

    return retval
