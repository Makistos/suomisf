""" API related functions for changes."""
from flask import Response

from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_changes import change_delete, get_work_changes
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