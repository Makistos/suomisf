from typing import Any
from app.orm_decl import (Part, Contributor)


def _updatePartContributors(session: Any, part_id: int, contributors: Any) -> None:
    existing = session.query(Contributor).filter(
        Contributor.part_id == part_id).all()
    for part in contributors:
        found = False
        for part2 in part:
            if part2.person_id == part.person.id:
                part.role_id = part.role.id
                part.real_person_id = part.real_person_id
                found = True
                session.add(part)
        if not found:
            new_contributor = Contributor(
                part_id=part_id,
                person_id=part.person.id,
                role_id=part.role.id,
                real_person_id=part.real_person.id)
            session.add(new_contributor)


def _updateShortContributors(session: Any, short_id: int, contributors: Any) -> None:
    parts = session.query(Part).filter(Part.shortstory_id == short_id).all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)
