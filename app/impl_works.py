""" Implementations for work related functions.
"""
import html
from typing import Dict, List, Any, Union
import bleach
from sqlalchemy import or_, and_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased
from marshmallow import exceptions
from app.impl_helpers import objects_differ, str_differ
from app.impl_logs import log_changes
from app.route_helpers import new_session
from app.impl import (ResponseType, SearchResult,
                      SearchResultFields, searchscore, set_language, check_int,
                      get_join_changes)
from app.orm_decl import (Edition, Genre, Part, Tag, Work, WorkType,
                          WorkTag, WorkGenre, WorkLink, Bookseries, ShortStory,
                          Contributor, Person)
from app.model import (WorkBriefSchema, WorkTypeBriefSchema,
                       ShortBriefSchema)
from app.model_bookindex import (BookIndexSchema)
from app.model import WorkSchema
from app.impl_contributors import (update_work_contributors,
                                   contributors_have_changed,
                                   get_contributors_string,
                                   has_contribution_role)
from app.impl_genres import genresHaveChanged
from app.impl_tags import tags_have_changed
from app.impl_links import links_have_changed
from app.impl_editions import create_first_edition
from app.impl_genres import checkGenreField
from app.impl_editions import delete_edition
from app.impl_bookseries import add_bookseries
from app.impl_shorts import save_short_to_work
from app.types import ContributorTarget, HttpResponseCode

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
    if objects_differ(data['bookseries'], work.bookseries):
        bs_id = None
        if old_values is not None:
            old_values['Kirjasarja'] = (work.bookseries.name
                                        if work.bookseries else '')
        if (data['bookseries'] != "" and data['bookseries'] is not None and
                isinstance(data['bookseries'], str)):
            # User added a new bookseries. Front returns this as a string
            # in the bookseries field so we need to add this bookseries to
            # the database first.
            bs_id = add_bookseries(data['bookseries'])
        else:
            if (data['bookseries'] == "" or data["bookseries"] is None or
                    data["bookseries"]["name"] == "" or
                    data["bookseries"]["name"] is None):
                # User cleared the field -> remove bookseries
                work.bookseries_id = None
                return None
            bs_id = check_int(data['bookseries']['id'], zeros_allowed=False,
                              negative_values=False)
            if bs_id is not None:
                bs = session.query(Bookseries)\
                    .filter(Bookseries.id == bs_id)\
                    .first()
                if not bs:
                    app.logger.error(f'''WorkSave: Bookseries not found. Id =
                                     {data["bookseries"]["id"]}.''')
                    return ResponseType('Kirjasarjaa ei löydy',
                                        HttpResponseCode.BAD_REQUEST.value)
        work.bookseries_id = bs_id
    return None


def _set_tags(
        session: Any, work: Work, tags: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Sets the tags for a given work.

    Args:
        session (Any): The session object for the database connection.
        work (Work): The work object to set the tags for.
        data (Any): The data object containing the tags information.
        old_values (Union[Dict[str, Any], None]): The old values of the work
        object.

    Returns:
        Union[ResponseType, None]: The response type if there is an error,
                                   otherwise None.
    """
    if tags_have_changed(work.tags, tags):
        # Check if we need to create new tags
        try:
            for tag in tags:
                if tag['id'] == 0:
                    already_exists = session.query(Tag)\
                        .filter(Tag.name == tag['name'])\
                        .first()
                    if not already_exists:
                        new_tag = Tag(name=tag['name'], type_id=1)
                        session.add(new_tag)
                        session.flush()
                        tag['id'] = new_tag.id
                    else:
                        tag['id'] = already_exists.id
        except SQLAlchemyError as exp:
            app.logger.error(f'{exp}')
            return ResponseType('Uusia asiasanoja ei saatu talletettua.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

        existing_tags = session.query(WorkTag)\
            .filter(WorkTag.work_id == work.id)\
            .all()
        # (to_add, to_remove) = get_join_changes(
        #     [x.tag_id for x in existing_tags],
        #     [x['id'] for x in data['tags']])
        if len(existing_tags) > 0:
            for tag in existing_tags:
                session.delete(tag)
        for tag in tags:
            st = WorkTag(tag_id=tag['id'], work_id=work.id)
            session.add(st)
        old_tags = session.query(Tag.name)\
            .filter(Tag.id.in_([x.tag_id for x in existing_tags]))\
            .all()
        if old_values is not None:
            old_values['Asiasanat'] = ','.join([str(x[0]) for x in old_tags])

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
        if data['description']:
            html_text = html.unescape(data['description'])
        else:
            html_text = ''
    except (TypeError) as exp:
        app.logger.error('WorkSave: Failed to unescape html: ' +
                         data["description"] + '.' + str(exp))
        return ResponseType('Kuvauksen html-muotoilu epäonnistui',
                            HttpResponseCode.BAD_REQUEST.value)
    if str_differ(html_text, work.description):
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
                return ResponseType('WorkSave: Virheellinen teostyyppi.',
                                    HttpResponseCode.BAD_REQUEST.value)
            if old_values is not None:
                if work.work_type.id != work_type_id:
                    if work.work_type:
                        old_values['Tyyppi'] = work.work_type.name
                    else:
                        old_values['Tyyppi'] = ''
            work.type = work_type_id
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
        return ResponseType(f'GetWork: Tietokantavirhe. id={work_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not work:
        app.logger.error(f'GetWork: Work not found {work_id}.')
        return ResponseType('Teosta ei löytynyt. id={id}.',
                            HttpResponseCode.NOT_FOUND.value)
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
        return ResponseType('GetWork: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


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
        lower_search = bleach.clean(searchword).lower()
        try:
            works = session.query(Work)\
                .filter(Work.title.ilike('%' + lower_search + '%') |
                        Work.subtitle.ilike('%' + lower_search + '%') |
                        Work.orig_title.ilike('%' + lower_search + '%') |
                        Work.misc.ilike('%' + lower_search + '%') |
                        Work.description.ilike('%' + lower_search + '%'))\
                .join(Part)\
                .filter(Part.work_id == Work.id)\
                .join(Edition)\
                .filter(Edition.id == Part.edition_id)\
                .filter(Edition.title.ilike('%' + lower_search + '%') |
                        Edition.subtitle.ilike('%' + lower_search + '%'))\
                .order_by(Work.title)\
                .all()
        except SQLAlchemyError as exp:
            app.logger.error('Exception in SearchWorks: ' + str(exp))
            return []

        for work in works:
            if work.id in found_works:
                found_works[work.id]['score'] *= searchscore(
                    'work', work, lower_search)
            else:
                description = (work.description if work.description else '')
                if lower_search in description.lower():
                    start = description.lower().index(lower_search)
                    description = (
                        description[:start] + '<b>' +
                        description[start:start + len(lower_search)] +
                        '</b>' + description[start + len(lower_search):]
                        )

                item: SearchResultFields = {
                    'id': work.id,
                    'img': '',
                    'header': work.title,
                    'description': description,
                    'author': work.author_str,
                    'type': 'work',
                    'score': searchscore('work', work, lower_search)
                }
                found_works[work.id] = item
        retval = [value for _, value in found_works.items()]

    return retval


def search_books(params: Dict[str, str]) -> ResponseType:
    """
    Searches for books based on the given parameters.

    Args:
        params (Dict[str, str]): A dictionary containing the search parameters:
            - author: Author name or alternate name
            - title: Book title
            - orig_name: Original title
            - printyear_first: Earliest print year
            - printyear_last: Latest print year
            - genre: Genre ID
            - nationality: Author nationality ID
            - type: Work type ID

    Returns:
        ResponseType: An object representing the response of the search.
    """
    session = new_session()

    try:
        # Start base query
        query = session.query(Work).distinct()

        # Add author filter
        if 'author' in params and params['author']:
            author = bleach.clean(params['author'])
            query = query\
                .join(Part, Work.id == Part.work_id)\
                .join(Contributor, Part.id == Contributor.part_id)\
                .join(Person,
                      or_(
                        Person.id == Contributor.person_id,
                        Person.id == Contributor.real_person_id
                      ))\
                .filter(
                    and_(
                        Contributor.role_id == 1,
                        Part.shortstory_id.is_(None),
                        or_(
                            Person.name.ilike(f'{author}%'),
                            Person.alt_name.ilike(f'{author}%')
                        )
                    )
                )

        # Add print year filters with explicit join conditions for first
        # editions
        if any(key in params and params[key] for key in
               ['printyear_first', 'printyear_last']):
            # Create subquery to get first editions
            first_editions = session.query(
                Part.work_id,
                func.min(Edition.id).label('first_edition_id')
            ).join(
                Edition, Part.edition_id == Edition.id
            ).group_by(Part.work_id).subquery()

            # Join with first editions only
            query = query.join(
                first_editions, Work.id == first_editions.c.work_id
            ).join(
                Edition, Edition.id == first_editions.c.first_edition_id
            )

            if 'printyear_first' in params and params['printyear_first']:
                try:
                    year = int(bleach.clean(params['printyear_first']))
                    query = query.filter(Edition.pubyear >= year)
                except ValueError:
                    app.logger.error('Failed to convert printyear_first')

            if 'printyear_last' in params and params['printyear_last']:
                try:
                    year = int(bleach.clean(params['printyear_last']))
                    query = query.filter(Edition.pubyear <= year)
                except ValueError:
                    app.logger.error('Failed to convert printyear_last')

        # Add genre filter with explicit join to handle multiple genres
        if 'genre' in params and params['genre']:
            try:
                # Handle genre IDs that come as a list
                genre_ids = params['genre'] \
                    if isinstance(params['genre'], list) else [params['genre']]
                # Clean and convert each ID to int
                genre_ids = [int(bleach.clean(str(gid)))
                             for gid in genre_ids if gid]

                if genre_ids:
                    query = query.join(WorkGenre, Work.id ==
                                       WorkGenre.work_id)\
                        .filter(WorkGenre.genre_id.in_(genre_ids))
            except (ValueError, AttributeError) as exp:
                app.logger.error(f'Failed to convert genre ids: {exp}')
                return ResponseType(
                    'Virheellinen genre-id',
                    HttpResponseCode.BAD_REQUEST.value
                )

        # Add nationality filter with explicit joins and alias
        if 'nationality' in params and params['nationality']:
            # Create alias for Part table to avoid ambiguous joins
            part_alias = aliased(Part)
            contrib_alias = aliased(Contributor)

            # Join with aliases and explicit conditions
            query = query.join(
                part_alias, Work.id == part_alias.work_id
            ).join(
                contrib_alias,
                and_(
                    part_alias.id == contrib_alias.part_id,
                    contrib_alias.role_id == 1,  # Author role
                    part_alias.shortstory_id.is_(None)
                )
            ).join(
                Person,
                or_(
                    Person.id == contrib_alias.person_id,
                    Person.id == contrib_alias.real_person_id
                )
            ).filter(
                Person.nationality_id == int(params['nationality'])
            )

        # Add title filters
        if 'title' in params and params['title']:
            title = bleach.clean(params['title'])
            query = query.filter(
                or_(
                    Work.title.ilike(f'{title}%'),
                    Work.title.ilike(f'% {title}%')
                )
            )

        if 'orig_name' in params and params['orig_name']:
            orig_name = bleach.clean(params['orig_name'])
            query = query.filter(
                or_(
                    Work.orig_title.ilike(f'{orig_name}%'),
                    Work.orig_title.ilike(f'% {orig_name}%')
                )
            )

        # Add publication year filters
        if 'pubyear_first' in params and params['pubyear_first']:
            try:
                year = int(bleach.clean(params['pubyear_first']))
                query = query.filter(Work.pubyear >= year)
            except ValueError:
                app.logger.error('Failed to convert pubyear_first')

        if 'pubyear_last' in params and params['pubyear_last']:
            try:
                year = int(bleach.clean(params['pubyear_last']))
                query = query.filter(Work.pubyear <= year)
            except ValueError:
                app.logger.error('Failed to convert pubyear_last')

        # Add work type filter
        if 'type' in params and params['type']:
            query = query.filter(Work.type == int(params['type']))

        # Add ordering
        query = query.order_by(Work.author_str, Work.title)

        # Execute query
        works = query.all()

        # Serialize results
        schema = WorkBriefSchema(many=True)
        retval = schema.dump(works)
        return ResponseType(retval, HttpResponseCode.OK.value)

    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in search_books: {exp}')
        return ResponseType(
            f'Tietokantavirhe: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value
        )
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error in search_books: {exp}')
        return ResponseType(
            f'Skeemavirhe: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value
        )


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
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    # queries = get_recorded_queries()
    # app.logger.debug(queries)
    try:
        # schema = WorkBriefSchema(many=True)
        schema = BookIndexSchema(many=True)
        retval = schema.dump(works)
    except exceptions.MarshmallowError as exp:
        app.logger.error(exp)
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def work_tag_add(work_id: int, tag_id: int) -> ResponseType:
    """
    Adds a tag to a work.

    Args:
        work_id (int): The ID of the work to add the tag to.
        tag_id (int): The ID of the tag to add to the work.

    Returns
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
            return ResponseType('Novellia ei löydy',
                                HttpResponseCode.BAD_REQUEST.value)

        work_tag = WorkTag()
        work_tag.work_id = work_id
        work_tag.tag_id = tag_id
        session.add(work_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in WorkTagAdd(): ' + str(exp))
        return ResponseType(f'''WorkTagAdd: Tietokantavirhe. work_id={work_id},
                            tag_id={tag_id}.''',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)


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
                                work_id={work_id}, tag_id={tag_id}.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        session.delete(work_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in WorkTagRemove(): ' + str(exp))
        return ResponseType(f'WorkTagRemove: Tietokantavirhe. \
                            work_id={work_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


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
        return ResponseType('Tyhjä nimi', HttpResponseCode.BAD_REQUEST.value)

    if 'contributions' not in data:
        app.logger.error('WorkAdd: No contributions.')
        return ResponseType('Ei kirjoittajaa tai toimittajaa',
                            HttpResponseCode.BAD_REQUEST.value)

    if not (has_contribution_role(data['contributions'], 1) or
            has_contribution_role(data['contributions'], 3)):
        app.logger.error('WorkAdd: No author or editor.')
        return ResponseType('Ei kirjoittajaa tai toimittajaa',
                            HttpResponseCode.BAD_REQUEST.value)

    work.title = data['title']
    if 'subtitle' in data:
        work.subtitle = data['subtitle']
    else:
        work.subtitle = work.title

    if 'orig_title' in data:
        work.orig_title = data['orig_title']
    else:
        work.orig_title = ''

    if 'pubyear' in data:
        work.pubyear = check_int(data['pubyear'])
    else:
        work.pubyear = None

    if 'bookseriesnum' in data:
        work.bookseriesnum = data['bookseriesnum']
    else:
        work.bookseriesnum = ''
    if 'bookseries' in data:
        result = _set_bookseries(session, work, data, None)
        if result:
            return result
    if 'bookseriesorder' in data:
        work.bookseriesorder = check_int(data['bookseriesorder'])
    else:
        work.bookseriesorder = None

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
        work.descr_attr = data['descr_attr']
    if 'misc' in data:
        work.misc = data['misc']
    if 'imported_string' in data:
        work.imported_string = data['imported_string']

    try:
        session.add(work)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe teoksessa. \
                             work_id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Add first edition (requires work id)
    new_edition = create_first_edition(work)
    try:
        session.add(new_edition)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe painoksessa. \
                            work_id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Add part to tie work and edition together (requires work id and edition
    # id)
    new_part = Part(work_id=work.id, edition_id=new_edition.id)
    try:
        session.add(new_part)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe Part-taulussa. \
                            work_id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Add contributors (requires part id)
    update_work_contributors(session, work.id, data['contributions'])

    # Add tags (requires work id)
    if 'tags' in data:
        result = _set_tags(session, work, data['tags'], None)
        if result:
            return result

    # Add links (requires work id)
    if 'links' in data:
        for link in data['links']:
            if 'link' not in link:
                app.logger.error('WorkAdd: Link missing link.')
                return ResponseType('Linkin tiedot puutteelliset',
                                    HttpResponseCode.BAD_REQUEST.value)
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
                return ResponseType(
                    'Genren tiedot puutteelliset',
                    HttpResponseCode.INTERNAL_SERVER_ERROR.value)
            new_genre = WorkGenre(work_id=work.id, genre_id=genre['id'])
            session.add(new_genre)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe asiasanoissa, linkeissä\
                            tai genreissä. work_id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Update author string
    try:
        author_str = work.update_author_str()
        work.author_str = author_str
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in WorkAdd: ' + str(exp))
        return ResponseType(f'WorkAdd: Tietokantavirhe tekijänimissä. \
                            work_id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session, obj=work, action='Uusi')
    session.commit()
    return ResponseType(str(work.id), HttpResponseCode.CREATED.value)


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
    retval = ResponseType('OK', HttpResponseCode.OK.value)
    session = new_session()
    old_values = {}
    work: Any = None
    data = params['data']
    work_id = check_int(data['id'])

    work = session.query(Work).filter(Work.id == work_id).first()
    if not work:
        app.logger.error(f'WorkSave: Work not found. Id = {work_id}.')
        return ResponseType('Teosta ei löydy',
                            HttpResponseCode.NOT_FOUND.value)

    if 'title' in data:
        if str_differ(data['title'], work.title):
            if len(data['title']) == 0:
                app.logger.error(f'WorkSave: Empty title. Id = {work_id}.')
                return ResponseType('Tyhjä nimi',
                                    HttpResponseCode.BAD_REQUEST.value)
            old_values['Nimeke'] = work.title
            work.title = data['title']

    if 'subtitle' in data:
        if str_differ(data['subtitle'], work.subtitle):
            old_values['Alaotsikko'] = work.subtitle
            work.subtitle = data['subtitle']

    if 'orig_title' in data:
        if str_differ(data['orig_title'], work.orig_title):
            old_values['Alkukielinen nimi'] = work.orig_title
            work.orig_title = data['orig_title']

    if 'pubyear' in data:
        if data['pubyear'] != work.pubyear:
            old_values['Julkaisuvuosi'] = work.pubyear
            work.pubyear = check_int(data['pubyear'])

    if 'bookseriesnum' in data:
        if data['bookseriesnum'] != work.bookseriesnum:
            old_values['Kirjasarjan numero'] = work.bookseriesnum
            work.bookseriesnum = data['bookseriesnum']

    if 'bookseriesorder' in data:
        if data['bookseriesorder'] != work.bookseriesorder:
            old_values['Kirjasarjan järjestys'] = work.bookseriesorder
            work.bookseriesorder = check_int(data['bookseriesorder'])

    if 'misc' in data:
        if str_differ(data['misc'], work.misc):
            old_values['Muuta'] = work.misc
            work.misc = data['misc']

    if 'description' in data:
        result = _set_description(work, data, old_values)
        if result:
            return result

    if 'descr_attr' in data:
        if str_differ(data['descr_attr'], work.descr_attr):
            old_values['Kuvauksen lähde'] = work.descr_attr
            work.descr_attr = data['descr_attr']

    if 'imported_string' in data:
        if str_differ(data['imported_string'], work.imported_string):
            old_values['Lähde'] = work.imported_string
            work.imported_string = data['imported_string']

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
            old_values['Tekijät'] = get_contributors_string(
                work.contributions, ContributorTarget.WORK)
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
            old_genres = session.query(Genre.name)\
                .filter(Genre.id.in_([x.genre_id for x in existing_genres]))\
                .all()
            # to_add = session.query(Genre.name)\
            #     .filter(Genre.id.in_(to_add))\
            #     .all()
            old_values['Genret'] = ','.join([str(x[0]) for x in old_genres])
            # if (len(to_add) > 0 and len(to_remove) > 0):
            #     old_values['Genret'] += '\n'
            # old_values['Genret'] += ' +' + ','.join([str(x[0]) for x in
            # to_remove])

    # Tags
    if 'tags' in data:
        result = _set_tags(session, work, data['tags'], old_values)
        if result:
            return result

    # Links
    if 'links' in data:
        new_links = [x for x in data['links'] if x['link'] != '']
        if links_have_changed(work.links, new_links):
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
        return ResponseType(f'WorkSave: Tietokantavirhe. id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        author_str = work.update_author_str()
        work.author_str = author_str
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in WorkSave() commit: ' + str(exp))
        return ResponseType(f'WorkSave: Tietokantavirhe. id={work.id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

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
        return ResponseType('WorkTypeGetAll: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = WorkTypeBriefSchema(many=True)
        retval = schema.dump(worktypes)
    except exceptions.MarshmallowError as exp:
        app.logger.error('Exception in WorkTypeGetAll(): ' + str(exp))
        return ResponseType('WorkTypeGetAll: Serialisointivirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


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
        return ResponseType('WorkDelete: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if work is None:
        app.logger.error('Exception in WorkDelete(): Work not found.')
        return ResponseType('WorkDelete: Teosta ei löydy',
                            HttpResponseCode.NOT_FOUND.value)

    # Delete everything related to the work
    try:
        editions = session.query(Edition)\
            .join(Part)\
            .filter(Part.work_id == work_id)\
            .filter(Part.edition_id == Edition.id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in WorkDelete() deleting editions: {exp}')
        return ResponseType('WorkDelete: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    for edition in editions:
        success = delete_edition(session, edition.id)
        if not success:
            session.rollback()
            return ResponseType('WorkDelete: Tietokantavirhe',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

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
        return ResponseType('WorkDelete: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in WorkDelete() commit: {exp}')
        return ResponseType('WorkDelete: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('WorkDelete: Teos poistettu',
                        HttpResponseCode.OK.value)


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
        return ResponseType('WorkShorts: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    schema = ShortBriefSchema(many=True)
    retval = schema.dump(shorts)
    return ResponseType(retval, HttpResponseCode.OK.value)


def save_work_shorts(params: Any) -> ResponseType:
    """
    Saves short stories to a work.

    This function is way too complex thanks to the less-than-perfect database
    model. The only way to store contributors to a story is through the part
    table. If a story is not connected to any work then we need to create an
    "empty" part which does not reference any works (or editions for that
    matter).

    In this case it is possible that a story is removed from the only work they
    are attached to so we need to make sure these stories have an empty part.

    Args:
        params (Any): A dictionary containing the parameters for saving the
                      short stories.
            It should have the following keys:
            - 'work_id': The ID of the work to which the short stories will be
                         saved.
            - 'shorts': A list of short stories to be saved.

    Returns:
        ResponseType: The response object indicating the success of the
                      operation.
            It has the following attributes:
            - 'message': A string indicating the success message.
            - 'status_code': An integer representing the HTTP status code.

    Raises:
        None

    """
    session = new_session()

    work_id = params['work_id']
    new_shorts_list = params['shorts']

    # Because of the stupid db schema we need to save contributors first so we
    # can put them back later.
    old_contributors: Dict[int, List[Dict[str, Any]]] = {}
    new_contributors: Dict[int, List[Dict[str, Any]]] = {}
    old_story_ids: Dict[int, int] = {}

    # Find short stories that existed for work
    try:
        old_stories_list = session.query(ShortStory)\
            .join(Part)\
            .filter(Part.work_id == work_id)\
            .filter(Part.shortstory_id.isnot(None))\
            .filter(ShortStory.id == Part.shortstory_id)\
            .distinct()\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'save_work_shorts(): {(work_id)} {str(exp)}')
        return ResponseType(f'Tietokantavirhe: {exp}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Store contributors for existing stories, this is needed in case a story
    # is removed from work and there are no other works or magazines it appears
    # in. In that case we need to save contributors to an "empty" part.
    for story in old_stories_list:
        try:
            contribs = session.query(Contributor)\
                .join(Part)\
                .filter(Part.shortstory_id == story.id)\
                .filter(Part.id == Contributor.part_id)\
                .all()
        except SQLAlchemyError as exp:
            app.logger.error(f'save_work_shorts(): ({work_id}) {str(exp)}')
            return ResponseType(f'Tietokantavirhe: {exp}',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        old_contributors[story.id] = []
        for contrib in contribs:
            found = False
            # Check if contributor info is already in list
            for contrib2 in old_contributors[story.id]:
                if (contrib.person_id == contrib2["person_id"] and
                        contrib.role_id == contrib2["role_id"]):
                    found = True
            # Save contributor info if it's author or translator
            if (not found and contrib.role_id == 1 or contrib.role_id == 2):
                old_contributors[story.id].append({
                    "person_id": contrib.person_id,
                    "role_id": contrib.role_id,
                    "real_person_id": contrib.real_person_id,
                    "description": contrib.description
                })
        old_story_ids[story.id] = story.id

    # Find contributors for new stories
    for short in new_shorts_list:
        try:
            contribs = session.query(Contributor)\
                .join(Part)\
                .filter(Part.shortstory_id == short)\
                .filter(Part.id == Contributor.part_id)\
                .all()
        except SQLAlchemyError as exp:
            app.logger.error(f'save_work_shorts(): ({work_id}) {str(exp)}')
            return ResponseType(f'Tietokantavirhe: {exp}',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        if contribs:
            for contrib in contribs:
                if short not in new_contributors:
                    new_contributors[short] = []
                # Check if this contributor already exists for this short
                duplicate = False
                for existing_contrib in new_contributors[short]:
                    if (existing_contrib[0]['person_id'] == contrib.person_id
                            and existing_contrib[0]['role_id'] ==
                            contrib.role_id):
                        duplicate = True
                        break
                if not duplicate:
                    new_contributors[short].append([
                        {
                            "person_id": contrib.person_id,
                            "role_id": contrib.role_id,
                            "real_person_id": contrib.real_person_id,
                            "description": contrib.description
                        }
                    ])

    # Delete old parts
    old_parts = session.query(Part)\
        .filter(Part.work_id == work_id)\
        .filter(Part.shortstory_id.isnot(None))\
        .all()
    for part in old_parts:
        contribs = session.query(Contributor)\
            .filter(Contributor.part_id == part.id)\
            .all()
        for contrib in contribs:
            session.delete(contrib)

    session.flush()

    for part in old_parts:
        session.delete(part)

    session.flush()

    for short in new_shorts_list:
        retval = save_short_to_work(session, work_id, short)
        if not retval:
            session.rollback()
            app.logger.error(
                'save_work_shorts(): '
                f'Failed to save short {short} to work {work_id}.')
            return ResponseType('Tietojen tallentaminen ei onnistunut',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Save contributors to new entries
    try:
        new_parts = session.query(Part)\
            .filter(Part.work_id == work_id)\
            .filter(Part.shortstory_id.isnot(None))\
            .all()
        for part in new_parts:
            for contrib in new_contributors[part.shortstory_id]:
                new_contrib = Contributor(
                    part_id=part.id,
                    person_id=contrib[0]['person_id'],
                    role_id=contrib[0]['role_id'],
                    real_person_id=contrib[0]['real_person_id'],
                    description=contrib[0]['description']
                )
                session.add(new_contrib)
            # This story has a part
            if part.shortstory_id in old_contributors:
                del old_contributors[part.shortstory_id]
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(
            'save_work_shorts(): '
            f'Failed to save contributors for work {work_id}: {exp}.')
        return ResponseType(
            f'Tekijätietoja ei saatu tallennettua: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.flush()

    # Save contributor info for shorts that are not in any work anymore.
    # old_contributors should only contain shorts that are not in the work
    # any more.
    # First create the parts:
    new_part_ids = []
    try:
        for short in old_contributors:
            parts = session.query(Part)\
                .filter(Part.shortstory_id == short)\
                .all()
            if len(parts) == 0:
                part = Part(shortstory_id=short)
                session.add(part)
                new_part_ids.append((part.id, short))
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(
            'save_work_shorts(): '
            'Failed to save contributors for stories for work '
            f'{work_id}: {exp} .')
        return ResponseType(
            f'Tekijätietoja ei saatu tallennettua: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.flush()

    # Then add contributors to these homeless stories:
    try:
        for part in new_part_ids:
            for contrib in old_contributors[part[1]]:
                new_contrib = Contributor(
                    part_id=part[0],
                    person_id=contrib['person_id'],
                    role_id=contrib['role_id'],
                    real_person_id=contrib['real_person_id'],
                    description=contrib['description'],
                )
                session.add(new_contrib)
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(
            'save_work_shorts(): '
            f'Failed to save contributors for stories {work_id}: {exp} .')
        return ResponseType(
            f'Tekijätietoja ei saatu tallennettua: {exp}',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.commit()

    return ResponseType('OK', HttpResponseCode.OK.value)


def get_latest_works(count: int) -> ResponseType:
    """
    Returns the latest works.

    Args:
        count (number): The number of works to return.

    Returns:
        ResponseType: The response containing the list of works.
    """
    session = new_session()
    works = session.query(Work)\
        .order_by(Work.id.desc())\
        .limit(count)\
        .all()
    try:
        schema = WorkBriefSchema(many=True)
        retval = schema.dump(works)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Exception in get_latest_works(): {exp}')
        return ResponseType('get_latest_works: Skeemavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)
