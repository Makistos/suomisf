"""Similar works: the lists computed by scripts/work_similarity.py.

See docs/work-similarity-plan.md. The page only reads; nothing is
computed in the request.
"""
from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.impl import ResponseType
from app.route_helpers import new_session
from app.thumbnails import thumb_src
from app.types import HttpResponseCode

DEFAULT_LIMIT = 8
MAX_LIMIT = 40

DESCRIPTION = 'description'
# Tag types (tagtype.id) and the name shown for each reason.
TYPE_NAMES = {1: 'Aihe', 2: 'Alagenre', 3: 'Tyyli', 4: 'Toimija',
              5: 'Paikka', 6: 'Aika', DESCRIPTION: 'Kuvaus'}
# Shown only when no stronger reason exists.
WEAK_TYPES = {4, 5, 6}   # Toimija, Paikka, Aika


def _reasons(stored: List[Dict[str, Any]],
             tags: Dict[int, str]) -> List[Dict[str, Any]]:
    """Stored reasons (biggest contribution first) with tag names; era,
    actor and place reasons only if nothing stronger exists. Tags deleted
    since the run are left out, and a tag reason left with none."""
    named = []
    for r in stored:
        names = [{'id': t, 'name': tags[t]} for t in r['tags'] if t in tags]
        if names or r['type'] == DESCRIPTION:
            named.append({'type': r['type'],
                          'type_name': TYPE_NAMES.get(r['type'],
                                                      str(r['type'])),
                          'tags': names})
    strong = [r for r in named if r['type'] not in WEAK_TYPES]
    return strong or named


def get_similar_works(work_id: int, limit: int = DEFAULT_LIMIT
                      ) -> ResponseType:
    """
    The works most similar to a work, best first.

    Each item: id, title, author_str, pubyear (original year), image (the
    first cover of the earliest edition that has one, with thumb_src, or
    None) and reasons ({type, type_name, tags: [{id, name}]}, strongest
    first; type is a tag type id or "description"). A work with no
    computed list gives an empty list.
    """
    limit = max(1, min(limit, MAX_LIMIT))
    session = new_session()
    try:
        rows = session.execute(text(
            'SELECT w.id, w.title, w.author_str, w.pubyear, s.reasons '
            'FROM work_similarity s '
            'JOIN work w ON w.id = s.target_work_id '
            'WHERE s.source_work_id = :id ORDER BY s.rank LIMIT :limit'),
            {'id': work_id, 'limit': limit}).all()
        ids = [r.id for r in rows]
        tag_ids = {t for r in rows for reason in r.reasons
                   for t in reason['tags']}
        tags = {t.id: t.name for t in session.execute(text(
            'SELECT id, name FROM tag WHERE id = ANY(:ids)'),
            {'ids': list(tag_ids)})} if tag_ids else {}
        covers = {c.work_id: c.image_src for c in session.execute(text(
            'SELECT DISTINCT ON (e.work_id) e.work_id, i.image_src '
            'FROM edition e JOIN editionimage i ON i.edition_id = e.id '
            'WHERE e.work_id = ANY(:ids) '
            'ORDER BY e.work_id, e.pubyear, e.editionnum NULLS LAST, '
            'e.version NULLS FIRST, e.id, i.id'),
            {'ids': ids})} if ids else {}
    except SQLAlchemyError as exp:
        app.logger.error(f'get_similar_works: {exp}')
        return ResponseType('get_similar_works: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    items = []
    for r in rows:
        src = covers.get(r.id)
        items.append({
            'id': r.id,
            'title': r.title,
            'author_str': r.author_str,
            'pubyear': r.pubyear,
            'image': ({'image_src': src, 'thumb_src': thumb_src(src)}
                      if src else None),
            'reasons': _reasons(r.reasons, tags),
        })
    return ResponseType(items, HttpResponseCode.OK.value)
