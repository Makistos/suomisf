from app import app
from app.orm_decl import (ShortStory, Part, Author, Person, StoryGenre, StoryTag)
from .route_helpers import *
from flask import (render_template, request, flash, redirect, url_for, make_response, jsonify, Response)
from flask_login import login_required, current_user
import json

@app.route('/save_story_title', methods=['GET', 'POST'])
@login_required
@admin_required
def save_story_title():
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
def save_story_orig_title():
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
def save_story_pubyear():
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

@app.route('/save_authors_to_story', methods=["POST"])
@login_required
@admin_required
def save_authors_to_story() -> Response:
    session = new_session()

    (storyid, people_ids) = get_select_ids(request.form)
    session = new_session()
    existing_people = session.query(Author)\
                             .join(Part)\
                             .filter(Part.id == Author.part_id)\
                             .filter(Part.shortstory_id == storyid)\
                             .all()

    (to_add, to_remove) = get_join_changes([x.person_id for x in existing_people], [int(x['id']) for x in people_ids])

    for id in to_remove:
        auth = session.query(Author)\
                      .filter(Author.person_id == id)\
                      .join(Part)\
                      .filter(Part.id == Author.part_id)\
                      .filter(Part.shortstory_id == storyid)\
                      .first()
        session.delete(auth)
    for id in to_add:
        parts = session.query(Part)\
                       .filter(Part.shortstory_id == storyid)\
                       .all()
        for part in parts:
            auth = Author(person_id=id, part_id=part.id)
            session.add(auth)
    
    session.commit()
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)

@app.route('/authors_for_story/<storyid>', methods=["GET"])
@login_required
@admin_required
def authors_for_story(storyid):
    session = new_session()
    people = session.query(Person)\
                    .join(Author)\
                    .filter(Author.person_id == Person.id)\
                    .join(Part)\
                    .filter(Part.shortstory_id == storyid)\
                    .filter(Author.part_id == Part.id)\
                    .all()

    retval: List[Dict[str, str]] = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)
    
    return Response(json.dumps(retval))

@app.route('/genres_for_story/<storyid>', methods=["GET"])
@login_required
@admin_required
def genres_for_story(storyid):
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

@app.route('/tags_for_story/<storyid>', methods=["GET"])
@login_required
@admin_required
def tags_for_story(storyid):
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
