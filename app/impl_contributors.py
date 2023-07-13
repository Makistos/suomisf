from typing import Any, Dict, Union, List
from app.orm_decl import (Part, Contributor, Edition)
from sqlalchemy import and_, or_
from app.impl import checkInt
from app import app

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
    """
    Returns a boolean indicating whether or not the list of new values is different from the list of old values
    :param old_values: list of previous contributors
    :param new_values: list of new contributors
    :return: boolean indicating whether or not the list of new values is different from the list of old values
    """
    l: Any = []
    for value in new_values:
        if value['person']['id'] == 0 or value['role']['id'] == 0:
            # Remove empty rows (person and role are required fields)
            continue
        l.append(value)
    if len(old_values) != len(l):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.person_id != l[idx]['person']['id'] or \
                old_value.role_id != l[idx]['role']['id'] or \
                old_value.description != l[idx]['description']:
            return True
    return False


def updateShortContributors(session: Any, short_id: int, contributors: Any) -> None:
    parts = session.query(Part).filter(Part.shortstory_id == short_id).all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)


def updateEditionContributors(session: Any, edition: Edition, contributors: Any) -> bool:
    """
    Updates the contributors for the given edition in the database.

    Args:
        session: A database session object.
        edition: An Edition object representing the edition to update.
        contributors: A list of dictionaries representing the new contributors.
            Each dictionary should have the following keys:
            - 'person': A dictionary representing the person who contributed.
                This dictionary should have the following keys:
                - 'id': The ID of the person in the database.
            - 'role': A dictionary representing the role of the contributor.
                This dictionary should have the following keys:
                - 'id': The ID of the role in the database.
            - 'description': A string describing the contribution.

    Returns:
        None
    """
    retval = False
    parts = session.query(Part)\
        .filter(Part.edition_id == edition.id)\
        .filter(Part.shortstory_id == None)\
        .all()
    for part in parts:
        # First delete contributors that are not author or editor
        session.query(Contributor)\
        .filter(Contributor.part_id == part.id)\
        .filter(and_(Contributor.role_id != 1, Contributor.role_id != 3))\
        .delete()
        # Then add the new contributors
        for contrib in contributors:
            if 'person' in contrib and 'id' in contrib['person']:
                person_id = checkInt(contrib['person']['id'], negativeValuesAllowed=False, zerosAllowed=False)
            else:
                person_id = None
            if person_id == None:
                app.logger.error('Missing or invalid person id.')
                continue
            if 'role' in contrib and 'id' in contrib['role']:
                role_id = checkInt(contrib['role']['id'], negativeValuesAllowed=False, zerosAllowed=False)
            else:
                role_id = None
            if role_id == None:
                app.logger.error('Missing or invalid role id.')
                continue
            if 'description' in contrib:
                description = contrib['description']
            else:
                description = None
            new_contributor = Contributor( # type: ignore
                part_id=part.id,
                person_id=person_id,
                role_id=role_id,
                description=description)
            session.add(new_contributor)
            retval = True
    return retval


def updateWorkContributors(session: Any, work_id: int, contributors: Any) -> None:
    """
    Updates the contributors of a work in the database.

    Args:
        session: The database session.
        work_id: The ID of the work to update.
        contributors: The list of contributors to update the work with.
    """
    parts = session.query(Part)\
        .filter(Part.work_id == work_id)\
        .filter(Part.shortstory_id == None)\
        .all()
    for part in parts:
        _updatePartContributors(session, part.id, contributors)


def getContributorsString(contributors: Any) -> str:
    """ Return a string representation of contributors.
        @param contributors: List of Contributor objects
        @return: String representation of contributors
    """
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

def getWorkContributors(session: Any, work_id: int) -> Any:
    """
    Returns a list of dictionaries representing the contributors of a work.

    Args:
        session: The database session.
        work_id: The ID of the work to get the contributors of.

    Returns:
        A list of dictionaries representing the contributors of the work.
        Each dictionary should have the following keys:
        - 'person': A dictionary representing the person who contributed.
            This dictionary should have the following keys:
            - 'id': The ID of the person in the database.
            - 'name
        - 'role': A dictionary representing the role of the contributor.
            This dictionary should have the following keys:
            - 'id': The ID of the role in the database.
            - 'name'
        - 'description': A string describing the contribution.
    """
    contributors = session.query(Contributor)\
        .join(Part)\
        .filter(Contributor.part_id == Part.id)\
        .filter(Part.work_id == work_id)\
        .filter(Part.shortstory_id == None)\
        .filter(or_(Contributor.role_id == 1, Contributor.role_id == 3))\
        .distinct()\
        .all()
    retval: List[Dict[Any, Any]] = []
    # Remove duplicates (distinct isn't enough as it does not combine people in
    # different editions)
    for contrib in contributors:
        found = False
        for contrib2 in retval:
            if contrib.person_id == contrib2['person']['id'] and contrib.role_id == contrib2['role']['id'] \
                and contrib.description == contrib2['description']:
                found = True
        if not found:
            c = {'person': {'id': contrib.person_id, 'name': contrib.person.name},
                    'role': {'id': contrib.role_id, 'name': contrib.role.name},
                    'description': contrib.description}
            retval.append(c)

    return retval