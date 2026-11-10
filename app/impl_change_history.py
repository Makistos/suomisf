"""Change history with derived new values.

The log stores only each changed field's old value. The value a change
set (its new value) is derived when the history is read:

* the new value of a change is the old value of the next later change to
  the same field of the same object, and
* for the newest change of a field it is the field's current value.

Fields have been renamed over the years (e.g. "Sivumäärä" is now
"Sivuja"), so old names are mapped to the current ones first. Single tag
additions and removals are logged as events ("Lisätty: x",
"Poistettu: x") rather than as the old tag list; going back in time they
are undone from the list.

Only works and their editions are handled here.
"""
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.impl_contributors import get_contributors_string
from app.impl_links import links_old_value
from app.types import ContributorTarget

# Old field names -> the name the current code logs, per table.
FIELD_ALIASES: Dict[str, Dict[str, str]] = {
    'Teos': {
        'Alkup.nimi': 'Alkukielinen nimi',
        'Otsikko': 'Nimeke',
    },
    'Painos': {
        'Sivumäärä': 'Sivuja',
        'isbn': 'ISBN',
        'Laitos': 'Laitosnro',
        'Julk.vuosi': 'Kustannusvuosi',
        'Julkaisuvuosi': 'Kustannusvuosi',
        'Julkaisija': 'Kustantaja',
        'Julk.sarja': 'Kustantajan sarja',
        'Julk.sarjan nro': 'Kustantajan sarjan numero',
    },
}

# Fields logged as a comma-separated list of names.
COMMA_LIST_FIELDS = {'Asiasanat', 'Genret'}

# The long description is logged cut to this length.
DESCRIPTION_LOG_LENGTH = 200

EVENT_PREFIXES = ('Lisätty: ', 'Poistettu: ')


def canonical_field(table: str, field: Optional[str]) -> str:
    """The current name of a logged field."""
    field = field or ''
    return FIELD_ALIASES.get(table, {}).get(field, field)


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _name(obj: Any) -> str:
    return obj.name if obj is not None else ''


def _names(objs: Any) -> str:
    return ','.join(sorted(o.name for o in objs))


def _tristate(value: Any, labels: Dict[int, str]) -> Optional[str]:
    return labels.get(value) if value is not None else None


# Current value of each field, formatted as the code logs the old value.
WORK_FIELDS: Dict[str, Callable[[Any], Optional[str]]] = {
    'Nimeke': lambda w: w.title,
    'Alaotsikko': lambda w: w.subtitle,
    'Alkukielinen nimi': lambda w: w.orig_title,
    'Julkaisuvuosi': lambda w: _text(w.pubyear),
    'Kirjasarja': lambda w: _name(w.bookseries),
    'Kirjasarjan numero': lambda w: w.bookseriesnum,
    'Kirjasarjan järjestys': lambda w: _text(w.bookseriesorder),
    'Muuta': lambda w: w.misc,
    'Kuvaus': lambda w: (w.description or '')[:DESCRIPTION_LOG_LENGTH],
    'Kuvauksen lähde': lambda w: w.descr_attr,
    'Lähde': lambda w: w.imported_string,
    'Tyyppi': lambda w: _name(w.work_type),
    'Kieli': lambda w: w.language_name.name if w.language_name else None,
    'Asiasanat': lambda w: _names(w.tags),
    'Genret': lambda w: _names(w.genres),
    'Linkit': lambda w: links_old_value(w.links),
    'Tekijät': lambda w: get_contributors_string(
        w.contributions, ContributorTarget.WORK),
}

EDITION_FIELDS: Dict[str, Callable[[Any], Optional[str]]] = {
    'Nimeke': lambda e: e.title,
    'Alaotsikko': lambda e: e.subtitle,
    'Kustannusvuosi': lambda e: _text(e.pubyear),
    'Painosnro': lambda e: _text(e.editionnum),
    'Laitosnro': lambda e: _text(e.version),
    'ISBN': lambda e: e.isbn,
    'Sivuja': lambda e: _text(e.pages),
    'Sidonta': lambda e: _name(e.binding),
    'Formaatti': lambda e: _name(e.format),
    'Koko': lambda e: _text(e.size),
    'Painopaikka': lambda e: e.printedin,
    'Kustantaja': lambda e: _name(e.publisher),
    'Kustantajan sarja': lambda e: _name(e.pubseries),
    'Kustantajan sarjan numero': lambda e: _text(e.pubseriesnum),
    'Kansipaperi': lambda e: _tristate(
        e.dustcover, {1: 'Ei tietoa', 2: 'Kyllä', 3: 'Ei'}),
    'Ylivetokansi': lambda e: _tristate(
        e.coverimage, {1: 'Ei tietoa', 2: 'Ei', 3: 'Kyllä'}),
    'Muuta': lambda e: e.misc,
    'Lähde': lambda e: e.imported_string,
    'Tarkastettu': lambda e: 'Kyllä' if e.verified else 'Ei',
    'Tekijät': lambda e: get_contributors_string(
        e.contributions, ContributorTarget.EDITION),
}


def current_value(table: str, obj: Any, field: str) -> Tuple[bool, Any]:
    """(known, value): the field's current value, if it can be read."""
    getters = WORK_FIELDS if table == 'Teos' else (
        EDITION_FIELDS if table == 'Painos' else {})
    getter = getters.get(field)
    if obj is None or getter is None:
        return False, None
    return True, getter(obj)


def _split(value: Optional[str]) -> List[str]:
    return [x.strip() for x in (value or '').split(',') if x.strip()]


def _undo_event(state: Optional[str], event: str) -> Optional[str]:
    """The comma list before a "Lisätty: x" / "Poistettu: x" event."""
    if state is None:
        return None
    names = _split(state)
    prefix, name = event.split(': ', 1)
    if prefix == 'Lisätty':
        names = [x for x in names if x != name]
    elif name not in names:
        names.append(name)
    return ','.join(sorted(names))


def is_event(field: str, old_value: Optional[str]) -> bool:
    """True for a single tag addition or removal."""
    return (field in COMMA_LIST_FIELDS and old_value is not None
            and old_value.startswith(EVENT_PREFIXES))


def add_new_values(rows: List[Dict[str, Any]],
                   objects: Dict[Tuple[str, int], Any]) -> None:
    """Add "field", "new_value" and "new_value_source" to dumped log rows.

    rows: LogSchema dumps (any order). objects: the current object of each
    (table_name, table_id), missing if it no longer exists.
    new_value_source is "next" (the next change's old value), "current"
    (the current value) or None (no new value: not an update, a tag event,
    or a field whose current value can't be read).
    """
    for row in rows:
        row['field'] = canonical_field(row['table_name'], row['field_name'])
        row['new_value'] = None
        row['new_value_source'] = None

    chains: Dict[Tuple[str, int, str], List[Dict[str, Any]]] = {}
    for row in rows:
        if row['action'] != 'Päivitys':
            continue
        key = (row['table_name'], row['table_id'], row['field'])
        chains.setdefault(key, []).append(row)

    for (table, table_id, field), chain in chains.items():
        chain.sort(key=lambda r: (r['date'], r['id']), reverse=True)
        known, state = current_value(table, objects.get((table, table_id)),
                                     field)
        source: Optional[str] = 'current' if known else None
        for row in chain:
            old = row['old_value']
            if is_event(field, old):
                # The list before this event, for the change before it.
                state = _undo_event(state, old) if known else None
                continue
            if known:
                row['new_value'] = state
                row['new_value_source'] = source
            state, known, source = old, True, 'next'
