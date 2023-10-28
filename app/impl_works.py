""" Implementations for work related functions.
"""
import html
from typing import Dict, List, Any, Union
import bleach
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.impl import (ResponseType, SearchResult,
                      SearchResultFields, searchscore, set_language, check_int,
                      log_changes, get_join_changes)
from app.orm_decl import (Edition, Part, Work, WorkType, WorkTag,
                          WorkGenre, WorkLink, Bookseries, ShortStory)
from app.model import (WorkBriefSchema, WorkTypeBriefSchema, ShortBriefSchema)
from app.model_bookindex import (BookIndexSchema)
from app.model import WorkSchema
from app.impl_contributors import (update_work_contributors,
                                   contributors_have_changed,
                                   get_contributors_string,
                                   has_contribution_role)
from app.impl_genres import genresHaveChanged
from app.impl_tags import tags_have_changed
from app.impl_links import linksHaveChanged
from app.impl_editions import create_first_edition
from app.impl_genres import checkGenreField
from app.impl_editions import delete_edition
from app.impl_bookseries import add_bookseries

from app import app


def _set_bookseries(
        session: Any, work: Work, data: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Sets the book series for a given work.

    Args:
        session (Any): The session object for the database connection.
        work (Work): The work object to set the book series for.
        data (Any): The data object containing the book series information.
        old_values (Union[Dict[str, Any], None]): The old values of the work
        object.

    Returns:
        Union[ResponseType, None]: The response type if there is an error,
                                   otherwise None.
    """
    if data['bookseries'] != work.bookseries:
        bs_id = None
        if old_values is not None:
            old_values['Kirjasarja'] = (work.bookseries.name
                                        if work.bookseries else '')
        if 'id' not in data['bookseries']:
            # User added a new bookseries. Front returns this as a string
            # in the bookseries field so we need to add this bookseries to
            # the database first.
            bs_id = add_bookseries(bleach.clean(data['bookseries']))
        else:
            bs_id = check_int(data['bookseries']['id'], zeros_allowed=False,
                              negative_values=False)
            if bs_id is not None:
                bs = session.query(Bookseries)\
                    .filter(Bookseries.id == bs_id)\
                    .first()
                if not bs:
                    app.logger.error(f'''WorkSave: Bookseries not found. Id =
                                     {data["bookseries"]["id"]}.''')
                    return ResponseType('Kirjasarjaa ei löydy', 400)
        work.bookseries_id = bs_id
    return None


def _set_description(
        work: Work,
        data: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Set the description of a work.

    Args:
        work (Work): The work object to set the description for.
        data (Any): The data containing the new description.
        old_values (Union[Dict[str, Any], None]): The old values of the work,
        if available.

    Returns:
        Union[ResponseType, None]: The response type if there was an error,
                                   otherwise None.
    """
    try:
        html_text = html.unescape(data['description'])
    except (TypeError) as exp:
        app.logger.error('WorkSave: Failed to unescape html: ' +
                         data["description"] + '.' + str(exp))
        return ResponseType('Kuvauksen html-muotoilu epäonnistui', 400)
    if html_text != work.description:
        if old_values is not None:
            old_values['Kuvaus'] = (work.description[0:200]
                                    if work.description else '')
        work.description = html_text
    return None


def _set_work_type(
        work: Any,
        data: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Sets the work type for a given work.

    Args:
        work (Any): The work object to set the work type for.
        data (Any): The data containing the work type information.
        old_values (Union[Dict[str, Any], None]): The old values of the work
        type, if any.

    Returns:
        Union[ResponseType, None]: The response type if an error occurs,
                                   None otherwise.
    """
    if data['work_type'] is not None:
        if 'id' in data['work_type']:
            work_type_id = check_int(data['work_type']['id'],
                                     zeros_allowed=False,
                                     negative_values=False)

            if work_type_id is None:
                app.logger.error('WorkSave: Invalid work_type id.')
                return ResponseType('WorkSave: Virheellinen teostyyppi.', 400)
            if old_values is not None:
                if work.work_type.id != work_type_id:
                    if work.work_type:
                        old_values['Tyyppi'] = work.work_type.name
                    else:
                        old_values['Tyyppi'] = ''
            work.work_type_id = work_type_id
    return None


def create_author_str(authors: List[Any], editions: List[Any]) -> str:
    """
    Generate a string representing the list of authors or editors of a book.

    Args:
        authors (List[Any]): A list of author objects.
        editions (List[Any]): A list of edition objects.

    Returns:
        str: A string representing the list of authors or editors of a book.
    """
    retval = ''
    if len(authors) > 0:
        retval = ' & '.join([author.name for author in authors])
    else:
        retval = ' & '.join([x.name for x in editions[0].editors]) + ' (toim.)'
    return retval


def _similar_description(
        descr1: Union[str, None], descr2: Union[str, None]) -> bool:
    """
    Check if two descriptions are similar. Empty string and None values are
    considered same.

    Args:
        descr1 (Union[str, None]): The first description.
        descr2 (Union[str, None]): The second description.

    Returns:
        bool: True if the descriptions are similar, False otherwise.
    """
    if descr1 == '':
        descr1 = None
    if descr2 == '':
        descr2 = None

    return descr1 == descr2


def get_work(work_id: int) -> ResponseType:
    """
    Retrieves a specific work from the database based on the provided work ID.

    Args:
        work_id (int): The ID of the work to retrieve.

    Returns:
        ResponseType: The response object containing the retrieved work if
        successful, or an error message with a status code if unsuccessful.
    """
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetWork: ' + str(exp))
        return ResponseType(f'GetWork: Tietokantavirhe. id={work_id}', 400)

    if not work:
        app.logger.error(f'GetWork: Work not found {work_id}.')
        return ResponseType('Teosta ei löytynyt. id={id}.', 400)
    try:
        contributions: List[Any] = []
        # Remove duplicates
        for contributor in work.contributions:
            already_added = False
            for contribution in contributions:
                if (contribution.person_id == contributor.person_id and
                    contribution.role_id == contributor.role_id and
                    contribution.real_person_id == contributor.real_person_id
                    and _similar_description(contribution.description,
                                             contributor.description)):
                    already_added = True
            if not already_added:
                contributions.append(contributor)
        work.contributions = contributions
        contributions = []
        for short in work.stories:
            for contributor in short.contributors:
                already_added = False
                for contribution in contributions:
                    if (contribution.person_id == contributor.person_id and
                        contribution.role_id == contributor.role_id and
                        contribution.real_person_id ==
                        contributor.real_person_id and
                        _similar_description(contribution.description,
                                             contributor.description)):
                        already_added = True
                if not already_added:
                    contributions.append(contributor)
            short.contributors = contributions
            contributions = []
        schema = WorkSchema()
        retval = schema.dump(work)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetWork schema error: ' + str(exp))
        return ResponseType('GetWork: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


# def get_works_by_author(author: int) -> ResponseType:
#     session = new_session()

#     return ResponseType('', 200)


def search_works(session: Any, searchwords: List[str]) -> SearchResult:
    """
    Search for works based on the given search words.

    Args:
        session (Any): The session object to use for the database query.
        searchwords (List[str]): The list of search words to use for the
        search.

    Returns:
        SearchResult: A list of search results matching the search words.
    """
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
                found_works[work.id]['score'] *= searchscore(
                    'work', work, searchword)
            else:
                description = (work.description if work.description else '')

                item: SearchResultFields = {
                    'id': work.id,
                    'img': '',
                    'header': work.title,
                    'description': description,
                    'type': 'work',
                    'score': searchscore('work', work, searchword)
                }
                found_works[work.id] = item
        retval = [value for _, value in found_works.items()]

    return retval


def search_books(params: Dict[str, str]) -> ResponseType:
    """
    Searches for books based on the given parameters.

    Args:
        params (Dict[str, str]): A dictionary containing the search parameters.

    Returns:
        ResponseType: An object representing the response of the search.
    """
    session = new_session()
    joins: List[str] = []

    stmt = 'SELECT DISTINCT work.* FROM work '
    if 'author' in params and params['author'] != '':
        author = bleach.clean(params['author'])
        stmt += 'INNER JOIN part on part.work_id = work.id '
        stmt += 'AND part.shortstory_id is null '
        stmt += 'INNER JOIN contributor on contributor.part_id = part.id '
        stmt += 'AND contributor.role_id = 1 '
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
                # pylint: disable-next=unused-variable
                test_value = int(printyear_first)
                if 'part' not in joins:
                    stmt += 'INNER JOIN part on part.work_id = work.id '
                    joins.append('part')
                if 'edition' not in joins:
                    stmt += 'INNER JOIN edition on edition.id '
                    stmt += '= part.edition_id '
                    joins.append('edition')
                stmt += 'AND edition.pubyear >= ' + printyear_first + ' '
            except TypeError:
                app.logger.error('Failed to convert printyear_first')
    if 'printyear_last' in params and params['printyear_last'] != '':
        if 'printyear_last' in params and params['printyear_last'] != '':
            printyear_last = bleach.clean(params['printyear_last'])
            try:
                test_value = int(printyear_last)
                if 'part' not in joins:
                    stmt += 'INNER JOIN part on part.work_id = work.id '
                    joins.append('part')
                if 'edition' not in joins:
                    stmt += 'INNER JOIN edition on edition.id = '
                    stmt += 'part.edition_id '
                    joins.append('edition')
                stmt += 'AND edition.pubyear <= ' + printyear_last + ' '
            except (TypeError) as exp:
                app.logger.error(f'Failed to convert printyear_last: {exp}')
    if 'genre' in params and params['genre'] != '':
        stmt += 'INNER JOIN workgenre on workgenre.work_id = work.id '
        stmt += 'AND workgenre.genre_id = "' + str(params['genre']) + '" '
    if 'nationality' in params and params['nationality'] != '':
        if 'part' not in joins:
            stmt += 'INNER JOIN part on part.work_id = work.id AND '
            stmt += 'part.shortstory_id is null '
            joins.append('part')
        if 'contributor' not in joins:
            stmt += 'INNER JOIN contributor on contributor.part_id = part.id '
            stmt += 'AND contributor.role_id = 1 '
            joins.append('contributor')
        if 'person' not in joins:
            stmt += 'INNER JOIN person on person.id = contributor.person_id '
            joins.append('person')
        stmt += 'AND person.nationality_id = "' + \
            str(params['nationality']) + '" '
    if ('title' in params or 'orig_name' in params
        or 'pubyear_first' in params or 'pubyear_last' in params
            or 'genre' in params or 'nationality' in params
            or 'type' in params):
        stmt += 'WHERE 1=1 '
        if 'title' in params and params['title'] != '':
            title = bleach.clean(params['title'])
            stmt += 'AND (lower(work.title) like lower("' + title + '%") \
                OR lower(work.title) like lower("% ' + title + '%")) '
        if 'orig_name' in params and params['orig_name'] != '':
            orig_name = bleach.clean(params['orig_name'])
            stmt += 'AND (lower(work.orig_title) like lower("'
            stmt += orig_name + '%") \
                OR lower(work.orig_title) like lower("% ' + orig_name + '%")) '
        if 'pubyear_first' in params and params['pubyear_first'] != '':
            pubyear_first = bleach.clean(params['pubyear_first'])
            try:
                # Test that value is actually an integer, we still need to use
                # the string version in the query.
                test_value = int(pubyear_first)
                stmt += 'AND work.pubyear >= ' + pubyear_first + ' '
            except (TypeError) as exp:
                app.logger.error(f'Failed to convert pubyear_first: {exp}')
        if 'pubyear_last' in params and params['pubyear_last'] != '':
            pubyear_last = bleach.clean(params['pubyear_last'])
            try:
                test_value = int(pubyear_last)  # noqa: F841
                stmt += 'AND work.pubyear <= ' + pubyear_last + ' '
            except (TypeError) as exp:
                app.logger.error(f'Failed to convert pubyear_first: {exp}')
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


def search_works_by_author(params: Dict[str, str]) -> ResponseType:
    """
    Search for works by author.

    Args:
        params (Dict[str, str]): A dictionary of parameters for the search.

    Returns:
        ResponseType: The response type containing the search results.

    Raises:
        SQLAlchemyError: If there is an error in the SQLAlchemy query.
        exceptions.MarshmallowError: If there is an error in the Marshmallow
                                     schema.

    """
    session = new_session()

    try:
        works = session.query(Work)\
            .filter(Work.author_str.ilike(params['letter'] + '%'))\
            .order_by(Work.author_str).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in SearchWorksByAuthor: ' + str(exp))
        return ResponseType(f'SearchWorksByAuthor: Tietokantavirhe. id={id}',
                            400)

    try:
        # schema = WorkBriefSchema(many=True)
        schema = BookIndexSchema(many=True)
        retval = schema.dump(works)
    except exceptions.MarshmallowError as exp:
        app.logger.error('SearchWorksByAuthor schema error: ' + str(exp))
        return ResponseType('SearchWorksByAuthor: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def work_tag_add(work_id: int, tag_id: int) -> ResponseType:
    """
    Adds a tag to a work.

    Args:
        work_id (int): The ID of the work to add the tag to.
        tag_id (int): The ID of the tag to add to the work.

    Returns:
        ResponseType: The response indicating the success or failure of the
        operation.
    """
    session = new_session()

    try:
        work = session.query(Work).filter(
            Work.id == work_id).first()
        if not work:
            app.logger.error(
                f'WorkTagAdd: Short not found. Id = {work_id}.')
            return ResponseType('Novellia ei löydy', 400)

        work_tag = WorkTag()
        work_tag.work_id = work_id
        work_tag.tag_id = tag_id
        session.add(work_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in WorkTagAdd(): ' + str(exp))
        return ResponseType(f'''WorkTagAdd: Tietokantavirhe. work_id={work_id},
                            tag_id={tag_id}.''', 400)

    return ResponseType('', 200)


def work_tag_remove(work_id: int, tag_id: int) -> ResponseType:
    """
    Remove a tag from a work.

    Parameters:
        work_id (int): The ID of the work.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: An instance of the ResponseType class containing the
        result of the operation.
    """
    retval = ResponseType('', 200)
    session = new_session()

    try:
        work_tag = session.query(WorkTag)\
            .filter(WorkTag.work_id == work_id, WorkTag.tag_id == tag_id)\
            .first()
        if not work_tag:
            app.logger.error(
                f'WorkTagRemove: Short has no such tag: work_id {work_id},\
                      tag {tag_id}.'
            )
            return ResponseType(f'WorkTagRemove: Tagia ei löydy novellilta. \
                                work_id={work_id}, tag_id={tag_id}.', 400)
        session.delete(work_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in WorkTagRemove(): ' + str(exp))
        return ResponseType(f'WorkTagRemove: Tietokantavirhe. \
                            work_id={work_id}, tag_id={tag_id}.', 400)

    return retval


def work_add(params: Any) -> ResponseType:
    """
    A function that adds a new work to the database.

    Parameters:
    - params (Any): The parameters for the work.

    Returns:
    - ResponseType: The response containing the result of the operation.
    """
    session = new_session()

    data = params['data']

    work = Work()

    if len(data['title']) == 0:
        app.logger.error('WorkAdd: Empty title.')
        return ResponseType('Tyhjä nimi', 400)

    if 'contributions' not in data:
        app.logger.error('WorkAdd: No contributions.')
        return ResponseType('Ei kirjoittajaa tai toimittajaa', 400)

    if not (has_contribution_role(data['contributions'], 1) or
            has_contribution_role(data['contributions'], 3)):
        app.logger.error('WorkAdd: No author or editor.')
        return ResponseType('Ei kirjoittajaa tai toimittajaa', 400)

    work.title = bleach.clean(data['title'])
    work.subtitle = bleach.clean(data['subtitle'])
    work.orig_title = bleach.clean(data['orig_title'])

    work.pubyear = check_int(data['pubyear'])

    work.bookseriesnum = bleach.clean(data['bookseriesnum'])
    if 'bookseries' in data:
        result = _set_bookseries(session, work, data, None)
        if result:
            return result
    work.bookseriesorder = check_int(data['bookseriesorder'])

    if 'language' in data:
        result = set_language(session, work, data, None)
        if result:
            return result
    # Work type is required and defaults to 1 (book)
    work.type = 1
    if 'work_type' in data:
        result = _set_work_type(work, data, None)

    if 'description' in data:
        result = _set_description(work, data, None)
        if result:
            return result
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
        return ResponseType(f'WorkAdd: Tietokantavirhe teoksessa. \
                             work_id={work.id}', 400)

    # Add first edition (requires work id)
    new_edition = create_first_edition(work)
    try:
        session.add(new_edition)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe painoksessa. \
                            work_id={work.id}', 400)

    # Add part to tie work and edition together (requires work id and edition
    # id)
    new_part = Part(work_id=work.id, edition_id=new_edition.id)
    try:
        session.add(new_part)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe Part-taulussa. \
                            work_id={work.id}', 400)

    # Add contributors (requires part id)
    update_work_contributors(session, work.id, data['contributions'])

    # Add tags (requires work id)
    if 'tags' in data:
        for tag in data['tags']:
            if 'id' in tag:
                if tag['id'] != 0 and tag['id'] is not None:
                    new_tag = WorkTag(work_id=work.id, tag_id=tag['id'])
                    session.add(new_tag)

    # Add links (requires work id)
    if 'links' in data:
        for link in data['links']:
            if 'link' not in link:
                app.logger.error('WorkAdd: Link missing link.')
                return ResponseType('Linkin tiedot puutteelliset', 500)
            if link['link'] != '' and link['link'] is not None:
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
            is_ok = checkGenreField(session, genre)
            if not is_ok:
                app.logger.error('WorkAdd: Genre missing id.')
                return ResponseType('Genren tiedot puutteelliset', 400)
            new_genre = WorkGenre(work_id=work.id, genre_id=genre['id'])
            session.add(new_genre)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe asiasanoissa, linkeissä\
                            tai genreissä. work_id={work.id}', 400)

    # Update author string
    try:
        author_str = work.update_author_str()
        work.author_str = author_str
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe tekijänimissä. \
                            work_id={work.id}', 400)

    log_changes(session, obj=work, action='Uusi')
    session.commit()
    return ResponseType(str(work.id), 201)


# This is a simple function, splitting it to fit standards would make no sense.
# pylint: disable-next=too-many-locals,too-many-branches,too-many-statements,too-many-return-statements # noqa: E501
def work_update(
        params: Any) -> ResponseType:
    """
    Updates the work information based on the given parameters.

    Parameters:
    - params (Any): The parameters for the update.

    Returns:
    - ResponseType: The response type object indicating the status of the
    update.
    """
    retval = ResponseType('OK', 200)
    session = new_session()
    old_values = {}
    work: Any = None
    data = params['data']
    work_id = check_int(data['id'])

    work = session.query(Work).filter(Work.id == work_id).first()
    if not work:
        app.logger.error(f'WorkSave: Work not found. Id = {work_id}.')
        return ResponseType('Teosta ei löydy', 400)

    if 'title' in data:
        if data['title'] != work.title:
            if len(data['title']) == 0:
                app.logger.error(f'WorkSave: Empty title. Id = {work_id}.')
                return ResponseType('Tyhjä nimi', 400)
            old_values['Nimeke'] = work.title
            work.title = bleach.clean(data['title'])

    if 'subtitle' in data:
        if data['subtitle'] != work.subtitle:
            old_values['Alaotsikko'] = work.subtitle
            work.subtitle = bleach.clean(data['subtitle'])

    if 'orig_title' in data:
        if data['orig_title'] != work.orig_title:
            old_values['Alkukielinen nimi'] = work.orig_title
            work.orig_title = bleach.clean(data['orig_title'])

    if 'pubyear' in data:
        if data['pubyear'] != work.pubyear:
            old_values['Julkaisuvuosi'] = work.pubyear
            work.pubyear = check_int(data['pubyear'])

    if 'bookseriesnum' in data:
        if data['bookseriesnum'] != work.bookseriesnum:
            old_values['Kirjasarjan numero'] = work.bookseriesnum
            work.bookseriesnum = bleach.clean(data['bookseriesnum'])

    if 'bookseriesorder' in data:
        if data['bookseriesorder'] != work.bookseriesorder:
            old_values['Kirjasarjan järjestys'] = work.bookseriesorder
            work.bookseriesorder = bleach.clean(
                str(data['bookseriesorder']))

    if 'misc' in data:
        if data['misc'] != work.misc:
            old_values['Muuta'] = work.misc
            work.misc = bleach.clean(data['misc'])

    if 'description' in data:
        result = _set_description(work, data, old_values)
        if result:
            return result

    if 'descr_attr' in data:
        if data['descr_attr'] != work.descr_attr:
            old_values['Kuvauksen lähde'] = work.descr_attr
            work.descr_attr = bleach.clean(data['descr_attrs'])

    if 'imported_string' in data:
        if data['imported_string'] != work.imported_string:
            old_values['Lähde'] = work.imported_string
            work.imported_string = bleach.clean(data['imported_string'])

    # Language
    if 'language' in data:
        result = set_language(session, work, data, old_values)
        if result:
            return result

    # Bookseries
    if 'bookseries' in data:
        result = _set_bookseries(session, work, data, old_values)
        if result:
            return result

    # Worktype
    if 'work_type' in data:
        result = _set_work_type(work, data, old_values)
        if result:
            return result

    # Contributors
    if 'contributions' in data:
        if contributors_have_changed(work.contributions,
                                     data['contributions']):
            old_values['Tekijät'] = get_contributors_string(work.contributions)
            update_work_contributors(session, work.id, data['contributions'])

    # Genres
    if 'genres' in data:
        if genresHaveChanged(work.genres, data['genres']):
            existing_genres = session.query(WorkGenre)\
                .filter(WorkGenre.work_id == work_id)\
                .all()
            (to_add, to_remove) = get_join_changes(
                [x.genre_id for x in existing_genres],
                [x['id'] for x in data['genres']])
            if len(existing_genres) > 0:
                for genre in existing_genres:
                    session.delete(genre)
            for genre in data['genres']:
                sg = WorkGenre(genre_id=genre['id'], work_id=work.id)
                session.add(sg)
            old_values['Genret'] = ' -'.join([str(x) for x in to_add])
            old_values['Genret'] += ' +'.join([str(x) for x in to_remove])

    # Tags
    if 'tags' in data:
        if tags_have_changed(work.tags, data['tags']):
            existing_tags = session.query(WorkTag)\
                .filter(WorkTag.work_id == work_id)\
                .all()
            (to_add, to_remove) = get_join_changes(
                [x.tag_id for x in existing_tags],
                [x['id'] for x in data['tags']])
            if len(existing_tags) > 0:
                for tag in existing_tags:
                    session.delete(tag)
            for tag in data['tags']:
                st = WorkTag(tag_id=tag['id'], work_id=work.id)
                session.add(st)
            old_values['Asiasanat'] = ' -'.join([str(x) for x in to_add])
            old_values['Asiasanat'] += ' +'.join([str(x) for x in to_remove])

    # Links
    if 'links' in data:
        new_links = [x for x in data['links'] if x['link'] != '']
        if linksHaveChanged(work.links, new_links):
            existing_links = session.query(WorkLink)\
                .filter(WorkLink.work_id == work_id)\
                .all()
            (to_add, to_remove) = get_join_changes(
                [x.link for x in existing_links],
                [x['link'] for x in data['links']])
            if len(existing_links) > 0:
                for link in existing_links:
                    session.delete(link)
            for link in new_links:
                if 'link' not in link:
                    app.logger.error('work_update: Link missing address.')
                    return ResponseType('work_update: Linkin tiedot \
                                        puutteelliset', 400)
                sl = WorkLink(work_id=work.id, link=link['link'],
                              description=link['description'])
                session.add(sl)
            old_values['Linkit'] = ' -'.join([str(x) for x in to_add])
            old_values['Linkit'] += ' +'.join([str(x) for x in to_remove])

    # Awards

    if len(old_values) == 0:
        # Nothing has changed.
        return retval

    log_changes(session=session, obj=work, action='Päivitys',
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


def worktype_get_all() -> ResponseType:
    """
    Retrieves all work types from the database and returns them as a response.

    Returns:
        ResponseType: The response object containing the result of the
        operation.
    """
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


def work_delete(work_id: int) -> ResponseType:
    """
    Deletes a work from the database and all related records.

    Args:
        id (int): The ID of the work to be deleted.

    Returns:
        ResponseType: The response indicating the success or failure of the
            deletion operation.
            - If the work is successfully deleted, returns a response with
              status code 200 and the message 'WorkDelete: Teos poistettu'.
            - If the work is not found, returns a response with status code
              404 and the message 'WorkDelete: Teosta ei löydy'.
            - If there is a database error while deleting the work or its
              related records, returns a response with status code 400 and the
              message 'WorkDelete: Tietokantavirhe'.
    """
    session = new_session()
    old_values = {}

    try:
        work = session.query(Work).filter(Work.id == work_id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkDelete(): ' + str(exp))
        return ResponseType('WorkDelete: Tietokantavirhe', 400)

    if work is None:
        app.logger.error('Exception in WorkDelete(): Work not found.')
        return ResponseType('WorkDelete: Teosta ei löydy', 404)

    # Delete everything related to the work
    try:
        editions = session.query(Edition)\
            .join(Part)\
            .filter(Part.work_id == work_id)\
            .filter(Part.edition_id == Edition.id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in WorkDelete() deleting editions: {exp}')
        return ResponseType('WorkDelete: Tietokantavirhe', 400)
    for edition in editions:
        success = delete_edition(session, edition.id)
        if not success:
            session.rollback()
            return ResponseType('WorkDelete: Tietokantavirhe', 400)

    try:
        old_values['Nimi'] = work.title
        log_changes(session, obj=work, action='Poisto', old_values=old_values)
        session.query(WorkGenre).filter(WorkGenre.work_id == work_id).delete()
        session.query(WorkTag).filter(WorkTag.work_id == work_id).delete()
        session.query(WorkLink).filter(WorkLink.work_id == work_id).delete()
        session.query(Work).filter(Work.id == work_id).delete()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in WorkDelete() deleting work: {exp}')
        return ResponseType('WorkDelete: Tietokantavirhe', 400)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in WorkDelete() commit: {exp}')
        return ResponseType('WorkDelete: Tietokantavirhe', 400)

    return ResponseType('WorkDelete: Teos poistettu', 200)


def get_work_shorts(work_id: int) -> ResponseType:
    """
    Retrieves the short stories associated with a work.

    Args:
        work_id (int): The ID of the work.

    Returns:
        ResponseType: The response containing the serialized short stories.
    """
    session = new_session()
    try:
        shorts = session.query(ShortStory)\
            .join(Part)\
            .filter(Part.work_id == work_id)\
            .filter(Part.shortstory_id == ShortStory.id)\
            .distinct()\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in WorkShorts(): {str(exp)}')
        return ResponseType('WorkShorts: Tietokantavirhe', 400)
    schema = ShortBriefSchema(many=True)
    retval = schema.dump(shorts)
    return ResponseType(retval, 200)
