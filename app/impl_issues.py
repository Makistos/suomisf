""" Issue related functions. """
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (Issue, IssueTag, Tag)
from app.model import IssueSchema, TagSchema

from app import app
from app.types import HttpResponseCode


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
        app.logger.error('get_issue: ' + str(exp))
        return ResponseType(f'get_issue: Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = IssueSchema()
        retval = schema.dump(issue)
    except exceptions.MarshmallowError as exp:
        app.logger.error('get_issue schema error: ' + str(exp))
        return ResponseType('get_issue: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_issue_tags(issue_id: int) -> ResponseType:
    """
    Get the tags associated with a specific issue.

    Args:
        id (int): The ID of the issue.

    Returns:
        ResponseType: The response object containing the tags associated with
                      the issue.
    """
    session = new_session()
    try:
        tags = session.query(Tag)\
            .join(IssueTag)\
            .filter(IssueTag.issue_id == issue_id)\
            .filter(IssueTag.tag_id == Tag.id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_issue_tags: {exp}')
        return ResponseType(f'get_issue_tags: Tietokantavirhe. id={issue_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = TagSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_issue_tags schema error: {exp}')
        return ResponseType('get_issue_tags: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


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
    session = new_session()

    try:
        short = session.query(Issue).filter(
            Issue.id == issue_id).first()
        if not short:
            app.logger.error(
                f'issue_tag_add: Issue not found. Id = {issue_id}.')
            return ResponseType('Numeroa ei löydy',
                                HttpResponseCode.BAD_REQUEST.value)

        issue_tag = IssueTag()
        issue_tag.issue_id = issue_id
        issue_tag.tag_id = tag_id
        session.add(issue_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'issue_tag_add() ({issue_id}, {tag_id}): {exp}')
        return ResponseType('issue_tag_add: Tietokantavirhe. '
                            f'issue_id={issue_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)


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
    session = new_session()

    try:
        issue_tag = session.query(IssueTag)\
            .filter(IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id)\
            .first()
        if not issue_tag:
            app.logger.error(
                ('issue_tag_remove: Issue has no such tag: '
                 f'issue_id {issue_id}, '
                 f'tag {tag_id}.')
            )
            return ResponseType('issue_tag_remove: Tagia ei löydy numerolta. '
                                f'issue_id={issue_id}, tag_id={tag_id}.',
                                HttpResponseCode.BAD_REQUEST.value)
        session.delete(issue_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'issue_tag_remove() ({issue_id}, {tag_id}): {exp}')
        return ResponseType('issue_tag_remove: Tietokantavirhe. '
                            f'issue_id={issue_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)
