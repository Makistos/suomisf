###
# Work related functions


import json
from flask import Response, request
from flask_jwt_extended import jwt_required
from app.api_jwt import (jwt_admin_required, jwt_self_or_admin_required,
                         is_self_or_admin, forbidden_not_self,
                         optional_user_id)

from app.api_helpers import make_api_response, validate_positive_integer_id
from app.impl import ResponseType
from app.impl_awards import get_awards_for_work
from app.impl_bookindex import book_index
from app.impl_work_similarity import DEFAULT_LIMIT, get_similar_works
from app.impl_works import (get_author_works, get_latest_works, get_omnibus,
                            get_work, get_work_shorts, save_omnibus,
                            save_work_shorts,
                            search_books, search_works_by_authorstr, work_add,
                            work_delete, work_read_list, work_read_remove,
                            work_read_set, work_tag_add, work_tag_remove,
                            work_cover_set, work_update, works_by_type,
                            worktype_get_all)
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


@app.route('/api/works/<workid>/similar', methods=['get'])
def api_work_similar(workid: str) -> Response:
    """
    @api {get} /api/works/:id/similar?limit=8 Similar works
    @apiName Get Similar Works
    @apiGroup Work
    @apiPermission none
    @apiDescription The works most similar to a work, best first, as
    computed by scripts/work_similarity.py (see
    docs/work-similarity-plan.md). A work with no computed list (one
    without a description of 20+ words) gives an empty list.
    @apiParam {Number} id Work id.
    @apiQuery {Number{1-40}} [limit=8] Number of works.
    @apiSuccess {Object[]} response Similar works: id, title, author_str,
    pubyear, image ({image_src, thumb_src} of the earliest edition's
    cover, or null), reasons (strongest first), score (the ranking score)
    and signals (its parts: S, T, T_raw, D, G, Y, coverage, types by tag
    type id, same_series).
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        [
          {
            "id": 2390,
            "title": "Ennustusten aika",
            "author_str": "Eddings, David",
            "pubyear": 1982,
            "image": {"image_src": "/images/books/x.jpg",
                      "thumb_src": "/images/books/thumbs/x.webp"},
            "reasons": [
              {"type": 2, "type_name": "Alagenre",
               "tags": [{"id": 1033, "name": "korkea fantasia"}]},
              {"type": "description", "type_name": "Kuvaus", "tags": []}
            ],
            "score": 0.56,
            "signals": {"S": 0.68, "T": 0.81, "T_raw": 0.62, "D": 0.34,
                        "G": 1.0, "Y": 0.51, "coverage": 0.89,
                        "types": {"1": 0.41, "2": 1.0},
                        "same_series": false}
          }
        ]
    @apiError (Error 400) {String} response Invalid id or limit.
    """
    int_id, error = validate_positive_integer_id(workid, 'teoksen id')
    if error is not None or int_id is None:
        return make_api_response(error or ResponseType(
            'Virheellinen teoksen id.', HttpResponseCode.BAD_REQUEST.value))
    limit_arg = request.args.get('limit', str(DEFAULT_LIMIT))
    if not limit_arg.isdigit() or int(limit_arg) < 1:
        return make_api_response(ResponseType(
            f'Virheellinen limit: {limit_arg}.',
            HttpResponseCode.BAD_REQUEST.value))
    return make_api_response(get_similar_works(int_id, int(limit_arg)))


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
@jwt_admin_required()  # type: ignore
def api_workshorts_save() -> Response:
    """ Save shorts in a collection. """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    return make_api_response(save_work_shorts(params))


@app.route('/api/works/bytype/<worktype>', methods=['get'])
def api_works_bytype(worktype: int) -> Response:
    try:
        wt = int(worktype)
    except (TypeError, ValueError) as exp:
        app.logger.error(exp)
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(works_by_type(wt))


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


@app.route('/api/bookindex', methods=['get'])
def api_bookindex() -> Response:
    """
    One page of the book index: every work, filtered, sorted and paged.

    Query parameters (all optional): author, title, orig_title,
    origyear_min, origyear_max, printyear_min, printyear_max, nationality,
    type (comma-separated ids), genre (comma-separated abbreviations),
    initial, sort (author|title|year|newest), page, rows (50|100|200).

    Returns:
        {"total": int, "page": int, "rows": int, "works": [...]}; 400 for a
        parameter that can't be used.
    """
    # A logged-in user gets their own owned and wishlisted marks; an expired
    # token gets 401 so the frontend renews it (optional_user_id).
    user_id = optional_user_id()
    return make_api_response(book_index(request.args.to_dict(), user_id))


@app.route('/api/works/<workid>/cover', methods=['put'])
@jwt_admin_required()  # type: ignore
def api_work_cover(workid: str) -> Response:
    """
    Set which cover the work page shows.

    Body: {"image_id": <id of an edition image of this work> | null}.
    null lets the page pick a cover itself.

    Returns:
        200 on success; 400 for a bad id or an image that isn't a cover
        of this work; 404 if the work doesn't exist.
    """
    work_id, error = validate_positive_integer_id(workid, 'teoksen id')
    if error:
        return make_api_response(error)
    body = request.get_json(silent=True)
    image_id = body.get('image_id', 'missing') \
        if isinstance(body, dict) else 'missing'
    # bool is an int in Python; a cover id never is.
    if image_id is not None and (not isinstance(image_id, int)
                                 or isinstance(image_id, bool)
                                 or image_id < 1):
        return make_api_response(ResponseType(
            'Virheellinen kuvan tunniste',
            status=HttpResponseCode.BAD_REQUEST.value))
    return make_api_response(work_cover_set(int(work_id), image_id))


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
    retval = search_works_by_authorstr(params)
    return make_api_response(retval)


@app.route('/api/worksbyauthor/<authorid>', methods=['get'])
def api_searchworksbyauthor(authorid: str) -> Response:
    """
    Searches for works by author ID.

    Args:
        authorid (str): The ID of the author to search for.
    Returns:
        Response: The API response containing the search results.
    """
    try:
        int_id = int(authorid)
    except (TypeError, ValueError):
        app.logger.error(f'api_searchworksbyauthor: Invalid id {authorid}.')
        response = ResponseType(f'Virheellinen tunniste: {authorid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = get_author_works(int_id)
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


@app.route('/api/works/random/incomplete', methods=['post'])
def api_random_incomplete_work() -> Response:
    """
    @api {post} /api/works/random/incomplete Get random incomplete works
    @apiName Get Random Incomplete Works
    @apiGroup Work
    @apiDescription Get random works that lack specified data fields.
    @apiParam {Number} [count=1] Number of works to return (1-100).
    @apiParam {String[]} [missing_fields] Array of fields to check for missing
                                          data.
    @apiParamExample {json} Request-Example:
        {
            "count": 5,
            "missing_fields": ["description", "tags", "genres", "stories",
                               "page_count"]
        }
    @apiParamExample {json} Available Fields:
        Work fields: ["description", "links", "tags", "genres", "language",
                      "stories", "kirjasampo_tags", "kirjasampo_link"]
        Edition fields: ["page_count", "size", "binding", "image"]
        Note: "stories" field only applies to collections (work type 2)
        Note: "kirjasampo_tags" = has a kirjasampo.fi link but tags have
              never been imported from it
        Note: "kirjasampo_link" = no kirjasampo.fi link, leaving out works
              with the tag for works missing from Kirjasampo
              (KIRJASAMPO_MISSING_TAG_ID in impl_works.py)
    @apiSuccess {ResponseType} works Array of work objects missing specified
                                     data.
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
            "response": [
                {
                    "id": 123,
                    "title": "Some Collection",
                    "work_type": {"id": 2, "name": "Kokoelma"},
                    "description": null,
                    "tags": [],
                    "stories": [],
                    "editions": [
                        {
                            "id": 456,
                            "pages": null,
                            ...
                        }
                    ],
                    ...
                }
            ],
            "status": 200
        }
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad Request
        {
            "response": "Invalid count: must be between 1 and 100",
            "status": 400
        }
    """
    params = request.data.decode('utf-8')
    try:
        params = json.loads(params) if params else {}
    except json.decoder.JSONDecodeError as exp:
        app.logger.error(f'Invalid JSON: {exp}.')
        response = ResponseType(f'Virheellinen JSON: {exp}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    from app.impl_works import get_random_incomplete_works

    return make_api_response(get_random_incomplete_works(params))


@app.route('/api/works/<workid>/omnibus', methods=['get'])
def api_get_omnibus(workid: int) -> Response:
    """
    Get omnibus entries linking works together.

    Expects query parameters 'omnibus_id' or 'work_id'.

    Returns:
        Response: API response containing omnibus entries.
    """
    return make_api_response(get_omnibus(workid))


@app.route('/api/works/omnibus', methods=['post'])
@jwt_admin_required()  # type: ignore
def api_create_omnibus() -> Response:
    """
    Create omnibus entry linking works together.

    Expects JSON payload with 'omnibus_id', 'work_id', and optional
    'explanation'.

    Returns:
        Response: API response indicating success or failure.
    """
    params = request.data.decode('utf-8')
    try:
        params = json.loads(params)
    except json.decoder.JSONDecodeError as exp:
        app.logger.error(f'Invalid JSON: {exp}.')
        response = ResponseType(f'Virheellinen JSON: {exp}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(save_omnibus(params))


@app.route('/api/works/read/<userid>', methods=['get'])
def api_workreadlist(userid: str) -> Response:
    """
    List the works a user has marked as read.

    Args:
        userid (str): The id of the user.

    Returns:
        Response: The API response containing the user's read works.
    """
    (uid, err) = validate_positive_integer_id(userid, "kayttajatunnus")
    if err:
        app.logger.error(f'api_workreadlist: {err.response}')
        return make_api_response(err)
    if uid is None:
        response = ResponseType(
            'api_workreadlist: Virheellinen kayttajatunnus.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(work_read_list(uid))


@app.route('/api/works/read', methods=['post', 'put'])
@jwt_required()  # type: ignore
def api_workreadset() -> Response:
    """
    Mark a work read for a user, or update the opinion if already read.

    Expects a JSON body with 'work_id', 'user_id' and an optional 'opinion'
    (-1 = didn't like, 0 = it was ok, 1 = liked; null = read, no opinion)
    and 'description' (the user's note; omitted = keep the current one).

    Returns:
        Response: The API response indicating success or failure.
    """
    try:
        params = json.loads(request.data.decode('utf-8'))
    except json.decoder.JSONDecodeError as exp:
        app.logger.error(f'api_workreadset: Invalid JSON: {exp}.')
        response = ResponseType(f'Virheellinen JSON: {exp}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    if not is_self_or_admin(params.get('user_id')):
        return forbidden_not_self()
    return make_api_response(work_read_set(params))


@app.route('/api/works/<workid>/read/<userid>', methods=['delete'])
@jwt_self_or_admin_required('userid')
def api_workreadremove(workid: str, userid: str) -> Response:
    """
    Unmark a work as read for a user.

    Args:
        workid (str): The id of the work.
        userid (str): The id of the user.

    Returns:
        Response: The API response indicating success or failure.
    """
    (wid, err) = validate_positive_integer_id(workid, "teosid")
    (uid, err2) = validate_positive_integer_id(userid, "kayttajatunnus")
    if err:
        app.logger.error(f'api_workreadremove: {err.response}')
        return make_api_response(err)
    if err2:
        app.logger.error(f'api_workreadremove: {err2.response}')
        return make_api_response(err2)
    if wid is None or uid is None:
        response = ResponseType(
            'api_workreadremove: Virheellinen teosid tai kayttajatunnus.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(work_read_remove(wid, uid))
