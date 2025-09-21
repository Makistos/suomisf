""" Pubseries related functions. """
from typing import Any, Union
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Pubseries
from app.model import (PubseriesSchema, PubseriesBriefSchema)
from app.impl import ResponseType, check_int
from app import app
from app.types import HttpResponseCode
from app.impl_links import links_have_changed
from app.impl_logs import log_changes
from app.route_helpers import get_join_changes
from app.orm_decl import PubseriesLink


def filter_pubseries(query: str) -> ResponseType:
    """
    Filters the pubseries based on the provided query.

    Args:
        query (str): The query string to filter the pubseries by.

    Returns:
        ResponseType: The response containing the filtered pubseries.

    Raises:
        SQLAlchemyError: If there is an error querying the database.
        exceptions.MarshmallowError: If there is an error with the schema.

    Examples:
        >>> filter_pubseries('query')
        ResponseType(...)
    """
    session = new_session()
    try:
        pubseries = session.query(Pubseries)\
            .filter(Pubseries.name.ilike(query + '%'))\
            .order_by(Pubseries.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterPubseries (query: {query}): ' + str(exp))
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = PubseriesBriefSchema(many=True)
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'Schema error (query: {query}): ' + str(exp))
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_pubseries(series_id: int) -> ResponseType:
    """
    Retrieves a single pubseries from the database based on the given series
    ID.

    Parameters:
        series_id (int): The ID of the pubseries to retrieve.

    Returns:
        ResponseType: The response object containing the retrieved pubseries
        data if successful, or an error message if unsuccessful.
    """
    session = new_session()

    try:
        pubseries = session.query(Pubseries).filter(
            Pubseries.id == series_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'Tietokantavirhe. id={series_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    if pubseries is None:
        return ResponseType(f'Sarjaa ei löydy. id={series_id}',
                            HttpResponseCode.NOT_FOUND.value)
    try:
        schema = PubseriesSchema()
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(exp)
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def list_pubseries() -> ResponseType:
    """
    Retrieves a list of all pubseries from the database.

    Returns:
        ResponseType: The response object containing the list of pubseries and
                      the HTTP status code.
    """
    session = new_session()

    try:
        pubseries = session.query(Pubseries).all()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = PubseriesBriefSchema(many=True)
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('Schema error: ' + str(exp))
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def pubseries_create(params: Any) -> ResponseType:
    """
    Creates a new publication series with the given parameters.

    Args:
        params (Any): The parameters for creating the publication series.

    Returns:
        ResponseType: The response containing the ID of the created publication
                      series or an error message.

    Raises:
        SQLAlchemyError: If there is an error during the database transaction.
    """
    session = new_session()
    data = params['data']

    if 'name' not in data:
        app.logger.error('PubseriesCreate: Name is missing.')
        return ResponseType('PubseriesCreate: Nimi puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)

    ps = session.query(Pubseries)\
        .filter(Pubseries.name == data['name']).first()
    if ps:
        app.logger.error('PubseriesCreate: Name already exists.')
        return ResponseType('PubseriesCreate: Nimi on jo olemassa.',
                            HttpResponseCode.BAD_REQUEST.value)

    pubseries = Pubseries()
    pubseries.name = data['name']

    if 'description' in data:
        if data['description'] == '':
            description = None
        else:
            description = data['description']
        pubseries.description = description

    try:
        session.add(pubseries)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in PubseriesCreate: ' + str(exp))
        return ResponseType('PubseriesCreate: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if 'links' in data:
        new_links = [x for x in data['links'] if x['link'] != '']
        for link in new_links:
            if link['link'] != '':
                new_link = PubseriesLink(pubseries_id=pubseries.id,
                                         link=link['link'],
                                         description=link['description'])
                session.add(new_link)
        try:
            session.commit()
        except SQLAlchemyError as exp:
            session.rollback()
            app.logger.error('Exception in PubseriesCreate (links): '
                             + str(exp))
            return ResponseType('Tietokantavirhe.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session, obj=pubseries, action='Uusi')

    return ResponseType(str(pubseries.id), HttpResponseCode.CREATED.value)


def pubseries_update(params: Any) -> ResponseType:
    """
    Updates a publication series with the given parameters.

    Args:
        params (Any): The parameters for the update.

    Returns:
        ResponseType: The response indicating the success or failure of the
                      update.
    """
    session = new_session()
    data = params['data']
    old_values = {}

    pubseries_id = check_int(data['id'],
                             negative_values=False,
                             zeros_allowed=False)
    if pubseries_id is None:
        app.logger.error('PubseriesUpdate: Invalid id.')
        return ResponseType('PubseriesUpdate: Virheellinen id.',
                            HttpResponseCode.BAD_REQUEST.value)

    pubseries = session.query(Pubseries)\
        .filter(Pubseries.id == pubseries_id).first()
    if not pubseries:
        app.logger.error('PubseriesUpdate: Unknown pubseries id.')
        return ResponseType('PubseriesUpdate: Tuntematon id.',
                            HttpResponseCode.BAD_REQUEST.value)

    if 'name' in data:
        if data['name'] == '':
            app.logger.error('PubseriesUpdate: Name cannot be empty.')
            return ResponseType('PubseriesUpdate: Nimi ei voi olla tyhjä.',
                                HttpResponseCode.BAD_REQUEST.value)
        ps = session.query(Pubseries).filter(Pubseries.name == data['name'])\
            .filter(Pubseries.id != pubseries_id)\
            .first()
        if ps:
            app.logger.error('PubseriesUpdate: Name already exists.')
            return ResponseType('PubseriesUpdate: Nimi on jo olemassa.',
                                HttpResponseCode.BAD_REQUEST.value)
        if data['name'] != pubseries.name:
            old_values['Nimi'] = pubseries.name
            pubseries.name = data['name']

    if 'description' in data:
        if data['description'] != pubseries.description:
            old_values['Kuvaus'] = pubseries.description
            if data['description'] == '':
                pubseries.description = None
            else:
                pubseries.description = data['description']

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in PubseriesUpdate: ' + str(exp))
        return ResponseType('PubseriesUpdate: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if 'links' in data:
        new_links = [x for x in data['links'] if x['link'] != '']
        if links_have_changed(pubseries.links, new_links):
            existing_links = session.query(PubseriesLink)\
                .filter(PubseriesLink.pubseries_id == pubseries.id).all()
            (to_add, to_remove) = get_join_changes(
                [x.link for x in existing_links],
                [x['link'] for x in data['links']])
            for link in existing_links:
                session.delete(link)
            # Add new links
            for link in new_links:
                if link['link'] != '':
                    new_link = PubseriesLink(pubseries_id=pubseries_id,
                                             link=link['link'],
                                             description=link['description'])
                    session.add(new_link)
            old_values['Linkit'] = '-'.join([str(x) for x in to_add])
            old_values['Linkit'] += '+'.join([str(x) for x in to_remove])
            try:
                session.commit()
            except SQLAlchemyError as exp:
                session.rollback()
                app.logger.error('Exception in PubseriesUpdate (links): '
                                 + str(exp))
                return ResponseType(
                    'PubseriesUpdate: Tietokantavirhe.',
                    HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_id = log_changes(session,
                         obj=pubseries,
                         old_values=old_values,
                         action='Päivitys')

    if log_id == 0:
        app.logger.error('PubseriesUpdate: Failed to log changes.')

    return ResponseType('OK', HttpResponseCode.OK.value)


def pubseries_delete(pubseries_id: int) -> ResponseType:
    """
    Deletes a pubseries from the database based on the provided ID.

    Args:
        pubseries_id (int): The ID of the pubseries to delete.

    Returns:
        ResponseType: The response type containing the result of the operation.
    """
    session = new_session()
    pubseries = session.query(Pubseries)\
        .filter(Pubseries.id == pubseries_id)\
        .first()
    if pubseries is None:
        return ResponseType(f'Sarjaa ei löydy: {pubseries_id}',
                            HttpResponseCode.NOT_FOUND.value)
    session.delete(pubseries)
    session.commit()
    return ResponseType('OK', HttpResponseCode.OK.value)


def add_pubseries(name: str, publisher_id: int) -> Union[int, None]:
    """
    Adds a new Pubseries with the given name and publisher ID to the database.

    Parameters:
        name (str): The name of the Pubseries.
        publisher_id (int): The ID of the publisher associated with the
                            Pubseries.

    Returns:
        Union[int, None]: The ID of the added Pubseries if successful, None
                          otherwise.
    """
    session = new_session()
    try:
        pubseries = Pubseries(name=name, publisher_id=publisher_id)
        session.add(pubseries)
        session.commit()
        return pubseries.id
    except SQLAlchemyError as exp:
        app.logger.error('Exception in AddPubseries: ' + str(exp))
        return None
