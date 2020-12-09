from app import app
from flask import render_template, request, flash, redirect, url_for, make_response
from app.orm_decl import (Person, Publisher, Edition, Part, Translator, Editor)
from app.forms import (EditionForm, EditionEditorForm, EditionTranslatorForm)
from .route_helpers import *

def save_edition(session, form, edition):
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
    #edition.artist_id = artist.id
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
def edit_edition(editionid):
    session = new_session()
    publisher_series = {}
    publisher = {}
    pubseries = []
    translators = []
    editors = []
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
        #form.translators.data = ', '.join([t.name for t in translators])
        #form.editors.data = ', '.join([e.name for e in editors])
    if form.validate_on_submit():
        save_edition(session, form, edition)
        return redirect(url_for('edition', editionid=edition.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
        # app.logger.debug("pubid={}".format(form.pubseries.data))
    return render_template('edit_edition.html', form=form,
                           source=source)


@app.route('/edition/<editionid>', methods=['GET', 'POST'])
def edition(editionid):
    stories = []
    session = new_session()
    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()
    works = session.query(Work)\
                   .join(Part)\
                   .filter(Part.edition_id == editionid).all()
    work_ids = [x.id for x in works]
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

    form_tr = EditionTranslatorForm(request.form)
    form_ed = EditionEditorForm(request.form)

    if form_tr.submit_tr.data and form_tr.validate():
        save_translator_to_edition(session, editionid, form_tr.translator.data)
        return redirect(url_for('edition', editionid=editionid))
    if form_ed.submit_ed.data and form_ed.validate():
        for editor in editors:
            save_editor_to_work(session, editor.id, form_ed.editor.data)
        return redirect(url_for('edition', editionid=editionid))

    return render_template('edition.html', edition=edition,
                           other_editions=other_editions, works=works,
                           translators=translators, editors=editors,
                           stories=stories, form_translator=form_tr,
                           form_editor=form_ed)

