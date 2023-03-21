import json
from typing import Dict, Tuple, Any
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import Publisher
from app.model import (PublisherBriefSchema,
                       PublisherSchema, PublisherBriefSchemaWEditions)
from app.impl import ResponseType, checkInt, LogChanges
from app import app


def FilterPublishers(query: str) -> ResponseType:
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


def PublisherAdd(params: Any) -> ResponseType:
    session = new_session()
    retval = ResponseType('OK', 200)

    return retval


def PublisherUpdate(params: Any) -> ResponseType:
    session = new_session()
    retval = ResponseType('OK', 200)
    old_values = {}
    publisher: Any = None
    data = params['data']
    changed = params['changed']
    publisher_id = checkInt(data['id'])

    if len(changed) == 0:
        return ResponseType('OK', 200)

    publisher = session.query(Publisher).filter(
        Publisher.id == publisher_id).first()

    if 'name' in changed:
        if changed['name'] == True:
            if len(data['name']) == 0:
                app.logger.error('PublisherUpdate: Name is a required field')
                return ResponseType('PublisherUpdate: Nimi on pakollinen tieto.', 400)
            if data['name'] != publisher.name:
                similar = session.query(Publisher).filter(
                    Publisher.name == data['name']).all()
                if len(similar) > 0:
                    app.logger.error('PublisherUpdate: Name must be unique.')
                    return ResponseType('PublisherUpdate: Nimi on jo käytössä', 400)
            old_values['name'] = publisher.name
            publisher.name = data['name']

    if 'fullname' in changed:
        if changed['fullname'] == True:
            if len(data['fullname']) == 0:
                app.logger.error(
                    'PublisherUpdate: fullname is a required field')
                return ResponseType('PublisherUpdate: Nimi on pakollinen tieto.', 400)
            if data['fullname'] != publisher.fullname:
                similar = session.query(Publisher).filter(
                    Publisher.fullname == data['fullname']).all()
                if len(similar) > 0:
                    app.logger.error(
                        'PublisherUpdate: fullname must be unique.')
                    return ResponseType('PublisherUpdate: Nimi on jo käytössä', 400)
            old_values['fullname'] = publisher.fullname
            publisher.fullname = data['fullname']

    if 'description' in changed:
        if changed['description'] == True:
            old_values['description'] = publisher.description
            publisher.description = data['description']

    LogChanges(session=session, obj=publisher, action='Päivitys',
               fields=changed, old_values=old_values)

    try:
        session.add(publisher)
    except SQLAlchemyError as exp:
        app.logger.error(f'Exception in PublisherUpdate: {exp}.')
        return ResponseType(f'PublisherUpdate: Tietokantavirhe.', 400)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'Exception in PublisherUpdate commit: {exp}.')
        return ResponseType(f'PublisherUpdate: Tietokantavirhe tallennettaessa.', 400)

    return retval
