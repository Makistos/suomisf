from app import app
from flask import Flask
from app.orm_decl import Person, Author, Editor, Translator, Publisher, Work,\
Edition, Pubseries, Bookseries, User, UserBook, Genre, ShortStory
from flask import render_template, request, flash, redirect, url_for, make_response
from app.forms import WorkForm, EditionForm, WorkAuthorForm
from .route_helpers import *
from typing import List, Dict

# Book related routes

def save_genres(session, work, genrefield):

    for g in genrefield.split(','):
        genreobj = Genre(workid=work.id, genre_name=g.strip())
        session.add(genreobj)
    session.commit()

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
    save_genres(session, work, form.genre.data)

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

@app.route('/books_by_genre/<genre>')
def books_by_genre(genre):

    session = new_session()

    works = session.query(Work)\
                   .join(Genre)\
                   .filter(Genre.workid == Work.id)\
                   .filter(Genre.genre_name == genre)\
                   .all()
    return render_template('books.html', works=works)

@app.route('/books')
def books():
    session = new_session()
    works = session.query(Work)\
                   .order_by(Work.creator_str)\
                   .all()
    return render_template('books.html', works=works)


@app.route('/booksX/<letter>')
def booksX(letter):
    session = new_session()
    works = session.query(Work)\
                   .order_by(Work.creator_str)\
                   .all()
    creators = [x.creator_str[0] for x in works]
    letters = list(set([x[0] for x in creators if not x[0].islower()]))
    letters.sort()
    #app.logger.debug(''.join(letters))

    works = session.query(Work)\
                   .filter(Work.creator_str.like(letter + '%'))\
                   .order_by(Work.creator_str)\
                   .all()

    prev_letter = None
    next_letter = None

    for idx, l in enumerate(letters):
        if l == letter:
            if idx > 0 and idx < len(letters) - 1:
                prev_letter = letters[idx-1]
                next_letter = letters[idx+1]
                break
            elif idx == 0:
                prev_letter = letters[-1]
                next_letter = letters[1]
                break
            elif idx == len(letters) - 1:
                prev_letter = letters[-2]
                next_letter = letters[0]
                break

    return render_template('books.html', letter=letter,
            works=works, prev_letter=prev_letter, next_letter=next_letter)

@app.route('/anthologies')
def anthologies():
    session = new_session()

    anthologies = session.query(Work).filter(Work.collection == 1).all()

    return render_template('books.html', works=anthologies)

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
                        .filter(Bookseries.id == work.bookseries_id,\
                                Work.id == workid)\
                        .first()
    search_list = {**search_list, **author_list(session)}

    if work.collection == True:
        stories = session.query(Part.title.label('title'),
                                ShortStory.title.label('orig_title'),
                                ShortStory.pubyear,
                                ShortStory.language,
                                ShortStory.genre,
                                ShortStory.id,\
                                ShortStory.creator_str)\
                         .join(Part)\
                         .filter(Part.shortstory_id == ShortStory.id)\
                         .filter(Part.work_id == workid)\
                         .group_by(Part.shortstory_id)\
                         .all()
    form = WorkAuthorForm(request.form)

    if form.validate_on_submit():
        save_author_to_work(session, workid, form.author.data)
        return redirect(url_for('work', workid=workid))
    else:
        app.logger.debug("Errors: {}".format(form.errors))

    return render_template('work.html', work=work, authors=authors,
            bookseries=bookseries, search_lists=search_list, form=form,
            stories=stories)

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
        if authors:
            form.author.data = ', '.join([a.name for a in authors])
        form.pubyear.data = work.pubyear
        form.language.data = work.language
        if bookseries:
            form.bookseries.data = bookseries.name
        form.bookseriesnum.data = work.bookseriesnum
        form.genre.data = ','.join([x.genre_name for x in work.genres])
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
        form.pages.data = edition.pages
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
        edition.pages = form.pages.data
        #if form.pubseriesnum.data is not None:
        #    try:
        #    edition.pubseriesnum = None
        #    except ValueError:
        #        edition.pubseriesnum = None
        #else:
        #    edition.pubseriesnum = None
        #if form.pubseriesnum.data == "":
        #    edition.pubseriesnum = 0
        #else:
        #    edition.pubseriesnum = int(form.pubseriesnum.data)
        edition.isbn = form.isbn.data
        edition.misc = form.misc.data
        session.add(edition)
        session.commit()
        return redirect(url_for('edition', editionid=edition.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
        #app.logger.debug("pubid={}".format(form.pubseries.data))
    return render_template('edit_edition.html', form=form,
            search_list=search_list, translators=translators,
            editors=editors, pubseries=pubseries, source=source,
            selected_pubseries=selected_pubseries)


@app.route('/edition/<editionid>')
def edition(editionid):
    stories = []
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
    translators = session.query(Person)\
                         .join(Translator)\
                         .filter(Person.id == Translator.person_id)\
                         .join(Part)\
                         .filter(Part.id == Translator.part_id,
                                 Part.edition_id == editionid)\
                         .all()
    editors = session.query(Person)\
                     .join(Editor)\
                     .filter(Person.id == Editor.person_id)\
                     .join(Edition)\
                     .filter(Edition.id == Editor.edition_id)\
                     .filter(Edition.id == editionid)\
                     .all()
    if edition.collection == True:
        stories = session.query(Part.title.label('title'),
                                ShortStory.title.label('orig_title'),
                                ShortStory.pubyear,
                                ShortStory.language,
                                ShortStory.genre,
                                ShortStory.id,
                                ShortStory.creator_str)\
                         .join(Part)\
                         .filter(Part.shortstory_id == ShortStory.id)\
                         .filter(Part.edition_id == editionid)\
                         .group_by(Part.shortstory_id)\
                         .all()

    return render_template('edition.html', edition = edition,
                            other_editions=other_editions,
                            translators=translators, editors=editors,
                            stories=stories)

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
        person = session.query(Person)\
                        .filter(Person.name == authorid)\
                        .first()
        parts = session.query(Part)\
                       .filter(work_id == workid)\
                       .all()
        for part in parts:
            app.logger.debug("part = {}, author= {}".format(part.id,
                authorid))
            author = Author(part_id=part.id, person_id=authorid)
            session.add(author)
        session.commit()
        return redirect(url_for('work', workid=work.id))
    else:
        app.logger.debug("Errors: {}".format(form.errors))
    return render_template('work.html', id = work.id, form=form, search_lists =
            search_list, source = '')

@app.route('/remove_author_from_work/<workid>/<authorid>', methods=["GET", "POST"])
def remove_author_from_work(workid, authorid):

    session = new_session()

    parts = session.query(Author)\
                   .join(Part)\
                   .filter(Part.work_id == workid)\
                   .filter(Author.part_id == Part.id, Author.person_id == authorid)\
                   .all()
    for part in parts:
        session.delete(part)
    session.commit()

    update_creators(session, workid)

    return redirect(url_for('work', workid=workid))


@app.route('/story/<id>', methods=['GET', 'POST'])
def story(id):
    search_list = {}

    session = new_session()
    story = session.query(Part.title.label('title'),
                          ShortStory.title.label('orig_title'),
                          ShortStory.pubyear,
                          ShortStory.language,
                          ShortStory.genre,
                          ShortStory.id)\
                   .join(Part)\
                   .filter(Part.shortstory_id == id)\
                   .first()

    editions = session.query(Edition)\
                      .join(Part)\
                      .filter(Part.shortstory_id == id)\
                      .filter(Part.edition_id == Edition.id)\
                      .all()

    works = session.query(Work)\
                   .join(Part)\
                   .filter(Part.shortstory_id == id)\
                   .filter(Part.work_id == Work.id)\
                   .all()

    authors = session.query(Person)\
                     .join(Author)\
                     .filter(Person.id == Author.person_id)\
                     .join(Part)\
                     .filter(Author.part_id == Part.id,
                             Part.shortstory_id == id)\
                     .all()

    search_list = {**search_list, **author_list(session)}

    return render_template('story.html', id=id, story=story,
                           editions=editions, works=works,
                           authors=authors, search_lists=search_list)
