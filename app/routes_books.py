import time
from app import app
from app.orm_decl import (Person, Work,
                          Edition, UserBook, Genre,
                          ShortStory, WorkGenre, Part, Country, Contributor)
from flask import render_template, request, redirect, url_for
from app.forms import (WorkForm)
from .route_helpers import *
from typing import List, Dict, Any
from sqlalchemy import func
import datetime

# Book related routes


@app.route('/books/lang')
def books_by_lang(lang: str) -> List[Any]:
    """ Returns a list of books such that each work is only represented by the
        first edition for given work in this language. """
    retval: List[Any] = []
    session = new_session()
    authors = session.query(Person)\
                     .join(Contributor, Contributor.role_id == 1)\
                     .filter(Person.id == Contributor.person_id)\
                     .join(Part, Part.id == Contributor.part_id)\
                     .join(Work)\
                     .filter(Work.id == Part.work_id)\
                     .order_by(Person.name)\
                     .all()

    for author in authors:
        for work in author.works:
            first_ed = sorted([x for x in work.editions if x.lang == lang],
                              key=lambda x: x['edition_num'])[0]
            # retval += {
    return retval


@app.route('/books_by_genre/<genre>')
def books_by_genre(genre: Any) -> Any:

    session = new_session()

    works_db = session.query(Work)\
        .join(WorkGenre)\
        .filter(WorkGenre.work_id == Work.id)\
        .join(Genre)\
        .filter(Genre.id == WorkGenre.genre_id)\
        .filter(Genre.name == genre)\
        .all()
    (works, count) = make_book_list(works_db)
    page: str = create_booklisting(works)
    return render_template('books.html', books=page, count=count)


@app.route('/books_by_origin/<country>')
def books_by_origin(country: str) -> Any:
    session = new_session()

    # country_id = session.query(Country.id).filter(
    #     Country.name == country).first()
    if country[0] == '!':
        country_id = int(country[1:])
        works_db = session.query(Work)\
            .join(Part, Part.id == Contributor.part_id)\
            .filter(Work.id == Part.work_id)\
            .join(Contributor, Contributor.role_id == 1)\
            .join(Person)\
            .filter(Person.id == Contributor.person_id)\
            .filter(Person.nationality_id != country_id)\
            .all()
    else:
        country_id = int(country)
        works_db = session.query(Work)\
            .join(Part, Part.id == Contributor.part_id)\
            .filter(Work.id == Part.work_id)\
            .join(Contributor, Contributor.role_id == 1)\
            .join(Person, Person.id == Contributor.person_id)\
            .filter(Person.nationality_id == country_id)\
            .all()
    (works, count) = make_book_list(works_db)
    page: str = create_booklisting(works)
    return render_template('books.html', books=page, count=count)


@app.route('/book_count_by_year/')
def book_count_by_year() -> str:
    session = new_session()

    # All based on edition pubyear
    counts = session.query(Edition.pubyear, func.count(Edition.pubyear).label('count'))\
                    .group_by(Edition.pubyear)\
                    .all()

    return render_template('book_count_by_year.html', counts=counts)


@app.route('/editions_by_year/<year>')
def editions_by_year(year: str) -> str:
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
                      .order_by(Work.author_str)\
                      .all()
    count = len(set([x[0].id for x in editions]))
    return render_template('editions.html', editions=editions,
                           title='Julkaisut ' + str(year),
                           count=count)


@app.route('/new_editions')
def new_editions() -> Any:
    curr_year = datetime.datetime.now().date().strftime('%Y')

    return redirect(url_for('editions_by_year', year=curr_year))


@app.route('/books')
def books() -> Any:
    session = new_session()
    works_db = session.query(Work)\
        .order_by(Work.author_str)\
        .all()
    (works, count) = make_book_list(works_db)
    page: str = create_booklisting(works)
    return render_template('books.html', books=page, count=count)


@app.route('/booksX/<letter>')
def booksX(letter: str) -> str:
    #times: List[float] = []
    # times.append(time.time())

    session = new_session()
    # times.append(time.time())
    works_db = session.query(Work).filter(Work.author_str != None)\
        .all()

    creators = [x.author_str[0] for x in works_db if len(x.author_str) > 0]
    # times.append(time.time())
    # times.append(time.time())
    letters = list(set([x[0] for x in creators if not x[0].islower()]))
    # times.append(time.time())
    letters.sort()
    # times.append(time.time())

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

    # times.append(time.time())
    # times.append(time.time())
    works_l = [x for x in works_db if x.author_str.startswith(letter)]
    # for i in range(len(times)):
    #    app.logger.debug('Perf for booksX:')
    #    app.logger.debug(f'Time {i}: {times[i] - times[0]}.')
    (works, count) = make_book_list(works_l)
    page: str = create_booklisting(works)
    genres = genre_summary(works_l)
    return render_template('books.html', letter=letter,
                           books=page, prev_letter=prev_letter, next_letter=next_letter,
                           count=count,
                           genres=genres)


@ app.route('/anthologies')
def anthologies() -> str:
    session = new_session()

    anthologies = session.query(Work).filter(Work.type == 2).all()

    (works, count) = make_book_list(anthologies)
    page: str = create_booklisting(works)
    return render_template('books.html', books=page, count=count)


@ app.route('/part_delete/<partid>', methods=["POST", "GET"])
def part_delete(partid: str, session: Any = None) -> None:

    commit = False
    if session == None:
        # This is an optimization hack. When calling this from
        # edition_delete() commit is not run for each part separately.
        commit = True
        session = new_session()

    translators = session.query(Contributor, Contributor.role_id == 2)\
        .filter(partid == Contributor.part_id)\
        .all()
    for translator in translators:
        session.delete(translator)

    authors = session.query(Contributor, Contributor.role_id == 1)\
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


def is_owned_edition(editionid: str) -> bool:
    session = new_session()
    owned = session.query(UserBook)\
        .filter(UserBook.edition_id == editionid)\
        .count()
    if owned > 0:
        return True
    else:
        return False


def is_owned_work(workid: str) -> bool:
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


@ app.route('/edition_delete/<editionid>', methods=["POST", "GET"])
def edition_delete(editionid: str, session: Any = None) -> None:
    """ Delete an edition along with rows from tables referencing
        the edition.
    """

    if (not current_user.is_admin) or is_owned_edition(editionid):
        return

    commit = False
    if session == None:
        # This is an optimization hack. When calling this from
        # edition_delete() commit is not run for each part separately.
        commit = True
        session = new_session()

    # Delete association rows for people

    editors = session.query(Contributor, Contributor.role_id == 3)\
        .join(Part, Part.id == Contributor.part_id)\
        .filter(Part.edition_id == editionid)\
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
    # for book in owned:
    #     session.delete(book)

    edition = session.query(Edition)\
        .filter(Edition.id == editionid)\
        .first()

    session.delete(edition)

    if commit:
        session.commit()
