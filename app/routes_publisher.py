import logging

from flask import redirect, render_template, request, url_for

from app import app
from app.forms import PublisherForm
from app.orm_decl import (Publisher, PublisherLink)
from sqlalchemy import func

from .route_helpers import *


@app.route('/publishers')
def publishers():
    session = new_session()
    publishers = session.query(Publisher)\
                        .order_by(Publisher.name)\
                        .all()
    return render_template('publishers.html', publishers=publishers)


@app.route('/publisher/<pubid>')
def publisher(pubid):
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
    series = session.query(Pubseries).filter(
        Pubseries.publisher_id == pubid).all()

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

    genre_list = {'SF': '', 'F': '', 'K': '', 'nSF': '', 'nF': '', 'nK': '',
                  'PF': '', 'paleof': '', 'kok': '', 'eiSF': '', 'rajatap': ''}
    for g in genres:
        app.logger.info(g.name)
        genre_list[g.abbr] = g.count

    editions = session.query(Edition)\
                      .order_by(Edition.pubyear)\
                      .filter(Edition.publisher_id == pubid).all()
    return render_template('publisher.html', publisher=publisher,
                           series=series, book_count=book_count, oldest=oldest,
                           newest=newest, editions=editions, genres=genre_list)


@app.route('/new_publisher', methods=['GET', 'POST'])
def new_publisher():
    form = PublisherForm()
    session = new_session()
    if form.validate_on_submit():
        publisher = Publisher(name=form.name.data, fullname=form.fullname.data)
        session.add(publisher)
        session.commit()
        return redirect(url_for('publisher', pubid=publisher.id))
    return render_template('new_publisher.html', form=form)