""" Functions related to short stories. """
from typing import Dict, Any, Union
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
import bleach

from app.impl import (ResponseType, check_int, log_changes, get_join_changes,
                      add_language)
from app.route_helpers import new_session
from app.orm_decl import (ShortStory, StoryTag, StoryType, StoryGenre,
                          Language, Part, Edition)
from app.model_shortsearch import ShortSchemaForSearch
from app.model import ShortSchema, StoryTypeSchema
from app.impl_contributors import (update_short_contributors,
                                   contributors_have_changed,
                                   get_contributors_string)

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
    if 'id' not in data['lang']:
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
                                      {data["language"]["id"]}.')
                    return ResponseType('Kieltä ei löydy', 400)
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
        app.logger.error(f'Exception in GetShortTypes: {exp}.')
        return ResponseType(f'GetShortTypes: Tietokantavirhe. id={id}', 400)

    try:
        schema = StoryTypeSchema(many=True)
        retval = schema.dump(types)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'GetShortTypes schema error: {exp}.')
        return ResponseType('GetShortTypes: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


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
        app.logger.error(f'Exception in GetShort: {exp}')
        return ResponseType(f'GetShort: Tietokantavirhe. id={short_id}', 400)

    try:
        schema = ShortSchema()
        retval = schema.dump(short)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'GetStory schema error: {exp}.')
        return ResponseType('GetStory: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def search_shorts(params: Dict[str, str]) -> ResponseType:
    """
    Searches for short stories based on the given parameters.

    Args:
        params (Dict[str, str]): A dictionary containing the search parameters.

    Returns:
        ResponseType: The response object containing the search results.
    """
    session = new_session()

    stmt = 'SELECT DISTINCT shortstory.* FROM shortstory '
    if 'author' in params:
        author = bleach.clean(params['author'])
        stmt += 'INNER JOIN part on part.shortstory_id = shortstory.id '
        stmt += 'INNER JOIN contributor on contributor.part_id = part.id '
        stmt += 'INNER JOIN person on person.id = contributor.person_id '
        stmt += 'AND (lower(person.name) like lower("' + author + \
            '%") OR lower(person.alt_name) like lower("' + author + '%")) '
    if ('title' in params or 'orig_name' in params
            or 'pubyear_first' in params or 'pubyear_last' in params):
        stmt += " WHERE 1=1 "
        if 'title' in params and params['title'] != '':
            title = bleach.clean(params['title'])
            stmt += 'AND lower(shortstory.title) like lower("%' + \
                title + '%") '
        if 'orig_name' in params and params['orig_name'] != '':
            orig_name = bleach.clean(params['orig_name'])
            stmt += 'AND lower(shortstory.orig_name) like lower("%' + \
                orig_name + '%") '
        if 'pubyear_first' in params and params['pubyear_first'] != '':
            pubyear_first = bleach.clean(params['pubyear_first'])
            try:
                # Test that value is actually an integer, we still need to use
                # the string version in the query.
                # pylint: disable-next=unused-variable
                test_value = int(pubyear_first)
                stmt += 'AND shortstory.pubyear >= ' + pubyear_first + ' '
            except (TypeError) as exp:
                app.logger.error(f'Failed to convert pubyear_first: {exp}')
        if 'pubyear_last' in params and params['pubyear_last'] != '':
            pubyear_last = bleach.clean(params['pubyear_last'])
            try:
                test_value = int(pubyear_last)  # noqa: F841
                stmt += 'AND shortstory.pubyear <= ' + pubyear_last + ' '
            except (TypeError) as exp:
                app.logger.error(f'Failed to convert pubyear_first: {exp}')

    stmt += 'ORDER BY shortstory.title'

    # print(stmt)
    try:
        shorts = session.query(ShortStory)\
            .from_statement(text(stmt))\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in SearchShorts: ' + str(exp))
        return ResponseType(f'SearchShorts: Tietokantavirhe. id={id}', 400)

    try:
        schema = ShortSchemaForSearch(many=True)
        retval = schema.dump(shorts)
    except exceptions.MarshmallowError as exp:
        app.logger.error('SearchShorts schema error: ' + str(exp))
        return ResponseType('SearchShorts: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


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
        return ResponseType('Otsikko ei voi olla tyhjä.', 400)
    story.title = data['title']

    if 'orig_name' in data:
        story.orig_title = data['orig_title']

    if 'type' not in data:
        typ = 1  # default, short story
    else:
        if not check_story_type(session, data['type']['id']):
            app.logger.error(
                f'StoryUpdate exception. Not a type: {data["type"]}.')
            return ResponseType(
                f'Virheellinen tyyppi {data["type"]}.', 400)
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
        return ResponseType(f'Tietokantavirhe: {exp}.', 400)

    if 'contributors' not in data:
        app.logger.error('story_add: No contributors.')
        return ResponseType('Tekijä puuttuu.', 400)

    # Add new part (required for contributors)
    part = Part(shortstory_id=story.id)
    session.add(part)
    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in story_add(): {exp}.')
        return ResponseType(f'Tietokantavirhe: {exp}.', 400)

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
        return ResponseType(f'Tietokantavirhe: {exp}.', 400)

    app.logger.error(f'story: {story.id}')
    return ResponseType(str(story.id), 201)


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
        return ResponseType(f'StoryUpdate: virheellinen id {data["id"]}.', 400)

    story = session.query(ShortStory).filter(
        ShortStory.id == short_id).first()
    if not story:
        app.logger.error(f'StoryUpdate: Story not found. Id = {short_id}.')
        return ResponseType(f'StoryUpdate: Novellia ei löydy. id={short_id}.',
                            400)

    # Save title
    if 'title' in data:
        if data['title'] is None or len(data['title']) == 0:
            app.logger.error('StoryUpdate: Title is a required field.')
            return ResponseType('StoryUpdate: Nimi on pakollinen tieto.', 400)
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
                    f'StoryUpdate: virheellinen tyyppi {data["type"]}.', 400)
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
        return ResponseType('StoryUpdate: Tietokantavirhe.', 400)

    # Save contributors
    if 'contributors' in data:
        if contributors_have_changed(story.contributors, data['contributors']):
            update_short_contributors(
                session, story.id, data['contributors'])
            old_values['Tekijät'] = get_contributors_string(story.contributors)

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
        return ResponseType(str(story.id), 200)

    log_changes(session=session, obj=story, name_field="title",
                action="Päivitys", old_values=old_values)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in StoryUpdate commit: {exp}.')
        return ResponseType('StoryUpdate: Tietokantavirhe tallennettaessa.',
                            400)

    return ResponseType(str(story.id), 200)


def story_delete(short_id: int) -> ResponseType:
    """
    Delete a story with the given short ID.

    Args:
        short_id (int): The short ID of the story to be deleted.

    Returns:
        ResponseType: The response indicating the result of the deletion.
    """

    session = new_session()
    try:
        story = session.query(ShortStory)\
            .filter(ShortStory.id == short_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in StoryDelete: {exp}.')
        return ResponseType('StoryDelete: Tietokantavirhe.', 400)

    if not story:
        app.logger.error(f'StoryDelete: Story not found. Id = {short_id}.')
        return ResponseType(f'StoryDelete: Novellia ei löydy. id={short_id}.',
                            400)
    session.delete(story)

    return ResponseType('OK', 200)


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
            return ResponseType('Novellia ei löydy', 400)

        short_tag = StoryTag()
        short_tag.shortstory_id = short_id
        short_tag.tag_id = tag_id
        session.add(short_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagAdd(): ' + str(exp))
        return ResponseType(f'ShortTagAdd: Tietokantavirhe. \
                            short_id={short_id}, tag_id={tag_id}.', 400)

    return ResponseType('Asiasana lisätty novellille', 200)


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
    retval = ResponseType('', 200)
    session = new_session()

    try:
        short_tag = session.query(StoryTag)\
            .filter(StoryTag.shortstory_id == short_id,
                    StoryTag.tag_id == tag_id)\
            .first()
        if not short_tag:
            app.logger.error(
                f'ShortTagRemove: Short has no such tag: short_id {short_id}, \
                      tag {tag_id}.'
            )
            return ResponseType(f'ShortTagRemove: Tagia ei löydy novellilta. \
                                short_id={short_id}, tag_id={tag_id}.', 400)
        session.delete(short_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagRemove(): ' + str(exp))
        return ResponseType(f'ShortTagRemove: Tietokantavirhe. \
                            short_id={short_id}, tag_id={tag_id}.', 400)

    return retval


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
