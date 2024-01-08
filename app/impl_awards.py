"""
Module for award-related functions.
"""
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.route_helpers import new_session
from app.impl import ResponseType
from app.model import AwardBriefSchema, AwardSchema
from app.orm_decl import Award
from app.types import HttpResponseCode

from app import app


def list_awards() -> ResponseType:
    """
    List all awards.

    Returns:
      list: A list of Award objects.
    """
    session = new_session()
    try:
        awards = session.query(Award).order_by(Award.name).all()
    except SQLAlchemyError as exp:
        app.logger.error(f'list_awards: {exp}.')
        return ResponseType(f'list_awards tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = AwardBriefSchema(many=True)
        awards = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'list_awards schema error: {exp}.')
        return ResponseType(f'list_awards skeemavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(awards, HttpResponseCode.OK.value)


def get_award(award_id: int) -> ResponseType:
    """
    Get an award.

    Args:
      award_id (int): The ID of the award to retrieve.

    Returns:
      Award: The retrieved award object.
    """
    session = new_session()

    try:
        award = session.query(Award).filter(Award.id == award_id).first()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_award: {exp}.')
        return ResponseType(
            f'get_award: Tietokantavirhe. id={award_id}: {exp}.',
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = AwardSchema()
        award = schema.dump(award)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_award schema error: {exp}.')
        return ResponseType(f'get_award: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(award, HttpResponseCode.OK)
