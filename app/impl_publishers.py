""" Functions related to publishers. """
from typing import Any
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Publisher
from app.model import (PublisherBriefSchema,
                       PublisherSchema, PublisherBriefSchemaWEditions,
                       PublisherLink)
from app.impl import ResponseType, check_int, log_changes
from app import app


def filter_publishers(query: str) -> ResponseType:
    """
    Retrieves a list of publishers whose names match the given query.

    Parameters:
        query (str): The query string to match with the names of the
        publishers.

    Returns:
        ResponseType: The response object containing the list of matching
        publishers and the HTTP status code.
    """
    session = new_session()
    try:
        publishers = session.query(Publisher)\
            .filter(Publisher.name.ilike(query + '%'))\
            .order_by(Publisher.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterPublishers (query: {query}): ' + str(exp))
        return ResponseType('FilterPublishers: Tietokantavirhe.', 400)
    try:
        schema = PublisherBriefSchema(many=True)
        retval = schema.dump(publishers)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterPublishers schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterPublishers: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def get_publisher(pub_id: int) -> ResponseType:
    """
    Retrieves a publisher with the given ID from the database.

    Args:
        pub_id (int): The ID of the publisher.

    Returns:
        ResponseType: The response object containing the retrieved publisher if
                      successful, or an error message if there was a database
                      or schema error.
    """
    session = new_session()

    try:
        publisher = session.query(Publisher)\
            .filter(Publisher.id == pub_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetPublishers: ' + str(exp))
        return ResponseType(f'GetPublishers: Tietokantavirhe. id={pub_id}',
                            400)

    try:
        schema = PublisherSchema()
        retval = schema.dump(publisher)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetPublisher schema error: ' + str(exp))
        return ResponseType('GetPublisher: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def list_publishers() -> ResponseType:
    """
    Retrieves a list of all publishers from the database.

    Returns:
        ResponseType: The response object containing the list of publishers and
                      the status code.
    """
    session = new_session()

    try:
        publishers = session.query(Publisher).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListPublishers: ' + str(exp))
        return ResponseType(f'ListPublishers: Tietokantavirhe. id={id}', 400)

    try:
        schema = PublisherBriefSchemaWEditions(many=True)
        retval = schema.dump(publishers)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListPublishers schema error: ' + str(exp))
        return ResponseType('ListPublishers: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def publisher_add(params: Any) -> ResponseType:
    """
    Adds a new publisher to the database.

    Args:
        params (Any): The parameters for the request.

    Returns:
        ResponseType: The response object indicating the status of the
                      operation.
    """
    session = new_session()
    retval = ResponseType('OK', 200)

    publisher = Publisher()
    data = params['data']
    publisher.name = data['name']
    publisher.fullname = data['fullname']
    publisher.description = data['description']
    publisher.image_src = data['image_src']

    try:
        session.add(publisher)
    except SQLAlchemyError as exp:
        app.logger.error('Exception in publisher_add: ' + str(exp))
        return ResponseType('publisher_add: Tietokantavirhe.', 400)

    # Add links for publisher, requires ID.
    if 'links' in data:
        for link in data['links']:
            if 'link' not in link:
                app.logger.error('publisher_add: Link missing link.')
                return ResponseType('Linkin tiedot puutteelliset', 500)
            if link['link'] != '' and link['link'] is not None:
                if 'description' in link:
                    description = link['description']
                else:
                    description = ''
                if 'link' in link:
                    new_link = PublisherLink(publisher_id=publisher.id,
                                             description=description)
                    session.add(new_link)
    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error('Exception in publisher_add commit: ' + str(exp))
        return ResponseType('publisher_add: Tietokantavirhe.', 400)

    return retval


def publisher_update(params: Any) -> ResponseType:
    """
    Updates the publisher information based on the provided parameters.

    Args:
        params (Any): The parameters for the publisher update.

    Returns:
        ResponseType: The response indicating the success or failure of the
                      update.
    """
    session = new_session()
    retval = ResponseType('OK', 200)
    old_values = {}
    publisher: Any = None
    data = params['data']
    changed = params['changed']
    publisher_id = check_int(data['id'])

    if len(changed) == 0:
        return ResponseType('OK', 200)

    publisher = session.query(Publisher).filter(
        Publisher.id == publisher_id).first()

    if 'name' in changed:
        if changed['name']:
            if len(data['name']) == 0:
                app.logger.error('PublisherUpdate: Name is a required field')
                return ResponseType(
                    'PublisherUpdate: Nimi on pakollinen tieto.', 400)
            if data['name'] != publisher.name:
                similar = session.query(Publisher).filter(
                    Publisher.name == data['name']).all()
                if len(similar) > 0:
                    app.logger.error('PublisherUpdate: Name must be unique.')
                    return ResponseType(
                        'PublisherUpdate: Nimi on jo käytössä', 400)
            old_values['Nimi'] = publisher.name
            publisher.name = data['name']

    if 'fullname' in changed:
        if changed['fullname']:
            if len(data['fullname']) == 0:
                app.logger.error(
                    'PublisherUpdate: fullname is a required field')
                return ResponseType(
                    'PublisherUpdate: Nimi on pakollinen tieto.', 400)
            if data['fullname'] != publisher.fullname:
                similar = session.query(Publisher).filter(
                    Publisher.fullname == data['fullname']).all()
                if len(similar) > 0:
                    app.logger.error(
                        'PublisherUpdate: fullname must be unique.')
                    return ResponseType(
                        'PublisherUpdate: Nimi on jo käytössä', 400)
            old_values['Koko nimi'] = publisher.fullname
            publisher.fullname = data['fullname']

    if 'description' in changed:
        if changed['description']:
            old_values['Kuvaus'] = publisher.description
            publisher.description = data['description']

    log_changes(session=session, obj=publisher, action='Päivitys',
                old_values=old_values)

    try:
        session.add(publisher)
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in PublisherUpdate: {exp}.')
        return ResponseType('PublisherUpdate: Tietokantavirhe.', 400)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in PublisherUpdate commit: {exp}.')
        return ResponseType(
            'PublisherUpdate: Tietokantavirhe tallennettaessa.', 400)

    return retval
