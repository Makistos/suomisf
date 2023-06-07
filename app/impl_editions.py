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

# Save new edition to database
def EditionCreate(params: Any) -> ResponseType:
  retval = ResponseType('', 200)
  session = new_session()
  data = params['data']
  edition = Edition()
  edition.title = bleach.clean(data['title'])
  edition.subtitle = bleach.clean(data['subtitle'])

  return retval


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
        old_values['title'] = edition.title
        edition.title = bleach.clean(data['title'])

  if 'pubyear' in data:
    if data['pubyear'] == None:
      app.logger.error(f'EditionUpdate: Pubyear is empty.')
      return ResponseType(f'Julkaisuvuosi ei voi olla tyhjä.', 400)
    if data['pubyear'] != edition.pubyear:
      old_values['pubyear'] = edition.pubyear
      edition.pubyear = checkInt(data['pubyear'])

  if 'publisher' in data:
    if data['publisher'] == None:
      app.logger.error(f'EditionUpdate: Publisher is empty.')
      return ResponseType(f'Kustantaja ei voi olla tyhjä.', 400)
    if data['publisher']['id'] != edition.publisher_id:
        if data['publisher']['id'] != None:
            publisher_id = checkInt(data['publisher']['id'])
        else:
            publisher_id = None
        old_values['publisher'] = edition.publisher['name']
        edition.publisher_id = publisher_id

  if 'editionnum' in data:
    if data['editionnum'] == None:
      app.logger.error(f'EditionUpdate: Editionnum is empty.')
      return ResponseType(f'Painosnumero ei voi olla tyhjä.', 400)
    if data['editionnum'] != edition.editionnum:
      old_values['editionnum'] = edition.editionnum
      edition.editionnum = checkInt(data['editionnum'])

  if 'version' in data:
    if data['version'] == '':
      data['version'] = None
    if data['version'] != edition.version:
      old_values['version'] = edition.version
      edition.version = checkInt(data['version'])

  if 'isbn' in data:
    if data['isbn'] != edition.isbn:
      old_values['isbn'] = edition.isbn
      edition.isbn = bleach.clean(data['isbn'])

  if 'pages' in data:
    if data['pages'] != edition.pages:
      old_values['pages'] = edition.pages
      edition.pages = checkInt(data['pages'])

  if 'binding' in data:
    if data['binding']['id'] != edition.binding_id:
      old_values['binding'] = edition.binding.name
      edition.binding_id = checkInt(data['binding']['id'])

  if 'format' in data:
    if data['format']['id'] != edition.format_id:
      old_values['format'] = edition.format.name
      edition.format_id = checkInt(data['format']['id'])

  if 'size' in data:
    if data['size'] != edition.size:
      old_values['size'] = edition.size
      edition.size = checkInt(data['size'])

  if 'printedin' in data:
    if data['printedin'] != edition.printedin:
      old_values['printedin'] = edition.printedin
      edition.printedin = bleach.clean(data['printedin'])

  if 'pubseries' in data:
    if data['pubseries']['id'] != edition.pubseries_id:
      if data['pubseries']['id'] != None:
        pubseries_id = checkInt(data['pubseries']['id'])
      else:
        pubseries_id = None
      old_values['pubseries'] = edition.pubseries['name']
      edition.pubseries = pubseries_id

  if 'pubseriesnum' in data:
    if data['pubseriesnum'] != edition.pubseriesnum:
      old_values['pubseriesnum'] = edition.pubseriesnum
      edition.pubseriesnum = checkInt(data['pubseriesnum'])

  if 'dustcover' in data:
    if data['dustcover'] != edition.dustcover:
      old_values['dustcover'] = edition.dustcover
      edition.dustcover = checkInt(data['dustcover'])

  if 'coverimage' in data:
    if data['coverimage'] != edition.coverimage:
      old_values['coverimage'] = edition.coverimage
      edition.coverimage = checkInt(data['coverimage'])

  if 'misc' in data:
    if data['misc'] != edition.misc:
      old_values['misc'] = edition.misc
      edition.misc = bleach.clean(data['misc'])

  if 'imported_string' in data:
    if data['imported_string'] != edition.imported_string:
      old_values['imported_string'] = edition.imported_string
      edition.imported_string = bleach.clean(data['imported_string'])

  if 'contributors' in data:
    if contributorsHaveChanged(edition.contributions, data['contributors']):
      updateEditionContributors(session, edition.id, data['contributors'])

  if len(old_values) == 0:
    # No changes
    return retval

  LogChanges(session=session, obj=edition, action='Päivitys',
              old_values=old_values)

  try:
    session.add(edition)
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
