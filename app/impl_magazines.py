""" Magazine related functions. """
from typing import Any, Dict
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl_logs import log_changes
from app.route_helpers import new_session
from app.orm_decl import (Magazine, Publisher)
from app.model import (MagazineSchema)
from app.impl import ResponseType
from app.model import MagazineBriefSchema
from app import app
from app.types import HttpResponseCode


def get_magazine(magazine_id: int) -> ResponseType:
    """
    Retrieves a magazine from the database based on the given ID.

    Args:
        id (int): The ID of the magazine to retrieve.

    Returns:
        ResponseType: The response containing the retrieved magazine.

    Raises:
        SQLAlchemyError: If there is an error executing the database query.
        exceptions.MarshmallowError: If there is an error serializing the
                                     magazine object.

    """
    session = new_session()

    try:
        magazine = session.query(Magazine)\
            .filter(Magazine.id == magazine_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in GetMagazine: { exp}')
        return ResponseType('GetMagazine: Tietokantavirhe.', 400)

    if not magazine:
        return ResponseType('Lehteä ei ole olemassa.',
                            HttpResponseCode.NOT_FOUND.value)

    try:
        schema = MagazineSchema()
        retval = schema.dump(magazine)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'GetMagazine schema error: {exp}')
        return ResponseType('GetMagazine: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def list_magazines() -> ResponseType:
    """
    Retrieves a list of magazines from the database.

    Returns:
        ResponseType: The response containing the list of magazines.

    Raises:
        SQLAlchemyError: If there is an error with the database query.
        exceptions.MarshmallowError: If there is an error with the schema.
    """
    session = new_session()
    try:
        magazines = session.query(Magazine).all()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.', 400)

    try:
        schema = MagazineBriefSchema(many=True)
        retval = schema.dump(magazines)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}')
        return ResponseType('Skeemavirhe.', 400)
    return ResponseType(retval, 200)


def add_magazine(params: Dict[str, Any]) -> ResponseType:
    """
    Adds a new magazine to the database.

    Args:
        magazine_data (dict): The magazine data to add.

    Returns:
        ResponseType: The response object containing the added magazine.

    Raises:
        SQLAlchemyError: If there is an error executing the database query.
        exceptions.MarshmallowError: If there is an error serializing the
                                     magazine object.
    """
    session = new_session()
    magazine = params['data']

    new_magazine = Magazine()
    if 'name' not in magazine:
        app.logger.error('Missing name.')
        return ResponseType('Name missing.',
                            HttpResponseCode.BAD_REQUEST.value)
    new_magazine.name = magazine['name']
    if 'publisher_id' in magazine:
        try:
            pub_id = int(magazine['publisher_id'])
        except (ValueError, TypeError):
            app.logger.error(
                f'Invalid publisher id: {magazine["publisher_id"]}.')
            return ResponseType('Virheellinen kustantajan id: '
                                f'{magazine["publisher_id"]} .',
                                HttpResponseCode.BAD_REQUEST.value)
        try:
            publisher = session.query(Publisher)\
                .filter(Publisher.id == pub_id)\
                .first()
        except SQLAlchemyError as exp:
            app.logger.error(exp)
            return ResponseType('Tietokantavirhe.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        if publisher:
            magazine.publisher_id = magazine['publisher_id']
        else:
            app.logger.error(f'Publisher {pub_id} not found.')
            return ResponseType(f'Kustantajaa {pub_id} ei loydy.',
                                HttpResponseCode.BAD_REQUEST.value)
        new_magazine.publisher_id = pub_id
    new_magazine.description = magazine['description'] if 'description' in \
        magazine else None
    new_magazine.link = magazine['link'] if 'link' in magazine else None
    new_magazine.issn = magazine['issn'] if 'issn' in magazine else None
    if 'type' in magazine:
        try:
            type_int = int(magazine['type'])
        except (ValueError, TypeError):
            app.logger.error(f'Invalid type: {magazine["type"]}.')
            return ResponseType('Virheellinen tyyppi: '
                                f'{magazine["type"]} .',
                                HttpResponseCode.BAD_REQUEST.value)
        if type_int < 0 or type_int > 1:
            app.logger.error('Type must be 0 or 1: '
                             f'{magazine["type"]}.')
            return ResponseType('Tyyppi on virheellinen: '
                                f'{magazine["type"]}.',
                                HttpResponseCode.BAD_REQUEST.value)
        new_magazine.type = type_int

    try:
        session.add(new_magazine)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session, obj=new_magazine, action="Uusi")

    return ResponseType(str(new_magazine.id), HttpResponseCode.CREATED.value)


def update_magazine(params: Dict[str, Any]) -> ResponseType:
    """
    Updates an existing magazine in the database.

    Args:
        magazine_data (dict): The magazine data to update.

    Returns:
        ResponseType: The response object containing the updated magazine.

    Raises:
        SQLAlchemyError: If there is an error executing the database query.
        exceptions.MarshmallowError: If there is an error serializing the
                                     magazine object.
    """
    session = new_session()
    old_values = {}
    magazine_data = params['data']

    try:
        magazine_id = int(magazine_data['id'])
    except ValueError:
        app.logger.error('Magazine id must be integer: '
                         f'{magazine_data["id"]}.')
        return ResponseType('Magazine id on virheellinen: '
                            f'{magazine_data["id"]}.',
                            HttpResponseCode.BAD_REQUEST.value)
    try:
        magazine = session.query(Magazine)\
            .filter(Magazine.id == magazine_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if 'name' in magazine_data:
        old_values['name'] = magazine.name
        magazine.name = magazine_data['name']
    if 'publisher_id' in magazine_data:
        try:
            pub_id = int(magazine_data['publisher_id'])
        except ValueError:
            app.logger.error('Publisher id must be integer: '
                             f'{magazine_data["publisher_id"]}.')
            return ResponseType('Kustantajan id on virheellinen: '
                                f'{magazine_data["publisher_id"]}.',
                                HttpResponseCode.BAD_REQUEST.value)
        try:
            publisher = session.query(Publisher)\
                .filter(Publisher.id == pub_id)\
                .first()
        except SQLAlchemyError as exp:
            app.logger.error(exp)
            return ResponseType('Tietokantavirhe.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        if publisher:
            magazine.publisher_id = magazine_data['publisher_id']
            old_values['publisher'] = publisher.name
        else:
            app.logger.error(f'Publisher {pub_id} not found.')
            return ResponseType(f'Kustantajaa {pub_id} ei loydy.',
                                HttpResponseCode.BAD_REQUEST.value)
    if 'description' in magazine_data:
        magazine.description = magazine_data['description']
    if 'link' in magazine_data:
        magazine.link = magazine_data['link']
    if 'issn' in magazine_data:
        magazine.issn = magazine_data['issn']
    if 'type' in magazine_data:
        try:
            type_int = int(magazine_data['type'])
        except ValueError:
            app.logger.error('Type must be integer: '
                             f'{magazine_data["type"]}.')
            return ResponseType('Tyyppi on virheellinen: '
                                f'{magazine_data["type"]}.',
                                HttpResponseCode.BAD_REQUEST.value)
        if type_int < 0 or type_int > 1:
            app.logger.error('Type must be 0 or 1: '
                             f'{magazine_data["type"]}.')
            return ResponseType('Tyyppi on virheellinen: '
                                f'{magazine_data["type"]}.',
                                HttpResponseCode.BAD_REQUEST.value)
        magazine.type = magazine_data['type']

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.BAD_REQUEST.value)

    log_changes(session, obj=magazine, action="Paivitys")

    return ResponseType('OK', HttpResponseCode.OK.value)


def delete_magazine(magazine_id: int) -> ResponseType:
    """
    Deletes a magazine from the database based on the given ID.

    Args:
        id (int): The ID of the magazine to delete.

    Returns:
        ResponseType: The response type indicating the success or failure of
                      the deletion.

    Raises:
        SQLAlchemyError: If there is an error executing the database query.
    """
    session = new_session()
    try:
        session.query(Magazine).filter(Magazine.id == magazine_id).delete()
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)
