"""
The light tag list (GET /api/tagindex) for the new tag list page.

One group at a time, optionally one initial letter or a search, with each
tag's count and no works: the current list loads every tag with all its
works only to count them.
"""

from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.impl import ResponseType
from app.route_helpers import new_session
from app.types import HttpResponseCode

AIHE = 1
ALAGENRE = 2
# Tab order on the page: the most important group first (owner,
# 2026-11-23), then as on the work page.
TYPE_ORDER = (2, 3, 1, 4, 5, 6, 7)
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ'
OTHER = '0'  # any name that doesn't start with A-Ö, e.g. "1800-luku"
SORTS = {'name': 'name, id', 'count': 'count DESC, name, id'}

# Counted as on the current list: works, stories and magazine articles.
TAGS_SQL = """
WITH counted AS (
    SELECT t.id, t.name, coalesce(t.type_id, :aihe) AS type_id,
        (SELECT count(*) FROM worktag x WHERE x.tag_id = t.id)
        + (SELECT count(*) FROM storytag x WHERE x.tag_id = t.id)
        + (SELECT count(*) FROM articletag x WHERE x.tag_id = t.id)
        AS count
    FROM tag t
    WHERE (:q = '' OR t.name ILIKE '%' || :q || '%')
)
SELECT id, name, type_id, count FROM counted
WHERE (:unused OR count > 0)
"""


class BadParameter(ValueError):
    """A parameter that can't be used; reported as 400."""


def _initial_matches(name: str, letter: str) -> bool:
    first = name[:1].upper()
    if letter == OTHER:
        return first not in LETTERS
    return first == letter


def tag_index(params: Dict[str, str]) -> ResponseType:
    """
    One group of the tag list.

    Args:
        params: type (tag type id, default Alagenre; a tag without a type
            is Aihe); letter (initial A-Ö, or 0 for any other); q (part of
            the name; overrides the letter); sort (name or count); unused
            (1 to include tags with nothing linked, for admins).

    Returns:
        ResponseType: {types: [{id, name, count}] (counts follow q and
        unused, not the letter), tags: [{id, name, count}]}; 400 for a
        parameter that can't be used.
    """
    try:
        type_param = (params.get('type') or str(ALAGENRE)).strip()
        if not type_param.isdigit() or int(type_param) not in TYPE_ORDER:
            raise BadParameter('type')
        type_id = int(type_param)
        letter = (params.get('letter') or '').strip().upper()
        if letter and letter != OTHER and \
                (len(letter) != 1 or letter not in LETTERS):
            raise BadParameter('letter')
        sort = (params.get('sort') or 'name').strip()
        if sort not in SORTS:
            raise BadParameter('sort')
        q = (params.get('q') or '').strip()
        unused = params.get('unused') == '1'
        session = new_session()
        try:
            rows = session.execute(
                text(TAGS_SQL + ' ORDER BY ' + SORTS[sort]),
                {'aihe': AIHE, 'q': q, 'unused': unused}).all()
            names = dict(session.execute(
                text('SELECT id, name FROM tagtype')).all())
        finally:
            session.close()
    except BadParameter as exp:
        app.logger.info(f'tag_index: bad parameter {exp}.')
        return ResponseType(f'Virheellinen parametri: {exp}',
                            HttpResponseCode.BAD_REQUEST.value)
    except SQLAlchemyError as exp:
        app.logger.error(f'tag_index: {exp}')
        return ResponseType('tag_index: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    counts: Dict[int, int] = {t: 0 for t in TYPE_ORDER}
    tags: List[Dict[str, Any]] = []
    for row in rows:
        counts[row.type_id] = counts.get(row.type_id, 0) + 1
        if row.type_id != type_id:
            continue
        if letter and not q and not _initial_matches(row.name, letter):
            continue
        tags.append({'id': row.id, 'name': row.name, 'count': row.count})
    return ResponseType({
        'types': [{'id': t, 'name': names.get(t, ''), 'count': counts[t]}
                  for t in TYPE_ORDER],
        'tags': tags,
    }, HttpResponseCode.OK.value)
