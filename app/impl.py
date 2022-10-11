import datetime

from sqlalchemy.exc import SQLAlchemyError
from app.api_errors import APIError
from app.route_helpers import new_session
from app.orm_decl import (Country, Log, Genre, Language)
from app.model import *
from marshmallow import exceptions
from typing import Dict, NamedTuple, Tuple, List, Union, Any, TypedDict
from app import app
from sqlalchemy import text
import bleach
from enum import IntEnum


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
        cutoff_date = datetime.datetime.now() - datetime.timedelta(period_length)
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
        return ResponseType('Countrylist: Skeemavirhe.', 400)

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
