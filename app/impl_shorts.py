import bleach
from typing import Dict, Any, Union
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.impl import (ResponseType, checkInt, LogChanges, GetJoinChanges,
                      AddLanguage, SetLanguage)
from app.route_helpers import new_session
from app.orm_decl import (ShortStory, StoryTag, Edition,
                          Part, Contributor, StoryType, Contributor,
                          Genre, StoryGenre, Language)
from app.model_shortsearch import ShortSchemaForSearch
from app.model import ShortSchema, StoryTypeSchema
from app.impl_contributors import (updateShortContributors,
                                   contributorsHaveChanged, getContributorsString)

from app import app

def _setLanguage(session: Any, item: Any, data: Any, old_values:  Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    if data['lang'] != item.language:
        lang_id = None
        if old_values is not None:
            if item.lang != None:
                old_values['Kieli'] = item.lang.name
            else:
                old_values['Kieli'] = None
        if not 'id' in data['lang']:
            # User added a new language. Front returns this as a string
            # in the language field so we need to add this language to
            # the database first.
            lang_id = AddLanguage(bleach.clean(data['lang']))
        else:
            lang_id = checkInt(data['lang']['id'])
            if lang_id != None:
                lang = session.query(Language)\
                    .filter(Language.id == lang_id)\
                    .first()
                if not lang:
                    app.logger.error('SetLanguage: Language not found. Id = ' + str(data['language']['id']) + '.')
                    return ResponseType('Kieltä ei löydy', 400)
        item.language = lang_id
    return None

def checkStoryType(session: Any, story_type: Any) -> bool:
    st = checkInt(story_type)
    if st == None:
        return False
    t = session.query(StoryType).filter(StoryType.id == st).first()
    if not t:
        return False
    return True


def GetShortTypes() -> ResponseType:
    session = new_session()

    try:
        types = session.query(StoryType).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetShortTypes: ' + str(exp))
        return ResponseType(f'GetShortTypes: Tietokantavirhe. id={id}', 400)

    try:
        schema = StoryTypeSchema(many=True)
        retval = schema.dump(types)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetShortTypes schema error: ' + str(exp))
        return ResponseType('GetShortTypes: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def GetShort(id: int) -> ResponseType:
    session = new_session()

    try:
        short = session.query(ShortStory).filter(
            ShortStory.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetShort: ' + str(exp))
        return ResponseType(f'GetShort: Tietokantavirhe. id={id}', 400)

    try:
        schema = ShortSchema()
        retval = schema.dump(short)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetStory schema error: ' + str(exp))
        return ResponseType('GetStory: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def SearchShorts(params: Dict[str, str]) -> ResponseType:
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
                test_value = int(pubyear_first)
                stmt += 'AND shortstory.pubyear >= ' + pubyear_first + ' '
            except (TypeError) as exp:
                app.logger.error('Failed to convert pubyear_first')
        if 'pubyear_last' in params and params['pubyear_last'] != '':
            pubyear_last = bleach.clean(params['pubyear_last'])
            try:
                test_value = int(pubyear_last)
                stmt += 'AND shortstory.pubyear <= ' + pubyear_last + ' '
            except (TypeError) as exp:
                app.logger.error('Failed to convert pubyear_first')

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


def StoryAdd(data: Any) -> ResponseType:
    session = new_session()
    retval = ResponseType('OK', 201)

    changes = data['changed']

    for key, value in changes.items():
        if type(value) is list:
            for item in value:
                for key2, value2 in item.items():
                    if value2 == True:
                        print(f'Key: {key}/{key2}')
        elif value == True:
            print(f'Key: {key}')

    return retval


def StoryUpdate(params: Any) -> ResponseType:
    session = new_session()
    old_values = {}
    story: Any = None
    retval = ResponseType('OK', 200)
    data = params['data']
    short_id = checkInt(data['id'])

    short_id = checkInt(data['id'], False, False)
    if short_id == None:
        app.logger.error(f'StoryUpdate: Invalid id: {data["id"]}.')
        return ResponseType(f'StoryUpdate: virheellinen id {data["id"]}.', 400)

    story = session.query(ShortStory).filter(
        ShortStory.id == short_id).first()
    if not story:
        app.logger.error(f'StoryUpdate: Story not found. Id = {short_id}.')
        return ResponseType(f'StoryUpdate: Novellia ei löydy. id={short_id}.', 400)

    # Save title
    if 'title' in data:
        if data['title'] == None or len(data['title']) == 0:
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
            pubyear = checkInt(data['pubyear'])
            old_values['Julkaistu'] = story.pubyear
            story.pubyear = pubyear

    # Save story type
    if 'type' in data:
        if data['type']['id'] != story.type.id:
            if checkStoryType(session, data['type']['id']) == False:
                app.logger.error(
                    f'StoryUpdate exception. Not a type: {data["type"]}.')
                return ResponseType(
                    f'StoryUpdate: virheellinen tyyppi {data["type"]}.', 400)
            old_values['Tyyppi'] = story.type.name
            story.story_type = data["type"]['id']

    # Save original language
    if 'lang' in data:
        result =  _setLanguage(session, story, data, old_values)
        if result:
            return result

    try:
        session.add(story)
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in StoryUpdate: {exp}.')
        return ResponseType(f'StoryUpdate: Tietokantavirhe.', 400)

    # Save contributors
    if 'contributors' in data:
        if contributorsHaveChanged(story.contributors, data['contributors']):
            updateShortContributors(
                session, story.id, data['contributors'])
            old_values['Tekijät'] = getContributorsString(story.contributors)

    # Save genres
    if 'genres' in data:
        existing_genres = session.query(StoryGenre)\
            .filter(StoryGenre.shortstory_id == story.id) \
            .all()
        (to_add, to_remove) = GetJoinChanges(
            [x.genre_id for x in existing_genres],
            [x['id'] for x in data['genres']])
        for id in to_remove:
            dg = session.query(StoryGenre)\
                .filter(StoryGenre.genre_id == id)\
                .filter(StoryGenre.shortstory_id == story.id)\
                .first()
            session.delete(dg)
        for id in to_add:
            sg = StoryGenre(genre_id=id, shortstory_id=story.id)
            session.add(sg)
        if len(to_add) > 0 or len(to_remove) > 0:
            old_values['Genret'] = ' -'.join([str(x) for x in to_add])
            old_values['Genret'] += ' +'.join([str(x) for x in to_remove])

    # Save tags
    if 'tags' in data:
        existing_tags = session.query(StoryTag)\
            .filter(StoryTag.shortstory_id == story.id)\
            .all()
        (to_add, to_remove) = GetJoinChanges(
            [x.tag_id for x in existing_tags],
            [x['id'] for x in data['tags']])
        for id in to_remove:
            dt = session.query(StoryTag)\
                .filter(StoryTag.tag_id == id)\
                .filter(StoryTag.shortstory_id == story.id)\
                .first()
            session.delete(dt)
        for id in to_add:
            st = StoryTag(tag_id=id, shortstory_id=story.id)
            session.add(st)
        if len(to_add) > 0 or len(to_remove) > 0:
            old_values['Asiasanat'] = ' -'.join([str(x) for x in to_add])
            old_values['Asiasanat'] += ' +'.join([str(x) for x in to_remove])

    if len(old_values) == 0:
        return ResponseType('OK', 200)

    LogChanges(session=session, obj=story, name_field="title", action="Päivitys",
               old_values=old_values)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in StoryUpdate commit: {exp}.')
        return ResponseType(f'StoryUpdate: Tietokantavirhe tallennettaessa.', 400)

    return retval


def StoryDelete(id: int) -> ResponseType:
    session = new_session()
    retval = ResponseType('OK', 200)

    return retval


def StoryTagAdd(short_id: int, tag_id: int) -> ResponseType:
    session = new_session()

    try:
        short = session.query(ShortStory).filter(
            ShortStory.id == short_id).first()
        if not short:
            app.logger.error(
                f'StoryTagAdd: Short not found. Id = {short_id}.')
            return ResponseType('Novellia ei löydy', 400)

        shortTag = StoryTag()
        shortTag.shortstory_id = short_id
        shortTag.tag_id = tag_id
        session.add(shortTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagAdd(): ' + str(exp))
        return ResponseType(f'ShortTagAdd: Tietokantavirhe. short_id={short_id}, tag_id={tag_id}.', 400)

    return ResponseType('Asiasana lisätty novellille', 200)


def StoryTagRemove(short_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        shortTag = session.query(StoryTag)\
            .filter(StoryTag.shortstory_id == short_id, StoryTag.tag_id == tag_id)\
            .first()
        if not shortTag:
            app.logger.error(
                f'ShortTagRemove: Short has no such tag: short_id {short_id}, tag {tag_id}.'
            )
            return ResponseType(f'ShortTagRemove: Tagia ei löydy novellilta. short_id={short_id}, tag_id={tag_id}.', 400)
        session.delete(shortTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in ShortTagRemove(): ' + str(exp))
        return ResponseType(f'ShortTagRemove: Tietokantavirhe. short_id={short_id}, tag_id={tag_id}.', 400)

    return retval
