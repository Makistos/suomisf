import logging

from flask import (redirect, render_template, request,
                   url_for, jsonify, Response, make_response)
from flask_login import current_user, login_user, logout_user
from flask_login.utils import login_required

from app import app
from app.forms import PersonForm
from app.orm_decl import (Person, PersonTag, Author, Translator, Editor,
                          Part, Work, Edition, Genre, Awarded, ArticlePerson,
                          ArticleAuthor, Bookseries, ShortStory, Award,
                          AwardCategory, Country, Language, PersonLanguage,
                          Tag, PersonTag, Alias)
from sqlalchemy import func
from typing import Dict, Any, List
from .route_helpers import *
import urllib
import json


@app.route('/people')
def people() -> Any:
    session = new_session()
    people = session.query(Person).order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Henkilöluettelo',
                           letters=letters)


@app.route('/authors')
def authors() -> Any:
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
def translators() -> Any:
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
def editors() -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(Editor)\
                    .filter(Editor.person_id == Person.id)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))

    return render_template('people.html', people=people,
                           header='Toimittajat',
                           letters=letters)


@app.route('/person/<personid>', methods=['POST', 'GET'])
def person(personid: Any) -> Any:
    session = new_session()
    if personid.isdigit():
        person = session.query(Person).filter(Person.id == personid).first()
    else:
        personid = urllib.parse.unquote(personid)
        person = session.query(Person).filter(Person.name == personid).first()
        if not person:
            person = session.query(Person).filter(
                Person.alt_name == personid).first()

    series = session.query(Bookseries)\
                    .join(Work)\
                    .join(Part.authors)\
                    .filter(Bookseries.id == Work.bookseries_id)\
                    .filter(Part.work_id == Work.id)\
                    .filter(Person.id == personid)\
                    .group_by(Bookseries.id)\
                    .all()
    form = PersonForm(request.form)

    genres = session.query(Genre.name, Genre.abbr, func.count(Genre.id).label('count'))\
                    .join(Work.genres)\
                    .join(Work.parts)\
                    .filter(Part.shortstory_id == None)\
                    .join(Author.person)\
                    .filter(Author.part_id == Part.id)\
                    .filter(Person.id == person.id)\
                    .group_by(Genre.name)\
                    .all()

    genre_list: Dict[str, List[str]] = {}
    for genre in genres:
        genre_list[genre.abbr] = [genre.count, genre.name]

    if request.method == 'GET':
        form.name.data = person.name
        form.alt_name.data = person.alt_name
        form.fullname.data = person.fullname
        form.image_attr.data = person.image_attr
        form.dob.data = person.dob
        form.dod.data = person.dod
        form.bio.data = person.bio
        form.bio_src.data = person.bio_src
    elif form.validate_on_submit():
        person.name = form.name.data
        person.alt_name = form.alt_name.data
        person.fullname = form.fullname.data
        person.image_attr = form.image_attr.data
        person.dob = form.dob.data
        person.dod = form.dod.data
        person.bio = form.bio.data.strip()
        person.bio_src = form.bio_src.data
        session.add(person)
        session.commit()
        log_change(session, 'Person', person.id)
        # Reload data so changes are updated to view
        person = session.query(Person).filter(Person.id == person.id).first()
    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')
    return render_template('person.html', person=person,
                           genres=genre_list,
                           series=series,
                           form=form)


@app.route('/new_person', methods=['POST', 'GET'])
def new_person() -> Any:
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
        session.add(person)
        session.commit()
        log_change(session, 'Person', person.id, action='NEW')
        return redirect(url_for('person', personid=person.id))
    # else:
    #     app.logger.debug("Errors: {}".format(form.errors))
    return render_template('new_person.html', form=form, personid=person.id)


@app.route('/people_by_nationality/<nationality>')
def people_by_nationality(nationality: str) -> Any:
    session = new_session()
    country = session.query(Country).filter(
        Country.name == nationality).first()
    people = session.query(Person)\
                    .filter(Person.nationality_id == country)\
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
        if people:
            for person in people:
                retval['results'].append(
                    {'id': str(person.id), 'text': person.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))


@app.route('/languages_for_person/<personid>')
def languages_for_person(personid: Any) -> Response:
    session = new_session()
    languages = session.query(Language)\
        .join(PersonLanguage)\
        .filter(PersonLanguage.language_id == Language.id)\
        .join(Person)\
        .filter(PersonLanguage.person_id == Person.id)\
        .filter(Person.id == personid)\
        .all()

    retval: List[Dict[str, str]] = []
    if languages:
        for language in languages:
            obj: Dict[str, str] = {'id': language.id, 'text': language.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_languages_to_person', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_languages_to_person() -> Any:
    session = new_session()

    (personid, language_ids) = get_select_ids(request.form)
    language_ids = create_new_languages(session, language_ids)

    existing_languages = session.query(PersonLanguage)\
        .filter(PersonLanguage.person_id == personid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        [x.person_id for x in existing_languages],
        [int(x['id']) for x in language_ids])

    for id in to_remove:
        pl = session.query(PersonLanguage)\
            .filter(PersonLanguage.language_id == id)\
            .filter(PersonLanguage.person_id == personid)\
            .first()
        session.delete(pl)
    for id in to_add:
        pl = PersonLanguage(person_id=personid, language_id=id)
        session.add(pl)

    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/remove_image_from_person/<personid>')
@login_required  # type: ignore
@admin_required
def remove_image_from_person(personid: Any) -> Any:
    return redirect(url_for('person', personid=personid))


@app.route('/tags_for_person/<personid>')
def tags_for_person(personid: Any) -> Response:
    session = new_session()
    tags = session.query(Tag)\
        .join(PersonTag)\
        .filter(PersonTag.tag_id == Tag.id)\
        .join(Person)\
        .filter(PersonTag.person_id == Person.id)\
        .filter(Person.id == personid)\
        .all()

    retval: List[Dict[str, str]] = []
    if tags:
        for tag in tags:
            obj: Dict[str, str] = {'id': tag.id, 'text': tag.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_tags_to_person', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_tags_to_person() -> Any:

    (personid, tag_ids) = get_select_ids(request.form)

    session = new_session()
    tag_ids = create_new_tags(session, tag_ids)

    existing_tags = session.query(PersonTag)\
                           .filter(PersonTag.person_id == personid)\
                           .all()

    (to_add, to_remove) = get_join_changes(
        [x.tag_id for x in existing_tags], [int(x['id']) for x in tag_ids])

    for id in to_remove:
        wt = session.query(PersonTag)\
                    .filter(PersonTag.person_id == personid, PersonTag.tag_id == id)\
                    .first()
        session.delete(wt)
    for id in to_add:
        wt = PersonTag(person_id=personid, tag_id=id)
        session.add(wt)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/aliases_for_person/<personid>')
def aliases_for_person(personid: Any) -> Response:
    session = new_session()
    aliases = session.query(Alias).filter(Alias.realname == personid).all()
    ids = [x.alias for x in aliases]

    personas = session.query(Person)\
        .filter(Person.id.in_(ids))\
        .all()

    retval: List[Dict[str, str]] = []
    if personas:
        for persona in personas:
            obj: Dict[str, str] = {'id': persona.id, 'text': persona.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_aliases_to_person', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_aliases_to_person() -> Any:
    (personid, alias_ids) = get_select_ids(request.form)

    session = new_session()
    alias_ids = create_new_people(session, alias_ids)

    existing_aliases = session.query(Alias.alias)\
                              .filter(Alias.realname == personid)\
                              .all()

    (to_add, to_remove) = get_join_changes(
        existing_aliases, [int(x['id']) for x in alias_ids])

    for id in to_remove:
        alias = session.query(Alias)\
            .filter(Alias.realname == personid, Alias.alias == id)\
            .first()
        session.delete(alias)
    for id in to_add:
        alias = Alias(realname=personid, alias=id)
        session.add(alias)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/real_names_for_person/<personid>')
def real_names_for_person(personid: Any) -> Response:
    session = new_session()
    aliases = session.query(Alias).filter(Alias.alias == personid).all()
    ids = [x.realname for x in aliases]

    tags = session.query(Person)\
        .filter(Person.id.in_(ids))\
        .first()

    retval: List[Dict[str, str]] = []
    if tags:
        for tag in tags:
            obj: Dict[str, str] = {'id': tag.id, 'text': tag.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_real_names_to_person', methods=['POST'])
def save_real_names_to_person() -> Response:
    session = new_session()

    (personid, realname_ids) = get_select_ids(request.form)

    existing_realnames = session.query(Alias.realname)\
                                .filter(Alias.alias == personid)\
                                .all()

    (to_add, to_remove) = get_join_changes(
        existing_realnames, [int(x['id']) for x in realname_ids])

    for id in to_remove:
        realname = session.query(Alias)\
            .filter(Alias.alias == personid, Alias.realname == id)\
            .first()
        session.delete(realname)
    for id in to_add:
        realname = Alias(realname=id, alias=personid)
        session.add(realname)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@app.route('/nationality_for_person/<personid>')
def nationality_for_person(personid: Any) -> Response:
    session = new_session()

    country = session.query(Country)\
        .join(Person)\
        .filter(Country.id == Person.nationality_id)\
        .filter(Person.id == personid)\
        .first()
    retval: List[Dict[str, str]] = []
    if country:
        obj: Dict[str, str] = {'id': country.id, 'text': country.name}
        retval.append(obj)
    return Response(json.dumps(retval))


@app.route('/save_nationality_to_person', methods=['POST'])
@login_required  # type: ignore
@admin_required
def save_nationality_to_person() -> Response:
    session = new_session()
    (personid, country_ids) = get_select_ids(request.form)

    person = session.query(Person).filter(Person.id == personid).first()

    person.nationality_id = country_ids[0]['id']
    session.add(person)
    session.commit()

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)
