from app import app
from flask import Flask
from app.orm_decl import Person, Author, Editor, Translator, Publisher, Work, Edition, Pubseries, Bookseries, User, UserBook
from flask import render_template, request, flash, redirect, url_for, make_response
from app.forms import WorkForm, EditionForm
from .route_helpers import *

# Book related routes


def save_work(session, form, work):
    author = session.query(Person).filter(Person.name ==
            form.authors.data).first()
    work.id = form.id.data
    work.title = form.title.data
    work.pubyear = form.pubyear.data
    work.language = form.language.data
    if form.bookseries.data != '':
        bookseries = session.query(Bookseries).filter(Bookseries.name ==
                form.bookseries.data).first()
        work.bookseries_id = bookseries.id
    work.bookseriesnum = form.bookseriesnum.data
    work.genre = form.genre.data
    work.misc = form.misc.data
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


@app.route('/books/lang')
def books_by_lang(lang):
    """ Returns a list of books such that each work is only represented by the
        first edition for given work in this language. """
    retval = []
    session = new_session()
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .join(Work)\
                     .filter(Work.id == Author.work_id)\
                     .order_by(Person.name)\
                     .all()

    for author in authors:
        for work in author.works:
            first_ed = sorted([x for x in work.editions if x.lang == lang],
                        key=lambda x: x['edition_num'])[0]
            #retval += {



@app.route('/books')
def books():
    session = new_session()
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .order_by(Person.name)\
                     .all()
    return render_template('books.html', authors=authors)


@app.route('/booksX/<letter>')
def booksX(letter):
    session = new_session()
    #app.logger.debug(session.query(Person).join(BookPerson).filter(Person.id ==
    #                BookPerson.person_id).filter(BookPerson.type ==
    #                'A').filter(Person.name.ilike('A%')).order_by(Person.name))
    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .filter(Person.name.ilike(letter + '%')).order_by(Person.name).all()
    return render_template('books.html', authors=authors, letter=letter)


@app.route('/work/<workid>')
def work(workid):
    session = new_session()
    work = session.query(Work).filter(Work.id == workid).first()
    #editions = session.query(Edition).filter(Edition.work_id == workid).all()
    authors = people_for_book(session, workid, 'A')
    translators = people_for_book(session, workid, 'T')
#    s = ''
    editors = people_for_book(session, workid, 'E')
    return render_template('work.html', work=work, authors=authors,
            translators=translators, editors=editors)

@app.route('/edit_work/<workid>', methods=["POST", "GET"])
def edit_work(workid):
    search_list = {}
    session = new_session()
    if workid != 0:
        work = session.query(Work)\
                      .filter(Work.id == workid)\
                      .first()
        authors = session.query(Person)\
                         .join(Author)\
                         .join(Part)\
                         .filter(Author.person_id == Person.id,\
                                 Author.part_id == Part.id,
                                 Part.work_id == workid)\
                         .all()
        bookseries = session.query(Bookseries)\
                            .join(Work)\
                            .filter(Bookseries.id == work.bookseries_id,\
                                    Work.id == workid)\
                            .first()
    else:
        work = Work()

    search_list = {**search_list, **author_list(session)}

    form = WorkForm(request.form)
    if request.method == 'GET':
        form.id.data = work.id
        form.title.data = work.title
        form.authors.data = ', '.join([a.name for a in authors])
        form.pubyear.data = work.pubyear
        form.language.data = work.language
        publisher = session.query(Publisher).filter(Publisher.name ==
                form.publisher.data).first()
        if bookseries:
            form.bookseries.data = bookseries.name
        form.bookseriesnum.data = work.bookseriesnum
        form.genre.data = work.genre
        form.misc.data = work.misc
        form.source.data = work.fullstring

    if form.validate_on_submit():
        save_work(session, form, work) # Save work, edition and part
        return redirect(url_for('work', workid=work.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_work.html', id = work.id, form=form, search_lists =
            search_list, source = work.fullstring)

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

@app.route('/edit_edition/<editionid>', methods=["POST", "GET"])
def edit_edition(editionid):
    session = new_session()
    publisher_series = {}
    publisher = {}
    pubseries = []
    translators = []
    editors = []
    if str(editionid) != '0':
        edition = session.query(Edition)\
                          .filter(Edition.id == editionid)\
                          .first()
        publisher = session.query(Publisher)\
                           .filter(Publisher.id == edition.publisher_id)\
                           .first()
        translators = session.query(Person)\
                             .join(Translator)\
                             .join(Part)\
                             .filter(Translator.person_id == Person.id)\
                             .filter(Translator.part_id == Part.id,
                                     Part.edition_id == Edition.id,
                                     Edition.id == editionid)\
                             .first()
        editors = session.query(Person)\
                         .join(Editor)\
                         .filter(Editor.person_id == Person.id)\
                         .filter(Editor.edition_id == editionid)\
                         .first()
        pubseries = \
                session.query(Pubseries)\
                       .join(Edition)\
                       .filter(Pubseries.id == edition.pubseries_id)\
                       .first()
        if publisher:
            publisher_series = pubseries_list(session, publisher.id)
        else:
            publisher_series = {}
    form = EditionForm()
    selected_pubseries = '0'
    search_list = publisher_list(session)
    source = edition.fullstring
    if publisher_series:
        form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series['pubseries']
    else:
        form.pubseries.choices = [('0', "Ei sarjaa")]
    if request.method == 'GET':
        form.id.data = edition.id
        form.title.data = edition.title
        form.pubyear.data = edition.pubyear
        form.language.data = edition.language
        form.edition.data = edition.editionnum
        if publisher:
            form.publisher.data = publisher.name
        if translators:
            form.translators.data = translators.name
        if editors:
            form.editors.data = editors.name
        if pubseries:
            form.pubseries.data = pubseries.name
        form.pubseriesnum.data = edition.pubseriesnum
        form.isbn.data = edition.isbn
        form.misc.data = edition.misc
        if pubseries:
            i = 0
            for idx, s in enumerate(publisher_series['pubseries']):
                if s[1] == pubseries.name:
                    i = s[0]
                    break
            form.pubseries.choices = [('0', 'Ei sarjaa')] + publisher_series['pubseries']
            form.pubseries.default = str(i)
            selected_pubseries = str(i)
        #form.translators.data = ', '.join([t.name for t in translators])
        #form.editors.data = ', '.join([e.name for e in editors])
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
        if form.pubseries.data == 0:
            edition.pubseries_id = None
        else:
            edition.pubseries_id = form.pubseries.data
        edition.publisher_id = publisher.id
        edition.pubseriesnum = form.pubseriesnum.data
        edition.isbn = form.isbn.data
        edition.misc = form.misc.data
        session.add(edition)
        session.commit()
        return redirect(url_for('edition', editionid=edition.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
        app.logger.debug("pubid={}".format(form.pubseries.data))
    return render_template('edit_edition.html', form=form,
            search_list=search_list, translators=translators,
            editors=editors, pubseries=pubseries, source=source,
            selected_pubseries=selected_pubseries)


@app.route('/edition/<editionid>')
def edition(editionid):
    session = new_session()
    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()
    other_editions = session.query(Edition)\
                            .join(Part)\
                            .filter(Part.work_id == edition.work.id)\
                            .filter(Edition.id != edition.id)\
                            .order_by(Edition.language, Edition.pubyear)\
                            .all()
    return render_template('edition.html', edition = edition,
                            other_editions=other_editions)

@app.route('/part_delete/<partid>', methods=["POST", "GET"])
def part_delete(partid, session = None):

    commit = False
    if session == None:
        # This is an optimization hack. When calling this from
        # edition_delete() commit is not run for each part separately.
        commit = True
        session = new_session()

    translators = session.query(Translator)\
                         .join(Part)\
                         .filter(Part.person_id == Translator.id)\
                         .filter(Part.id == partid)\
                         .all()
    for translator in translators:
        session.delete(translator)

    authors = session.query(Author)\
                     .join(Part)\
                     .filter(Part.id == partid)\
                     .all()
    for author in authors:
        session.delete(author)

    part = session.query(Part)\
                  .filter(Part.id == partid)\
                  .first()
    session.delete(part)

    if commit:
        session.commit()


def is_owned_edition(editionid):
    session = new_session()
    owned = session.query(UserBook)\
                   .filter(UserBook.edition_id == editionid)\
                   .count()
    if owned > 0:
        return True
    else:
        return False


def is_owned_work(workid):
    session = new_session()
    owned = session.query(UserBook)\
                   .join(Edition)\
                   .filter(UserBook.edition_id == Edition.id)\
                   .join(Part)\
                   .filter(Part.edition_id == Edition.id, Part.work_id ==
                           workid)\
                   .count()
    if owned > 0:
        return True
    else:
        return False


@app.route('/edition_delete/<editionid>', methods=["POST", "GET"])
def edition_delete(editionid, session = None):
    """ Delete an edition along with rows from tables referencing
        the edition.
    """

    if (not current_user.is_admin) or is_owned_edition(editionid):
        return ""

    commit = False
    if session == None:
        # This is an optimization hack. When calling this from
        # edition_delete() commit is not run for each part separately.
        commit = True
        session = new_session()

    # Delete association rows for people

    editors = session.query(Editor)\
                    .filter(Edition.edition_id == editionid)\
                    .all()
    for editor in editors:
        session.delete(editor)


    parts = session.query(Part)\
                   .filter(Part.edition_id == editionid)\
                   .all()
    for part in parts:
        part_delete(part.id, session)

    userbooks = session.query(UserBook)\
                   .filter(UserBook.edition_id == editionid)\
                   .all()
    for book in owned:
        session.delete(book)

    edition = session.query(Edition)\
                     .filter(Edition.id == editionid)\
                     .first()

    session.delete(edition)

    if commit:
        session.commit()

    return ""

@app.route('/work_delete/<workid>', methods=["POST", "GET"])
def work_delete(workid):
    """ Delete a work from the database along with all the editions
        and all the rows associated with them.
    """
    if (not current_user.is_admin) or is_owned_work(editionid):
        return ""

    session = new_session()

    editions = session.query(Edition)\
                      .join(Part)\
                      .filter(Edition.id == Part.edition_id)\
                      .filter(Part.work_id == workid)\
                      .all()

    for edition in editions:
        edition_delete(edition.id, session)

    work = session.query(Work)\
                  .filter(Work.id == workid)\
                  .first()
    session.delete(work)

    session.commit()

@app.route('/add_authored/<authorid>', methods=["POST", "GET"])
def add_authored(authorid):
    session = new_session()
    author = session.query(Person)\
                    .filter(Person.id == authorid)\
                    .first()
    work = Work()

    search_list = {}

    form = WorkForm(request.form)
    if request.method == 'GET':
        form.authors.data = author.name

    if form.validate_on_submit():
        save_work(session, form, work) # Save work, edition and part
        return redirect(url_for('work', bookid=work.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('edit_work.html', id = work.id, form=form, search_lists =
            search_list, source = '')
    pass
