""" Functions related to tags. """
from typing import Any, List
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.orm_decl import (Tag, ArticleTag, IssueTag,
                          PersonTag, StoryTag, TagType, WorkTag)
from app.model import (TagBriefSchema, TagSchema, TagTypeSchema)
from app.route_helpers import new_session
from app.impl import ResponseType
from app import app
from app.types import HttpResponseCode


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
        if new_values[idx]['id'] == 0:
            # New tag -> Must have changed
            return True
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
        return ResponseType('TagFilter: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = TagSchema(many=True, only=('id', 'name'))
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagFilter schema error (query: {query}): ' + str(exp))
        return ResponseType('TagFilter: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def tag_list() -> ResponseType:
    """
    Retrieves a list of tags from the database.

    Returns:
        ResponseType: An object representing the response containing the list
                       of tags.
    """
    session = new_session()

    try:
        tags = session.query(Tag).order_by(Tag.name).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagList: ' + str(exp))
        return ResponseType('TagList: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = TagBriefSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error('TagList schema error: ' + str(exp))
        return ResponseType('TagList: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def tag_list_quick() -> ResponseType:
    """
    Retrieve a list of tags along with their associated counts and types.

    Executes a SQL query to fetch tags from the database, including their
    associated counts from the `worktag`, `articletag`, and `storytag` tables,
    as well as their type information from the `tagtype` table. The results
    are ordered by tag name.

    Returns:
        ResponseType: A response object containing a list of tags with their
        details or an error message in case of a database error.

    Raises:
        SQLAlchemyError: If there is an error executing the SQL query.

    Example response:
        [
            {
                'id': 1,
                'name': 'example_tag',
                'workcount': 10,
                'articlecount': 5,
                'storycount': 2,
                    'id': 1,
                    'name': 'example_type'
            },
            ...
        ]
    """
    session = new_session()

    tags = None
    retval = []

    stmt = """
SELECT
    tag.id,
    tag.name,
    COALESCE(tagtype.id, 0) AS typeid,
    COALESCE(tagtype.name, 'Unknown') AS typename,

    -- Count actual occurrences in each table separately
    (SELECT COUNT(*) FROM worktag WHERE worktag.tag_id = tag.id) AS workcount,
    (SELECT COUNT(*) FROM articletag WHERE articletag.tag_id = tag.id)
    AS articlecount,
    (SELECT COUNT(*) FROM storytag WHERE storytag.tag_id = tag.id)
    AS storycount

FROM tag
LEFT JOIN tagtype ON tag.type_id = tagtype.id
ORDER BY tag.name;
"""
    try:
        tags = session.execute(stmt).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagListFast: ' + str(exp))
        return ResponseType('TagListFast: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if tags:
        for tag in tags:
            retval.append({
                'id': tag.id,
                'name': tag.name,
                'workcount': tag.workcount,
                'articlecount': tag.articlecount,
                'storycount': tag.storycount,
                'type': {
                    'id': tag.typeid,
                    'name': tag.typename
                }
            })
    return ResponseType(retval, HttpResponseCode.OK.value)


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
        return ResponseType('TagInfo: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = TagSchema()
        retval = schema.dump(tag)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'TagInfo schema error (id: {tag_id}): ' + str(exp))
        return ResponseType('TagInfo: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, 200)


def tag_forminfo(tag_id: int) -> ResponseType:
    """
    Retrieves information about a tag based on its ID for form purposes.

    Args:
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: An object containing the tag information for form
                       purposes.
    Raises:
        SQLAlchemyError: If there is an error in querying the database.
        exceptions.MarshmallowError: If there is an error in the schema.
    """
    session = new_session()

    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in TagFormInfo (id: {tag_id}): ' + str(exp))
        return ResponseType('TagFormInfo: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = TagSchema(only=('id', 'name', 'description', 'type'))
        retval = schema.dump(tag)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'TagFormInfo schema error (id: {tag_id}): ' + str(exp))
        return ResponseType('TagFormInfo: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

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
        return ResponseType('TagSearch: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = TagBriefSchema(many=True)
        retval = schema.dump(tags)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'TagSearch schema error (query: {query}): ' + str(exp))
        return ResponseType('TagSearch: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


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
        return ResponseType('Asiasana on jo olemassa',
                            HttpResponseCode.BAD_REQUEST.value)

    tag = Tag()
    tag.name = name
    tag.type_id = 1
    session.add(tag)
    session.commit()

    return ResponseType({'id': tag.id}, HttpResponseCode.CREATED.value)


def tag_update(params: Any) -> ResponseType:
    """ See api_tagupdate() in api.py. """
    session = new_session()
    tag_id = params['id']
    name = params['name']
    type_id = params['type']['id']
    description = params['description']

    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception {tag_id}, name: {name}:  {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not tag:
        app.logger.error(f'Tag not found. Id = {tag_id}.')
        return ResponseType('Asiasanan tunnistetta ei löydy',
                            HttpResponseCode.BAD_REQUEST.value)
    if name != tag.name:
        # Check that we are not trying to rename to an existing tag
        if _tag_exists(session, name):
            app.logger.error(
                f'Tag already exists. Id = {tag_id}, name = {name}.')
            return ResponseType('Asiasana on jo olemassa',
                                HttpResponseCode.BAD_REQUEST.value)

    tag.name = name
    tag.type_id = type_id
    tag.description = description
    session.add(tag)
    session.commit()

    return ResponseType(tag_id, HttpResponseCode.OK.value)


def tag_delete(tag_id: int) -> ResponseType:
    """ See api_tagDelete in api.py. """
    retval = ResponseType('', HttpResponseCode.OK.value)

    session = new_session()

    article_tags = session.query(ArticleTag).filter(
        ArticleTag.tag_id == tag_id).all()
    if article_tags:
        app.logger.error(f'TagDelete: Tag is attached to articles. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään artikkeleiden kanssa.',
                            HttpResponseCode.BAD_REQUEST.value)

    issue_tags = session.query(IssueTag)\
        .filter(IssueTag.tag_id == tag_id).all()
    if issue_tags:
        app.logger.error(f'TagDelete: Tag is attached to issues. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään lehden numeroiden kanssa.',
                            HttpResponseCode.BAD_REQUEST.value)

    person_tags = session.query(PersonTag)\
        .filter(PersonTag.tag_id == tag_id).all()
    if person_tags:
        app.logger.error(f'TagDelete: Tag is attached to people. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään henkilöiden kanssa.',
                            HttpResponseCode.BAD_REQUEST.value)

    story_tags = session.query(StoryTag)\
        .filter(StoryTag.tag_id == tag_id).all()
    if story_tags:
        app.logger.error(f'TagDelete: Tag is attached to stories. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään novelleiden kanssa.',
                            HttpResponseCode.BAD_REQUEST.value)

    work_tags = session.query(WorkTag).filter(WorkTag.tag_id == tag_id).all()
    if work_tags:
        app.logger.error(f'TagDelete: Tag is attached to works. \
                         Id = {tag_id}.')
        return ResponseType('Asiasanaa käytetään teosten kanssa.',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        tag = session.query(Tag)\
            .filter(Tag.id == tag_id)\
            .first()
        session.delete(tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagDelete: ' + str(exp))
        return ResponseType(f'TagDelete: Tietokantavirhe. id={tag_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not tag:
        app.logger.error(f'TagDelete: Tag not found. id = {tag_id}.')
        return ResponseType('Asiasanan tunnistetta ei löydy',
                            HttpResponseCode.BAD_REQUEST.value)

    return retval


def tag_merge(id_to: int, id_from: int) -> ResponseType:
    """ See api_tagMerge in api.py. """
    retval = ResponseType('', HttpResponseCode.OK.value)
    session = new_session()

    try:
        tag_to = session.query(Tag).filter(Tag.id == id_to).first()
        tag_from = session.query(Tag).filter(Tag.id == id_from).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagMerge: ' + str(exp))
        return ResponseType(f'TagMerge: Tietokantavirhe. id={id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not tag_to or not tag_from:
        app.logger.error(
            f'TagMerge: Tag not found. To = {id_to}, From = {id_from}.')
        return ResponseType('Tuntematon asiasanan tunniste',
                            HttpResponseCode.BAD_REQUEST.value)

    # Update
    try:
        # Each tag merge does three things:
        # 1. Find tags already existing for target tag.
        # 2. Update existing tags to point to the new tag, but omit ones
        #    that already point to the new tag.
        # 3. Delete old that might have been left because of 2.
        #
        # Finally delete the old tag.

        # Article tag
        to_tags = session.query(ArticleTag)\
            .filter(ArticleTag.tag_id == id_to)\
            .all()

        session.query(ArticleTag)\
            .filter(ArticleTag.tag_id == id_from)\
            .filter(ArticleTag.article_id.notin_(
                [x.article_id for x in to_tags]))\
            .update({ArticleTag.article_id: id_to}, synchronize_session=False)

        session.query(ArticleTag)\
            .filter(ArticleTag.tag_id == id_from)\
            .delete()

        # Story tag
        to_tags = session.query(StoryTag)\
            .filter(StoryTag.tag_id == id_to)\
            .all()

        session.query(StoryTag)\
            .filter(StoryTag.tag_id == id_from)\
            .filter(StoryTag.shortstory_id.notin_(
                [x.shortstory_id for x in to_tags]))\
            .update({StoryTag.shortstory_id: id_to}, synchronize_session=False)

        session.query(StoryTag)\
            .filter(StoryTag.tag_id == id_from)\
            .delete()

        # Issue tag
        to_tags = session.query(IssueTag)\
            .filter(IssueTag.tag_id == id_to)\
            .all()

        session.query(IssueTag)\
            .filter(IssueTag.tag_id == id_from)\
            .filter(IssueTag.issue_id.notin_([x.issue_id for x in to_tags]))\
            .update({IssueTag.issue_id: id_to}, synchronize_session=False)

        session.query(IssueTag)\
            .filter(IssueTag.tag_id == id_from)\
            .delete()

        # Person tag
        to_tags = session.query(PersonTag)\
            .filter(PersonTag.tag_id == id_to)\
            .all()

        session.query(PersonTag)\
            .filter(PersonTag.tag_id == id_from)\
            .filter(PersonTag.person_id.notin_(
                [x.person_id for x in to_tags]))\
            .update({PersonTag.person_id: id_to},
                    synchronize_session=False)

        session.query(PersonTag)\
            .filter(PersonTag.tag_id == id_from)\
            .delete()

        # Work tags
        to_tags = session.query(WorkTag)\
            .filter(WorkTag.tag_id == id_to)\
            .all()

        session.query(WorkTag)\
            .filter(WorkTag.tag_id == id_from)\
            .filter(WorkTag.work_id.notin_([x.work_id for x in to_tags]))\
            .update({WorkTag.tag_id: id_to}, synchronize_session=False)

        session.query(WorkTag)\
            .filter(WorkTag.tag_id == id_from)\
            .delete()

        session.query(Tag)\
            .filter(Tag.id == id_from)\
            .delete()

        session.commit()

    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'Tietokantavirhe. id={id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return retval


def tag_types() -> ResponseType:
    """ See api_tagTypes in api.py. """
    session = new_session()
    try:
        types = session.query(TagType).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagTypes: ' + str(exp))
        return ResponseType('TagTypes: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = TagTypeSchema(many=True)
        retval = schema.dump(types)
    except exceptions.MarshmallowError as exp:
        app.logger.error('TagTypes schema error: ' + str(exp))
        return ResponseType('TagTypes: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK)
