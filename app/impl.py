""" Misc functions and definitions not in other impl_* files.
"""
from datetime import datetime, timedelta
from enum import IntEnum
import json
from typing import Dict, NamedTuple, Tuple, List, Union, Any, TypedDict, Set
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.api_errors import APIError
from app.route_helpers import new_session
from app.orm_decl import (Country, Log, Genre, Language, ContributorRole,
                          Work, Edition, ShortStory, Magazine, EditionImage,
                          ArticleLink, BookseriesLink, EditionLink,
                          PersonLink, PublisherLink, PubseriesLink, WorkLink)
from app.model import (GenreBriefSchema, EditionBriefestSchema, LanguageSchema,
                       CountryBriefSchema, ContributorRoleSchema, LogSchema,
                       LinkSchema, EditionImageSchema)
from app.types import HttpResponseCode, ContributorType
from app import app


class ResponseType(NamedTuple):
    """ Response type.
    """
    response: Union[str, Dict[str, Any]]
    status: Union[int, HttpResponseCode]


class SearchResultFields(TypedDict):
    """ Search result fields.
    """
    id: str
    img: str
    header: str
    description: str
    author: str
    type: str
    score: int


SearchResult = List[SearchResultFields]
SearchResults = Dict[str, SearchResult]

EmptySearchResult: SearchResultFields = {
    'id': '',
    'img': '',
    'header': '',
    'description': '',
    'author': '',
    'type': '',
    'score': 0
}

#######
# General stuff
#######


class SearchScores(IntEnum):
    """ Scores for each search result, used to sort results.
    """
    PERSON_NAME = 20
    PERSON_OTHER = 10
    WORK_TITLE = 19
    WORK_OTHER = 9
    STORY_NAME = 18
    STORY_OTHER = 8
    ARTICLE_TITLE = 17
    ARTICLE_OTHER = 7
    PUBLISHER_NAME = 16
    PUBLISHER_OTHER = 6
    STARTS_WITH = 10
    NONE = 0


# pylint: disable-next=dangerous-default-value
def check_int(value: Any = None,
              zeros_allowed: bool = True,
              negative_values: bool = False,
              allowed: List[int] = []) -> Union[int, None]:
    """
    Search for a given `item` and `word` in the specified `table` and return
    the corresponding search score.

    Args:
        table (str): The table to search in. Can be either 'work' or 'person'.
        item (Any): The item to search within.
        word (str): The word to search for.

    Returns:
        IntEnum: The search score value based on the search result. Possible i
        values are:
            - `SearchScores.NONE`: If no match is found.
            - `SearchScores.WORK_TITLE`: If the word is found in the `item`'s
                                         title when `table` is 'work'.
            - `SearchScores.WORK_OTHER`: If the word is found in the `item` but
                                         not in the title when `table` is
                                         'work'.
            - `SearchScores.PERSON_NAME`: If the word is found in the `item`'s
                                          fullname, name, or alt_name when
                                          `table` is 'person'.
            - `SearchScores.PERSON_OTHER`: If the word is found in the `item`
                                           but not in fullname, name, or
                                           alt_name when `table` is 'person'.
    """
    retval: int = 0
    try:
        retval = int(value)
    except (TypeError, ValueError):
        return None
    if not zeros_allowed and retval == 0:
        return None
    if not negative_values and retval < 0:
        return None
    if len(allowed) > 0:
        if retval not in allowed:
            return None
    return retval


def searchscore(table: str, item: Any, word: str) -> IntEnum:
    """
    Calculate the search score for a given item in a table based on a search
    word.

    Args:
        table (str): The name of the table to search in.
        item (Any): The item to search for.
        word (str): The search word.

    Returns:
        IntEnum: The search score for the item.
    """
    retval: IntEnum = SearchScores.NONE

    if table == 'work':
        if word in item.title.lower():
            retval = SearchScores.WORK_TITLE
            if item.title.lower().startswith(word):
                return retval + SearchScores.STARTS_WITH
        return SearchScores.WORK_OTHER
    if table == 'person':
        if item.fullname:
            if word in item.fullname.lower():
                retval = SearchScores.PERSON_NAME
                if item.fullname.lower().startswith(word):
                    return retval + SearchScores.STARTS_WITH
        if item.name:
            if word in item.name.lower():
                retval = SearchScores.PERSON_NAME
                if item.name.lower().startswith(word):
                    return retval + SearchScores.STARTS_WITH
        if item.alt_name.lower():
            if word in item.alt_name:
                retval = SearchScores.PERSON_NAME
                if item.alt_name.lower().startswith(word):
                    return retval + SearchScores.STARTS_WITH
        else:
            return SearchScores.PERSON_OTHER
    if table == 'story':
        if word in item.title.lower():
            retval = SearchScores.STORY_NAME
            if item.title.lower().startswith(word):
                return retval + SearchScores.STARTS_WITH
        else:
            return SearchScores.STORY_OTHER
    return retval


def get_changes(params: Dict[str, Any]) -> ResponseType:
    """
    Get changes made to the database.

    Defaults to all changes made in the last 30 days.

    Args:
        params (Dict[str, Any]): A dictionary containing the parameters for the
        function.

    Returns:
        ResponseType: The response type of the function.
    """
    period_length: int = 30
    stmt: str = 'SELECT Log.* FROM Log WHERE 1=1 '
    session = new_session()

    if 'period' in params:
        try:
            period_length = int(params['period'])
        except TypeError as exp:
            app.logger.error(f'get_changes: {exp}')
            raise APIError(f'Invalid period length {params["period"]}.',
                           HttpResponseCode.BAD_REQUEST) from exp
        cutoff_date = datetime.now() - timedelta(period_length)
        stmt += 'AND Log.Date >= "' + str(cutoff_date) + '" '
    else:
        cutoff_date = datetime.now() - timedelta(days=30)
        stmt += 'AND Log.Date >= "' + str(cutoff_date) + '" '

    if 'table' in params:
        table = params['table']
        stmt += 'AND table_name = "' + table + '" '

    if 'id' in params:
        try:
            table_id = int(params['id'])
        except TypeError as exp:
            app.logger.error(f'get_changes: {exp}')
            raise APIError(f'Invalid table id  {params["id"]}.',
                           HttpResponseCode.BAD_REQUEST) from exp
        stmt += 'AND table_id = "' + str(table_id) + '" '

    if 'action' in params:
        action = params['action']
        stmt += 'AND action = "' + action + '" '

    if 'field' in params:
        field = params['field']
        stmt += 'AND field_name = "' + field + '" '

    if 'userid' in params:
        try:
            userid = int(params['userid'])
        except TypeError as exp:
            app.logger.error(f'get_changes: {exp}')
            raise APIError(f'Invalid user id  {params["userid"]}.',
                           HttpResponseCode.BAD_REQUEST) from exp
        stmt += 'AND user_id = "' + str(userid) + '" '

    stmt += 'ORDER BY date DESC '
    if 'limit' in params:
        limit: int = 0
        try:
            limit = int(params['limit'])
        except TypeError as exp:
            app.logger.error(f'get_changes: {exp}')
            raise APIError(f'Invalid limit {params["limit"]}.',
                           HttpResponseCode.BAD_REQUEST) from exp
        stmt += 'LIMIT ' + str(limit) + ' '

    print(stmt)
    try:
        changes = session.query(Log)\
            .from_statement(text(stmt))\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in get_changes: {exp}.')
        return ResponseType(f'get_changes: Tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR)
    # changes = session.query(Log).filter(
    #     Log.date >= cutoff_date).order_by(Log.date.desc()).all()
    try:
        schema = LogSchema(many=True)
        retval = schema.dump(changes)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_changes schema error: {exp}.')
        return ResponseType(f'get_changes: Skeemavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, HttpResponseCode.OK)


def genre_list() -> ResponseType:
    """
    Calculate the search score for a given item in a table based on a search
    word.

    Args:
        table (str): The name of the table to search in.
        item (Any): The item to search for.
        word (str): The search word.

    Returns:
        IntEnum: The search score for the item.
    """
    session = new_session()

    try:
        genres = session.query(Genre).order_by(Genre.id)
    except SQLAlchemyError as exp:
        app.logger.error(f'Db Exception in genre_list(): {exp}.')
        return ResponseType(f'genre_list: Tietokantavirhe: {exp}.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)
    try:
        schema = GenreBriefSchema(many=True)
        retval = schema.dump(genres)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'genre_list schema error: {exp}.')
        return ResponseType(f'genre_list: Skeemavirhe: {exp}.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, HttpResponseCode.OK)


def country_list() -> ResponseType:
    """
    Retrieves a list of countries from the database and returns it in the
    response.

    Returns:
        ResponseType: The response object containing the list of countries and
        the status code.

    Raises:
        SQLAlchemyError: If there is an error with the database query.
        exceptions.MarshmallowError: If there is an error with the data schema.

    Example Usage:
        response = CountryList()
        print(response)
    """
    session = new_session()

    try:
        countries = session.query(Country).order_by(Country.name)
    except SQLAlchemyError as exp:
        app.logger.error(f'Db Exception in country_list(): {exp}.')
        return ResponseType(f'country_list: Tietokantavirhe: {exp}.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)
    try:
        schema = CountryBriefSchema(many=True)
        retval = schema.dump(countries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'country_list schema error: {exp}.')
        return ResponseType(f'country_list: Skeemavirhe: {exp}.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, HttpResponseCode.OK)


def role_list() -> ResponseType:
    """
    Retrieves a list of contributor roles from the database.

    Returns:
        ResponseType: The response object containing the list of roles and
        the HTTP status code.
    """
    session = new_session()

    try:
        roles = session.query(ContributorRole)
    except SQLAlchemyError as exp:
        app.logger.error(f'role_list: Db Exception: {exp}')
        return ResponseType('role_list: Tietokantavirhe.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)
    try:
        schema = ContributorRoleSchema(many=True)
        retval = schema.dump(roles)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'role_list schema error: {exp}')
        return ResponseType('role_list: Skeemavirhe.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, status=HttpResponseCode.OK)


def role_get(target: str) -> ResponseType:
    """
    Retrieves a single contributor role from the database.

    Args:
        target (str): The name of the role to retrieve.

    Returns:
        ResponseType: The response object containing the role and the HTTP
        status code.
    """
    session = new_session()
    role_ids: List[int] = []

    if target in ['work', 'edition']:
        # Work has author, editor and subject, edition has everything else
        role_ids = [ContributorType.AUTHOR.value, ContributorType.EDITOR.value,
                    ContributorType.SUBJECT.value]
    elif target == 'short':
        role_ids = [ContributorType.AUTHOR.value,
                    ContributorType.TRANSLATOR.value,
                    ContributorType.SUBJECT.value]
    elif target == 'issue':
        role_ids = [ContributorType.EDITOR_IN_CHIEF.value,
                    ContributorType.COVER_ARTIST.value]
    else:
        app.logger.error(f'role_get: Unknown target: {target}')
        return ResponseType(f'role_get: Tuntematon kohde {target}.',
                            status=HttpResponseCode.BAD_REQUEST)

    try:
        if target == 'edition':
            roles = session.query(ContributorRole)\
                .filter(ContributorRole.id.notin_(role_ids)).all()
        else:
            roles = session.query(ContributorRole)\
                .filter(ContributorRole.id.in_(role_ids)).all()

    except SQLAlchemyError as exp:
        app.logger.error(f'role_list Db Exception: {exp}')
        return ResponseType('role_get tietokantavirhe: {exp}.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)
    try:
        schema = ContributorRoleSchema(many=True)
        retval = schema.dump(roles)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'role_get schema error: {exp}')
        return ResponseType('role_get skeemavirhe: {exp}',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, status=HttpResponseCode.OK)


def filter_countries(query: str) -> ResponseType:
    """
    Retrieves a list of countries that match the given query.

    Args:
        query (str): The search query.

    Returns:
        ResponseType: The response object containing either the filtered
        countries or an error message.
    """
    session = new_session()
    try:
        countries = session.query(Country)\
            .filter(Country.name.ilike(query + '%'))\
            .order_by(Country.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterCountries (query: {query}): ' + str(exp))
        return ResponseType('FilterCountries: Tietokantavirhe.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)
    try:
        schema = CountryBriefSchema(many=True)
        retval = schema.dump(countries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterCountries schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterCountries: Skeemavirhe.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, HttpResponseCode.OK)


def filter_languages(query: str) -> ResponseType:
    """
    Filters the languages based on the given query.

    Args:
        query (str): A string representing the query to filter the languages.

    Returns:
        ResponseType: An instance of ResponseType containing the filtered
        languages.
    """
    session = new_session()
    try:
        languages = session.query(Language)\
            .filter(Language.name.ilike(query + '%'))\
            .order_by(Language.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterLanguages (query: {query}): {exp}.')
        return ResponseType('FilterLanguages: Tietokantavirhe.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)
    try:
        schema = LanguageSchema(many=True)
        retval = schema.dump(languages)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterLanguages schema error (query: {query}): {exp}.')
        return ResponseType('FilterLanguages: Skeemavirhe.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, HttpResponseCode.OK)


def set_language(
        session: Any,
        item: Any,
        data: Any,
        old_values:  Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Set the language for an item.

    Args:
        session (Any): The current session.
        item (Any): The item to set the language for.
        data (Any): The data containing the new language information.
        old_values (Union[Dict[str, Any], None]): The old values of the item.

    Returns:
        Union[ResponseType, None]: The response type or None.
    """
    lang_id: Union[int, None] = None

    if old_values is not None:
        if item.language_name:
            old_values['Kieli'] = item.language_name.name
        else:
            old_values['Kieli'] = None

    if not data['language'] or data['language'] is None:
        lang_id = None
    elif isinstance(data['language'], str) or 'id' not in data['language']:
        # User added a new language. Front returns this as a string
        # in the language field so we need to add this language to
        # the database first.
        lang_id = add_language(data['language'])
    else:
        lang_id = None
        lang_id = check_int(data['language']['id']) if data['language'] \
            else None
        if lang_id is not None:
            lang = session.query(Language)\
                .filter(Language.id == lang_id)\
                .first()
            if not lang:
                app.logger.error('SetLanguage: Language not found. Id = %s'
                                 ', {lang_id')
                return ResponseType('Kieltä ei löydy',
                                    status=HttpResponseCode.BAD_REQUEST)
    item.language = lang_id
    return None


def add_language(name: str) -> Union[int, None]:
    """
    Adds a new language to the database.

    Args:
        name (str): The name of the language.

    Returns:
        Union[int, None]: The ID of the newly added language if successful,
        None otherwise.
    """
    session = new_session()
    existing = session.query(Language)\
        .filter(Language.name == name)\
        .first()
    if existing:
        return existing.id
    try:
        language = Language(name=name)
        session.add(language)
        session.commit()
        return language.id
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in AddLanguage (name: {name}): {exp}')
        return None


def filter_link_names(query: str) -> ResponseType:
    """
    Filters link names based on a given query and returns a response.

    Args:
        query (str): The query to filter the link names.

    Returns:
        ResponseType: The response containing the filtered link names.

    Raises:
        SQLAlchemyError: If there is an error in the SQL query.

    Example:
        filter_link_names('query') -> ResponseType
    """
    session = new_session()
    try:
        al = session.query(ArticleLink.description)\
            .filter(ArticleLink.description.ilike(query + '%'))\
            .distinct().all()
        bl = session.query(BookseriesLink.description)\
            .filter(BookseriesLink.description.ilike(query + '%'))\
            .distinct().all()
        el = session.query(EditionLink.description)\
            .filter(EditionLink.description.ilike(query + '%'))\
            .distinct().all()
        pel = session.query(PersonLink.description)\
            .filter(PersonLink.description.ilike(query + '%')).distinct().all()
        pul = session.query(PublisherLink.description)\
            .filter(PublisherLink.description.ilike(query + '%'))\
            .distinct().all()
        publ = session.query(PubseriesLink.description)\
            .filter(PubseriesLink.description.ilike(query + '%'))\
            .distinct().all()
        wl = session.query(WorkLink.description)\
            .filter(WorkLink.description.ilike(query + '%')).distinct().all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterLinkNames (query: {query}): {exp}.')
        return ResponseType(f'FilterLinkNames: Tietokantavirhe: {exp}.',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    link_names: List[str] = list(set([x for x in al]
                                     + [x for x in bl]
                                     + [x for x in el]
                                     + [x for x in pel]
                                     + [x for x in pul]
                                     + [x for x in publ]
                                     + [x for x in wl]))
    # linkNames.sort()
    # retval: List[Dict[str, str]] = []
    # for ln in linkNames:
    #     retval.append({'name': ln})
    schema = LinkSchema(many=True)
    retval = schema.dump(link_names)
    return ResponseType(retval, HttpResponseCode.OK)


def get_select_ids(
        form: Any,
        item_field: str = 'itemId') -> Tuple[int, List[Dict[str, str]]]:
    ''' Read parameters from  a front end request for a select component.

        Each request has the parent id (work id etc) and a list of item ids
        corresponding to the items selected in a select component. This
        function parses these fields and returns parent id and a list
        containing the ids as ints.

        Args:
            form (request.form): Form that contains the values.
            item_field (str): Name for the parent id field. Default: "itemId".

        Returns:
            Tuple[int, List[int]]: A tuple of parent id and list of item ids.
    '''
    if ('items' not in form or item_field not in form):
        return (0, [])

    parentid = int(json.loads(form[item_field]))
    items = json.loads(form['items'])

    return (parentid, items)


def get_join_changes(
        existing: Union[List[int], Set[int]],
        new: List[int]) -> Tuple[List[int], List[int]]:
    """
    Calculate the changes needed to update an existing list or set with a new
    list.

    Args:
        existing (Union[List[int], Set[int]]): The existing list or set.
        new (List[int]): The new list to update.

    Returns:
        Tuple[List[int], List[int]]: A tuple containing two lists. The first
        list contains the items to add to the existing list or set. The second
        list contains the items to delete from the existing list or set.
    """
    to_add: List[int] = new
    to_delete: List[int] = []

    if existing:
        for item_id in existing:
            if item_id in new:
                to_add.remove(item_id)
            else:
                to_delete.append(item_id)

    return (to_add, to_delete)


def get_frontpage_data() -> ResponseType:
    """
    Retrieves data for the front page.

    This function connects to a database session and retrieves various counts
    and information to populate the front page of a website or application. It
    queries the number of works, editions, short stories, magazines, and
    edition images from the session. It also retrieves the latest editions and
    formats the data using the EditionBriefestSchema. The result is returned as
    a dictionary with keys 'works', 'editions', 'shorts', 'magazines',
    'covers', and 'latest'. The function returns a ResponseType object with the
    populated dictionary and a status code of 200.

    Returns:
        ResponseType: The response object containing the front page data.
    """
    session = new_session()
    retval = {}
    work_count = session.query(Work.id).count()
    retval['works'] = work_count
    edition_count = session.query(Edition.id).count()
    retval['editions'] = edition_count
    shorts_count = session.query(ShortStory.id)\
        .filter(ShortStory.story_type.in_((1, 2, 3))).count()
    retval['shorts'] = shorts_count
    magazine_count = session.query(Magazine.id).count()
    retval['magazines'] = magazine_count
    cover_count = session.query(EditionImage.id).count()
    retval['covers'] = cover_count
    latest = session.query(Edition).order_by(Edition.id.desc()).all()
    latest_list: List[Any] = []
    ids: List[int] = []
    for edition in latest:
        try:
            if edition.work[0].id not in ids:
                latest_list.append(edition)
                ids.append(edition.work[0].id)
            if len(latest_list) == 4:
                break
        except IndexError as exp:
            app.logger.error(
                f'IndexError in get_frontpage_data() {edition.id}: {exp}')
            return ResponseType(
                f'get_frontpage_data: Indeksivirhe {edition.id}: {exp}.',
                status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    schema = EditionBriefestSchema()
    latest_list = schema.dump(latest_list, many=True)
    retval['latest'] = latest_list
    return ResponseType(retval, 200)


def get_latest_covers(count: int) -> ResponseType:
    """
    Retrieves the latest covers.

    Args:
        count (int): The number of covers to retrieve.

    Returns:
        ResponseType: The response containing the serialized covers.
    """
    session = new_session()
    try:
        covers = session.query(EditionImage)\
            .order_by(EditionImage.id.desc())\
            .limit(count)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in get_latest_covers(): {str(exp)}')
        return ResponseType('get_latest_covers: Tietokantavirhe',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    try:
        schema = EditionImageSchema(many=True)
        retval = schema.dump(covers)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Exception in get_latest_covers(): {str(exp)}')
        return ResponseType('get_latest_covers: Skeemavirhe',
                            status=HttpResponseCode.INTERNAL_SERVER_ERROR)

    return ResponseType(retval, 200)
