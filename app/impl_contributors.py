from typing import Any, Dict, Union, List
from app.orm_decl import (Part, Contributor, Edition)
from sqlalchemy import and_, or_

def _updatePartContributors(session: Any, part_id: int, contributors: Any) -> None:
    # Remove existing rows from table.
    session.query(Contributor).filter(
        Contributor.part_id == part_id)\
        .delete()
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


def updateEditionContributors(session: Any, edition: Edition, contributors: Any) -> None:
    parts = session.query(Part)\
        .filter(Part.edition_id == edition.id)\
        .filter(Part.shortstory_id == None)\
        .all()
    # work_contributors = session.query(Contributor)\
    #     .join(Part)\
    #     .filter(Part.work_id == edition.work[0].id)\
    #     .filter(Contributor.part_id == Part.id)\
    #     .filter(or_(Contributor.role_id == 1, Contributor.role_id == 3))\
    #     .distinct().all()
    # for contrib in work_contributors:
    #     exists = False
    #     for c in contributors:
    #         if c['person']['id'] == contrib.person_id and c['role']['id'] == contrib.role_id and c['description'] == contrib.description:
    #             exists = True
    #     if not exists:
    #         contributors.append({
    #             'person': {
    #                 'id': contrib.person_id,
    #                 'name': contrib.person.name
    #             },
    #             'role': {
    #                 'id': contrib.role_id,
    #                 'name': contrib.role.name
    #             },
    #             'description': contrib.description
    #         })
    for part in parts:
        session.query(Contributor)\
        .filter(Contributor.part_id == part.id)\
        .filter(and_(Contributor.role_id != 1, Contributor.role_id != 3))\
        .delete()
        for contrib in contributors:
            new_contributor = Contributor(
                part_id=part.id,
                person_id=contrib['person']['id'],
                role_id=contrib['role']['id'],
                description=contrib['description'])
            session.add(new_contributor)
        #_updatePartContributors(session, part.id, contributors)


def updateWorkContributors(session: Any, work_id: int, contributors: Any) -> None:
    parts = session.query(Part)\
        .filter(Part.work_id == work_id)\
        .filter(Part.shortstory_id == None)\
        .all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)

def getContributorsString(contributors: Any) -> str:
    retval = []
    for contrib in contributors:
        str = ''
        if contrib.role_id != 1 or contrib.role_id != 3:
            str += contrib.person.name + ' [' + contrib.role.name
            if contrib.description != None and contrib.description != '':
               str+= '(' + contrib.description + ')'
            str += ']'
        retval.append(str)
    return '\n'.join(retval)