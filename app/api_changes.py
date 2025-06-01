""" API related functions for changes."""
from typing import Any, Dict
from flask import Response, request

from app.api_errors import APIError
from app.api_helpers import make_api_response
from app.impl import ResponseType, get_changes
from app.impl_changes import change_delete, get_work_changes
from app.impl_people import get_person_changes
from app.types import HttpResponseCode
from app.api_jwt import jwt_admin_required

from app import app


@app.route('/api/work/<workid>/changes', methods=['get'])
def api_workchanges(workid: int) -> Response:
    """
    Get changes for a work.

    Args:
        workid (int): The ID of the work.

    Returns:
        Response: The API response containing the changes.
    """
    try:
        work_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {workid}.')
        response = ResponseType(f'Virheellinen tunniste: {workid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_work_changes(work_id))


@app.route('/api/person/<personid>/changes', methods=['get'])
def api_personchanges(personid: int) -> Response:
    """
    Get changes for a person.

    Args:
        personid (int): The ID of the person.

    Returns:
        Response: The API response containing the changes.
    """
    try:
        person_id = int(personid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {personid}.')
        response = ResponseType(f'Virheellinen tunniste: {personid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_person_changes(person_id))


@app.route('/api/changes/<changeid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_change_delete(changeid: str) -> Response:
    """
    Delete a change.

    Args:
        changeid (int): The ID of the change to be deleted.

    Returns:
        Response: The API response containing the result of the deletion.
    """
    try:
        change_id = int(changeid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {changeid}.')
        response = ResponseType(f'Virheellinen tunniste: {changeid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = change_delete(change_id)

    return make_api_response(retval)


@app.route('/api/changes', methods=['get'])
def api_changes() -> Response:
    """
    Get changes done to the data from the Log table.

    Parameters:
        None

    Returns:
        A tuple containing the response string and the HTTP status code.
    """
    url_params = request.args.to_dict()

    params: Dict[str, Any] = {}
    for (param, value) in url_params.items():
        # param, value = p.split('=')
        if value in ('null', 'undefined'):
            value = None
        params[param] = value

    try:
        retval = get_changes(params)
    except APIError as exp:
        app.logger.error(f'Exception in api_changes: {exp}')
        response = ResponseType(
            'api_changes: poikkeus.',
            status=HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        return make_api_response(response)

    return make_api_response(retval)
