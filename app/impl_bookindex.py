"""
The paged book index (GET /api/bookindex) for the new book index page.

Every work, filtered, sorted and paged on the server, with only what a list
row shows. POST /api/searchworks keeps serving the current page and the
book suggestions unchanged.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app import app
from app.impl import ResponseType
from app.orm_decl import (Bookseries, Edition, EditionContributor, Genre,
                          Person, UserBook, Work, WorkContributor, WorkGenre)
from app.route_helpers import new_session
from app.types import HttpResponseCode

ROWS = (50, 100, 200)
SORTS = ('author', 'title', 'year', 'newest')
WRITER = 1
TRANSLATOR = 2
# userbook.condition_id: 1-5 owned in that condition, 6 on the wishlist.
WISHLIST = 6


class BadParameter(ValueError):
    """A parameter that can't be used; reported as 400."""


def _int(params: Dict[str, str], name: str) -> Optional[int]:
    value = (params.get(name) or '').strip()
    if not value:
        return None
    if not value.isdigit():
        raise BadParameter(name)
    return int(value)


def _ints(params: Dict[str, str], name: str) -> List[int]:
    values = [v.strip() for v in (params.get(name) or '').split(',')
              if v.strip()]
    if not all(v.isdigit() for v in values):
        raise BadParameter(name)
    return [int(v) for v in values]


def _words(params: Dict[str, str], name: str) -> List[str]:
    return [v.strip() for v in (params.get(name) or '').split(',')
            if v.strip()]


def _text_match(column: Any, value: str) -> Any:
    """From the start of the text or of any word in it, as in searchworks."""
    return or_(column.ilike(f'{value}%'), column.ilike(f'% {value}%'))


def _filtered(session: Any, params: Dict[str, str]) -> Any:
    query = session.query(Work.id)

    author = (params.get('author') or '').strip()
    if author:
        writers = session.query(WorkContributor.work_id).join(
            Person, or_(Person.id == WorkContributor.person_id,
                        Person.id == WorkContributor.real_person_id)
        ).filter(WorkContributor.role_id == WRITER,
                 or_(Person.name.ilike(f'{author}%'),
                     Person.alt_name.ilike(f'{author}%')))
        query = query.filter(Work.id.in_(writers))

    title = (params.get('title') or '').strip()
    if title:
        query = query.filter(_text_match(Work.title, title))
    orig_title = (params.get('orig_title') or '').strip()
    if orig_title:
        query = query.filter(_text_match(Work.orig_title, orig_title))

    origyear_min = _int(params, 'origyear_min')
    origyear_max = _int(params, 'origyear_max')
    if origyear_min is not None:
        query = query.filter(Work.pubyear >= origyear_min)
    if origyear_max is not None:
        query = query.filter(Work.pubyear <= origyear_max)

    # Any Finnish printing in the range, not only the first.
    printyear_min = _int(params, 'printyear_min')
    printyear_max = _int(params, 'printyear_max')
    if printyear_min is not None or printyear_max is not None:
        printed = session.query(Edition.work_id)
        if printyear_min is not None:
            printed = printed.filter(Edition.pubyear >= printyear_min)
        if printyear_max is not None:
            printed = printed.filter(Edition.pubyear <= printyear_max)
        query = query.filter(Work.id.in_(printed))

    nationality = _int(params, 'nationality')
    if nationality is not None:
        from_country = session.query(WorkContributor.work_id).join(
            Person, Person.id == WorkContributor.person_id
        ).filter(WorkContributor.role_id == WRITER,
                 Person.nationality_id == nationality)
        query = query.filter(Work.id.in_(from_country))

    types = _ints(params, 'type')
    if types:
        query = query.filter(Work.type.in_(types))

    genres = _words(params, 'genre')
    if genres:
        in_genre = session.query(WorkGenre.work_id).join(
            Genre, Genre.id == WorkGenre.genre_id
        ).filter(Genre.abbr.in_(genres))
        query = query.filter(Work.id.in_(in_genre))

    initial = (params.get('initial') or '').strip()
    if initial:
        if len(initial) != 1 or not initial.isalpha():
            raise BadParameter('initial')
        query = query.filter(
            func.upper(func.left(Work.author_str, 1)) == initial.upper())
    return query


def _order(sort: str) -> Tuple[Any, ...]:
    if sort == 'title':
        return (Work.title, Work.id)
    if sort == 'year':
        return (Work.pubyear.asc().nulls_last(), Work.title, Work.id)
    if sort == 'newest':
        return (Work.pubyear.desc().nulls_last(), Work.title, Work.id)
    return (Work.author_str, Work.title, Work.id)


def _brief(p: Person) -> Dict[str, Any]:
    return {'id': p.id, 'name': p.name, 'alt_name': p.alt_name}


def _bookseries(series: Optional[Bookseries]) -> Optional[Dict[str, Any]]:
    """A work's book series with the series it belongs to, or None."""
    if series is None:
        return None
    return {'id': series.id, 'name': series.name,
            'partof': ({'id': series.partof.id, 'name': series.partof.name}
                       if series.partof else None)}


def _named(item: Any) -> Optional[Dict[str, Any]]:
    return {'id': item.id, 'name': item.name} if item else None


def _translators(edition: Optional[Edition]) -> List[Person]:
    found: List[Person] = []
    for c in (edition.contributions or []) if edition else []:
        if c.role_id == TRANSLATOR and c.person and c.person not in found:
            found.append(c.person)
    return found


def _row(work: Work, owned: Set[int], wished: Set[int]) -> Dict[str, Any]:
    # By laitos, then printing: each laitos's printings stay together.
    editions = sorted(work.editions or [],
                      key=lambda e: (e.version or 1, e.editionnum or 1,
                                     e.pubyear or 9999, e.id))
    first = editions[0] if editions else None
    translators = _translators(first)
    # The real writers behind a pen name several people share.
    real: List[Person] = []
    for c in work.contributions or []:
        if c.role_id == WRITER and c.real_person and \
                c.real_person not in real:
            real.append(c.real_person)
    series = work.bookseries
    return {
        'id': work.id,
        'title': work.title,
        'subtitle': work.subtitle,
        'orig_title': work.orig_title,
        'pubyear': work.pubyear,
        'author_str': work.author_str,
        'type': work.type,
        'authors': [_brief(p) for p in work.authors or []],
        'real_authors': [_brief(p) for p in real],
        'translators': [_brief(p) for p in translators],
        'bookseries': _bookseries(series),
        'bookseriesnum': work.bookseriesnum,
        'genres': [{'id': g.id, 'abbr': g.abbr, 'name': g.name}
                   for g in work.genres or []],
        'printings': len(editions),
        'first_edition': ({
            'id': first.id,
            'pubyear': first.pubyear,
            'publisher': _named(first.publisher),
            'pubseries': _named(first.pubseries),
        } if first else None),
        # Each printing on its own line: a new laitos can have another
        # title, translator and publisher.
        'editions': [{'id': e.id, 'title': e.title, 'pubyear': e.pubyear,
                      'editionnum': e.editionnum, 'version': e.version,
                      'translators': [_brief(p) for p in _translators(e)],
                      'publisher': _named(e.publisher),
                      'pubseries': _named(e.pubseries),
                      'owned': e.id in owned, 'wishlisted': e.id in wished}
                     for e in editions],
    }


def _own_marks(session: Any, user_id: Optional[int],
               edition_ids: List[int]) -> Tuple[Set[int], Set[int]]:
    """The user's own owned and wishlisted printings among these."""
    if user_id is None or not edition_ids:
        return set(), set()
    rows = session.query(UserBook.edition_id, UserBook.condition_id).filter(
        UserBook.user_id == user_id,
        UserBook.edition_id.in_(edition_ids)).all()
    owned = {e for e, c in rows if c is not None and 0 < c < WISHLIST}
    wished = {e for e, c in rows if c == WISHLIST}
    return owned, wished


def book_index(params: Dict[str, str],
               user_id: Optional[int] = None) -> ResponseType:
    """
    One page of the book index.

    Args:
        params: author, title, orig_title (prefix of the text or a word);
            origyear_min/max (the original's year); printyear_min/max (any
            Finnish printing); nationality (writer's country id); type
            (comma-separated work type ids); genre (comma-separated genre
            abbreviations, any of them); initial (first letter of the
            author string); sort (author, title, year, newest); page
            (from 1); rows (50, 100 or 200).
        user_id: the logged-in user, for their own owned and wishlisted
            marks on the printings; None for a visitor.

    Returns:
        ResponseType: {total, page, rows, works: [row, ...]}; 400 for a
        parameter that can't be used.
    """
    try:
        page = _int(params, 'page')
        page = 1 if page is None else page
        rows = _int(params, 'rows')
        rows = ROWS[0] if rows is None else rows
        sort = (params.get('sort') or 'author').strip()
        if page < 1 or rows not in ROWS or sort not in SORTS:
            raise BadParameter('page, rows or sort')
        session = new_session()
        try:
            query = _filtered(session, params)
            total = query.order_by(None).count()
            ids = [r[0] for r in query.order_by(*_order(sort))
                   .offset((page - 1) * rows).limit(rows).all()]
            works = session.query(Work).filter(Work.id.in_(ids)).options(
                selectinload(Work.authors),
                selectinload(Work.genres),
                selectinload(Work.bookseries).selectinload(Bookseries.partof),
                selectinload(Work.contributions)
                .selectinload(WorkContributor.real_person),
                selectinload(Work.editions).selectinload(Edition.publisher),
                selectinload(Work.editions).selectinload(Edition.pubseries),
                selectinload(Work.editions)
                .selectinload(Edition.contributions)
                .selectinload(EditionContributor.person),
            ).all() if ids else []
            owned, wished = _own_marks(
                session, user_id,
                [e.id for w in works for e in w.editions or []])
            by_id = {w.id: w for w in works}
            result = [_row(by_id[i], owned, wished) for i in ids
                      if i in by_id]
        finally:
            session.close()
    except BadParameter as exp:
        app.logger.info(f'book_index: bad parameter {exp}.')
        return ResponseType(f'Virheellinen parametri: {exp}',
                            HttpResponseCode.BAD_REQUEST.value)
    except SQLAlchemyError as exp:
        app.logger.error(f'book_index: {exp}')
        return ResponseType('book_index: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType({'total': total, 'page': page, 'rows': rows,
                         'works': result}, HttpResponseCode.OK.value)
