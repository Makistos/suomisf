""" Editions implementation """
import json
from typing import Any, Dict, Union
import os
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.api_helpers import allowed_image
from app.impl_helpers import objects_differ, str_differ
from app.impl_logs import log_changes
from app.impl_publishers import add_publisher
from app.isbn import check_isbn  # type: ignore
from app.orm_decl import (
    BookCondition,
    Edition,
    Part,
    User,
    Work,
    BindingType,
    Format,
    Publisher,
    Pubseries,
    Contributor,
    EditionImage,
    EditionLink,
    EditionPrice,
    ShortStory,
    Log,
    UserBook
)
from app.impl_contributors import (
    contributors_have_changed,
    update_edition_contributors,
    get_contributors_string,
    get_work_contributors,
)
from app.route_helpers import new_session
from app.model import (BindingBriefSchema, EditionSchema, ShortBriefSchema,
                       EditionBriefSchema, UserBookSchema)
from app.impl import ResponseType, check_int
from app.impl_pubseries import add_pubseries
from app.types import ContributorTarget, HttpResponseCode
from app import app


# Save first edition for work
def create_first_edition(work: Work) -> Edition:
    """
    Create the first edition of a work.

    Args:
        work (Work): The work object containing the details of the work.

    Returns:
        Edition: The first edition of the work.

    """
    retval = Edition()
    retval.title = work.title
    retval.subtitle = work.subtitle
    retval.pubyear = work.pubyear or 0
    retval.editionnum = 1
    retval.version = 1
    retval.binding_id = 1
    retval.dustcover = 1
    retval.coverimage = 1
    retval.format_id = 1

    return retval


def _set_publisher(
    session: Any,
    edition: Edition,
    data: Any,
    old_values: Union[Dict[str, Any], None]
) -> Union[ResponseType, None]:
    """
    Sets the publisher for the given edition and returns a response type or
    None.

    Args:
        session: The session object.
        edition: The edition object.
        data: The data object.
        old_values: The old values.

    Returns:
        Union[ResponseType, None]: The response type or None.
    """
    if (data["publisher"] == "" or data["publisher"] is None):
        app.logger.error(f'Publisher missing for edition {edition.id}')
        return ResponseType('Kustantaja on pakollinen tieto',
                            HttpResponseCode.BAD_REQUEST.value)
    if objects_differ(data["publisher"], edition.publisher):
        if old_values is not None:
            old_values["Kustantaja"] = (edition.publisher.name
                                        if edition.publisher else '')
        if (data["publisher"] is not None and
                "id" not in data["publisher"]):
            pub_id = check_int(data["publisher"])
            if not pub_id:
                # User added a new publisher. Front returns this as a string
                # with the name of the new publisher
                pub_id = add_publisher(session, data["publisher"])
                if not pub_id:
                    app.logger.error(
                        f'Internal error creating publisher for {edition.id}')
                    return ResponseType(
                        'Uuden kustantajan luominen ei onnistunut: '
                        f'{data["publisher"]}',
                        HttpResponseCode.INTERNAL_SERVER_ERROR.value)
        else:
            pub_id = check_int(data["publisher"]["id"])  # type: ignore
            if pub_id is None:
                app.logger.error(
                    f'Publisher missing for edition {edition.id}')
                return ResponseType('Kustantaja on pakollinen tieto',
                                    HttpResponseCode.BAD_REQUEST.value)
            publisher = session.query(Publisher).filter(
                Publisher.id == pub_id
            ).first()
            if not publisher:
                app.logger.error(
                    f'Publisher missing for edition {edition.id}')
                return ResponseType('Kustantaja on pakollinen tieto',
                                    HttpResponseCode.BAD_REQUEST.value)
        edition.publisher_id = pub_id
    return None


def _set_pubseries(
    session: Any,
    edition: Edition,
    data: Any,
    old_values: Union[Dict[str, Any], None]
) -> Union[ResponseType, None]:
    """
    Sets the pubseries of an edition.

    Args:
        session (Any): The session object for database operations.
        edition (Edition): The edition object to update.
        data (Any): The data containing the new pubseries information.
        old_values (Union[Dict[str, Any], None]): The old values of the
                                                  edition object before the
                                                  update.

    Returns:
        Union[ResponseType, None]: If the pubseries was updated successfully,
                                   returns None. Otherwise, returns a
                                   ResponseType object with an error message.
    """
    if data["pubseries"] != edition.pubseries:
        ps_id = None
        if old_values is not None:
            old_values["Kustantajan sarja"] = (edition.pubseries.name
                                               if edition.pubseries else '')
        if (data["pubseries"] != "" and data["pubseries"] is not None and
                isinstance(data["pubseries"], str)):
            # User added a new pubseries. Front returns this as a string
            # in the bookseries field so we need to create a new pubseries
            # to the # database first.
            if edition.publisher_id:
                ps_id = add_pubseries(data["pubseries"],
                                      edition.publisher_id)
        else:
            if (data["pubseries"] == "" or data["pubseries"] is None or
                    data["pubseries"]["name"] == "" or
                    data["pubseries"]["name"] is None):
                # User cleared the field -> remove pubseries
                edition.pubseries_id = None
                return None
            ps_id = check_int(data["pubseries"]["id"])
            if ps_id is not None:
                ps = session.query(Pubseries)\
                    .filter(Pubseries.id == ps_id).first()
                if not ps:
                    app.logger.error('_set_pubseries: Pubseries not found. '
                                     f'id={ps_id}')
                    return ResponseType('Kustantajan sarjaa ei löydy. '
                                        f'id={ps_id}',
                                        HttpResponseCode.BAD_REQUEST.value)
        edition.pubseries_id = ps_id
    return None


def get_edition(edition_id: int) -> Any:
    """
    Gets an edition from the database.

    Args:
        edition_id (int): The ID of the edition to be retrieved.

    Returns:
        Any: The retrieved edition or None if not found.
    """
    session = new_session()
    edition = session.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        app.logger.error("Edition not found. id={edition_id}")
        return ResponseType("Painosta ei löydy.",
                            HttpResponseCode.BAD_REQUEST.value)
    schema = EditionSchema()
    retval = schema.dump(edition)
    return ResponseType(retval, HttpResponseCode.OK.value)


# Save new edition to database. Params requires work_id parameter.
def create_edition(params: Any) -> ResponseType:
    """
    Creates a new edition based on the provided parameters.

    Args:
        params (Any): The parameters for creating the edition.

    Returns:
        ResponseType: The response containing the created edition ID or an
                      error message.
    """
    session = new_session()
    data = params["data"]

    if "work_id" not in data:
        app.logger.error("Work_id not found.")
        return ResponseType("Teoksen id (work_id) puuttuu.",
                            HttpResponseCode.BAD_REQUEST.value)

    # Check that work exists
    work_id = check_int(data["work_id"],
                        zeros_allowed=False,
                        negative_values=False)
    if not work_id:
        app.logger.error(
            'create_edition: Invalid work_id. '
            f'work_id={data["work_id"]}'
        )
        return ResponseType(f'Virheellinen teoksen id. id={data["work_id"]}',
                            HttpResponseCode.BAD_REQUEST.value)
    work = session.query(Work).filter(Work.id == work_id).first()
    if not work:
        app.logger.error(
            'Work not found. id={data["work_id"]}'
        )
        return ResponseType(f'Teosta ei löydy. id={data["work_id"]}',
                            HttpResponseCode.BAD_REQUEST.value)

    bindings = session.query(BindingType).all()
    formats = session.query(Format).all()

    edition = Edition()
    if "title" in data:
        edition.title = data["title"]
    if "subtitle" in data:
        edition.subtitle = data["subtitle"]
    # Check that pubyear exists (required)
    if "pubyear" not in data:
        app.logger.error("Pubyear not found.")
        return ResponseType("Julkaisuvuosi (pubyear) puuttuu.",
                            HttpResponseCode.BAD_REQUEST.value)
    pubyear: Union[int, None] = check_int(value=data["pubyear"])
    if not pubyear:
        app.logger.error(
            'create_edition: Invalid pubyear. '
            f'pubyear={data["pubyear"]}'
        )
        return ResponseType(
            f'Julkaisuvuosi on virheellinen. pubyear={data["pubyear"]}',
            HttpResponseCode.BAD_REQUEST.value
        )
    edition.pubyear = pubyear
    if "editionnum" in data:
        editionnum = check_int(data["editionnum"])
        # if not editionnum:
        #     app.logger.error(
        #         'create_edition: Invalid edition number. edition '
        #         f'number={data["editionnum"]}'
        #     )
        #     return ResponseType(
        #         'Painosnumero on virheellinen. '
        #         f'Painosnumero={data["editionnum"]}',
        #         HttpResponseCode.BAD_REQUEST.value
        #     )
        edition.editionnum = editionnum
    if "version" in data:
        version = check_int(data["version"])
        if not version:
            version = 1
        edition.version = version
    if "publisher" in data and data["publisher"] is not None:
        result = _set_publisher(session, edition, data, None)
        if result:
            return result

    if "isbn" in data:
        isbn = data["isbn"]
        if isbn not in [None, ""]:
            if not check_isbn(data["isbn"]):
                app.logger.error(
                    'Invalid ISBN. '
                    f'ISBN={isbn}'
                )
                return ResponseType('Virheellinen ISBN.',
                                    HttpResponseCode.BAD_REQUEST.value)
        elif isbn == "":
            isbn = None
        edition.isbn = isbn

    # Publisher's series, not required
    if "pubseries" in data:
        result = _set_pubseries(session, edition, data, None)
        if result is not None:
            app.logger.error('Failed to set pubseries for new edition')
            return result

    if "pubseriesnum" in data:
        edition.pubseriesnum = check_int(data["pubseriesnum"])
    if "coll_info" in data:
        # This is not really used anywhere, but it's here for completeness
        edition.coll_info = data["coll_info"]
    if "pages" in data:
        edition.pages = check_int(data["pages"], negative_values=False)
    if "binding" in data and "id" in data["binding"]:
        # Invalid binding id will just set binding to None
        edition.binding_id = check_int(
            data["binding"]["id"], allowed=[b.id for b in bindings]
        )
    else:
        edition.binding_id = bindings[0].id

    if "format" in data and data["format"] is not None:
        # Invalid format id will just set format to None
        edition.format_id = check_int(
            data["format"]["id"], allowed=[f.id for f in formats]
        )
    else:
        edition.format_id = formats[0].id

    if "size" in data:
        edition.size = check_int(data["size"], negative_values=False)
    if "dustcover" in data:
        dustcover: Union[int, None] = check_int(data["dustcover"],
                                                allowed=[1, 2, 3])
        if dustcover:
            edition.dustcover = dustcover
        else:
            # Default value
            edition.dustcover = 1
    if "coverimage" in data:
        coverimage: Union[int, None] = check_int(data["coverimage"],
                                                 allowed=[1, 2, 3])
        if coverimage:
            edition.coverimage = coverimage
        else:
            # Default value
            edition.coverimage = 1

    if "misc" in data:
        edition.misc = data["misc"]
    if "imported_string" in data:
        edition.imported_string = data["imported_string"]

    if "verified" in data:
        edition.verified = data["verified"]

    try:
        session.add(edition)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        app.logger.error(f"{e}")
        return ResponseType("Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Create Part. This requires edition to exist.
    part = Part()
    part.edition_id = edition.id
    part.work_id = work_id
    try:
        session.add(part)
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        app.logger.error(f"{e}")
        return ResponseType("Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Contributors require a part.
    if "contributors" in data:
        contributors = get_work_contributors(session, part.work_id)
        for contrib in data["contributors"]:
            if ("person" in contrib and "id" in contrib["person"] and
                    contrib["person"]["id"] != 0):
                contributors.append(contrib)
        update_edition_contributors(session, edition, contributors)
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        app.logger.error({e})
        return ResponseType("Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session, obj=edition, action="Uusi")
    session.commit()

    return ResponseType(str(edition.id), HttpResponseCode.CREATED.value)


# Save changes to edition to database.
def update_edition(params: Any) -> ResponseType:
    """ Update edition in database. """
    retval = ResponseType("", HttpResponseCode.OK.value)
    session = new_session()
    old_values = {}
    data = params["data"]
    edition_id = check_int(data["id"])

    edition = session.query(Edition).filter(Edition.id == edition_id).first()
    if not edition:
        app.logger.error(f"update_edition: Edition {edition_id} not found.")
        return ResponseType(f"Painosta {edition_id} ei löydy.",
                            HttpResponseCode.NOT_FOUND.value)

    bindings = session.query(BindingType).all()
    formats = session.query(Format).all()

    # Title, required field, cannot be empty
    if "title" in data and str_differ(data["title"], edition.title):
        if not edition.title or len(edition.title) == 0:
            app.logger.error("update_edition: Title is empty.")
            return ResponseType("Otsikko ei voi olla tyhjä.",
                                HttpResponseCode.BAD_REQUEST.value)
        old_values["Nimeke"] = edition.title
        edition.title = data["title"]

    # Subtitle, not required
    if "subtitle" in data and str_differ(data["subtitle"], edition.subtitle):
        old_values["Alaotsikko"] = edition.subtitle
        subtitle: Union[str, None] = data["subtitle"]
        if subtitle == "":
            subtitle = None
        edition.subtitle = subtitle

    # Pubyear, required field
    if "pubyear" in data:
        pubyear = check_int(data['pubyear'])
        if pubyear is not None:
            if pubyear != edition.pubyear:
                old_values["Kustannusvuosi"] = edition.pubyear
            edition.pubyear = pubyear
        else:
            app.logger.error("update_edition: Pubyear is empty.")
            return ResponseType("Julkaisuvuosi ei voi olla tyhjä.",
                                HttpResponseCode.BAD_REQUEST.value)

    # Publisher, required field. Has to exist in database.
    if "publisher" in data and data["publisher"] is not None:
        result = _set_publisher(session, edition, data, old_values)
        if result:
            return result

    editionnum = check_int(data["editionnum"])
    # if editionnum is None:
    #     app.logger.error("update_edition: Invalid editionnum.")
    #     return ResponseType("Virheellinen painosnumero.",
    #                         HttpResponseCode.BAD_REQUEST.value)
    old_values["Painosnro"] = edition.editionnum
    edition.editionnum = editionnum

    # Version (laitos), not required
    if "version" in data:
        if data["version"] == "":
            data["version"] = None
        if data["version"] != edition.version:
            version = check_int(data["version"])
            if version is None and data["version"] is not None:
                # Trying to set a value but it's not an integer
                app.logger.error("update_edition: Invalid version.")
                return ResponseType("Virheellinen laitos.",
                                    HttpResponseCode.BAD_REQUEST.value)
            # Either removing value (version=None) or setting a new one
            old_values["Laitosnro"] = edition.version
            edition.version = version

    # ISBN, not required
    if "isbn" in data and str_differ(data["isbn"], edition.isbn):
        old_values["ISBN"] = edition.isbn
        isbn: Union[str, None] = data["isbn"]
        if isbn == "" or isbn is None:
            isbn = None
        else:
            if not check_isbn(isbn):
                app.logger.error("update_edition: Invalid ISBN: {isbn}.")
                return ResponseType("Virheellinen ISBN.",
                                    HttpResponseCode.BAD_REQUEST.value)
        edition.isbn = isbn

    # Number of pages, not required
    if "pages" in data and data["pages"] != edition.pages:
        pages = check_int(data["pages"], negative_values=False)
        if pages is None and data["pages"] is not None:
            # Trying to set a value but it's not an integer
            app.logger.error("update_edition: Invalid pages.")
            return ResponseType("Virheellinen sivumäärä.",
                                HttpResponseCode.BAD_REQUEST.value)
        # Either removing value or setting a new one
        old_values["Sivuja"] = edition.pages
        edition.pages = pages

    # Binding type, required field. Has to exist in database.
    if "binding" in data and data["binding"] is not None:
        if data["binding"]["id"] != edition.binding_id:
            binding_id = check_int(
                data["binding"]["id"], allowed=[b.id for b in bindings]
            )
            if binding_id is None:
                app.logger.error("update_edition: Invalid binding.")
                return ResponseType("Virheellinen sidonta.",
                                    HttpResponseCode.BAD_REQUEST.value)
            old_values["Sidonta"] = edition.binding.name
            edition.binding_id = binding_id

    # Edition format, required field. Has to exist in database.
    if ("format" in data
            and data["format"] is not None
            and "id" in data["format"]
            and data["format"]["id"] != edition.format_id):
        format_id = check_int(
            data["format"]["id"], allowed=[f.id for f in formats]
        )
        if format_id is None:
            app.logger.error("update_edition: Invalid format.")
            return ResponseType("Virheellinen formaatti.",
                                HttpResponseCode.BAD_REQUEST.value)
        old_values["Formaatti"] = edition.format.name
        edition.format_id = format_id

    # Size (height in cm), not required
    if "size" in data and data["size"] != edition.size:
        size = check_int(data["size"], negative_values=False)
        if size is None and data["size"] is not None:
            # Trying to set a value but it's not an integer
            app.logger.error("update_edition: Invalid size.")
            return ResponseType("Virheellinen koko.",
                                HttpResponseCode.BAD_REQUEST.value)
        # Either removing value or setting a new one
        old_values["Koko"] = edition.size
        edition.size = size

    # Print location, not required
    if ("printedin" in data and
            str_differ(data["printedin"], edition.printedin)):
        old_values["Painopaikka"] = edition.printedin
        printedin: Union[str, None] = data["printedin"]
        if printedin == "":
            printedin = None
        edition.printedin = printedin

    # Publisher's series, not required
    if "pubseries" in data:
        result = _set_pubseries(session, edition, data, old_values)
        if result:
            return retval

    # Publisher's series number, not required
    if "pubseriesnum" in data and data["pubseriesnum"] != edition.pubseriesnum:
        pubseriesnum = check_int(data["pubseriesnum"])
        if pubseriesnum is None and data["pubseriesnum"] is not None:
            # Trying to set a value but it's not an integer
            app.logger.error("update_edition: Invalid pubseriesnum.")
            return ResponseType("Virheellinen sarjan numero.",
                                HttpResponseCode.BAD_REQUEST.value)
        old_values["Kustantajan sarjan numero"] = edition.pubseriesnum
        edition.pubseriesnum = pubseriesnum

    # Whether the book has a dustcover, not required
    if "dustcover" in data and data["dustcover"] != edition.dustcover:
        dustcover = check_int(data["dustcover"], allowed=[1, 2, 3])
        if dustcover is None:
            app.logger.error("update_edition: Invalid dustcover.")
            return ResponseType("Virheellinen kansipaperin tyyppi.",
                                HttpResponseCode.BAD_REQUEST.value)
        if edition.dustcover == 1:
            old_value = "Ei tietoa"
        elif edition.dustcover == 2:
            old_value = "Kyllä"
        else:
            old_value = "Ei"
        old_values["Kansipaperi"] = old_value
        edition.dustcover = dustcover

    # Whether the book has a cover image, not required.
    # This is used for hardcovers only.
    if "coverimage" in data and data["coverimage"] != edition.coverimage:
        coverimage = check_int(data["coverimage"], allowed=[1, 2, 3])
        if coverimage is None:
            app.logger.error("update_edition: Invalid coverimage.")
            return ResponseType("Virheellinen kansikuvan tyyppi.",
                                HttpResponseCode.BAD_REQUEST.value)
        if edition.coverimage == 1:
            old_value = "Ei tietoa"
        elif edition.coverimage == 2:
            old_value = "Ei"
        else:
            old_value = "Kyllä"
        old_values["Ylivetokansi"] = old_value
        edition.coverimage = coverimage

    # Miscellanous notes, not required
    if "misc" in data and str_differ(data["misc"], edition.misc):
        old_values["Muuta"] = edition.misc
        misc: Union[str, None] = data["misc"]
        if misc == "":
            misc = None
        edition.misc = misc

    # Holds string where data was originally extracted from. Also used for
    # source.
    if ("imported_string" in data
            and str_differ(data["imported_string"], edition.imported_string)):
        old_values["Lähde"] = edition.imported_string
        imported_string = data["imported_string"]
        if imported_string == "":
            imported_string = ''
        edition.imported_string = imported_string

    if "verified" in data and data["verified"] != edition.verified:
        if edition.verified:
            old_values["Tarkastettu"] = "Kyllä"
        else:
            old_values["Tarkastettu"] = "Ei"
        edition.verified = data["verified"]

    if "contributors" in data:
        if contributors_have_changed(edition.contributions,
                                     data["contributors"]):
            changes = update_edition_contributors(
                session, edition, data["contributors"]
            )
            if changes:
                # We check for invalid values in updateEditionContributors and
                # only log this if there were any updates.
                old_values["Tekijät"] = get_contributors_string(
                    edition.contributions, ContributorTarget.EDITION)

    if len(old_values) == 0:
        # No changes
        session.rollback()
        return retval

    log_changes(session=session,
                obj=edition,
                action="Päivitys",
                old_values=old_values)

    try:
        session.add(edition)
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error("update_edition: " + str(exp))
        return ResponseType(
            "update_edition: Tietokantavirhe. id={edition.id}.",
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error("update_edition: " + str(exp))
        return ResponseType("update_edition: Tietokantavirhe. id={edition.id}",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return retval


def get_bindings() -> ResponseType:
    """
    Retrieves all bindings from the database.

    Returns
    -------
    ResponseType
        A ResponseType object containing the retrieved bindings.
    """
    session = new_session()
    try:
        bindings = session.query(BindingType).all()
    except SQLAlchemyError as exp:
        app.logger.error("binding_get_all: " + str(exp))
        return ResponseType("binding_get_all: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = BindingBriefSchema(many=True)
        retval = schema.dump(bindings)
    except exceptions.MarshmallowError as exp:
        app.logger.error("binding_get_all: " + str(exp))
        return ResponseType("binding_get_all: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def delete_edition(session: Any, edition_id: int) -> bool:  # noqa: C901
    """
    Deletes an edition from the database.

    Args:
        session (Any): The database session.
        edition_id (int): The ID of the edition to be deleted.

    Returns:
        bool: True if the edition was successfully deleted, False otherwise.
    """
    try:
        parts = session.query(Part).filter(Part.edition_id == edition_id).all()
        for part in parts:
            session.query(Contributor)\
              .filter(Contributor.part_id == part.id).delete()
            session.delete(part)
        session.query(EditionImage).filter(
            EditionImage.edition_id == edition_id
        ).delete()
        session.query(EditionLink)\
            .filter(EditionLink.edition_id == edition_id)\
            .delete()
        session.query(EditionPrice).filter(
            EditionPrice.edition_id == edition_id
        ).delete()
        session.query(Edition).filter(Edition.id == edition_id).delete()
    except SQLAlchemyError as exp:
        app.logger.error("delete_edition: " + str(exp))
        return False
    return True


def edition_delete(edition_id: str) -> ResponseType:
    """
    Deletes an edition with the given edition_id.

    Args:
        edition_id (str): The ID of the edition to be deleted.

    Returns:
        ResponseType: The response type indicating the success or failure of
                      the deletion.
    """
    session = new_session()
    old_values = {}
    int_id = check_int(edition_id, zeros_allowed=False, negative_values=False)
    if int_id is None:
        app.logger.error("edition_delete: Invalid id. id={id}")
        return ResponseType("edition_delete: Virheellinen id.",
                            HttpResponseCode.BAD_REQUEST.value)

    edition = session.query(Edition).filter(Edition.id == int_id).first()
    if not edition:
        app.logger.error(
            "edition_delete: Edition not found. id={editionId}"
        )
        return ResponseType("edition_delete: Painosta ei löydy.",
                            HttpResponseCode.BAD_REQUEST.value)

    if not edition.version:
        version = "1"
    else:
        version = str(edition.version)
    old_values["Painos"] = (
        "-Painos: " + str(edition.editionnum) + ", Laitos: " + version
    )
    log_id = log_changes(
        session=session, obj=edition, action="Poisto", old_values=old_values
    )
    success = delete_edition(session, int_id)  # type: ignore
    if not success:
        if log_id != 0:
            # Delete invalid Log line
            session.query(Log).filter(Log.id == log_id).delete()
        session.rollback()
        app.logger.error("Exception in edition_delete, id={edition_id}")
        return ResponseType("edition_delete: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.commit()

    return ResponseType("Poisto onnistui.", HttpResponseCode.OK.value)


def edition_image_upload(editionid: str, image: FileStorage) -> ResponseType:
    """
    Uploads an image for a specific edition.

    Args:
        editionid (str): The ID of the edition.
        image (FileStorage): The image file to be uploaded.

    Returns:
        ResponseType: The response object indicating the status of the upload.
    """
    old_values: Dict[str, Union[str, None]] = {}
    int_id = check_int(editionid,
                       zeros_allowed=False,
                       negative_values=False)

    if int_id is None:
        return ResponseType("edition_image_upload: Virheellinen id.",
                            HttpResponseCode.BAD_REQUEST.value)
    image_name = image.filename

    if image_name is None or image_name == "":
        return ResponseType("edition_image_upload: Kuvan nimi puuttuu.",
                            HttpResponseCode.BAD_REQUEST.value)
    assert image_name is not None

    if not allowed_image(image_name):
        return ResponseType("edition_image_upload: Virheellinen kuvan tyyppi.",
                            HttpResponseCode.BAD_REQUEST.value)

    filename = secure_filename(image_name)
    image.save(os.path.join(app.config["BOOKCOVER_SAVELOC"], filename))

    session = new_session()
    file_loc = app.config["BOOKCOVER_DIR"] + filename
    edition_image = EditionImage(edition_id=int_id, image_src=file_loc)
    old_values["Kansikuva"] = f"Lisätty: {edition_image.image_src}"
    try:
        session.add(edition_image)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f"edition_image_upload, id={int_id}: \
                          {exp}")
        return ResponseType("edition_image_upload: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    edition = session.query(Edition).filter(Edition.id == int_id).first()
    log_changes(session=session,
                obj=edition,
                action="Päivitys",
                old_values=old_values)
    session.commit()
    return ResponseType("Kuvan lisäys onnistui.", HttpResponseCode.OK.value)


def edition_image_delete(editionid: str, imageid: str) -> ResponseType:
    """Delete image from edition.
    @param editionid: Edition id
    @param imageid: Image id
    """
    session = new_session()

    int_id = check_int(editionid,
                       zeros_allowed=False,
                       negative_values=False)
    if int_id is None:
        return ResponseType("edition_image_delete: Virheellinen painoksen id.",
                            HttpResponseCode.BAD_REQUEST.value)
    image_id = check_int(imageid, zeros_allowed=False, negative_values=False)
    if image_id is None:
        return ResponseType("edition_image_delete: Virheellinen kuvan id.",
                            HttpResponseCode.BAD_REQUEST.value)

    edition = session.query(Edition).filter(Edition.id == int_id).first()
    edition_image = session.query(EditionImage)\
        .filter(EditionImage.id == image_id)\
        .first()
    if edition_image is None:
        return ResponseType("edition_image_delete: Kuvaa ei löydy.",
                            HttpResponseCode.BAD_REQUEST.value)

    old_values = {}
    old_values["Kansikuva"] = edition_image.image_src
    log_id = log_changes(
        session=session, obj=edition, action="Poisto", old_values=old_values
    )
    if log_id == 0:
        app.logger.error('edition_image_delete: Failed to log changes.')

    try:
        session.delete(edition_image)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        if log_id != 0:
            # Delete invalid Log line
            session.query(Log).filter(Log.id == log_id).delete()
        app.logger.error(f"edition_image_delete: {exp}")
        return ResponseType("edition_image_delete: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType("Kuvan poisto onnistui.", HttpResponseCode.OK.value)


def edition_shorts(edition_id: str) -> ResponseType:
    """
    Retrieves a list of short stories for a given edition.

    Args:
        edition_id (str): The ID of the edition.

    Returns:
        ResponseType: A response object containing the list of short stories.
    """
    session = new_session()
    try:
        shorts = session.query(ShortStory)\
            .join(Part)\
            .filter(Part.edition_id == edition_id)\
            .filter(Part.shortstory_id == ShortStory.id)\
            .distinct()\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'edition_shorts(): {str(exp)}')
        return ResponseType('edition_shorts: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = ShortBriefSchema(many=True)
        retval = schema.dump(shorts)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'edition_shorts(): {str(exp)}')
        return ResponseType('edition_shorts: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_latest_editions(count: int) -> ResponseType:
    """
    Retrieves the latest editions from the database.

    Args:
        count (int): The number of editions to retrieve.

    Returns:
        ResponseType: The response object containing the list of editions.
    """
    session = new_session()
    try:
        editions = session.query(Edition)\
            .order_by(Edition.id.desc())\
            .limit(count)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_latest_editions: {str(exp)}')
        return ResponseType('get_latest_editions: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = EditionBriefSchema(many=True)
        retval = schema.dump(editions)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Exception in get_latest_editions(): {str(exp)}')
        return ResponseType('get_latest_editions: Tietokantavirhe',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def editionowner_get(editionid: int, userid: int) -> ResponseType:
    """
    Get the owner of an edition.
    """
    retval = []
    session = new_session()
    try:
        edition = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == userid)\
            .filter(UserBook.condition_id > 0)\
            .filter(UserBook.condition_id < 6)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionowner_get: {str(exp)}")
    try:
        schema = UserBookSchema()
        if edition:
            retval = schema.dump(edition)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f"editionowner_get: {str(exp)}")
        return ResponseType("editionowner_get: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def editionowner_getowned(userid: int, wishlist: bool = False) -> ResponseType:
    """
    Get books owned by user.
    """
    books = None
    retval = []
    session = new_session()
    stmt = 'SELECT userbook.description, edition.id as edition_id, '
    stmt += 'edition.title, edition.version, '
    stmt += 'edition.editionnum, edition.pubyear, bookcondition.value, '
    stmt += 'work.author_str, publisher_id as publisher_id, '
    stmt += 'publisher.name as publisher_name, '
    stmt += 'work.id as work_id, '
    stmt += 'bookcondition.name as condition_name '
    stmt += 'FROM userbook '
    stmt += 'JOIN edition on userbook.edition_id = edition.id '
    stmt += 'JOIN bookcondition on userbook.condition_id = bookcondition.id '
    stmt += 'JOIN part on edition.id = part.edition_id '
    stmt += 'AND part.shortstory_id IS NULL '
    stmt += 'JOIN work on part.work_id = work.id '
    stmt += 'LEFT JOIN publisher on edition.publisher_id = publisher.id '
    stmt += 'WHERE userbook.user_id = ' + str(userid) + ' '
    if (wishlist is False):
        stmt += 'and userbook.condition_id > 0 and userbook.condition_id <= 5 '
    else:
        stmt += 'and userbook.condition_id = 6 '
    stmt += 'ORDER BY author_str, title, pubyear'

    try:
        books = session.execute(stmt).all()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionowner_getowned: {str(exp)}")
    try:

        if books:
            for book in books:
                description = book[0]
                edition_id = book[1]
                title = book[2]
                version = book[3]
                editionnum = book[4]
                pubyear = book[5]
                value = book[6]
                author_str = book[7]
                publisher_id = book[8]
                publisher_name = book[9]
                work_id = book[10]
                condition_name = book[11]
                retval.append({'description': description,
                               'edition_id': edition_id,
                               'title': title,
                               'version': version,
                               'editionnum': editionnum,
                               'pubyear': pubyear,
                               'value': value,
                               'author_str': author_str,
                               'publisher_id': publisher_id,
                               'publisher_name': publisher_name,
                               'work_id': work_id,
                               'condition_name': condition_name
                               })
    except exceptions.MarshmallowError as exp:
        app.logger.error(f"editionowner_getowned: {str(exp)}")
        return ResponseType("editionowner_getowned: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def editionowner_add(params: dict) -> ResponseType:
    """
    Add or update the owner of an edition.
    """

    # Check parameters
    try:
        editionid = check_int(params["editionid"])
        userid = check_int(params["userid"])
        condition = check_int(params["condition"])
    except (ValueError, TypeError):
        return ResponseType("Invalid parameters.",
                            HttpResponseCode.BAD_REQUEST.value)
    if not editionid or not userid or not condition:
        return ResponseType("Invalid parameters.",
                            HttpResponseCode.BAD_REQUEST.value)
    if (condition < 1 or condition > 5):
        return ResponseType("Invalid parameters.",
                            HttpResponseCode.BAD_REQUEST.value)

    session = new_session()
    try:
        userbook = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == userid)\
            .filter(UserBook.condition_id > 0)\
            .filter(UserBook.condition_id <= 5)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionowner_add: {str(exp)}")

    if not userbook:
        app.logger.error(
            f"editionowner_add: Userbook not found. id={editionid}")
        return ResponseType("editionowner_add: Omistajatietoa ei käydy.",
                            HttpResponseCode.BAD_REQUEST.value)

    try:
        userbook.condition_id = condition
        if 'description' in params:
            userbook.description = params['description']
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f"editionowner_add: {str(exp)}")
        return ResponseType("editionowner_add: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(None, HttpResponseCode.OK.value)


def editionowner_update(params: dict) -> ResponseType:
    """
    Add or update the owner of an edition.
    """
    # Check parameters
    try:
        editionid = check_int(params["edition_id"])
        userid = check_int(params["user_id"])
    except (ValueError, TypeError):
        return ResponseType("Invalid parameters.",
                            HttpResponseCode.BAD_REQUEST.value)

    if not editionid or not userid:
        return ResponseType("Invalid parameters.",
                            HttpResponseCode.BAD_REQUEST.value)

    session = new_session()
    try:
        userbook = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == userid)\
            .filter(UserBook.condition_id > 0)\
            .filter(UserBook.condition_id <= 5)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionowner_update: {str(exp)}")
        return ResponseType("editionowner_update: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not userbook:
        userbook = UserBook()
        userbook.edition_id = editionid
        userbook.user_id = userid
        session.add(userbook)

    if 'condition' in params:
        condition = check_int(params["condition"]["value"])
        if (not condition or condition < 1 or condition > 5):
            app.logger.error(
                f"editionowner_update: Invalid condition. {condition}")
            return ResponseType("Invalid parameters.",
                                HttpResponseCode.BAD_REQUEST.value)
        cond = session.query(BookCondition)\
            .filter(BookCondition.value == condition)\
            .first()
        if (cond):
            userbook.condition_id = cond.id
    if 'description' in params:
        userbook.description = params['description']

    try:
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionowner_update: {str(exp)}")
        session.rollback()
        return ResponseType("editionowner_update: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType("OK", HttpResponseCode.OK.value)


def editionowner_list(editionid: int) -> ResponseType:
    """
    List the owners of an edition.
    """
    session = new_session()
    try:
        users = session.query(User)\
            .join(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == User.id)\
            .filter(UserBook.condition_id > 0)\
            .filter(UserBook.condition_id <= 5)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionowner_list: {str(exp)}")

    try:
        schema = User(many=True)  # type: ignore
        retval = schema.dump(users.owners)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f"editionowner_list: {str(exp)}")
        return ResponseType("editionowner_list: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def editionowner_remove(editionid: int, userid: int) -> ResponseType:
    """
    Remove the owner of an edition.
    """
    session = new_session()
    try:
        userbook = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == userid)\
            .filter(UserBook.condition_id > 0)\
            .filter(UserBook.condition_id <= 5)\
            .first()
        if userbook:
            session.delete(userbook)
            session.commit()

    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f"editionowner_remove: {str(exp)}")
        return ResponseType("editionowner_remove: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(None, HttpResponseCode.OK.value)


def editionwishlist_get(editionid: int) -> ResponseType:
    """
    Get the wishlist owners of an edition.

    Args:
        editionid (int): The ID of the edition.

    Returns:
        ResponseType: The API response containing the owners of the edition.
    """
    session = new_session()
    try:
        userbooks = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.condition == 6)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f"editionwishlist_get: {str(exp)}")
        return ResponseType("editionwishlist_get: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = UserBook(many=True)
        retval = schema.dump(userbooks)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f"editionwishlist_get: {str(exp)}")
        return ResponseType("editionwishlist_get: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def editionwishlist_add(editionid: int, userid: int) -> ResponseType:
    """
    Add a book to the user's wishlist.

    Args:
        editionid (int): The ID of the book edition.
        userid (int): The ID of the user.

    Returns:
        ResponseType: A response containing the result of the operation.
    """
    session = new_session()
    ub = session.query(UserBook)\
        .filter(UserBook.edition_id == editionid)\
        .filter(UserBook.user_id == userid)\
        .filter(UserBook.condition_id == 6)\
        .first()

    if ub:
        return ResponseType(None, HttpResponseCode.OK.value)

    try:
        userbook = UserBook(edition_id=editionid,
                            user_id=userid,
                            condition_id=6)
        session.add(userbook)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f"editionwishlist_add: {str(exp)}")
        return ResponseType("editionwishlist_add: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(None, HttpResponseCode.OK.value)


def editionwishlist_remove(editionid: int, userid: int) -> ResponseType:
    """
    Remove user from edition's wishlist.

    Args:
    editionid (int): Id of the edition.
    userid (int): Id of the user.

    Returns:
    ResponseType: Result of the operation.
    """
    session = new_session()
    try:
        userbook = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == userid)\
            .filter(UserBook.condition_id == 6)\
            .first()
        if userbook:
            session.delete(userbook)
            session.commit()

    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f"editionwishlist_remove: {str(exp)}")
        return ResponseType("editionwishlist_remove: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(None, HttpResponseCode.OK.value)


def editionwishlist_user(editionid: int, userid: int) -> ResponseType:
    """
    Checks if given user (userid) has given edition (editionid) in their
    wishlist.

    Args:
    editionid (int): The id of the edition.
    userid (int): The id of the user.

    Returns:
    ResponseType: A JSON response containing a boolean value indicating if the
    edition is in the users wishlist.
    """
    session = new_session()
    try:
        ub = session.query(UserBook)\
            .filter(UserBook.edition_id == editionid)\
            .filter(UserBook.user_id == userid)\
            .filter(UserBook.condition_id == 6)\
            .first()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f"editionwishlist_user: {str(exp)}")
        return ResponseType("editionwishlist_user: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    retval = json.dumps({'wishlisted': ub is not None})
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_edition_work(edition_id: int) -> ResponseType:
    """
    Get the work ID for a given edition ID.

    Args:
        edition_id (int): The ID of the edition.

    Returns:
        ResponseType: Response containing the work ID or error message.
    """

    session = new_session()

    try:
        edition = session.query(Edition).filter(Edition.id == edition_id)\
            .first()

        if not edition:
            return ResponseType(
                f'Painosta ei löytynyt tunnuksella: {edition_id}',
                status=HttpResponseCode.NOT_FOUND.value
            )

        if not edition.work[0].id:
            return ResponseType(
                f'Painoksella {edition_id} ei ole liitettyä teosta',
                status=HttpResponseCode.NOT_FOUND.value
            )

        return ResponseType(edition.work[0].id, HttpResponseCode.OK.value)

    except Exception as e:
        app.logger.error(f'get_edition_work: Database error: {e}')
        return ResponseType(
            'Tietokantavirhe haettaessa teosta.',
            status=HttpResponseCode.INTERNAL_SERVER_ERROR.value
        )
    finally:
        session.close()
