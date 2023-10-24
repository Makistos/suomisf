""" Functions related to tags. """
from typing import Any, List
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.orm_decl import (Tag, ArticleTag, IssueTag,
                          PersonTag, StoryTag, WorkTag)
from app.model import (TagBriefSchema, TagSchema)
from app.route_helpers import new_session
from app.impl import ResponseType
from app import app


def tags_have_changed(old_values: List[Any], new_values: List[Any]) -> bool:
    """
    Check if the tags have changed.

    Args:
        old_values (List[Any]): The list of old tag values.
        new_values (List[Any]): The list of new tag values.

    Returns:
        bool: True if the tags have changed, False otherwise.
    """
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.id != new_values[idx]['id']:
            return True
    return False


def tag_filter(query: str) -> ResponseType:
    """
    Retrieves a list of tags from the database that match the given query.

    Args:
        query (str): The query string to match against tag names.

    Returns:
        ResponseType: The response containing the list of matching tags.

    Raises:
        SQLAlchemyError: If there is an error during the database query.
        exceptions.MarshmallowError: If there is an error during schema
                                     serialization.
    """
    session = new_session()

    try:
        tags = session.query(Tag)\
            .filter(Tag.name.ilike(query + '%'))\
            .order_by(Tag.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in TagFilter (query: {query}): ' + str(exp))
        return ResponseType('TagFilter: Tietokantavirhe.', 400)
    try:
        schema = TagSchema(many=True, only=('id', 'name'))
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagFilter schema error (query: {query}): ' + str(exp))
        return ResponseType('TagFilter: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def tag_list() -> ResponseType:
    """
    Retrieves a list of tags from the database.

    Returns:
        ResponseType: An object representing the response containing the list
                       of tags.
    """
    session = new_session()

    try:
        tags = session.query(Tag).order_by(Tag.name)
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagList: ' + str(exp))
        return ResponseType('TagList: Tietokantavirhe.', 400)

    try:
        schema = TagBriefSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error('TagList schema error: ' + str(exp))
        return ResponseType('TagList: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def tag_info(tag_id: int) -> ResponseType:
    """
    Retrieves information about a tag based on its ID.

    Args:
        id (int): The ID of the tag.

    Returns:
        ResponseType: An object containing the tag information.

    Raises:
        SQLAlchemyError: If there is an error in querying the database.
        exceptions.MarshmallowError: If there is an error in the schema.

    """
    session = new_session()

    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in TagInfo (id: {tag_id}): ' + str(exp))
        return ResponseType('TagInfo: Tietokantavirhe.', 400)

    try:
        schema = TagSchema()
        retval = schema.dump(tag)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'TagInfo schema error (id: {tag_id}): ' + str(exp))
        return ResponseType('TagInfo: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def tag_search(query: str) -> ResponseType:
    """
    Searches for tags based on a given query string.

    Args:
        query (str): The query string used to search for tags.

    Returns:
        ResponseType: An object representing the response of the tag search
                       operation.
    """
    session = new_session()

    try:
        tags = session.query(Tag)\
            .filter(Tag.name.ilike(query + '%'))\
            .order_by(Tag.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in TagSearch (query: {query}): ' + str(exp))
        return ResponseType('TagSearch: Tietokantavirhe.', 400)

    try:
        schema = TagBriefSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagSearch schema error (query: {query}): ' + str(exp))
        return ResponseType('TagSearch: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def _tag_exists(session: Any, name: str) -> bool:
    """
    Check if a tag with the given name exists in the database.

    Args:
        session (Any): The database session.
        name (str): The name of the tag to check.

    Returns:
        bool: True if the tag exists, False otherwise.
    """

    try:
        count = session.query(Tag)\
            .filter(Tag.name.ilike(name))\
            .count()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in _tagExists (name: {name}): ' + str(exp))
        return False

    if count > 0:
        return True

    return False


def tag_create(name: str) -> ResponseType:
    """
    Creates a new tag with the specified name.

    Parameters:
        name (str): The name of the tag to create.

    Returns:
        ResponseType: The response object indicating the status of the tag
                       creation.
    """
    session = new_session()
    if _tag_exists(session, name):
        app.logger.error(
            f'TagRename: Tag already exists. name = {name}.')
        return ResponseType('Asiasana on jo olemassa', 400)

    tag = Tag()
    tag.name = name
    session.add(tag)
    session.commit()

    return ResponseType({'id': tag.id}, 200)


def tag_rename(tag_id: int, name: str) -> ResponseType:
    """ See api_tagRename() in api.py. """
    session = new_session()

    if _tag_exists(session, name):
        app.logger.error(
            f'TagRename: Tag already exists. Id = {tag_id}, name = {name}.')
        return ResponseType('Asiasana on jo olemassa', 400)

    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in TagRename (id: {tag_id}, name: {name}):  {exp}')
        return ResponseType('TagRename: Tietokantavirhe.', 400)

    if not tag:
        app.logger.error(f'TagRename: Tag not found. Id = {tag_id}.')
        return ResponseType('Asiasanan tunnistetta ei löydy', 400)

    tag.name = name
    session.add(tag)
    session.commit()
    try:
        schema = TagSchema()
        retval = schema.dump(tag)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagSearch schema error (name: {name}): ' + str(exp))
        return ResponseType('TagSearch: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def tag_delete(tag_id: int) -> ResponseType:
    """ See api_tagDelete in api.py. """
    retval = ResponseType('', 200)

    session = new_session()

    article_tags = session.query(ArticleTag).filter(
        ArticleTag.tag_id == tag_id).all()
    if article_tags:
        app.logger.error(f'TagDelete: Tag is attached to articles. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään artikkeleiden kanssa.', 400)

    issue_tags = session.query(IssueTag)\
        .filter(IssueTag.tag_id == tag_id).all()
    if issue_tags:
        app.logger.error(f'TagDelete: Tag is attached to issues. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään lehden numeroiden kanssa.',
                            400)

    person_tags = session.query(PersonTag)\
        .filter(PersonTag.tag_id == tag_id).all()
    if person_tags:
        app.logger.error(f'TagDelete: Tag is attached to people. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään henkilöiden kanssa.', 400)

    story_tags = session.query(StoryTag)\
        .filter(StoryTag.tag_id == tag_id).all()
    if story_tags:
        app.logger.error(f'TagDelete: Tag is attached to stories. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään novelleiden kanssa.', 400)

    work_tags = session.query(WorkTag).filter(WorkTag.tag_id == tag_id).all()
    if work_tags:
        app.logger.error(f'TagDelete: Tag is attached to works. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään teosten kanssa.', 400)

    try:
        tag = session.query(Tag)\
            .filter(Tag.id == tag_id)\
            .first()
        session.delete(tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagDelete: ' + str(exp))
        return ResponseType(f'TagDelete: Tietokantavirhe. id={tag_id}', 400)

    if not tag:
        app.logger.error(f'TagDelete: Tag not found. id = {tag_id}.')
        return ResponseType('Asiasanan tunnistetta ei löydy', 400)

    return retval


def tag_merge(id_to: int, id_from: int) -> ResponseType:
    """ See api_tagMerge in api.py. """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        tag_to = session.query(Tag).filter(Tag.id == id_to).first()
        tag_from = session.query(Tag).filter(Tag.id == id_from).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagMerge: ' + str(exp))
        return ResponseType(f'TagMerge: Tietokantavirhe. id={id}', 400)

    if not tag_to or not tag_from:
        app.logger.error(
            f'TagMerge: Tag not found. To = {id_to}, From = {id_from}.')
        return ResponseType('Tuntematon asiasanan tunniste', 400)

    # Update
    try:
        session.query(ArticleTag)\
            .filter(ArticleTag.tag_id == id_from)\
            .update({ArticleTag.article_id: id_to}, synchronize_session=True)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagMerge: ' + str(exp))
        return ResponseType(f'TagMerge: Tietokantavirhe. id={id}', 400)

    return retval
