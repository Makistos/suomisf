from datetime import datetime, timedelta
from xmlrpc.client import Boolean

from sqlalchemy.exc import SQLAlchemyError
from app.api_errors import APIError
from app.route_helpers import new_session
from app.orm_decl import (Country, Log, Genre, Language, ContributorRole,
                          Work, Edition, ShortStory, Magazine, EditionImage)
from app.model import *
from marshmallow import exceptions
from typing import Dict, NamedTuple, Tuple, List, Union, Any, TypedDict, Set
from app import app
from sqlalchemy import text
import bleach
from enum import IntEnum
from flask_login import current_user
import json


class ResponseType(NamedTuple):
    response: Union[str, Dict[str, Any]]
    status: int


class SearchResultFields(TypedDict):
    id: str
    img: str
    header: str
    description: str
    type: str
    score: int


SearchResult = List[SearchResultFields]
SearchResults = Dict[str, SearchResult]


#######
# General stuff
#######


class SearchScores(IntEnum):
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
    NONE = 0

# def getJoinChanges(existing: List[Any], updated: List[Any], comparator) -> List[Any]:


def checkInt(value: Any = None,
             zerosAllowed: Boolean = True,
             negativeValuesAllowed: Boolean = False) -> Union[int, None]:
    """
    Checks that given value is an integer.

    Parameters
    ----------

    """
    retval: int = 0
    try:
        retval = int(value)
    except (TypeError, ValueError) as exp:
        return None
    if not zerosAllowed and retval == 0:
        return None
    if not negativeValuesAllowed and retval < 0:
        return None
    return retval


def searchScore(table: str, item: Any, word: str) -> IntEnum:
    retval: IntEnum = SearchScores.NONE

    if table == 'work':
        if word in item.title.lower():
            return SearchScores.WORK_TITLE
        else:
            return SearchScores.WORK_OTHER
    if table == 'person':
        if item.fullname:
            if word in item.fullname.lower():
                return SearchScores.PERSON_NAME
        if item.name:
            if word in item.name.lower():
                return SearchScores.PERSON_NAME
        if item.alt_name.lower():
            if word in item.alt_name:
                return SearchScores.PERSON_NAME
        else:
            return SearchScores.PERSON_OTHER
    return retval


def GetChanges(params: Dict[str, Any]) -> ResponseType:
    # Get changes made to the database.
    #
    # Defaults to all changes made in the last 30 days.
    #
    period_length: int = 30
    stmt: str = 'SELECT Log.* FROM Log WHERE 1=1 '
    session = new_session()

    if 'period' in params:
        try:
            period_length = int(params['period'])
        except TypeError as exp:
            raise APIError
        cutoff_date = datetime.now() - timedelta(period_length)
        stmt += 'AND Log.Date >= "' + str(cutoff_date) + '" '

    if 'table' in params:
        table = bleach.clean(params['table'])
        stmt += 'AND table_name = "' + table + '" '

    if 'id' in params:
        try:
            id = int(params['id'])
        except TypeError as exp:
            raise APIError
        stmt += 'AND table_id = "' + str(id) + '" '

    if 'action' in params:
        action = bleach.clean(params['action'])
        stmt += 'AND action = "' + action + '" '

    if 'field' in params:
        field = bleach.clean(params['field'])
        stmt += 'AND field_name = "' + field + '" '

    if 'userid' in params:
        try:
            userid = int(params['userid'])
        except TypeError as exp:
            raise APIError
        stmt += 'AND user_id = "' + str(userid) + '" '

    stmt += 'ORDER BY date DESC '
    if 'limit' in params:
        limit: int = 0
        try:
            limit = int(params['limit'])
        except TypeError as exp:
            raise APIError
        stmt += 'LIMIT ' + str(limit) + ' '

    print(stmt)
    changes = session.query(Log)\
        .from_statement(text(stmt))\
        .all()
    # changes = session.query(Log).filter(
    #     Log.date >= cutoff_date).order_by(Log.date.desc()).all()
    schema = LogSchema(many=True)
    retval = schema.dump(changes)

    return ResponseType(retval, 200)


table_locals = {'article': 'Artikkeli',
                'edition': 'Painos',
                'issue': 'Irtonumero',
                'magazine': 'Lehti',
                'person': 'Henkilö',
                'publisher': 'Kustantaja',
                'shortstory': 'Novelli',
                'work': 'Teos'}


def LogChanges(session: Any, obj: Any, action: str = 'Päivitys',
               fields: List[str] = [], old_values: Dict[str, Any] = {}) -> None:
    ''' Log a change made to data.

    Logging is done in the same session as the object itself, so it will
    also be in the same commit. I.e. if storing data fails for some reason
    log is also not stored.

    Args:
        session (Any): Session handler.
        obj (Any): Object that was changed.
        action (str, optional): Description of change, either "Päivitys" or "Uusi". Defaults to 'Päivitys'.
        fields (List[str], optional): Fields that were changed. Needed for "Päivitys", not used for "Uusi". Defaults to [].
    '''
    name: str = obj.name
    tbl_name = table_locals[obj.__table__.name]

    if action == 'Päivitys':
        for field in fields:
            if field in old_values:
                old_value = old_values[field]
            else:
                old_value = None
            log = Log(table_name=tbl_name,
                      field_name=field,
                      table_id=obj.id,
                      object_name=name,
                      action=action,
                      user_id=current_user.get_id(),
                      old_value=old_value,
                      date=datetime.now())
            session.add(log)
    else:
        log = Log(table_name=tbl_name,
                  field_name='',
                  table_id=obj.id,
                  object_name=name,
                  action=action,
                  user_id=current_user.get_id(),
                  date=datetime.now())
        session.add(log)


def GenreList() -> ResponseType:
    session = new_session()

    try:
        genres = session.query(Genre).order_by(Genre.id)
    except SQLAlchemyError as exp:
        app.logger.error('Db Exception in GenreList(): ' + str(exp))
        return ResponseType('GenreList: Tietokantavirhe.', 400)
    try:
        schema = GenreBriefSchema(many=True)
        retval = schema.dump(genres)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GenreList schema error: ' + str(exp))
        return ResponseType('Genrelist: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def CountryList() -> ResponseType:
    session = new_session()

    try:
        countries = session.query(Country).order_by(Country.name)
    except SQLAlchemyError as exp:
        app.logger.error('Db Exception in CountryList(): ' + str(exp))
        return ResponseType('CountryList: Tietokantavirhe.', 400)
    try:
        schema = CountryBriefSchema(many=True)
        retval = schema.dump(countries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('CountryList schema error: ' + str(exp))
        return ResponseType('CountryList: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def RoleList() -> ResponseType:
    session = new_session()

    try:
        roles = session.query(ContributorRole)
    except SQLAlchemyError as exp:
        app.logger.error('Db Exception in RoleList(): ' + str(exp))
        return ResponseType('RoleList: Tietokantavirhe.', 400)
    try:
        schema = ContributorRoleSchema(many=True)
        retval = schema.dump(roles)
    except exceptions.MarshmallowError as exp:
        app.logger.error('RoleList schema error: ' + str(exp))
        return ResponseType('RoleList: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def FilterCountries(query: str) -> ResponseType:
    session = new_session()
    try:
        countries = session.query(Country)\
            .filter(Country.name.ilike(query + '%'))\
            .order_by(Country.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterCountries (query: {query}): ' + str(exp))
        return ResponseType('FilterCountries: Tietokantavirhe.', 400)
    try:
        schema = CountryBriefSchema(many=True)
        retval = schema.dump(countries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterCountries schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterCountries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def FilterLanguages(query: str) -> ResponseType:
    session = new_session()
    try:
        languages = session.query(Language)\
            .filter(Language.name.ilike(query + '%'))\
            .order_by(Language.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterLanguages (query: {query}): ' + str(exp))
        return ResponseType('FilterLanguages: Tietokantavirhe.', 400)
    try:
        schema = LanguageSchema(many=True)
        retval = schema.dump(languages)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterLanguages schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterLanguages: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def GetSelectIds(form: Any, item_field: str = 'itemId') -> Tuple[int, List[Dict[str, str]]]:
    ''' Read parameters from  a front end request for a select component.

        Each request has the parent id (work id etc) and a list of item ids
        corresponding to the items selected in a select component. This
        function parses these fields and returns parent id and a list containing
        the ids as ints.

        Args:
            form (request.form): Form that contains the values.
            item_field (str): Name for the parent id field. Default: "itemId".

        Returns:
            Tuple[int, List[int]]: A tuple of parent id and list of item ids.
    '''
    if ('items' not in form or item_field not in form):
        return(0, [])

    parentid = int(json.loads(form[item_field]))
    items = json.loads(form['items'])

    return(parentid, items)


def GetJoinChanges(existing: Union[List[int], Set[int]], new: List[int]) -> Tuple[List[int], List[int]]:
    to_add: List[int] = new
    to_delete: List[int] = []

    if existing:
        for id in existing:
            if id in new:
                to_add.remove(id)
            else:
                to_delete.append(id)

    return (to_add, to_delete)


def GetFrontpageData() -> ResponseType:
    session = new_session()
    retval = {}
    workCount = session.query(Work.id).count()
    retval['works'] = workCount
    editionCount = session.query(Edition.id).count()
    retval['editions'] = editionCount
    shortsCount = session.query(ShortStory.id).count()
    retval['shorts'] = shortsCount
    magazineCount = session.query(Magazine.id).count()
    retval['magazines'] = magazineCount
    coverCount = session.query(EditionImage.id).count()
    retval['covers'] = coverCount
    latest = session.query(Edition).order_by(Edition.id.desc()).all()
    latestList: List[Any] = []
    ids: List[int] = []
    for edition in latest:
        if edition.id not in ids:
            latestList.append(edition)
            ids.append(edition.id)
        if len(latestList) == 4:
            break

    schema = EditionBriefestSchema()
    latestList = schema.dump(latestList, many=True)
    retval['latest'] = latestList
    return ResponseType(retval, 200)
