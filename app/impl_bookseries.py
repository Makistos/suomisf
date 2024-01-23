""" Bookseries related functions. """
from typing import Any, Union
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl_logs import log_changes

from app.orm_decl import (Bookseries, Work)
from app.model import (BookseriesSchema, BookseriesBriefSchema)
from app.route_helpers import new_session
from app.impl import ResponseType, check_int
from app import app
from app.types import HttpResponseCode


def filter_bookseries(query: str) -> ResponseType:
    """
    Filter book series based on a query string.

    Args:
        query (str): The query string used to filter the book series.

    Returns:
        ResponseType: An object representing the response of the function.
            If successful, it contains the filtered book series.
            If an error occurs, it contains an error message and status code.
    """
    session = new_session()
    try:
        bookseries = session.query(Bookseries)\
            .filter(Bookseries.name.ilike(query + '%'))\
            .order_by(Bookseries.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterBookseries (query: {query}): ' + str(exp))
        return ResponseType('FilterBookseries: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = BookseriesBriefSchema(many=True)
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterBookseries schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterBookseries: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_bookseries(series_id: int) -> ResponseType:
    """
    Retrieves a book series from the database based on the provided series ID.

    Args:
        series_id (int): The ID of the book series to retrieve.

    Returns:
        ResponseType: The retrieved book series object or an error response.
    """
    session = new_session()

    try:
        bookseries = session.query(Bookseries).filter(
            Bookseries.id == series_id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetBookseries: ' + str(exp))
        return ResponseType(f'GetBookseries: Tietokantavirhe. id={series_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    if bookseries is None:
        return ResponseType(f'GetBookseries: Sarjaa ei löydy. id={series_id}',
                            HttpResponseCode.NOT_FOUND.value)
    try:
        schema = BookseriesSchema()
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetBookseries schema error: ' + str(exp))
        return ResponseType('GetBookseries: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def list_bookseries() -> ResponseType:
    """
    Retrieves a list of all book series from the database.

    Returns:
        ResponseType: The response object containing the list of book series.
    """
    session = new_session()

    try:
        bookseries = session.query(Bookseries).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListBookseries: ' + str(exp))
        return ResponseType(f'ListBookseries: Tietokantavirhe. id={id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = BookseriesBriefSchema(many=True)
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListBookseries schema error: ' + str(exp))
        return ResponseType('ListBookseries: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def bookseries_create(params: Any) -> ResponseType:
    """
    Creates a new book series with the given parameters.

    Args:
        params (Any): The parameters for creating the book series.

    Returns:
        ResponseType: The response containing the ID of the created book series
                      or an error message.

    Raises:
        SQLAlchemyError: If there is an error during the database transaction.
    """
    session = new_session()
    data = params['data']

    if 'name' not in data:
        app.logger.error('BookseriesCreate: Name is missing.')
        return ResponseType('BookseriesCreate: Nimi puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)

    bs = session.query(Bookseries)\
        .filter(Bookseries.name == data['name']).first()
    if bs:
        app.logger.error('BookseriesCreate: Name already exists.')
        return ResponseType('BookseriesCreate: Nimi on jo olemassa.',
                            HttpResponseCode.BAD_REQUEST.value)

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
        return ResponseType('BookseriesCreate: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session, obj=bookseries, action='Uusi')

    return ResponseType(str(bookseries.id), HttpResponseCode.CREATED.value)


def bookseries_update(params: Any) -> ResponseType:
    """
    Updates a book series with the given parameters.

    Args:
        params (Any): The parameters for the update.

    Returns:
        ResponseType: The response indicating the success or failure of the
                      update.

    Raises:
        ValueError: If the book series ID is invalid.
        ValueError: If the book series ID does not exist.
        ValueError: If the name is empty.
        ValueError: If the name already exists.
        ValueError: If there is an exception during the database commit.
    """
    session = new_session()
    data = params['data']
    old_values = {}

    bookseries_id = check_int(data['id'],
                              negative_values=False,
                              zeros_allowed=False)
    if bookseries_id is None:
        app.logger.error('BookseriesUpdate: Invalid id.')
        return ResponseType('BookseriesUpdate: Virheellinen id.',
                            HttpResponseCode.BAD_REQUEST.value)

    bookseries = session.query(Bookseries)\
        .filter(Bookseries.id == bookseries_id).first()
    if not bookseries:
        app.logger.error('BookseriesUpdate: Unknown bookseries id.')
        return ResponseType('BookseriesUpdate: Tuntematon id.',
                            HttpResponseCode.BAD_REQUEST.value)

    if 'name' in data:
        if data['name'] == '':
            app.logger.error('BookseriesUpdate: Name cannot be empty.')
            return ResponseType('BookseriesUpdate: Nimi ei voi olla tyhjä.',
                                400)
        bs = session.query(Bookseries).filter(Bookseries.name == data['name'])\
            .filter(Bookseries.id != bookseries_id)\
            .first()
        if bs:
            app.logger.error('BookseriesCreate: Name already exists.')
            return ResponseType('BookseriesCreate: Nimi on jo olemassa.',
                                HttpResponseCode.BAD_REQUEST.value)
        if data['name'] != bookseries.name:
            old_values['Nimi'] = bookseries.name
            bookseries.name = data['name']

    if 'orig_name' in data:
        if data['orig_name'] != bookseries.orig_name:
            old_values['Alkukielinen nimi'] = bookseries.orig_name
            if data['orig_name'] == '':
                bookseries.orig_name = None
            else:
                bookseries.orig_name = data['orig_name']

    if 'important' in data:
        if data['important'] != bookseries.important:
            old_values['Tärkeä'] = bookseries.important
            bookseries.important = data['important']

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in BookseriesUpdate: ' + str(exp))
        return ResponseType('BookseriesUpdate: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_id = log_changes(session,
                         obj=bookseries,
                         old_values=old_values,
                         action='Päivitys')

    if log_id == 0:
        app.logger.error('BookseriesUpdate: Failed to log changes.')

    return ResponseType('OK', HttpResponseCode.OK.value)


def bookseries_delete(series_id: str) -> ResponseType:
    """
    Deletes a book series from the database.

    Parameters:
        series_id (str): The ID of the book series to be deleted.

    Returns:
        ResponseType: The response indicating the status of the deletion
                      operation.
    """
    session = new_session()
    old_values = {}

    bookseries_id = check_int(series_id,
                              negative_values=False,
                              zeros_allowed=False)
    if bookseries_id is None:
        app.logger.error('BookseriesDelete: Invalid id.')
        return ResponseType('BookseriesDelete: Virheellinen id.',
                            HttpResponseCode.BAD_REQUEST.value)

    bookseries = session.query(Bookseries)\
        .filter(Bookseries.id == bookseries_id).first()
    if not bookseries:
        app.logger.error('BookseriesDelete: Unknown bookseries id.')
        return ResponseType('BookseriesDelete: Tuntematon id.',
                            HttpResponseCode.BAD_REQUEST.value)
    old_values['Nimi'] = bookseries.name

    works = session.query(Work)\
        .filter(Work.bookseries_id == bookseries_id).all()
    if works:
        app.logger.error('BookseriesDelete: Bookseries has works.')
        return ResponseType('BookseriesDelete: Kirjasarjalla on teoksia.',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        log_id = log_changes(session,
                             obj=bookseries,
                             action='Poisto',
                             old_values=old_values)
        if log_id == 0:
            app.logger.error('BookseriesDelete: Failed to log changes.')
        session.delete(bookseries)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in BookseriesDelete: ' + str(exp))
        return ResponseType('BookseriesDelete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def add_bookseries(name: str) -> Union[int, None]:
    """
    Add a book series to the database.

    Parameters:
        name (str): The name of the book series.

    Returns:
        Union[int, None]: The ID of the newly added book series if successful,
                          None otherwise.
    """
    session = new_session()
    existing = session.query(Bookseries)\
        .filter(Bookseries.name == name)\
        .first()
    if existing:
        return existing.id
    try:
        bs = Bookseries(name=name)
        session.add(bs)
        session.commit()
        return bs.id
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in AddBookseries: ' + str(exp))
        return None
