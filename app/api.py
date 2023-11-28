# pylint: disable=too-many-lines
""" API functions. """
import json
from typing import Any, Tuple, NewType, Union, List, Dict
import jsonschema
from jsonschema import validate
import bleach
from flask_jwt_extended import jwt_required
from flask import request
from flask.wrappers import Response
from app.impl import (ResponseType, get_frontpage_data, SearchResult,
                      get_changes, filter_countries, filter_languages,
                      country_list, filter_link_names, genre_list, role_list)
from app.api_errors import APIError
from app.api_jwt import jwt_admin_required
from app.impl_articles import (get_article, article_tag_add,
                               article_tag_remove, article_tags)
from app.impl_bookseries import (list_bookseries, get_bookseries,
                                 bookseries_create, bookseries_update,
                                 bookseries_delete, filter_bookseries)
from app.impl_editions import (get_bindings, create_edition, update_edition,
                               edition_delete, edition_image_upload,
                               edition_image_delete, edition_shorts)
from app.impl_issues import (get_issue, get_issue_tags, issue_tag_add,
                             issue_tag_remove)
from app.impl_magazines import (list_magazines, get_magazine)
from app.impl_people import (search_people, filter_aliases, person_update,
                             person_shorts, person_tag_add, person_tag_remove,
                             filter_people, list_people, person_delete,
                             get_person, get_author_first_letters, person_add)
from app.impl_publishers import (publisher_add, publisher_update,
                                 list_publishers, get_publisher,
                                 filter_publishers)
from app.impl_pubseries import (list_pubseries, get_pubseries,
                                filter_pubseries)
from app.impl_shorts import (search_shorts, story_add, story_updated,
                             story_delete, get_short, get_short_types,
                             story_tag_add, story_tag_remove)
from app.impl_tags import (tag_list, tag_search, tag_create, tag_info,
                           tag_rename, tag_filter, tag_merge, tag_delete)
from app.impl_users import (login_user, refresh_token, list_users, get_user)
from app.impl_works import (search_works, get_work, work_add, work_update,
                            work_delete, get_work_shorts, worktype_get_all,
                            work_tag_add, work_tag_remove,
                            search_works_by_author, search_books,
                            save_work_shorts)
from app.api_schemas import (PersonSchema, BookseriesSchema)
from app.route_helpers import new_session
from app import app

DEFAULT_MIMETYPE = 'application/json'  # Data is always returned as JSON


ConstraintType = NewType('ConstraintType', List[Dict[str, str]])
FilterType = NewType('FilterType', Dict[str, Union[str, ConstraintType]])


###
# Generic functions

def make_api_error(response: ResponseType) -> Response:
    """
    Generate a response object for an API error.

    Args:
        response (ResponseType): The response object containing the error
                                  message.

    Returns:
        Response: The response object with the error message, status code, and
                   mimetype.
    """
    return Response(response=list(json.dumps({'msg': response.response})),
                    status=response.status,
                    mimetype=DEFAULT_MIMETYPE)


def make_api_response(response: ResponseType) -> Response:
    """
    Generate a Flask Response object from a given ResponseType object.

    Args:
        response (ResponseType): The ResponseType object to be converted into a
                                 Flask Response object.

    Returns:
        Response: The Flask Response object generated from the given
                  ResponseType object.
    """
    # Response is made into a list for performance as per Flask documentation
    if response.status >= 400 and response.status <= 511:
        return make_api_error(response)

    return Response(response=json.dumps(response.response),
                    status=response.status,
                    mimetype=DEFAULT_MIMETYPE)


def login_options(req: Any) -> Dict[str, Any]:
    """
    Generate the login options based on the given request.

    Args:
        request (Any): The request object containing the login parameters.

    Returns:
        Dict[str, str]: A dictionary containing the login options.

    Raises:
        TypeError: If the request does not contain the required parameters.
        KeyError: If the request does not contain the required parameters.

    """
    options = {}
    try:
        if req.json:
            options['username'] = req.json['username']
            options['password'] = req.json['password']
        else:
            options['username'] = req.json['authorization']['username']
            options['password'] = req.json['authorization']['password']
    except (TypeError, KeyError) as exp:
        app.logger.error(f'api_login: Virheelliset parametrit: {exp}.')
        return {}

    if not options['username'] or not options['password']:
        app.logger.error('api_login: Virheelliset parametrit.')
        return {}

    return options


def fix_operator(op: str, value: str) -> Tuple[str, str]:
    """
    Fixes the operator and value for a given operation.

    Args:
        op (str): The operation to be fixed.
        value (str): The value to be fixed.

    Returns:
        Tuple[str, str]: A tuple containing the fixed operator and value.

    Raises:
        APIError: If the operation is not valid.
    """

    if op == 'equals':
        return ('eq', value)
    if op == 'notequals':
        return ('ne', value)
    if op == 'startsWith':
        if value:
            value = value + '%'
        return ('ilike', value)
    if op == 'endsWith':
        if value:
            value = '%' + value
        return ('ilike', value)
    if op == 'contains':
        if value:
            value = '%' + value + '%'
        return ('ilike', value)
    if op == 'notContains':
        if value:
            value = '%' + value + '%'
        # Needs special attention in filtering
        return ('notContains', value)
    if op == 'lt':
        return ('lt', value)
    if op == 'lte':
        return ('lte', value)
    if op == 'gt':
        return ('gt', value)
    if op == 'gte':
        return ('gte', value)
    if op == 'in':
        # Needs special attention in filtering
        return ('in', value)
    else:
        raise APIError(f'Invalid filter operation {op}', 405)

###
# User control related functions

# This function is used to log in the user using the HTTP POST method.
# 1. The function checks if the parameters are passed correctly.
# 2. If the parameters are not passed correctly, the function returns a 401
#    error.
# 3. If the parameters are passed correctly, the function calls the LoginUser
#    function.


@app.route('/api/login', methods=['post'])
@jwt_required(optional=True)  # type: ignore
def api_login() -> Response:
    """
    @api {post} /api/login Login
    @apiName Login
    @apiGroup User
    @apiPermission none
    @apiDescription Log in the user. The user must be registered in the system.
    @apiBody {String} username Username
    @apiBody {String} password Password
    @apiSuccess {String} access_token Access token
    @apiSuccess {String} refresh_token Refresh token
    @apiSuccess {String} user Username
    @apiSuccess {String} role User role
    @apiSuccess {String} id User id
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "access_token": <access_token>,
        "refresh_token": <refresh_token>,
        "user": "exampleuser",
        "role": "user",
        "id": 1
        }
    @apiError (Error 401) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 401 Unauthorized
        {
        "code": 401,
        "message": "Kirjautuminen ei onnistunut"
        }

    """
    options = login_options(request)
    if not options:
        err = ResponseType('Virheellinen kirjautuminen', 401)
        return make_api_error(err)
    retval = login_user(options)
    return retval


@app.route('/api/refresh', methods=['post'])
@jwt_required(refresh=True)  # type: ignore
def api_refresh() -> Response:
    """
    @api {post} /api/refresh Refresh token
    @apiName Refresh Token
    @apiGroup User
    @apiPermission user
    @apiDescription Refresh the access token.
    @apiHeader {String} Authorization Bearer token
    @apiSuccess {String} access_token Access token
    @apiSuccess {String} refresh_token Refresh token
    @apiSuccess {String} user Username
    @apiSuccess {String} role User role
    @apiSuccess {String} id User id
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "access_token": <access_token>,
        "refresh_token": <refresh_token>,
        "user": "exampleuser",
        "role": "user",
        "id": 1
        }
    @apiError (Error 401) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 401 Unauthorized
        {
        "code": 401,
        "message": "Kirjautuminen ei onnistunut"
        }
    """
    options = {}
    try:
        if request.json:
            options['username'] = request.json['username']
        else:
            options['username'] = request.json['authorization']['username']
    except (TypeError, KeyError) as exp:
        response = ResponseType(f'api_login: Virheelliset parametrit: {exp}.',
                                401)
        return make_api_response(response)

    if not options['username']:
        response = ResponseType('api_login: Virheelliset parametrit.', 401)
        return make_api_response(response)
    return refresh_token(options)


###
# Front page
@app.route('/api/frontpagedata', methods=['get'])
def frontpagestats() -> Response:
    """
    @api {get} /api/frontpagedata Front page data
    @apiName Front page data
    @apiGroup Front page
    @apiPermission none
    @apiDescription Get data for the front page. This includes various
    statistics and the latest additions to the database.
    @apiSuccess {Number} works Number of works in the database
    @apiSuccess {Number} editions Number of editions in the database
    @apiSuccess {Number} magazines Number of magazines in the database
    @apiSuccess {Number} shorts Number of short stories in the database
    @apiSuccess {Number} covers Number of covers in the database
    @apiSuccess {Edition[]} latest Latest additions to the database (4)
    @apiSuccessExample {json} Success-Response:
        HTTP/1.1 200 OK
        {
        "response": [
            {
            "works": 1000,
            "editions": 2000,
            "magazines": 3000,
            "shorts": 4000,
            "magazines": 50,
            "covers": 1500,
            "latest": [
                {
                    }
                ]
            }
        ]
        }
    @apiError (Error 400) {String} message Error message
    @apiErrorExample {json} Error-Response:
        HTTP/1.1 400 Bad request
        {
        "code": 400,
        "message": "GetFrontpageData: Tietokantavirhe."
        }
    """
    return make_api_response(get_frontpage_data())


###
# Generic search functions

@ app.route('/api/search/<pattern>', methods=['get', 'post'])
def api_search(pattern: str) -> Tuple[str, int]:
    """
    Searches for a pattern in the API and returns the results.

    Args:
        pattern (str): The pattern to search for.

    Returns:
        Tuple[str, int]: A tuple containing the search results as a JSON string
                         and the HTTP status code.
    """
    retcode = 200
    results: SearchResult = []

    # searchword = request.args.get('search', '')
    pattern = bleach.clean(pattern)
    words = pattern.split(' ')

    session = new_session()
    results = search_works(session, words)
    results += search_people(session, words)
    results = sorted(results, key=lambda d: d['score'], reverse=True)
    return json.dumps(results), retcode


###
# Alias related functions

@app.route('/api/filter/alias/<id>', methods=['get'])
def api_filteralias(personid: str) -> Response:
    """
    This function is a Flask route that handles GET requests to the
    '/api/filter/alias/<id>' endpoint. It takes a string parameter 'personid'
    which represents the id of the person. The function tries to convert the
    'personid' to an integer. If the conversion fails, it logs an error message
    and returns a Response object with a 400 status code and an error message.
    If the conversion is successful, the function calls the 'filter_aliases'
    function with the converted 'personid' and returns the result as a Response
    object. The function returns the Response object.
    """
    try:
        int_id = int(personid)
    except (TypeError, ValueError):
        app.logger.error(f'api_filteralias: Invalid id {personid}.')
        response = ResponseType(f'Virheellinen tunniste: {personid}.', 400)
        return make_api_response(response)

    return make_api_response(filter_aliases(int_id))


###
# Article related functions

@ app.route('/api/articles/<articleid>', methods=['get'])
def api_getarticle(articleid: str) -> Response:
    """
    Retrieves an article from the API based on the provided article ID.

    Parameters:
        articleId (str): The ID of the article to retrieve.

    Returns:
        Response: The response object containing the article data.

    Raises:
        ValueError: If the provided article ID is invalid.

    Example:
        api_getarticle('123')
    """

    try:
        int_id = int(articleid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getarticle: Invalid id {articleid}.')
        response = ResponseType(
            f'api_getarticle: Virheellinen tunniste {articleid}.', 400)
        return make_api_response(response)

    return make_api_response(get_article(int_id))


@app.route('/api/articles/<articleid>/tags', methods=['get'])
def api_getarticletags(articleid: int) -> Response:
    """
    Get the tags associated with a specific article.

    Parameters:
        articleId (int): The ID of the article.

    Returns:
        Response: The response object containing the tags associated with the
                  article.
    """

    try:
        int_id = int(articleid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getarticletags: Invalid id {articleid}.')
        response = ResponseType(
            f'apigetarticletags: Virheellinen tunniste {articleid}.', 400)
        return make_api_response(response)

    retval = article_tags(int_id)
    return make_api_response(retval)


@app.route('/api/articles/<articleid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtoarticle(articleid: int, tagid: int) -> Response:
    """
    API endpoint for adding or removing a tag from an article.

    Args:
        id (int): The ID of the article.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response containing the result of the operation.
    """
    if request.method == 'PUT':
        func = article_tag_add
    elif request.method == 'DELETE':
        func = article_tag_remove

    try:
        int_id = int(articleid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={articleid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    retval = func(int_id, tag_id)

    return make_api_response(retval)


###
# Binding related functions

@app.route('/api/bindings', methods=['get'])
def api_bindings() -> Response:
    """
    This function is a route handler for the '/api/bindings' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API call.
    """
    retval = make_api_response(get_bindings())
    return retval


###
# Bookseries related functions

@ app.route('/api/bookseries', methods=['get'])
def api_listbookseries() -> Response:
    """
    This function is a route handler for the '/api/bookseries' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the list of book series.
    """
    return make_api_response(list_bookseries())


@app.route('/api/bookseries', methods=['post', 'put'])
@jwt_admin_required()   # type: ignore
def api_bookseriescreateupdate() -> Response:
    """
    Create or update a book series.

    This function is responsible for handling the '/api/bookseries' endpoint
    with both 'POST' and 'PUT' methods. It expects a JSON payload containing
    the book series data.

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
        app.logger.error('api_bookseriescreateupdate: Invalid JSON.')
        response = ResponseType(
            'api_bookseriescreateupdate: Virheelliset parametrit.', 400)
        return make_api_response(response)
    try:
        validate(instance=params, schema=BookseriesSchema)
    except jsonschema.exceptions.ValidationError:
        app.logger.error('api_bookseriescreateupdate: Invalid JSON.')
        response = ResponseType(
            'api_bookseriescreateupdate: Virheelliset parametrit.', 400)
        return make_api_response(response)
    if request.method == 'POST':
        retval = make_api_response(bookseries_create(params))
    elif request.method == 'PUT':
        retval = make_api_response(bookseries_update(params))

    return retval


@app.route('/api/bookseries/<bookseriesid>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_bookseriesdelete(bookseriesid: str) -> Response:
    """
    Delete a book series by its ID.

    Args:
        bookseriesId (str): The ID of the book series to be deleted.

    Returns:
        Response: The API response indicating the success or failure of the
                  deletion.
    """
    return make_api_response(bookseries_delete(bookseriesid))


@ app.route('/api/bookseries/<bookseriesid>', methods=['get'])
def api_getbookseries(bookseriesid: str) -> Response:
    """
    Get a book series by its ID.

    Args:
        bookseriesId (str): The ID of the book series.

    Returns:
        Response: The response object containing the book series data.

    Raises:
        TypeError: If the book series ID is not a valid integer.
        ValueError: If the book series ID is not a valid integer.

    Example:
        >>> api_GetBookseries('123')
        <Response [200]>
    """

    try:
        int_id = int(bookseriesid)
    except (TypeError, ValueError):
        app.logger.error(f'api_getbookseries: Invalid id {bookseriesid}.')
        response = ResponseType(
           f'api_getbookseries: Virheellinen tunniste {bookseriesid}.', 400)
        return make_api_response(response)

    return make_api_response(get_bookseries(int_id))


@app.route('/api/filter/bookseries/<pattern>', methods=['get'])
def api_filterbookseries(pattern: str) -> Response:
    """
    Filters book series based on a given pattern.

    Args:
        pattern (str): The pattern to filter the book series.

    Returns:
        Response: The response object containing the filtered book series.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterBookseries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_bookseries(pattern)
    return make_api_response(retval)


###
# Change related functions

@ app.route('/api/changes', methods=['get'])
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
        if value == 'null' or value == 'undefined':
            value = None
        params[param] = value

    try:
        retval = get_changes(params)
    except APIError as exp:
        app.logger.error('Exception in api_Changes: ' + str(exp))
        response = ResponseType('api_Changes: poikkeus.', 400)
        return make_api_response(response)

    return make_api_response(retval)


###
# Country related functions

@ app.route('/api/countries', methods=['get'])
def countries() -> Response:
    """
    Returns a list of all of the countries in the system ordered by name.
    """
    return make_api_response(country_list())


@app.route('/api/filter/countries/<pattern>', methods=['get'])
def api_filtercountries(pattern: str) -> Response:
    """
    Filter countries based on a given pattern.

    Args:
        pattern (str): The pattern to filter the countries.

    Returns:
        Response: The response object containing the filtered countries.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterCountries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_countries(pattern)
    return make_api_response(retval)

###
# Edition related functions


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
        app.logger.error('api_uploadEditionImage: File not found.')
        response = ResponseType('Tiedosto puuttuu', status=400)
        return make_api_response(response)

    retval = make_api_response(
        edition_image_upload(editionid, file))
    return retval


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


@app.route('/api/filter/linknames/<pattern>', methods=['get'])
def api_filterlinknames(pattern: str) -> Response:
    """
    This function is a Flask route that handles GET requests to the
    '/api/filter/linknames/<pattern>' endpoint. It takes a single parameter
    'pattern' of type string. The function cleans the 'pattern' using the
    'bleach' library and then calls the 'filter_link_names' function
    with the cleaned 'pattern' as an argument. The return type of this function
    is 'Response'.
    """
    pattern = bleach.clean(pattern)
    retval = filter_link_names(pattern)
    return make_api_response(retval)

###
# Genre related functions


@ app.route('/api/genres', methods=['get'])
def genres() -> Response:
    """
    Returns a list of all of the genres in the system in the order
    they are in the database (i.e. by id).
    """
    return make_api_response(genre_list())


###
# Issue related functions
@ app.route('/api/issues/<issueid>', methods=['get'])
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
            f'api_getissueformagazine: Virheellinen tunniste {issueid}.', 400)
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
            f'api_getissuetags: Virheellinen tunniste {issue_id}.', 400)
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
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    retval = func(issue_id, tag_id)

    return make_api_response(retval)


###
# Language related functions

@app.route('/api/filter/languages/<pattern>', methods=['get'])
def api_filterlanguages(pattern: str) -> Response:
    """
    Filter languages based on a given pattern.

    Args:
        pattern (str): The pattern to filter languages.

    Returns:
        Response: The response object containing the filtered languages.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterLanguages: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_languages(pattern)
    return make_api_response(retval)


###
# Magazine related functions

@ app.route('/api/magazines', methods=['get'])
def api_listmagazines() -> Response:
    """
    Retrieves a list of magazines from the API.

    Returns:
        Response: The response object containing the list of magazines.
    """

    return make_api_response(list_magazines())


@ app.route('/api/magazines/<magazineid>', methods=['get'])
def api_getmagazine(magazineid: str) -> Response:
    """
    Get a magazine by its ID.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Response: The response object containing the magazine data.

    Raises:
        ValueError: If the magazine ID is invalid.
    """

    try:
        int_id = int(magazineid)
    except (ValueError, TypeError):
        app.logger.error(f'api_GetMagazine: Invalid id {magazineid}.')
        response = ResponseType(
            f'api_GetMagazine: Virheellinen tunniste {magazineid}.', 400)
        return make_api_response(response)

    return make_api_response(get_magazine(int_id))


@ app.route('/api/magazines/<magazineid>', methods=['patch'])
def api_updatemagazine(magazineid: str) -> Tuple[str, int]:
    """
    Updates a magazine with the given `magazineId`.

    Args:
        magazineId (str): The ID of the magazine to update.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        status code.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)

    # return UpdateMagazine(options, "")


@ app.route('/api/magazines/<magazineid>/issues', methods=['get'])
def api_getmagazineissues(magazineid: str) -> Tuple[str, int]:
    """
    Retrieves the issues of a specific magazine.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
                         value.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazineIssues(options)


@ app.route('/api/magazines/<magazineid>/publisher', methods=['get'])
def api_getmagazinepublisher(magazineid: str) -> Tuple[str, int]:
    """
    Get the publisher of a magazine.

    Args:
        magazineid (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazinePublisher(options)


@ app.route('/api/magazines/<magazineid>/tags', methods=['get'])
def api_getmagazinetags(magazineid: str) -> Tuple[str, int]:
    """
    Get the tags associated with a specific magazine.

    Args:
        magazineid (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        value.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazineTags(options)

###
# People related functions


@app.route('/api/people', methods=['post', 'put'], strict_slashes=False)
@jwt_admin_required()  # type: ignore
def api_createupdateperson() -> Response:
    """
    Create or update a person in the API.

    This function is responsible for handling the POST and PUT requests to the
    '/api/people' endpoint. It expects a JSON payload containing the person's
    information.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API request.

    Raises:
        TypeError: If the request data is not a valid JSON.
        ValueError: If the JSON payload is invalid.
        jsonschema.exceptions.ValidationError: If the JSON payload does not
                                               conform to the PersonSchema.

    Note:
        - This function requires the request method to be either 'POST' or
          'PUT'.
        - The request data should be a valid JSON string.
        - The JSON payload should conform to the PersonSchema.
        - The function logs any errors encountered during the process.

    """
    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error('api_CreateUpdatePerson: Invalid JSON.')
        return make_api_response(
            ResponseType('api_CreateUpdatePerson: Virheelliset parametrit.',
                         400))
    try:
        validate(instance=params, schema=PersonSchema)
    except jsonschema.exceptions.ValidationError as exp:
        app.logger.error(f'api_CreateUpdatePerson: Invalid JSON {exp}.')
        return make_api_response(
            ResponseType('api_CreateUpdatePerson: Virheelliset parametrit.',
                         400))
    if request.method == 'POST':
        retval = make_api_response(person_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(person_update(params))

    return retval


@app.route('/api/people/', methods=['get'])
def api_getpeople() -> Response:

    """
    This function receives parameters in the form of
    first=50&...filters_name_operator=1&filters_name_constraints_value=null..
    I.e. the original dictionary has been translated into variables. The
    Javascript dictionary looks like this:
    {
        first: 0,
        rows: 50,
        page: 0,
        sortField: "name",
        sortOrder: 1,
        multiSortMeta: null,
        filters: {
            global: { value: null, matchMode: FilterMatchMode.CONTAINS },
            name: { operator: FilterOperator.AND,
                    constraints: [
                      { value: null,
                        matchMode: FilterMatchMode.STARTS_WITH
                      }
                    ]
                  },
            dob: { operator: FilterOperator.AND,
                   constraints: [
                     { value: null,
                       matchMode: FilterMatchMode.EQUALS
                     }
                   ]
                  },
            dod: { operator: FilterOperator.AND,
                   constraints: [
                      { value: null,
                        matchMode: FilterMatchMode.EQUALS
                      }
                   ]
                 },
            nationality: { value: null, matchMode: FilterMatchMode.EQUALS },
            work_count: { value: null, matchMode: FilterMatchMode.EQUALS },
            story_count: { value: null, matchMode: FilterMatchMode.EQUALS },
            roles: { value: null, matchMode: FilterMatchMode.EQUALS }
        }
    }
    This function will translate the parameter list back to a similar Python
    dict.
    Those constants in the list are explained in the implementation function,
    but they are simple self-explaining strings.
    """

    url_params = request.args.to_dict()
    params: Dict[str, Any] = {}
    for (param, value) in url_params.items():
        # param, value = p.split('=')
        if value == 'null' or value == 'undefined':
            value = None
        if '_' not in param and param != 'filters':
            # This takes care of the first six parameters.
            params[param] = value
        else:
            # In effect we have two situations here: either a parameter that
            # has a simple value, like filters_global_value=null or a
            # constraint e.g. filters_name_constraints_0_value=null.
            parts = param.split('_')
            # Filters is the only word these parameters
            # start with so we can skip that
            filter_field = parts[1]  # global, name, dob, etc.
            filter_name = parts[2]   # value, operator, constraints, etc.
            if filter_field not in params:
                params[filter_field] = {}
            if filter_name == 'constraints':
                constraint_num = int(parts[3])  # 0, 1...
                constraint_name = parts[4]  # value or matchmode
                if 'constraints' not in params[filter_field]:
                    params[filter_field]['constraints'] = [{}]
                if len(params[filter_field]['constraints']) < constraint_num:
                    # Array values might be in wrong order
                    len_inc = constraint_num - \
                        len(params[filter_field]['constraints'])
                    for _ in range(len_inc):
                        params[filter_field]['constraints'].append([{}])
                params[filter_field][
                    'constraints'][constraint_num][constraint_name] = value
            else:
                if filter_name == 'matchMode':
                    s = params[filter_field]['value']
                    try:
                        (value, s) = fix_operator(value, s)
                    except APIError as exp:
                        return make_api_response(
                            ResponseType(exp.message, exp.code))
                    params[filter_field]['value'] = s
                params[filter_field][filter_name] = value
    try:
        retval = list_people(params)
    except APIError as exp:
        print(exp.message)
        return make_api_response(ResponseType(exp.message, exp.code))
    return make_api_response(retval)


@ app.route('/api/people/<person_id>', methods=['get'], strict_slashes=False)
def api_getperson(person_id: str) -> Response:
    """
    Retrieves a person's information based on the provided person ID.

    Parameters:
        person_id (str): The ID of the person to retrieve.

    Returns:
        Response: The response containing the person's information.

    Raises:
        TypeError: If the person ID is not an integer.
        ValueError: If the person ID is not a valid integer.
    """
    # app.logger.error(app.url_map)
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error(f'api_getperson: Invalid id {person_id}.')
        response = ResponseType(
            f'api_getperson: Virheellinen tunniste {person_id}.', 400)
        return make_api_response(response)

    return make_api_response(get_person(int_id))


@app.route('/api/people/<person_id>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deleteperson(person_id: str) -> Response:
    """
    Delete a person from the API.

    Args:
        person_id (str): The ID of the person to be deleted.

    Returns:
        Response: The response object containing the result of the deletion.
    """
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error(f'api_DeletePerson: Invalid id {person_id}.')
        response = ResponseType(
            f'api_DeletePerson: Virheellinen tunniste {person_id}.', 400)
        return make_api_response(response)
    return make_api_response(person_delete(int_id))


@app.route('/api/people/shorts/<personid>', methods=['get'])
def api_listshorts(personid: int) -> Response:
    """
    Retrieves a list of shorts for a specific person.

    Args:
        id (int): The ID of the person.

    Returns:
        Response: The response object containing the list of shorts.
    """
    try:
        int_id = int(personid)
    except (TypeError, ValueError):
        app.logger.error(f'api_ListShorts: Invalid id {personid}.')
        response = ResponseType(
            f'api_ListShorts: Virheellinen tunniste {personid}.', 400)
        return make_api_response(response)
    return make_api_response(person_shorts(int_id))


@app.route('/api/person/<personid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtoperson(personid: int, tagid: int) -> Response:
    """
    Handles the API endpoint for adding or removing a tag from a person.

    Args:
        id (int): The ID of the person.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        None
    """
    if request.method == 'PUT':
        func = person_tag_add
    elif request.method == 'DELETE':
        func = person_tag_remove

    try:
        person_id = int(personid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={personid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    retval = func(person_id, tag_id)

    return make_api_response(retval)


@app.route('/api/filter/people/<pattern>', methods=['get'])
def api_filterpeople(pattern: str) -> Response:
    """
    Filter people list.

    Pattern has to be at least three characters long. Matching is done
    from start of the name field.

    Parameters
    ----------
    pattern: str
        Pattern to search for.

    Returns
    -------

    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 3:
        app.logger.error('FilterPeople: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_people(pattern)
    return make_api_response(retval)

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


@app.route('/api/publishers/', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_publishercreateupdate() -> Response:
    """
    Create or update a publisher.

    This function is responsible for handling the '/api/publishers/' endpoint
    requests with both 'POST' and 'PUT' methods. It expects the request data to
    be in JSON format and performs input validation using the `bleach` library.

    Parameters:
    - None

    Returns:
    - A `Response` object representing the API response.

    Raises:
    - None
    """
    params = request.data.decode('utf-8')
    params = json.loads(params)
    if request.method == 'POST':
        retval = make_api_response(publisher_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(publisher_update(params))

    return retval


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
        app.logger.error(f'api_GetPubseries: Invalid id {pubseriesid}.')
        response = ResponseType(
            f'api_GetBookseries: Virheellinen tunniste {pubseriesid}.', 400)
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
        app.logger.error('FilterPubseries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_pubseries(pattern)
    return make_api_response(retval)

###
# Publisher related functions


@ app.route('/api/publishers', methods=['get'])
def api_listpublishers() -> Response:
    """
    This function is a route handler for the '/api/publishers' endpoint. It
    accepts GET requests and returns a tuple containing the response data and
    the HTTP status code.

    Parameters:
    None

    Returns:
    A tuple containing the response data and the HTTP status code.
    """
    return make_api_response(list_publishers())


@ app.route('/api/publishers/<publisherid>', methods=['get'])
def api_getpublisher(publisherid: str) -> Response:
    """
    Retrieves a publisher from the API based on the provided publisher ID.

    Parameters:
        publisherid (str): The ID of the publisher to retrieve.

    Returns:
        ResponseType: The response object containing the publisher data or an
        error message.
    """
    try:
        int_id = int(publisherid)
    except (TypeError, ValueError):
        app.logger.error(f'api_GetPublisher: Invalid id {publisherid}.')
        response = ResponseType(
            f'api_GetPublisher: Virheellinen tunniste {publisherid}.', 400)
        return make_api_response(response)

    return make_api_response(get_publisher(int_id))


@app.route('/api/filter/publishers/<pattern>', methods=['get'])
def api_filterpublishers(pattern: str) -> Response:
    """
    Filter publishers based on a given pattern.

    Args:
        pattern (str): The pattern to filter publishers.

    Returns:
        Response: The response containing the filtered publishers.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterPublishers: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = filter_publishers(pattern)
    return make_api_response(retval)


###
# Role related functions

@app.route('/api/roles/', methods=['get'])
def api_roles() -> Response:
    """
    Returns a list of contributor roles in the system in the order they are
    in the database (i.e. by id).
    """
    return make_api_response(role_list())

###
# Story related functions


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
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    retval = story_delete(short_id)

    return make_api_response(retval)


@ app.route('/api/shorts/<shortid>', methods=['get'])
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
            f'api_GetShort: Virheellinen tunniste {shortid}.', 400)
        return make_api_response(response)

    return make_api_response(get_short(int_id))


@ app.route('/api/searchshorts', methods=['post'])
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
    if request.method == 'PUT':
        func = story_tag_add
    elif request.method == 'DELETE':
        func = story_tag_remove

    try:
        int_id = int(storyid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={storyid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    retval = func(int_id, tag_id)

    return make_api_response(retval)


###
# User related functions

@ app.route('/api/users', methods=['get'])
def api_listusers() -> Response:
    """
    This function is an API endpoint that returns a list of users. It is
    decorated with the `@app.route` decorator, which maps the URL `/api/users`
    to this function. The function accepts GET requests and returns a tuple
    containing a string and an integer. The string represents the response
    body, and the integer represents the HTTP status code. The function calls
    the `make_api_response` function, passing the result of the `list_users`
    function as an argument.
    """

    return make_api_response(list_users())


@ app.route('/api/users/<userid>', methods=['get'])
def api_getuser(userid: str) -> Response:
    """
    Get a user by their ID.

    Args:
        userId (str): The ID of the user.

    Returns:
        Response: The response object containing the user information.
    """

    try:
        int_id = int(userid)
    except (TypeError, ValueError):
        app.logger.error(f'api_GetUser: Invalid id {userid}.')
        response = ResponseType(f'Virheellinen tunniste: {userid}.', 400)
        return make_api_response(response)

    return make_api_response(get_user(int_id))


###
# Tag related functions

@ app.route('/api/tags', methods=['get'])
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
        else:
            app.logger.error(f'api_tags: Invalid parameters: {args}')
            response = ResponseType(
                'app_tags: Parametrejä ei ole tuettu.', 400)
            return make_api_response(response)

    return make_api_response(tag_list())


@ app.route('/api/tags', methods=['post'])
@ jwt_admin_required()  # type: ignore
def api_tagcreate() -> Response:
    """
    Create a new tag.

    """
    url_params = request.args.to_dict()
    name = url_params['name']

    retval = tag_create(name)

    return make_api_response(retval)


@ app.route('/api/tags/<tag_id>', methods=['get'])
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
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    return make_api_response(tag_info(int_id))


@ app.route('/api/tags', methods=['put'])
@ jwt_admin_required()  # type: ignore
def api_tagrename() -> Response:
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
    # url_params = request.get_json()
    url_params = json.loads(request.data)

    try:
        int_id = int(url_params['id'])
    except (TypeError, ValueError):
        app.logger.error(
            f'api_tagrename: Invalid ID. Id = {url_params["id"]}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    name = url_params['name']
    if len(name) == 0:
        app.logger.error('api_tagrename: Empty name.')
        response = ResponseType(
            'Asiasana ei voi olla tyhjä merkkijono', status=400)
        return make_api_response(response)

    response = tag_rename(int_id, name)
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
            'Liian lyhyt hakuehto', status=400)
        return make_api_response(response)
    retval = tag_filter(pattern)
    return make_api_response(retval)


@ app.route('/api/tags/<id>/merge/<id2>', methods=['post'])
@ jwt_admin_required()  # type: ignore
def api_tagmerge(id1: int, id2: int) -> Response:
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
        id_to = int(id1)
        id_from = int(id2)
    except (TypeError, ValueError):
        app.logger.error(f'api_tagmerge: Invalid id. Id = {id1}.')
        response = ResponseType('Virheellinen asiasanan tunniste.', status=400)
        return make_api_response(response)

    retval = tag_merge(id_to, id_from)
    return make_api_response(retval)


@ app.route('/api/tags/<tagd>', methods=['delete'])
@ jwt_admin_required()  # type: ignore
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
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    response = tag_delete(int_id)
    retval = make_api_response(response)
    return retval


###
# Work related functions

# @ app.route('/api/works', methods=['get'])
# def api_getworks() -> Response:
#     """
#     Get works by author from the API.

#     Parameters:
#         None

#     Returns:
#         Response: The response object containing the works by the specified
#         author.
#     """
#     url_params = request.args.to_dict()

#     if 'author' in url_params:
#         retval = get_works_by_author(url_params['author'])

#     return make_api_response(retval)


@ app.route('/api/works/<workid>', methods=['get'])
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
        response = ResponseType(f'Virheellinen tunniste: {workid}.', 400)
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
    params = json.loads(params)
    if request.method == 'POST':
        retval = make_api_response(work_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(work_update(params))

    return retval


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
        return make_api_response(ResponseType(f'Virheellinen tunniste: \
                                              {workid}.', 400))

    return make_api_response(work_delete(int_id))


@app.route('/api/works/shorts/<workid>', methods=['get'])
def api_workshorts(workid: int) -> Response:
    """ Get shorts in a collection. """
    try:
        int_id = int(workid)
    except (TypeError, ValueError):
        app.logger.error(f'api_WorkShorts: Invalid id {workid}.')
        response = ResponseType(f'Virheellinen tunniste: {workid}.', 400)
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
    if request.method == 'PUT':
        func = work_tag_add
    elif request.method == 'DELETE':
        func = work_tag_remove

    try:
        work_id = int(workid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={workid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return make_api_response(response)

    retval = func(work_id, tag_id)

    return make_api_response(retval)


@ app.route('/api/worksbyinitial/<letter>', methods=['get'])
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


@ app.route('/api/searchworks', methods=['post'])
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


# @ app.route('/api/worktypes', methods=['get'])
# def worktypes() -> Response:
#     """
#     Returns a list of all of the work types in the system in the order they
#     are in the database (i.e. by id).
#     """
#     return MakeApiResponse(WorkTypesList())

###
# Misc functions

@ app.route('/api/firstlettervector/<target>', methods=['get'])
def firstlettervector(target: str) -> Tuple[str, int]:
    """Get first letters for for target type.

    This function is used internally by the UI to create
    links to various pages, e.g. a list for choosing books
    based on the first letter of the author.

    Parameters
    ----------
    target: str
        Either "works" or "stories".

    Returns
    -------
    List[str, int]
        str is the return value in JSON. int is http return code.
        Str contains a dictionary where each item's key is a letter and
        value is the count of items (e.g. works).

    """
    # url_params = request.args.to_dict()
    retval = get_author_first_letters(target)

    return retval
