# Desc: Editions implementation
import json
from app.route_helpers import new_session
from typing import Any, Dict, List, Optional, Union
from app.orm_decl import (Edition, Part, Tag)
from app.impl_contributors import contributorsHaveChanged, updateEditionContributors
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.model import EditionSchema
from app.impl import ResponseType, checkInt, LogChanges, GetJoinChanges
import bleach
from app import app



# Save changes to edition to database.
def EditionUpdate(params: Any) -> ResponseType:
  retval = ResponseType('', 200)
  session = new_session()
  old_values = {}
  data = params['data']
  edition_id = checkInt(data['id'])

  edition = session.query(Edition).filter(Edition.id == edition_id).first()
  if not edition:
    app.logger.error(f'EditionUpdate: Edition {edition_id} not found.')
    return ResponseType(f'Painosta {edition_id} ei löydy.', 404)

  if 'title' in data:
    edition.title = bleach.clean(data['title'])
    if data['title'] != edition.title:
      if len(edition.title) == 0:
        app.logger.error(f'EditionUpdate: Title is empty.')
        return ResponseType(f'Otsikko ei voi olla tyhjä.', 400)
      else:
        old_values['title'] = data['title']
        edition.title = bleach.clean(data['title'])

  if 'publisher' in data:
    if data['publisher'] == None:
      app.logger.error(f'EditionUpdate: Publisher is empty.')
      return ResponseType(f'Kustantaja ei voi olla tyhjä.', 400)
    if data['publisher'] != edition.publisher:
      old_values['publisher'] = data['publisher']
      edition.publisher = bleach.clean(data['publisher'])

  if len(old_values) == 0:
    # No changes
    return retval

  LogChanges(session=session, obj=edition, action='Päivitys',
              old_values=old_values)

  try:
    session.add()
  except SQLAlchemyError as exp:
    session.rollback()
    app.logger.error('Exception in EditionUpdate: ' + str(exp))
    return ResponseType('EditionUpdate: Tietokantavirhe. id={edition.id}.', 400)

  try:
    session.commit()
  except SQLAlchemyError as exp:
    session.rollback()
    app.logger.error('Exception in EditionUpdate: ' + str(exp))
    return ResponseType('EditionUpdate: Tietokantavirhe. id={edition.id}', 400)

  return retval