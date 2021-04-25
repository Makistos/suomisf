
import logging
import json

from flask import redirect, render_template, request, url_for, make_response
from flask_login import current_user
from app import app
from app.forms import BookseriesForm, PubseriesForm
from app.orm_decl import (Bookseries, BookseriesLink, Pubseries, PubseriesLink,
                          Person, Part, Work, Edition, UserBookseries, UserPubseries, Author)
from sqlalchemy import func

from .route_helpers import *
from typing import Any


@app.route('/allbookseries')
def allbookseries():
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    Session = sessionmaker(bind=engine)
    session = Session()
    series = session.query(Bookseries).order_by(Bookseries.name).all()
    return render_template('allbookseries.html', series=series)


@app.route('/bookseries/<seriesid>')
def bookseries(seriesid):
    session = new_session()
    series = session.query(Bookseries)\
                    .filter(Bookseries.id == seriesid)\
                    .first()
    authors = session.query(Person)\
                     .join(Work.authors)\
                     .join(Author.parts)\
                     .join(Part.edition)\
                     .filter(Work.bookseries_id == seriesid)\
                     .order_by(Person.name, Work.bookseriesnum)\
                     .all()
    editions = session.query(Edition)\
                      .join(Part.work)\
                      .join(Part.edition)\
                      .filter(Work.bookseries_id == seriesid)\
                      .order_by(Work.bookseriesorder, Work.creator_str)\
                      .all()
    return render_template('bookseries.html', series=series, editions=editions)


@app.route('/new_bookseries', methods=['POST', 'GET'])
def new_bookseries() -> Any:
    session = new_session()
    form = BookseriesForm(request.form)

    if form.validate_on_submit():
        bookseries = Bookseries(name=form.name.data,
                                orig_name=form.orig_name.data,
                                important=form.important.data)
        session.add(bookseries)
        session.commit()
        return redirect(url_for('bookseries', seriesid=bookseries.id))
    return render_template('new_bookseries.html', form=form)


# Publisher series related routes

@app.route('/allpubseries')
def allpubseries():
    session = new_session()
    series = session.query(Pubseries).order_by(Pubseries.name).all()
    app.logger.debug(session.query(Pubseries).order_by(Pubseries.name))
    return render_template('allpubseries.html', series=series)


@app.route('/pubseries/<seriesid>')
def pubseries(seriesid):
    session = new_session()
    app.logger.debug(session.query(Pubseries).filter(Pubseries.id == seriesid))
    series = session.query(Pubseries)\
                    .filter(Pubseries.id == seriesid)\
                    .first()
    books = session.query(Edition)\
                   .join(Part.work)\
                   .join(Part.edition)\
                   .filter(Edition.pubseries_id == seriesid)\
                   .order_by(Edition.pubseriesnum, Edition.pubyear)\
                   .all()
    favorite = session.query(UserPubseries)\
        .filter(UserPubseries.series_id == seriesid,
                UserPubseries.user_id == current_user.get_id())\
        .count()
    return render_template('pubseries.html', series=series, books=books,
                           favorite=favorite)


@app.route('/new_pubseries', methods=['GET', 'POST'])
def new_pubseries():
    form = PubseriesForm()
    session = new_session()
    search_lists = {'publisher': [str(x.name) for x in
                                  session.query(Publisher)
                                  .order_by(Publisher.name)
                                  .all()]}
    if form.validate_on_submit():
        publisher = session.query(Publisher)\
                           .filter(Publisher.name == form.publisher.data)\
                           .first()
        pubseries = Pubseries(name=form.name.data, publisher_id=publisher.id,
                              important=form.important.data)
        session.add(pubseries)
        session.commit()
        return redirect(url_for('index'))
    return render_template('new_pubseries.html', form=form,
                           search_lists=search_lists)


@app.route('/list_pubseries/<pubname>', methods=['GET', 'POST'])
def list_pubseries(pubname):
    session = new_session()
    series = session.query(Pubseries)\
                    .join(Publisher)\
                    .filter(Publisher.name == pubname)\
                    .all()
    data = []
    for s in series:
        data.append((str(s.id), s.name))
    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response
