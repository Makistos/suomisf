from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Pubseries
from app.model import (PubseriesSchema, PubseriesBriefSchema)
from app.impl import ResponseType
from app import app


def GetPubseries(id: int) -> ResponseType:
    session = new_session()

    try:
        pubseries = session.query(Pubseries).filter(
            Pubseries.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetPubseries: ' + str(exp))
        return ResponseType(f'GetPubseries: Tietokantavirhe. id={id}', 400)

    try:
        schema = PubseriesSchema()
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetPubseries schema error: ' + str(exp))
        return ResponseType('GetPubseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ListPubseries() -> ResponseType:
    session = new_session()

    try:
        pubseries = session.query(Pubseries).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListPubseries: ' + str(exp))
        return ResponseType(f'ListPubseries: Tietokantavirhe.', 400)

    try:
        schema = PubseriesBriefSchema(many=True)
        retval = schema.dump(pubseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListPubseries schema error: ' + str(exp))
        return ResponseType('ListPubseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)
