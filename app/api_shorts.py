###
# Story related functions


import json
from flask import Response, request
from app.api_helpers import make_api_response
from app.api_jwt import jwt_admin_required
from app.types import HttpResponseCode

from app import app
from app.impl import ResponseType
from app.impl_shorts import (get_latest_shorts, story_tag_add,
                             story_tag_remove, story_updated,
                             story_add, story_delete, get_short, search_shorts,
                             get_short_types)


@app.route('/api/shorts', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_shortcreateupdate() -> Response:
    """
    Create or update a short story.

    This function is an API endpoint that handles both POST and PUT requests to
    '/api/shorts'. It requires admin authentication using JWT.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
    """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    if request.method == 'POST':
        retval = make_api_response(story_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(story_updated(params))
    else:
        app.logger.error(
            f'api_shortcreateupdate: Invalid method {request.method}.')
        response = ResponseType(
            'api_shortcreateupdate: Virheellinen metodin kutsu.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return retval


@app.route('/api/shorts/<shortid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_shortdelete(shortid: int) -> Response:
    """
    Delete a short by its ID.

    Parameters:
        id (int): The ID of the short to be deleted.

    Returns:
        Response: The response object containing the result of the deletion.
    """
    try:
        short_id = int(shortid)
    except (TypeError, ValueError):
        app.logger.error(
            f'api_shortdelete: Invalid id. id={shortid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = story_delete(short_id)

    return make_api_response(retval)


@app.route('/api/shorts/<shortid>', methods=['get'])
def api_getshort(shortid: str) -> Response:
    """
    Retrieves a short by its ID.

    Args:
        shortid (str): The ID of the short.

    Returns:
        Response: The response object containing the short.
    """
    try:
        int_id = int(shortid)
    except (ValueError, TypeError):
        app.logger.error(f'api_GetShort: Invalid id {shortid}.')
        response = ResponseType(
            f'api_GetShort: Virheellinen tunniste {shortid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_short(int_id))


@app.route('/api/searchshorts', methods=['post'])
def api_searchshorts() -> Response:
    """
    A function that handles the '/api/searchshorts' endpoint for the API.

    This function is triggered when a POST request is made to the
    '/api/searchshorts' endpoint. It expects a JSON payload in the request body
    containing search parameters.

    Parameters:
        None

    Returns:
        Response: The response object containing the search results.

    Raises:
        None
    """
    # st = time.time()
    params = json.loads(request.data)
    retval = search_shorts(params)
    # et = time.time()
    # elapsed = str(et-st)
    # app.logger.warn('SearchShorts: done in ' + elapsed + " s")
    return make_api_response(retval)


@app.route('/api/shorttypes', methods=['get'])
def api_shorttypes() -> Response:
    """
    Retrieves the short types from the API.

    Returns:
        Response: The API response containing the short types.
    """
    return make_api_response(get_short_types())


@app.route('/api/story/<storyid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtostory(storyid: int, tagid: int) -> Response:
    """
    API endpoint for adding or removing a tag from a story.

    Args:
        id (int): The ID of the story.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        TypeError: If the ID or tag ID is not an integer.
        ValueError: If the ID or tag ID is not a valid integer.
    """
    func = None
    if request.method == 'PUT':
        func = story_tag_add
    elif request.method == 'DELETE':
        func = story_tag_remove
    else:
        app.logger.error(
            f'api_tagtostory: Invalid request method {request.method}.')
        response = ResponseType(
            f'api_tagtostory: Virheellinen pyyntömetodi {request.method}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    try:
        int_id = int(storyid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={storyid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = func(int_id, tag_id)

    return make_api_response(retval)


@app.route('/api/latest/shorts/<count>', methods=['get'])
def api_latestshorts(count: int) -> Response:
    """
    Get the latest shorts.

    Args:
        count (int): The number of shorts to return.

    Returns:
        Response: The response object containing the list of latest shorts.

    Raises:
        None
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        app.logger.error(f'api_latestshorts: Invalid count {count}.')
        response = ResponseType(
            f'api_latestshorts: Virheellinen maara {count}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_latest_shorts(count))
