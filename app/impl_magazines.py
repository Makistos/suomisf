""" Magazine related functions. """
import html
from typing import Any, Dict, Union
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl_helpers import str_differ
from app.impl_logs import log_changes
from app.impl_tags import tags_have_changed
from app.route_helpers import new_session
from app.orm_decl import (Magazine, MagazineTag, MagazineType, Publisher, Tag)
from app.model import (MagazineSchema, MagazineTypeSchema)
from app.impl import ResponseType
from app.model import MagazineBriefSchema
from app import app
from app.types import HttpResponseCode


def _set_description(
        magazine: Magazine,
        data: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Set the description of a magazine.

    Args:
        magazine (Magazine): The work object to set the description for.
        data (Any): The data containing the new description.
        old_values (Union[Dict[str, Any], None]): The old values of the
        magazine, if available.

    Returns:
        Union[ResponseType, None]: The response type if there was an error,
                                   otherwise None.
    """
    try:
        if data['description']:
            html_text = html.unescape(data['description'])
        else:
            html_text = ''
    except (TypeError) as exp:
        app.logger.error('WorkSave: Failed to unescape html: ' +
                         data["description"] + '.' + str(exp))
        return ResponseType('Kuvauksen html-muotoilu epäonnistui',
                            HttpResponseCode.BAD_REQUEST.value)
    if str_differ(html_text, magazine.description):
        if old_values is not None:
            old_values['Kuvaus'] = (magazine.description[0:200]
                                    if magazine.description else '')
        magazine.description = html_text
    return None


def _set_tags(
        session: Any, magazine: Magazine, tags: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Sets the tags for a given work.

    Args:
        session (Any): The session object for the database connection.
        work (Work): The work object to set the tags for.
        data (Any): The data object containing the tags information.
        old_values (Union[Dict[str, Any], None]): The old values of the work
        object.

    Returns:
        Union[ResponseType, None]: The response type if there is an error,
                                   otherwise None.
    """
    if tags_have_changed(magazine.tags, tags):
        # Check if we need to create new tags
        try:
            for tag in tags:
                if tag['id'] == 0:
                    already_exists = session.query(Tag)\
                        .filter(Tag.name == tag['name'])\
                        .first()
                    if not already_exists:
                        new_tag = Tag(name=tag['name'], type_id=1)
                        session.add(new_tag)
                        session.flush()
                        tag['id'] = new_tag.id
                    else:
                        tag['id'] = already_exists.id
        except SQLAlchemyError as exp:
            app.logger.error(f'{exp}')
            return ResponseType('Uusia asiasanoja ei saatu talletettua.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)

        existing_tags = session.query(MagazineTag)\
            .filter(MagazineTag.work_id == magazine.id)\
            .all()
        # (to_add, to_remove) = get_join_changes(
        #     [x.tag_id for x in existing_tags],
        #     [x['id'] for x in data['tags']])
        if len(existing_tags) > 0:
            for tag in existing_tags:
                session.delete(tag)
        for tag in tags:
            st = MagazineTag(tag_id=tag['id'], magazine_id=magazine.id)
            session.add(st)
        old_tags = session.query(Tag.name)\
            .filter(Tag.id.in_([x.tag_id for x in existing_tags]))\
            .all()
        if old_values is not None:
            old_values['Asiasanat'] = ','.join([str(x[0]) for x in old_tags])

    return None


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
    if ('publisher' in magazine and
            magazine['publisher'] is not None and
            'id' in magazine['publisher']):
        try:
            pub_id = int(magazine['publisher']['id'])
        except (ValueError, TypeError):
            app.logger.error(
                f'Invalid publisher id: {magazine["publisher"]["id"]}.')
            return ResponseType('Virheellinen kustantajan id: '
                                f'{magazine["publisher"]["id"]} .',
                                HttpResponseCode.BAD_REQUEST.value)
        try:
            publisher = session.query(Publisher)\
                .filter(Publisher.id == pub_id)\
                .first()
        except SQLAlchemyError as exp:
            app.logger.error(exp)
            return ResponseType('Tietokantavirhe.',
                                HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        if not publisher:
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
            type_int = int(magazine['type']['id'])
        except (ValueError, TypeError):
            app.logger.error(f'Invalid type: {magazine["type"]}.')
            return ResponseType('Virheellinen tyyppi: '
                                f'{magazine["type"]} .',
                                HttpResponseCode.BAD_REQUEST.value)
        new_magazine.type_id = type_int

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

    if 'name' in magazine_data and magazine_data['name'] != magazine.name:
        old_values['name'] = magazine.name
        magazine.name = magazine_data['name']
    if 'publisher' in magazine_data and \
            magazine_data['publisher']['id'] != magazine.publisher_id:
        try:
            pub_id = int(magazine_data['publisher']['id'])
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
            magazine.publisher_id = magazine_data['publisher']['id']
            old_values['publisher'] = publisher.name
        else:
            app.logger.error(f'Publisher {pub_id} not found.')
            return ResponseType(f'Kustantajaa {pub_id} ei loydy.',
                                HttpResponseCode.BAD_REQUEST.value)
    if 'description' in magazine_data:
        result = _set_description(magazine, magazine_data,  old_values)
        if result:
            return result
    if 'link' in magazine_data and str_differ(magazine_data['link'],
                                              magazine.link):
        magazine.link = magazine_data['link']
    if 'issn' in magazine_data and str_differ(magazine_data['issn'],
                                              magazine.issn):
        magazine.issn = magazine_data['issn']
    if 'type' in magazine_data and \
            magazine_data['type']['id'] != magazine.type_id:
        try:
            type_int = int(magazine_data['type']['id'])
        except ValueError:
            app.logger.error('Type must be integer: '
                             f'{magazine_data["type"]}.')
            return ResponseType('Tyyppi on virheellinen: '
                                f'{magazine_data["type"]}.',
                                HttpResponseCode.BAD_REQUEST.value)
        magazine.type_id = type_int

    if 'tags' in magazine_data:
        result = _set_tags(session, magazine, magazine_data['tags'],
                           old_values)
        if result:
            return result

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


def get_magazine_types() -> ResponseType:
    """
    Retrieves a list of magazine types.

    Returns:
        ResponseType: The response containing the list of magazine types.
    """

    session = new_session()
    try:
        types = session.query(MagazineType).all()
    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = MagazineTypeSchema(many=True)
        retval = schema.dump(types)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}')
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)
