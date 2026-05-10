"""Fetch/parse kirjasampo.fi tags and import them into works."""

from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.exc import SQLAlchemyError

from app.impl import ResponseType
from app.orm_decl import Tag, TagImportOmit, TagImportReplace, Work, WorkTag
from app.route_helpers import new_session
from app.types import HttpResponseCode
from app import app

ALLOWED_HOST = "www.kirjasampo.fi"
_HEADERS = {
    "User-Agent": (
        "SF-Bibliografia/1.0 (yp@sf-bibliografia.fi) Python requests"
    )
}

_VALID_ACTIONS = {"add", "replace", "omit"}


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


def _find_or_create_tag(session: Any, name: str) -> Tag:
    """Return existing tag by name (case-insensitive) or create one."""
    tag = (
        session.query(Tag)
        .filter(Tag.name.ilike(name))
        .first()
    )
    if not tag:
        tag = Tag()
        tag.name = name
        tag.type_id = 1
        session.add(tag)
        session.flush()  # get tag.id without committing
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

        for item in items:
            name: str = item.get("name", "").strip().lower()
            raw_id: Any = item.get("id")
            raw_action: Any = item.get("action")

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

                tag = _find_or_create_tag(session, name)

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

        session.commit()
        return ResponseType(results, HttpResponseCode.OK)

    except SQLAlchemyError as exc:
        app.logger.error(f"work_import_tags: {exc}")
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
