import bleach
from app.route_helpers import new_session
from app.impl import (ResponseType, SearchScores, SearchResult,
                      SearchResultFields, searchScore, AddLanguage)
from app.orm_decl import (Contributor, Edition, Part, Work, WorkType, WorkTag,
                          WorkGenre, WorkLink, WorkTag, Person, Language, Bookseries)
from app.model import (CountryBriefSchema, WorkBriefSchema, WorkTypeBriefSchema)
from app.model import WorkSchema
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl import ResponseType, checkInt, LogChanges, GetJoinChanges
from app.impl_contributors import (updateWorkContributors, contributorsHaveChanged,
                                   getContributorsString, hasContributionRole)
from app.impl_genres import genresHaveChanged
from app.impl_tags import tagsHaveChanged
from app.impl_links import linksHaveChanged
from app.impl_editions import EditionCreateFirst
from app.impl_genres import checkGenreField
from app.impl_editions import deleteEdition
from app.impl_bookseries import AddBookseries
import html

from typing import Dict, List, Any, Union
from app import app

def _setBookseries(session: Any, work: Work, data: Any, old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    if data['bookseries'] != work.bookseries:
        bs_id = None
        if old_values:
            if work.bookseries:
                old_values['bookseries'] = work.bookseries.name
            else:
                old_values['bookseries'] = ''
        if not 'id' in data['bookseries']:
            # User added a new bookseries. Front returns this as a string
            # in the bookseries field so we need to add this bookseries to
            # the database first.
            bs_id = AddBookseries(bleach.clean(data['bookseries']))
        else:
            bs_id = checkInt(data['bookseries']['id'], zerosAllowed=False, negativeValuesAllowed=False)
            if bs_id != None:
                bs = session.query(Bookseries)\
                    .filter(Bookseries.id == bs_id)\
                    .first()
                if not bs:
                    app.logger.error('WorkSave: Bookseries not found. Id = ' + str(data['bookseries']['id']) + '.')
                    return ResponseType('Kirjasarjaa ei löydy', 400)
        work.bookseries_id = bs_id
    return None


def _setDescription(work: Work, data: Any, old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    try:
        html_text = html.unescape(data['description'])
    except (TypeError) as exp:
        app.logger.error('WorkSave: Failed to unescape html: ' + data["description"] + '.')
        return ResponseType('Kuvauksen html-muotoilu epäonnistui', 400)
    if html_text != work.description:
        if old_values:
            if work.description:
                old_values['description'] = work.description[0:200]
            else:
                old_values['description'] = ''
        work.description = html_text
    return None


def _setLanguage(session: Any, work: Any, data: Any, old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    if data['language'] != work.language:
        lang_id = None
        if old_values:
            if work.language_name:
                old_values['language'] = work.language_name.name
            else:
                old_values['language'] = None
        if not 'id' in data['language']:
            # User added a new language. Front returns this as a string
            # in the language field so we need to add this language to
            # the database first.
            lang_id = AddLanguage(bleach.clean(data['language']))
        else:
            lang_id = checkInt(data['language']['id'])
            if lang_id != None:
                lang = session.query(Language)\
                    .filter(Language.id == lang_id)\
                    .first()
                if not lang:
                    app.logger.error('WorkSave: Language not found. Id = ' + str(data['language']['id']) + '.')
                    return ResponseType('Kieltä ei löydy', 400)
        work.language = lang_id
    return None


def _setWorkType(work: Any, data: Any, old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    if data['work_type'] is not None:
        if 'id' in data['work_type']:
            work_type_id = checkInt(data['work_type']['id'],
                                zerosAllowed=False,
                                negativeValuesAllowed=False)

            if work_type_id == None:
                app.logger.error('WorkSave: Invalid work_type id.')
                return ResponseType('WorkSave: Virheellinen teostyyppi.', 400)
            if old_values:
                if work.work_type.id != work_type_id:
                    if work.work_type:
                        old_values['work_type'] = work.work_type.name
                    else:
                        old_values['work_type'] = ''
            work.work_type_id = work_type_id
    return None


def createAuthorStr(authors: List[Any], editions: List[Any]) -> str:
    retval = ''
    if len(authors)>0:
        retval = ' & '.join([author.name for author in authors])
    else:
        retval = ' & '.join([x.name for x in editions[0].editors]) + ' (toim.)'
    return retval


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


# def WorkTypesList() -> ResponseType:
#     session = new_session()

#     try:
#         types = session.query(WorkType).order_by(WorkType.id)
#     except SQLAlchemyError as exp:
#         app.logger.error('Exception in WorkTypesList: ' + str(exp))
#         return ResponseType(f'WorkTypesList: Tietokantavirhe. id={id}', 400)

#     try:
#         schema = CountryBriefSchema(many=True)
#         retval = schema.dump(types)
#     except exceptions.MarshmallowError as exp:
#         app.logger.error('WorkTypesList schema error: ' + str(exp))
#         return ResponseType('WorkTypesList: Skeemavirhe.', 400)

#     return ResponseType(retval, 200)


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

    data = params['data']

    work = Work()

    if len(data['title']) == 0:
        app.logger.error('WorkAdd: Empty title.')
        return ResponseType('Tyhjä nimi', 400)

    if not 'contributions' in data:
        app.logger.error('WorkAdd: No contributions.')
        return ResponseType('Ei kirjoittajaa tai toimittajaa', 400)

    if not (hasContributionRole(data['contributions'], 1) or
            hasContributionRole(data['contributions'], 3)):
        app.logger.error('WorkAdd: No author or editor.')
        return ResponseType('Ei kirjoittajaa tai toimittajaa', 400)

    work.title = bleach.clean(data['title'])
    work.subtitle = bleach.clean(data['subtitle'])
    work.orig_title = bleach.clean(data['orig_title'])

    work.pubyear = checkInt(data['pubyear'])

    work.bookseriesnum = bleach.clean(data['bookseriesnum'])
    if 'bookseries' in data:
        result = _setBookseries(session, work, data, None)
        if result:
            return result
        # if data['bookseries'] is not None:
        #     if 'id' in data['bookseries']:
        #         work.bookseries_id = checkInt(data['bookseries']['id'],
        #                                     zerosAllowed=False,
        #                                     negativeValuesAllowed=False)
    work.bookseriesorder = checkInt(data['bookseriesorder'])

    if 'language' in data:
        result = _setLanguage(session, work, data, None)
        if result:
            return result
    # Work type is required and defaults to 1 (book)
    work.type =  1
    if 'work_type' in data:
        result = _setWorkType(work, data, None)
        # if data['work_type'] is not None:
        #     if 'id' in data['work_type']:
        #         work_type = checkInt(data['work_type']['id'],
        #                             zerosAllowed=False,
        #                             negativeValuesAllowed=False)

    if 'description' in data:
        result = _setDescription(work, data, None)
        if result:
            return result
        #work.description = html.unescape(bleach.clean(data['description']))
    if 'descr_attr' in data:
        work.descr_attr = bleach.clean(data['descr_attr'])
    if 'misc' in data:
        work.misc = bleach.clean(data['misc'])
    if 'imported_string' in data:
        work.imported_string = bleach.clean(data['imported_string'])

    try:
        session.add(work)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe teoksessa. work_id={work.id}', 400)

    # Add first edition (requires work id)
    new_edition = EditionCreateFirst(work)
    try:
        session.add(new_edition)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe painoksessa. work_id={work.id}', 400)

    # Add part to tie work and edition together (requires work id and edition id)
    new_part = Part(work_id=work.id, edition_id=new_edition.id)
    try:
        session.add(new_part)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe Part-taulussa. work_id={work.id}', 400)

    # Add contributors (requires part id)
    updateWorkContributors(session, work.id, data['contributions'])

    # Add tags (requires work id)
    if 'tags' in data:
        for tag in data['tags']:
            if 'id' in tag:
                if tag['id'] != 0 and tag['id'] != None:
                    new_tag = WorkTag(work_id=work.id, tag_id=tag['id'])
                    session.add(new_tag)

    # Add links (requires work id)
    if 'links' in data:
        for link in data['links']:
            if not 'link' in link:
                app.logger.error('WorkAdd: Link missing link.')
                return ResponseType('Linkin tiedot puutteelliset', 400)
            if link['link'] != '' and link['link'] != None:
                # Description is not a required field
                if 'description' in link:
                    description = link['description']
                else:
                    description = None
                if 'link' in link:
                    new_link = WorkLink(work_id=work.id, link=link['link'],
                                        description=description)
                    session.add(new_link)

    # Add genres (requires work id)
    if 'genres' in data:
        for genre in data['genres']:
            isOk = checkGenreField(session, genre)
            if not isOk:
                app.logger.error('WorkAdd: Genre missing id.')
                return ResponseType('Genren tiedot puutteelliset', 400)
            new_genre = WorkGenre(work_id=work.id, genre_id=genre['id'])
            session.add(new_genre)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe asiasanoissa, linkeissä tai genreissä. work_id={work.id}',
                            400)

    # Update author string
    try:
        author_str = work.update_author_str()
        work.author_str = author_str
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe tekijänimissä. work_id={work.id}', 400)

    LogChanges(session, obj=work, action='Uusi')
    return ResponseType(str(work.id), 201)

# Save changes to work to database
def WorkUpdate(params: Any) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()
    old_values = {}
    work: Any = None
    data = params['data']
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
            work.pubyear = checkInt(data['pubyear'])

    if 'bookseriesnum' in data:
        if data['bookseriesnum'] != work.bookseriesnum:
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
        result = _setDescription(work, data, old_values)
        if result:
            return result

    if 'descr_attr' in data:
        if data['descr_attr'] != work.descr_attr:
            old_values['descr_attr'] = work.descr_attr
            work.descr_attr = bleach.clean(data['descr_attrs'])

    if 'imported_string' in data:
        if data['imported_string'] != work.imported_string:
            old_values['imported_string'] = work.imported_string
            work.imported_string = bleach.clean(data['imported_string'])

    # Language
    if 'language' in data:
        result = _setLanguage(session, work, data, old_values)
        if result:
            return result
        # if data['language'] != work.language:
        #     lang_id = None
        #     if work.language_name:
        #         old_values['language'] = work.language_name.name
        #     else:
        #         old_values['language'] = None
        #     if not 'id' in data['language']:
        #         # User added a new language. Front returns this as a string
        #         # in the language field so we need to add this language to
        #         # the database first.
        #         lang_id = AddLanguage(bleach.clean(data['language']))
        #     else:
        #         lang_id = checkInt(data['language']['id'])
        #         if lang_id != None:
        #             lang = session.query(Language)\
        #                 .filter(Language.id == lang_id)\
        #                 .first()
        #             if not lang:
        #                 app.logger.error('WorkSave: Language not found. Id = ' + str(data['language']['id']) + '.')
        #                 return ResponseType('Kieltä ei löydy', 400)
        #     work.language = lang_id

    # Bookseries
    if 'bookseries' in data:
        result = _setBookseries(session, work, data, old_values)
        if result:
            return result
        # if data['bookseries'] != work.bookseries:
        #     bs_id = None
        #     if work.bookseries:
        #         old_values['bookseries'] = work.bookseries.name
        #     else:
        #         old_values['bookseries'] = ''
        #     if not 'id' in data['bookseries']:
        #         # User added a new bookseries. Front returns this as a string
        #         # in the bookseries field so we need to add this bookseries to
        #         # the database first.
        #         bs_id = AddBookseries(bleach.clean(data['bookseries']))
        #     else:
        #         bs_id = checkInt(data['bookseries']['id'])
        #         if bs_id != None:
        #             bs = session.query(Bookseries)\
        #                 .filter(Bookseries.id == bs_id)\
        #                 .first()
        #             if not bs:
        #                 app.logger.error('WorkSave: Bookseries not found. Id = ' + str(data['bookseries']['id']) + '.')
        #                 return ResponseType('Kirjasarjaa ei löydy', 400)
        #     work.bookseries_id = bs_id

    # Worktype
    if 'work_type' in data:
        result = _setWorkType(work, data, old_values)
        if result:
            return result

    # Contributors
    if 'contributions' in data:
        if contributorsHaveChanged(work.contributions, data['contributions']):
            old_values['contributions'] = getContributorsString(work.contributions)
            updateWorkContributors(session, work.id, data['contributions'])

    # Genres
    if 'genres' in data:
        if genresHaveChanged(work.genres, data['genres']):
            existing_genres = session.query(WorkGenre)\
                .filter(WorkGenre.work_id == work_id)\
                .all()
            (to_add, to_remove) = GetJoinChanges([x.genre_id for x in existing_genres],
                                                [x['id'] for x in data['genres']])
            if len(existing_genres) > 0:
                for genre in existing_genres:
                    session.delete(genre)
            # for id in to_remove:
            #     dg = session.query(WorkGenre)\
            #         .filter(WorkGenre.work_id == id)\
            #         .filter(WorkGenre.genre_id == id)\
            #         .first()
            #     session.delete(dg)
            # for id in to_add:
            for genre in data['genres']:
                sg = WorkGenre(genre_id=genre['id'], work_id=work.id)
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
            if len(existing_tags) > 0:
                for tag in existing_tags:
                    session.delete(tag)
            for tag in data['tags']:
                st = WorkTag(tag_id=tag['id'], work_id=work.id)
                session.add(st)

            # for id in to_remove:
            #     dt = session.query(WorkTag)\
            #         .filter(WorkTag.work_id == id)\
            #         .filter(WorkTag.tag_id == id)\
            #         .first()
            #     session.delete(dt)
            # for id in to_add:
            #     st = WorkTag(tag_id=id, work_id=work.id)
            #     session.add(st)
            old_values['tags'] = ' -'.join([str(x) for x in to_add])
            old_values['tags'] += ' +'.join([str(x) for x in to_remove])

    # Links
    if 'links' in data:
        new_links = [x for x in data['links'] if x['link'] != '']
        if linksHaveChanged(work.links, new_links):
            existing_links = session.query(WorkLink)\
                .filter(WorkLink.work_id == work_id)\
                .all()
            (to_add, to_remove) = GetJoinChanges([x.link for x in existing_links],
                                                    [x['link'] for x in data['links']])
            if len(existing_links) > 0:
                for link in existing_links:
                    session.delete(link)
            for link in new_links:
                if 'link' not in link:
                    app.logger.error('WorkSave: Link missing address.')
                    return ResponseType('Linkin tiedot puutteelliset', 400)
                sl = WorkLink(work_id=work.id, link=link['link'],
                              description=link['description'])
                session.add(sl)
            old_values['links'] = ' -'.join([str(x) for x in to_add])
            old_values['links'] += ' +'.join([str(x) for x in to_remove])

    # Awards

    if len(old_values) == 0:
        # Nothing has changed.
        return retval

    LogChanges(session=session, obj=work, action='Päivitys',
               old_values=old_values)

    try:
        session.add(work)
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in WorkSave(): ' + str(exp))
        return ResponseType(f'WorkSave: Tietokantavirhe. id={work.id}', 400)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in WorkSave() commit: ' + str(exp))
        return ResponseType(f'WorkSave: Tietokantavirhe. id={work.id}', 400)

    work.update_author_str()

    return retval


def WorkTypeGetAll() -> ResponseType:
    session = new_session()

    try:
        worktypes = session.query(WorkType).order_by(WorkType.id).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkTypeGetAll(): ' + str(exp))
        return ResponseType('WorkTypeGetAll: Tietokantavirhe', 400)

    try:
        schema = WorkTypeBriefSchema(many=True)
        retval = schema.dump(worktypes)
    except exceptions.MarshmallowError as exp:
        app.logger.error('Exception in WorkTypeGetAll(): ' + str(exp))
        return ResponseType('WorkTypeGetAll: Serialisointivirhe', 400)

    return ResponseType(retval, 200)

def WorkDelete(id: int) -> ResponseType:
    session = new_session()
    old_values = {}

    try:
        work = session.query(Work).filter(Work.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkDelete(): ' + str(exp))
        return ResponseType('WorkDelete: Tietokantavirhe', 400)

    if work == None:
        app.logger.error('Exception in WorkDelete(): Work not found.')
        return ResponseType('WorkDelete: Teosta ei löydy', 404)

    # Delete everything related to the work
    try:
        editions = session.query(Edition)\
        .join(Part)\
        .filter(Part.work_id == id)\
        .filter(Part.edition_id == Edition.id)\
        .all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkDelete() deleting editions: ' + str(exp))
        return ResponseType('WorkDelete: Tietokantavirhe', 400)
    for edition in editions:
        success = deleteEdition(session, edition.id)
        if not success:
            session.rollback()
            return ResponseType('WorkDelete: Tietokantavirhe', 400)

    try:
        old_values['name'] = work.title
        LogChanges(session, obj=work, action='Poisto', old_values=old_values)
        session.query(WorkGenre).filter(WorkGenre.work_id == id).delete()
        session.query(WorkTag).filter(WorkTag.work_id == id).delete()
        session.query(WorkLink).filter(WorkLink.work_id == id).delete()
        session.query(Work).filter(Work.id == id).delete()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in WorkDelete() deleting work: ' + str(exp))
        return ResponseType('WorkDelete: Tietokantavirhe', 400)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in WorkDelete() commit: ' + str(exp))
        return ResponseType('WorkDelete: Tietokantavirhe', 400)

    return ResponseType('WorkDelete: Teos poistettu', 200)