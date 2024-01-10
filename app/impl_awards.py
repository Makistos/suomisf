"""
Module for award-related functions.
"""
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.route_helpers import new_session
from app.impl import ResponseType
from app.model import AwardBriefSchema, AwardSchema, AwardedSchema
from app.orm_decl import Award, Awarded
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
        retval = schema.dump(award)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_award schema error: {exp}.')
        return ResponseType(f'get_award: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK)


def get_awards_for_work(work_id: int) -> ResponseType:
    """
    Get the awards for a specific work.

    Args:
        work_id (int): The ID of the work.

    Returns:
        ResponseType: The list of awards for the work.
    """
    session = new_session()

    try:
        awards = session.query(Awarded)\
            .filter(Awarded.work_id == work_id)\
            .order_by(Awarded.year)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_awards_for_work: {exp}.')
        return ResponseType(f'get_awards_for_work: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = AwardedSchema(many=True)
        retval = schema.dump(awards)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_awards_for_work schema error: {exp}.')
        return ResponseType(f'get_awards_for_work: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def update_awarded(params: Any) -> ResponseType:
    session = new_session()
    old_values = {}
    data = params["data"]

    return ResponseType('OK', HttpResponseCode.OK.value)