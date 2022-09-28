import bleach
import json
from typing import Dict, Tuple
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (ShortStory, StoryTag)
from app.model import (ShortSchema)

from app import app


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
        schema = ShortSchema(many=True)
        retval = schema.dump(shorts)
    except exceptions.MarshmallowError as exp:
        app.logger.error('SearchShorts schema error: ' + str(exp))
        return ResponseType('SearchShorts: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


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
