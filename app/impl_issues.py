import json
from typing import Dict, Tuple
from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (Issue, IssueTag)
from app.model import IssueSchema
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app import app


def GetIssue(id: int) -> ResponseType:
    session = new_session()

    try:
        issue = session.query(Issue)\
            .filter(Issue.id == id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetIssue: ' + str(exp))
        return ResponseType(f'GetIssue: Tietokantavirhe. id={id}', 400)

    try:
        schema = IssueSchema()
        retval = schema.dump(issue)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetBookseries schema error: ' + str(exp))
        return ResponseType('GetBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def GetIssueTags(id: int) -> ResponseType:

    return ResponseType(json.dumps([{
        "id": "<integer>",
        "name": "<string>",
        "uri": "<string>",
    }]), 200)


def IssueTagAdd(issue_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        short = session.query(Issue).filter(
            Issue.id == issue_id).first()
        if not short:
            app.logger.error(
                f'IssueTagAdd: Issue not found. Id = {issue_id}.')
            return ResponseType('Numeroa ei löydy', 400)

        issueTag = IssueTag()
        issueTag.issue_id = issue_id
        issueTag.tag_id = tag_id
        session.add(issueTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in IssueTagAdd(): ' + str(exp))
        return ResponseType(f'IssueTagAdd: Tietokantavirhe. issue_id={issue_id}, tag_id={tag_id}.', 400)

    return retval


def IssueTagRemove(issue_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        issueTag = session.query(IssueTag)\
            .filter(IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id)\
            .first()
        if not issueTag:
            app.logger.error(
                f'IssueTagRemove: Issue has no such tag: issue_id {issue_id}, tag {tag_id}.'
            )
            return ResponseType(f'IssueTagRemove: Tagia ei löydy numerolta. issue_id={issue_id}, tag_id={tag_id}.', 400)
        session.delete(issueTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagRemove(): ' + str(exp))
        return ResponseType(f'IssueTagRemove: Tietokantavirhe. issue_id={issue_id}, tag_id={tag_id}.', 400)

    return retval
