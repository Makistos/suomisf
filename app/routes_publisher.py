import logging

from flask import redirect, render_template, request, url_for, Response

from app import app
from app.forms import PublisherForm
from app.orm_decl import (Publisher, PublisherLink, Edition, Pubseries, Genre,
                          Part, Work)
from sqlalchemy import func, desc
from typing import Any, Dict, List
import json

from .route_helpers import *


@app.route('/publishers')
def publishers() -> Any:
    session = new_session()
    publishers = session.query(Publisher)\
                        .filter(Publisher.editions != None)\
                        .order_by(Publisher.name)\
                        .all()
    return render_template('publishers.html', publishers=publishers)


@app.route('/publisher/<pubid>', methods=['POST', 'GET'])
def publisher(pubid: Any) -> Any:
    session = new_session()
    publisher = session.query(Publisher).filter(Publisher.id == pubid).first()
    book_count = session.query(Edition)\
                        .filter(Edition.publisher_id == pubid)\
                        .count()
    oldest = session.query(Edition)\
                    .filter(Edition.publisher_id == pubid)\
                    .order_by(Edition.pubyear)\
                    .first()
    newest = session.query(Edition)\
                    .filter(Edition.publisher_id == pubid)\
                    .order_by(desc(Edition.pubyear))\
                    .first()

    genres = session.query(Genre.name, Genre.abbr, func.count(Genre.name).label('count'))\
                    .join(Work.genres)\
                    .join(Part)\
                    .join(Edition)\
                    .filter(Part.work_id == Work.id)\
                    .filter(Part.shortstory_id == None)\
                    .filter(Edition.id == Part.edition_id)\
                    .filter(Edition.publisher_id == pubid)\
                    .group_by(Genre.name)\
                    .order_by(func.count(Genre.name).desc())\
                    .all()

    # genre_list = {'SF': [], 'F': '', 'K': '', 'nSF': '', 'nF': '', 'nK': '',
    #               'PF': '', 'paleof': '', 'kok': '', 'eiSF': '', 'rajatap': ''}
    genre_list: Dict[str, List[str]] = {}
    for g in genres:
        app.logger.info(g.name)
        genre_list[g.abbr] = [str(g.count), g.name]

    editions = session.query(Edition)\
                      .order_by(Edition.pubyear)\
                      .filter(Edition.publisher_id == pubid).all()

    form = PublisherForm(request.form)

    if request.method == 'GET':
        form.name.data = publisher.name
        form.fullname.data = publisher.fullname
        form.description.data = publisher.description
    elif form.validate_on_submit():
        changes: List[str] = []
        if publisher.name != form.name.data:
            publisher.name = form.name.data
            changes.append('Nimi')
        if publisher.fullname != form.fullname.data:
            publisher.fullname = form.fullname.data
            changes.append('Pitkä nimi')
        descr = form.description.data.strip()
        if publisher.description != descr:
            publisher.description = descr
            changes.append('Kuvaus')
        session.add(publisher)
        session.commit()

        # Save links
        links = list(publisher.links)
        if dynamic_changed(links, form.links.data):
            changes.append('Linkit')

        session.query(PublisherLink)\
               .filter(PublisherLink.publisher_id == publisher.id).delete()

        for link in form.links.data:
            if link['link']:
                if len(link['link']) > 0:
                    pl = PublisherLink(publisher_id=publisher.id,
                                       link=link['link'],
                                       description=link['description'])
                    session.add(pl)
        session.commit()

        log_change(session, publisher, fields=changes)

    else:
        app.logger.error('Errors: {}'.format(form.errors))
        print(f'Errors: {form.errors}')

    return render_template('publisher.html', publisher=publisher,
                           book_count=book_count, oldest=oldest,
                           newest=newest, editions=editions, genres=genre_list,
                           form=form)


@app.route('/new_publisher', methods=['GET', 'POST'])
def new_publisher() -> Any:
    form = PublisherForm()
    session = new_session()
    if form.validate_on_submit():
        publisher = Publisher(name=form.name.data, fullname=form.fullname.data)
        session.add(publisher)
        session.commit()
        return redirect(url_for('publisher', pubid=publisher.id))
    return render_template('new_publisher.html', form=form)


@app.route('/select_publisher', methods=['GET'])
def select_publisher() -> Response:
    search = request.args['q']
    session = new_session()

    if search:
        retval: Dict[str, List[Dict[str, Any]]] = {}
        publishers = session.query(Publisher)\
                            .filter(Publisher.name.ilike('%' + search + '%'))\
                            .order_by(Publisher.name)\
                            .all()

        retval['results'] = []
        if publishers:
            for pub in publishers:
                retval['results'].append({'id': pub.id, 'text': pub.name})
        return Response(json.dumps(retval))
    else:
        return Response(json.dumps(['']))
