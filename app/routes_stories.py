from app import app
from app.orm_decl import (ShortStory, Part, Author, Person)
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


@app.route('/people_for_story/<storyid>')
def people_for_story(storyid):
    session = new_session()
    people = session.query(Person)\
                    .join(Author)\
                    .filter(Person.id == Author.person_id)\
                    .join(Part)\
                    .filter(Author.part_id == Part.id)\
                    .filter(Part.shortstory_id == storyid)\
                    .all()

    retval: List[Dict[str, str]]  = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(retval)
