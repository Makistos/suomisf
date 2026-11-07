"""Fetch/parse kirjasampo.fi tags and import them into works."""

import datetime
import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.impl import ResponseType
from app.impl_logs import log_changes
from app.orm_decl import (
    Tag, TagImportOmit, TagImportReplace, TagType, Work, WorkTag)
from app.route_helpers import new_session
from app.types import HttpResponseCode
from app import app
from app.names import clean_name

ALLOWED_HOST = "www.kirjasampo.fi"
_HEADERS = {
    "User-Agent": (
        "SF-Bibliografia/1.0 (yp@sf-bibliografia.fi) Python requests"
    )
}

_VALID_ACTIONS = {"add", "replace", "omit"}

# Type given to new tags when the import item doesn't name one.
DEFAULT_TAG_TYPE_ID = 1  # Aihe

# Kirjasampo sections that aren't subject tags: on a work page, and the
# publication details of an edition page (whose tags are on its work).
SKIPPED_SECTIONS = {
    "Tekijä", "Päähenkilöt", "Alkukieli", "julkaisut", "Osana julkaisua",
    "Kirjastonhoitaja suosittelee", "Palkinto", "Lisätietoa verkossa",
    "Sisältää julkaisut", "Teoksen kuvailutiedot", "Ilmestymisaika",
    "Kustantaja", "Kieli", "Kääntäjä", "Alkuteos",
}
# Sections whose items collapse into one fixed tag.
SECTION_OVERRIDES = {"Elokuvat": "elokuva"}


def _is_valid_kirjasampo_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in ("http", "https")
            and parsed.netloc == ALLOWED_HOST
        )
    except Exception:
        return False


def kirjasampo_tags(url: str) -> ResponseType:
    """Fetch all tags from a kirjasampo.fi work page.

    Tags are organised in named sections such as
    "Kirjallisuudenlaji", "Aiheet ja teemat", etc. Each section
    that contains hyperlinked tag items is included in the result.

    Parameters
    ----------
    url:
        Full URL of the kirjasampo.fi work page.

    Returns
    -------
    ResponseType
        On success: response value is a dict mapping section label
        (str) to a list of tag strings.
        On error: response with an appropriate HTTP error status.
    """
    if not url:
        return ResponseType(
            "URL puuttuu.",
            HttpResponseCode.BAD_REQUEST,
        )

    if not _is_valid_kirjasampo_url(url):
        return ResponseType(
            "Virheellinen URL. Sallittu vain kirjasampo.fi-osoitteet.",
            HttpResponseCode.BAD_REQUEST,
        )

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
    except requests.RequestException as exc:
        return ResponseType(
            f"Sivun haku epäonnistui: {exc}",
            HttpResponseCode.INTERNAL_SERVER_ERROR,
        )

    if resp.status_code != 200:
        return ResponseType(
            f"Kirjasampo palautti virhekoodin {resp.status_code}.",
            HttpResponseCode.INTERNAL_SERVER_ERROR,
        )

    soup = BeautifulSoup(resp.content, "html.parser")
    result: dict[str, list[str]] = {}

    for section in soup.select("div.kulsa-field"):
        heading = section.select_one("h2.kulsa-field-label")
        if not heading:
            continue
        label = heading.get_text(strip=True)
        items = [
            a.get_text(strip=True).lower()
            for a in section.select("div.kulsa-field-item a")
        ]
        if items:
            result[label] = items

    if not result:
        return ResponseType(
            "Sivulta ei löytynyt tunnisteita.",
            HttpResponseCode.NOT_FOUND,
        )

    return ResponseType(result, HttpResponseCode.OK)


# ---------------------------------------------------------------------------
# Tag import


def _resolve_action(
    session: Any,
    name: str,
    action: str | None,
    tag_id: int | None,
) -> tuple[str, int | None]:
    """Return (effective_action, effective_tag_id) for one import item.

    When action is None the stored mappings are consulted; unknown names
    default to "add".
    """
    if action is not None:
        return action, tag_id

    omit = session.query(TagImportOmit).get(name)
    if omit:
        return "omit", None

    replace = session.query(TagImportReplace).get(name)
    if replace:
        return "replace", replace.tag_id

    return "add", None


def _find_tag(session: Any, name: str) -> Tag | None:
    """Return the tag with exactly this name, ignoring case, or None."""
    return (
        session.query(Tag)
        .filter(func.lower(Tag.name) == clean_name(name).lower())
        .order_by(Tag.id)
        .first()
    )


def _find_or_create_tag(
    session: Any, name: str, type_id: int | None = None
) -> Tag:
    """Return existing tag by name (case-insensitive) or create one.

    type_id is the type of a new tag (default Aihe); an existing tag
    keeps its type.
    """
    tag = _find_tag(session, name)
    if not tag:
        tag = Tag()
        tag.name = name
        tag.type_id = type_id or DEFAULT_TAG_TYPE_ID
        session.add(tag)
        session.flush()  # get tag.id without committing
        log_changes(session, obj=tag, action='Uusi')
    return tag


def _worktag_exists(session: Any, work_id: int, tag_id: int) -> bool:
    return (
        session.query(WorkTag)
        .filter(WorkTag.work_id == work_id, WorkTag.tag_id == tag_id)
        .first()
    ) is not None


def work_import_tags(
    work_id: int, items: list[dict[str, Any]]
) -> ResponseType:
    """Add tags from an import list to a work.

    Each item in *items* is a dict with:

    name (str):
        Tag name as it appears in the external source.
    id (int | None):
        ID of an existing local tag. Required for action "replace".
    action (str | None):
        One of "add", "replace", "omit", or omitted/None to auto-resolve
        from stored mappings (defaulting to "add" for unknown names).
    type_id (int | None):
        Type of the tag if "add" creates one (default Aihe). An
        existing tag keeps its type.

    Actions
    -------
    add
        Look up or create a tag by *name*, add it to the work.
        Clears any stored replace/omit mapping for *name*.
    replace
        Use the existing tag identified by *id* instead of *name*.
        Stores the mapping persistently so future imports without an
        explicit action will apply it automatically.
        Clears any stored omit mapping for *name*.
    omit
        Do not add a tag for *name* to the work.
        Stores the omit decision persistently.
        Clears any stored replace mapping for *name*.
        A previously omitted name can be un-omitted by sending it with
        action "add" or "replace".

    Returns
    -------
    ResponseType
        On success: list of per-item result dicts.
        On error: error ResponseType.
    """
    session = new_session()

    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        if not work:
            return ResponseType(
                f"Teosta ei löydy: id={work_id}",
                HttpResponseCode.BAD_REQUEST,
            )

        results = []
        old_tags = ','.join(sorted(t.name for t in work.tags))

        for item in items:
            name: str = item.get("name", "").strip().lower()
            raw_id: Any = item.get("id")
            raw_action: Any = item.get("action")
            raw_type: Any = item.get("type_id")

            if not name:
                results.append({"name": "", "status": "error",
                                 "error": "name is required"})
                continue

            tag_id: int | None = (
                int(raw_id) if raw_id is not None and raw_id != "" else None
            )
            action: str | None = (
                raw_action.strip().lower()
                if isinstance(raw_action, str) and raw_action.strip()
                else None
            )

            if action is not None and action not in _VALID_ACTIONS:
                results.append({
                    "name": name, "status": "error",
                    "error": f"invalid action '{action}'"
                })
                continue

            type_id: int | None = None
            if raw_type is not None and raw_type != "":
                try:
                    type_id = int(raw_type)
                except (TypeError, ValueError):
                    type_id = -1
                if session.query(TagType).get(type_id) is None:
                    results.append({
                        "name": name, "status": "error",
                        "error": f"tag type id={raw_type} not found"
                    })
                    continue

            effective_action, effective_id = _resolve_action(
                session, name, action, tag_id
            )

            if effective_action == "add":
                # Clear stored mappings
                omit_rec = session.query(TagImportOmit).get(name)
                if omit_rec:
                    session.delete(omit_rec)
                replace_rec = session.query(TagImportReplace).get(name)
                if replace_rec:
                    session.delete(replace_rec)

                tag = _find_or_create_tag(session, name, type_id)

                if _worktag_exists(session, work_id, tag.id):
                    results.append({
                        "name": name,
                        "effective_action": "add",
                        "tag_id": tag.id,
                        "status": "already_present",
                    })
                else:
                    wt = WorkTag()
                    wt.work_id = work_id
                    wt.tag_id = tag.id
                    session.add(wt)
                    results.append({
                        "name": name,
                        "effective_action": "add",
                        "tag_id": tag.id,
                        "status": "added",
                    })

            elif effective_action == "replace":
                if not effective_id:
                    results.append({
                        "name": name, "status": "error",
                        "error": "replace requires a non-empty id"
                    })
                    continue

                target = session.query(Tag).get(effective_id)
                if not target:
                    results.append({
                        "name": name, "status": "error",
                        "error": (
                            f"tag id={effective_id} not found"
                        ),
                    })
                    continue

                # Clear omit; upsert replace
                omit_rec = session.query(TagImportOmit).get(name)
                if omit_rec:
                    session.delete(omit_rec)
                replace_rec = session.query(TagImportReplace).get(name)
                if replace_rec:
                    replace_rec.tag_id = effective_id
                else:
                    replace_rec = TagImportReplace()
                    replace_rec.name = name
                    replace_rec.tag_id = effective_id
                    session.add(replace_rec)

                if _worktag_exists(session, work_id, effective_id):
                    results.append({
                        "name": name,
                        "effective_action": "replace",
                        "tag_id": effective_id,
                        "status": "already_present",
                    })
                else:
                    wt = WorkTag()
                    wt.work_id = work_id
                    wt.tag_id = effective_id
                    session.add(wt)
                    results.append({
                        "name": name,
                        "effective_action": "replace",
                        "tag_id": effective_id,
                        "status": "added",
                    })

            else:  # omit
                # Clear replace; upsert omit
                replace_rec = session.query(TagImportReplace).get(name)
                if replace_rec:
                    session.delete(replace_rec)
                omit_rec = session.query(TagImportOmit).get(name)
                if not omit_rec:
                    omit_rec = TagImportOmit()
                    omit_rec.name = name
                    session.add(omit_rec)

                results.append({
                    "name": name,
                    "effective_action": "omit",
                    "tag_id": None,
                    "status": "omitted",
                })

        if any(r.get("status") == "added" for r in results):
            log_changes(session, obj=work, name_field='title',
                        old_values={'Asiasanat': old_tags})
        work.kirjasampo_imported = datetime.datetime.now(
            datetime.timezone.utc)
        session.commit()
        return ResponseType(results, HttpResponseCode.OK)

    except SQLAlchemyError as exc:
        app.logger.error(f"work_import_tags: {exc}")
        return ResponseType(
            "Tietokantavirhe.",
            HttpResponseCode.INTERNAL_SERVER_ERROR,
        )


def _strip_qualifiers(name: str) -> str:
    """Drop parenthesised qualifiers: "avaruus (luokka)" -> "avaruus"."""
    return clean_name(re.sub(r"\s*\([^)]*\)", " ", name))


def import_name(name: str) -> str:
    """The name a Kirjasampo tag is matched and its mappings stored by."""
    return _strip_qualifiers(name).lower()


def _preview_groups(
    sections: dict[str, list[str]]
) -> list[tuple[str, list[tuple[str, str]]]]:
    """Apply the import rules to scraped sections.

    Returns (section, [(name, raw_name), ...]) in page order, without
    the skipped sections and with empty names dropped.
    """
    groups = []
    for section, raw_names in sections.items():
        if section in SKIPPED_SECTIONS:
            continue
        if section in SECTION_OVERRIDES:
            override = SECTION_OVERRIDES[section]
            items = [(override, override)] if raw_names else []
        else:
            items = []
            seen: set[str] = set()
            for raw in raw_names:
                name = import_name(raw)
                if name and name not in seen:
                    seen.add(name)
                    items.append((name, raw))
        if items:
            groups.append((section, items))
    return groups


def _tag_brief(tag: Tag) -> dict[str, Any]:
    return {
        "id": tag.id,
        "name": tag.name,
        "type": (
            {"id": tag.type.id, "name": tag.type.name}
            if tag.type else None
        ),
    }


def work_import_preview(work_id: int) -> ResponseType:
    """Tags a Kirjasampo import would bring to a work, for review.

    Fetches the work's Kirjasampo page and returns its tag sections in
    page order, as a list of {section, items}. Each item has:

    name: the cleaned name, used for matching and stored mappings
    raw_name: the name as on the page
    mapping: {"action": "omit"}, {"action": "replace", "tag": {...}}
        or None
    match: the existing tag with the same name, or None if importing
        would create one
    on_work: whether the work already has the tag importing would add

    A page without tags gives an empty list.
    """
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        if not work:
            return ResponseType(
                f"Teosta ei löydy: id={work_id}",
                HttpResponseCode.BAD_REQUEST,
            )
        link = next(
            (wl.link for wl in work.links if "kirjasampo.fi" in wl.link),
            None,
        )
        if not link:
            return ResponseType(
                "Teoksella ei ole Kirjasampo-linkkiä.",
                HttpResponseCode.BAD_REQUEST,
            )

        fetched = kirjasampo_tags(link)
        if fetched.status == HttpResponseCode.NOT_FOUND:
            # The page exists but has no tags.
            return ResponseType([], HttpResponseCode.OK)
        if fetched.status != HttpResponseCode.OK:
            return fetched

        work_tag_ids = {t.id for t in work.tags}
        groups = []
        for section, items in _preview_groups(fetched.response):
            rows = []
            for name, raw in items:
                mapping: dict[str, Any] | None = None
                target: Tag | None = None
                if session.query(TagImportOmit).get(name):
                    mapping = {"action": "omit"}
                else:
                    replace = session.query(TagImportReplace).get(name)
                    if replace and replace.tag:
                        target = replace.tag
                        mapping = {
                            "action": "replace",
                            "tag": _tag_brief(replace.tag),
                        }
                match = _find_tag(session, name)
                adds = target or match
                rows.append({
                    "name": name,
                    "raw_name": raw,
                    "mapping": mapping,
                    "match": _tag_brief(match) if match else None,
                    "on_work": adds is not None and adds.id in work_tag_ids,
                })
            groups.append({"section": section, "items": rows})
        return ResponseType(groups, HttpResponseCode.OK)

    except SQLAlchemyError as exc:
        app.logger.error(f"work_import_preview: {exc}")
        return ResponseType(
            "Tietokantavirhe.",
            HttpResponseCode.INTERNAL_SERVER_ERROR,
        )


def get_import_mappings() -> ResponseType:
    """Return all stored tag import replace and omit mappings.

    Returns
    -------
    ResponseType
        On success: dict with keys "replace" (list of
        {name, tag_id, tag_name}) and "omit" (list of name strings).
    """
    session = new_session()
    try:
        replaces = session.query(TagImportReplace).all()
        omits = session.query(TagImportOmit).all()
        return ResponseType(
            {
                "replace": [
                    {
                        "name": r.name,
                        "tag_id": r.tag_id,
                        "tag_name": r.tag.name if r.tag else None,
                    }
                    for r in replaces
                ],
                "omit": [o.name for o in omits],
            },
            HttpResponseCode.OK,
        )
    except SQLAlchemyError as exc:
        app.logger.error(f"get_import_mappings: {exc}")
        return ResponseType(
            "Tietokantavirhe.",
            HttpResponseCode.INTERNAL_SERVER_ERROR,
        )
