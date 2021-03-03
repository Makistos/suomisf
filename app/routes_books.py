from app import app
from flask import Flask
from app.orm_decl import (Person, Author, Editor, Translator, Publisher, Work,
                          Edition, Pubseries, Bookseries, User, UserBook, Genre,
                          ShortStory, WorkGenre, Issue, IssueContent, Part)
from flask import render_template, request, flash, redirect, url_for, make_response
from app.forms import (WorkForm, EditionForm, WorkAuthorForm, WorkStoryForm, StoryForm,
                       EditionEditorForm, EditionTranslatorForm)
from .route_helpers import *
from typing import List, Dict
from sqlalchemy import func, distinct

# Book related routes


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
            # retval += {


@app.route('/books_by_genre/<genre>')
def books_by_genre(genre):

    session = new_session()

    works = session.query(Work)\
                   .join(WorkGenre)\
                   .filter(WorkGenre.work_id == Work.id)\
                   .join(Genre)\
                   .filter(Genre.id == WorkGenre.genre_id)\
                   .filter(Genre.name == genre)\
                   .all()
    return render_template('books.html', works=works)


@app.route('/books_by_origin/<country>')
def books_by_origin(country):
    session = new_session()

    if country[0] == '!':
        works = session.query(Work)\
                       .join(Part)\
                       .filter(Work.id == Part.work_id)\
                       .join(Author)\
                       .filter(Part.id == Author.part_id)\
                       .join(Person)\
                       .filter(Person.id == Author.person_id)\
                       .filter(Person.nationality != country[1:])\
                       .all()
    else:
        works = session.query(Work)\
                       .join(Part)\
                       .filter(Work.id == Part.work_id)\
                       .join(Author)\
                       .filter(Part.id == Author.part_id)\
                       .join(Person)\
                       .filter(Person.id == Author.person_id,
                               Person.nationality == country)\
                       .all()
    return render_template('books.html', works=works)


@app.route('/book_count_by_year/')
def book_count_by_year():
    session = new_session()

    # All based on edition pubyear
    counts = session.query(Edition.pubyear, func.count(Edition.pubyear).label('count'))\
                    .group_by(Edition.pubyear)\
                    .all()

    return render_template('book_count_by_year.html', counts=counts)


@app.route('/editions_by_year/<year>')
def editions_by_year(year):
    session = new_session()

    editions = session.query(Edition, Genre.name.label('genre_name'))\
                      .filter(Edition.pubyear == year)\
                      .join(Part)\
                      .filter(Part.edition_id == Edition.id)\
                      .join(Work)\
                      .filter(Work.id == Part.work_id)\
                      .join(WorkGenre)\
                      .filter(WorkGenre.work_id == Work.id)\
                      .join(Genre)\
                      .filter(Genre.id == WorkGenre.genre_id)\
                      .order_by(Work.creator_str)\
                      .all()
    count = len(set([x[0].id for x in editions]))
    return render_template('editions.html', editions=editions,
                           title='Julkaisut ' + str(year),
                           count=count)


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
    # app.logger.debug(''.join(letters))

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


@app.route('/part_delete/<partid>', methods=["POST", "GET"])
def part_delete(partid, session=None):

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
def edition_delete(editionid, session=None):
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
        form.author.data = author.name

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
    return render_template('person.html', id=authorid, form=form, search_lists=search_list, source='')


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


@app.route('/remove_story_from_work/<workid>/<storyid>', methods=["GET", "POST"])
def remove_story_from_work(workid, storyid):
    session = new_session()

    parts = session.query(Part)\
                   .filter(Part.work_id == workid,
                           Part.shortstory_id == storyid)\
                   .all()

    for part in parts:
        session.delete(part)

    stories = session.query(Part)\
                     .filter(Part.work_id == workid)\
                     .filter(Part.shortstory_id is not None)\
                     .scalar()

    if not stories is None:
        work = session.query(Work).filter(Work.id == workid).first()
        work.collection = False
        session.add(work)

    session.commit()

    return redirect(url_for('work', workid=workid))


@app.route('/remove_story_from_edition/<editionid>/<storyid>', methods=['GET', 'POST'])
def remove_story_from_edition(editionid, storyid):
    session = new_session()

    part = session.query(Part)\
                  .filter(Part.edition_id == editionid,
                          Part.shortstory_id == storyid)\
                  .first()
    session.delete(part)

    stories = session.query(Part)\
                     .filter(Part.edition_id == editionid)\
                     .filter(Part.shortstory_id is not None)\
                     .first()

    if len(stories) == 0:
        works = session.query(Work)\
                       .join(Part)\
                       .filter(Part.work_id == Work.id)\
                       .filter(Part.edition_id == editionid)\
                       .all()
        for work in works:
            work.collection = False
            session.add(work)
    session.commit()


@app.route('/remove_translator_from_work/<editionid>/<translatorid>', methods=['GET', 'POST'])
def remove_translator_from_work(editionid, translatorid):
    session = new_session()

    translator = session.query(Translator)\
                        .join(Part)\
                        .filter(Part.id == Translator.part_id)\
                        .filter(Part.edition_id == editionid)\
                        .filter(Translator.person_id == translatorid)\
                        .first()

    session.delete(translator)
    session.commit()


@app.route('/remove_editor_from_work/<editionid>/<editorid>', methods=['GET', 'POST'])
def remove_editor_from_work(editionid, editorid):
    session = new_session()

    editor = session.query(Editor)\
        .filter(Editor.edition_id == editionid)\
        .filter(Editor.person_id == editorid)\
        .first()
    session.delete(editor)
    session.commit()


@app.route('/remove_author_from_story<storyid>/<authorid>', methods=['GET', 'POST'])
def remove_author_from_story(storyid, authorid):
    session = new_session()

    parts = session.query(Part)\
                   .filter(Part.shortstory_id == storyid)\
                   .all()

    part_ids = [x.id for x in parts]

    authors = session.query(Author)\
                     .filter(Author.person_id == authorid)\
                     .filter(Author.part_id.in_(part_ids))\
                     .all()

    for author in authors:
        session.delete(author)
    session.commit()

    update_story_creators(session, storyid)

    return redirect(url_for('story', id=storyid))


@app.route('/edit_story/<id>', methods=['GET', 'POST'])
def edit_story(id):
    session = new_session()
    form = StoryForm(request.form)

    story = session.query(ShortStory)\
                   .filter(ShortStory.id == id)\
                   .first()

    if request.method == 'GET':
        form.title.data = story.title
        form.orig_title.data = story.orig_title
        form.language.data = story.language
        form.pubyear.data = story.pubyear

    if form.validate_on_submit():
        story.title = form.title.data
        story.orig_title = form.orig_title.database
        story.language = form.language.data
        story.pubyear = form.pubyear.data
        session.add(story)
        session.commit()
        return redirect(url_for('story', id=story.id))
    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_story.html', form=form)


@app.route('/edit_work_story/<id>/<workid>', methods=['GET', 'POST'])
def edit_work_story(id, workid):
    session = new_session()

    if id != 0:
        story = session.query(ShortStory).filter(ShortStory.id == id).first()
    else:
        story = ShortStory()

    form = StoryForm(request.form)

    if request.method == 'GET':
        form.work_id.data = workid
        form.author.data = author.name
        form.title.data = story.title
        form.orig_title.data = story.orig_title
        form.language.data = story.language
        form.pubyear.data = story.pubyear
        form.work_id.data = workid

    if form.validata_on_submit():
        story.title = form.title.data
        story.orig_title = form.orig_title.database
        story.language = form.language.data
        story.pubyear = form.pubyear.data
        session.add(story)
        session.commit()

        if workid == '0':
            return redirect(url_for('story', id=story.id))
        else:
            save_story_to_work(session, form.work_id.data, story.title)
            return redirect(url_for('work', workid=form.work_id))

    else:
        app.logger.debug('Errors: {}'.format(form.errors))

    return render_template('edit_story.html', form=form)
