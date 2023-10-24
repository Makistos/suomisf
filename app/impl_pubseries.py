""" Pubseries related functions. """
from typing import Union
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Pubseries
from app.model import (PubseriesSchema, PubseriesBriefSchema)
from app.impl import ResponseType
from app import app


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
        return ResponseType('FilterPubseries: Tietokantavirhe.', 400)
    try:
        schema = PubseriesBriefSchema(many=True)
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterPubseries schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterPubseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


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
        app.logger.error('Exception in GetPubseries: ' + str(exp))
        return ResponseType(f'GetPubseries: Tietokantavirhe. id={series_id}',
                            400)

    try:
        schema = PubseriesSchema()
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetPubseries schema error: ' + str(exp))
        return ResponseType('GetPubseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


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
        app.logger.error('Exception in ListPubseries: ' + str(exp))
        return ResponseType('ListPubseries: Tietokantavirhe.', 400)

    try:
        schema = PubseriesBriefSchema(many=True)
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListPubseries schema error: ' + str(exp))
        return ResponseType('ListPubseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


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
