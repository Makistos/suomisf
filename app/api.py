from http.client import RemoteDisconnected
from app import app
import bleach
from flask import request
from webargs.flaskparser import parser
from app.model import *
from .impl import *
from typing import Any, Tuple, NewType, Union, List, Dict, TypedDict
import json
from .api_errors import APIError
from app.api_errors import APIError
from app.route_helpers import new_session


SearchResult = List[SearchResultFields]
SearchResults = Dict[str, SearchResult]


@app.route('/api/login', methods=['post'])
def api_login() -> Tuple[str, int]:
    options = {}
    try:
        options['username'] = request.json['username']
        options['password'] = request.json['password']
    except (TypeError, KeyError) as exp:
        return json.dumps({'code': 401,
                           'message': 'Invalid parameters'}), 401
    return LoginUser(options)


@app.route('/api/bookseries/<bookseriesId>', methods=['get'])
def api_GetBookseries(bookseriesId: str) -> Tuple[str, int]:
    options = {}
    options['bookseriesId'] = bookseriesId

    return GetBookseries(options)


@app.route('/api/pubseries/<pubseriesId>', methods=['get'])
def api_GetPubseries(pubseriesId: str) -> Tuple[str, int]:
    options = {}
    options['pubseriesId'] = pubseriesId

    return GetPubseries(options)


@app.route('/api/issues/<issueId>', methods=['get'])
def api_GetIssueForMagazine(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    return GetIssue(options)


@app.route('/api/articles/<articleId>', methods=['get'])
def api_GetArticle(articleId: str) -> Tuple[str, int]:
    options = {}
    options['articleId'] = articleId

    return GetArticle(options)


@app.route('/api/shorts/<shortId>', methods=['get'])
def api_GetShort(shortId: str) -> Tuple[str, int]:
    options = {}
    options['shortId'] = shortId
    return GetShort(options)


@app.route('/api/issues/<issueId>', methods=['post'])
def api_PostIssue(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    return PostIssue(options)


@app.route('/api/issues/<issueId>', methods=['patch'])
def api_UpdateIssue(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    schema = IssueSchema()

    # body = parser.parse(schema, request, location='json')

    return UpdateIssue(options, "")


@app.route('/api/issues/<issueId>/articles', methods=['get'])
def api_GetIssueArticles(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    return GetIssueArticles(options)


@app.route('/api/issues/<issueId>/editors', methods=['get'])
def api_GetIssue(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    return GetIssue(options)


@app.route('/api/issues/<issueId>/shorts', methods=['get'])
def api_GetIssueShorts(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    return GetIssueShorts(options)


@app.route('/api/issues/<issueId>/tags', methods=['get'])
def api_GetIssueTags(issueId: str) -> Tuple[str, int]:

    options = {}
    options["issueId"] = issueId

    return GetIssueTags(options)


@app.route('/api/magazines', methods=['get'])
def api_ListMagazines() -> Tuple[str, int]:

    return ListMagazines()


@app.route('/api/magazines/<magazineId>', methods=['get'])
def api_GetMagazine(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    return GetMagazine(options)


@app.route('/api/magazines/<magazineId>', methods=['patch'])
def api_UpdateMagazine(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    schema = MagazineSchema()

    # body = parser.parse(schema, request, location='json')

    return UpdateMagazine(options, "")


@app.route('/api/magazines/<magazineId>/issues', methods=['get'])
def api_GetMagazineIssues(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    return GetMagazineIssues(options)


@app.route('/api/magazines/<magazineId>/publisher', methods=['get'])
def api_GetMagazinePublisher(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    return GetMagazinePublisher(options)


@app.route('/api/magazines/<magazineId>/tags', methods=['get'])
def api_GetMagazineTags(magazineId: str) -> Tuple[str, int]:

    options = {}
    options["magazineId"] = magazineId

    return GetMagazineTags(options)


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


@app.route('/api/people/', methods=['get'])
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


@ app.route('/api/people/<id>', methods=['get'])
def api_GetPerson(id: str) -> Tuple[str, int]:
    options = {}
    options['personId'] = id
    return GetPerson(options)


@ app.route('/api/publishers/<id>', methods=['get'])
def api_GetPublisher(id: str) -> Tuple[str, int]:
    options = {}
    options['publisherId'] = id
    return GetPublisher(options)


@app.route('/api/bookseries', methods=['get'])
def api_ListBookseries() -> Tuple[str, int]:
    return ListBookseries()


@ app.route('/api/countries', methods=['get'])
def api_ListCountries() -> Tuple[str, str]:
    return ListCountries()


@app.route('/api/publishers', methods=['get'])
def api_ListPublishers() -> Tuple[str, int]:
    return ListPublishers()


@app.route('/api/pubseries', methods=['get'])
def api_ListPubseries() -> Tuple[str, int]:
    return ListPubseries()


@ app.route('/api/users', methods=['get'])
def api_ListUsers() -> Tuple[str, int]:

    return ListUsers()


@ app.route('/api/users/<userId>', methods=['get'])
def api_GetUser(userId: str) -> Tuple[str, int]:

    options = {}
    options["userId"] = userId

    return GetUser(options)


@app.route('/api/works', methods=['get'])
def api_GetWorks() -> Tuple[str, int]:
    url_params = request.args.to_dict()
    if 'author' in url_params:
        retval = GetWorksByAuthor(url_params['author'])

    return retval


@ app.route('/api/works/<id>', methods=['get'])
def api_getWork(id: str) -> Tuple[str, int]:
    options = {}
    options['workId'] = id

    return GetWork(options)


@app.route('/api/search/<pattern>', methods=['get', 'post'])
def api_Search(pattern: str) -> Tuple[str, int]:
    retval = ''
    retcode = 200
    results: SearchResult = []

    #searchword = request.args.get('search', '')
    pattern = bleach.clean(pattern)
    words = pattern.split(' ')

    session = new_session()
    results = SearchWorks(session, words)
    results += SearchPeople(session, words)
    results = sorted(results, key=lambda d: d['score'], reverse=True)
    return json.dumps(results), retcode


@app.route('/api/searchshorts', methods=['post'])
def api_searchShorts() -> Tuple[str, int]:
    retval: Tuple[str, int]
    params = json.loads(request.data)
    retval = SearchShorts(params)
    ret = json.dumps(retval[0])
    return retval[0], retval[1]


@app.route('/api/changes', methods=['get'])
def api_Changes() -> Tuple[str, int]:
    retval = ('', 200)
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
        print(exp.message)
    return json.dumps(retval), 200


@app.route('/api/firstlettervector', methods=['get'])
def firstlettervector() -> Tuple[str, int]:
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
    retval = GetAuthorFirstLetters(url_params['target'])

    return retval
