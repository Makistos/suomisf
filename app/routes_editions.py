from sqlalchemy.sql.expression import false
from werkzeug.datastructures import FileStorage
from app import app
from sqlalchemy import func
from flask import (render_template, request, flash, redirect, url_for,
                   make_response, jsonify, Response)
from flask_login import login_required, current_user
from app.orm_decl import (Person, Publisher, Edition,
                          Part, Translator, Editor, Pubseries,
                          Work, ShortStory, Translator, Author, BindingType,
                          PublicationSize)
from app.forms import (EditionForm, EditionEditorForm, EditionTranslatorForm)
from werkzeug.utils import secure_filename
from .route_helpers import *
from typing import Dict, Any, List, Optional
import json
import os


def save_edition(session: Any, form: Any, edition: Any) -> None:
    edition.title = form.title.data
    edition.subtitle = form.subtitle.data
    edition.pubyear = form.pubyear.data
    edition.language = form.language.data
    edition.editionnum = form.edition.data
    edition.version = form.version.data
    translator = session.query(Person).filter(Person.name ==
                                              form.translators.data).first()
    editor = session.query(Person).filter(Person.name ==
                                          form.editors.data).first()
    publisher = session.query(Publisher).filter(Publisher.name ==
                                                form.publisher.data).first()
    if form.pubseries.data == 0:
        edition.pubseries_id = None
    else:
        edition.pubseries_id = form.pubseries.data
    edition.publisher_id = publisher.id
    edition.pubseriesnum = form.pubseriesnum.data
    edition.pages = form.pages.data
    edition.cover_id = form.cover.data
    edition.binding_id = form.binding.data
    edition.format_id = form.format.data
    edition.size_id = form.size.data
    edition.description = form.description.data
    # edition.artist_id = artist.id
    edition.isbn = form.isbn.data
    edition.misc = form.misc.data
    edition.image_src = form.image_src.data
    session.add(edition)
    session.commit()

    parts: List[Part] = []
    if form.id == 0:
        # Add parts
        for work in form.workid.split(','):
            part = Part(edition_id=edition.id, work_id=work)
            session.add(part)
            parts.append(part)
        session.commit()
    else:
        parts = session.query(Part)\
                       .filter(Part.edition_id == edition.id)\
                       .all()

    # Save translator and editor
    for part in parts:
        if translator:
            transl = session.query(Translator)\
                .filter(Translator.part_id == part.id, Translator.person_id == translator.id)\
                .first()
            if not transl:
                transl = Translator(part_id=part.id, person_id=translator.id)
                session.add(transl)
        if editor:
            ed = session.query(Editor)\
                        .filter(Editor.edition_id == edition.id, Editor.person_id == editor.id)\
                        .first()
            if not ed:
                ed = Editor(edition_id=edition.id, person_id=editor.id)
                session.add(ed)
    session.commit()


@app.route('/edit_edition/<editionid>', methods=["POST", "GET"])
def edit_edition(editionid: Any) -> Any:
    session = new_session()
    publisher_series: Any
    publisher: Any
    pubseries: Any
    translators: Any
    editors: Any
    if str(editionid) != '0':
        edition = session.query(Edition)\
            .filter(Edition.id == editionid)\
            .first()
        publisher = session.query(Publisher)\
                           .filter(Publisher.id == edition.publisher_id)\
                           .first()
        translators = session.query(Person)\
                             .join(Translator)\
                             .join(Part)\
                             .filter(Translator.person_id == Person.id)\
                             .filter(Translator.part_id == Part.id,
                                     Part.edition_id == Edition.id,
                                     Edition.id == editionid)\
                             .first()
        editors = session.query(Person)\
                         .join(Editor)\
                         .filter(Editor.person_id == Person.id)\
                         .filter(Editor.edition_id == editionid)\
                         .first()
        pubseries = \
            session.query(Pubseries)\
            .filter(Pubseries.id == edition.pubseries_id)\
            .first()
        if publisher:
            publisher_series = pubseries_list(session, publisher.id)
        else:
            publisher_series = {}
    else:
        edition = Edition()
        publisher = Publisher()
        translators = Translator()
        editors = Editor()
        pubseries = Pubseries()

    form = EditionForm()
    selected_pubseries = '0'
    source = edition.imported_string
    form.cover.choices = cover_list(session)
    form.binding.choices = binding_list(session)
    form.format.choices = format_list(session)
    form.size.choices = size_list(session)

    if request.method == 'GET':
        form.id.data = edition.id
        form.workid.data = ','.join([str(x.id) for x in edition.work])
        form.title.data = edition.title
        form.subtitle.data = edition.subtitle
        form.pubyear.data = edition.pubyear
        form.language.data = edition.language
        form.edition.data = edition.editionnum
        if edition.version:
            form.version.data = edition.version
        if publisher:
            form.publisher.data = publisher.name
        if translators:
            form.translators.data = translators.name
        if editors:
            form.editors.data = editors.name
        if pubseries:
            form.pubseries.data = pubseries.name
        form.pubseriesnum.data = edition.pubseriesnum
        form.pages.data = edition.pages
        form.cover.data = edition.cover_id
        form.binding.data = edition.binding_id
        form.format.data = edition.format_id
        form.size.data = edition.size_id
        form.description.data = edition.description
        # form.artist.data  = artist.name
        form.isbn.data = edition.isbn
        form.misc.data = edition.misc
        form.image_src.data = edition.image_src
        # if pubseries:
        #     i = 0
        #     for idx, s in enumerate(publisher_series):
        #         if s[1] == pubseries.name:
        #             i = s[0]
        #             break
        #     form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series
        #     form.pubseries.default = str(i)
        #     selected_pubseries = str(i)
        # form.translators.data = ', '.join([t.name for t in translators])
        # form.editors.data = ', '.join([e.name for e in editors])
    if form.validate_on_submit():
        save_edition(session, form, edition)
        return redirect(url_for('edition', editionid=edition.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
        # app.logger.debug("pubid={}".format(form.pubseries.data))
    return render_template('edit_edition.html', form=form,
                           source=source)


@app.route('/edition/<editionid>', methods=['GET', 'POST'])
def edition(editionid: Any) -> Any:
    stories = []
    session = new_session()
    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()
    works = session.query(Work)\
                   .join(Part)\
                   .filter(Part.edition_id == editionid).all()
    work_ids = [x.id for x in works]
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .join(Part)\
                     .filter(Part.id == Author.part_id)\
                     .filter(Part.edition_id == editionid)\
                     .all()

    other_editions = session.query(Edition)\
                            .join(Part)\
                            .filter(Part.work_id in work_ids)\
                            .filter(Edition.id != edition.id)\
                            .order_by(Edition.language, Edition.pubyear)\
                            .all()
    translators = session.query(Person)\
                         .join(Translator)\
                         .filter(Person.id == Translator.person_id)\
                         .join(Part)\
                         .filter(Part.id == Translator.part_id,
                                 Part.edition_id == editionid)\
                         .all()
    editors = session.query(Person)\
                     .join(Editor)\
                     .filter(Person.id == Editor.person_id)\
                     .join(Edition)\
                     .filter(Edition.id == Editor.edition_id)\
                     .filter(Edition.id == editionid)\
                     .all()

    stories = session.query(ShortStory)\
                     .join(Part)\
                     .filter(Part.shortstory_id == ShortStory.id)\
                     .filter(Part.edition_id == editionid)\
                     .group_by(Part.shortstory_id)\
                     .all()

    binding_count = session.query(func.count(BindingType.id)).first()
    bindings: List[str] = [''] * (binding_count[0] + 1)
    if edition.binding_id:
        bindings[edition.binding_id] = 'checked'

    form = EditionForm(request.form)

    if request.method == 'GET':
        form.id.data = edition.id
        form.title.data = edition.title
        #form.subtitle.data = edition.subtitle
        form.pubyear.data = edition.pubyear
        form.editionnum.data = edition.editionnum
        form.version.data = edition.version
        form.isbn.data = edition.isbn
        form.pubseriesnum = edition.pubseriesnum
        form.pages.data = edition.pages
        form.description.data = edition.description
        form.misc.data = edition.misc
        form.binding.data = edition.binding_id

    elif form.validate_on_submit():
        edition.title = form.title.data
        #edition.subtitle = form.subtitle.data
        edition.pubyear = form.pubyear.data
        edition.editionnum = form.editionnum.data
        edition.version = form.version.data
        edition.isbn = form.isbn.data
        edition.pubseriesnum = form.pubseriesnum.data
        edition.pages = form.pages.data
        edition.description = form.description.data
        edition.misc = form.misc.data
        edition.binding_id = form.binding.data

        session.add(edition)
        session.commit()
    else:
        app.logger.debug('Errors: {}'.format(form.errors))
        print('Errors: {}'.format(form.errors))

    return render_template('edition.html', form=form,
                           edition=edition, authors=authors,
                           other_editions=other_editions, works=works,
                           translators=translators, editors=editors,
                           stories=stories, bindings=bindings)

# Translator


@app.route('/translators_for_edition/<editionid>')
def translators_for_edition(editionid: Any) -> Any:
    session = new_session()

    people = session.query(Person)\
                    .join(Translator)\
                    .filter(Person.id == Translator.person_id)\
                    .join(Part)\
                    .filter(Part.id == Translator.part_id)\
                    .filter(Part.edition_id == editionid)\
                    .all()

    return(make_people_response(people))


@app.route('/save_translators_to_edition', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_translator_to_edition() -> Any:
    session = new_session()

    (editionid, people_ids) = get_select_ids(request.form)

    existing_people = session.query(Translator)\
        .join(Part)\
        .filter(Part.id == Translator.part_id)\
        .filter(Part.edition_id == editionid)\
        .all()

    parts = session.query(Part)\
                   .filter(Part.edition_id == editionid)\
                   .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people],
        [int(x['id']) for x in people_ids])

    for id in to_remove:
        tr = session.query(Translator)\
                    .filter(Translator.person_id == id)\
                    .join(Part)\
                    .filter(Part.id == Translator.part_id)\
                    .filter(Part.edition_id == editionid)\
                    .first()
        session.delete(tr)
    for id in to_add:
        for part in parts:
            tr = Translator(part_id=part.id, person_id=id)
            session.add(tr)

    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)

# Editor


@ app.route('/editors_for_edition/<editionid>')
def editors_for_edition(editionid: Any) -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(Editor)\
                    .filter(Person.id == Editor.person_id)\
                    .filter(Editor.edition_id == editionid)\
                    .all()

    return(make_people_response(people))


@ app.route('/save_editors_to_edition', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_editor_to_edition() -> Any:
    session = new_session()
    (editionid, people_ids) = get_select_ids(request.form)
    session.commit()

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
    edition.pubseries_id = pubseries_id
    session.add(edition)
    session.commit()

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
    obj: List[Dict[str, str]] = [{'id': publisher.id, 'text': publisher.name}]
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

# Size


@app.route('/size_for_edition/<editionid>', methods=['GET'])
def size_for_edition(editionid: Any) -> Any:
    session = new_session()
    size = session.query(PublicationSize)\
                  .join(Edition)\
                  .filter(PublicationSize.id == Edition.size_id)\
                  .filter(Edition.id == editionid)\
                  .first()

    retval: List[Dict[str, str]] = []
    if size:
        obj: Dict[str, str] = {'id': size.id, 'text': size.name}
        retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_size_to_edition', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_size_to_edition() -> Any:
    (editionid, size_id) = get_select_ids(request.form)

    session = new_session()

    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()
    edition.publisher_id = size_id[0]['id']
    session.add(edition)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)

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
        image: FileStorage = None
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
            edition = session.query(Edition).filter(Edition.id == id).first()
            edition.image_src = app.config['BOOKCOVER_DIR'] + filename
            session.add(edition)
            session.commit()
            return redirect(request.url)
        else:
            return redirect(request.url)
    return redirect(request.url)


@app.route('/remove_image_from_edition/<editionid>')
@login_required  # type: ignore
@admin_required
def remove_image_from_edition(editionid: Any) -> Any:
    session = new_session()
    edition = session.query(Edition).filter(Edition.id == editionid).first()
    edition.image_src = ''
    session.add(edition)
    session.commit()

    return redirect(url_for('edition', editionid=editionid))
