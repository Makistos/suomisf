""" Issue related API functions
"""

from flask.wrappers import Response
from flask import request

from app.api_helpers import make_api_response
from app.impl_issues import (get_issue, get_issue_tags, issue_tag_add,
                             issue_tag_remove)
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


@ app.route('/api/issues/<issueid>/tags', methods=['get'])
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
    if request.method == 'PUT':
        func = issue_tag_add
    elif request.method == 'DELETE':
        func = issue_tag_remove

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
