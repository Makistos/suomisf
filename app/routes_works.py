from flask.globals import session
from app import app
from flask import (render_template, request, flash, redirect, url_for,
                   make_response, jsonify, Response)
from flask_login import login_required, current_user
from app.orm_decl import (Person, Work, Bookseries,
                          Edition, Part, Author, Genre, WorkGenre, ShortStory,
                          BindingType, Editor, Translator, Part, WorkTag, Tag)
from app.forms import (WorkAuthorForm, WorkForm,
                       WorkStoryForm, StoryForm, EditionForm)
from sqlalchemy import func
import json
from .route_helpers import *
from typing import Any, List, Dict


def save_work(session: Any, form: Any, work: Any) -> Any:
    author = session.query(Person).filter(Person.name ==
                                          form.author.data).first()
    work.id = form.id.data
    work.title = form.title.data
    work.pubyear = form.pubyear.data
    work.language = form.language.data
    if form.bookseries.data != '':
        bookseries = session.query(Bookseries).filter(Bookseries.name ==
                                                      form.bookseries.data).first()
        work.bookseries_id = bookseries.id
    else:
        work.bookseries_id = None
    work.bookseriesnum = form.bookseriesnum.data
    work.misc = form.misc.data
    work.collection = form.collection.data
    session.add(work)
    session.commit()
    if work.id == 0:
        # New work so needs a row to Edition and Part tables.
        edition = Edition()
        edition.title = work.title
        edition.pubyear = work.pubyear
        edition.language = work.language
        session.add(edition)
        session.commit()
        part = Part()
        part.work_id = work.id
        part.edition_id = edition.id
        part.title = work.title
        session.add(part)
        session.commit()
    save_genres(session, work, form.genre.data)


@app.route('/edit_work/<workid>', methods=["POST", "GET"])
def edit_work(workid: Any) -> Any:
    search_list: Dict[str, Any] = {}
    session = new_session()
    authors = []
    bookseries: Any
    if workid != '0':
        work = session.query(Work)\
                      .filter(Work.id == workid)\
                      .first()
        authors = session.query(Person)\
                         .join(Author)\
                         .join(Part)\
                         .filter(Author.person_id == Person.id,
                                 Author.part_id == Part.id,
                                 Part.work_id == workid)\
                         .all()
        bookseries = session.query(Bookseries)\
                            .join(Work)\
                            .filter(Bookseries.id == work.bookseries_id,
                                    Work.id == workid)\
                            .first()
        bookseriesid = None
        if bookseries:
            bookseriesid = bookseries.id
    else:
        work = Work()

    search_list = {**search_list, **author_list(session)}

    form = WorkForm(request.form)
    form.genre.choices = genre_select(session)
    if request.method == 'GET':
        form.id.data = work.id
        form.title.data = work.title
        form.subtitle.data = work.subtitle
        form.orig_title.data = work.orig_title
        if authors:
            form.author.data = ', '.join([a.name for a in authors])
        form.pubyear.data = work.pubyear
        form.language.data = work.language
        if bookseries:
            form.bookseries.data = bookseries.name
        form.bookseriesnum.data = work.bookseriesnum
        form.bookseriesorder.data = work.bookseriesorder
        form.misc.data = work.misc
        form.image_src.data = work.image_src
        form.description.data = work.description
        form.source.data = work.imported_string
        form.collection.data = work.collection
        form.genre.process_data([str(x.id) for x in work.genres])

    if form.validate_on_submit():
        save_work(session, form, work)  # Save work, edition and part
        return redirect(url_for('work', workid=work.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_work.html', id=work.id, form=form,
                           search_lists=search_list,
                           source=work.imported_string,
                           selected_bookseries=bookseriesid)


@app.route('/work/<workid>', methods=["POST", "GET"])
@login_required  # type: ignore
@admin_required
def work(workid: Any) -> Any:
    """ Popup has a form to add authors. """
    search_list: Dict[str, Any] = {}
    stories: List[Any] = []
    session = new_session()
    work = session.query(Work)\
                  .filter(Work.id == workid)\
                  .first()
    authors = people_for_book(session, workid, 'A')
    bookseries = session.query(Bookseries)\
                        .join(Work)\
                        .filter(Bookseries.id == work.bookseries_id,
                                Work.id == workid)\
                        .first()
    search_list = {**search_list, **author_list(session)}

    stories = session.query(ShortStory)\
        .join(Part)\
        .filter(Part.shortstory_id == ShortStory.id)\
        .filter(Part.work_id == workid)\
        .group_by(Part.shortstory_id)\
        .all()
    form = WorkForm(request.form)
    prev_book = None
    next_book = None
    if bookseries:
        books_in_series = session.query(Work)\
                                 .filter(Work.bookseries_id == bookseries.id)\
                                 .order_by(Work.bookseriesorder, Work.pubyear)\
                                 .all()
        for idx, book in enumerate(books_in_series):
            if book.id == int(workid):
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

    if request.method == 'GET':
        form.id.data = work.id
        form.title.data = work.title
        form.subtitle.data = work.subtitle
        form.orig_title = work.orig_title
        form.pubyear = work.pubyear
        form.bookseriesnum.data = work.bookseriesnum
        form.bookseriesorder.data = work.bookseriesorder
        form.description.data = work.description
        form.source.data = work.imported_string
    elif form.validate_on_submit():
        work.title = form.title.data
        work.subtitle = form.subtitle.data
        work.orig_title = form.orig_title.data
        work.pubyear = form.pubyear.data
        work.bookseriesnum = form.bookseriesnum.data
        work.bookseriesorder = form.bookseriesorder.data
        work.description = form.description.data
        work.imported_string = form.source.data
        session.add(work)
        session.commit()
    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')

    return render_template('work.html', work=work, authors=authors,
                           form=form, stories=stories,
                           prev_book=prev_book, next_book=next_book)


@app.route('/add_edition/<workid>', methods=["POST", "GET"])
def add_edition(workid: Any) -> Any:
    session = new_session()

    works = session.query(Work).filter(Work.id == workid).all()
    edition = Edition(title=works[0].title)
    edition.imported_string = current_user.name
    session.add(edition)
    session.commit()
    editionid = edition.id
    edition = session.query(Edition).filter(Edition.id == editionid).first()

    # Copy authors to edition from work
    authors = session.query(Author)\
                     .join(Part)\
                     .filter(Author.part_id == Part.id)\
                     .filter(Part.work_id == workid)\
                     .distinct(Author.part_id, Author.part_id)\
                     .all()
    for author in authors:
        part = Part(work_id=workid, edition_id=edition.id)
        session.add(part)
        session.commit()
        auth = Author(part_id=part.id, person_id=author.person_id)
        session.add(auth)
        session.commit()
    session.commit()

    form = EditionForm(request.form)

    editors = session.query(Person)\
                     .join(Editor)\
                     .filter(Person.id == Editor.person_id)\
                     .join(Edition)\
                     .filter(Edition.id == Editor.edition_id)\
                     .filter(Edition.id == edition.id)\
                     .all()
    translators = session.query(Person)\
                         .join(Translator)\
                         .filter(Person.id == Translator.person_id)\
                         .join(Part)\
                         .filter(Part.id == Translator.part_id,
                                 Part.edition_id == edition.id)\
                         .all()
    stories = session.query(ShortStory)\
                     .join(Part)\
                     .filter(Part.shortstory_id == ShortStory.id)\
                     .filter(Part.edition_id == edition.id)\
                     .group_by(Part.shortstory_id)\
                     .all()
    binding_count = session.query(func.count(BindingType.id)).first()
    bindings: List[str] = [''] * (binding_count[0] + 1)
    if edition.binding_id:
        bindings[edition.binding_id] = 'checked'

    return render_template('edition.html', form=form,
                           edition=edition, authors=None,
                           other_editions=None, works=works,
                           translators=translators, editors=editors,
                           stories=stories, bindings=bindings)


@app.route('/save_authors_to_work', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_authors_to_work() -> Any:
    session = new_session()

    (workid, people_ids) = get_select_ids(request.form)

    existing_people = session.query(Author)\
        .join(Part)\
        .filter(Part.id == Author.part_id)\
        .filter(Part.work_id == workid)\
        .all()

    parts = session.query(Part)\
                   .filter(Part.work_id == workid)\
                   .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people],
        [int(x['id']) for x in people_ids])

    for id in to_remove:
        auth = session.query(Author)\
            .filter(Author.person_id == id)\
            .join(Part)\
            .filter(Part.id == Author.part_id)\
            .filter(Part.work_id == workid)\
            .first()
        session.delete(auth)
    for id in to_add:
        for part in parts:
            auth = Author(part_id=part.id, person_id=id)
            session.add(auth)

    session.commit()

    update_work_creators(workid)

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/authors_for_work/<workid>')
def authors_for_work(workid: Any) -> Any:
    session = new_session()

    people = session.query(Person)\
                    .join(Author)\
                    .filter(Person.id == Author.person_id)\
                    .join(Part)\
                    .filter(Part.id == Author.part_id)\
                    .filter(Part.work_id == workid)\
                    .all()

    return(make_people_response(people))


@app.route('/save_bookseries_to_work')
@login_required  # type: ignore
@admin_required
def save_bookseries_to_work() -> Any:
    session = new_session()

    (workid, series_ids) = get_select_ids(request.form)
    work = session.query(Work)\
                  .filter(Work.id == workid)\
                  .first()

    work.bookseries_id = series_ids[0]
    session.add(work)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/bookseries_for_work/<workid>')
def bookseries_for_work(workid: Any) -> Any:
    session = new_session()

    bookseries = session.query(Bookseries)\
                        .join(Work)\
                        .filter(Bookseries.id == Work.bookseries_id)\
                        .filter(Work.id == workid)\
                        .all()
    retval: List[Dict[str, str]] = []
    if bookseries:
        obj: Dict[str, str] = {}
        obj['id'] = str(bookseries.id)
        obj['text'] = bookseries.name
        retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/genres_for_work/<workid>')
def genres_for_work(workid: Any) -> Any:
    session = new_session()

    genres = session.query(Genre)\
                    .join(WorkGenre)\
                    .filter(WorkGenre.genre_id == Genre.id)\
                    .filter(WorkGenre.work_id == workid)\
                    .all()

    retval: List[Dict[str, str]] = []
    if genres:
        for genre in genres:
            obj: Dict[str, str] = {}
            obj['id'] = str(genre.id)
            obj['text'] = genre.name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/save_genres_to_work')
@login_required  # type: ignore
@admin_required
def save_genres_to_work() -> Any:
    session = new_session()

    (workid, genre_ids) = get_select_ids(request.form)

    existing_genres = session.query(Genre)\
        .join(WorkGenre)\
        .filter(Genre.id == WorkGenre.genre_id)\
        .filter(WorkGenre.work_id == workid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.genre_id for x in existing_genres],
        [int(x['id']) for x in genre_ids])

    for id in to_remove:
        auth = session.query(WorkGenre)\
            .filter(WorkGenre.genre_id == id)\
            .filter(WorkGenre.work_id == workid)\
            .first()
        session.delete(auth)
    for id in to_add:
        wg = WorkGenre(genre_id=id, work_id=workid)
        session.add(wg)

    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/tags_for_work/<workid>')
def tags_for_work(workid: Any) -> Any:
    session = new_session()

    genres = session.query(Tag)\
                    .join(WorkTag)\
                    .filter(WorkTag.tag_id == Tag.id)\
                    .filter(WorkTag.work_id == workid)\
                    .all()

    retval: List[Dict[str, str]] = []
    if genres:
        for genre in genres:
            obj: Dict[str, str] = {}
            obj['id'] = str(genre.id)
            obj['text'] = genre.name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/save_tags_to_work', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_tags_to_work() -> Any:

    (workid, tag_ids) = get_select_ids(request.form)

    session = new_session()
    tag_ids = create_new_tags(session, tag_ids)

    existing_tags = session.query(WorkTag)\
                           .filter(WorkTag.work_id == workid)\
                           .all()

    (to_add, to_remove) = get_join_changes(
        [x.tag_id for x in existing_tags], [int(x['id']) for x in tag_ids])

    for id in to_remove:
        wt = session.query(WorkTag)\
                    .filter(WorkTag.work_id == workid, WorkTag.tag_id == id)\
                    .first()
        session.delete(wt)
    for id in to_add:
        wt = WorkTag(work_id=workid, tag_id=id)
        session.add(wt)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)
