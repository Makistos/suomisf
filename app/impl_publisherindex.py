"""
The light publisher list (GET /api/publisherindex) for the new publisher
list page.

Each publisher with its edition count, year span and magazines, counted in
the database. GET /api/publishers keeps returning every edition for the
current page.
"""

from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.impl import ResponseType
from app.orm_decl import Edition, Issue, Magazine, Publisher
from app.route_helpers import new_session
from app.types import HttpResponseCode


def publisher_index() -> ResponseType:
    """
    Every publisher, ordered by name.

    Returns:
        ResponseType: {total, publishers: [{id, name, fullname, editions,
        first_year, last_year, magazines: [{id, name, issues}]}]};
        first_year and last_year are null for a publisher without editions.
    """
    session = new_session()
    try:
        counts = {r[0]: (r[1], r[2], r[3]) for r in session.query(
            Edition.publisher_id, func.count(Edition.id),
            func.min(Edition.pubyear), func.max(Edition.pubyear)
        ).filter(Edition.publisher_id.isnot(None))
            .group_by(Edition.publisher_id).all()}
        issues = dict(session.query(Issue.magazine_id, func.count(Issue.id))
                      .group_by(Issue.magazine_id).all())
        magazines: Dict[int, List[Dict[str, Any]]] = {}
        for m in session.query(Magazine.id, Magazine.name,
                               Magazine.publisher_id) \
                .filter(Magazine.publisher_id.isnot(None)) \
                .order_by(Magazine.name).all():
            magazines.setdefault(m.publisher_id, []).append(
                {'id': m.id, 'name': m.name, 'issues': issues.get(m.id, 0)})
        rows = []
        for p in session.query(Publisher.id, Publisher.name,
                               Publisher.fullname) \
                .order_by(Publisher.name, Publisher.id).all():
            n, first, last = counts.get(p.id, (0, None, None))
            rows.append({'id': p.id, 'name': p.name, 'fullname': p.fullname,
                         'editions': n, 'first_year': first,
                         'last_year': last,
                         'magazines': magazines.get(p.id, [])})
    except SQLAlchemyError as exp:
        app.logger.error(f'publisher_index: {exp}')
        return ResponseType('publisher_index: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    finally:
        session.close()
    return ResponseType({'total': len(rows), 'publishers': rows},
                        HttpResponseCode.OK.value)
