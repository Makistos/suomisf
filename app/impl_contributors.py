""" Contributor related functions."""
from typing import Any, Dict, Union, List
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.orm_decl import (Part, Contributor, Edition, IssueContributor)
from app.impl import check_int
from app import app
from app.orm_decl import Person
from app.types import ContributorType, ContributorTarget


def _create_new_person(session: Any, contrib: Any) -> Union[Person, None]:
    """
    Create a new person and add it to the database.

    This function is used to create a new person when adding a new contributor.
    This person will have the same name and alt_name so information needs to be
    fixed later.
    """
    person = Person()
    # Check if this person already exists somehow
    try:
        existing_person: Person = session.query(Person)\
            .filter(Person.name == contrib['person']).first()
    except SQLAlchemyError as exp:
        app.logger.error('_createNewPerson: ' + str(exp))
        return None
    if existing_person:
        return existing_person
    person.name = contrib['person']
    person.alt_name = contrib['person']
    session.add(person)
    try:
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('_createNewPerson: ' + str(exp))
        session.rollback()
        return None
    return person


def _create_new_contributors(session: Any, contributors: Any) -> List[Any]:
    """
    Create new contributors based on the provided session and contributors
    list.

    Args:
        session (Any): The session object for the database connection.
        contributors (Any): The list of contributors.

    Returns:
        List[Any]: The list of new contributors created.

    """
    retval: List[Any] = []
    person: Union[Person, None] = None
    for contrib in contributors:
        person = None
        if isinstance(contrib['person'], str) or 'id' not in contrib['person']:
            person = _create_new_person(session, contrib)
        else:
            person = session.query(Person)\
                .filter(Person.id == contrib['person']['id']).first()
            if not person:
                person = _create_new_person(session, contrib)
        if person:
            description = (contrib['description']
                           if 'description' in contrib else '')
            contrib = {'person': {'id': person.id}, 'role': contrib['role'],
                       'description': description}
            retval.append(contrib)

    return retval


def _update_part_contributors(
        session: Any,
        part_id: int,
        contributors: Any,
        item_type: ContributorTarget
        ) -> None:
    """ Update the contributors of a part for works."""
    # Remove existing rows from table.
    if item_type == ContributorTarget.WORK:
        session.query(Contributor).filter(
            Contributor.part_id == part_id)\
            .filter(or_(Contributor.role_id == ContributorType.AUTHOR.value,
                        Contributor.role_id == ContributorType.EDITOR.value,
                        Contributor.role_id == ContributorType.SUBJECT.value))\
            .delete()
    elif item_type == ContributorTarget.EDITION:
        session.query(Contributor).filter(
            Contributor.part_id == part_id)\
            .filter(and_
                    (Contributor.role_id != ContributorType.AUTHOR.value,
                     Contributor.role_id != ContributorType.EDITOR.value,
                     Contributor.role_id != ContributorType.SUBJECT.value))\
            .delete()
    elif item_type == ContributorTarget.SHORT:
        tmp = session.query(Contributor).filter(
            Contributor.part_id == part_id)\
            .join(Part)\
            .filter(Part.shortstory_id.isnot(None))\
            .all()
        for contrib in tmp:
            session.delete(contrib)
    else:
        app.logger.eror(f'Unknown contributor type: {item_type.value}')
        raise ValueError(f'Unknown contributor type: {item_type.value}')

    session.flush()
    for contrib in contributors:
        new_contributor = Contributor(
            part_id=part_id,
            person_id=contrib['person']['id'],
            role_id=contrib['role']['id'],
            description=contrib['description'])
        # if 'real_person' in contrib:
        #     new_contributor.real_person.id = contrib['real_person'].id,
        session.add(new_contributor)


def _remove_duplicates_and_empty(contributors: List[Any]) -> List[Any]:
    """
    Remove duplicate and empty contributors from the list. This happens with a
    work if it has multiple editions and when it has no contributors (there
    will be one empty contributor). They can not be removed with the distinct
    operation because they are separate rows in the database. But from the
    point of seeing if things have changed we need to remove duplicates.
    """
    retval: List[Any] = []
    for contrib in contributors:
        found = False
        if not isinstance(contrib['person'], dict):
            # User added new person
            found = True
            retval.append(contrib)
            continue
        for contrib2 in retval:
            if (contrib['person']['id'] == contrib2['person']['id'] and
                    contrib['role']['id'] == contrib2['role']['id'] and
                    contrib.description == contrib2.description):
                found = True
        if not found and contrib['person']['id'] not in (0, None):
            retval.append(contrib)
    return retval


def contributors_have_changed(
        old_values: List[Any],
        new_values: List[Any]) -> bool:
    """
    Returns a boolean indicating whether or not the list of new values is
    different from the list of old values.

    Args:
        old_values (List[Any]): list of previous contributors
        new_values(List[Any]): list of new contributors

    Returns:
        boolean: indicating whether or not the list of new values is
        different from the list of old values.
    """
    # old_values = _remove_duplicates_and_empty(old_values)
    new_values = _remove_duplicates_and_empty(new_values)
    if len(old_values) != len(new_values):
        return True
    l: Any = []
    for value in new_values:
        if 'id' not in value['person']:
            # User added a new contributor that does not exist in the database
            return True
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


def update_short_contributors(
        session: Any,
        short_id: int, contributors: Any) -> None:
    """
    Update the short contributors for a given short ID.

    Args:
        session (Any): The session object for database operations.
        short_id (int): The ID of the short story.
        contributors (Any): The contributors object.

    Returns:
        None: This function does not return anything.
    """
    parts = session.query(Part).filter(Part.shortstory_id == short_id).all()
    short_contributors =\
        [x for x in contributors
         if x['role']['id'] == 1 or x['role']['id'] == 2
            or x['role']['id'] == 6]
    contributors = _create_new_contributors(session, short_contributors)
    for part in parts:
        _update_part_contributors(session, part.id, short_contributors,
                                  ContributorTarget.SHORT)


def update_edition_contributors(
        session: Any,
        edition: Edition, contributors: Any) -> bool:
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
        .filter(Part.shortstory_id.is_(None))\
        .all()
    # Create new contributors if needed
    contributors = _create_new_contributors(session, contributors)
    for part in parts:
        # First delete contributors that are not author or editor
        session.query(Contributor)\
            .filter(Contributor.part_id == part.id)\
            .filter(and_(Contributor.role_id != ContributorType.AUTHOR.value,
                         Contributor.role_id != ContributorType.EDITOR.value))\
            .delete()
        # Then add the new contributors
        for contrib in contributors:
            person_id = contrib['person']['id']
            if 'role' in contrib and 'id' in contrib['role']:
                role_id = check_int(contrib['role']['id'],
                                    negative_values=False, zeros_allowed=False)
            else:
                role_id = None
                app.logger.error('Missing or invalid role id.')
                continue
            if 'description' in contrib:
                description = contrib['description']
            else:
                description = None
            new_contributor = Contributor(  # type: ignore
                part_id=part.id,
                person_id=person_id,
                role_id=role_id,
                description=description)
            session.add(new_contributor)
            retval = True
    return retval


def update_work_contributors(
        session: Any,
        work_id: int,
        contributors: Any) -> bool:
    """
    Updates the contributors of a work in the database.

    Args:
        session: The database session.
        work_id: The ID of the work to update.
        contributors: The list of contributors to update the work with.
    """
    retval = False
    parts = session.query(Part)\
        .filter(Part.work_id == work_id)\
        .filter(Part.shortstory_id.is_(None)) \
        .all()
    # Create new contributors if needed
    contributors = _create_new_contributors(session, contributors)
    for part in parts:
        _update_part_contributors(session, part.id, contributors,
                                  ContributorTarget.WORK)

    return retval


def get_contributors_string(contributors: Any,
                            contribution_type: ContributorTarget) -> str:
    """ Return a string representation of contributors.
        @param contributors: List of Contributor objects
        @return: String representation of contributors
    """
    retval = []
    # Select contributors:
    cleaned_contribs: List[Contributor] = []
    if contribution_type in [ContributorTarget.WORK, ContributorTarget.SHORT]:
        # Remove duplicates caused by multiple editions
        for contrib in contributors:
            found = False
            for contrib2 in cleaned_contribs:
                if (contrib.person.id == contrib2.person.id and
                        contrib.role.id == contrib2.role.id and
                        contrib.description == contrib2.description):
                    found = True
            if not found:
                cleaned_contribs.append(contrib)
    elif contribution_type == ContributorTarget.EDITION:
        # Remove authors and editors
        cleaned_contribs = [
            x for x in contributors if x.role.id != ContributorType.AUTHOR and
            x.role_id != ContributorType.EDITOR]
    for contrib in cleaned_contribs:
        s = ''
        if contrib.role_id != 1 or contrib.role_id != 3:
            s += contrib.person.name + ' [' + contrib.role.name
            if contrib.description is not None and contrib.description != '':
                s += '(' + contrib.description + ')'
            s += ']'
        retval.append(s)
    return '\n'.join(retval)


def get_work_contributors(session: Any, work_id: int) -> Any:
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
        .filter(Part.shortstory_id.is_(None))\
        .filter(or_(Contributor.role_id == ContributorType.AUTHOR,
                    Contributor.role_id == ContributorType.EDITOR))\
        .distinct()\
        .all()
    retval: List[Dict[Any, Any]] = []
    # Remove duplicates (distinct isn't enough as it does not combine people in
    # different editions)
    for contrib in contributors:
        found = False
        for contrib2 in retval:
            desc1 = contrib.description if contrib.description else ''
            desc2 = contrib2['description'] if contrib2['description'] else ''
            if (contrib.person_id == contrib2['person']['id'] and
                    contrib.role_id == contrib2['role']['id'] and
                    desc1 == desc2):
                found = True
            if (contrib.person_id == contrib2['person']['id'] and
                    contrib.role_id == contrib2['role']['id'] and
                    contrib.description == contrib2['description']):
                found = True
        if not found:
            c = {'person': {'id': contrib.person_id,
                            'name': contrib.person.name},
                 'role': {'id': contrib.role_id,
                          'name': contrib.role.name},
                 'description': contrib.description}
            retval.append(c)

    return retval


def get_issue_contributors(session: Any, issue_id: int) -> List[Dict[Any, Any]]:
    """
    Returns a list of dictionaries representing the contributors of an issue.

    Args:
        session: The database session.
        issue_id: The ID of the issue to get the contributors of.

    Returns:
        A list of dictionaries representing the contributors of the issue.
        Each dictionary should have the following keys:
        - 'person': A dictionary representing the person who contributed.
            This dictionary should have the following keys:
            - 'id': The ID of the person in the database.
            - 'name': The name of the person.
        - 'role': A dictionary representing the role of the contributor.
            This dictionary should have the following keys:
            - 'id': The ID of the role in the database.
            - 'name': The name of the role.
        - 'description': A string describing the contribution.
    """
    contributors = session.query(IssueContributor)\
        .filter(IssueContributor.issue_id == issue_id)\
        .all()

    retval: List[Dict[Any, Any]] = []

    for contrib in contributors:
        c = {'person': {'id': contrib.person_id,
                        'name': contrib.person.name},
             'role': {'id': contrib.role_id,
                      'name': contrib.role.name},
             'description': contrib.description}
        retval.append(c)

    return retval


def has_contribution_role(contributors: List[Any], role_id: int) -> bool:
    """
    Returns a boolean indicating whether or not the given list of contributors
    contains a contributor with the given role.

    Args:
        contributors: A list of dictionaries representing the contributors.
        role_id: The ID of the role to check for.

    Returns:
        A boolean indicating whether or not the given list of contributors
        contains a contributor with the given role.
    """
    for contrib in contributors:
        if contrib['role']['id'] == role_id:
            return True
    return False


def update_issue_contributors(
        session: Any,
        issue_id: int,
        contributors: Any) -> bool:
    """
    Updates the contributors for the given issue in the database.

    Args:
        session: A database session object.
        issue_id: The ID of the issue to update.
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
        bool: True if contributors were updated or no changes were made, False
              otherwise.
    """
    retval = False

    try:
        # Get current contributors for comparison
        current_contributors = session.query(IssueContributor)\
            .filter(IssueContributor.issue_id == issue_id)\
            .all()

        # Check if contributors have changed
        if not contributors_have_changed(current_contributors, contributors):
            return True

        # Remove existing contributors for this issue
        session.query(IssueContributor)\
            .filter(IssueContributor.issue_id == issue_id)\
            .delete()

        # Create new contributors if needed
        contributors = _create_new_contributors(session, contributors)

        # Add the new contributors
        for contrib in contributors:
            person_id = contrib['person']['id']
            if 'role' in contrib and 'id' in contrib['role']:
                role_id = check_int(contrib['role']['id'],
                                    negative_values=False, zeros_allowed=False)
            else:
                role_id = None
                app.logger.error('Missing or invalid role id.')
                continue
            if 'description' in contrib:
                description = contrib['description']
            else:
                description = None

            new_contributor = IssueContributor(
                issue_id=issue_id,
                person_id=person_id,
                role_id=role_id,
                description=description)
            session.add(new_contributor)

        retval = True

    except SQLAlchemyError as exp:
        app.logger.error('update_issue_contributors: ' + str(exp))
        session.rollback()
        retval = False

    return retval
