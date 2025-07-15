###
# Tag related functions

import json
import bleach
from flask import Response, request

from app import app
from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_tags import (tag_create, tag_delete, tag_filter, tag_forminfo,
                           tag_info, tag_list, tag_list_quick, tag_merge,
                           tag_search, tag_types, tag_update)
from app.types import HttpResponseCode
from app.api_jwt import jwt_admin_required


@app.route('/api/tags', methods=['get'])
def api_tags() -> Response:
    """
    Handles the GET request to '/api/tags' endpoint.

    Returns:
        Response: The response object containing the tags.
    """
    if request.args:
        args = request.args.to_dict()
        if 'search' in args:
            pattern = bleach.clean(args['search'])
            return make_api_response(tag_search(pattern))
        app.logger.error(f'api_tags: Invalid parameters: {args}')
        response = ResponseType(
            'app_tags: Parametrejä ei ole tuettu.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(tag_list())


@app.route('/api/tagsquick', methods=['get'])
def api_tagsquick() -> Response:
    """
    Get tags for quick search.

    Returns:
        Response: The response object containing the tags.
    """
    return make_api_response(tag_list_quick())


@app.route('/api/tags', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_tagcreate() -> Response:
    """
    Create a new tag.

    """
    params = json.loads(request.data.decode('utf-8'))
    name = params['data']['name']

    retval = tag_create(name)

    return make_api_response(retval)


@app.route('/api/tags/<tag_id>', methods=['get'])
def api_tag(tag_id: str) -> Response:
    """
    Retrieves information about a tag with the specified ID.

    Parameters:
        tag_id (str): The ID of the tag to retrieve information for.

    Returns:
        Response: The API response containing the tag information.
    """
    try:
        int_id = int(tag_id)
    except (TypeError, ValueError):
        app.logger.error(f'api_tag: Invalid id {tag_id}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(tag_info(int_id))


@app.route('/api/tags/form/<tag_id>', methods=['get'])
def api_tagform(tag_id: str) -> Response:
    """
    Retrieves the form for a tag with the specified ID.

    Parameters:
        tag_id (str): The ID of the tag to retrieve the form for.

    Returns:
        Response: The API response containing the tag form.
    """
    try:
        int_id = int(tag_id)
    except (TypeError, ValueError):
        app.logger.error(f'api_tagform: Invalid id {tag_id}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(tag_forminfo(int_id))


@app.route('/api/tags', methods=['put'])
@jwt_admin_required()  # type: ignore
def api_tagupdate() -> Response:
    """
    Rename given tag. Cannot be named to an existing tag. tagMerge is used
    for combining tags.

    Parameters
    ----------
    id : int
        Id of tag to rename.
    name: str
        New name for tag.

    Returns
    -------
    200 - Request succeeded.
    400 - Bad Request. Either a tag by that name already exists of not tag
          with given id found or parameters are faulty.
    """
    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error('nvalid JSON.')
        response = ResponseType('Virheellinen JSON',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    response = tag_update(params)
    return make_api_response(response)


@app.route('/api/filter/tags/<pattern>', methods=['get'])
def api_filtertags(pattern: str) -> Response:
    """
    Filter tags based on a given pattern.

    Args:
        pattern (str): The pattern to filter the tags.

    Returns:
        Response: The response object containing the filtered tags.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterTags: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    retval = tag_filter(pattern)
    return make_api_response(retval)


@app.route('/api/tags/<source_id>/merge/<target_id>', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_tagmerge(source_id: int, target_id: int) -> Response:
    """
    Merge items of two tags into one and delete the obsolete tag.

    Parameters
    ----------
    id: int
        Id of tag to merge into.
    id2: int
        Id of tag to merge from.

    Returns
    -------
    200 - Request succeeded
    400 - Request failed because one of the ids was invalid.
    """
    try:
        id_to = int(source_id)
        id_from = int(target_id)
    except (TypeError, ValueError):
        app.logger.error('api_tagmerge: Invalid id. Source = %s, target = %s',
                         source_id, target_id)
        response = ResponseType('Virheellinen asiasanan tunniste.',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = tag_merge(id_to, id_from)
    return make_api_response(retval)


@app.route('/api/tags/<tagid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_tagdelete(tagid: int) -> Response:
    """
    Delete selected tag. Tag is only deleted if it isn't used anywhere.

    Parameters
    ----------
    id : int
        Id of tag to delete.

    Returns
    -------
    200 - Request succeeded
    400 - Request failed. Either id was not a number or tag with given id was
          not found.
    """
    try:
        int_id = int(tagid)
    except (TypeError,  ValueError):
        app.logger.error(f'api_tagDelete: Invalid ID. Id = {tagid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    response = tag_delete(int_id)
    retval = make_api_response(response)
    return retval


@app.route('/api/tags/types', methods=['get'])
def api_tagtypes() -> Response:
    """
    Get all tag types.

    Parameters
    ----------
    None

    Returns
    -------
    200 - Request succeeded
    400 - Request failed
    """
    retval = tag_types()
    return make_api_response(retval)
