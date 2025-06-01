###
# Work related functions


import json
from flask import Response, request
from app.api_jwt import jwt_admin_required

from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_awards import get_awards_for_work
from app.impl_works import (get_latest_works, get_work, get_work_shorts,
                            save_work_shorts,
                            search_books, search_works_by_author, work_add,
                            work_delete, work_tag_add, work_tag_remove,
                            work_update, worktype_get_all)
from app.types import HttpResponseCode

from app import app


@app.route('/api/works/<workid>', methods=['get'])
def api_getwork(workid: str) -> Response:
    """
    @api {get} /api/works/:id Get work
    @apiName Get Work
    @apiGroup Work
    @apiDescription Get work by id.
    @apiParam {Number} id of Work.
    @apiSuccess {ResponseType} work Work object.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response":
                {
                "misc": "",
                "work_type": {
                    "id": 1,
                    "name": "Romaani"
                },
                "title": "Kivineitsyt",
                "id": 1,
                "bookseriesorder": 0,
                "links": [],
                "bookseries": null,
                "tags": [],
                "genres": [
                    {
                    "abbr": "F",
                    "id": 1,
                    "name": "Fantasia"
                    }
                ],
                "contributions": [
                    {
                    "real_person": null,
                    "description": null,
                    "role": {
                        "id": 1,
                        "name": "Kirjoittaja"
                    },
                    "person": {
                        "id": 1,
                        "alt_name": "Barry Unsworth",
                        "name": "Unsworth, Barry"
                    }
                    }
                ],
                "language_name": null,
                "bookseriesnum": "",
                "awards": [],
                "subtitle": "",
                "descr_attr": null,
                "imported_string": "\n<b>Kivineitsyt</b>. (Stone Virgin, 1985).
                                    Suom Aira Buffa. WSOY 1986. [F].",
                "author_str": "Unsworth, Barry",
                "pubyear": 1985,
                "orig_title": "Stone Virgin",
                "editions": [
                    {
                    "size": null,
                    "misc": "",
                    "title": "Kivineitsyt",
                    "id": 1,
                    "dustcover": 1,
                    "format": {
                        "id": 1,
                        "name": "Paperi"
                    },
                    "version": null,
                    "images": [],
                    "coverimage": 1,
                    "isbn": "",
                    "contributions": [
                        {
                        "real_person": null,
                        "description": null,
                        "role": {
                            "id": 2,
                            "name": "Kääntäjä"
                        },
                        "person": {
                            "id": 2,
                            "alt_name": "Aira Buffa",
                            "name": "Buffa, Aira"
                        }
                        }
                    ],
                    "pages": null,
                    "subtitle": "",
                    "binding": {
                        "id": 1,
                        "name": "Ei tietoa/muu"
                    },
                    "pubseries": null,
                    "publisher": {
                        "image_attr": null,
                        "name": "WSOY",
                        "id": 387,
                        "fullname": "Werner Söderström Oy",
                        "image_src": null
                    },
                    "imported_string": "\n<b>Kivineitsyt</b>. (Stone Virgin,
                                        1985). Suom Aira Buffa. WSOY 1986.
                                        [F].",
                    "editionnum": 1,
                    "printedin": null,
                    "pubyear": 1986,
                    "pubseriesnum": null
                    }
                ],
                "description": null,
                "stories": []
                },
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "GetWork: Tietokantavirhe",
            "status": 400
        }
    """
    try:
        int_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getWork: Invalid id {workid}.')
        response = ResponseType(f'Virheellinen tunniste: {workid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_work(int_id))


@app.route('/api/works', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_workcreateupdate() -> Response:
    """
    Create or update a work in the API.

    This function handles the '/api/works' endpoint and supports both POST and
    PUT methods. The function expects a JSON payload in the request data.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.

    Raises:
        None
    """
    params = request.data.decode('utf-8')
    try:
        params = json.loads(params)
    except json.decoder.JSONDecodeError as exp:
        app.logger.error(f'Invalid JSON: {exp}.')
        response = ResponseType(f'Virheellinen JSON: {exp}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    if request.method == 'POST':
        retval = make_api_response(work_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(work_update(params))
    else:
        app.logger.error(
            f'api_workcreateupdate: Invalid method {request.method}.')
        response = ResponseType(
            'api_workcreateupdate: Virheellinen metodin kutsu.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return retval


@app.route('/api/latest/works/<count>', methods=['get'])
def api_latestworks(count: int) -> Response:
    """
    Get the latest works.

    Args:
        count (int): The number of works to return.

    Returns:
        Response: The response object containing the list of latest works.

    Raises:
        ValueError: If the count is not an integer.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        app.logger.error(f'api_latestworks: Invalid count {count}.')
        response = ResponseType(
            f'api_latestworks: Virheellinen maara {count}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_latest_works(count))


@app.route('/api/works/<workid>/awards', methods=['get'])
def api_workawards(workid: str) -> Response:
    """
    @api {get} /api/works/awards/:id Get work awards
    @apiName Get Work Awards
    @apiGroup Work
    @apiDescription Get awards for a work.
    @apiParam {Number} id of Work.
    @apiSuccess {ResponseType} awards Array of awards.
    @apiSuccessExample {json} Success-Response:
    """
    try:
        int_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'api_workawards: Invalid id {workid}.')
        response = ResponseType(f'Virheellinen tunniste: {workid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_awards_for_work(int_id))


@app.route('/api/works/<workid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_workdelete(workid: str) -> Response:
    """
    @api {delete} /api/works/:id Delete work
    @apiName Delete Work
    @apiGroup Work
    @apiDescription Delete work by id.
    @apiParam {Number} id of Work.
    @apiSuccess {ResponseType} work Work object.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response": "WorkDelete: Teos poistettu",
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "WorkDelete: Tietokantavirhe",
            "status": 400
        }
    """
    try:
        int_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'api_workdelete: Invalid id {workid}.')
        return make_api_response(
            ResponseType(f'Virheellinen tunniste: {workid}.',
                         HttpResponseCode.BAD_REQUEST.value))

    return make_api_response(work_delete(int_id))


@app.route('/api/works/shorts/<workid>', methods=['get'])
def api_workshorts(workid: int) -> Response:
    """ Get shorts in a collection. """
    try:
        int_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'api_WorkShorts: Invalid id {workid}.')
        response = ResponseType(f'Virheellinen tunniste: {workid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_work_shorts(int_id))


@app.route('/api/works/shorts', methods=['put', 'post'])
def api_workshorts_save() -> Response:
    """ Save shorts in a collection. """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    return make_api_response(save_work_shorts(params))


@app.route('/api/worktypes', methods=['get'])
def api_worktypes() -> Response:
    """
    @api {get} /api/worktypes Get all work types
    @apiName Get WorkTypes
    @apiGroup Work
    @apiDescription Get all work types in the system.
    @apiSuccess {ResponseType} worktypes List of work types.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response": [
                {
                    "id": 1,
                    "name": "Romaani"
                },
                {
                    "id": 2,
                    "name": "Kokoelma"
                },
                ...
            ],
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "WorkTypeGetAll: Tietokantavirhe",
            "status": 400
        }
    """
    retval = make_api_response(worktype_get_all())
    return retval


@app.route('/api/work/<workid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtowork(workid: int, tagid: int) -> Response:
    """
    Endpoint for adding or removing a tag from a work item.

    Args:
        id (int): The ID of the work item.
        tagid (int): The ID of the tag to be added or removed.

    Returns:
        Response: The API response containing the result of the operation.
    """
    func = None
    if request.method == 'PUT':
        func = work_tag_add
    elif request.method == 'DELETE':
        func = work_tag_remove
    else:
        app.logger.error(
            f'api_tagtowork: Invalid request method {request.method}.')
        response = ResponseType(
            f'api_tagtowork: Virheellinen pyyntömetodi {request.method}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    try:
        work_id = int(workid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={workid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = func(work_id, tag_id)

    return make_api_response(retval)


@app.route('/api/worksbyinitial/<letter>', methods=['get'])
def api_searchworksbyinitial(letter: str) -> Response:
    """
    Searches for works by author initial.

    Args:
        letter (str): The author initial to search for.

    Returns:
        Response: The API response containing the search results.
    """
    params = {}
    params['letter'] = letter
    retval = search_works_by_author(params)
    return make_api_response(retval)


@app.route('/api/searchworks', methods=['post'])
def api_searchworks() -> Response:
    """
    A function that handles the '/api/searchworks' endpoint.

    Parameters:
    - None

    Returns:
    - Response: The API response containing the search results.

    Description:
    - This function is responsible for handling the '/api/searchworks'
      endpoint, which is used to search for works.
    - It expects a POST request with JSON data containing the search
      parameters.
    - The function retrieves the search parameters from the request data and
      passes them to the 'search_books' function.
    - The 'search_books' function performs the actual search and returns the
      search results.
    - Finally, the function creates an API response using the
      'make_api_response' function and returns it.

    Note:
    - This function assumes that the 'search_books' and 'make_api_response'
      functions are defined elsewhere in the codebase.
    """
    params = json.loads(request.data)
    retval = search_books(params)

    return make_api_response(retval)
