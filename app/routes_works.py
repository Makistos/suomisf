from app import app
from flask import render_template, request, flash, redirect, url_for, make_response
from app.orm_decl import (Person, Work, Bookseries, Edition, Part)
from app.forms import (WorkAuthorForm, WorkForm, WorkStoryForm, StoryForm, EditionForm)

from .route_helpers import *


def save_work(session, form, work):
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
        edition.pubyear = work.pubyear
        edition.language = work.language
        session.add(edition)
        session.commit()
        part = Part()
        part.work_id = work.id
        part.edition_id = edition.id
        part.title = work.title
        session.add(part)
        session.commit()
    save_genres(session, work, form.genre.data)

@app.route('/edit_work/<workid>', methods=["POST", "GET"])
def edit_work(workid):
    search_list = {}
    session = new_session()
    authors = []
    bookseries = []
    if workid != '0':
        work = session.query(Work)\
                      .filter(Work.id == workid)\
                      .first()
        authors = session.query(Person)\
                         .join(Author)\
                         .join(Part)\
                         .filter(Author.person_id == Person.id,
                                 Author.part_id == Part.id,
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
def work(workid):
    """ Popup has a form to add authors. """
    search_list: Dict = {}
    stories: List = []
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
    search_list = {**search_list, **author_list(session)}

    stories = session.query(ShortStory)\
        .join(Part)\
        .filter(Part.shortstory_id == ShortStory.id)\
        .filter(Part.work_id == workid)\
        .group_by(Part.shortstory_id)\
        .all()
    form = WorkAuthorForm(request.form)
    form_story = WorkStoryForm(request.form)
    form_newstory = StoryForm(request.form)

    if form.submit.data and form.validate():
        save_author_to_work(session, workid, form.author.data)
        return redirect(url_for('work', workid=workid))
    if form_story.submit_story.data and form_story.validate():
        save_story_to_work(session, workid, form_story.title.data)
        return redirect(url_for('work', workid=workid))
    if form_newstory.submit_story.data and form_story.validate():
        save_newstory_to_work(session, workid, form_newstory)
        return redirect(url_for('work', workid=workid))

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
    return render_template('work.html', work=work, authors=authors,
                           bookseries=bookseries, search_lists=search_list, form=form,
                           form_story=form_story, form_newstory=form_newstory,
                           stories=stories, prev_book=prev_book, next_book=next_book)

@app.route('/add_edition/<workid>', methods=["POST", "GET"])
def add_edition(workid):
    session = new_session()

    pubseries = []
    edition = Edition()

    selected_pubseries = 0
    search_list = publisher_list(session)

    form = EditionForm()

    form.pubseries.choices = [(0, "Ei sarjaa")]
    if request.method == 'GET':
        form.id.data = 0

    if form.validate_on_submit():
        edition.title = form.title.data
        edition.pubyear = form.pubyear.data
        edition.language = form.language.data
        edition.editionnum = form.edition.data
        translator = session.query(Person).filter(Person.name ==
                                                  form.translators.data).first()
        editor = session.query(Person).filter(Person.name ==
                                              form.editors.data).first()
        publisher = session.query(Publisher).filter(Publisher.name ==
                                                    form.publisher.data).first()
        if form.pubseries.data:
            edition.pubseries_id = form.pubseries.data
        edition.pubseriesnum = form.pubseriesnum.data
        edition.isbn = form.isbn.data
        edition.misc = form.misc.data
        session.add(edition)
        session.commit()

        # New edition so requires a row in Part table as well
        part = Part()
        part.work_id = workid
        part.edition_id = edition.id
        session.add(part)
        session.commit()
        return redirect(url_for('edition', editionid=edition.id))
    else:
        app.logger.debug("pubid={}".format(form.pubseries.data))
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_edition.html', form=form,
                           search_list=search_list,
                           selected_pubseries=selected_pubseries, translators=None,
                           editors=None, pubseries=None, source=None)
