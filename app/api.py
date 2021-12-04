from app import app
from flask import Blueprint, request
from webargs.flaskparser import parser
from marshmallow import Schema, fields
from app.model import *
from .impl import *
from typing import Any

#app = Blueprint('api', __name__)


@app.route('/api/issues/<issueId>', methods=['get'])
def api_GetIssueForMagazine(issueId):

    options = {}
    options["issueId"] = issueId

    return GetIssue(options)


@app.route('/api/issues/<issueId>', methods=['post'])
def api_PostIssue(issueId):

    options = {}
    options["issueId"] = issueId

    return PostIssue(options)


@app.route('/api/issues/<issueId>', methods=['patch'])
def api_UpdateIssue(issueId):

    options = {}
    options["issueId"] = issueId

    schema = Issue()

    body = parser.parse(schema, request, location='json')

    return UpdateIssue(options, body)


@app.route('/api/issues/<issueId>/articles', methods=['get'])
def api_GetIssueArticles(issueId):

    options = {}
    options["issueId"] = issueId

    return GetIssueArticles(options)


@app.route('/api/issues/<issueId>/editors', methods=['get'])
def api_GetIssue(issueId):

    options = {}
    options["issueId"] = issueId

    return GetIssue(options)


@app.route('/api/issues/<issueId>/shorts', methods=['get'])
def api_GetIssueShorts(issueId):

    options = {}
    options["issueId"] = issueId

    return GetIssueShorts(options)


@app.route('/api/issues/<issueId>/tags', methods=['get'])
def api_GetIssueTags(issueId):

    options = {}
    options["issueId"] = issueId

    return GetIssueTags(options)


@app.route('/api/magazines', methods=['get'])
def api_ListMagazines():

    return ListMagazines()


@app.route('/api/magazines/<magazineId>', methods=['get'])
def api_GetMagazine(magazineId):

    options = {}
    options["magazineId"] = magazineId

    return GetMagazine(options)


@app.route('/api/magazines/<magazineId>', methods=['patch'])
def api_UpdateMagazine(magazineId):

    options = {}
    options["magazineId"] = magazineId

    schema = Magazine()

    body = parser.parse(schema, request, location='json')

    return UpdateMagazine(options, body)


@app.route('/api/magazines/<magazineId>/issues', methods=['get'])
def api_GetMagazineIssues(magazineId):

    options = {}
    options["magazineId"] = magazineId

    return GetMagazineIssues(options)


@app.route('/api/magazines/<magazineId>/publisher', methods=['get'])
def api_GetMagazinePublisher(magazineId):

    options = {}
    options["magazineId"] = magazineId

    return GetMagazinePublisher(options)


@app.route('/api/magazines/<magazineId>/tags', methods=['get'])
def api_GetMagazineTags(magazineId):

    options = {}
    options["magazineId"] = magazineId

    return GetMagazineTags(options)


@app.route('/api/publishers/<id>', methods=['get'])
def api_GetPublisher(id: Any) -> Any:
    options = {}
    options['publisherId'] = id
    return GetPublisher(options)


@app.route('/api/users', methods=['get'])
def api_ListUser():

    options = {}
    options["id"] = request.args.get("id")

    return ListUser(options)


@app.route('/api/users/<userId>', methods=['get'])
def api_GetUser(userId):

    options = {}
    options["userId"] = userId

    return GetUser(options)


@app.route('/api/works/<workId>', methods=['get'])
def api_getWork():
    options = {}
    options['id'] = request.args.get('id')

    return ListWork(options)
