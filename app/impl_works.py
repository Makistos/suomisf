import bleach
from app.route_helpers import new_session
from app.impl import (ResponseType, SearchScores, SearchResult,
                      SearchResultFields, searchScore)
from app.orm_decl import (Work, WorkType, WorkTag)
from app.model import (CountryBriefSchema, WorkBriefSchema)
from app.model import WorkSchema
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from typing import Dict, List, Any
from app import app


def GetWork(id: int) -> ResponseType:
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetWork: ' + str(exp))
        return ResponseType(f'GetWork: Tietokantavirhe. id={id}', 400)

    if not work:
        app.logger.error(f'GetWork: Work not found {id}.')
        return ResponseType('Teosta ei löytynyt. id={id}.', 400)
    try:
        schema = WorkSchema()
        retval = schema.dump(work)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetWork schema error: ' + str(exp))
        return ResponseType('GetWork: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def GetWorksByAuthor(author: int) -> ResponseType:
    session = new_session()

    return ResponseType('', 200)


def SearchWorks(session: Any, searchwords: List[str]) -> SearchResult:
    retval: SearchResult = []
    found_works: Dict[int, SearchResultFields] = {}

    for searchword in searchwords:
        works = session.query(Work)\
            .filter(Work.title.ilike('%' + searchword + '%') |
                    Work.subtitle.ilike('%' + searchword + '%') |
                    Work.orig_title.ilike('%' + searchword + '%') |
                    Work.misc.ilike('%' + searchword + '%') |
                    Work.description.ilike('%' + searchword + '%'))\
            .order_by(Work.title)\
            .all()

        for work in works:
            if work.id in found_works:
                found_works[work.id]['score'] *= searchScore(
                    'work', work, searchword)
            else:
                if work.description:
                    description = work.description
                else:
                    description = ''

                item: SearchResultFields = {
                    'id': work.id,
                    'img': '',
                    'header': work.title,
                    'description': description,
                    'type': 'work',
                    'score': searchScore('work', work, searchword)
                }
                found_works[work.id] = item
        retval = [value for _, value in found_works.items()]

    return retval


def SearchBooks(params: Dict[str, str]) -> ResponseType:
    session = new_session()
    joins: List[str] = []

    stmt = 'SELECT DISTINCT work.* FROM work '
    if 'author' in params and params['author'] != '':
        author = bleach.clean(params['author'])
        stmt += 'INNER JOIN part on part.work_id = work.id AND part.shortstory_id is null '
        stmt += 'INNER JOIN contributor on contributor.part_id = part.id AND contributor.role_id = 1 '
        stmt += 'INNER JOIN person on person.id = contributor.person_id '
        stmt += 'AND (lower(person.name) like lower("' + author + \
            '%") OR lower(person.alt_name) like lower("' + author + '%")) '
        joins.append('part')
        joins.append('contributor')
        joins.append('person')
    if 'printyear_first' in params and params['printyear_first'] != '':
        if 'printyear_first' in params and params['printyear_first'] != '':
            printyear_first = bleach.clean(params['printyear_first'])
            try:
                test_value = int(printyear_first)
                if not 'part' in joins:
                    stmt += 'INNER JOIN part on part.work_id = work.id '
                    joins.append('part')
                if not 'edition' in joins:
                    stmt += 'INNER JOIN edition on edition.id = part.edition_id '
                    joins.append('edition')
                stmt += 'AND edition.pubyear >= ' + printyear_first + ' '
            except (TypeError) as exp:
                app.logger.error('Failed to convert printyear_first')
    if 'printyear_last' in params and params['printyear_last'] != '':
        if 'printyear_last' in params and params['printyear_last'] != '':
            printyear_last = bleach.clean(params['printyear_last'])
            try:
                test_value = int(printyear_last)
                if not 'part' in joins:
                    stmt += 'INNER JOIN part on part.work_id = work.id '
                    joins.append('part')
                if not 'edition' in joins:
                    stmt += 'INNER JOIN edition on edition.id = part.edition_id '
                    joins.append('edition')
                stmt += 'AND edition.pubyear <= ' + printyear_last + ' '
            except (TypeError) as exp:
                app.logger.error('Failed to convert printyear_last')
    if 'genre' in params and params['genre'] != '':
        stmt += 'INNER JOIN workgenre on workgenre.work_id = work.id '
        stmt += 'AND workgenre.genre_id = "' + str(params['genre']) + '" '
    if 'nationality' in params and params['nationality'] != '':
        if not 'part' in joins:
            stmt += 'INNER JOIN part on part.work_id = work.id AND part.shortstory_id is null '
            joins.append('part')
        if not 'contributor' in joins:
            stmt += 'INNER JOIN contributor on contributor.part_id = part.id AND contributor.role_id = 1 '
            joins.append('contributor')
        if not 'person' in joins:
            stmt += 'INNER JOIN person on person.id = contributor.person_id '
            joins.append('person')
        stmt += 'AND person.nationality_id = "' + \
            str(params['nationality']) + '" '
    if ('title' in params or 'orig_name' in params
        or 'pubyear_first' in params or 'pubyear_last' in params
            or 'genre' in params or 'nationality' in params or 'type' in params):
        stmt += 'WHERE 1=1 '
        if 'title' in params and params['title'] != '':
            title = bleach.clean(params['title'])
            stmt += 'AND (lower(work.title) like lower("' + title + '%") \
                OR lower(work.title) like lower("% ' + title + '%")) '
        if 'orig_name' in params and params['orig_name'] != '':
            orig_name = bleach.clean(params['orig_name'])
            stmt += 'AND (lower(work.orig_title) like lower("' + orig_name + '%") \
                OR lower(work.orig_title) like lower("% ' + orig_name + '%")) '
        if 'pubyear_first' in params and params['pubyear_first'] != '':
            pubyear_first = bleach.clean(params['pubyear_first'])
            try:
                # Test that value is actually an integer, we still need to use
                # the string version in the query.
                test_value = int(pubyear_first)
                stmt += 'AND work.pubyear >= ' + pubyear_first + ' '
            except (TypeError) as exp:
                app.logger.error('Failed to convert pubyear_first')
        if 'pubyear_last' in params and params['pubyear_last'] != '':
            pubyear_last = bleach.clean(params['pubyear_last'])
            try:
                test_value = int(pubyear_last)
                stmt += 'AND work.pubyear <= ' + pubyear_last + ' '
            except (TypeError) as exp:
                app.logger.error('Failed to convert pubyear_first')
        if 'type' in params and params['type'] != '':
            stmt += 'AND work.type = "' + str(params['type']) + '" '
    stmt += ' ORDER BY work.author_str, work.title'

    # app.logger.warn(stmt)
    try:
        works = session.query(Work)\
            .from_statement(text(stmt))\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in SearchBooks: ' + str(exp))
        return ResponseType(f'SearchBooks: Tietokantavirhe. id={id}', 400)

    try:
        schema = WorkBriefSchema(many=True)
        retval = schema.dump(works)
    except exceptions.MarshmallowError as exp:
        app.logger.error('SearchBooks schema error: ' + str(exp))
        return ResponseType('SearchBooks: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def SearchWorksByAuthor(params: Dict[str, str]) -> ResponseType:
    session = new_session()

    try:
        works = session.query(Work)\
            .filter(Work.author_str.ilike(params['letter'] + '%'))\
            .order_by(Work.author_str)
    except SQLAlchemyError as exp:
        app.logger.error('Exception in SearchWorksByAuthor: ' + str(exp))
        return ResponseType(f'SearchWorksByAuthor: Tietokantavirhe. id={id}', 400)

    try:
        schema = WorkBriefSchema(many=True)
        retval = schema.dump(works)
    except exceptions.MarshmallowError as exp:
        app.logger.error('SearchWorksByAuthor schema error: ' + str(exp))
        return ResponseType('SearchWorksByAuthor: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def WorkTypesList() -> ResponseType:
    session = new_session()

    try:
        types = session.query(WorkType).order_by(WorkType.id)
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkTypesList: ' + str(exp))
        return ResponseType(f'WorkTypesList: Tietokantavirhe. id={id}', 400)

    try:
        schema = CountryBriefSchema(many=True)
        retval = schema.dump(types)
    except exceptions.MarshmallowError as exp:
        app.logger.error('WorkTypesList schema error: ' + str(exp))
        return ResponseType('WorkTypesList: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def WorkTagAdd(work_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        short = session.query(Work).filter(
            Work.id == work_id).first()
        if not short:
            app.logger.error(
                f'WorkTagAdd: Short not found. Id = {work_id}.')
            return ResponseType('Novellia ei löydy', 400)

        shortTag = WorkTag()
        shortTag.work_id = work_id
        shortTag.tag_id = tag_id
        session.add(shortTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in WorkTagAdd(): ' + str(exp))
        return ResponseType(f'WorkTagAdd: Tietokantavirhe. work_id={work_id}, tag_id={tag_id}.', 400)

    return retval


def WorkTagRemove(work_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        shortTag = session.query(WorkTag)\
            .filter(WorkTag.work_id == work_id, WorkTag.tag_id == tag_id)\
            .first()
        if not shortTag:
            app.logger.error(
                f'WorkTagRemove: Short has no such tag: work_id {work_id}, tag {tag_id}.'
            )
            return ResponseType(f'WorkTagRemove: Tagia ei löydy novellilta. work_id={work_id}, tag_id={tag_id}.', 400)
        session.delete(shortTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in WorkTagRemove(): ' + str(exp))
        return ResponseType(f'WorkTagRemove: Tietokantavirhe. work_id={work_id}, tag_id={tag_id}.', 400)

    return retval
