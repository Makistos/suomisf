"""
  This module contains the implementation of the LogSchema class for handling
  log data.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app import app
from app.impl import ResponseType
from app.route_helpers import new_session
from app.model import LogSchema
from app.orm_decl import Log, Tag, Work
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
                'award': 'Palkinto',
                'bookseries': 'Kirjasarja',
                'edition': 'Painos',
                'issue': 'Irtonumero',
                'magazine': 'Lehti',
                'person': 'Henkilö',
                'publisher': 'Kustantaja',
                'pubseries': 'Julkaisusarja',
                'shortstory': 'Novelli',
                'tag': 'Asiasana',
                'work': 'Teos'}


# pylint: disable-next=dangerous-default-value
def log_changes(session: Any, obj: Any, name_field: str = "name",
                action: str = 'Päivitys',
                old_values: Optional[Dict[str, Any]] = None) -> int:
    ''' Log a change made to data.

    Logging is done in the same session as the object itself, so it will
    also be in the same commit. I.e. if storing data fails for some reason
    log is also not stored.

    Args:
        session (Any): Session handler.
        obj (Any): Object that was changed.
        name_field (str, optional): Attribute holding the object's name.
                                    Defaults to "name".
        action (str, optional): "Uusi", "Päivitys" or "Poisto". Defaults
                                to 'Päivitys'.
        old_values (Dict[str, Any], optional): Changed fields and their old
                                               values, one row per field.
                                               Needed for "Päivitys" and
                                               "Poisto", not used for
                                               "Uusi".

    Returns:
        int: The number of log entries added, 0 if nothing was logged.
    '''
    retval: int = 0
    name = getattr(obj, name_field)
    if name is not None:
        name = str(name)[:200]

    if obj.__table__.name not in table_locals:
        app.logger.error(f'Unknown table {obj.__table__.name}.')
        return retval

    tbl_name = table_locals[obj.__table__.name]

    if obj.id is None:
        # A new object: flush so the log row can point to its id.
        session.flush()

    try:
        jwt_id = get_jwt_identity()
    except RuntimeError:
        # Called outside a request, e.g. from a script: no user to log.
        jwt_id = None

    if jwt_id is None:
        app.logger.warning('No JWT token or missing identity.')
        return retval

    user_id = int(jwt_id)
    if action in ['Päivitys', 'Poisto']:
        for field, value in (old_values or {}).items():
            # old_value is a String(500) column, but callers pass mixed
            # Python types (ints, etc.) - normalize to str/None here so
            # every row in a batched multi-field insert binds the same
            # type. SQLAlchemy 2.0's insertmanyvalues batching infers a
            # shared cast per column from the first row's Python type;
            # a later row with a different type (e.g. int then str) can
            # produce a cast that fails on the other rows' values.
            if value is not None:
                value = str(value)[:499]
            log = Log(table_name=tbl_name,
                      field_name=field,
                      table_id=obj.id,
                      object_name=name,
                      action=action,
                      user_id=user_id,
                      old_value=value,
                      date=datetime.now(timezone.utc))
            session.add(log)
            retval += 1
    else:
        log = Log(table_name=tbl_name,
                  field_name='',
                  table_id=obj.id,
                  object_name=name,
                  action=action,
                  user_id=user_id,
                  date=datetime.now(timezone.utc))
        session.add(log)
        retval = 1
    return retval


def log_and_commit(session: Any, obj: Any, name_field: str = "name",
                   action: str = 'Päivitys',
                   old_values: Optional[Dict[str, Any]] = None) -> int:
    ''' Log a change that has already been committed and commit the log.

    Use log_changes instead when the change itself is still to be
    committed, so that both go in the same commit.

    Returns:
        int: The number of log entries stored, 0 if nothing was logged.
    '''
    count = log_changes(session, obj=obj, name_field=name_field,
                        action=action, old_values=old_values)
    if count:
        try:
            session.commit()
        except SQLAlchemyError as exp:
            session.rollback()
            app.logger.error(f'log_and_commit: {exp}.')
            return 0
    return count


def log_tag_change(session: Any, obj: Any, tag_id: int, added: bool,
                   name_field: str = "name") -> int:
    ''' Log adding a tag to or removing it from obj.

    Like log_changes, the log goes in the same commit as the change.

    Args:
        session (Any): Session handler.
        obj (Any): The work, person, story, issue or article.
        tag_id (int): The tag that was added or removed.
        added (bool): True if the tag was added, False if removed.
        name_field (str, optional): Attribute holding obj's name.

    Returns:
        int: The number of log entries added.
    '''
    tag = session.query(Tag).filter(Tag.id == tag_id).first()
    tag_name = tag.name if tag else str(tag_id)
    change = 'Lisätty' if added else 'Poistettu'
    return log_changes(session, obj=obj, name_field=name_field,
                       old_values={'Asiasanat': f'{change}: {tag_name}'})


def log_list_change(session: Any, obj: Any, field: str,
                    old_ids: List[int], new_ids: List[int], model: Any,
                    name_field: str = "name") -> int:
    ''' Log a changed list of linked rows, such as the stories of an
    edition, if the list changed.

    The old value is the titles of the old rows in their old order.

    Args:
        session (Any): Session handler.
        obj (Any): The object the list belongs to.
        field (str): The log's field name, e.g. "Novellit".
        old_ids (List[int]): Ids of the linked rows before the change.
        new_ids (List[int]): Ids of the linked rows after the change.
        model (Any): The linked rows' class; it must have a title.
        name_field (str, optional): Attribute holding obj's name.

    Returns:
        int: The number of log entries added.
    '''
    old_ids = [int(x) for x in old_ids]
    if old_ids == [int(x) for x in new_ids]:
        return 0
    titles = dict(session.query(model.id, model.title)
                  .filter(model.id.in_(old_ids)).all()) if old_ids else {}
    old_value = '; '.join(titles.get(x, str(x)) for x in old_ids)
    return log_changes(session, obj=obj, name_field=name_field,
                       old_values={field: old_value})
