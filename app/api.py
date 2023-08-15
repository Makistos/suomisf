import re
from urllib import response
import json
from typing import Any, Tuple, NewType, Type, Union, List, Dict
from app.model import *
from app import app
import bleach  # type: ignore
from flask import request # type: ignore
from flask.wrappers import Response # type: ignore
from app.route_helpers import admin_required, new_session
from app.api_errors import APIError
from app.api_errors import APIError
from app.api_jwt import jwt_admin_required
import time
from app.impl import *
from app.impl_articles import *
from app.impl_bookseries import *
from app.impl_editions import *
from app.impl_issues import *
from app.impl_magazines import *
from app.impl_people import *
from app.impl_publishers import *
from app.impl_pubseries import *
from app.impl_shorts import *
from app.impl_tags import *
from app.impl_users import *
from app.impl_works import *
from flask_jwt_extended import jwt_required
import urllib
import jsonschema
from jsonschema import validate

default_mimetype = 'application/json'  # Data is always returned as JSON


ConstraintType = NewType('ConstraintType', List[Dict[str, str]])
FilterType = NewType('FilterType', Dict[str, Union[str, ConstraintType]])


###
# Generic functions

def MakeAPIError(response: ResponseType) -> Response:
    return Response(response=list(json.dumps({'msg': response.response})),
                    status=response.status,
                    mimetype=default_mimetype)


def MakeApiResponse(response: ResponseType) -> Response:
    # Response is made into a list for performance as per Flask documentation
    if response.status >= 400 and response.status <= 511:
        return MakeAPIError(response)

    return Response(response=list(json.dumps(response.response)),
                    status=response.status,
                    mimetype=default_mimetype)


def login_options(request: Any) -> Dict[str, str]:
    options = {}
    try:
        if request.json:
            options['username'] = request.json['username']
            options['password'] = request.json['password']
        else:
            options['username'] = request.json['authorization']['username']
            options['password'] = request.json['authorization']['password']
    except (TypeError, KeyError) as exp:
        response = ResponseType('api_login: Virheelliset parametrit.', 401)
        return MakeApiResponse(response)

    if not options['username'] or not options['password']:
        response = ResponseType('api_login: Virheelliset parametrit.', 401)
        return MakeApiResponse(response)

    return options

def fixOperator(op: str, value: str) -> Tuple[str, str]:

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
        raise APIError('Invalid filter operation %s' % op, 405)

###
# User control related functions

# This function is used to log in the user using the HTTP POST method.
# 1. The function checks if the parameters are passed correctly.
# 2. If the parameters are not passed correctly, the function returns a 401 error.
# 3. If the parameters are passed correctly, the function calls the LoginUser function.

@app.route('/api/login', methods=['post'])
@jwt_required(optional=True)
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
    retval = LoginUser(options)
    return retval

@app.route('/api/refresh', methods=['post'])
@jwt_required(refresh=True)
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
        response = ResponseType('api_login: Virheelliset parametrit.', 401)
        return MakeApiResponse(response)

    if not options['username']:
        response = ResponseType('api_login: Virheelliset parametrit.', 401)
        return MakeApiResponse(response)
    return RefreshToken(options)


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
    return MakeApiResponse(GetFrontpageData())


###
# Generic search functions

@ app.route('/api/search/<pattern>', methods=['get', 'post'])
def api_Search(pattern: str) -> Tuple[str, int]:
    retval = ''
    retcode = 200
    results: SearchResult = []

    # searchword = request.args.get('search', '')
    pattern = bleach.clean(pattern)
    words = pattern.split(' ')

    session = new_session()
    results = SearchWorks(session, words)
    results += SearchPeople(session, words)
    results = sorted(results, key=lambda d: d['score'], reverse=True)
    return json.dumps(results), retcode


###
# Alias related functions

@app.route('/api/filter/alias/<id>', methods=['get'])
def api_FilterAlias(id: str) -> Response:
    try:
        person_id = int(id)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_FilterAlias: Invalid id {id}.')
        response = ResponseType(f'Virheellinen tunniste: {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(FilterAliases(person_id))


###
# Article related functions

@ app.route('/api/articles/<articleId>', methods=['get'])
def api_GetArticle(articleId: str) -> Response:

    try:
        id = int(articleId)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetArticle: Invalid id {articleId}.')
        response = ResponseType(
            f'api_GetArticle: Virheellinen tunniste {articleId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetArticle(id))


@app.route('/api/articles/<articleId>/tags', methods=['get'])
def api_GetArticleTags(articleId: int) -> Response:

    try:
        article_id = int(articleId)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetArticleTags: Invalid id {articleId}.')
        response = ResponseType(
            f'apiGetArticleTags: Virheellinen tunniste {articleId}.', 400)
        return MakeApiResponse(response)

    retval = ArticleTags(article_id)
    return MakeApiResponse(retval)

@app.route('/api/articles/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()
def api_tagToArticle(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = ArticleTagAdd
    elif request.method == 'DELETE':
        func = ArticleTagRemove

    try:
        article_id = int(id)
        tag_id = int(tagid)
    except (TypeError, ValueError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(article_id, tag_id)

    return MakeApiResponse(retval)


###
# Binding related functions

@app.route('/api/bindings', methods=['get'])
def api_Bindings() -> Response:
    retval = MakeApiResponse(BindingGetAll())
    return retval


###
# Bookseries related functions

@ app.route('/api/bookseries', methods=['get'])
def api_ListBookseries() -> Response:
    return MakeApiResponse(ListBookseries())

BookseriesSchema = {
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "properties": {
                "id": {"type": ["integer", "null"]},
                "name": {"type": "string"},
                "orig_name": {"type": "string"},
                "important": {"type": "boolean"},
            },
            "required": ["name"],
        },
    },
}

@app.route('/api/bookseries', methods=['post', 'put'])
@jwt_admin_required()   # type: ignore
def api_BookseriesCreateUpdate() -> Response:
    try:
        params = json.loads(bleach.clean(request.data.decode('utf-8')))
    except (TypeError, ValueError) as exp:
        app.logger.error('api_BookseriesCreateUpdate: Invalid JSON.')
        response = ResponseType('api_BookseriesCreateUpdate: Virheelliset parametrit.', 400)
        return MakeApiResponse(response)
    try:
        validate(instance=params, schema=BookseriesSchema)
    except jsonschema.exceptions.ValidationError as exp:
        app.logger.error('api_BookseriesCreateUpdate: Invalid JSON.')
        response = ResponseType('api_BookseriesCreateUpdate: Virheelliset parametrit.', 400)
        return MakeApiResponse(response)
    if request.method == 'POST':
        retval = MakeApiResponse(BookseriesCreate(params))
    elif request.method == 'PUT':
        retval = MakeApiResponse(BookseriesUpdate(params))

    return retval


@app.route('/api/bookseries/<bookseriesId>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_BookseriesDelete(bookseriesId: str) -> Response:
    return MakeApiResponse(BookseriesDelete(bookseriesId))


@ app.route('/api/bookseries/<bookseriesId>', methods=['get'])
def api_GetBookseries(bookseriesId: str) -> Response:

    try:
        id = int(bookseriesId)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetBookseries: Invalid id {bookseriesId}.')
        response = ResponseType(
           f'apiGetBookseries: Virheellinen tunniste {bookseriesId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetBookseries(id))

@app.route('/api/filter/bookseries/<pattern>', methods=['get'])
def api_FilterBookseries(pattern: str) -> Response:
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterBookseries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return MakeApiResponse(response)
    retval = FilterBookseries(pattern)
    return MakeApiResponse(retval)


###
# Change related functions

@ app.route('/api/changes', methods=['get'])
def api_Changes() -> Tuple[str, int]:
    url_params = request.args.to_dict()

    params: Dict[str, Any] = {}
    for (param, value) in url_params.items():
        # param, value = p.split('=')
        if value == 'null' or value == 'undefined':
            value = None
        params[param] = value

    try:
        retval = GetChanges(params)
    except APIError as exp:
        app.logger.error('Exception in api_Changes: ' + str(exp))
        response = Response('api_Changes: poikkeus.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(retval)


###
# Country related functions

@ app.route('/api/countries', methods=['get'])
def countries() -> Response:
    """
    Returns a list of all of the countries in the system ordered by name.
    """
    return MakeApiResponse(CountryList())

@app.route('/api/filter/countries/<pattern>', methods=['get'])
def api_FilterCountries(pattern: str) -> Response:
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterCountries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return MakeApiResponse(response)
    retval = FilterCountries(pattern)
    return MakeApiResponse(retval)

###
# Edition related functions

@app.route('/api/editions', methods=['post', 'put'])
@jwt_admin_required()
def api_EditionCreateUpdate() -> Response:
    params = bleach.clean(request.data.decode('utf-8'))
    params = json.loads(params)
    if request.method == 'POST':
        retval = MakeApiResponse(EditionCreate(params))
    elif request.method == 'PUT':
        retval = MakeApiResponse(EditionUpdate(params))

    return retval

@app.route('/api/editions/<editionId>', methods=['delete'])
@jwt_admin_required()
def api_EditionDelete(editionId: str) -> Response:
    return MakeApiResponse(EditionDelete(editionId))

@app.route('/api/editions/<id>/images', methods=['post'])
@jwt_admin_required()
def api_uploadEditionImage(id: str) -> Response:
    try:
        file = request.files['file']
    except KeyError as exp:
        app.logger.error('api_uploadEditionImage: File not found.')
        response = ResponseType('Tiedosto puuttuu', status=400)
        return MakeApiResponse(response)

    retval = MakeApiResponse(
        EditionImageUpload(id, file))
    return retval

@app.route('/api/editions/<id>/images/<imageid>', methods=['delete'])
@jwt_admin_required()
def api_deleteEditionImage(id: str, imageid: str) -> Response:
    retval = MakeApiResponse(
        EditionImageDelete(id, imageid))
    return retval


###
# Genre related functions

@ app.route('/api/genres', methods=['get'])
def genres() -> Response:
    """
    Returns a list of all of the genres in the system in the order
    they are in the database (i.e. by id).
    """
    return MakeApiResponse(GenreList())


###
# Issue related functions
@ app.route('/api/issues/<issueId>', methods=['get'])
def api_GetIssueForMagazine(issueId: str) -> Response:

    try:
        id = int(issueId)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetIssueForMagazine: Invalid id {issueId}.')
        response = ResponseType(
            f'api_GetIssueForMagazine: Virheellinen tunniste {issueId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetIssue(id))

@ app.route('/api/issues/<issueId>/tags', methods=['get'])
def api_GetIssueTags(issueId: str) -> Response:

    try:
        id = int(issueId)
    except:
        app.logger.error(f'api_GetIssueTags: Invalid id {issueId}.')
        response = ResponseType(
            f'api_GetIssueTags: Virheellinen tunniste {issueId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetIssueTags(id))

@app.route('/api/issue/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()
def api_tagToIssue(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = IssueTagAdd
    elif request.method == 'DELETE':
        func = IssueTagRemove

    try:
        issue_id = int(id)
        tag_id = int(tagid)
    except (TypeError, ValueError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(issue_id, tag_id)

    return MakeApiResponse(retval)


###
# Language related functions

@app.route('/api/filter/languages/<pattern>', methods=['get'])
def api_FilterLanguages(pattern: str) -> Response:
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterLanguages: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return MakeApiResponse(response)
    retval = FilterLanguages(pattern)
    return MakeApiResponse(retval)


###
# Magazine related functions

@ app.route('/api/magazines', methods=['get'])
def api_ListMagazines() -> Response:

    return MakeApiResponse(ListMagazines())


@ app.route('/api/magazines/<magazineId>', methods=['get'])
def api_GetMagazine(magazineId: str) -> Response:

    try:
        id = int(magazineId)
    except:
        app.logger.error(f'api_GetMagazine: Invalid id {magazineId}.')
        response = ResponseType(
            f'api_GetMagazine: Virheellinen tunniste {magazineId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetMagazine(id))


@ app.route('/api/magazines/<magazineId>', methods=['patch'])
def api_UpdateMagazine(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    schema = MagazineSchema()

    # body = parser.parse(schema, request, location='json')

    # return UpdateMagazine(options, "")


@ app.route('/api/magazines/<magazineId>/issues', methods=['get'])
def api_GetMagazineIssues(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    # return GetMagazineIssues(options)


@ app.route('/api/magazines/<magazineId>/publisher', methods=['get'])
def api_GetMagazinePublisher(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    # return GetMagazinePublisher(options)


@ app.route('/api/magazines/<magazineId>/tags', methods=['get'])
def api_GetMagazineTags(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    # return GetMagazineTags(options)

###
# People related functions

@ app.route('/api/people/', methods=['get'])
def api_GetPeople() -> Tuple[str, int]:
    # This function receives parameters in the form of
    # first=50&...filters_name_operator=1&filters_name_constraints_value=null..
    # I.e. the original dictionary has been translated into variables. The
    # Javascript dictionary looks like this:
    # {
    #     first: 0,
    #     rows: 50,
    #     page: 0,
    #     sortField: "name",
    #     sortOrder: 1,
    #     multiSortMeta: null,
    #     filters: {
    #         global: { value: null, matchMode: FilterMatchMode.CONTAINS },
    #         name: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.STARTS_WITH }] },
    #         dob: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.EQUALS }] },
    #         dod: { operator: FilterOperator.AND, constraints: [{ value: null, matchMode: FilterMatchMode.EQUALS }] },
    #         nationality: { value: null, matchMode: FilterMatchMode.EQUALS },
    #         work_count: { value: null, matchMode: FilterMatchMode.EQUALS },
    #         story_count: { value: null, matchMode: FilterMatchMode.EQUALS },
    #         roles: { value: null, matchMode: FilterMatchMode.EQUALS }
    #     }
    # }
    #
    # This function will translate the parameter list back to a similar Python
    # dict.
    # Those constants in the list are explained in the implementation function,
    # but they are simple self-explaining strings.

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
            # has a simple value, like filters_global_value=null or a constraint
            # e.g. filters_name_constraints_0_value=null.
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
                params[filter_field]['constraints'][constraint_num][constraint_name] = value
            else:
                if filter_name == 'matchMode':
                    s = params[filter_field]['value']
                    try:
                        (value, s) = fixOperator(value, s)
                    except APIError as exp:
                        return exp.message, exp.code
                    params[filter_field]['value'] = s
                params[filter_field][filter_name] = value
    try:
        retval = ListPeople(params)
    except APIError as exp:
        print(exp.message)
        return exp.message, exp.code
    return retval


@ app.route('/api/people/<person_id>', methods=['get'])
def api_GetPerson(person_id: str) -> Response:
    try:
        id = int(person_id)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetPerson: Invalid id {person_id}.')
        response = ResponseType(
            f'api_GetPerson: Virheellinen tunniste {person_id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetPerson(id))

@app.route('/api/person/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()
def api_tagToPerson(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = PersonTagAdd
    elif request.method == 'DELETE':
        func = PersonTagRemove

    try:
        person_id = int(id)
        tag_id = int(tagid)
    except (TypeError, ValueError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(person_id, tag_id)

    return MakeApiResponse(retval)

@app.route('/api/filter/people/<pattern>', methods=['get'])
def api_FilterPeople(pattern: str) -> Response:
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
        return MakeApiResponse(response)
    retval = FilterPeople(pattern)
    return MakeApiResponse(retval)

###
# Pubseries related functions

@ app.route('/api/pubseries', methods=['get'])
def api_ListPubseries() -> Tuple[str, int]:
    return MakeApiResponse(ListPubseries())

@app.route('/api/publishers/', methods=['post', 'put'])
@jwt_admin_required()
def api_PublisherCreateUpdate() -> Response:
    params = bleach.clean(request.data.decode('utf-8'))
    params = json.loads(params)
    if request.method == 'POST':
        retval = MakeApiResponse(PublisherAdd(params))
    elif request.method == 'PUT':
        retval = MakeApiResponse(PublisherUpdate(params))

    return retval

@ app.route('/api/pubseries/<pubseriesId>', methods=['get'])
def api_GetPubseries(pubseriesId: str) -> Response:
    try:
        id = int(pubseriesId)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetPubseries: Invalid id {pubseriesId}.')
        response = ResponseType(
            f'api_GetBookseries: Virheellinen tunniste {pubseriesId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetPubseries(id))

@app.route('/api/filter/pubseries/<pattern>', methods=['get'])
def api_FilterPubseries(pattern: str) -> Response:
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterPubseries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return MakeApiResponse(response)
    retval = FilterPubseries(pattern)
    return MakeApiResponse(retval)

###
# Publisher related functions

@ app.route('/api/publishers', methods=['get'])
def api_ListPublishers() -> Tuple[str, int]:
    return MakeApiResponse(ListPublishers())

@ app.route('/api/publishers/<id>', methods=['get'])
def api_GetPublisher(id: str) -> ResponseType:
    try:
        publisher_id = int(id)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetPublisher: Invalid id {id}.')
        response = ResponseType(
            f'api_GetPublisher: Virheellinen tunniste {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetPublisher(publisher_id))

@app.route('/api/filter/publishers/<pattern>', methods=['get'])
def api_FilterPublishers(pattern: str) -> Response:
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterPublishers: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return MakeApiResponse(response)
    retval = FilterPublishers(pattern)
    return MakeApiResponse(retval)


###
# Role related functions

@app.route('/api/roles/', methods=['get'])
def api_roles() -> Response:
    """
    Returns a list of contributor roles in the system in the order they are
    in the database (i.e. by id).
    """
    return MakeApiResponse(RoleList())

###
# Story related functions

@app.route('/api/shorts/', methods=['post', 'put'])
@jwt_admin_required()
def api_ShortCreateUpdate() -> Response:
    params = bleach.clean(request.data.decode('utf-8'))
    params = json.loads(params)
    if request.method == 'POST':
        retval = MakeApiResponse(StoryAdd(params))
    elif request.method == 'PUT':
        retval = MakeApiResponse(StoryUpdate(params))

    return retval

@app.route('/api/shorts/<id>', methods=['delete'])
@jwt_admin_required()
def api_ShortDelete(id: int) -> Response:
    try:
        short_id = int(id)
    except (TypeError, ValueError) as exp:
        app.logger.error(
            f'api_ShortDelete: Invalid id. id={id}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = StoryDelete(short_id)

    return MakeApiResponse(retval)

@ app.route('/api/shorts/<shortId>', methods=['get'])
def api_GetShort(shortId: str) -> Response:
    try:
        id = int(shortId)
    except:
        app.logger.error(f'api_GetShort: Invalid id {shortId}.')
        response = ResponseType(
            f'api_GetShort: Virheellinen tunniste {shortId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetShort(id))

@ app.route('/api/searchshorts', methods=['post'])
def api_searchShorts() -> Response:
    st = time.time()
    params = json.loads(request.data)
    retval = SearchShorts(params)
    et = time.time()
    elapsed = str(et-st)
    app.logger.warn('SearchShorts: done in ' + elapsed + " s")
    return MakeApiResponse(retval)


@app.route('/api/shorttypes', methods=['get'])
def api_shortTypes() -> Response:
    return MakeApiResponse(GetShortTypes())

@app.route('/api/story/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()
def api_tagToStory(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = StoryTagAdd
    elif request.method == 'DELETE':
        func = StoryTagRemove

    try:
        story_id = int(id)
        tag_id = int(tagid)
    except (TypeError, ValueError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(story_id, tag_id)

    return MakeApiResponse(retval)


###
# User related functions

@ app.route('/api/users', methods=['get'])
def api_ListUsers() -> Tuple[str, int]:

    return MakeApiResponse(ListUsers())


@ app.route('/api/users/<userId>', methods=['get'])
def api_GetUser(userId: str) -> Response:

    try:
        id = int(userId)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_GetUser: Invalid id {id}.')
        response = ResponseType(f'Virheellinen tunniste: {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetUser(id))


###
# Tag related functions

@ app.route('/api/tags', methods=['get'])
def api_tags() -> Response:
    if request.args:
        args = request.args.to_dict()
        if 'search' in args:
            pattern = bleach.clean(args['search'])
            return MakeApiResponse(TagSearch(pattern))
        else:
            app.logger.error(f'api_tags: Invalid parameters: ' + str(args))
            response = ResponseType(
                'app_tags: Parametrejä ei ole tuettu.', 400)
            return MakeApiResponse(response)

    return MakeApiResponse(TagList())

@ app.route('/api/tags', methods=['post'])
@ jwt_admin_required()
def api_tagCreate() -> Tuple[str, int]:
    """
    Create a new tag.

    """
    url_params = request.args.to_dict()
    name = url_params['name']
    name = bleach.clean(name)

    retval = TagCreate(name)

    return MakeApiResponse(retval)

@ app.route('/api/tags/<id>', methods=['get'])
def api_tag(id: str) -> Response:
    try:
        tag_id = int(id)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_tag: Invalid id {id}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    return MakeApiResponse(TagInfo(tag_id))

@ app.route('/api/tags', methods=['put'])
@ jwt_admin_required()
def api_tagRename() -> Response:
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
    url_params = request.get_json()

    try:
        id = int(url_params['id'])
    except (TypeError, ValueError) as exp:
        app.logger.error(
            'api_tagRename: Invalid ID. Id = {}.'.format(url_params['id']))
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    name = bleach.clean(url_params['name'])
    if len(name) == 0:
        app.logger.error('api_tagRename: Empty name.')
        response = ResponseType(
            'Asiasana ei voi olla tyhjä merkkijono', status=400)
        return MakeApiResponse(response)

    name = bleach.clean(name)
    response = TagRename(id, name)
    return MakeApiResponse(response)

@app.route('/api/filter/tags/<pattern>', methods=['get'])
def api_FilterTags(pattern: str) -> Response:
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterTags: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=400)
        return MakeApiResponse(response)
    retval = TagFilter(pattern)
    return MakeApiResponse(retval)

@ app.route('/api/tags/<id>/merge/<id2>', methods=['post'])
@ jwt_admin_required()
def api_tagMerge(id: int, id2: int) -> Tuple[str, int]:
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
        idTo = int(id)
        idFrom = int(id2)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_tagMerge: Invalid id. Id = {id}.')
        response = ResponseType('Virheellinen asiasanan tunniste.', status=400)
        return MakeApiResponse(response)

    retval = TagMerge(idTo, idFrom)
    return MakeApiResponse(retval)

@ app.route('/api/tags/<id>', methods=['delete'])
@ jwt_admin_required()
def api_tagDelete(id: int) -> Response:
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
        id = int(id)
    except (TypeError,  ValueError) as exp:
        app.logger.error(f'api_tagDelete: Invalid ID. Id = {id}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    response = TagDelete(id)
    retval = MakeApiResponse(response)
    return retval


###
# Work related functions

@ app.route('/api/works', methods=['get'])
def api_GetWorks() -> Response:
    url_params = request.args.to_dict()

    if 'author' in url_params:
        retval = GetWorksByAuthor(url_params['author'])

    return MakeApiResponse(retval)


@ app.route('/api/works/<id>', methods=['get'])
def api_getWork(id: str) -> Response:
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
                "imported_string": "\n<b>Kivineitsyt</b>. (Stone Virgin, 1985). Suom Aira Buffa. WSOY 1986. [F].",
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
                    "imported_string": "\n<b>Kivineitsyt</b>. (Stone Virgin, 1985). Suom Aira Buffa. WSOY 1986. [F].",
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
        work_id = int(id)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_getWork: Invalid id {id}.')
        response = ResponseType(f'Virheellinen tunniste: {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetWork(work_id))


@app.route('/api/works/', methods=['post', 'put'])
@jwt_admin_required()  # type: ignore
def api_WorkCreateUpdate() -> Response:
    params = bleach.clean(request.data.decode('utf-8'))
    params = json.loads(params)
    if request.method == 'POST':
        retval = MakeApiResponse(WorkAdd(params))
    elif request.method == 'PUT':
        retval = MakeApiResponse(WorkUpdate(params))

    return retval

@app.route('/api/works/<id>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_WorkDelete(id: str) -> Response:
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
        work_id = int(id)
    except (TypeError, ValueError) as exp:
        app.logger.error(f'api_WorkDelete: Invalid id {id}.')
        return MakeApiResponse(ResponseType(f'Virheellinen tunniste: {id}.', 400))

    return MakeApiResponse(WorkDelete(work_id))

@app.route('/api/worktypes', methods=['get'])
def api_WorkTypes() -> Response:
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
    retval = MakeApiResponse(WorkTypeGetAll())
    return retval

@app.route('/api/work/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagToWork(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = WorkTagAdd
    elif request.method == 'DELETE':
        func = WorkTagRemove

    try:
        work_id = int(id)
        tag_id = int(tagid)
    except (TypeError, ValueError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(work_id, tag_id)

    return MakeApiResponse(retval)

@ app.route('/api/worksbyinitial/<letter>', methods=['get'])
def api_searchWorksByInitial(letter: str) -> Response:
    params = {}
    params['letter'] = letter
    retval = SearchWorksByAuthor(params)
    return MakeApiResponse(retval)

@ app.route('/api/searchworks', methods=['post'])
def api_searchWorks() -> Response:
    params = json.loads(request.data)
    retval = SearchBooks(params)

    return MakeApiResponse(retval)


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
    url_params = request.args.to_dict()
    retval = GetAuthorFirstLetters(target)

    return retval
