import json
from typing import Dict, Tuple
from app.route_helpers import new_session
from app.orm_decl import (Magazine)
from app.model import (MagazineSchema)
from app.impl import ResponseType
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app import app
from app.model import MagazineBriefSchema


def GetMagazine(id: int) -> ResponseType:
    session = new_session()

    try:
        magazine = session.query(Magazine)\
            .filter(Magazine.id == id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetMagazine: ' + str(exp))
        return ResponseType(f'GetMagazine: Tietokantavirhe.', 400)

    try:
        schema = MagazineSchema()
        retval = schema.dump(magazine)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetMagazine schema error: ' + str(exp))
        return ResponseType('GetMagazine: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ListMagazines() -> ResponseType:
    session = new_session()
    try:
        magazines = session.query(Magazine).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListMagazines: ' + str(exp))
        return ResponseType(f'ListMagazines: Tietokantavirhe.', 400)

    # retval = []
    # for magazine in magazines:
    #     retval.append({'id': magazine.id, 'name': magazine.name})
    try:
        schema = MagazineBriefSchema(many=True)
        retval = schema.dump(magazines)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListMagazines schema error: ' + str(exp))
        return ResponseType('ListMagazines: Skeemavirhe.', 400)
    return ResponseType(retval, 200)
