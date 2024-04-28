""" Module for changes-related functions. """
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.model import LogSchema
from app.impl import ResponseType
from app.orm_decl import Edition, Log, Part
from app.route_helpers import new_session
from app.types import HttpResponseCode

from app import app


def get_work_changes(workid: int) -> ResponseType:
    """
    Retrieves the changes made to the work and its editions with the given ID.

    Args:
        workid: The ID of the work to retrieve changes for.

    Returns:
        ResponseType: The response object containing the list of changes.
    """
    session = new_session()

    editions = [x[0] for x in session.query(Edition.id)
                .filter(Part.work_id == workid,
                Part.edition_id == Edition.id)
                .all()]
    try:
        changes = session.query(Log)\
            .filter(or_(
                and_(Log.table_id.in_(editions),
                    Log.table_name == 'Painos'),
                and_(Log.table_id == workid,
                    Log.table_name == 'Teos')))\
            .order_by(Log.id.desc())\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType('get_work_changes: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = LogSchema(many=True)
        retval = schema.dump(changes)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'Skeemavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.close()

    return ResponseType(retval, HttpResponseCode.OK.value)


def change_delete(changeid: int) -> ResponseType:
    """
    Deletes a change with the given ID.

    Args:
        changeid: The ID of the change to delete.

    Returns:
        ResponseType: The response object containing the status of the
                      deletion.
    """
    session = new_session()

    try:
        item = session.query(Log).filter(Log.id == changeid).first()
        session.delete(item)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'change_delete: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)
