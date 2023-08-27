from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Pubseries
from app.model import (PubseriesSchema, PubseriesBriefSchema)
from app.impl import ResponseType
from app import app
from typing import Any, Union


def FilterPubseries(query: str) -> ResponseType:
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

def AddPubseries(name: str, publisher_id: int) -> Union[int, None]:
    session = new_session()
    try:
        pubseries = Pubseries(name=name, publisher_id=publisher_id)
        session.add(pubseries)
        session.commit()
        return pubseries.id
    except SQLAlchemyError as exp:
        app.logger.error('Exception in AddPubseries: ' + str(exp))
        return None