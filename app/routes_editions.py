from werkzeug.datastructures import FileStorage
from app import app
from sqlalchemy import func
from flask import (render_template, request, redirect, url_for,
                   make_response, jsonify, Response)
from flask_login import login_required
from app.orm_decl import (Person, Publisher, Edition,
                          Part, Pubseries,
                          Work, ShortStory, BindingType,
                          EditionImage, Bookseries, Contributor)
from app.forms import (EditionForm)
from werkzeug.utils import secure_filename
from .route_helpers import *
from typing import Dict, Any, List, Optional
import json
import os


# def save_edition(session: Any, form: Any, edition: Any) -> None:
#     edition.title = form.title.data
#     edition.subtitle = form.subtitle.data
#     edition.pubyear = form.pubyear.data
#     edition.editionnum = form.edition.data
#     edition.version = form.version.data
#     translator = session.query(Person).filter(Person.name ==
#                                               form.translators.data).first()
#     editor = session.query(Person).filter(Person.name ==
#                                           form.editors.data).first()
#     publisher = session.query(Publisher).filter(Publisher.name ==
#                                                 form.publisher.data).first()
#     if form.pubseries.data == 0:
#         edition.pubseries_id = None
#     else:
#         edition.pubseries_id = form.pubseries.data
#     edition.publisher_id = publisher.id
#     edition.pubseriesnum = form.pubseriesnum.data
#     edition.pages = form.pages.data
#     edition.cover_id = form.cover.data
#     edition.binding_id = form.binding.data
#     edition.format_id = form.format.data
#     edition.size = form.size.data
#     # edition.artist_id = artist.id
#     edition.isbn = form.isbn.data
#     edition.misc = form.misc.data
#     edition.image_src = form.image_src.data
#     session.add(edition)
#     session.commit()

#     parts: List[Part] = []
#     if form.id == 0:
#         # Add parts
#         for work in form.workid.split(','):
#             part = Part(edition_id=edition.id, work_id=work)
#             session.add(part)
#             parts.append(part)
#         session.commit()
#     else:
#         parts = session.query(Part)\
#                        .filter(Part.edition_id == edition.id)\
#                        .all()

#     # Save translator and editor
#     for part in parts:
#         if translator:
#             transl = session.query(Contributor, Contributor.role_id == 2)\
#                 .filter(Contributor.part_id == part.id, Contributor.person_id == translator.id)\
#                 .first()
#             if not transl:
#                 transl = Contributor(
#                     part_id=part.id, person_id=translator.id, role_id=2)
#                 session.add(transl)
#         if editor:
#             ed = session.query(Contributor, Contributor.role_id == 3)\
#                         .join(Part, Part.id == Contributor.part_id)\
#                         .filter(Part.edition_id == edition.id, Contributor.person_id == editor.id)\
#                         .first()
#             if not ed:
#                 ed = Contributor(part_id=part.id,
#                                  person_id=editor.id, role_id=3)
#                 session.add(ed)
#     session.commit()


@app.route('/edition/<editionid>', methods=['GET', 'POST'])
def edition(editionid: Any) -> Any:
    stories = []
    session = new_session()
    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()

    work = session.query(Work)\
        .join(Part)\
        .filter(Part.edition_id == editionid).first()

    authors = session.query(Person)\
                     .join(Contributor.person)\
                     .filter(Contributor.role_id == 1)\
                     .join(Part, Part.id == Contributor.part_id)\
                     .filter(Part.edition_id == editionid)\
                     .all()

    other_editions = [x for x in work.editions if x.id != int(editionid)]

    translators = session.query(Person)\
        .join(Contributor.person)\
        .filter(Contributor.role_id == 2)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id,
                Part.edition_id == editionid)\
        .all()
    editors = session.query(Person)\
        .join(Contributor.person)\
        .filter(Contributor.role_id == 3)\
        .join(Part, Part.id == Contributor.part_id)\
        .filter(Part.edition_id == editionid)\
        .all()

    stories = session.query(ShortStory)\
        .join(Part)\
        .filter(Part.shortstory_id == ShortStory.id)\
        .filter(Part.edition_id == editionid)\
        .group_by(Part.shortstory_id)\
        .all()

    bookseries = session.query(Bookseries)\
        .join(Work)\
        .filter(Bookseries.id == work.bookseries_id,
                Work.id == work.id)\
        .first()

    prev_book = None
    next_book = None
    if bookseries:
        books_in_series = session.query(Work)\
                                 .filter(Work.bookseries_id == bookseries.id)\
                                 .order_by(Work.bookseriesorder, Work.pubyear)\
                                 .all()
        for idx, book in enumerate(books_in_series):
            if book.id == int(work.id):
                if len(books_in_series) > 1:
                    if idx == 0:
                        # First in series
                        next_book = books_in_series[1]
                    elif idx == len(books_in_series) - 1:
                        # Last in series
                        prev_book = books_in_series[-2]
                    else:
                        prev_book = books_in_series[idx-1]
                        next_book = books_in_series[idx+1]
                    break

    binding_count = session.query(func.count(BindingType.id)).first()
    bindings: List[str] = [''] * (binding_count[0] + 1)
    if edition.binding_id:
        bindings[edition.binding_id] = 'checked'
    dustcovers: List[str] = [''] * 4
    if edition.dustcover:
        dustcovers[edition.dustcover] = 'checked'
    else:
        dustcovers[1] = 'checked'
    coverimages: List[str] = [''] * 4
    if edition.coverimage:
        coverimages[edition.coverimage] = 'checked'
    else:
        coverimages[1] = 'checked'

    form = EditionForm(request.form)

    if request.method == 'GET':
        form.id.data = edition.id
        form.title.data = edition.title
        form.subtitle.data = edition.subtitle
        form.pubyear.data = edition.pubyear
        form.editionnum.data = edition.editionnum
        form.version.data = edition.version
        form.isbn.data = edition.isbn
        form.pubseriesnum = edition.pubseriesnum
        form.pages.data = edition.pages
        form.size.data = edition.size
        form.misc.data = edition.misc
        form.binding.data = edition.binding_id
        form.imported_string.data = edition.imported_string

    elif form.validate_on_submit():
        changes: List[str] = []
        if edition.title != form.title.data:
            changes.append('Nimeke')
            edition.title = form.title.data
        if edition.subtitle != form.subtitle.data:
            changes.append('Alaotsikko')
            edition.subtitle = form.subtitle.data
        if edition.pubyear != form.pubyear.data:
            changes.append('Julk.vuosi')
            edition.pubyear = form.pubyear.data
        if edition.editionnum != form.editionnum.data:
            changes.append('Painosnro')
            edition.editionnum = form.editionnum.data
        if edition.version != form.version.data:
            changes.append('Laitosnro')
            edition.version = form.version.data
        if edition.isbn != form.isbn.data:
            changes.append('ISBN')
            edition.isbn = form.isbn.data
        if edition.pubseriesnum != form.pubseriesnum.data:
            changes.append('Julk.sarjan nro')
            edition.pubseriesnum = form.pubseriesnum.data
        if edition.pages != form.pages.data:
            changes.append('Sivumäärä')
            edition.pages = form.pages.data
        if edition.size != form.size.data:
            changes.append('Koko')
            edition.size = form.size.data
        if edition.misc != form.misc.data:
            changes.append('Muita tietoja')
            edition.misc = form.misc.data
        if edition.binding_id != form.binding.data:
            changes.append('Sidonta')
            edition.binding_id = form.binding.data
        if edition.dustcover != form.dustcover.data:
            changes.append('Paperikansi')
            edition.dustcover = form.dustcover.data
        if edition.coverimage != form.coverimage.data:
            changes.append('Kansikuvallinen')
        edition.imported_string = form.imported_string.data
        edition.coverimage = form.coverimage.data

        session.add(edition)
        session.commit()
        log_change(session, edition,
                   fields=changes)
    else:
        app.logger.debug('Errors: {}'.format(form.errors))
        print('Errors: {}'.format(form.errors))

    if edition.version and edition.version > 1:
        ed = f'{edition.version}.laitos'
    else:
        ed = f'{edition.editionnum}.painos'
    title = f'SuomiSF - {edition.title}: {ed}'

    return render_template('edition.html', form=form,
                           edition=edition, authors=authors,
                           translators=translators, editors=editors,
                           stories=stories, bindings=bindings,
                           dustcovers=dustcovers, coverimages=coverimages,
                           other_editions=other_editions,
                           title=title,
                           prev_book=prev_book,
                           next_book=next_book)

# Translator


@app.route('/translators_for_edition/<editionid>')
def translators_for_edition(editionid: Any) -> Any:
    session = new_session()

    people = session.query(Person)\
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 2)\
                    .join(Part)\
                    .filter(Part.id == Contributor.part_id)\
                    .filter(Part.edition_id == editionid)\
                    .all()

    return(make_people_response(people))


@app.route('/save_translators_to_edition', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_translator_to_edition() -> Any:
    session = new_session()

    (editionid, people_ids) = get_select_ids(request.form)

    existing_people = session.query(Contributor)\
        .filter(Contributor.role_id == 2)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.edition_id == editionid)\
        .filter(Part.shortstory_id == None)\
        .all()

    parts = session.query(Part)\
                   .filter(Part.edition_id == editionid)\
                   .all()

    for x in existing_people:
        print(x)

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people],
        [int(x['id']) for x in people_ids])

    for id in to_remove:
        tr = session.query(Contributor)\
            .filter(Contributor.role_id == 2)\
            .filter(Contributor.person_id == id)\
            .join(Part)\
            .filter(Part.id == Contributor.part_id)\
            .filter(Part.edition_id == editionid)\
            .filter(Part.shortstory_id == None)\
            .first()
        session.delete(tr)
    for id in to_add:
        for part in parts:
            tr = Contributor(part_id=part.id, person_id=id, role_id=2)
            session.add(tr)

    session.commit()
    edition = session.query(Edition).filter(Edition.id == editionid).first()
    log_change(session, obj=edition, fields=['Kääntäjät'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)

# Editor


@ app.route('/editors_for_edition/<editionid>')
def editors_for_edition(editionid: Any) -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 3)\
                    .join(Part, Part.id == Contributor.part_id)\
                    .filter(Part.edition_id == editionid)\
                    .filter(Part.shortstory_id == None)\
                    .all()

    return(make_people_response(people))


@ app.route('/save_editors_to_edition', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_editor_to_edition() -> Any:
    session = new_session()
    (editionid, people_ids) = get_select_ids(request.form)
    existing_people = session.query(Contributor)\
        .filter(Contributor.role_id == 3)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.edition_id == editionid)\
        .filter(Part.shortstory_id == None)\
        .all()

    parts = session.query(Part)\
                   .filter(Part.edition_id == editionid)\
                   .filter(Part.shortstory_id == None)\
                   .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people],
        [int(x['id']) for x in people_ids])

    for id in to_remove:
        ed = session.query(Contributor)\
                    .filter(Contributor.role_id == 3)\
                    .filter(Contributor.person_id == id)\
                    .join(Part)\
                    .filter(Part.id == Contributor.part_id)\
                    .filter(Part.edition_id == editionid)\
                    .filter(Part.shortstory_id == None)\
                    .first()
        session.delete(ed)
    for id in to_add:
        for part in parts:
            ed = Contributor(part_id=part.id, person_id=id, role_id=3)
            session.add(ed)

    session.commit()

    works = session.query(Work)\
                   .join(Part)\
                   .filter(Work.id == Part.work_id)\
                   .filter(Part.edition_id == editionid)\
                   .all()
    for work in works:
        work.update_author_str()

    edition = session.query(Edition).filter(Edition.id == editionid).first()
    log_change(session, edition, fields=['Toimittajat'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)
# Pubseries


@app.route('/pubseries_for_edition/<editionid>')
def pubseries_for_edition(editionid: Any) -> Any:
    session = new_session()
    pubseries = session.query(Pubseries)\
                       .join(Edition)\
                       .filter(Pubseries.id == Edition.pubseries_id)\
                       .filter(Edition.id == editionid)\
                       .first()
    retval: List[Dict[str, str]] = []
    if pubseries:
        obj: Dict[str, str] = {'id': pubseries.id, 'text': pubseries.name}
        retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_pubseries_to_edition', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_pubseries_to_edition() -> Any:
    session = new_session()
    (editionid, pubseries_id) = get_select_ids(request.form)
    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()
    edition.pubseries_id = pubseries_id[0]['id']
    session.add(edition)
    session.commit()
    log_change(session, edition, fields=['Julk.sarja'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)

# Publisher


@app.route('/publisher_for_edition/<editionid>')
def publisher_for_edition(editionid: Any) -> Any:
    session = new_session()
    publisher = session.query(Publisher)\
                       .join(Edition)\
                       .filter(Publisher.id == Edition.publisher_id)\
                       .filter(Edition.id == editionid)\
                       .first()
    obj: List[Dict[str, str]] = []
    if publisher:
        obj = [{'id': publisher.id, 'text': publisher.name}]
    return Response(json.dumps(obj))


@ app.route('/save_publisher_to_edition', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_publisher_to_edition() -> Any:
    (editionid, publisher_id) = get_select_ids(request.form)

    session = new_session()

    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()
    edition.publisher_id = publisher_id[0]['id']
    session.add(edition)
    session.commit()
    log_change(session, edition, fields=['Julkaisija'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/save_cover_to_edition', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_cover_to_edition() -> Any:
    pass


@ app.route('/save_format_to_edition', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_format_to_edition() -> Any:
    pass


# Cover upload


def allowed_image(filename: Optional[str]) -> bool:
    if not filename:
        return False
    if not "." in filename:
        return False

    ext = filename.rsplit('.', 10)[1]
    if ext.upper() in ['jpg', 'JPG']:
        return True
    else:
        return False


@app.route('/save_image_to_edition', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_image_to_edition() -> Any:
    if request.method == 'POST':
        image: FileStorage
        id: str = ''
        if request.files:
            id = request.form['id']
            image = request.files['image']
            if image.filename == '':
                return redirect(request.url)
            if allowed_image(image.filename):
                filename = secure_filename(image.filename)  # type: ignore
                image.save(os.path.join(
                    app.config['BOOKCOVER_SAVELOC'], filename))
                session = new_session()
                ei = session.query(EditionImage)\
                            .filter(EditionImage.edition_id == int(id))\
                            .first()
                if ei:
                    ei.image_src = app.config['BOOKCOVER_DIR'] + filename
                else:
                    ei = EditionImage(edition_id=int(id),
                                      image_src=app.config['BOOKCOVER_DIR'] + filename)
                session.add(ei)
                session.commit()
                edition = session.query(Edition).filter(
                    Edition.id == id).first()
                log_change(session, edition, ['Kansikuva'])
                return redirect(request.url)
        else:
            return redirect(request.url)
    return redirect(request.url)


@app.route('/remove_image_from_edition/<editionid>')
@login_required  # type: ignore
@admin_required
def remove_image_from_edition(editionid: Any) -> Any:
    # session = new_session()
    # edition = session.query(Edition).filter(Edition.id == editionid).first()

    # edition.image_src = ''
    # session.add(edition)
    # session.commit()

    return redirect(url_for('edition', editionid=editionid))
