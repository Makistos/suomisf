""" Functions related to tags. """
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from marshmallow import exceptions
from app.orm_decl import (Tag, ArticleTag, IssueTag, Bookseries, Edition,
                          EditionContributor, Work, WorkContributor,
                          PersonTag, StoryTag, TagType, WorkTag)
from app.model import (TagBriefSchema, TagSchema, TagTypeSchema)
from app.route_helpers import new_session
from app.impl import ResponseType
from app.impl_logs import log_changes
from app import app
from app.types import HttpResponseCode
from app.names import clean_name


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
        schema = TagSchema(many=True, only=('id', 'name', 'type'))
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
        tags = session.execute(text(stmt)).all()
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


def _tag_page_loaders() -> List[Any]:
    """Load what TagSchema serializes up front (5,047 lazy-load queries for
    a tag with 360 works before)."""
    def contributors(rel: Any, model: Any) -> Any:
        return rel.options(selectinload(model.person),
                           selectinload(model.real_person),
                           selectinload(model.role))
    works = selectinload(Tag.works)
    return [
        works.options(
            contributors(selectinload(Work.contributions), WorkContributor),
            selectinload(Work.genres),
            selectinload(Work.bookseries).selectinload(Bookseries.partof),
            selectinload(Work.language_name)),
        works.selectinload(Work.editions).options(
            contributors(selectinload(Edition.contributions), EditionContributor),
            selectinload(Edition.images),
            selectinload(Edition.publisher),
            selectinload(Edition.owners),
            selectinload(Edition.wishlisted)),
        selectinload(Tag.stories),
        selectinload(Tag.articles),
        selectinload(Tag.magazines),
        selectinload(Tag.people),
        selectinload(Tag.type),
    ]


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
        tag = session.query(Tag).options(*_tag_page_loaders())\
            .filter(Tag.id == tag_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in TagInfo (id: {tag_id}): ' + str(exp))
        return ResponseType('TagInfo: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not tag:
        return ResponseType(f'Asiasanaa ei löydy. id={tag_id}.', HttpResponseCode.NOT_FOUND.value)

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

    if not tag:
        return ResponseType(f'Asiasanaa ei löydy. id={tag_id}.', HttpResponseCode.NOT_FOUND.value)

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
            .filter(Tag.name.ilike(clean_name(name)))\
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
    log_changes(session, obj=tag, action='Uusi')
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

    old_values = {}
    if name != tag.name:
        old_values['Nimi'] = tag.name
    if str(type_id) != str(tag.type_id):
        old_values['Tyyppi'] = tag.type_id
    if (description or None) != (tag.description or None):
        old_values['Kuvaus'] = tag.description
    tag.name = name
    tag.type_id = type_id
    tag.description = description
    session.add(tag)
    log_changes(session, obj=tag, old_values=old_values)
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
        if not tag:
            app.logger.error(f'TagDelete: Tag not found. id = {tag_id}.')
            return ResponseType('Asiasanan tunnistetta ei löydy',
                                HttpResponseCode.NOT_FOUND.value)
        log_changes(session, obj=tag, action='Poisto',
                    old_values={'Nimi': tag.name})
        session.delete(tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagDelete: ' + str(exp))
        return ResponseType(f'TagDelete: Tietokantavirhe. id={tag_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return retval


def tag_merge(id_to: int, id_from: int) -> ResponseType:
    """ See api_tagMerge in api.py. """
    retval = ResponseType('', HttpResponseCode.OK.value)
    # Merging a tag into itself would delete every link to it and then
    # the tag itself.
    if id_to == id_from:
        app.logger.error(f'TagMerge: Tag {id_to} merged with itself.')
        return ResponseType('Asiasanaa ei voi yhdistää itseensä.',
                            HttpResponseCode.BAD_REQUEST.value)
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
                            HttpResponseCode.NOT_FOUND.value)

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
            .update({ArticleTag.tag_id: id_to}, synchronize_session=False)

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
            .update({StoryTag.tag_id: id_to}, synchronize_session=False)

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
            .update({IssueTag.tag_id: id_to}, synchronize_session=False)

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
            .update({PersonTag.tag_id: id_to},
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

        log_changes(session, obj=tag_to,
                    old_values={'Yhdistetty': tag_from.name})
        log_changes(session, obj=tag_from, action='Poisto',
                    old_values={'Nimi': tag_from.name})
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


# Suggestions written by scripts/tag_similarity.py (migration 044).
SIMILARITY_KINDS = ('duplicate', 'related')
SIMILARITY_STATUSES = ('new', 'dismissed')

SIMILAR_STMT = """
WITH uses AS (
    SELECT tag_id, count(*) AS n FROM (
        SELECT tag_id FROM worktag
        UNION ALL SELECT tag_id FROM storytag
        UNION ALL SELECT tag_id FROM articletag) links
    GROUP BY tag_id)
SELECT s.kind, s.reason, s.name_score, s.containment, s.shared, s.status,
       s.decided_at, u.name AS decided_by, s.updated,
       a.id AS a_id, a.name AS a_name, a.type_id AS a_type_id,
       ta.name AS a_type, coalesce(ua.n, 0) AS a_uses,
       b.id AS b_id, b.name AS b_name, b.type_id AS b_type_id,
       tb.name AS b_type, coalesce(ub.n, 0) AS b_uses
FROM tag_similarity s
JOIN tag a ON a.id = s.tag_a
JOIN tag b ON b.id = s.tag_b
LEFT JOIN tagtype ta ON ta.id = a.type_id
LEFT JOIN tagtype tb ON tb.id = b.type_id
LEFT JOIN uses ua ON ua.tag_id = a.id
LEFT JOIN uses ub ON ub.tag_id = b.id
LEFT JOIN "user" u ON u.id = s.decided_by
WHERE s.status = :status AND (:kind IS NULL OR s.kind = :kind)
ORDER BY s.kind, coalesce(s.name_score, s.containment) DESC NULLS LAST,
         a.name, b.name
"""


def _similar_tag(row: Any, side: str) -> Dict[str, Any]:
    type_id = getattr(row, f'{side}_type_id')
    return {
        'id': getattr(row, f'{side}_id'),
        'name': getattr(row, f'{side}_name'),
        'type': ({'id': type_id, 'name': getattr(row, f'{side}_type')}
                 if type_id is not None else None),
        'uses': getattr(row, f'{side}_uses'),
    }


def tag_similar(kind: Optional[str], status: str) -> ResponseType:
    """ See api_tagsimilar in api_tags.py. """
    if kind is not None and kind not in SIMILARITY_KINDS:
        return ResponseType(f'Tuntematon tyyppi: {kind}',
                            HttpResponseCode.BAD_REQUEST.value)
    if status not in SIMILARITY_STATUSES:
        return ResponseType(f'Tuntematon tila: {status}',
                            HttpResponseCode.BAD_REQUEST.value)
    session = new_session()
    try:
        rows = session.execute(text(SIMILAR_STMT),
                               {'kind': kind, 'status': status}).all()
        updated = session.execute(
            text('SELECT max(updated) FROM tag_similarity')).scalar()
        # Pairs in each view: new duplicates, new related, dismissed.
        counts = dict(session.execute(text("""
            SELECT CASE WHEN status = 'dismissed' THEN 'dismissed'
                        ELSE kind END, count(*)
            FROM tag_similarity GROUP BY 1""")).all())
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagSimilar: ' + str(exp))
        return ResponseType('TagSimilar: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    pairs = [{
        'tag_a': _similar_tag(row, 'a'),
        'tag_b': _similar_tag(row, 'b'),
        'kind': row.kind,
        'reason': row.reason,
        'name_score': row.name_score,
        'containment': row.containment,
        'shared': row.shared,
        'status': row.status,
        'decided_by': row.decided_by,
        'decided_at': row.decided_at.isoformat() if row.decided_at else None,
    } for row in rows]
    return ResponseType({
        'updated': updated.isoformat() if updated else None,
        'counts': {view: counts.get(view, 0)
                   for view in ('duplicate', 'related', 'dismissed')},
        'pairs': pairs,
    }, HttpResponseCode.OK.value)


def tag_similar_decide(tag_a: int, tag_b: int, status: str,
                       user_id: int) -> ResponseType:
    """ Set the status of a suggested pair: 'dismissed' (not the same, or
    not related) or 'new' (restored). The job never changes it. Dismissing
    a pair an admin added removes it instead (status 'removed'). """
    if tag_a == tag_b:
        return ResponseType('Asiasanapari on virheellinen.',
                            HttpResponseCode.BAD_REQUEST.value)
    session = new_session()
    try:
        if status == 'dismissed' and session.execute(text("""
                DELETE FROM tag_similarity
                WHERE tag_a = :a AND tag_b = :b AND reason = 'manual'"""),
                {'a': min(tag_a, tag_b), 'b': max(tag_a, tag_b)}
                ).rowcount:  # type: ignore[attr-defined]
            session.commit()
            return ResponseType({'tag_a': min(tag_a, tag_b),
                                 'tag_b': max(tag_a, tag_b),
                                 'status': 'removed'},
                                HttpResponseCode.OK.value)
        result = session.execute(text("""
            UPDATE tag_similarity
            SET status = :status, decided_by = :user_id, decided_at = now()
            WHERE tag_a = :a AND tag_b = :b"""), {
                'status': status, 'user_id': user_id,
                'a': min(tag_a, tag_b), 'b': max(tag_a, tag_b)})
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in TagSimilarDecide: ' + str(exp))
        return ResponseType('TagSimilarDecide: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    if result.rowcount == 0:  # type: ignore[attr-defined]
        return ResponseType('Asiasanaparia ei löydy.',
                            HttpResponseCode.NOT_FOUND.value)
    return ResponseType({'tag_a': min(tag_a, tag_b),
                         'tag_b': max(tag_a, tag_b), 'status': status},
                        HttpResponseCode.OK.value)


TAG_SIMILAR_STMT = """
SELECT t.id, t.name, t.type_id, tt.name AS type_name, s.kind, s.reason
FROM tag_similarity s
JOIN tag t ON t.id = CASE WHEN s.tag_a = :id THEN s.tag_b ELSE s.tag_a END
LEFT JOIN tagtype tt ON tt.id = t.type_id
WHERE (s.tag_a = :id OR s.tag_b = :id) AND s.status = 'new'
ORDER BY s.kind, s.reason = 'manual' DESC,
         coalesce(s.name_score, s.containment) DESC NULLS LAST, t.name
"""


def tag_similar_to(tag_id: int) -> ResponseType:
    """ See api_tagsimilarto in api_tags.py. """
    session = new_session()
    try:
        rows = session.execute(text(TAG_SIMILAR_STMT), {'id': tag_id}).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in TagSimilarTo: ' + str(exp))
        return ResponseType('TagSimilarTo: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType([{
        'id': row.id,
        'name': row.name,
        'type': ({'id': row.type_id, 'name': row.type_name}
                 if row.type_id is not None else None),
        'kind': row.kind,
        'reason': row.reason,
    } for row in rows], HttpResponseCode.OK.value)


def tag_similar_add(tag_a: int, tag_b: int, user_id: int) -> ResponseType:
    """ Link two tags as related by hand (reason 'manual'), which the job
    never changes. A dismissed pair becomes this; a pair already
    suggested is left as it is. """
    if tag_a == tag_b:
        return ResponseType('Asiasanaa ei voi liittää itseensä.',
                            HttpResponseCode.BAD_REQUEST.value)
    a, b = min(tag_a, tag_b), max(tag_a, tag_b)
    session = new_session()
    try:
        found = session.execute(text(
            'SELECT count(*) FROM tag WHERE id IN (:a, :b)'),
            {'a': a, 'b': b}).scalar()
        if found != 2:
            return ResponseType('Tuntematon asiasanan tunniste',
                                HttpResponseCode.NOT_FOUND.value)
        session.execute(text("""
            INSERT INTO tag_similarity (tag_a, tag_b, kind, reason,
                                        decided_by, decided_at)
            VALUES (:a, :b, 'related', 'manual', :user_id, now())
            ON CONFLICT (tag_a, tag_b) DO UPDATE
            SET kind = 'related', reason = 'manual', status = 'new',
                name_score = NULL, containment = NULL, shared = 0,
                decided_by = :user_id, decided_at = now(), updated = now()
            WHERE tag_similarity.status = 'dismissed'"""),
            {'a': a, 'b': b, 'user_id': user_id})
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in TagSimilarAdd: ' + str(exp))
        return ResponseType('TagSimilarAdd: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType({'tag_a': a, 'tag_b': b}, HttpResponseCode.OK.value)


def tag_similar_kind(tag_a: int, tag_b: int, kind: str,
                     user_id: int) -> ResponseType:
    """ Set a pair's kind ('duplicate' or 'related') by hand. The job keeps
    it from then on, and keeps the pair even if its rules no longer find
    it. """
    if kind not in SIMILARITY_KINDS:
        return ResponseType(f'Tuntematon tyyppi: {kind}',
                            HttpResponseCode.BAD_REQUEST.value)
    a, b = min(tag_a, tag_b), max(tag_a, tag_b)
    session = new_session()
    try:
        result = session.execute(text("""
            UPDATE tag_similarity
            SET kind = :kind, kind_fixed = true, decided_by = :user_id,
                decided_at = now()
            WHERE tag_a = :a AND tag_b = :b"""),
            {'kind': kind, 'user_id': user_id, 'a': a, 'b': b})
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in TagSimilarKind: ' + str(exp))
        return ResponseType('TagSimilarKind: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    if result.rowcount == 0:  # type: ignore[attr-defined]
        return ResponseType('Asiasanaparia ei löydy.',
                            HttpResponseCode.NOT_FOUND.value)
    return ResponseType({'tag_a': a, 'tag_b': b, 'kind': kind},
                        HttpResponseCode.OK.value)
