from sqlalchemy.sql.expression import desc
from app import app
from flask import (render_template, request, redirect, url_for,
                   make_response, jsonify, Response)
from flask_login import login_required, current_user
from app.orm_decl import (AwardCategories, Person, Work, Bookseries,
                          Edition, Part, Genre, WorkGenre, ShortStory,
                          BindingType, Part, WorkTag, Tag,
                          Language, Contributor, WorkLink, Award, AwardCategory,
                          Awarded)
from app.forms import (WorkForm, StoryForm, EditionForm)
from sqlalchemy import func
import json
from .route_helpers import *
from typing import Any, List, Dict, Optional


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
        edition.subtitle = work.subtitle
        edition.pubyear = work.pubyear
        session.add(edition)
        session.commit()
        part = Part()
        part.work_id = work.id
        part.edition_id = edition.id
        part.title = work.title
        session.add(part)
        session.commit()


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
                         .join(Contributor, Contributor.role_id == 1)\
                         .join(Part)\
                         .filter(Contributor.person_id == Person.id,
                                 Contributor.part_id == Part.id,
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
def work(workid: Any) -> Any:
    """ Popup has a form to add authors. """
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
    types: List[str] = [''] * 4
    types[work.type] = 'checked'
    stories = session.query(ShortStory)\
        .join(Part)\
        .filter(Part.shortstory_id == ShortStory.id)\
        .filter(Part.work_id == workid)\
        .group_by(Part.shortstory_id)\
        .all()

    award_list = session.query(Award)\
        .join(AwardCategories)\
        .filter(AwardCategories.award_id == Award.id)\
        .join(AwardCategory)\
        .filter(AwardCategory.id == AwardCategories.category_id)\
        .filter(AwardCategory.type == 1)\
        .all()

    award_categories = session.query(AwardCategory)\
                              .filter(AwardCategory.type == 1)\
                              .all()

    form = WorkForm(request.form)
    form_story = StoryForm(request.form)
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

    awards_db = session.query(Award).all()
    awards = [(a.id, a.name) for a in awards_db]
    categories_db = session.query(AwardCategory).all()
    categories = [(c.id, c.name) for c in categories_db]

    if request.method == 'GET':
        form.id.data = work.id
        form.title.data = work.title
        form.subtitle.data = work.subtitle
        form.orig_title = work.orig_title
        form.pubyear = work.pubyear
        form.bookseriesnum.data = work.bookseriesnum
        form.bookseriesorder.data = work.bookseriesorder
        form.misc.data = work.misc
        form.description.data = work.description
        form.source.data = work.imported_string

    elif form.validate_on_submit():
        fields: List[str] = []
        if work.title != form.title.data:
            work.title = form.title.data
            fields.append('Otsikko')
        if work.subtitle != form.subtitle.data:
            work.subtitle = form.subtitle.data
            fields.append('Alaotsikko')
        if work.orig_title != form.orig_title.data:
            work.orig_title = form.orig_title.data
            fields.append('Alkup.nimi')
        if work.pubyear != form.pubyear.data:
            work.pubyear = form.pubyear.data
            fields.append('Julkaisuvuosi')
        if work.bookseriesnum != form.bookseriesnum.data:
            work.bookseriesnum = form.bookseriesnum.data
            fields.append('Kirjasarjan numero')
        work.bookseriesorder = form.bookseriesorder.data
        if work.misc != form.misc.data:
            work.misc = form.misc.data
            fields.append('Muuta')
        if (work.description != form.description.data and
                (work.description is not None or form.description.data != '')):
            work.description = form.description.data
            fields.append('Kuvaus')
        work.imported_string = form.source.data
        if work.type != form.type.data:
            work.type = form.type.data
            fields.append('Tyyppi')
        work.author_str = work.update_author_str()
        session.add(work)
        session.commit()
        # Save awards
        existing_awards = awards_to_data(work.awards)
        if form.awards.data[0]['name'] == '':
            # This is a bit ugly, but seems like editing the form list is not
            # possible. This fixes the issue that if there are no awards
            # then form.awards.data includes an empty item so dynamic_changed
            # returns true even if nothing has changed. This creates a new
            # log item every time such a page is saved.
            # Same fix is needed for every item using the same system, e.g.
            # links field below.
            existing_awards.insert(0, form.awards.data[0])
        if dynamic_changed(existing_awards, form.awards.data):
            fields.append('Palkinnot')

            session.query(Awarded)\
                .filter(Awarded.work_id == work.id).delete()

            for award in form.awards.data:
                if award['award_id']:
                    aw = Awarded(work_id=work.id,
                                 year=award['year'],
                                 award_id=award['award_id'],
                                 category_id=award['category_id'])
                    session.add(aw)
            session.commit()

        # Save links
        links = links_to_data(work.links)
        if form.links.data[0]['link'] == '':
            links.insert(0, form.links.data[0])
        if dynamic_changed(links, form.links.data):
            fields.append('Linkit')

            session.query(WorkLink)\
                .filter(WorkLink.work_id == work.id).delete()

            for link in form.links.data:
                if link['link']:
                    if len(link['link']) > 0:
                        wl = WorkLink(work_id=work.id,
                                      link=link['link'],
                                      description=link['description'])
                        session.add(wl)
            session.commit()
        # Reload data so changes are updated to view
        log_change(session, work, fields=fields)
    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')

    title = f'SuomiSF - {work.author_str}: {work.title}'

    return render_template('work.html', work=work,
                           form=form,
                           prev_book=prev_book, next_book=next_book,
                           types=types,
                           title=title,
                           awards=awards,
                           categories=categories,
                           award_list=award_list,
                           award_categories=award_categories)


@ app.route('/new_work', methods=['POST', 'GET'])
# @login_required  # type: ignore
# @admin_required
def new_work() -> Any:
    session = new_session()

    form = WorkForm()

    if request.method == 'GET':
        form.hidden_author_id.data = 0
        form.hidden_author_name.data = ''
        form.hidden_editor_id.data = 0
        form.hidden_editor_name.data = ''
    elif form.validate_on_submit():
        types: List[str] = [''] * 4
        types[1] = 'checked'
        form.hidden_author_id.data = form.authors.data
        form.hidden_editor_id.data = form.editors.data
        return render_template('work.html',
                               work=_create_new_work(session, form),
                               form=form, types=types,
                               next_book=None, prev_book=None)
    else:
        app.logger.debug("Errors: {}".format(form.errors))

    return render_template('new_work.html', form=form)


@ app.route('/add_edition/<workid>', methods=["POST", "GET"])
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
    authors = session.query(Contributor, Contributor.role_id == 1)\
        .join(Part)\
        .filter(Contributor.part_id == Part.id)\
        .filter(Part.work_id == workid)\
        .distinct(Contributor.part_id)\
        .all()
    for author in authors:
        part = Part(work_id=workid, edition_id=edition.id)
        session.add(part)
        session.commit()
        auth = Contributor(
            part_id=part.id, person_id=author.person_id, role_id=1)
        session.add(auth)
        session.commit()
    session.commit()

    form = EditionForm(request.form)

    editors = session.query(Person)\
        .join(Contributor, Contributor.role_id == 3)\
        .join(Part, Part.id == Contributor.part_id)\
        .filter(Person.id == Contributor.person_id)\
        .filter(Part.edition_id == editionid)\
        .all()
    translators = session.query(Person)\
        .join(Contributor, Contributor.role_id == 2)\
        .filter(Person.id == Contributor.person_id)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id,
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


@ app.route('/save_authors_to_work', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_authors_to_work() -> Any:
    session = new_session()

    (workid, people_ids) = get_select_ids(request.form)

    existing_people = session.query(Contributor)\
        .filter(Contributor.role_id == 1)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.work_id == workid)\
        .filter(Part.shortstory_id == None)\
        .all()

    parts = session.query(Part)\
        .filter(Part.work_id == workid)\
        .filter(Part.shortstory_id == None)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_people],
        [int(x['id']) for x in people_ids])

    for id in to_remove:
        auth = session.query(Contributor)\
            .filter(Contributor.role_id == 1)\
            .filter(Contributor.person_id == id)\
            .join(Part)\
            .filter(Part.id == Contributor.part_id)\
            .filter(Part.work_id == workid)\
            .filter(Part.shortstory_id == None)\
            .first()
        session.delete(auth)
    for id in to_add:
        for part in parts:
            auth = Contributor(part_id=part.id, person_id=id, role_id=1)
            session.add(auth)

    session.commit()

    work = session.query(Work).filter(Work.id == workid).first()
    work.update_author_str()
    session.add(work)
    session.commit()
    log_change(session, work, fields=['Kirjoittajat'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/authors_for_work/<workid>')
def authors_for_work(workid: Any) -> Any:
    session = new_session()

    people = session.query(Person)\
        .join(Contributor, Contributor.role_id == 1)\
        .filter(Person.id == Contributor.person_id)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.work_id == workid)\
        .filter(Part.shortstory_id == None)\
        .all()

    return(make_people_response(people))


@ app.route('/save_bookseries_to_work', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_bookseries_to_work() -> Any:
    session = new_session()

    (workid, series_ids) = get_select_ids(request.form)
    work = session.query(Work)\
        .filter(Work.id == workid)\
        .first()

    work.bookseries_id = series_ids[0]['id']
    session.add(work)
    session.commit()
    log_change(session, work, fields=['Kirjasarja'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/bookseries_for_work/<workid>')
def bookseries_for_work(workid: Any) -> Any:
    session = new_session()

    bookseries = session.query(Bookseries)\
        .join(Work)\
        .filter(Bookseries.id == Work.bookseries_id)\
        .filter(Work.id == workid)\
        .first()
    retval: List[Dict[str, str]] = []
    if bookseries:
        obj: Dict[str, str] = {}
        obj['id'] = str(bookseries.id)
        obj['text'] = bookseries.name
        retval.append(obj)

    return Response(json.dumps(retval))


@ app.route('/genres_for_work/<workid>')
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


@ app.route('/save_genres_to_work', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_genres_to_work() -> Any:
    session = new_session()

    (workid, genre_ids) = get_select_ids(request.form)

    existing_genres = session.query(Genre)\
        .join(WorkGenre)\
        .filter(Genre.id == WorkGenre.genre_id)\
        .filter(WorkGenre.work_id == workid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.id for x in existing_genres],
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
    work = session.query(Work).filter(Work.id == workid).first()
    log_change(session, work, fields=['Genret'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/tags_for_work/<workid>')
def tags_for_work(workid: Any) -> Any:
    session = new_session()

    tags = session.query(Tag)\
        .join(WorkTag)\
        .filter(WorkTag.tag_id == Tag.id)\
        .filter(WorkTag.work_id == workid)\
        .all()

    retval: List[Dict[str, str]] = []
    if tags:
        for tag in tags:
            obj: Dict[str, str] = {}
            obj['id'] = str(tag.id)
            obj['text'] = tag.name
            retval.append(obj)

    return Response(json.dumps(retval))


@ app.route('/save_tags_to_work', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
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
    work = session.query(Work).filter(Work.id == workid).first()
    log_change(session, work, fields=['Asiasanat'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/language_for_work/<workid>')
def language_for_work(workid: Any) -> Any:
    session = new_session()
    work = session.query(Work).filter(Work.id == workid).first()

    retval: List[Dict[str, str]] = []

    if work.language is not None:
        language = session.query(Language)\
            .join(Work)\
            .filter(Language.id == Work.language, Work.id == workid)\
            .first()
        obj: Dict[str, str] = {}
        obj['id'] = str(language.id)
        obj['text'] = language.name
        retval.append(obj)

    return Response(json.dumps(retval))


@ app.route('/save_language_to_work', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_language_to_work() -> Any:
    lang_id: int

    (workid, lang_ids) = get_select_ids(request.form)

    session = new_session()

    if str(lang_ids[0]['id']) == str(lang_ids[0]['text']):
        # Language was not found in db
        (lang_id, _) = create_new_language(
            session, lang_ids[0]['text'])
    else:
        lang = session.query(Language)\
            .filter(Language.id == lang_ids[0]['id'])\
            .first()
        lang_id = lang.id

    work = session.query(Work)\
        .filter(Work.id == workid)\
        .first()
    work.language = lang_id
    session.add(work)
    session.commit()
    log_change(session, work, fields=['Kieli'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/stories_for_work/<workid>')
def stories_for_work(workid: Any) -> Any:
    session = new_session()

    stories = session.query(ShortStory)\
        .join(Part)\
        .filter(Part.work_id == workid)\
        .filter(Part.shortstory_id == ShortStory.id)\
        .all()

    retval: List[Dict[str, str]] = []

    if stories:
        for story in stories:
            obj: Dict[str, str] = {}
            obj['id'] = str(story.id)
            if story.author_str:
                obj['text'] = story.author_str + ': ' + story.title
            else:
                obj['text'] = story.title
            retval.append(obj)

    return Response(json.dumps(retval))


@ app.route('/save_stories_to_work', methods=["POST"])
@ login_required  # type: ignore
@ admin_required
def save_stories_to_work() -> Any:
    session = new_session()

    (workid, story_ids) = get_select_ids(request.form)

    existing_stories = session.query(ShortStory)\
        .join(Part)\
        .filter(Part.work_id == workid)\
        .filter(Part.shortstory_id == ShortStory.id)\
        .all()

    existing_story_ids = [x.id for x in existing_stories]

    story_ids = create_new_shortstory_to_work(session, story_ids, workid)

    (to_add, to_remove) = get_join_changes(
        existing_story_ids, [int(x['id']) for x in story_ids])

    editions = session.query(Edition)\
        .join(Part)\
        .filter(Part.edition_id == Edition.id)\
        .filter(Part.work_id == workid)\
        .all()

    for id in to_remove:
        contributors = session.query(Contributor.person_id,
                                     Contributor.role_id,
                                     Contributor.real_person_id,
                                     Contributor.description)\
            .join(Part)\
            .filter(Part.id == Contributor.part_id)\
            .filter(Part.shortstory_id == id)\
            .distinct()\
            .all()
        parts = session.query(Part)\
            .filter(Part.work_id == workid)\
            .filter(Part.shortstory_id == id)\
            .all()
        for part in parts:
            session.query(Contributor).filter(
                Contributor.part_id == part.id).delete()
            session.delete(part)
        session.commit()
        # Make sure there is a contributor row in case short story
        # has no more links to works.
        existing_parts = session.query(Part)\
            .filter(Part.shortstory_id == id)\
            .all()
        if len(existing_parts) == 0:
            part = Part(shortstory_id=id)
            session.add(part)
            session.commit()
            for (person, role, real_person, description) in contributors:
                contributor = Contributor(
                    part_id=id,
                    person_id=person,
                    role_id=role,
                    real_person_id=real_person,
                    description=description)
                session.add(contributor)
            session.commit()
    for id in to_add:
        # authors = session.query(Person)\
        #     .join(Contributor, Contributor.role_id == 1)\
        #     .filter(Person.id == Contributor.person_id)\
        #     .join(Part)\
        #     .filter(Part.id == Contributor.part_id)\
        #     .filter(Part.shortstory_id == id)\
        #     .all()

        # Search for every contribution related to this shortstory
        contribs = session.query(Contributor)\
            .join(Part)\
            .filter(Part.id == Contributor.part_id)\
            .filter(Part.shortstory_id == id)\
            .all()

        # Remove duplicate contributions
        all_contribs: Dict[str, List[Dict[str, int]]] = {}
        for c in contribs:
            if c.person_id not in all_contribs:
                all_contribs[c.person_id] = []
            if c.role_id not in all_contribs[c.person_id]:
                all_contribs[c.person_id].append(
                    {"person_id": c.person_id,
                     "role_id": c.role_id})

        for edition in editions:
            part = Part(work_id=workid, edition_id=edition.id,
                        shortstory_id=id)
            session.add(part)
            session.commit()
            if contribs:
                for person in all_contribs.values():
                    for role in person:
                        author = Contributor(
                            person_id=role["person_id"],
                            part_id=part.id,
                            role_id=role["role_id"])
                        session.add(author)
                session.commit()
                #update_creators_to_story(session, id)

    session.commit()
    work = session.query(Work).filter(Work.id == workid).first()
    log_change(session, work, fields=['Novellit'])

    # for edition in editions:
    #     order_num: int = 1
    #     for story in story_ids:
    #         part = session.query(Part)\
    #             .filter(Part.shortstory_id == story['id'],
    #                     Part.work_id == workid,
    #                     Part.edition_id == edition.id)\
    #             .all()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/add_edition_to_work/<workid>')
@ login_required  # type: ignore
@ admin_required
def add_edition_to_work(workid: Any) -> Any:
    session = new_session()

    work = session.query(Work).filter(Work.id == workid).all()
    editions = session.query(Edition)\
        .join(Part)\
        .filter(Part.edition_id == Edition.id, Part.work_id == workid)\
        .order_by(Edition.pubyear)\
        .all()
    latest_edition = editions[-1]
    if latest_edition.editionnum:
        editionnum = latest_edition.editionnum + 1
        version = latest_edition.version
    else:
        editionnum = 1
        version = 1
    edition = Edition(title=work[0].title,
                      subtitle=work[0].subtitle,
                      pubyear=work[0].pubyear,
                      binding_id=1,
                      format_id=latest_edition.format_id,
                      publisher_id=latest_edition.publisher_id,
                      editionnum=editionnum,
                      version=version)

    session.add(edition)
    session.commit()

    part = Part(work_id=workid, edition_id=edition.id)
    session.add(part)
    session.commit()

    authors = session.query(Person)\
        .join(Contributor, Contributor.role_id == 1)\
        .filter(Person.id == Contributor.person_id)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.work_id == workid)\
        .filter(Part.shortstory_id == None)\
        .distinct()\
        .all()

    for author in authors:
        auth = Contributor(part_id=part.id, person_id=author.id, role_id=1)
        session.add(auth)
    session.commit()

    stories = session.query(Part)\
        .filter(Part.work_id == workid, Part.shortstory_id != None)\
        .all()

    for story in stories:
        part = Part(work_id=workid, edition_id=edition.id,
                    shortstory_id=story.shortstory_id)
        session.add(part)
    session.commit()

    log_change(session, edition, action='Uusi')

    return redirect(url_for('edition', editionid=edition.id))


def create_first_edition(session: Any, work: Work, publisher_id: Optional[int] = None) -> int:
    edition = Edition()
    edition.title = work.title
    edition.subtitle = work.subtitle
    edition.pubyear = work.pubyear
    edition.binding_id = 1
    edition.editionnum = 1
    if publisher_id:
        edition.publisher_id = publisher_id

    session.add(edition)
    session.commit()
    return edition.id


@ app.route('/new_work_for_person/<personid>', methods=['POST', 'GET'])
@ login_required  # type: ignore
@ admin_required
def new_work_for_person(personid: Any) -> Any:
    session = new_session()
    person = session.query(Person).filter(Person.id == personid).first()

    form = WorkForm(request.form)

    if request.method == 'GET':
        form.hidden_author_id.data = personid
        form.hidden_author_name.data = person.name
    elif form.validate_on_submit():
        types: List[str] = [''] * 4
        types[1] = 'checked'
        return render_template('work.html',
                               work=_create_new_work(session, form),
                               form=form, types=types,
                               next_book=None, prev_book=None)

    return render_template('new_work.html', form=form)


def _create_new_work(session: Any, form: Any) -> Any:
    work = Work()
    work.title = form.title.data
    work.subtitle = form.subtitle.data
    work.orig_title = form.orig_title.data
    work.pubyear = form.pubyear.data
    work.type = 1
    session.add(work)
    session.commit()

    edition_id = create_first_edition(session, work, form.publisher.data)
    part = Part(work_id=work.id, edition_id=edition_id)
    session.add(part)
    session.commit()
    if form.hidden_author_id.data:
        author = Contributor(
            person_id=form.hidden_author_id.data, part_id=part.id, role_id=1)
        session.add(author)
    if form.hidden_editor_id.data:
        editor = Contributor(
            person_id=form.hidden_editor_id.data, part_id=part.id, role_id=3)
        session.add(editor)
    session.commit()
    update_work_creators(session, work.id)
    log_change(session, work, action='Uusi')
    return work
