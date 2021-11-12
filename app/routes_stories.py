from app import app
from app.orm_decl import (ShortStory, Part,
                          Person, StoryGenre, StoryTag, Edition, Work, Tag, Genre, Contributor, StoryType)
from .route_helpers import *
from flask import (render_template, request, url_for,
                   make_response, jsonify, Response, redirect)
from flask_login import login_required
from app.forms import NewWorkForm, StoryForm
import json
from typing import List, Any, Dict


@app.route('/story/<id>', methods=['GET', 'POST'])
def story(id: Any) -> Any:

    session = new_session()
    story = session.query(ShortStory)\
        .filter(ShortStory.id == id)\
        .first()

    editions = session.query(Edition)\
                      .join(Part)\
                      .filter(Part.shortstory_id == id)\
                      .filter(Part.edition_id == Edition.id)\
                      .all()

    works = session.query(Work)\
                   .join(Part)\
                   .filter(Part.shortstory_id == id)\
                   .filter(Part.work_id == Work.id)\
                   .all()

    authors = session.query(Person)\
                     .distinct(Person.id)\
                     .join(Contributor, Contributor.role_id == 1)\
        .filter(Contributor.person_id == Person.id)\
        .filter(Person.id == Contributor.person_id)\
        .join(Part)\
        .filter(Contributor.part_id == Part.id,
                Part.shortstory_id == id)\
        .all()

    form = StoryForm(request.form)

    if request.method == 'GET':
        form.id.data = story.id
        form.title.data = story.title
        form.orig_title.data = story.orig_title
        form.pubyear.data = story.pubyear
    elif form.validate_on_submit():
        changes: List[str] = []
        if story.title != form.title.data:
            story.title = form.title.data
            changes.append('Nimi')
        if story.orig_title != form.orig_title.data:
            story.orig_title = form.orig_title.data
            changes.append('Alkukielinen nimi')
        if story.pubyear != form.pubyear.data:
            story.pubyear = form.pubyear.data
            changes.append('Alkup. julkaisuvuosi')
        session.add(story)
        session.commit()
        log_change(session, story, fields=changes)
    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')

    return render_template('story.html', id=id, story=story,
                           editions=editions, works=works,
                           authors=authors, form=form)


@app.route('/save_story_title', methods=['GET', 'POST'])
@login_required
@admin_required
def save_story_title() -> Any:
    session = new_session()

    if request.method == 'POST':
        try:
            id = request.form['pk']
            title = request.form['value']

            story = session.query(ShortStory)\
                .filter(ShortStory.id == id)\
                .first()
            story.title = title
            session.add(story)
            session.commit()
        except (KeyError) as exp:
            app.logger.error(f'Exception in save_story_title: {exp}.')
            return make_response(exp, 400)
        return make_response('OK', 200)

    return make_response('Tuntematon kutsu', 400)


@app.route('/save_story_orig_title', methods=['GET', 'POST'])
@login_required
@admin_required
def save_story_orig_title() -> Any:
    session = new_session()

    if request.method == 'POST':
        try:
            id = request.form['pk']
            title = request.form['value']

            story = session.query(ShortStory)\
                .filter(ShortStory.id == id)\
                .first()
            story.orig_title = title
            session.add(story)
            session.commit()
        except (KeyError) as exp:
            app.logger.error(f'Exception in save_story_title: {exp}.')
            return make_response(exp, 400)
        return make_response('OK', 200)

    return make_response('Tuntematon kutsu', 400)


@app.route('/save_story_pubyear', methods=['GET', 'POST'])
@login_required
@admin_required
def save_story_pubyear() -> Any:
    session = new_session()

    if request.method == 'POST':
        try:
            id = request.form['pk']
            try:
                if request.form['value'] == '':
                    pubyear = None
                else:
                    pubyear = int(request.form['value'])
            except ValueError as exp:
                return make_response('Vuosiluvun pitää olla numero', 400)

            story = session.query(ShortStory)\
                .filter(ShortStory.id == id)\
                .first()
            story.pubyear = pubyear
            session.add(story)
            session.commit()
        except (KeyError) as exp:
            app.logger.error(f'Exception in save_story_title: {exp}.')
            return make_response(exp, 400)
        return make_response('OK', 200)

    return make_response('Tuntematon kutsu', 400)


@app.route('/new_story_for_work/<workid>', methods=['POST', 'GET'])
@login_required  # type: ignore
@admin_required
def new_story_for_work(workid: Any) -> Any:
    session = new_session()

    form = StoryForm(request.form)

    if request.method == 'GET':
        form.hidden_work_id.data = workid

    # elif form.validate_on_submit():
    else:
        story = ShortStory()
        story.title = form.title.data
        story.orig_title = form.orig_title.data
        story.pubyear = form.pubyear.data
        story.story_type = 1
        session.add(story)
        session.commit()

        editions = session.query(Edition)\
                          .join(Part)\
                          .filter(Part.edition_id == Edition.id, Part.work_id == workid)\
                          .filter(Part.shortstory_id == None)\
                          .all()
        for edition in editions:
            part = Part(work_id=workid, edition_id=edition.id,
                        shortstory_id=story.id)
            session.add(part)
            session.commit()
            for author in form.authors.data:
                contributor = Contributor(
                    person_id=author, part_id=part.id, role_id=1)
                session.add(contributor)
            session.commit()

        return redirect(url_for('work', workid=workid))

    return render_template('new_story.html', form=form)


@app.route('/save_authors_to_story', methods=["POST"])
@login_required  # type: ignore
@admin_required
def save_authors_to_story() -> Response:
    session = new_session()

    (storyid, people_ids) = get_select_ids(request.form)
    existing_people = session.query(Contributor)\
        .filter(Contributor.role_id == 1)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.shortstory_id == storyid)\
        .all()

    existing_ids = set([int(x.person_id) for x in existing_people])
    (to_add, to_remove) = get_join_changes(
        existing_ids, [int(x['id']) for x in people_ids])

    for id in to_remove:
        auth = session.query(Contributor)\
                      .filter(Contributor.role_id == 1)\
                      .filter(Contributor.person_id == id)\
                      .join(Part)\
                      .filter(Part.id == Contributor.part_id)\
                      .filter(Part.shortstory_id == storyid)\
                      .all()
        for a in auth:
            session.delete(a)
    for id in to_add:
        parts: List[Any] = session.query(Part)\
            .filter(Part.shortstory_id == storyid)\
            .all()
        if not parts:
            story = session.query(ShortStory).filter(
                ShortStory.id == storyid).first()
            part = Part(shortstory_id=storyid, title=story.title)
            session.add(part)
            session.commit()
            parts.append(part)
        for part in parts:
            auth = Contributor(person_id=id, part_id=part.id, role_id=1)
            session.add(auth)

    session.commit()
    story = session.query(ShortStory).filter(ShortStory.id == storyid).first()
    log_change(session, story, fields=['Kirjoittajat'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/authors_for_story/<storyid>', methods=["GET"])
def authors_for_story(storyid):
    session = new_session()
    people = session.query(Person)\
                    .join(Contributor, Contributor.role_id == 1)\
                    .filter(Contributor.person_id == Person.id)\
                    .join(Part)\
                    .filter(Part.shortstory_id == storyid)\
                    .filter(Contributor.part_id == Part.id)\
                    .all()

    retval: List[Dict[str, str]] = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/translators_for_story/<storyid>', methods=['GET'])
def translators_for_story(storyid: Any):
    session = new_session()
    translators = session.query(Person)\
                         .join(Contributor.person)\
                         .filter(Contributor.role_id == 2)\
                         .join(Part)\
                         .filter(Part.id == Contributor.part_id)\
                         .filter(Part.shortstory_id == storyid)\
                         .all()

    retval: List[Dict[str, str]] = []

    if translators:
        for tr in translators:
            obj: Dict[str, str] = {}
            obj['id'] = str(tr.id)
            obj['text'] = tr.alt_name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/save_translators_to_story', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_translator_to_story() -> Any:
    session = new_session()

    (storyid, people_ids) = get_select_ids(request.form)

    existing_people = session.query(Contributor)\
        .filter(Contributor.role_id == 2)\
        .join(Part)\
        .filter(Part.id == Contributor.part_id)\
        .filter(Part.shortstory_id == storyid)\
        .all()

    parts = session.query(Part)\
                   .filter(Part.shortstory_id == storyid)\
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
            .filter(Part.shortstory_id == storyid)\
            .first()
        session.delete(tr)
    for id in to_add:
        for part in parts:
            tr = Contributor(part_id=part.id, person_id=id, role_id=2)
            session.add(tr)

    session.commit()
    story = session.query(ShortStory).filter(ShortStory.id == storyid).first()
    log_change(session, obj=story, fields=['Kääntäjät'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/genres_for_story/<storyid>', methods=["GET"])
def genres_for_story(storyid: Any):
    session = new_session()
    genres = session.query(Genre)\
                    .join(StoryGenre)\
                    .filter(Genre.id == StoryGenre.genre_id)\
                    .filter(StoryGenre.shortstory_id == storyid)\
                    .all()

    retval: List[Dict[str, str]] = []

    if genres:
        for genre in genres:
            obj: Dict[str, str] = {}
            obj['id'] = str(genre.id)
            obj['text'] = genre.name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/save_genres_to_story', methods=["POST"])
@login_required  # type: ignore
@admin_required
def save_genres_to_story() -> Response:
    session = new_session()

    (storyid, genre_ids) = get_select_ids(request.form)

    existing_genres = session.query(Genre)\
        .join(StoryGenre)\
        .filter(Genre.id == StoryGenre.genre_id)\
        .filter(StoryGenre.shortstory_id == storyid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.genre_id for x in existing_genres],
        [int(x['id']) for x in genre_ids])

    for id in to_remove:
        auth = session.query(StoryGenre)\
            .filter(StoryGenre.genre_id == id)\
            .filter(StoryGenre.shortstory_id == storyid)\
            .first()
        session.delete(auth)
    for id in to_add:
        sg = StoryGenre(genre_id=id, shortstory_id=storyid)
        session.add(sg)
    session.commit()
    story = session.query(ShortStory).filter(ShortStory.id == storyid).first()
    log_change(session, story, fields=['Genret'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/tags_for_story/<storyid>', methods=["GET"])
def tags_for_story(storyid: Any) -> Any:
    session = new_session()

    tags = session.query(Tag)\
                  .join(StoryTag)\
                  .filter(Tag.id == StoryTag.tag_id)\
                  .filter(StoryTag.shortstory_id == storyid)\
                  .all()

    retval: List[Dict[str,  str]] = []

    if tags:
        for tag in tags:
            obj: Dict[str, str] = {}
            obj['id'] = str(tag.id)
            obj['text'] = tag.name
            retval.append(obj)

    return Response(json.dumps(retval))


@app.route('/save_tags_to_story', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_tags_to_story() -> Any:

    (storyid, tag_ids) = get_select_ids(request.form)

    session = new_session()
    tag_ids = create_new_tags(session, tag_ids)

    existing_tags = session.query(StoryTag)\
                           .filter(StoryTag.shortstory_id == storyid)\
                           .all()

    (to_add, to_remove) = get_join_changes(
        [x.tag_id for x in existing_tags], [int(x['id']) for x in tag_ids])

    for id in to_remove:
        st = session.query(StoryTag)\
                    .filter(StoryTag.shortstory_id == storyid, StoryTag.tag_id == id)\
                    .first()
        session.delete(st)
    for id in to_add:
        wt = StoryTag(shortstory_id=storyid, tag_id=id)
        session.add(wt)
    session.commit()
    story = session.query(ShortStory).filter(ShortStory.id == storyid).first()
    log_change(session, story, fields=['Asiasanat'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/select_story', methods=['GET'])
def select_story() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        stories = session.query(ShortStory)\
                         .filter(ShortStory.title.ilike('%' + search + '%'))\
                         .order_by(ShortStory.title)\
                         .all()
        retval['results'] = []
        if stories:
            for story in stories:
                retval['results'].append(
                    {'id': str(story.id), 'text': story.author_str + ': ' + story.title})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps[''])


@app.route('/type_for_story/<storyid>')
def type_for_story(storyid: Any) -> Any:
    session = new_session()

    type = session.query(StoryType)\
                  .join(ShortStory, ShortStory.story_type == StoryType.id)\
                  .filter(ShortStory.id == storyid)\
                  .first()

    obj: List[Dict[str, str]] = [{'id': type.id, 'text': type.name}]

    return Response(json.dumps(obj))


@app.route('/save_type_to_story', methods=['POST'])
def save_type_to_story() -> Any:
    (storyid, type_id) = get_select_ids(request.form)

    session = new_session()

    story = session.query(ShortStory).filter(ShortStory.id == storyid).first()
    story.story_type = type_id[0]['id']
    session.add(story)
    session.commit()
    log_change(session, story, 'Tyyppi')

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/select_storytype')
def select_storytype() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        types = session.query(StoryType)\
            .filter(StoryType.name.ilike('%' + search + '%'))\
            .all()
        retval['results'] = []
        if types:
            for type in types:
                retval['results'].append(
                    {'id': str(type.id),  'text': type.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps[''])
