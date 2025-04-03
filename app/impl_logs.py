"""
  This module contains the implementation of the LogSchema class for handling
  log data.
"""
from datetime import datetime
from typing import Any, Dict
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app import app
from app.impl import ResponseType
from app.route_helpers import new_session
from app.model import LogSchema
from app.orm_decl import Log, Work
from app.types import HttpResponseCode


def get_work_changes(work_id: int) -> ResponseType:
    """
    Get the changes for a work.

    Args:
      work_id (int): The ID of the work.

    Returns:
      ResponseType: The changes for the work.
    """
    session = new_session()

    work = session.query(Work).filter(Work.id == work_id).first()

    if not work:
        app.logger.error(f'Work not found. Id = {work_id}.')
        return ResponseType('Teosta ei löydy',
                            HttpResponseCode.BAD_REQUEST.value)
    edition_ids = []
    for edition in work.editions:
        edition_ids.append(edition.id)

    try:
        changes = session.query(Log)\
            .filter(or_(
                and_(Log.table_id.in_(edition_ids),
                     Log.table_name == 'Painos'),
                and_(Log.table_id == work_id,
                     Log.table_name == 'Teos')))\
            .order_by(Log.id.desc())\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'get_work_changes: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = LogSchema(many=True)
        retval = schema.dump(changes)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_work_changes: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_edition_changes(edition_id: int) -> ResponseType:
    """
    Get the changes for an edition.

    Args:
      edition_id (int): The ID of the edition.

    Returns:
      ResponseType: The changes for the edition.
    """
    session = new_session()

    try:
        changes = session.query(Log)\
            .filter(Log.table_id == edition_id, Log.table_name == 'Painos')\
            .order_by(Log.id.desc())\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType('get_edition_changes: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = LogSchema(many=True)
        retval = schema.dump(changes)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'get_edition_changes: Skeemavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


table_locals = {'article': 'Artikkeli',
                'bookseries': 'Kirjasarja',
                'edition': 'Painos',
                'issue': 'Irtonumero',
                'magazine': 'Lehti',
                'person': 'Henkilö',
                'publisher': 'Kustantaja',
                'shortstory': 'Novelli',
                'work': 'Teos'}


# pylint: disable-next=dangerous-default-value
def log_changes(session: Any, obj: Any, name_field: str = "name",
                action: str = 'Päivitys',
                old_values: Dict[str, Any] = {}) -> int:
    ''' Log a change made to data.

    Logging is done in the same session as the object itself, so it will
    also be in the same commit. I.e. if storing data fails for some reason
    log is also not stored.

    Args:
        session (Any): Session handler.
        obj (Any): Object that was changed.
        action (str, optional): Description of change, either "Päivitys" or
                                "Uusi". Defaults to 'Päivitys'.
        fields (List[str], optional): Fields that were changed. Needed for
                                      "Päivitys", not used for "Uusi". Defaults
                                      to [].

    Returns:
        int: The id of the log entry.
    '''
    retval: int = 0
    name: str = getattr(obj, name_field)

    if obj.__table__.name not in table_locals:
        app.logger.error(f'Unknown table {obj.__table__.name}.')
        return retval

    tbl_name = table_locals[obj.__table__.name]

    jwt_id = get_jwt_identity()

    if jwt_id is None:
        app.logger.warning('No JWT token or missing identity.')
        return retval

    user_id = int(jwt_id)
    if action in ['Päivitys', 'Poisto']:
        for field, value in old_values.items():
            if isinstance(value, str):
                value = value[:499]
            log = Log(table_name=tbl_name,
                      field_name=field,
                      table_id=obj.id,
                      object_name=name,
                      action=action,
                      user_id=user_id,
                      old_value=value,
                      date=datetime.now())
            session.add(log)
            retval = log.id
    else:
        log = Log(table_name=tbl_name,
                  field_name='',
                  table_id=obj.id,
                  object_name=name,
                  action=action,
                  user_id=user_id,
                  date=datetime.now())
        session.add(log)
        retval = log.id
    return retval
