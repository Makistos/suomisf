import logging

from flask import redirect, render_template, request, url_for, jsonify, Response
from flask_login import current_user, login_user, logout_user

from app import app
from app.forms import PersonForm
from app.orm_decl import (Person, PersonTag, Author, Translator, Editor, 
                          Part, Work, Edition, Genre, Awarded, ArticlePerson, 
                          ArticleAuthor)
from sqlalchemy import func

from .route_helpers import *
import urllib
import json


@app.route('/people')
def people():
    session = new_session()
    people = session.query(Person).order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Henkilöluettelo',
                           letters=letters)


@app.route('/authors')
def authors():
    session = new_session()
    people = session.query(Person)\
                    .join(Author)\
                    .filter(Author.person_id == Person.id)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Kirjailijat',
                           letters=letters)


@app.route('/translators')
def translators():
    session = new_session()
    people = session.query(Person)\
                    .join(Translator)\
                    .filter(Translator.person_id == Person.id)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Kääntäjät',
                           letters=letters)


@app.route('/editors')
def editors():
    session = new_session()
    people = session.query(Person)\
                    .join(Editor)\
                    .filter(Editor.person_id == Person.id)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))

    return render_template('people.html', people=people,
                           header='Toimittajat',
                           letters=letters)


@app.route('/person/<personid>')
def person(personid):
    app.logger.info(personid)
    session = new_session()
    if personid.isdigit():
        person = session.query(Person).filter(Person.id == personid).first()
    else:
        personid = urllib.parse.unquote(personid)
        person = session.query(Person).filter(Person.name == personid).first()
        if not person:
            person = session.query(Person).filter(
                Person.alt_name == personid).first()

    authored = books_for_person(session, personid, 'A')
    series = session.query(Bookseries)\
                    .join(Work)\
                    .join(Part.authors)\
                    .filter(Bookseries.id == Work.bookseries_id)\
                    .filter(Part.work_id == Work.id)\
                    .filter(Person.id == person.id)\
                    .group_by(Bookseries.id)\
                    .all()

    translated = books_for_person(session, personid, 'T')
    edited = books_for_person(session, personid, 'E')
    # stories = session.query(ShortStory.title.label('orig_title'),
    #                         Part.title.label('title'),
    #                         ShortStory.pubyear,
    #                         ShortStory.id)\
    stories = session.query(ShortStory)\
        .join(Part.authors)\
        .join(Part.shortstory)\
        .filter(Person.id == person.id)\
        .group_by(ShortStory.id)\
        .order_by(Part.title)\
        .all()

    genres = session.query(Genre.name, Genre.abbr, func.count(Genre.id).label('count'))\
                    .join(Work.genres)\
                    .join(Work.parts)\
                    .filter(Part.shortstory_id == None)\
                    .join(Author.person)\
                    .filter(Author.part_id == Part.id)\
                    .filter(Person.id == person.id)\
                    .group_by(Genre.name)\
                    .all()

    person_awards = session.query(Awarded).filter(
        Awarded.person_id == person.id).all()
    novel_awards = session.query(Awarded)\
                          .join(Work)\
                          .filter(Work.id == Awarded.work_id)\
                          .join(Part)\
                          .filter(Part.work_id == Work.id)\
                          .join(Author)\
                          .filter(Author.part_id == Part.id)\
                          .filter(Author.person_id == person.id)\
                          .order_by(Awarded.year)\
                          .all()

    translated_stories = session.query(ShortStory)\
                                .join(Part)\
                                .filter(Part.shortstory_id == ShortStory.id)\
                                .join(Translator)\
                                .filter(Translator.part_id == Part.id)\
                                .filter(Translator.person_id == personid)
    genre_list = {'SF': '', 'F': '', 'K': '', 'nSF': '', 'nF': '', 'nK': '',
                  'PF': '', 'paleof': '', 'kok': '', 'eiSF': '', 'rajatap': ''}
    for g in genres:
        app.logger.info(g.name)
        genre_list[g.abbr] = g.count

    # aliases = session.query(Person)\
    #                 .join(Alias)\
    #                 .filter(Alias.realname == person.id)\
    #                 .all()
    # real_names = session.query(Person)\
    #                    .join(Alias)\
    #                    .filter(Alias.alias == person.id)\
    #                    .all()
    return render_template('person.html', person=person, authored=authored,
                           translated=translated, edited=edited, stories=stories, genres=genre_list,
                           series=series, translated_stories=translated_stories, person_awards=person_awards,
                           novel_awards=novel_awards)


@app.route('/edit_person/<personid>', methods=['POST', 'GET'])
def edit_person(personid):
    session = new_session()
    if personid != 0:
        person = session.query(Person).filter(Person.id == personid).first()
    else:
        person = Person()
    form = PersonForm(request.form)
    if request.method == 'GET':
        form.name.data = person.name
        form.alt_name.data = person.alt_name
        form.first_name.data = person.first_name
        form.last_name.data = person.last_name
        form.image_src.data = person.image_src
        form.image_attr.data = person.image_attr
        if person.dob:
            form.dob.data = person.dob
        else:
            form.dob.data = 0
        if person.dod:
            form.dod.data = person.dod
        else:
            form.dod.data = 0
        form.nationality.data = person.nationality
        form.other_names.data = person.other_names
        form.tags.data = ','.join([x.name for x in person.tags])
        form.bio.data = person.bio
        form.bio_src.data = person.bio_src
    if form.validate_on_submit():
        person.name = form.name.data
        person.alt_name = form.alt_name.data
        person.first_name = form.first_name.data
        person.last_name = form.last_name.data
        person.image_src = form.image_src.data
        if form.dob.data != 0:
            person.dob = form.dob.data
        if form.dod.data != 0:
            person.dod = form.dod.data
        person.nationality = form.nationality.data
        person.other_names = form.other_names.data
        person.bio = form.bio.data
        person.bio_src = form.bio_src.data
        session.add(person)
        session.commit()

        save_tags(session, form.tags.data, 'Person', person.id)

        return redirect(url_for('person', personid=person.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_person.html', form=form, personid=personid)


@app.route('/new_person', methods=['POST', 'GET'])
def new_person():
    session = new_session()
    person = Person()

    form = PersonForm(request.form)

    if form.validate_on_submit():
        person.name = form.name.data
        person.alt_name = form.alt_name.data
        person.first_name = form.first_name.data
        person.last_name = form.last_name.data
        if form.dob.data != 0:
            person.dob = form.dob.data
        if form.dod.data != 0:
            person.dod = form.dod.data
        person.nationality = form.nationality.data
        person.other_names = form.other_names.data
        person.image_src = form.image_src.data
        person.image_attr = form.image_attr.data
        person.bio = form.bio.data
        person.bio_src = form.bio_src.data
        session.add(person)
        session.commit()
        return redirect(url_for('person', personid=person.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_person.html', form=form, personid=person.id)

@app.route('/people_by_nationality/<nationality>')
def people_by_nationality(nationality: str):
    session = new_session()
    people = session.query(Person)\
                    .filter(Person.nationality == nationality)\
                    .all()

    return render_template('people.html', people=people,
                           header=nationality)

@app.route('/autocomp_person', methods=['POST', 'GET'])
def autocomp_person() -> Response:
    search = request.form['q']
    session = new_session()

    print('search')
    if search:
        people = session.query(Person)\
                        .filter(Person.name.ilike('%' + search + '%'))\
                        .order_by(Person.name)\
                        .all()
        l = [x.name for x in people]
        return Response(json.dumps(l))
    else:
        return Response(json.dumps(['']))


@app.route('/select_person', methods=['GET'])
def select_person() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        people = session.query(Person)\
                        .filter(Person.name.ilike('%' + search + '%'))\
                        .order_by(Person.name)\
                        .all()
        
        retval['results'] = []
        #retval: List[Dict[str, str]] = []
        if people:
            for person in people:
                obj: Dict[str, str] = {}
                obj['id'] = str(person.id)
                obj['text'] = person.name
                #retval.append(obj)
                retval['results'].append({'id': str(person.id), 'text': person.name})
        app.logger.debug('retval: ' + str(retval))
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))

@app.route('/authors_for_article/<articleid>')
def authors_for_article(articleid):
    session = new_session()
    people = session.query(Person)\
                    .join(ArticleAuthor)\
                    .filter(Person.id == ArticleAuthor.person_id)\
                    .filter(ArticleAuthor.article_id == articleid)\
                    .all()

    retval: List[Dict[str, str]]  = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(json.dumps(retval))

@app.route('/people_for_article/<articleid>')
def people_for_article(articleid):
    session = new_session()
    people = session.query(Person)\
                    .join(ArticlePerson)\
                    .filter(Person.id == ArticlePerson.person_id)\
                    .filter(ArticlePerson.article_id == articleid)\
                    .all()

    retval: List[Dict[str, str]]  = []
    if people:
        for person in people:
            obj: Dict[str, str] = {}
            obj['id'] = str(person.id)
            obj['text'] = person.name
            retval.append(obj)

    return Response(json.dumps(retval))