import logging

from flask import (redirect, render_template, request,
                   url_for, jsonify, Response, make_response)
from flask.globals import session
from flask_login.utils import login_required
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import app
from app.forms import PersonForm
from app.orm_decl import (ArticleAuthor, Person, PersonTag,
                          Part, Work, Genre,
                          Bookseries,
                          Country, Language, PersonLanguage,
                          Tag, PersonTag, Alias, Contributor, PersonLink, Awarded,
                          Award, AwardCategories, AwardCategory)
from sqlalchemy import func
from typing import Dict, Any, List, Optional
from .route_helpers import *
import urllib
import json
import os


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
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 1)\
                    .join(Part)\
                    .filter(Part.id == Contributor.part_id)\
                    .filter(Part.shortstory_id == None)\
                    .distinct(Person.id)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Kirjailijat',
                           letters=letters)


@app.route('/story_authors')
def story_authors() -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 1)\
                    .join(Part)\
                    .filter(Part.id == Contributor.part_id)\
                    .filter(Part.shortstory_id != None)\
                    .distinct(Person.id)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Novellistit',
                           letters=letters)


@app.route('/article_authors')
def article_authors() -> Any:
    session = new_session()

    people = session.query(Person)\
                    .join(ArticleAuthor)\
                    .filter(ArticleAuthor.person_id == Person.id)\
                    .distinct(Person.id)\
                    .order_by(Person.name)\
                    .all()

    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Artikkeleja kirjoittaneet',
                           letters=letters)


@app.route('/translators')
def translators() -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 2)\
                    .order_by(Person.name).all()
    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header='Kääntäjät',
                           letters=letters)


@app.route('/editors')
def editors() -> Any:
    session = new_session()
    people = session.query(Person)\
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 3)\
                    .join(Part, Part.id == Contributor.part_id)\
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
        if person:
            personid = person.id
        else:
            return redirect('/')
    else:
        personid = urllib.parse.unquote(personid)
        person = session.query(Person).filter(Person.name == personid).first()
        if not person:
            person = session.query(Person).filter(
                Person.alt_name == personid).first()
        personid = person.id

    series = session.query(Bookseries)\
                    .join(Work)\
                    .join(Part)\
                    .join(Contributor)\
                    .filter(Contributor.role_id == 1)\
                    .filter(Bookseries.id == Work.bookseries_id)\
                    .filter(Part.work_id == Work.id)\
                    .filter(Contributor.person_id == personid)\
                    .filter(Contributor.part_id == Part.id)\
                    .group_by(Bookseries.id)\
                    .all()
    form = PersonForm(request.form)

    genres = session.query(Genre.name, Genre.abbr, func.count(Genre.id).label('count'))\
                    .join(Work.genres)\
                    .join(Work.parts)\
                    .filter(Part.shortstory_id == None)\
                    .join(Contributor.person)\
                    .filter(Contributor.role_id == 0)\
                    .filter(Contributor.part_id == Part.id)\
                    .filter(Person.id == personid)\
                    .group_by(Genre.name)\
                    .all()

    novel_awards = session.query(Awarded)\
                          .join(Work)\
                          .filter(Work.id == Awarded.work_id)\
                          .join(Part, Part.work_id == Work.id)\
                          .join(Contributor, Contributor.part_id == Part.id)\
                          .filter(Contributor.person_id == personid)\
                          .filter(Contributor.role_id == 1)\
                          .all()

    award_list = session.query(Award)\
        .join(AwardCategories)\
        .filter(AwardCategories.award_id == Award.id)\
        .join(AwardCategory)\
        .filter(AwardCategory.id == AwardCategories.category_id)\
        .filter(AwardCategory.type == 0)\
        .all()

    award_categories = session.query(AwardCategory)\
                              .filter(AwardCategory.type == 0)\
                              .all()

    stories: List[Any] = []
    magazine_stories: List[Any] = []
    if person.stories:
        stories = list(person.stories)
    if person.magazine_stories:
        magazine_stories = list(person.magazine_stories)
    # First make both data sets into lists so they can be joined together.
    # Then make the result into a set which removes duplicates and finally
    # back to a list so that results can be sorted.
    stories = list(set(list(stories) +
                       list(magazine_stories)))

    stories.sort(key=lambda x: x.title)
    genre_list: Dict[str, List[str]] = {}
    for genre in genres:
        genre_list[genre.abbr] = [genre.count, genre.name]

    # links =
    if request.method == 'GET':
        form.name.data = person.name
        form.alt_name.data = person.alt_name
        form.fullname.data = person.fullname
        form.other_names.data = person.other_names
        form.image_attr.data = person.image_attr
        form.dob.data = person.dob
        form.dod.data = person.dod
        form.bio.data = person.bio
        form.bio_src.data = person.bio_src
    elif form.validate_on_submit():
        changes: List[str] = []
        if person.name != form.name.data:
            person.name = form.name.data
            changes.append('Nimi')
        person.alt_name = form.alt_name.data
        person.fullname = form.fullname.data
        other_names = form.other_names.data
        if (person.other_names != form.other_names.data and
                (person.other_names is not None or form.other_names.data != '')):
            person.other_names = form.other_names.data.strip()
            changes.append('Muut nimen kirjoitusasut')
        person.image_attr = form.image_attr.data
        if person.dob != form.dob.data:
            person.dob = form.dob.data
            changes.append('Syntymävuosi')
        if person.dod != form.dod.data:
            person.dod = form.dod.data
            changes.append('Kuolinvuosi')
        bio = form.bio.data.strip()
        if (person.bio != bio and
                (person.bio is not None or form.bio.data != '')):
            person.bio = form.bio.data.strip()
            changes.append('Biografia')
        person.bio_src = form.bio_src.data
        session.add(person)
        session.commit()

        # Save awards
        existing_awards = awards_to_data(person.personal_awards)
        if form.awards.data[0]['name'] == '':
            # This is a bit ugly, but seems like editing the form list is not
            # possible. This fixes the issue that if there are no awards
            # then form.awards.data includes an empty item so dynamic_changed
            # returns true even if nothing has changed. This creates a new
            # log item every time such a page is saved.
            # Same fix is needed for every item using the same system, e.g.
            # links field below.
            existing_awards.insert(0, form.awards.data)
        if form.awards.data[0] != 0 and dynamic_changed(existing_awards, form.awards.data):
            changes.append('Palkinnot')

            session.query(Awarded)\
                   .filter(Awarded.person_id == person.id).delete()

            for award in form.awards.data:
                if award['award_id']:
                    aw = Awarded(person_id=person.id,
                                 year=award['year'],
                                 award_id=award['award_id'],
                                 category_id=award['category_id'])
                    session.add(aw)
            session.commit()

        # Save links
        links = [{'link': x.link, 'description': x.description}
                 for x in list(person.links)]
        if form.links.data[0]['link'] == '':
            links.insert(0, form.links.data[0])
        if dynamic_changed(links, form.links.data):
            changes.append('Linkit')

            session.query(PersonLink)\
                .filter(PersonLink.person_id == person.id).delete()

            for link in form.links.data:
                if link['link']:
                    if len(link['link']) > 0:
                        pl = PersonLink(person_id=person.id,
                                        link=link['link'],
                                        description=link['description'])
                        session.add(pl)
            session.commit()
        # Reload data so changes are updated to view
        person = session.query(Person).filter(Person.id == person.id).first()
        log_change(session, person, fields=changes)
        if 'Nimi' in changes:
            update_creators(session, person)
    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')
    return render_template('person.html', person=person,
                           genres=genre_list,
                           series=series,
                           stories=stories,
                           novel_awards=novel_awards,
                           form=form,
                           award_list=award_list,
                           award_categories=award_categories)


@ app.route('/new_person', methods=['POST', 'GET'])
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
        log_change(session, person, action='Uusi')
        return redirect(url_for('person', personid=person.id))
    # else:
    #     app.logger.debug("Errors: {}".format(form.errors))
    return render_template('new_person.html', form=form, personid=person.id)


@ app.route('/people_by_nationality/<nationality>')
def people_by_nationality(nationality: str) -> Any:
    session = new_session()
    country = session.query(Country).filter(
        Country.id == nationality).first()
    people = session.query(Person)\
        .filter(Person.nationality_id == country.id)\
        .all()

    letters = sorted(set([x.name[0].upper() for x in people if x.name != '']))
    return render_template('people.html', people=people,
                           header=country.name, letters=letters)


@ app.route('/autocomp_person', methods=['POST', 'GET'])
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


@ app.route('/select_person', methods=['GET'])
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


def allowed_image(filename: Optional[str]) -> bool:
    if not filename:
        return False
    if not "." in filename:
        return False

    ext = filename.split('.', -1)[-1]
    if ext.upper() in ['jpg', 'JPG', 'png', 'PNG']:
        return True
    else:
        return False


@ app.route('/save_image_to_person', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_image_to_person() -> Any:
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
                    app.config['PERSONIMG_SAVELOC'], filename))
                session = new_session()
                person = session.query(Person).filter(Person.id == id).first()
                person.image_src = app.config['PERSONIMG_DIR'] + filename
                session.add(person)
                session.commit()
                log_change(session, person, ['Kuva'])
                return redirect(request.url)
        else:
            return redirect(request.url)
    return redirect(request.url)


@ app.route('/remove_image_from_person', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def remove_image_from_person() -> Any:
    id = json.loads(request.form['itemId'])
    session = new_session()
    person = session.query(Person).filter(Person.id == id).first()
    person.image_src = ''
    session.add(person)
    session.commit()
    return Response(json.dumps(['Ok']))


@ app.route('/languages_for_person/<personid>')
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


@ app.route('/save_languages_to_person', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
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
        if pl:
            session.delete(pl)
    for id in to_add:
        pl = PersonLanguage(person_id=personid, language_id=id)
        session.add(pl)

    session.commit()
    person = session.query(Person).filter(Person.id == personid).first()
    log_change(session, person, fields=['Kielet'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/tags_for_person/<personid>')
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


@ app.route('/save_tags_to_person', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
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
    person = session.query(Person).filter(Person.id == personid).first()
    log_change(session, person, fields=['Asiasanat'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/aliases_for_person/<personid>')
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


@ app.route('/save_aliases_to_person', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
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
    person = session.query(Person).filter(Person.id == personid).first()
    log_change(session, person, fields=['Aliakset'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/real_names_for_person/<personid>')
def real_names_for_person(personid: Any) -> Response:
    session = new_session()
    aliases = session.query(Alias).filter(Alias.alias == personid).all()
    ids = [x.realname for x in aliases]

    tags = session.query(Person)\
        .filter(Person.id.in_(ids))\
        .all()

    retval: List[Dict[str, str]] = []
    if tags:
        for tag in tags:
            obj: Dict[str, str] = {'id': tag.id, 'text': tag.name}
            retval.append(obj)
    return Response(json.dumps(retval))


@ app.route('/save_real_names_to_person', methods=['POST'])
def save_real_names_to_person() -> Response:
    session = new_session()

    (personid, realname_ids) = get_select_ids(request.form)

    existing_realnames = session.query(Alias)\
        .filter(Alias.alias == personid)\
        .all()

    (to_add, to_remove) = get_join_changes(
        set([int(x.realname) for x in existing_realnames]), [int(x['id']) for x in realname_ids])

    for id in to_remove:
        realname = session.query(Alias)\
            .filter(Alias.alias == personid, Alias.realname == id)\
            .first()
        session.delete(realname)
    for id in to_add:
        realname = Alias(realname=id, alias=personid)
        session.add(realname)
    session.commit()
    person = session.query(Person).filter(Person.id == personid).first()
    log_change(session, person, fields=['Oikea nimi'])

    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)


@ app.route('/nationality_for_person/<personid>')
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


@ app.route('/save_nationality_to_person', methods=['POST'])
@ login_required  # type: ignore
@ admin_required
def save_nationality_to_person() -> Response:
    session = new_session()
    (personid, country_ids) = get_select_ids(request.form)

    person = session.query(Person).filter(Person.id == personid).first()

    person.nationality_id = country_ids[0]['id']
    session.add(person)
    session.commit()
    log_change(session, person, fields=['Kansallisuus'])
    msg = 'Tallennus onnistui'
    category = 'success'
    resp = {'feedback': msg, 'category': category}
    return make_response(jsonify(resp), 200)
