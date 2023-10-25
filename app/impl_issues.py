""" Issue related functions. """
import json
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (Issue, IssueTag)
from app.model import IssueSchema

from app import app


def get_issue(issue_id: int) -> ResponseType:
    """
    Retrieves an issue from the database based on the provided ID.

    Args:
        id (int): The ID of the issue to retrieve.

    Returns:
        ResponseType: The response object containing the retrieved issue.

    Raises:
        SQLAlchemyError: If there is an error querying the database.
        exceptions.MarshmallowError: If there is an error serializing the
                                     issue.

    """
    session = new_session()

    try:
        issue = session.query(Issue)\
            .filter(Issue.id == issue_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetIssue: ' + str(exp))
        return ResponseType(f'GetIssue: Tietokantavirhe. id={issue_id}', 400)

    try:
        schema = IssueSchema()
        retval = schema.dump(issue)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetBookseries schema error: ' + str(exp))
        return ResponseType('GetBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def get_issue_tags(issue_id: int) -> ResponseType:
    """
    Get the tags associated with a specific issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the tags associated with
                      the issue.
    """

    return ResponseType(json.dumps([{
        "id": "<integer>",
        "name": "<string>",
        "uri": "<string>",
    }]), 200)


def issue_tag_add(issue_id: int, tag_id: int) -> ResponseType:
    """
    Adds a tag to an issue.

    Args:
        issue_id (int): The ID of the issue.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        short = session.query(Issue).filter(
            Issue.id == issue_id).first()
        if not short:
            app.logger.error(
                f'IssueTagAdd: Issue not found. Id = {issue_id}.')
            return ResponseType('Numeroa ei löydy', 400)

        issue_tag = IssueTag()
        issue_tag.issue_id = issue_id
        issue_tag.tag_id = tag_id
        session.add(issue_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in IssueTagAdd(): ' + str(exp))
        return ResponseType(f'IssueTagAdd: Tietokantavirhe. \
                            issue_id={issue_id}, tag_id={tag_id}.', 400)

    return retval


def issue_tag_remove(issue_id: int, tag_id: int) -> ResponseType:
    """
    Removes a tag from an issue.

    Args:
        issue_id (int): The ID of the issue.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: The response type object.

    Raises:
        SQLAlchemyError: If there is an error with the SQLAlchemy operation.

    """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        issue_tag = session.query(IssueTag)\
            .filter(IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id)\
            .first()
        if not issue_tag:
            app.logger.error(
                f'IssueTagRemove: Issue has no such tag: issue_id {issue_id}, \
                    tag {tag_id}.'
            )
            return ResponseType(f'IssueTagRemove: Tagia ei löydy numerolta. \
                                issue_id={issue_id}, tag_id={tag_id}.', 400)
        session.delete(issue_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagRemove(): ' + str(exp))
        return ResponseType(f'IssueTagRemove: Tietokantavirhe. \
                            issue_id={issue_id}, tag_id={tag_id}.', 400)

    return retval
