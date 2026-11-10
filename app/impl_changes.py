""" Module for changes-related functions. """
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.model import LogSchema
from app.impl import ResponseType
from app.impl_change_history import add_new_values
from app.orm_decl import Edition, Log, Work
from app.route_helpers import new_session
from app.types import HttpResponseCode

from app import app


def get_work_changes(workid: int) -> ResponseType:
    """
    Retrieves the changes made to the work and its editions with the given ID.

    Each change also has "field" (the field's current name), "new_value"
    and "new_value_source" (see impl_change_history.add_new_values), and
    "target": "Teos", or for an edition e.g. "2. painos (1995)".

    Args:
        workid: The ID of the work to retrieve changes for.

    Returns:
        ResponseType: The response object containing the list of changes.
    """
    session = new_session()

    work = session.query(Work).filter(Work.id == workid).first()
    edition_objs = session.query(Edition)\
        .filter(Edition.work_id == workid).all()
    editions = [x.id for x in edition_objs]
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

    objects = {('Painos', e.id): e for e in edition_objs}
    if work is not None:
        objects[('Teos', work.id)] = work
    add_new_values(retval, objects)
    for row in retval:
        row['target'] = _target_label(row, objects)

    session.close()

    return ResponseType(retval, HttpResponseCode.OK.value)


def _target_label(row: dict, objects: dict) -> str:
    """ "Teos", or an edition as "2. painos (1995)" or "Painos" if it is
    gone. """
    if row['table_name'] != 'Painos':
        return row['table_name']
    edition = objects.get(('Painos', row['table_id']))
    if edition is None:
        return 'Painos (poistettu)'
    label = f'{edition.editionnum}. painos' if edition.editionnum \
        else 'Painos'
    if edition.version and edition.version > 1:
        label = f'{edition.version}. laitos, {label}'
    return f'{label} ({edition.pubyear})' if edition.pubyear else label


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
        if item is None:
            return ResponseType('Muutosta ei löydy.',
                                HttpResponseCode.NOT_FOUND.value)
        # The row itself is gone after this, so leave a trace in the
        # server log: who deleted it and what it said.
        app.logger.warning(
            f'Change log row deleted by user {get_jwt_identity()}: '
            f'id={item.id} table={item.table_name} '
            f'table_id={item.table_id} object={item.object_name!r} '
            f'action={item.action} field={item.field_name} '
            f'old_value={item.old_value!r} user_id={item.user_id} '
            f'date={item.date}')
        session.delete(item)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType(f'change_delete: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('', HttpResponseCode.OK.value)
