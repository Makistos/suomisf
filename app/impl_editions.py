# Desc: Editions implementation
import json
from app.route_helpers import new_session
from typing import Any, Dict, List, Optional, Union
from app.orm_decl import (Edition, Part, Tag, Work, BindingType, Format,
                          Publisher, Pubseries)
from app.impl_contributors import contributorsHaveChanged, updateEditionContributors
from sqlalchemy.exc import SQLAlchemyError # type: ignore
from marshmallow import exceptions # type: ignore
from app.model import EditionSchema, BindingBriefSchema
from app.impl import ResponseType, checkInt, LogChanges, GetJoinChanges
import bleach # type: ignore
from app import app

# Save first edition for work
def EditionCreateFirst(work: Work) -> Edition:
  retval = Edition()
  retval.title = work.title
  retval.subtitle = work.subtitle
  retval.pubyear = work.pubyear or 0
  retval.editionnum = 1
  retval.version = 1

  return retval

# Save new edition to database. Params requires work_id parameter.
def EditionCreate(params: Any) -> ResponseType:
  retval = ResponseType('', 200)
  session = new_session()
  data = params['data']

  if 'work_id' not in data:
    app.logger.error('Exception in EditionCreate: work_id not found.')
    return ResponseType('EditionCreate: Teoksen id (work_id) puuttuu.', 400)

  # Check that work exists
  work = session.query(Work).filter(Work.id == bleach.clean(data['work_id'])).first()
  if not work:
    app.logger.error('Exception in EditionCreate: work not found. id={data["work_id"]}')
    return ResponseType(f'Teosta ei löydy. id={data["work_id"]}', 400)

  bindings = session.query(BindingType).all()
  formats = session.query(Format).all()

  edition = Edition()
  if 'title' in data:
    edition.title = bleach.clean(data['title'])
  if 'subtitle' in data:
    edition.subtitle = bleach.clean(data['subtitle'])
  # Check that pubyear exists (required)
  if not 'pubyear' in data:
    app.logger.error('Exception in EditionCreate: pubyear not found.')
    return ResponseType('EditionCreate: Julkaisuvuosi (pubyear) puuttuu.', 400)
  pubyear: Union[int, None] = checkInt(value=data['pubyear'])
  if not pubyear:
    app.logger.error('Exception in EditionCreate: Invalid pubyear. pubyear={data["pubyear"]}')
    return ResponseType(f'Julkaisuvuosi on virheellinen. pubyear={data["pubyear"]}', 400)
  edition.pubyear = pubyear
  if 'editionnum' in data:
    editionnum = checkInt(data['editionnum'])
    if not editionnum:
      app.logger.error('Exception in EditionCreate: Invalid edition number. edition number={data["editionnum"]}')
      return ResponseType(f'Painosnumero on virheellinen. Painosnumero={data["editionnum"]}', 400)
    edition.editionnum = editionnum
  if 'version' in data:
    version = checkInt(data['version'])
    if not version:
      version = 1
    edition.version = version
  if 'publisher' in data:
    publisher_id = checkInt(data['publisher']['id'],
                            negativeValuesAllowed=False)
    if not publisher_id:
      app.logger.error('Exception in EditionCreate: Invalid publisher id. publisher id={data["publisher"]["id"]}')
      return ResponseType(f'Kustantajan id on virheellinen. id={data["publisher"]["id"]}', 400)
    publisher = session.query(Publisher).filter(Publisher.id == publisher_id).first()
    if not publisher:
      app.logger.error('Exception in EditionCreate: Publisher not found. id={publisher_id}')
      return ResponseType(f'Kustantajaa ei löydy. id={publisher_id}', 400)
    edition.publisher_id = publisher_id

  if 'isbn' in data:
    # TODO: Validate ISBN
    edition.isbn = bleach.clean(data['isbn'])
  if 'pubseries' in data:
    pubseries_id = checkInt(data['pubseries']['id'],
                            negativeValuesAllowed=False)
    if pubseries_id:
      pubseries = session.query(Publisher).filter(Publisher.id == pubseries_id).first()
      if not pubseries:
        app.logger.error('Exception in EditionCreate: Pubseries not found. id={pubseries_id}')
        return ResponseType(f'Julkaisusarjaa ei löydy. id={pubseries_id}', 400)
    edition.pubseries_id = pubseries_id
  if 'pubseriesnum' in data:
    edition.pubseriesnum = checkInt(data['pubseriesnum'])
  if 'coll_info' in data:
    # This is not really used anywhere, but it's here for completeness
    edition.coll_info = bleach.clean(data['coll_info'])
  if 'pages' in data:
    edition.pages = checkInt(data['pages'], negativeValuesAllowed=False)
  if 'binding' in data:
    # Invalid binding id will just set binding to None
    edition.binding_id = checkInt(data['binding']['id'],
                                  allowed=[b.id for b in bindings])
  if 'format' in data:
    # Invalid format id will just set format to None
    edition.format_id = checkInt(data['format']['id'],
                                allowed=[f.id for f in formats])
  if 'size' in data:
    edition.size = checkInt(data['size'], negativeValuesAllowed=False)
  if 'dustcover' in data:
    dustcover:Union[int, None] = checkInt(data['dustcover'], allowed=[1, 2, 3])
    if dustcover:
      edition.dustcover = dustcover
    else:
      # Default value
      edition.dustcover = 1
  if 'coverimage' in data:
    coverimage: Union[int, None] = checkInt(data['coverimage'], allowed=[1, 2, 3])
    if coverimage:
      edition.coverimage = coverimage
    else:
      # Default value
      edition.coverimage = 1
  if 'misc' in data:
    edition.misc = bleach.clean(data['misc'])
  if 'imported_string' in data:
    edition.imported_string = bleach.clean(data['imported_string'])

  try:
    session.add(edition)
    session.commit()
  except SQLAlchemyError as e:
    app.logger.error(f'Exception in EditionCreate: {e}')
    return ResponseType('EditionCreate: Tietokantavirhe.', 500)

  # Create Part
  part = Part()
  part.edition_id = edition.id
  part.work_id = data['work_id']
  session.add(part)
  session.commit()

  retval = ResponseType(str(edition.id), 200)
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

  bindings = session.query(BindingType).all()
  formats = session.query(Format).all()

  # Title, required field, cannot be empty
  if 'title' in data:
    if data['title'] != edition.title:
      if not edition.title or len(edition.title) == 0:
        app.logger.error(f'EditionUpdate: Title is empty.')
        return ResponseType(f'Otsikko ei voi olla tyhjä.', 400)
      else:
        old_values['title'] = edition.title
        edition.title = bleach.clean(data['title'])

  # Subtitle, not required
  if 'subtitle' in data:
    if data['subtitle'] != edition.subtitle:
      old_values['subtitle'] = edition.subtitle
      subtitle: Union[str, None] = bleach.clean(data['subtitle'])
      if subtitle == '':
        subtitle = None
      edition.subtitle = subtitle

  # Pubyear, required field
  if 'pubyear' in data:
    if data['pubyear'] == None:
      app.logger.error(f'EditionUpdate: Pubyear is empty.')
      return ResponseType(f'Julkaisuvuosi ei voi olla tyhjä.', 400)
    if data['pubyear'] != edition.pubyear:
      old_values['pubyear'] = edition.pubyear
      edition.pubyear = checkInt(data['pubyear'])

  # Publisher, required field. Has to exist in database.
  if 'publisher' in data:
    if data['publisher']['id'] != edition.publisher_id:
      if data['publisher'] == None:
        app.logger.error(f'EditionUpdate: Publisher is empty.')
        return ResponseType(f'Kustantaja ei voi olla tyhjä.', 400)
      publisher_id = checkInt(data['publisher']['id'], negativeValuesAllowed=False)
      if publisher_id:
        publisher = session.query(Publisher).filter(Publisher.id == publisher_id).first()
        if not publisher:
          app.logger.error(f'EditionUpdate: Publisher not found. id={publisher_id}')
          return ResponseType(f'Kustantajaa ei löydy. id={publisher_id}', 400)
      else:
        app.logger.error(f'EditionUpdate: Invalid publisher id. id={publisher_id}')
        return ResponseType(f'Virheellinen kustantaja. id={publisher_id}', 400)
      old_values['publisher'] = edition.publisher.name
      edition.publisher_id = publisher_id

  # Edition number, required field
  if 'editionnum' in data:
    if data['editionnum'] == None:
      app.logger.error(f'EditionUpdate: Editionnum is empty.')
      return ResponseType(f'Painosnumero ei voi olla tyhjä.', 400)
    if data['editionnum'] != edition.editionnum:
      editionnum = checkInt(data['editionnum'])
      if editionnum == None:
        app.logger.error(f'EditionUpdate: Invalid editionnum.')
        return ResponseType(f'Virheellinen painosnumero.', 400)
      old_values['editionnum'] = edition.editionnum
      edition.editionnum = editionnum

  # Version (laitos), not required
  if 'version' in data:
    if data['version'] == '':
      data['version'] = None
    if data['version'] != edition.version:
      version = checkInt(data['version'])
      if version == None and data['version'] != None:
        # Trying to set a value but it's not an integer
        app.logger.error(f'EditionUpdate: Invalid version.')
        return ResponseType(f'Virheellinen laitos.', 400)
      # Either removing value (version=None) or setting a new one
      old_values['version'] = edition.version
      edition.version = version

  # ISBN, not required
  if 'isbn' in data:
    if data['isbn'] != edition.isbn:
      old_values['isbn'] = edition.isbn
      isbn: Union[str, None] = bleach.clean(data['isbn'])
      if isbn == '':
        isbn = None
      edition.isbn = isbn

  # Number of pages, not required
  if 'pages' in data:
    if data['pages'] != edition.pages:
      pages = checkInt(data['pages'], negativeValuesAllowed=False)
      if pages == None and data['pages'] != None:
        # Trying to set a value but it's not an integer
        app.logger.error(f'EditionUpdate: Invalid pages.')
        return ResponseType(f'Virheellinen sivumäärä.', 400)
      # Either removing value or setting a new one
      old_values['pages'] = edition.pages
      edition.pages = pages


  # Binding type, required field. Has to exist in database.
  if 'binding' in data:
    if data['binding']['id'] != edition.binding_id:
      binding_id = checkInt(data['binding']['id'], allowed=[b.id for b in bindings])
      if binding_id == None:
        app.logger.error(f'EditionUpdate: Invalid binding.')
        return ResponseType(f'Virheellinen sidonta.', 400)
      old_values['binding'] = edition.binding.name
      edition.binding_id = binding_id

  # Edition format, required field. Has to exist in database.
  if 'format' in data:
    if data['format']['id'] != edition.format_id:
      format_id = checkInt(data['format']['id'], allowed=[f.id for f in formats])
      if format_id == None:
        app.logger.error(f'EditionUpdate: Invalid format.')
        return ResponseType(f'Virheellinen formaatti.', 400)
      old_values['format'] = edition.format.name
      edition.format_id = format_id

  # Size (height in cm), not required
  if 'size' in data:
    if data['size'] != edition.size:
      size = checkInt(data['size'], negativeValuesAllowed=False)
      if size == None and data['size'] != None:
        # Trying to set a value but it's not an integer
        app.logger.error(f'EditionUpdate: Invalid size.')
        return ResponseType(f'Virheellinen koko.', 400)
      # Either removing value or setting a new one
      old_values['size'] = edition.size
      edition.size = size

  # Print location, not required
  if 'printedin' in data:
    if data['printedin'] != edition.printedin:
      old_values['printedin'] = edition.printedin
      printedin: Union[str, None] = bleach.clean(data['printedin'])
      if printedin == '':
        printedin = None
      edition.printedin = printedin

  # Publisher's series, not required
  if 'pubseries' in data:
    if data['pubseries']['id'] != edition.pubseries_id:
      if data['pubseries']['id'] != None:
        pubseries_id = checkInt(data['pubseries']['id'])
        if pubseries_id == None:
          app.logger.error(f'EditionUpdate: Invalid pubseries id.')
          return ResponseType(f'Virheellinen kustantajan sarja.', 400)
        pubseries = session.query(Pubseries).filter(Pubseries.id == pubseries_id).first()
        if not pubseries:
          app.logger.error(f'EditionUpdate: Pubseries not found. id={pubseries_id}')
          return ResponseType(f'Kustantajan sarjaa ei löydy. id={pubseries_id}', 400)
      else:
        pubseries_id = None
      old_values['pubseries'] = edition.pubseries.name
      edition.pubseries_id = pubseries_id

  # Publisher's series number, not required
  if 'pubseriesnum' in data:
    if data['pubseriesnum'] != edition.pubseriesnum:
      pubseriesnum = checkInt(data['pubseriesnum'])
      if pubseriesnum == None and data['pubseriesnum'] != None:
        # Trying to set a value but it's not an integer
        app.logger.error(f'EditionUpdate: Invalid pubseriesnum.')
        return ResponseType(f'Virheellinen sarjan numero.', 400)
      old_values['pubseriesnum'] = edition.pubseriesnum
      edition.pubseriesnum = pubseriesnum

  # Whether the book has a dustcover, not required
  if 'dustcover' in data:
    if data['dustcover'] != edition.dustcover:
      dustcover = checkInt(data['dustcover'], allowed=[1, 2, 3])
      if dustcover == None:
        app.logger.error(f'EditionUpdate: Invalid dustcover.')
        return ResponseType(f'Virheellinen kansipaperin tyyppi.', 400)
      if edition.dustcover == 1:
        old_value = "Ei tietoa"
      elif edition.dustcover == 2:
         old_value = "Ei"
      else:
        old_value = "Kyllä"
      old_values['dustcover'] = old_value
      edition.dustcover = dustcover

  # Whether the book has a cover image, not required.
  # This is used for hardcovers only.
  if 'coverimage' in data:
    if data['coverimage'] != edition.coverimage:
      coverimage = checkInt(data['coverimage'], allowed=[1, 2, 3])
      if coverimage == None:
        app.logger.error(f'EditionUpdate: Invalid coverimage.')
        return ResponseType(f'Virheellinen kansikuvan tyyppi.', 400)
      if edition.coverimage == 1:
        old_value = "Ei tietoa"
      elif edition.coverimage == 2:
         old_value = "Ei"
      else:
        old_value = "Kyllä"
      old_values['coverimage'] = old_value
      edition.coverimage = coverimage

  # Miscellanous notes, not required
  if 'misc' in data:
    if data['misc'] != edition.misc:
      old_values['misc'] = edition.misc
      misc: Union[str, None] = bleach.clean(data['misc'])
      if misc == '':
        misc = None
      edition.misc = misc

  # Holds string where data was originally extracted from. Also used for source.
  if 'imported_string' in data:
    if data['imported_string'] != edition.imported_string:
      old_values['imported_string'] = edition.imported_string
      imported_string: Union[str, None] = bleach.clean(data['imported_string'])
      if imported_string == '':
        imported_string = None
      edition.imported_string = imported_string

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

def BindingGetAll() -> ResponseType:
  session = new_session()
  try:
    bindings = session.query(BindingType).all()
  except SQLAlchemyError as exp:
    app.logger.error('Exception in BindingGetAll: ' + str(exp))
    return ResponseType('BindingGetAll: Tietokantavirhe.', 400)
  try:
    schema = BindingBriefSchema(many=True)
    retval = schema.dump(bindings)
  except exceptions.MarshmallowError as exp:
    app.logger.error('Exception in BindingGetAll: ' + str(exp))
    return ResponseType('BindingGetAll: Tietokantavirhe.', 400)
  return ResponseType(retval, 200)
