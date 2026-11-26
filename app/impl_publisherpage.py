"""
The new publisher page: its facts, series and magazines
(GET /api/publishers/<id>/summary) and its editions one page at a time
(GET /api/publishers/<id>/editions).

A publisher publishes editions, so the page lists editions, not works
(owner, 2026-11-26). GET /api/publishers/<id> keeps returning every edition
for the current page.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app import app
from app.impl import ResponseType
from app.impl_bookindex import (WISHLIST, BadParameter, _bookseries, _brief,
                                _int, _named, _own_marks, _text_match,
                                _translators)
from app.orm_decl import (Bookseries, Edition, EditionContributor, Genre,
                          Issue, Magazine, Person, Publisher, Pubseries,
                          UserBook, Work, WorkContributor, WorkGenre)
from app.route_helpers import new_session
from app.thumbnails import thumb_src
from app.types import HttpResponseCode

ROWS = (50, 100, 200)
DEFAULT_ROWS = 100
SORTS = ('oldest', 'newest', 'title', 'author')
WRITER = 1


def _publisher_id(value: str) -> int:
    if not str(value).isdigit():
        raise BadParameter('id')
    return int(value)


def _not_found() -> ResponseType:
    return ResponseType('Kustantajaa ei löytynyt.',
                        HttpResponseCode.NOT_FOUND.value)


def _own_counts(session: Any, pid: int,
                user_id: Optional[int]) -> Optional[Dict[str, int]]:
    """How many of the publisher's printings the user owns and wishes for."""
    if user_id is None:
        return None
    rows = session.query(UserBook.condition_id,
                         func.count(func.distinct(UserBook.edition_id))) \
        .join(Edition, Edition.id == UserBook.edition_id) \
        .filter(UserBook.user_id == user_id, Edition.publisher_id == pid) \
        .group_by(UserBook.condition_id).all()
    owned = sum(n for c, n in rows if c is not None and 0 < c < WISHLIST)
    wished = sum(n for c, n in rows if c == WISHLIST)
    return {'editions': owned, 'wishlisted': wished}


def publisher_summary(pub_id: str,
                      user_id: Optional[int] = None) -> ResponseType:
    """
    The publisher's facts, series and magazines, counted in the database.

    Returns:
        ResponseType: {id, name, fullname, description, links, editions,
        works, first_year, last_year, series: [{id, name, editions,
        first_year, last_year}], magazines: [{id, name, type, issues,
        first_year, last_year}], genres: [{abbr, name, works}] (distinct
        works, most first), own: {editions, wishlisted} for the logged-in
        user (null for a visitor)}; 400 for a bad id, 404 for an unknown
        one.
    """
    try:
        pid = _publisher_id(pub_id)
    except BadParameter:
        return ResponseType('Virheellinen kustantajan tunniste.',
                            HttpResponseCode.BAD_REQUEST.value)
    session = new_session()
    try:
        publisher = session.query(Publisher).options(
            selectinload(Publisher.links)).filter(Publisher.id == pid).first()
        if publisher is None:
            return _not_found()
        n, works, first, last = session.query(
            func.count(Edition.id), func.count(func.distinct(Edition.work_id)),
            func.min(Edition.pubyear), func.max(Edition.pubyear)
        ).filter(Edition.publisher_id == pid).one()
        series = [{'id': r.id, 'name': r.name, 'editions': r.n,
                   'first_year': r.first, 'last_year': r.last}
                  for r in session.query(
                      Pubseries.id, Pubseries.name,
                      func.count(Edition.id).label('n'),
                      func.min(Edition.pubyear).label('first'),
                      func.max(Edition.pubyear).label('last'))
                  .outerjoin(Edition, Edition.pubseries_id == Pubseries.id)
                  .filter(Pubseries.publisher_id == pid)
                  .group_by(Pubseries.id, Pubseries.name)
                  .order_by(Pubseries.name, Pubseries.id).all()]
        magazines = _magazines(session, pid)
        # Works, not editions (owner, 2026-11-27): 28 reprints of
        # Hobitti count once.
        works_n = func.count(func.distinct(Edition.work_id))
        genres = [{'abbr': g.abbr, 'name': g.name, 'works': g.n}
                  for g in session.query(Genre.abbr, Genre.name,
                                         works_n.label('n'))
                  .join(WorkGenre, WorkGenre.genre_id == Genre.id)
                  .join(Edition, Edition.work_id == WorkGenre.work_id)
                  .filter(Edition.publisher_id == pid)
                  .group_by(Genre.abbr, Genre.name)
                  .order_by(works_n.desc(), Genre.name).all()]
        data = {
            'id': publisher.id, 'name': publisher.name,
            'fullname': publisher.fullname,
            'description': publisher.description,
            'links': [{'link': li.link, 'description': li.description}
                      for li in publisher.links or []],
            'editions': n, 'works': works,
            'first_year': first, 'last_year': last,
            'series': series, 'magazines': magazines, 'genres': genres,
            'own': _own_counts(session, pid, user_id),
        }
    except SQLAlchemyError as exp:
        app.logger.error(f'publisher_summary: {exp}')
        return ResponseType('publisher_summary: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    finally:
        session.close()
    return ResponseType(data, HttpResponseCode.OK.value)


def _magazines(session: Any, pid: int) -> List[Dict[str, Any]]:
    """The publisher's magazines with their issue counts and years."""
    counts = {r[0]: (r[1], r[2], r[3]) for r in session.query(
        Issue.magazine_id, func.count(Issue.id), func.min(Issue.year),
        func.max(Issue.year)).group_by(Issue.magazine_id).all()}
    rows = []
    for m in session.query(Magazine).options(selectinload(Magazine.type)) \
            .filter(Magazine.publisher_id == pid).order_by(Magazine.name):
        n, first, last = counts.get(m.id, (0, None, None))
        rows.append({'id': m.id, 'name': m.name,
                     'type': m.type.name if m.type else None,
                     'issues': n, 'first_year': first, 'last_year': last})
    return rows


def _filtered(session: Any, pid: int, params: Dict[str, str]) -> Any:
    query = session.query(Edition.id).join(Work, Work.id == Edition.work_id) \
        .filter(Edition.publisher_id == pid)
    text = (params.get('q') or '').strip()
    if text:
        writers = session.query(WorkContributor.work_id).join(
            Person, or_(Person.id == WorkContributor.person_id,
                        Person.id == WorkContributor.real_person_id)
        ).filter(WorkContributor.role_id == WRITER,
                 or_(_text_match(Person.name, text),
                     _text_match(Person.alt_name, text)))
        query = query.filter(or_(
            Work.id.in_(writers), _text_match(Edition.title, text),
            _text_match(Work.title, text), _text_match(Work.orig_title, text)))
    year_min = _int(params, 'year_min')
    year_max = _int(params, 'year_max')
    if year_min is not None:
        query = query.filter(Edition.pubyear >= year_min)
    if year_max is not None:
        query = query.filter(Edition.pubyear <= year_max)
    return query


def _order(sort: str) -> List[Any]:
    if sort == 'newest':
        return [Edition.pubyear.desc().nulls_last(), Work.author_str,
                Edition.title, Edition.id]
    if sort == 'title':
        # The title the row shows: a few printings have an empty title, and
        # the page shows their work's (edition 8833 sorted first, 2026-11-26).
        shown = func.coalesce(func.nullif(func.trim(Edition.title), ''),
                              Work.title)
        return [shown, Edition.pubyear, Edition.id]
    if sort == 'author':
        return [Work.author_str, Edition.pubyear, Edition.title, Edition.id]
    return [Edition.pubyear.asc().nulls_last(), Work.author_str,
            Edition.title, Edition.id]


def _row(e: Edition, owned: set, wished: set) -> Dict[str, Any]:
    work = e.work
    image = next((i for i in e.images or [] if i.image_src), None)
    return {
        'id': e.id, 'title': e.title, 'subtitle': e.subtitle,
        'pubyear': e.pubyear, 'version': e.version,
        'editionnum': e.editionnum,
        'pubseries': _named(e.pubseries), 'pubseriesnum': e.pubseriesnum,
        'translators': [_brief(p) for p in _translators(e)],
        'work': {
            'id': work.id, 'title': work.title,
            'orig_title': work.orig_title, 'pubyear': work.pubyear,
            'author_str': work.author_str, 'type': work.type,
            'bookseries': _bookseries(work.bookseries),
            'bookseriesnum': work.bookseriesnum,
            'authors': [_brief(p) for p in work.authors or []],
            'genres': [{'id': g.id, 'abbr': g.abbr, 'name': g.name}
                       for g in work.genres or []],
        } if work else None,
        'cover': ({'image_src': image.image_src,
                   'thumb_src': thumb_src(image.image_src)}
                  if image else None),
        'owned': e.id in owned, 'wishlisted': e.id in wished,
    }


def publisher_editions(pub_id: str, params: Dict[str, str],
                       user_id: Optional[int] = None) -> ResponseType:
    """
    One page of the publisher's editions.

    Args:
        pub_id: the publisher.
        params: q (from the start of a word of the author's name, the
            edition's or work's title or the original title); year_min and
            year_max (the edition's year); sort (oldest, newest, title,
            author; oldest first by default); page (from 1); rows (50, 100
            or 200; 100 by default).
        user_id: the logged-in user, for their owned and wishlisted marks.

    Returns:
        ResponseType: {total, page, rows, editions: [...]}; 400 for a
        parameter that can't be used, 404 for an unknown publisher.
    """
    try:
        pid = _publisher_id(pub_id)
        page = _int(params, 'page')
        page = 1 if page is None else page
        rows = _int(params, 'rows')
        rows = DEFAULT_ROWS if rows is None else rows
        sort = (params.get('sort') or 'oldest').strip()
        if page < 1 or rows not in ROWS or sort not in SORTS:
            raise BadParameter('page, rows or sort')
        session = new_session()
        try:
            if session.query(Publisher.id).filter(
                    Publisher.id == pid).first() is None:
                return _not_found()
            query = _filtered(session, pid, params)
            total = query.order_by(None).count()
            ids = [r[0] for r in query.order_by(*_order(sort))
                   .offset((page - 1) * rows).limit(rows).all()]
            editions = session.query(Edition).filter(Edition.id.in_(ids)) \
                .options(
                    selectinload(Edition.work).selectinload(Work.authors),
                    selectinload(Edition.work).selectinload(Work.genres),
                    selectinload(Edition.work).selectinload(Work.bookseries)
                    .selectinload(Bookseries.partof),
                    selectinload(Edition.pubseries),
                    selectinload(Edition.images),
                    selectinload(Edition.contributions)
                    .selectinload(EditionContributor.person),
            ).all() if ids else []
            owned, wished = _own_marks(session, user_id, ids)
            by_id = {e.id: e for e in editions}
            result = [_row(by_id[i], owned, wished) for i in ids
                      if i in by_id]
        finally:
            session.close()
    except BadParameter as exp:
        return ResponseType(f'publisher_editions: virheellinen {exp}.',
                            HttpResponseCode.BAD_REQUEST.value)
    except SQLAlchemyError as exp:
        app.logger.error(f'publisher_editions: {exp}')
        return ResponseType('publisher_editions: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType({'total': total, 'page': page, 'rows': rows,
                         'editions': result}, HttpResponseCode.OK.value)
