from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.orm_decl import (Bookseries)
from app.model import (BookseriesSchema, BookseriesBriefSchema)
from app.route_helpers import new_session
from app.impl import ResponseType
from app import app


def FilterBookseries(query: str) -> ResponseType:
    session = new_session()
    try:
        bookseries = session.query(Bookseries)\
            .filter(Bookseries.name.ilike(query + '%'))\
            .order_by(Bookseries.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterBookseries (query: {query}): ' + str(exp))
        return ResponseType('FilterBookseries: Tietokantavirhe.', 400)
    try:
        schema = BookseriesBriefSchema(many=True)
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterBookseries schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def GetBookseries(id: int) -> ResponseType:
    session = new_session()

    try:
        bookseries = session.query(Bookseries).filter(
            Bookseries.id == id).first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetBookseries: ' + str(exp))
        return ResponseType(f'GetBookseries: Tietokantavirhe. id={id}', 400)

    try:
        schema = BookseriesSchema()
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetBookseries schema error: ' + str(exp))
        return ResponseType('GetBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ListBookseries() -> ResponseType:
    session = new_session()

    try:
        bookseries = session.query(Bookseries).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListBookseries: ' + str(exp))
        return ResponseType(f'ListBookseries: Tietokantavirhe. id={id}', 400)

    try:
        schema = BookseriesBriefSchema(many=True)
        retval = schema.dump(bookseries)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListBookseries schema error: ' + str(exp))
        return ResponseType('ListBookseries: Skeemavirhe.', 400)

    return ResponseType(retval, 200)
