""" Functions related to publishers. """
from typing import Any, Union, Dict, List
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl_links import links_have_changed
from app.impl_logs import log_changes
from app.model_publisher import PublisherPageSchema
from app.route_helpers import new_session
from app.orm_decl import Publisher
from app.model import (PublisherBriefSchema,
                       PublisherBriefSchemaWEditions,
                       PublisherLink)
from app.impl import ResponseType, check_int, get_join_changes
from app import app
from app.types import HttpResponseCode


def _save_links(
        session: Any,
        links: List[Dict[str, str]],
        publisher_id: int,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Save links to the database for a given publisher.

    Args:
        session: The database session.
        links: A list of links to be saved.
        publisher_id: Id of the publisher for whom the links are being saved.

    Returns:
        Union[ResponseType, None]: The response type or None.
    """
    existing_links = session.query(PublisherLink).filter(
        PublisherLink.publisher_id == publisher_id).all()
    (to_add, to_remove) = get_join_changes(
        [x.link for x in existing_links],
        [x['link'] for x in links])  # type: ignore
    _ = [session.delete(link) for link in existing_links
         if link.link in to_remove]
    # if len(existing_links) > 0:
    #     for link in existing_links:
    #         session.delete(link)
    new_links = [x for x in links if x['link'] != '']

    for link in new_links:
        if 'link' not in link:
            app.logger.error('Link missing link.')
            return ResponseType('Linkin tiedot puutteelliset',
                                HttpResponseCode.BAD_REQUEST.value)
        if link['link'] != '' and link['link'] is not None:
            if 'description' in link:
                description = link['description']
            else:
                description = ''
            if 'link' in link:
                new_link = PublisherLink(publisher_id=publisher_id,
                                         link=link['link'],
                                         description=description)
                session.add(new_link)

    if old_values:
        old_values['Linkit'] = '-'.join(str(x) for x in to_remove)
        old_values['Linkit'] = '+'.join(str(x) for x in to_add)

    return None


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
            f'Query: {query}: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = PublisherBriefSchema(many=True)
        retval = schema.dump(publishers)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Query: {query}: {exp}')
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_publisher(pub_id: int) -> ResponseType:
    """
    Retrieves a publisher with the given ID from the database.

    Args:
        pub_id (int): The ID of the publisher.

    Returns:
        ResponseType: The response object containing the retrieved publisher if
                      successful, or an error message if there was a database
                      or schema error.
        publisher_id_not_found: Try to get a publisher that doesn't exist
    """
    session = new_session()

    try:
        publisher = session.query(Publisher)\
            .filter(Publisher.id == pub_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'Tietokantavirhe. id={pub_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not publisher:
        return ResponseType(f'Kustantajaa {pub_id} ei ole olemassa.',
                            HttpResponseCode.NOT_FOUND.value)
    try:
        schema = PublisherPageSchema()
        retval = schema.dump(publisher)
    except exceptions.MarshmallowError as exp:
        app.logger.error(exp)
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def list_publishers() -> ResponseType:
    """
    Retrieves a list of all publishers from the database.

    Returns:
        ResponseType: The response object containing the list of publishers and
                      the status code.
    """
    session = new_session()

    try:
        publishers = session.query(Publisher).order_by(Publisher.name).all()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType(f'Tietokantavirhe. id={id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = PublisherBriefSchemaWEditions(many=True)
        retval = schema.dump(publishers)
    except exceptions.MarshmallowError as exp:
        app.logger.error(exp)
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


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

    publisher = Publisher()
    data = params['data']
    if 'name' not in data or data['name'] == '' or data['name'] is None:
        app.logger.error('Publisher name missing.')
        return ResponseType('Kustantajan nimi puuttuu',
                            HttpResponseCode.BAD_REQUEST.value)
    if ('fullname' not in data or data['fullname'] == '' or
            data['fullname'] is None):
        app.logger.error('Publisher fullname missing.')
        return ResponseType('Kustantajan koko nimi puuttuu',
                            HttpResponseCode.BAD_REQUEST.value)
    similar = session.query(Publisher) \
        .filter(or_(Publisher.name == data['name'],
                    Publisher.fullname == data['fullname']))\
        .all()
    if len(similar) > 0:
        app.logger.error(f'Publisher name or fullname must be unique: {data}.')
        return ResponseType('Nimi tai koko nimi on jo käytössä',
                            HttpResponseCode.BAD_REQUEST.value)

    publisher.name = data['name']
    publisher.fullname = data['fullname']
    publisher.description = data['description'] if 'description' in data \
        else None
    publisher.image_src = data['image_src'] if 'image_src' in data \
        else None
    publisher.image_attr = data['image_attr'] if 'image_attr' in data \
        else None

    try:
        session.add(publisher)
        session.flush()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Add links for publisher, requires ID.
    if 'links' in data:
        retval = _save_links(session=session,
                             links=data['links'],
                             publisher_id=publisher.id,
                             old_values=None)
        if retval:
            return retval

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(str(publisher.id), HttpResponseCode.CREATED.value)


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
    old_values = {}
    data = params['data']

    if 'id' not in data:
        app.logger.error('ID missing.')
        return ResponseType('ID on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)

    publisher_id = check_int(data['id'])

    if not publisher_id:
        app.logger.error('ID missing.')
        return ResponseType('ID on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)

    publisher = session.query(Publisher).filter(
        Publisher.id == publisher_id).first()
    if not publisher:
        app.logger.error('Publisher not found.')
        return ResponseType('Kustantaja ei ole olemassa',
                            HttpResponseCode.NOT_FOUND.value)

    if 'name' in data and data['name'] != publisher.name:
        if len(data['name']) == 0 or data['name'] is None:
            app.logger.error('Name is a required field')
            return ResponseType('Nimi on pakollinen tieto',
                                HttpResponseCode.BAD_REQUEST.value)
        similar = session.query(Publisher).filter(
            Publisher.name == data['name'],
            Publisher.id != publisher_id).all()
        if len(similar) > 0:
            app.logger.error('Name must be unique.')
            return ResponseType('Nimi on jo käytössä',
                                HttpResponseCode.BAD_REQUEST.value)
        old_values['Nimi'] = publisher.name
        publisher.name = data['name']

    if 'fullname' in data and data['fullname'] != publisher.fullname:
        if len(data['fullname']) == 0 or data['fullname'] is None:
            app.logger.error(
                'Fullname is a required field')
            return ResponseType(
                'Koko nimi on pakollinen tieto.',
                HttpResponseCode.BAD_REQUEST.value)
        if data['fullname'] != publisher.fullname:
            similar = session.query(Publisher).filter(
                Publisher.fullname == data['fullname'],
                Publisher.id != publisher_id).all()
            if len(similar) > 0:
                app.logger.error(
                    'Fullname must be unique.')
                return ResponseType(
                    'Koko nimi on jo käytössä',
                    HttpResponseCode.BAD_REQUEST.value)
        old_values['Koko nimi'] = publisher.fullname
        publisher.fullname = data['fullname']

    if 'description' in data and data['description'] != publisher.description:
        old_values['Kuvaus'] = publisher.description
        publisher.description = data['description']

    if 'image_src' in data and data['image_src'] != publisher.image_src:
        old_values['Kuva'] = publisher.image_src
        publisher.image_src = data['image_src']

    if 'image_attr' in data and data['image_attr'] != publisher.image_attr:
        old_values['Kuvan lähde'] = publisher.image_attr
        publisher.image_attr = data['image_attr']

    if 'links' in data and links_have_changed(publisher.links, data['links']):
        retval = _save_links(session=session,
                             links=data['links'],
                             publisher_id=publisher.id,
                             old_values=old_values)
        if retval:
            return retval

    log_changes(session=session, obj=publisher, action='Päivitys',
                old_values=old_values)

    try:
        session.add(publisher)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def publisher_delete(pub_id: int) -> ResponseType:
    """
    Deletes the publisher with the given ID from the database.

    If publisher does not exist, function still returns 200.

    Args:
        pub_id (int): The ID of the publisher to delete.

    Returns:
        ResponseType: The response indicating the success or failure of the
                      deletion.
    """
    session = new_session()
    try:
        session.query(PublisherLink)\
            .filter(PublisherLink.publisher_id == pub_id)\
            .delete()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe poistettaessa linkkejä.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    publisher = session.query(Publisher).filter(Publisher.id == pub_id).first()

    if publisher:
        try:
            session.delete(publisher)
            session.commit()
        except SQLAlchemyError as exp:
            session.rollback()
            app.logger.error(exp)
            return ResponseType('Tietokantavirhe poistettaessa.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    else:
        return ResponseType('Kustantajaa ei ole olemassa).',
                            HttpResponseCode.NOT_FOUND.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def add_publisher(session: Any, name: str) -> Union[int, None]:
    """
    Adds a publisher to the database if it doesn't already exist, and returns
    the publisher's ID.

    Args:
        session (Any): The database session.
        name (str): The name of the publisher to add.

    Returns:
        Union[int, None]: The ID of the publisher if it already exists, or None
        if an exception occurs.
    """

    publisher = session.query(Publisher).filter(Publisher.name == name).first()
    if publisher:
        return publisher.id

    publisher = Publisher(name=name, fullname=name)
    try:
        session.add(publisher)
        session.flush()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in AddPublisher: {exp}.')
        return None

    return publisher.id
