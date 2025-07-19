""" Functions related to short stories. """
from typing import Dict, Any, List, Union
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
import bleach

from app.impl import (EmptySearchResult, ResponseType, SearchResult,
                      SearchResultFields,
                      check_int, get_join_changes,
                      add_language, searchscore)
from app.impl_logs import log_changes
from app.route_helpers import new_session
from app.orm_decl import (Issue, Magazine, ShortStory, StoryTag, StoryType,
                          StoryGenre,
                          Language, Part, Edition, Awarded, IssueContent,
                          Contributor, Person)
from app.model_shortsearch import ShortSchemaForSearch
from app.model import ShortSchema, StoryTypeSchema, ShortBriefSchema
from app.impl_contributors import (update_short_contributors,
                                   contributors_have_changed,
                                   get_contributors_string)
from app.types import ContributorTarget, HttpResponseCode
from app import app


def _set_language(
        session: Any,
        item: Any,
        data: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Sets the language of an item for a short.

    Args:
        session (Any): The session object.
        item (Any): The item object to set the language for.
        data (Any): The data object containing the new language information.
        old_values (Union[Dict[str, Any], None]): The old values of the item,
        or None if no old values are available.

    Returns:
        Union[ResponseType, None]: The response type if an error occurs, or
        None if the language is set successfully.
    """
    if 'lang' not in data:
        return None
    if not data['lang'] or 'id' not in data['lang']:
        lang_id = None
        name = data['lang'] if data['lang'] != '' else None
    else:
        lang_id = check_int(data['lang']['id'])
        name = data['lang']['name']
    if lang_id != item.language:
        if old_values is not None:
            old_values['Kieli'] = (item.lang.name
                                   if item.lang is not None else '')
        if lang_id is None and name is not None:
            # User added a new language. Front returns this as a string
            # in the language field so we need to add this language to
            # the database first.
            lang_id = add_language(name)
        else:
            if lang_id is not None:
                lang = session.query(Language)\
                    .filter(Language.id == lang_id)\
                    .first()
                if not lang:
                    app.logger.error(f'SetLanguage: Language not found. Id = \
                                      {data["lang"]["id"]}.')
                    return ResponseType('Kieltä ei löydy',
                                        HttpResponseCode.BAD_REQUEST.value)
        item.language = lang_id
    return None


def check_story_type(session: Any, story_type: Any) -> bool:
    """
    Check the story type.

    Args:
        session (Any): The session object.
        story_type (Any): The story type.

    Returns:
        bool: True if the story type exists, False otherwise.
    """
    st = check_int(story_type)
    if st is None:
        return False
    t = session.query(StoryType).filter(StoryType.id == st).first()
    if not t:
        return False
    return True


def get_short_types() -> ResponseType:
    """
    Retrieves the short types from the database.

    Returns:
        ResponseType: The response object containing the result of the
        operation.
    """
    session = new_session()

    try:
        types = session.query(StoryType).all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in get_short_types: {exp}.')
        return ResponseType(
            f'get_short_types: Tietokantavirhe. id={id}: {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = StoryTypeSchema(many=True)
        retval = schema.dump(types)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_short_types schema error: {exp}.')
        return ResponseType(f'get_short_types: Skeemavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_short(short_id: int) -> ResponseType:
    """
    Retrieves a short story from the database based on the provided ID.

    Args:
        id (int): The ID of the short story to retrieve.

    Returns:
        ResponseType: The response containing the retrieved short story.

    Raises:
        SQLAlchemyError: If there is an error querying the database.
        exceptions.MarshmallowError: If there is an error with the schema.
    """
    session = new_session()

    try:
        short = session.query(ShortStory).filter(
            ShortStory.id == short_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_short exception: {exp}.')
        return ResponseType(
            f'get_short: Tietokantavirhe. id={short_id}: {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = ShortSchema()
        retval = schema.dump(short)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_short schema error: {exp}.')
        return ResponseType('get_short: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def search_stories(session: Any, searchwords: List[str]) -> SearchResult:
    retval: SearchResult = []
    found_stories: Dict[int, SearchResultFields] = {}

    for searchword in searchwords:
        lower_search = bleach.clean(searchword).lower()
        try:
            stories = session.query(ShortStory)\
                .filter(ShortStory.title.ilike(f'%{searchword}%'))\
                .all()
        except SQLAlchemyError as exp:
            app.logger.error(f'Exception in SearchStories: {exp}')
            return []
        for story in stories:
            item: SearchResultFields = EmptySearchResult
            if story.id in found_stories:
                found_stories[story]['score'] *= \
                    searchscore('story', story, lower_search)
            else:
                item: SearchResultFields = {
                    'id': story.id,
                    'header': story.title,
                    'author': ', '.join([a.name for a in story.authors]),
                    'img': '',
                    'type': 'story',
                    'score': searchscore('story', story, lower_search),
                    'description': ''
                }
            if item['id'] != '':
                found_stories[story.id] = item
        retval = [value for _, value in found_stories.items()]

    return retval


def search_shorts(params: Dict[str, str]) -> ResponseType:
    """
    Searches for short stories based on the given parameters.

    Args:
        params (Dict[str, str]): A dictionary containing the search parameters:
            - author: Author name or alternate name
            - title: Story title
            - orig_name: Original story title
            - pubyear_first: Earliest publication year
            - pubyear_last: Latest publication year

    Returns:
        ResponseType: The response object containing the search results.
    """
    session = new_session()

    # Start with base query
    query = session.query(ShortStory).distinct()

    # Add author filter if specified
    if 'author' in params and params['author']:
        author = bleach.clean(params['author'])
        query = query.join(Part, ShortStory.id == Part.shortstory_id)\
            .join(Contributor, Part.id == Contributor.part_id)\
            .join(Person, or_(
                Person.id == Contributor.person_id,
                Person.id == Contributor.real_person_id
            ))\
            .filter(
                or_(
                    Person.name.ilike(f'%{author}%'),
                    Person.alt_name.ilike(f'%{author}%')
                )
            )

    # Add title filter
    if 'title' in params and params['title']:
        title = bleach.clean(params['title'])
        query = query.filter(ShortStory.title.ilike(f'%{title}%'))

    # Add original title filter
    if 'orig_name' in params and params['orig_name']:
        orig_name = bleach.clean(params['orig_name'])
        query = query.filter(ShortStory.orig_name.ilike(f'%{orig_name}%'))

    # Add publication year range filters
    try:
        if 'pubyear_first' in params and params['pubyear_first']:
            year_first = int(bleach.clean(params['pubyear_first']))
            query = query.filter(ShortStory.pubyear >= year_first)

        if 'pubyear_last' in params and params['pubyear_last']:
            year_last = int(bleach.clean(params['pubyear_last']))
            query = query.filter(ShortStory.pubyear <= year_last)
    except ValueError as exp:
        app.logger.error(f'Invalid year format in search_shorts: {exp}')
        return ResponseType(
            'Virheellinen vuosiluku',
            HttpResponseCode.BAD_REQUEST.value
        )

    if 'type' in params and params['type']:
        typ = check_int(params['type'])
        if typ is None:
            app.logger.error(
                f'Invalid type in search_shorts: {params["type"]}')
            return ResponseType(
                'Virheellinen tyyppi',
                HttpResponseCode.BAD_REQUEST.value
            )
        query = query.filter(ShortStory.story_type == typ)

    if 'magazine' in params and params['magazine']:
        magazine = params['magazine']
        query = query.join(IssueContent, ShortStory.id ==
                           IssueContent.shortstory_id)\
            .join(Issue, Issue.id == IssueContent.issue_id)\
            .join(Magazine, Magazine.id == Issue.magazine_id)\
            .filter(Magazine.id == magazine)

    if 'awarded' in params and params['awarded'] and params['awarded'] != '0':
        query = query.join(Awarded, ShortStory.id == Awarded.story_id)

    # Add ordering
    query = query.order_by(ShortStory.title)

    try:
        shorts = query.all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Database error in search_shorts: {exp}')
        return ResponseType(
            f'Tietokantavirhe: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value
        )

    try:
        schema = ShortSchemaForSearch(many=True)
        result = schema.dump(shorts)
        return ResponseType(result, HttpResponseCode.OK.value)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error in search_shorts: {exp}')
        return ResponseType(
            f'Skeemavirhe: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value
        )


def story_add(data: Any) -> ResponseType:
    """
    Adds a story to the database.

    Args:
        data (Any): The data to be added to the database.

    Returns:
        ResponseType: The response indicating the success status of the
        operation.
    """
    session = new_session()

    data = data['data']

    story = ShortStory()

    if ('title' not in data or len(data['title']) == 0
            or data['title'] is None):
        app.logger.error('story_add: Title is empty.')
        return ResponseType('Otsikko ei voi olla tyhjä.',
                            HttpResponseCode.BAD_REQUEST.value)
    story.title = data['title']

    if 'orig_title' in data:
        story.orig_title = data['orig_title']

    if 'type' not in data:
        typ = 1  # default, short story
    else:
        if not check_story_type(session, data['type']['id']):
            app.logger.error(
                f'StoryUpdate exception. Not a type: {data["type"]}.')
            return ResponseType(
                f'Virheellinen tyyppi {data["type"]}.',
                HttpResponseCode.BAD_REQUEST.value)
        typ = data["type"]['id']
    story.story_type = typ

    if 'pubyear' in data:
        pubyear = check_int(data['pubyear'])
        story.pubyear = pubyear

    result = _set_language(session, story, data, old_values=None)
    if result:
        return result

    try:
        session.add(story)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in story_add(): {exp}.')
        return ResponseType(f'Tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if 'contributors' not in data:
        app.logger.error('story_add: No contributors.')
        return ResponseType('Tekijä puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)

    # Add new part (required for contributors)
    part = Part(shortstory_id=story.id)
    session.add(part)
    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in story_add(): {exp}.')
        return ResponseType(f'Tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Add contributors
    update_short_contributors(session, story.id, data['contributors'])

    # Add genres
    for genre in data['genres']:
        g = StoryGenre(shortstory_id=story.id, genre_id=genre['id'])
        session.add(g)

    # Add tags
    for tag in data['tags']:
        t = StoryTag(shortstory_id=story.id, tag_id=tag['id'])
        session.add(t)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in story_add(): {exp}.')
        return ResponseType(f'Tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    app.logger.error(f'story: {story.id}')
    return ResponseType(str(story.id), HttpResponseCode.CREATED.value)


def story_updated(params: Any) -> ResponseType:
    """
    Updates a story in the database based on the given parameters.

    Parameters:
    - params (Any): The parameters for updating the story.

    Returns:
    - ResponseType: The response indicating the success or failure of the
    update operation.
    """
    session = new_session()
    old_values = {}
    story: Any = None
    data = params['data']
    short_id = check_int(data['id'])

    short_id = check_int(data['id'], False, False)
    if short_id is None:
        app.logger.error(f'StoryUpdate: Invalid id: {data["id"]}.')
        return ResponseType(f'StoryUpdate: virheellinen id {data["id"]}.',
                            HttpResponseCode.BAD_REQUEST.value)

    story = session.query(ShortStory).filter(
        ShortStory.id == short_id).first()
    if not story:
        app.logger.error(f'StoryUpdate: Story not found. Id = {short_id}.')
        return ResponseType(f'StoryUpdate: Novellia ei löydy. id={short_id}.',
                            HttpResponseCode.BAD_REQUEST.value)

    # Save title
    if 'title' in data:
        if data['title'] is None or len(data['title']) == 0:
            app.logger.error('StoryUpdate: Title is a required field.')
            return ResponseType('StoryUpdate: Nimi on pakollinen tieto.',
                                HttpResponseCode.BAD_REQUEST.value)
        if data['title'] != story.title:
            old_values['Nimi'] = story.title
            story.title = data['title']

    # Save original title
    if 'orig_title' in data:
        if data['orig_title'] != story.orig_title:
            old_values['Alkukielinen nimi'] = story.orig_title
            story.orig_title = data['orig_title']

    # Save original (first) publication year
    if 'pubyear' in data:
        if data['pubyear'] != story.pubyear:
            pubyear = check_int(data['pubyear'])
            old_values['Julkaistu'] = story.pubyear
            story.pubyear = pubyear

    # Save story type
    if 'type' in data:
        if data['type']['id'] != story.type.id:
            if not check_story_type(session, data['type']['id']):
                app.logger.error(
                    f'StoryUpdate exception. Not a type: {data["type"]}.')
                return ResponseType(
                    f'StoryUpdate: virheellinen tyyppi {data["type"]}.',
                    HttpResponseCode.BAD_REQUEST.value)
            old_values['Tyyppi'] = story.type.name
            story.story_type = data["type"]['id']

    # Save original language
    if 'lang' in data:
        result = _set_language(session, story, data, old_values)
        if result:
            return result

    try:
        session.add(story)
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in StoryUpdate: {exp}.')
        return ResponseType('StoryUpdate: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Save contributors
    if 'contributors' in data:
        if contributors_have_changed(story.contributors, data['contributors']):
            try:
                contributor_str = get_contributors_string(
                    story.contributors, ContributorTarget.SHORT)
            except ValueError as exp:
                session.rollback()
                app.logger.error(f'Exception in StoryUpdate: {exp}.')
                return ResponseType(
                    f'StoryUpdate: Tietokantavirhe: {exp}.',
                    HttpResponseCode.INTERNAL_SERVER_ERROR.value)
            update_short_contributors(
                session, story.id, data['contributors'])
            old_values['Tekijät'] = contributor_str

    # Save genres
    if 'genres' in data:
        existing_genres = session.query(StoryGenre)\
            .filter(StoryGenre.shortstory_id == story.id) \
            .all()
        (to_add, to_remove) = get_join_changes(
            [x.genre_id for x in existing_genres],
            [x['id'] for x in data['genres']])
        for genre_id in to_remove:
            dg = session.query(StoryGenre)\
                .filter(StoryGenre.genre_id == genre_id)\
                .filter(StoryGenre.shortstory_id == story.id)\
                .first()
            session.delete(dg)
        for genre_id in to_add:
            sg = StoryGenre(genre_id=genre_id, shortstory_id=story.id)
            session.add(sg)
        if len(to_add) > 0 or len(to_remove) > 0:
            old_values['Genret'] = ' -'.join([str(x) for x in to_add])
            old_values['Genret'] += ' +'.join([str(x) for x in to_remove])

    # Save tags
    if 'tags' in data:
        existing_tags = session.query(StoryTag)\
            .filter(StoryTag.shortstory_id == story.id)\
            .all()
        (to_add, to_remove) = get_join_changes(
            [x.tag_id for x in existing_tags],
            [x['id'] for x in data['tags']])
        for tag_id in to_remove:
            dt = session.query(StoryTag)\
                .filter(StoryTag.tag_id == tag_id)\
                .filter(StoryTag.shortstory_id == story.id)\
                .first()
            session.delete(dt)
        for tag_id in to_add:
            st = StoryTag(tag_id=tag_id, shortstory_id=story.id)
            session.add(st)
        if len(to_add) > 0 or len(to_remove) > 0:
            old_values['Asiasanat'] = ' -'.join([str(x) for x in to_add])
            old_values['Asiasanat'] += ' +'.join([str(x) for x in to_remove])

    if len(old_values) == 0:
        return ResponseType(str(story.id), HttpResponseCode.OK.value)

    log_changes(session=session, obj=story, name_field="title",
                action="Päivitys", old_values=old_values)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in StoryUpdate commit: {exp}.')
        return ResponseType('StoryUpdate: Tietokantavirhe tallennettaessa.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(str(story.id), HttpResponseCode.OK.value)


def story_delete(short_id: int) -> ResponseType:
    """
    Delete a story with the given short ID.

    Args:
        short_id (int): The short ID of the story to be deleted.

    Returns:
        ResponseType: The response indicating the result of the deletion.
    """

    session = new_session()
    awarded = session.query(Awarded)\
        .filter(Awarded.story_id == short_id)\
        .all()
    if len(awarded) > 0:
        app.logger.error(
            f'StoryDelete: Story has been awarded. short_id={short_id}.')
        return ResponseType(f'story_delete: Novellilla on palkinto. \
                            id={short_id}.',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        story = session.query(ShortStory)\
            .filter(ShortStory.id == short_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in StoryDelete: {exp}.')
        return ResponseType('StoryDelete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not story:
        app.logger.error(f'StoryDelete: Story not found. Id = {short_id}.')
        return ResponseType(f'StoryDelete: Novellia ei löydy. id={short_id}.',
                            HttpResponseCode.BAD_REQUEST.value)

    in_issues = session.query(IssueContent)\
        .filter(IssueContent.shortstory_id == short_id)\
        .all()
    for issue in in_issues:
        session.delete(issue)

    genres = session.query(StoryGenre)\
        .filter(StoryGenre.shortstory_id == short_id)\
        .all()
    for genre in genres:
        session.delete(genre)

    tags = session.query(StoryTag)\
        .filter(StoryTag.shortstory_id == short_id)\
        .all()
    for tag in tags:
        session.delete(tag)

    contributors = session.query(Contributor)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.shortstory_id == short_id)\
        .all()
    for contrib in contributors:
        session.delete(contrib)

    parts = session.query(Part)\
        .filter(Part.shortstory_id == short_id)\
        .all()
    for part in parts:
        session.delete(part)

    session.delete(story)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in story_delete commit: {exp}.')
        return ResponseType('story_delete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def story_tag_add(short_id: int, tag_id: int) -> ResponseType:
    """
    Adds a tag to a short story.

    Args:
        short_id (int): The ID of the short story.
        tag_id (int): The ID of the tag to be added.

    Returns:
        ResponseType: The response type indicating the success or failure of
        the operation.
    """
    session = new_session()

    try:
        short = session.query(ShortStory).filter(
            ShortStory.id == short_id).first()
        if not short:
            app.logger.error(
                f'StoryTagAdd: Short not found. Id = {short_id}.')
            return ResponseType('Novellia ei löydy',
                                HttpResponseCode.BAD_REQUEST.value)

        short_tag = StoryTag()
        short_tag.shortstory_id = short_id
        short_tag.tag_id = tag_id
        session.add(short_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagAdd(): ' + str(exp))
        return ResponseType(f'ShortTagAdd: Tietokantavirhe. \
                            short_id={short_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('Asiasana lisätty novellille',
                        HttpResponseCode.OK.value)


def story_tag_remove(short_id: int, tag_id: int) -> ResponseType:
    """
    Removes a tag from a story.

    Parameters:
        short_id (int): The ID of the short story.
        tag_id (int): The ID of the tag to be removed.

    Returns:
        ResponseType: The response object containing the result of the
        operation.
    """
    session = new_session()
    tag_name = ""
    try:
        short_tag = session.query(StoryTag)\
            .filter(StoryTag.shortstory_id == short_id,
                    StoryTag.tag_id == tag_id)\
            .first()
        if not short_tag:
            app.logger.error(
                'story_tag_remove: Short has no such tag: '
                'short_id {short_id}, '
                'tag {tag_id}.'
            )
            return ResponseType('story_tag_remove: '
                                'Tagia ei löydy novellilta. '
                                f'short_id={short_id}, tag_id={tag_id}.',
                                HttpResponseCode.BAD_REQUEST.value)
        tag_name = short_tag.name
        session.delete(short_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(f'story_tag_remove():  {exp}.')
        return ResponseType(f'story_tagremove: Tietokantavirhe. \
                            short_id={short_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    short = session.query(ShortStory).filter(
        ShortStory.id == short_id).first()
    return ResponseType(
        f'Asiasana {tag_name} poistettu novellilta {short.title}.',
        HttpResponseCode.OK.value)


def save_short_to_edition(
        session: Any, edition_id: int, short_id: int) -> bool:
    """
    Save a short to an edition.

    Args:
        session (Any): The session object used to interact with the database.
        edition_id (int): The ID of the edition.
        short_id (int): The ID of the short.

    Returns:
        bool: True if the short is successfully saved to the edition, False
              otherwise.
    """

    try:
        # Get work id from part
        part = session.query(Part)\
            .filter(Part.edition_id == edition_id)\
            .first()
        short_part = Part(work_id=part.work_id, edition_id=edition_id,
                          shortstory_id=short_id)
        session.add(short_part)
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in save_short_to_edition: {exp}')
        return False
    return True


def save_short_to_work(session: Any, work_id: int, short_id: int) -> bool:
    """
    Saves a short to a work in the database.

    This will add the short to all work editions.

    Args:
        session (Any): The database session.
        work_id (int): The ID of the work.
        short_id (int): The ID of the short.

    Returns:
        bool: True if the short is saved successfully, False otherwise.
    """
    try:
        editions = session.query(Edition)\
            .join(Part)\
            .filter(Part.edition_id == Edition.id)\
            .filter(Part.work_id == work_id)\
            .filter(Part.shortstory_id.is_(None))\
            .all()
        for edition in editions:
            retval = save_short_to_edition(session, edition.id, short_id)
            if not retval:
                return False
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in save_short_to_work: {exp}')
        return False
    return True


def get_latest_shorts(count: int) -> ResponseType:
    """
    Retrieves the latest shorts.

    Args:
        count (int): The number of shorts to retrieve.

    Returns:
        ResponseType: The response containing the serialized shorts.
    """
    session = new_session()
    try:
        shorts = session.query(ShortStory)\
            .order_by(ShortStory.id.desc())\
            .limit(count)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in get_latest_shorts(): {str(exp)}')
        return ResponseType('Tietokantavirhe',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    try:
        schema = ShortBriefSchema(many=True)
        retval = schema.dump(shorts)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Exception in get_latest_shorts(): {str(exp)}')
        return ResponseType('get_latest_shorts: Tietokantavirhe',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, status=HttpResponseCode.OK.value)
