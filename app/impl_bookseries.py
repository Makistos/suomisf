from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.orm_decl import (Bookseries, Work)
from app.model import (BookseriesSchema, BookseriesBriefSchema)
from app.route_helpers import new_session
from app.impl import ResponseType, LogChanges, checkInt
from app import app
from typing import Any, Union
import bleach


def FilterBookseries(query: str) -> ResponseType:
    session = new_session()
    try:
        bookseries = session.query(Bookseries)\
            .filter(Bookseries.name.ilike(query + '%'))\
            .order_by(Bookseries.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterBookseries (query: {query}): ' + str(exp))
        return ResponseType('FilterBookseries: Tietokantavirhe.', 400)
    try:
        schema = BookseriesBriefSchema(many=True)
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterBookseries schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def GetBookseries(id: int) -> ResponseType:
    session = new_session()

    try:
        bookseries = session.query(Bookseries).filter(
            Bookseries.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetBookseries: ' + str(exp))
        return ResponseType(f'GetBookseries: Tietokantavirhe. id={id}', 400)

    try:
        schema = BookseriesSchema()
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetBookseries schema error: ' + str(exp))
        return ResponseType('GetBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ListBookseries() -> ResponseType:
    session = new_session()

    try:
        bookseries = session.query(Bookseries).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListBookseries: ' + str(exp))
        return ResponseType(f'ListBookseries: Tietokantavirhe. id={id}', 400)

    try:
        schema = BookseriesBriefSchema(many=True)
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListBookseries schema error: ' + str(exp))
        return ResponseType('ListBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)

def BookseriesCreate(params: Any) -> ResponseType:
    """
    Creates a new bookseries in the database.
    """
    session = new_session()
    data = params['data']

    if 'name' not in data:
        app.logger.error('BookseriesCreate: Name is missing.')
        return ResponseType('BookseriesCreate: Nimi puuttuu.', 400)

    bs = session.query(Bookseries).filter(Bookseries.name == data['name']).first()
    if bs:
        app.logger.error('BookseriesCreate: Name already exists.')
        return ResponseType('BookseriesCreate: Nimi on jo olemassa.', 400)

    bookseries = Bookseries()
    bookseries.name = data['name']

    if 'orig_name' in data:
        if data['orig_name'] == '':
            orig_name = None
        else:
            orig_name = data['orig_name']
        bookseries.orig_name = orig_name

    if 'important' in data:
        if data['important'] == 0:
            important = False
        else:
            important = True
        bookseries.important = important

    try:
        session.add(bookseries)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in BookseriesCreate: ' + str(exp))
        return ResponseType('BookseriesCreate: Tietokantavirhe.', 400)

    LogChanges(session, obj=bookseries, action='Uusi')

    return ResponseType(str(bookseries.id), 201)


def BookseriesUpdate(params: Any) -> ResponseType:
    retval = ResponseType('OK', 200)
    session = new_session()
    data = params['data']
    old_values = {}

    bookseries_id = checkInt(data['id'], negativeValuesAllowed=False, zerosAllowed=False)
    if bookseries_id == None:
        app.logger.error('BookseriesUpdate: Invalid id.')
        return ResponseType('BookseriesUpdate: Virheellinen id.', 400)

    bookseries = session.query(Bookseries).filter(Bookseries.id == bookseries_id).first()
    if not bookseries:
        app.logger.error('BookseriesUpdate: Unknown bookseries id.')
        return ResponseType('BookseriesUpdate: Tuntematon id.', 400)

    if 'name' in data:
        if data['name'] == '':
            app.logger.error('BookseriesUpdate: Name cannot be empty.')
            return ResponseType('BookseriesUpdate: Nimi ei voi olla tyhjä.', 400)
        bs = session.query(Bookseries).filter(Bookseries.name == data['name'])\
            .filter(Bookseries.id != bookseries_id)\
            .first()
        if bs:
            app.logger.error('BookseriesCreate: Name already exists.')
            return ResponseType('BookseriesCreate: Nimi on jo olemassa.', 400)
        if data['name'] != bookseries.name:
            old_values['name'] = bookseries.name
            bookseries.name = data['name']

    if 'orig_name' in data:
        if data['orig_name'] != bookseries.orig_name:
            old_values['orig_name'] = bookseries.orig_name
            if data['orig_name'] == '':
                bookseries.orig_name = None
            else:
                bookseries.orig_name = data['orig_name']

    if 'important' in data:
        old_values['important'] = bookseries.important
        bookseries.important = data['important']

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in BookseriesUpdate: ' + str(exp))
        return ResponseType('BookseriesUpdate: Tietokantavirhe.', 400)

    id = LogChanges(session, obj=bookseries, old_values=old_values, action='Päivitys')

    return retval

def BookseriesDelete(id: str) -> ResponseType:
    session = new_session()
    old_values = {}

    bookseries_id = checkInt(id, negativeValuesAllowed=False, zerosAllowed=False)
    if bookseries_id == None:
        app.logger.error('BookseriesDelete: Invalid id.')
        return ResponseType('BookseriesDelete: Virheellinen id.', 400)

    bookseries = session.query(Bookseries).filter(Bookseries.id == bookseries_id).first()
    if not bookseries:
        app.logger.error('BookseriesDelete: Unknown bookseries id.')
        return ResponseType('BookseriesDelete: Tuntematon id.', 400)
    old_values['name'] = bookseries.name

    works = session.query(Work).filter(Work.bookseries_id == bookseries_id).all()
    if works:
        app.logger.error('BookseriesDelete: Bookseries has works.')
        return ResponseType('BookseriesDelete: Kirjasarjalla on teoksia.', 400)

    try:
        session.delete(bookseries)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in BookseriesDelete: ' + str(exp))
        return ResponseType('BookseriesDelete: Tietokantavirhe.', 400)

    LogChanges(session, obj=bookseries, action='Poisto', old_values=old_values)

    return ResponseType('OK', 200)