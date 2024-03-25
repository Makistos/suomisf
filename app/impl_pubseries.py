""" Pubseries related functions. """
from typing import Any, Union
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Publisher, Pubseries
from app.model import (PubseriesSchema, PubseriesBriefSchema)
from app.impl import ResponseType
from app import app
from app.types import HttpResponseCode


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
    Creates a new pubseries based on the provided parameters.

    Args:
        params (Any): The input parameters for creating the pubseries.

    Returns:
        ResponseType: The response type containing the result of the operation.
    """
    session = new_session()
    data = params['data']
    pubseries = Pubseries()
    if 'name' in data:
        pubseries.name = data['name']
    else:
        app.logger.error('Pubseries name is required')
        return ResponseType('Sarjan nimi on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)
    ps = session.query(Pubseries)\
        .filter(Pubseries.name == pubseries.name)\
        .first()
    if ps:
        app.logger.error(f'Pubseries already exists: {pubseries.name}')
        return ResponseType(f'Sarja on jo olemassa: {pubseries.name}',
                            HttpResponseCode.BAD_REQUEST.value)

    if 'publisher_id' in data:
        pubseries.publisher_id = data['publisher_id']
    else:
        app.logger.error('Pubseries requires a publisher')
        return ResponseType('Kustantaja on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)

    publisher = session.query(Publisher)\
        .filter(Publisher.id == pubseries.publisher_id)\
        .first()

    if publisher is None:
        app.logger.error(f'Publisher does not exist: {pubseries.publisher_id}')
        return ResponseType('Kustantajaa ei ole olemassa: '
                            f'{pubseries.publisher_id}',
                            HttpResponseCode.BAD_REQUEST.value)

    pubseries.important = data['important'] if 'important' in data else False
    pubseries.image_attr = data['image_attr'] if 'image_attr' in data else None
    pubseries.image_src = data['image_src'] if 'image_src' in data else None

    try:
        session.add(pubseries)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(str(pubseries.id), HttpResponseCode.CREATED.value)


def pubseries_update(params: Any) -> ResponseType:
    """
    Updates a pubseries in the database based on the provided parameters.

    Args:
        params (Any): The input parameters for updating the pubseries.

    Returns:
        ResponseType: The response type containing the result of the operation.
    """
    session = new_session()
    data = params['data']
    if 'id' not in data:
        app.logger.error('Pubseries ID is required')
        return ResponseType('Sarjan ID on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        pubseries_id = int(data['id'])
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {data["id"]}.')
        return ResponseType(
            f'Virheellinen tunniste {data["id"]}.',
            HttpResponseCode.BAD_REQUEST.value)

    pubseries = session.query(Pubseries)\
        .filter(Pubseries.id == pubseries_id)\
        .first()
    if pubseries is None:
        return ResponseType(f'Sarjaa ei löydy: {pubseries_id}',
                            HttpResponseCode.BAD_REQUEST.value)

    if 'name' in data:
        pubseries.name = data['name']
    else:
        app.logger.error('Pubseries name is required')
        return ResponseType('Sarjan nimi on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)

    if 'publisher_id' in data:
        pub_id = data['publisher_id']
        try:
            publisher_id = int(pub_id)
        except (TypeError, ValueError):
            app.logger.error(f'Invalid publisher id {pub_id}.')
            return ResponseType(
                f'Virheellinen kustantajan tunniste {pub_id}.',
                HttpResponseCode.BAD_REQUEST.value)
    elif 'publisher' not in data:
        app.logger.error('Pubseries requires a publisher')
        return ResponseType('Kustantaja on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)
    elif 'id' not in data['publisher']:
        app.logger.error('Publisher ID is required')
        return ResponseType('Kustantajan tunniste on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)
    else:
        pub_id = data['publisher']['id']
        try:
            publisher_id = int(pub_id)
        except (TypeError, ValueError):
            app.logger.error(f'Invalid publisher id {pub_id}.')
            return ResponseType(
                f'Virheellinen kustantajan tunniste {pub_id}.',
                HttpResponseCode.BAD_REQUEST.value)

    publisher = session.query(Publisher)\
        .filter(Publisher.id == publisher_id)\
        .first()
    if publisher is None:
        app.logger.error(f'Publisher not found: {publisher_id}')
        return ResponseType(f'Kustantajaa ei löydy: {publisher_id}',
                            HttpResponseCode.BAD_REQUEST.value)
    pubseries.publisher_id = publisher_id

    if 'important' in data:
        pubseries.important = data['important']
    if 'image_attr' in data:
        pubseries.image_attr = data['image_attr']
    if 'image_src' in data:
        pubseries.image_src = data['image_src']

    try:
        session.add(pubseries)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

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
