""" Link related functions. """

from typing import Any, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.impl import ResponseType
from app.impl_logs import log_changes
from app.names import clean_name
from app.orm_decl import Work, WorkLink
from app.route_helpers import new_session
from app.types import HttpResponseCode


def links_old_value(links: List[Any]) -> str:
    """
    The change log's old value for a list of links: each address, followed
    by its description in parentheses if it has one, separated by commas.
    """
    return ', '.join(f'{x.link} ({x.description})' if x.description
                     else str(x.link) for x in links)


def links_have_changed(old_values: List[Any],
                       new_values: List[Any]) -> bool:
    """
    Check if the old and new values of links have changed.

    Args:
        old_values (List[Any]): The list of old values.
        new_values (List[Any]): The list of new values.

    Returns:
        bool: True if the values have changed, False otherwise.
    """
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.description != new_values[idx]['description'] or \
         old_value.link != new_values[idx]['link']:
            return True
    return False


def _source_filter(query: Any, source: Optional[str]) -> Any:
    """Filter WorkLinks by source; None or '' matches links without one."""
    if not source:
        return query.filter(or_(WorkLink.description.is_(None),
                                WorkLink.description == ''))
    return query.filter(WorkLink.description == source)


def worklink_sources() -> ResponseType:
    """
    List the distinct sources (descriptions) of work links.

    Returns:
        ResponseType: List of {"source", "count", "works"}, most used
                      first. Links without a source have source null.
    """
    session = new_session()
    try:
        source = func.nullif(WorkLink.description, '')
        rows = session.query(source,
                             func.count(WorkLink.id),
                             func.count(func.distinct(WorkLink.work_id)))\
            .group_by(source)\
            .order_by(func.count(WorkLink.id).desc(), source)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'worklink_sources: {exp}')
        return ResponseType('worklink_sources: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(
        [{'source': s, 'count': c, 'works': w} for s, c, w in rows],
        HttpResponseCode.OK.value)


def worklink_source_links(source: Optional[str]) -> ResponseType:
    """
    List the work links that have the given source.

    Args:
        source (Optional[str]): Source; None or '' for links without one.

    Returns:
        ResponseType: List of {"id", "link", "work_id", "work_title"}
                      ordered by work title.
    """
    session = new_session()
    try:
        rows = _source_filter(
            session.query(WorkLink.id, WorkLink.link, Work.id, Work.title)
            .join(Work, Work.id == WorkLink.work_id), source)\
            .order_by(Work.title, WorkLink.id)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'worklink_source_links: {exp}')
        return ResponseType('worklink_source_links: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(
        [{'id': i, 'link': link, 'work_id': w, 'work_title': t}
         for i, link, w, t in rows],
        HttpResponseCode.OK.value)


def worklink_sources_merge(sources: List[Optional[str]],
                           target: str) -> ResponseType:
    """
    Give every work link whose source is one of *sources* the source
    *target*: renames a source (one source) or combines several into one.
    The change is logged on each affected work.

    Args:
        sources (List[Optional[str]]): Sources to replace; None or '' for
                                       links without a source.
        target (str): The new source, trimmed; must not be empty.

    Returns:
        ResponseType: {"updated": number of links changed}.
    """
    target = clean_name(target or '') or ''
    if not target:
        return ResponseType('Uusi lähde puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)
    if not sources:
        return ResponseType('Yhdistettävät lähteet puuttuvat.',
                            HttpResponseCode.BAD_REQUEST.value)
    session = new_session()
    try:
        updated = 0
        for source in sources:
            if source == target:
                continue
            links = _source_filter(session.query(WorkLink), source).all()
            for link in links:
                work = session.query(Work).get(link.work_id)
                if work:
                    log_changes(session, obj=work, name_field='title',
                                old_values={'Linkit': f'{link.link} '
                                            f'({source or "-"})'})
                link.description = target
                updated += 1
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'worklink_sources_merge: {exp}')
        return ResponseType('worklink_sources_merge: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType({'updated': updated}, HttpResponseCode.OK.value)


def worklink_source_delete(source: Optional[str]) -> ResponseType:
    """
    Delete every work link that has the given source. The removed link is
    logged on each affected work.

    Args:
        source (Optional[str]): Source; None or '' for links without one.

    Returns:
        ResponseType: {"deleted": number of links deleted}.
    """
    session = new_session()
    try:
        links = _source_filter(session.query(WorkLink), source).all()
        for link in links:
            work = session.query(Work).get(link.work_id)
            if work:
                log_changes(session, obj=work, name_field='title',
                            old_values={'Linkit': f'-{link.link} '
                                        f'({source or "-"})'})
            session.delete(link)
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'worklink_source_delete: {exp}')
        return ResponseType('worklink_source_delete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType({'deleted': len(links)}, HttpResponseCode.OK.value)
