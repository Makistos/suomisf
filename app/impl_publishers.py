import json
from typing import Dict, Tuple
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Publisher
from app.model import (PublisherBriefSchema,
                       PublisherSchema, PublisherBriefSchemaWEditions)
from app.impl import ResponseType
from app import app


def GetPublisher(id: int) -> ResponseType:
    session = new_session()

    try:
        publisher = session.query(Publisher)\
            .filter(Publisher.id == id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetPublishers: ' + str(exp))
        return ResponseType(f'GetPublishers: Tietokantavirhe. id={id}', 400)

    try:
        schema = PublisherSchema()
        retval = schema.dump(publisher)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetPublisher schema error: ' + str(exp))
        return ResponseType('GetPublisher: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ListPublishers() -> ResponseType:
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
