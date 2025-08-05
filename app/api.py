# pylint: disable=too-many-lines
""" API functions. """
import json
from typing import Any, Tuple, NewType, Union, List, Dict
import bleach
from flask_jwt_extended import jwt_required
from flask import request
from flask.wrappers import Response
from app.api_helpers import make_api_error, make_api_response
from app.impl import (ResponseType, get_frontpage_data, SearchResult,
                      filter_languages,
                      filter_link_names, genre_list,
                      get_latest_covers)
from app.api_errors import APIError
from app.impl_editions import get_bindings
from app.impl_people import (filter_aliases,
                             get_author_first_letters)
from app.impl_users import (login_user, refresh_token, register_user)
from app.route_helpers import new_session
from app.types import HttpResponseCode
from app import app

ConstraintType = NewType('ConstraintType', List[Dict[str, str]])
FilterType = NewType('FilterType', Dict[str, Union[str, ConstraintType]])


###
# Generic functions


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
        app.logger.error('Virheelliset parametrit: %s.', exp)
        return {}

    if not options['username'] or not options['password']:
        app.logger.error('api_login: Virheelliset parametrit.')
        return {}

    return options


def fix_operator(operator: str, value: str) -> Tuple[str, str]:
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

    if operator == 'equals':
        return ('eq', value)
    if operator == 'notequals':
        return ('ne', value)
    if operator == 'startsWith':
        if value:
            value = value + '%'
        return ('ilike', value)
    if operator == 'endsWith':
        if value:
            value = '%' + value
        return ('ilike', value)
    if operator == 'contains':
        if value:
            value = '%' + value + '%'
        return ('ilike', value)
    if operator == 'notContains':
        if value:
            value = '%' + value + '%'
        # Needs special attention in filtering
        return ('notContains', value)
    if operator == 'lt':
        return ('lt', value)
    if operator == 'lte':
        return ('lte', value)
    if operator == 'gt':
        return ('gt', value)
    if operator == 'gte':
        return ('gte', value)
    if operator == 'in':
        # Needs special attention in filtering
        return ('in', value)
    raise APIError(f'Invalid filter operation {operator}',
                   HttpResponseCode.METHOD_NOT_ALLOWED.value)

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
        err = ResponseType('Virheellinen kirjautuminen',
                           HttpResponseCode.UNAUTHORIZED.value)
        return make_api_error(err)
    retval = login_user(options)
    return retval


@app.route('/api/register', methods=['post'])
def api_register() -> Response:
    options = login_options(request)
    if not options:
        err = ResponseType('Virheellinen rekisteröinti',
                           HttpResponseCode.UNAUTHORIZED.value)
        return make_api_error(err)
    retval = register_user(options)
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
            if 'username' in request.json:
                options['username'] = request.json['username']
            elif 'authorization' in request.json:
                options['username'] = request.json['authorization']['username']
    except (TypeError, KeyError) as exp:
        response = ResponseType(f'api_login: Virheelliset parametrit: {exp}.',
                                HttpResponseCode.UNAUTHORIZED.value)
        return make_api_response(response)

    if 'username' not in options:
        response = ResponseType('api_login: Virheelliset parametrit.',
                                HttpResponseCode.UNAUTHORIZED.value)
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
@app.route('/api/search/<pattern>', methods=['get', 'post'])
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

    pattern = bleach.clean(pattern)

    session = new_session()
    results = search_with_fts(session, pattern)
    return json.dumps(results[0:50]), retcode


def search_with_fts(session: Any, search_term: str) -> SearchResult:
    """
    Search using PostgreSQL full-text search across multiple tables.

    Args:
        session: Database session
        search_term (str): The search term to query

    Returns:
        SearchResult: List of search results with consistent format
    """
    from sqlalchemy import text

    query = text("""
    WITH query AS (
      SELECT plainto_tsquery('voikko', :search_term) AS q
    )

    SELECT
      w.id,
      w.title,
      w.description AS desc,
      'work' AS table,
      ts_rank(w.fts, q.q) AS rank,
      1 AS table_order,
      (ts_rank(w.fts, q.q) * 10.0 + (12 - 1)) AS combined_score
    FROM work w, query q
    WHERE w.fts @@ q.q

    UNION ALL

    SELECT
      e.id,
      e.title,
      '' AS desc,
      'edition' AS table,
      ts_rank(e.fts, q.q) AS rank,
      2 AS table_order,
      (ts_rank(e.fts, q.q) * 10.0 + (12 - 2)) AS combined_score
    FROM edition e, query q
    WHERE e.fts @@ q.q

    UNION ALL

    SELECT
      p.id,
      p.name AS title,
      p.bio AS desc,
      'person' AS table,
      ts_rank(p.fts, q.q) AS rank,
      3 AS table_order,
      (ts_rank(p.fts, q.q) * 10.0 + (12 - 3)) AS combined_score
    FROM person p, query q
    WHERE p.fts @@ q.q

    UNION ALL

    SELECT
      s.id,
      s.title,
      '' AS desc,
      'shortstory' AS table,
      ts_rank(s.fts, q.q) AS rank,
      4 AS table_order,
      (ts_rank(s.fts, q.q) * 10.0 + (12 - 4)) AS combined_score
    FROM shortstory s, query q
    WHERE s.fts @@ q.q

    UNION ALL

    SELECT
      t.id,
      t.name AS title,
      t.description AS desc,
      'tag' AS table,
      ts_rank(t.fts, q.q) AS rank,
      5 AS table_order,
      (ts_rank(t.fts, q.q) * 10.0 + (12 - 5)) AS combined_score
    FROM tag t, query q
    WHERE t.fts @@ q.q

    UNION ALL

    SELECT
      bs.id,
      bs.name AS title,
      '' AS desc,
      'bookseries' AS table,
      ts_rank(bs.fts, q.q) AS rank,
      6 AS table_order,
      (ts_rank(bs.fts, q.q) * 10.0 + (12 - 6)) AS combined_score
    FROM bookseries bs, query q
    WHERE bs.fts @@ q.q

    UNION ALL

    SELECT
      ps.id,
      ps.name AS title,
      '' AS desc,
      'pubseries' AS table,
      ts_rank(ps.fts, q.q) AS rank,
      7 AS table_order,
      (ts_rank(ps.fts, q.q) * 10.0 + (12 - 7)) AS combined_score
    FROM pubseries ps, query q
    WHERE ps.fts @@ q.q

    UNION ALL

    SELECT
      pub.id,
      pub.name AS title,
      pub.description AS desc,
      'publisher' AS table,
      ts_rank(pub.fts, q.q) AS rank,
      8 AS table_order,
      (ts_rank(pub.fts, q.q) * 10.0 + (12 - 8)) AS combined_score
    FROM publisher pub, query q
    WHERE pub.fts @@ q.q

    UNION ALL

    SELECT
      m.id,
      m.name AS title,
      m.description AS desc,
      'magazine' AS table,
      ts_rank(m.fts, q.q) AS rank,
      9 AS table_order,
      (ts_rank(m.fts, q.q) * 10.0 + (12 - 9)) AS combined_score
    FROM magazine m, query q
    WHERE m.fts @@ q.q

    UNION ALL

    SELECT
      i.id,
      i.title,
      i.notes AS desc,
      'issue' AS table,
      ts_rank(i.fts, q.q) AS rank,
      10 AS table_order,
      (ts_rank(i.fts, q.q) * 10.0 + (12 - 10)) AS combined_score
    FROM issue i, query q
    WHERE i.fts @@ q.q

    UNION ALL

    SELECT
      a.id,
      a.name AS title,
      a.description AS desc,
      'award' AS table,
      ts_rank(a.fts, q.q) AS rank,
      11 AS table_order,
      (ts_rank(a.fts, q.q) * 10.0 + (12 - 11)) AS combined_score
    FROM award a, query q
    WHERE a.fts @@ q.q

    ORDER BY combined_score DESC, title;
    """)

    try:
        result = session.execute(query, {'search_term': search_term})
        rows = result.fetchall()

        # Convert to the expected format matching current SearchResult
        formatted_results = []
        for row in rows:
            formatted_results.append({
                'id': row[0],
                'img': '',
                'header': row[1],
                'description': row[2] or '',
                'type': row[3],
                'score': float(row[6])  # Use combined_score for consistency
            })

        return formatted_results

    except Exception as e:
        app.logger.error(f'search_with_fts: Database error: {e}')
        return []

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
        app.logger.error('api_filteralias: Invalid id %s.', personid)
        response = ResponseType(f'Virheellinen tunniste: {personid}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(filter_aliases(int_id))


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


@app.route('/api/genres', methods=['get'])
def genres() -> Response:
    """
    Returns a list of all of the genres in the system in the order
    they are in the database (i.e. by id).
    """
    return make_api_response(genre_list())


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
            'Liian lyhyt hakuehto', status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    retval = filter_languages(pattern)
    return make_api_response(retval)

###
# Latest additions


@app.route('/api/latest/covers/<count>', methods=['get'])
def api_latestcovers(count: int) -> Response:
    """
    Get the latest covers.

    Args:
        count (int): The number of covers to return.

    Returns:
        Response: The response object containing the list of latest covers.

    Raises:
        ValueError: If the count is not an integer.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        app.logger.error(f'api_latestcovers: Invalid count {count}.')
        response = ResponseType(
            f'api_latestcovers: Virheellinen maara {count}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_latest_covers(count))

###
# Misc functions


@app.route('/api/firstlettervector/<target>', methods=['get'])
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


###
# Edition related functions

@app.route('/api/editions/<edition_id>/work', methods=['get'])
def api_edition_work(edition_id: str) -> Response:
    """
    Get the work ID for a given edition ID.

    Args:
        edition_id (str): The ID of the edition.

    Returns:
        Response: The response object containing the work ID.

    Raises:
        ValueError: If the edition_id is not a valid integer.
    """
    try:
        int_edition_id = int(edition_id)
    except (ValueError, TypeError):
        app.logger.error('api_edition_work: Invalid edition id %s.',
                         edition_id)
        response = ResponseType(f'Virheellinen painos tunniste: {edition_id}.',
                                HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    from app.impl_editions import get_edition_work
    return make_api_response(get_edition_work(int_edition_id))
