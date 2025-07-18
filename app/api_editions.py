###
# Edition related functions

from flask import Response, request
import json
from flask_jwt_extended import jwt_required
from app.api_helpers import make_api_response
from app.api_jwt import jwt_admin_required
from app.impl import ResponseType
from app.impl_editions import (
    create_edition, edition_delete, edition_image_upload, edition_image_delete,
    edition_shorts,
    editionowner_list, editionowner_get, editionowner_getowned,
    editionowner_remove, editionowner_add, editionowner_update, get_edition,
    get_latest_editions,
    update_edition
)
from app import app
from app.impl_logs import get_edition_changes
from app.types import HttpResponseCode
from app.api_helpers import validate_positive_integer_id


@app.route('/api/editions/<editionid>', methods=['get'])
def api_getedition(editionid: str) -> Response:
    """
    Get an edition by its ID.

    Args:
        editionId (str): The ID of the edition.

    Returns:
        Response: The response object containing the edition data.

    Raises:
        TypeError: If the edition ID is not a valid integer.
        ValueError: If the edition ID is not a valid integer.

    Example:
        >>> api_GetEdition('123')
        <Response [200]>
    """
    try:
        int_id = int(editionid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getedition: Invalid id {editionid}.')
        response = ResponseType(
           f'api_getedition: Virheellinen tunniste {editionid}.',
           status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_edition(int_id))


@app.route('/api/editions', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_editioncreateupdate() -> Response:
    """
    Create or update an edition using the provided API endpoint.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API request.
    """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    if request.method == 'POST':
        retval = make_api_response(create_edition(params))
    elif request.method == 'PUT':
        retval = make_api_response(update_edition(params))
    else:
        app.logger.error(
            f'api_editioncreateupdate: Invalid method {request.method}.')
        response = ResponseType(
            'api_editioncreateupdate: Virheellinen metodin kutsu.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return retval


@app.route('/api/editions/<editionid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_editiondelete(editionid: str) -> Response:
    """
    Delete an edition.

    Parameters:
        editionId (str): The ID of the edition to be deleted.

    Returns:
        Response: The API response.
    """
    return make_api_response(edition_delete(editionid))


@app.route('/api/editions/<editionid>/images', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_uploadeditionimage(editionid: str) -> Response:
    """
    Uploads an image for a specific edition.

    Args:
        id (str): The ID of the edition.

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

    retval = make_api_response(
        edition_image_upload(editionid, file))
    return retval


@app.route('/api/editions/<edition_id>/changes', methods=['get'])
def api_editionchanges(edition_id: int) -> Response:
    """
    Get changes for an edition.

    Args:
        edition_id (int): The ID of the edition.

    Returns:
        Response: The API response containing the changes.
    """
    return make_api_response(get_edition_changes(edition_id))


@app.route('/api/editions/<editionid>/images/<imageid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deleteeditionimage(editionid: str, imageid: str) -> Response:
    """
    Delete an edition image.

    Args:
        id (str): The ID of the edition.
        imageid (str): The ID of the image.

    Returns:
        Response: The response object containing the result of the deletion.
    """
    retval = make_api_response(
        edition_image_delete(editionid, imageid))
    return retval


@app.route('/api/editions/<editionid>/owners', methods=['get'])
def api_editionowners(editionid: str) -> Response:
    """
    Get the owners of an edition.

    Args:
        editionid (str): The ID of the edition.

    Returns:
        Response: The API response containing the owners of the edition.
    """
    (ed_id, err) = validate_positive_integer_id(editionid, "painosid")

    if err:
        app.logger.error(f'api_editionowners: {err.response}')
        return make_api_response(err)
    elif ed_id is None:
        app.logger.error('api_editionowners: Invalid editionid.')
        response = ResponseType(
            'api_editionowners: Virheellinen painosid.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(editionowner_list(ed_id))


@app.route('/api/editions/<editionid>/owner/<personid>', methods=['get'])
def api_editionownerperson(editionid: str, personid: str) -> Response:
    """
    Get the owner info of an edition.

    Args:
        editionid (str): The ID of the edition.
        personid (str): The ID of the person.

    Returns:
        Response: The API response containing the owner information.
    """
    # personid is valid, proceed to get the owner info
    (person_id, err) = validate_positive_integer_id(personid, "henkiloid")
    (ed_id, err2) = validate_positive_integer_id(editionid, "painosid")
    if err:
        app.logger.error(f'api_editionownerperson: {err.response}')
        return make_api_response(err)
    if err2:
        app.logger.error(f'api_editionownerperson: {err2.response}')
        return make_api_response(err2)
    elif person_id is None or ed_id is None:
        app.logger.error('api_editionownerperson: '
                         'Invalid editionid or personid.')
        response = ResponseType(
            'api_editionownerperson: Virheellinen painosid tai henkilotunnus.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    app.logger.info(f'api_editionownerperson: Getting owner {personid} '
                    f'for edition {editionid}.')
    # Call the function to get the owner info
    return make_api_response(editionowner_get(ed_id, person_id))


@app.route('/api/editions/owned/<userid>', methods=['get'])
def api_editionsowned(userid: str) -> Response:
    """
    Get the owner info of an edition.

    Args:
        userid (str): The ID of the person.

    Returns:
        Response: The API response containing the owner information.
    """
    (uid, err) = validate_positive_integer_id(userid, "kayttajatunnus")
    if err:
        app.logger.error(f'api_editionsowned: {err.response}')
        return make_api_response(err)
    elif uid is None:
        app.logger.error('api_editionsowned: Invalid userid.')
        response = ResponseType(
            'api_editionsowned: Virheellinen kayttajatunnus.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(editionowner_getowned(uid, False))


@app.route('/api/editions/<editionid>/owner/<personid>', methods=['delete'])
@jwt_required()  # type: ignore
def api_deleteowner(editionid: str, personid: str) -> Response:
    """
    Delete the owner of an edition.

    Parameters:
        editionid (str): The ID of the edition.
        personid (str): The ID of the person.

    Returns:
        Response: The response object containing the result of the operation.
    """
    (ed_id, err) = validate_positive_integer_id(editionid, "painosid")
    (person_id, err2) = validate_positive_integer_id(personid, "henkiloid")
    if err:
        app.logger.error(f'api_deleteowner: {err.response}')
        return make_api_response(err)
    if err2:
        app.logger.error(f'api_deleteowner: {err2.response}')
        return make_api_response(err2)
    elif person_id is None or ed_id is None:
        app.logger.error('api_deleteowner: '
                         'Invalid editionid or personid.')
        response = ResponseType(
            'api_deleteowner: Virheellinen painosid tai henkilotunnus.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    # Call the function to remove the owner
    return make_api_response(editionowner_remove(ed_id, person_id))


@app.route('/api/editions/owner', methods=['post', 'put'])
@jwt_required()
def api_addeditionowner() -> Response:
    """
    Add or update the owner of an edition.

    Parameters:
        editionid (str): The ID of the edition.
        params (dict): A dictionary containing the owner information.

    Returns:
        Response: The response object containing the result of the operation.
    """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    if request.method == 'POST':
        retval = make_api_response(editionowner_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(editionowner_update(params))
    else:
        app.logger.error(
            f'api_editioncreateupdate: Invalid method {request.method}.')
        response = ResponseType(
            'api_editioncreateupdate: Virheellinen metodin kutsu.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return retval


@app.route('/api/editions/<editionid>/shorts', methods=['get'])
def api_editionshorts(editionid: str) -> Response:
    """
    Get the shorts for a specific edition.

    Args:
        editionid (str): The ID of the edition.

    Returns:
        Response: The API response containing the shorts for the edition.
    """
    return make_api_response(edition_shorts(editionid))


@app.route('/api/latest/editions/<count>', methods=['get'])
def api_latesteditions(count: int) -> Response:
    """
    Get the latest editions.

    Args:
        count (int): The number of editions to return.

    Returns:
        Response: The response object containing the list of latest editions.

    Raises:
        ValueError: If the count is not an integer.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        app.logger.error(f'api_latesteditions: Invalid count {count}.')
        response = ResponseType(
            f'api_latesteditions: Virheellinen maara {count}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_latest_editions(count))
