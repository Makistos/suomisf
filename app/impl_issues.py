""" Issue related functions. """
from typing import Any, Dict
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (Issue, IssueTag, PublicationSize, Tag)
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


def add_issue(params: Dict[str, Any]) -> ResponseType:
    """
    Adds a new issue to the database.

    Args:
        issue_data (dict): The issue data to add.

    Returns:
        ResponseType: The response object containing the added issue.

    Raises:
        SQLAlchemyError: If there is an error executing the database query.
        exceptions.MarshmallowError: If there is an error serializing the
                                     issue object.
    """
    session = new_session()
    issue = params['data']

    new_issue = Issue()

    if 'magazine_id' not in issue:
        app.logger.error('Missing magazine_id.')
        return ResponseType('Lehnde tunniste puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)
    try:
        magazine_id_int = int(issue['magazine_id'])
    except ValueError:
        app.logger.error('Invalid magazine_id.')
        return ResponseType('Lehnde tunniste on virheellinen.',
                            HttpResponseCode.BAD_REQUEST.value)

    new_issue.magazine_id = magazine_id_int

    new_issue.number = issue['number'] if 'number' in issue else None
    new_issue.number_extra = issue['number_extra']\
        if 'number_extra' in issue else None
    new_issue.count = issue['count'] if 'count' in issue else None
    new_issue.year = issue['year'] if 'year' in issue else None
    new_issue.cover_number = issue['cover_number']\
        if 'cover_number' in issue else None
    new_issue.image_attr = issue['image_attr']\
        if 'image_attr' in issue else None
    new_issue.image_src = issue['image_src']\
        if 'image_src' in issue else None
    new_issue.pages = issue['pages'] if 'pages' in issue else None
    if 'size_id' in issue:
        try:
            size_id_int = int(issue['size_id'])
        except ValueError:
            app.logger.error('Invalid size_id.')
            return ResponseType('Julkaisukoko on virheellinen.',
                                HttpResponseCode.BAD_REQUEST.value)

        pub_size = session.query(PublicationSize)\
            .filter(PublicationSize.id == size_id_int)\
            .first()
        if not pub_size:
            app.logger.error('Invalid size_id.')
            return ResponseType('Julkaisukoko on virheellinen: {size_id}.',
                                HttpResponseCode.BAD_REQUEST.value)

        new_issue.size_id = size_id_int
    new_issue.size_id = issue['size_id'] if 'size_id' in issue else None
    new_issue.link = issue['link'] if 'link' in issue else None
    new_issue.notes = issue['notes'] if 'notes' in issue else None
    new_issue.title = issue['title'] if 'title' in issue else None

    session.add(new_issue)
    session.commit()

    return ResponseType(str(new_issue.id), HttpResponseCode.OK.value)


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
