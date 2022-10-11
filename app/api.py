import re
from urllib import response
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from typing import Any, Tuple, NewType, Type, Union, List, Dict
from app.model import *
from app import app
import bleach
from flask import request
from flask.wrappers import Response
from app.route_helpers import admin_required, new_session
from app.api_errors import APIError
from app.api_errors import APIError
from app.api_jwt import jwt_admin_required
from app.impl import *
from app.impl_articles import *
from app.impl_bookseries import *
from app.impl_issues import *
from app.impl_magazines import *
from app.impl_people import *
from app.impl_publishers import *
from app.impl_pubseries import *
from app.impl_shorts import *
from app.impl_tags import *
from app.impl_users import *
from app.impl_works import *

default_mimetype = 'application/json'  # Data is always returned as JSON


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


@ app.route('/api/login', methods=['post'])
def api_login() -> Response:
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

    return LoginUser(options)


@ app.route('/api/bookseries/<bookseriesId>', methods=['get'])
def api_GetBookseries(bookseriesId: str) -> Response:

    try:
        id = int(bookseriesId)
    except TypeError as exp:
        app.logger.error(f'api_GetBookseries: Invalid id {bookseriesId}.')
        response = ResponseType(
            f'apiGetBookseries: Virheellinen tunniste {bookseriesId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetBookseries(id))


@ app.route('/api/pubseries/<pubseriesId>', methods=['get'])
def api_GetPubseries(pubseriesId: str) -> Response:
    try:
        id = int(pubseriesId)
    except TypeError as exp:
        app.logger.error(f'api_GetPubseries: Invalid id {pubseriesId}.')
        response = ResponseType(
            f'api_GetBookseries: Virheellinen tunniste {pubseriesId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetPubseries(id))


@ app.route('/api/issues/<issueId>', methods=['get'])
def api_GetIssueForMagazine(issueId: str) -> Response:

    try:
        id = int(issueId)
    except TypeError as exp:
        app.logger.error(f'api_GetIssueForMagazine: Invalid id {issueId}.')
        response = ResponseType(
            f'api_GetIssueForMagazine: Virheellinen tunniste {issueId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetIssue(id))


@ app.route('/api/articles/<articleId>', methods=['get'])
def api_GetArticle(articleId: str) -> Response:

    try:
        id = int(articleId)
    except TypeError as exp:
        app.logger.error(f'api_GetArticle: Invalid id {articleId}.')
        response = ResponseType(
            f'api_GetArticle: Virheellinen tunniste {articleId}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetArticle(id))


@app.route('/api/articles/<articleId>/tags', methods=['get'])
def api_GetArticleTags(articleId: int) -> Response:

    try:
        article_id = int(articleId)
    except TypeError as exp:
        app.logger.error(f'api_GetArticleTags: Invalid id {articleId}.')
        response = ResponseType(
            f'apiGetArticleTags: Virheellinen tunniste {articleId}.', 400)
        return MakeApiResponse(response)

    retval = ArticleTags(article_id)
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


ConstraintType = NewType('ConstraintType', List[Dict[str, str]])
FilterType = NewType('FilterType', Dict[str, Union[str, ConstraintType]])


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
    except TypeError as exp:
        app.logger.error(f'api_GetPerson: Invalid id {id}.')
        response = ResponseType(
            f'api_GetPerson: Virheellinen tunniste {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetPerson(id))


@ app.route('/api/publishers/<id>', methods=['get'])
def api_GetPublisher(id: str) -> ResponseType:
    try:
        publisher_id = int(id)
    except TypeError as exp:
        app.logger.error(f'api_GetPublisher: Invalid id {id}.')
        response = ResponseType(
            f'api_GetPublisher: Virheellinen tunniste {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetPublisher(publisher_id))


@ app.route('/api/bookseries', methods=['get'])
def api_ListBookseries() -> Response:
    return MakeApiResponse(ListBookseries())


@ app.route('/api/publishers', methods=['get'])
def api_ListPublishers() -> Tuple[str, int]:
    return MakeApiResponse(ListPublishers())


@ app.route('/api/pubseries', methods=['get'])
def api_ListPubseries() -> Tuple[str, int]:
    return MakeApiResponse(ListPubseries())


@ app.route('/api/users', methods=['get'])
def api_ListUsers() -> Tuple[str, int]:

    return MakeApiResponse(ListUsers())


@ app.route('/api/users/<userId>', methods=['get'])
def api_GetUser(userId: str) -> Response:

    try:
        id = int(userId)
    except TypeError as exp:
        app.logger.error(f'api_GetUser: Invalid id {id}.')
        response = ResponseType(f'Virheellinen tunniste: {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetUser(id))


@ app.route('/api/works', methods=['get'])
def api_GetWorks() -> Response:
    url_params = request.args.to_dict()

    if 'author' in url_params:
        retval = GetWorksByAuthor(url_params['author'])

    return MakeApiResponse(retval)


@ app.route('/api/works/<id>', methods=['get'])
def api_getWork(id: str) -> Response:

    try:
        work_id = int(id)
    except TypeError as exp:
        app.logger.error(f'api_getWork: Invalid id {id}.')
        response = ResponseType(f'Virheellinen tunniste: {id}.', 400)
        return MakeApiResponse(response)

    return MakeApiResponse(GetWork(work_id))


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


@ app.route('/api/searchworks', methods=['post'])
def api_searchWorks() -> Response:
    params = json.loads(request.data)
    retval = SearchBooks(params)

    return MakeApiResponse(retval)


@ app.route('/api/worksbyinitial/<letter>', methods=['get'])
def api_searchWorksByInitial(letter: str) -> Response:
    params = {}
    params['letter'] = letter
    retval = SearchWorksByAuthor(params)
    return MakeApiResponse(retval)


@ app.route('/api/searchshorts', methods=['post'])
def api_searchShorts() -> Response:
    params = json.loads(request.data)
    retval = SearchShorts(params)
    return MakeApiResponse(retval)


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


@ app.route('/api/genres', methods=['get'])
def genres() -> Response:
    """
    Returns a list of all of the genres in the system in the order
    they are in the database (i.e. by id).
    """
    return MakeApiResponse(GenreList())


@ app.route('/api/countries', methods=['get'])
def countries() -> Response:
    """
    Returns a list of all of the countries in the system ordered by name.
    """
    return MakeApiResponse(CountryList())


@ app.route('/api/worktypes', methods=['get'])
def worktypes() -> Response:
    """
    Returns a list of all of the work types in the system in the order they
    are in the database (i.e. by id).
    """
    return MakeApiResponse(WorkTypesList())


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


@ app.route('/api/tags/<id>', methods=['get'])
def api_tag(id: str) -> Response:
    try:
        tag_id = int(id)
    except TypeError as exp:
        app.logger.error(f'api_tag: Invalid id {id}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    return MakeApiResponse(TagInfo(tag_id))


# API calls requiring admin rights

# Articles

@app.route('/api/articles/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required
def api_tagToArticle(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = ArticleTagAdd
    elif request.method == 'DELETE':
        func = ArticleTagRemove

    try:
        article_id = int(id)
        tag_id = int(tagid)
    except (TypeError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(article_id, tag_id)

    return MakeApiResponse(retval)


# Shorts


@app.route('/api/shorts/', methods=['post', 'put'])
@jwt_admin_required
def api_ShortCreateUpdate() -> Response:
    params = json.loads(request.data)
    params = bleach.clean(params)
    if request.method == 'POST':
        retval = MakeApiResponse(StoryAdd(params))
    elif request.method == 'PUT':
        retval = MakeApiResponse(StoryUpdate(params))

    return retval


@app.route('/api/shorts/<id>', methods=['delete'])
@jwt_admin_required
def api_ShortDelete(id: int) -> Response:
    try:
        short_id = int(id)
    except TypeError as exp:
        app.logger.error(
            f'api_ShortDelete: Invalid id. id={id}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = StoryDelete(short_id)

    return MakeApiResponse(retval)


@app.route('/api/issue/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required
def api_tagToIssue(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = IssueTagAdd
    elif request.method == 'DELETE':
        func = IssueTagRemove

    try:
        issue_id = int(id)
        tag_id = int(tagid)
    except (TypeError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(issue_id, tag_id)

    return MakeApiResponse(retval)


@app.route('/api/person/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required
def api_tagToPerson(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = PersonTagAdd
    elif request.method == 'DELETE':
        func = PersonTagRemove

    try:
        person_id = int(id)
        tag_id = int(tagid)
    except (TypeError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(person_id, tag_id)

    return MakeApiResponse(retval)


@app.route('/api/story/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required
def api_tagToStory(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = StoryTagAdd
    elif request.method == 'DELETE':
        func = StoryTagRemove

    try:
        story_id = int(id)
        tag_id = int(tagid)
    except (TypeError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(story_id, tag_id)

    return MakeApiResponse(retval)


@app.route('/api/work/<id>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required
def api_tagToWork(id: int, tagid: int) -> Response:
    if request.method == 'PUT':
        func = WorkTagAdd
    elif request.method == 'DELETE':
        func = WorkTagRemove

    try:
        work_id = int(id)
        tag_id = int(tagid)
    except (TypeError) as exp:
        app.logger.error(
            f'{func.__name__}: Invalid id. id={id}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste', status=400)
        return MakeApiResponse(response)

    retval = func(work_id, tag_id)

    return MakeApiResponse(retval)


@ app.route('/api/tags', methods=['post'])
@ jwt_admin_required
def api_tagCreate() -> Tuple[str, int]:
    url_params = request.args.to_dict()
    name = url_params['name']
    name = bleach.clean(name)

    retval = TagCreate(name)

    return MakeApiResponse(retval)


@ app.route('/api/tags/<id>/merge/<id2>', methods=['post'])
@ jwt_admin_required
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
    except (TypeError) as exp:
        app.logger.error(f'api_tagMerge: Invalid id. Id = {id}.')
        response = ResponseType('Virheellinen asiasanan tunniste.', status=400)
        return MakeApiResponse(response)

    retval = TagMerge(idTo, idFrom)
    return MakeApiResponse(retval)


@ app.route('/api/tags/<id>', methods=['delete'])
@ jwt_admin_required
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


@ app.route('/api/tags', methods=['put'])
@ jwt_admin_required
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
