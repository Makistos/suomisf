import bleach
from app.route_helpers import new_session
from app.impl import (ResponseType, SearchScores, SearchResult,
                      SearchResultFields, searchScore)
from app.orm_decl import (Work, WorkType, WorkTag, WorkGenre, WorkTag)
from app.model import (CountryBriefSchema, WorkBriefSchema)
from app.model import WorkSchema
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import ResponseType, checkInt, LogChanges, GetJoinChanges
from app.impl_contributors import updateWorkContributors, contributorsHaveChanged
from app.impl_genres import genresHaveChanged
from app.impl_tags import tagsHaveChanged

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
        contributions: List[Any] = []
        # Remove duplicates
        for contributor in work.contributions:
            already_added = False
            for contribution in contributions:
                if (contribution.person_id == contributor.person_id and
                    contribution.role_id == contributor.role_id and
                    contribution.real_person_id == contributor.real_person_id and
                    contribution.description == contributor.description):
                    already_added = True
            if not already_added:
                contributions.append(contributor)
        work.contributions = contributions
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


def WorkAdd(params: Any) -> ResponseType:
    session = new_session()
    retval = ResponseType('', 200)

    changes = params['changed']

    return retval


def WorkUpdate(params: Any) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()
    old_values = {}
    work: Any = None
    data = params['data']
    changed = params['changed']
    work_id = checkInt(data['id'])

    work = session.query(Work).filter(Work.id == work_id).first()
    if not work:
        app.logger.error(f'WorkSave: Work not found. Id = {work_id}.')
        return ResponseType('Teosta ei löydy', 400)

    if 'title' in data:
        if data['title'] != work.title:
            if len(data['title']) == 0:
                app.logger.error(f'WorkSave: Empty title. Id = {work_id}.')
                return ResponseType('Tyhjä nimi', 400)
            old_values['title'] = work.title
            work.title = bleach.clean(data['title'])

    if 'subtitle' in data:
        if data['subtitle'] != work.subtitle:
            old_values['subtitle'] = work.subtitle
            work.subtitle = bleach.clean(data['subtitle'])

    if 'orig_title' in data:
        if data['orig_title'] != work.orig_title:
            old_values['orig_title'] = work.orig_title
            work.orig_title = bleach.clean(data['orig_title'])

    if 'pubyear' in data:
        if data['pubyear'] != work.pubyear:
            old_values['pubyear'] = work.pubyear
            work.pubyear = bleach.clean(data['pubyear'])

    if 'bookseries_number' in data:
        if data['bookseries_number'] != work.bookseriesnum:
            old_values['bookseriesnum'] = work.bookseriesnum
            work.bookseriesnum = bleach.clean(data['bookseriesnum'])

    if 'bookseriesorder' in data:
        if data['bookseriesorder'] != work.bookseriesorder:
            old_values['bookseriesorder'] = work.bookseriesorder
            work.bookseriesorder = bleach.clean(data['bookseriesorder'])

    if 'misc' in data:
        if data['misc'] != work.misc:
            old_values['misc'] = work.misc
            work.misc = bleach.clean(data['misc'])

    if 'description' in data:
        if data['description'] != work.description:
            old_values['description'] = work.description
            work.description = bleach.clean(data['description'])

    if 'descr_attrs' in data:
        if data['descr_attrs'] != work.descr_attr:
            old_values['descr_attr'] = work.descr_attr
            work.descr_attr = bleach.clean(data['descr_attrs'])

    if 'imported_string' in data:
        if data['imported_string'] != work.imported_string:
            old_values['imported_string'] = work.imported_string
            work.imported_string = bleach.clean(data['imported_string'])

    # Language
    if 'language' in data:
        if data['language'] != work.language:
            if data['language'] != None:
                language = checkInt(data['language']['id'])
            else:
                language = None
            old_values['language'] = work.language
            work.language = language

    # Bookseries
    if 'bookseries' in data:
        if data['bookseries'] != None:
            if data['bookseries']['id'] != work.bookseries['id']:
                if data['bookseries']['id'] != None:
                    bookseries_id = checkInt(data['bookseries_id'])
                else:
                    bookseries_id = None
                old_values['bookseries'] = work.bookseries['name']
                work.bookseries_id = bookseries_id

    # Worktype
    if 'type' in data:
        if data['type'] != work.type:
            old_values['type'] = work.type
            work.type = checkInt(data['type'])

    # Contributors
    if 'contributors' in data:
        if contributorsHaveChanged(work.contributions, data['contributors']):
            updateWorkContributors(session, work.id, data['contributors'])

    # Genres
    if 'genres' in data:
        if genresHaveChanged(work.genres, data['genres']):
            existing_genres = session.query(WorkGenre)\
                .filter(WorkGenre.work_id == work_id)\
                .all()
            (to_add, to_remove) = GetJoinChanges([x.genre_id for x in existing_genres],
                                                [x['id'] for x in data['genres']])
            for id in to_remove:
                dg = session.query(WorkGenre)\
                    .filter(WorkGenre.work_id == id)\
                    .filter(WorkGenre.genre_id == id)\
                    .first()
                session.delete(dg)
            for id in to_add:
                sg = WorkGenre(genre_id=id, work_id=work.id)
                session.add(sg)
            old_values['genres'] = ' -'.join([str(x) for x in to_add])
            old_values['genres'] += ' +'.join([str(x) for x in to_remove])

    # Tags
    if 'tags' in data:
        if tagsHaveChanged(work.tags, data['tags']):
            existing_tags = session.query(WorkTag)\
                .filter(WorkTag.work_id == work_id)\
                .all()
            (to_add, to_remove) = GetJoinChanges([x.tag_id for x in existing_tags],
                                                [x['id'] for x in data['tags']])
            for id in to_remove:
                dt = session.query(WorkTag)\
                    .filter(WorkTag.work_id == id)\
                    .filter(WorkTag.tag_id == id)\
                    .first()
                session.delete(dt)
            for id in to_add:
                st = WorkTag(tag_id=id, work_id=work.id)
                session.add(st)
            old_values['tags'] = ' -'.join([str(x) for x in to_add])
            old_values['tags'] += ' +'.join([str(x) for x in to_remove])

    # Links

    # Awards

    if len(old_values) == 0:
        # Nothing has changed.
        return retval

    LogChanges(session=session, obj=work, action='Päivitys',
               old_values=old_values, fields=changed)

    try:
        session.add(work)
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkSave(): ' + str(exp))
        return ResponseType(f'WorkSave: Tietokantavirhe. id={work.id}', 400)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in WorkSave() commit: ' + str(exp))
        return ResponseType(f'WorkSave: Tietokantavirhe. id={work.id}', 400)
    return retval
