from app import app
from flask import Blueprint, request
from webargs.flaskparser import parser
from marshmallow import Schema, fields
from app.model import *
from .impl import *
from typing import Any, Tuple
import json
#app = Blueprint('api', __name__)


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

    body = parser.parse(schema, request, location='json')

    return UpdateIssue(options, body)


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

    body = parser.parse(schema, request, location='json')

    return UpdateMagazine(options, body)


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


@app.route('/api/people', methods=['get'])
def api_GetPeople() -> Tuple[str, int]:
    return ListPeople()


@app.route('/api/people/<id>', methods=['get'])
def api_GetPerson(id: str) -> Tuple[str, int]:
    options = {}
    options['personId'] = id
    return GetPerson(options)


@app.route('/api/publishers/<id>', methods=['get'])
def api_GetPublisher(id: str) -> Tuple[str, int]:
    options = {}
    options['publisherId'] = id
    return GetPublisher(options)


@app.route('/api/users', methods=['get'])
def api_ListUsers() -> Tuple[str, int]:

    return ListUsers()


@app.route('/api/users/<userId>', methods=['get'])
def api_GetUser(userId: str) -> Tuple[str, int]:

    options = {}
    options["userId"] = userId

    return GetUser(options)


@app.route('/api/works/<workId>', methods=['get'])
def api_getWork(workid: str) -> Tuple[str, int]:
    options = {}
    options['id'] = workid

    return ListWork(options)
