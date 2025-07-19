""" Issue related API functions
"""

import json
from flask.wrappers import Response
from flask import request

from app.api_helpers import make_api_response
from app.impl_issues import (get_issue, get_issue_tags, issue_add,
                             issue_articles_get, issue_articles_save,
                             issue_delete, issue_image_add, issue_image_delete,
                             issue_shorts_get,
                             issue_shorts_save,
                             issue_tag_add,
                             issue_tag_remove, issue_update, publication_sizes)
from app.impl_contributors import (get_issue_contributors,
                                   update_issue_contributors)
from app.api_jwt import jwt_admin_required
from app.types import HttpResponseCode
from app.impl import ResponseType
from app import app


@app.route('/api/issues/<issueid>', methods=['get'])
def api_getissueformagazine(issueid: str) -> Response:
    """
    Get the issue for a magazine.

    Args:
        issueId (str): The ID of the issue.

    Returns:
        Response: The response object containing the issue data.
    """

    try:
        int_id = int(issueid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getissueformagazine: Invalid id {issueid}.')
        response = ResponseType(
            f'api_getissueformagazine: Virheellinen tunniste {issueid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_issue(int_id))


@app.route('/api/issues', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_createupdateissue() -> Response:
    """
    Create or update an issue in the API.

    This function is responsible for handling the '/api/issues' endpoint with
    both 'POST' and 'PUT' methods. It expects a JSON payload containing the
    issue data.

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
        app.logger.error('Invalid JSON.')
        response = ResponseType(
            'Virheelliset parametrit.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    if request.method == 'POST':
        retval = make_api_response(issue_add(params))
    else:
        retval = make_api_response(issue_update(params))

    return retval


@app.route('/api/issues/<issueid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deleteissue(issueid: int) -> Response:
    """
    API endpoint for deleting an issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        Response: The API response.

    Raises:
        None
    """
    try:
        int_id = int(issueid)
    except (TypeError, ValueError):
        app.logger.error(f'api_deleteissue: Invalid id {issueid}.')
        response = ResponseType(
            f'api_deleteissue: Virheellinen tunniste {issueid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(issue_delete(int_id))


@app.route('/api/issues/<issueid>/shorts', methods=['get'])
def api_getissueshorts(issueid: int) -> Response:
    """
    Get the issue for a short story.

    Args:
        issueId (int): The ID of the issue.

    Returns:
        Response: The response object containing the issue data.
    """
    return make_api_response(issue_shorts_get(issueid))


@app.route('/api/issues/shorts', methods=['put'])
@jwt_admin_required()  # type: ignore
def api_addissueshorts() -> Response:
    """
    Add issues to a short story.

    This function is an API endpoint that handles 'PUT' requests to
    '/api/issues/shorts'. It requires admin authentication using JWT.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
    """
    params = json.loads(request.data.decode('utf-8'))
    return make_api_response(issue_shorts_save(params))


@app.route('/api/issues/<issueid>/articles', methods=['get'])
def api_getissuearticles(issueid: int) -> Response:
    """
    Get the issue for an article.

    Args:
        issueId (int): The ID of the issue.

    Returns:
        Response: The response object containing the issue data.
    """
    return make_api_response(issue_articles_get(issueid))


@app.route('/api/issues/articles', methods=['put'])
@jwt_admin_required()  # type: ignore
def api_addissuearticles() -> Response:
    """
    Add issues to an article.

    This function is an API endpoint that handles 'PUT' requests to
    '/api/issues/articles'. It requires admin authentication using JWT.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
    """
    params = json.loads(request.data.decode('utf-8'))
    return make_api_response(issue_articles_save(params))


@app.route('/api/issues/<issueid>/tags', methods=['get'])
def api_getissuetags(issue_id: str) -> Response:
    """
    Get the tags associated with a specific issue.

    Parameters:
        issueId (str): The ID of the issue.

    Returns:
        Response: The response containing the tags associated with the issue.
    """

    try:
        int_id = int(issue_id)
    except (ValueError, TypeError):
        app.logger.error(f'api_getissuetags: Invalid id {issue_id}.')
        response = ResponseType(
            f'api_getissuetags: Virheellinen tunniste {issue_id}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_issue_tags(int_id))


@app.route('/api/issue/<issueid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtoissue(issueid: int, tagid: int) -> Response:
    """
    API endpoint for adding or removing a tag from an issue.

    Args:
        id (int): The ID of the issue.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        None
    """
    func = None
    if request.method == 'PUT':
        func = issue_tag_add
    elif request.method == 'DELETE':
        func = issue_tag_remove
    else:
        app.logger.error(
            f'api_tagtoissue: Invalid request method {request.method}.')
        response = ResponseType(
            f'api_tagtoissue: Virheellinen pyyntömetodi {request.method}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    try:
        issue_id = int(issueid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={issueid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = func(issue_id, tag_id)

    return make_api_response(retval)


@app.route('/api/issues/sizes', methods=['get'])
def api_getissuesizes() -> Response:
    """
    Get the issue sizes.
    """
    return make_api_response(publication_sizes())


@app.route('/api/issues/<issueid>/covers', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_uploadissueimage(issueid: int) -> Response:
    """
    Uploads an image for a specific issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        Response: The response object containing the result of the image
                  upload.
    """
    try:
        file = request.files['file']
    except KeyError:
        app.logger.error('File not found.')
        response = ResponseType('Tiedosto puuttuu',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(issue_image_add(issueid, file))


@app.route('/api/issues/<issueid>/covers', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deleteissueimage(issueid: int) -> Response:
    """
    API endpoint for deleting an issue image.

    Args:
        id (int): The ID of the issue.

    Returns:
        Response: The API response.

    Raises:
        None
    """
    return make_api_response(issue_image_delete(issueid))


@app.route('/api/issues/<issueid>/contributors', methods=['get'])
def api_getissuecontributors(issueid: str) -> Response:
    """
    Get the contributors for an issue.

    Args:
        issueid (str): The ID of the issue.

    Returns:
        Response: The response object containing the issue contributors data.
    """
    try:
        int_id = int(issueid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getissuecontributors: Invalid id {issueid}.')
        response = ResponseType(
            f'api_getissuecontributors: Virheellinen tunniste {issueid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    from app.route_helpers import new_session
    session = new_session()
    try:
        return make_api_response(get_issue_contributors(session, int_id))
    finally:
        session.close()


@app.route('/api/issues/<issueid>/contributors', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_updateissuecontributors(issueid: str) -> Response:
    """
    Update the contributors for an issue.

    Args:
        issueid (str): The ID of the issue.

    Returns:
        Response: The response object containing the result of the operation.
    """
    try:
        int_id = int(issueid)
    except (TypeError, ValueError):
        app.logger.error(f'api_updateissuecontributors: Invalid id {issueid}.')
        response = ResponseType(
            f'api_updateissuecontributors: Virheellinen tunniste {issueid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error('api_updateissuecontributors: Invalid JSON.')
        response = ResponseType(
            'Virheelliset parametrit.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    from app.route_helpers import new_session
    session = new_session()
    try:
        success = update_issue_contributors(session, int_id, params)
        if success:
            response = ResponseType(
                'Kontribuuttorien päivitys onnistui.',
                status=HttpResponseCode.OK.value)
        else:
            response = ResponseType(
                'Kontribuuttorien päivitys epäonnistui.',
                status=HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        return make_api_response(response)
    finally:
        session.close()
