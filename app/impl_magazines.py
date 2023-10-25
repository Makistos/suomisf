""" Magazine related functions. """
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import (Magazine)
from app.model import (MagazineSchema)
from app.impl import ResponseType
from app.model import MagazineBriefSchema
from app import app


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
        app.logger.error(f'Exception in ListMagazines: {exp}')
        return ResponseType('ListMagazines: Tietokantavirhe.', 400)

    # retval = []
    # for magazine in magazines:
    #     retval.append({'id': magazine.id, 'name': magazine.name})
    try:
        schema = MagazineBriefSchema(many=True)
        retval = schema.dump(magazines)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'ListMagazines schema error: {exp}')
        return ResponseType('ListMagazines: Skeemavirhe.', 400)
    return ResponseType(retval, 200)
