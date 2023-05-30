from typing import Any, Dict, Union, List
from app.orm_decl import (Part, Contributor)


def _updatePartContributors(session: Any, part_id: int, contributors: Any) -> None:
    # Remove existing rows from table.
    session.query(Contributor).filter(
        Contributor.part_id == part_id).delete()
    for contrib in contributors:
        new_contributor = Contributor(
            part_id=part_id,
            person_id=contrib['person']['id'],
            role_id=contrib['role']['id'],
            description=contrib['description'])
        # if 'real_person' in contrib:
        #     new_contributor.real_person.id = contrib['real_person'].id,
        session.add(new_contributor)


def contributorsHaveChanged(old_values: List[Any], new_values: List[Any]) -> bool:
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.person_id != new_values[idx]['person']['id'] or \
                old_value.role_id != new_values[idx]['role']['id'] or \
                old_value.description != new_values[idx]['description']:
            return True
    return False


def updateShortContributors(session: Any, short_id: int, contributors: Any) -> None:
    parts = session.query(Part).filter(Part.shortstory_id == short_id).all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)


def updateEditionContributors(session: Any, edition_id: int, contributors: Any) -> None:
    parts = session.query(Part)\
        .filter(Part.edition_id == edition_id)\
        .filter(Part.shortstory_id == None)\
        .all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)


def updateWorkContributors(session: Any, work_id: int, contributors: Any) -> None:
    parts = session.query(Part)\
        .filter(Part.work_id == work_id)\
        .filter(Part.shortstory_id == None)\
        .all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)
