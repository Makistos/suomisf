from ast import expr_context
import json
from app import app
from app.route_helpers import new_session
from app.model import (PersonSchema, PersonBriefSchema)
from app.orm_decl import (Person, PersonTag)
from sqlalchemy.exc import SQLAlchemyError
from app.orm_decl import (Alias, Country, ContributorRole, Work)
from app.impl import (ResponseType, SearchResult,
                      SearchResultFields, searchScore)
from collections import Counter
from typing import Tuple, Dict, Any, List, Union
from operator import not_
from app.api_errors import APIError
from sqlalchemy import func
from marshmallow import exceptions


_allowed_person_fields = ['name', 'dob', 'dod',
                          'nationality',
                          'workcount', 'storycount',
                          'roles',
                          'global']

_person_relationships = {'nationality': 'name',
                         'roles': 'name'}


def _filter_person_query(table: Any,
                         query: Any,
                         key: str,
                         raw_filters: Dict[str, Any],
                         related_table: Any = None) -> Any:
    op = raw_filters['matchMode']
    value = raw_filters['value']
    if key in _person_relationships:
        column = getattr(table, key, None)
        related_key = _person_relationships[key]
        related_col = getattr(related_table, related_key, None)
        if op == 'in':
            filt = query.join(column).filter(related_col.in_([value]))
        else:
            attr = list(filter(lambda e: hasattr(related_col, e % op), [
                '%s', '%s_', '__%s__']))[0] % op
            filt = getattr(related_col, attr)(value)
        if op == 'notContains':
            query = query.join(column).filter(not_(filt))
        else:
            query = query.join(column).filter(filt)
    else:
        column = getattr(table, key, None)
        if op == 'in':
            filt = column.in_(value)
        else:
            if op == 'notContains':
                op_ = 'ilike'
            else:
                op_ = op
            attr = list(filter(lambda e: hasattr(column, e % op_), [
                '%s', '%s_', '__%s__']))[0] % op_
            filt = getattr(column, attr)(value)
        if op == 'notContains':
            query = query.filter(~filt)
        else:
            query = query.filter(filt)
    return query


def FilterPeople(query: str) -> ResponseType:
    session = new_session()
    try:
        people = session.query(Person)\
            .filter(Person.name.ilike(query + '%'))\
            .order_by(Person.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterPeople (query: {query}): ' + str(exp))
        return ResponseType('FilterPeople: Tietokantavirhe.', 400)
    try:
        schema = PersonBriefSchema(many=True)
        retval = schema.dump(people)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterPeople schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterPeople: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def FilterAliases(person_id: int) -> ResponseType:
    session = new_session()
    try:
        aliases = session.query(Alias)\
            .filter(Alias.realname == person_id)\
            .all()
        ids = [x.alias for x in aliases]
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterAliases (åerson_id {person_id}): ' + str(exp))
        return ResponseType('FilterAliases: Tietokantavirhe.', 400)

    # aliases = session.query(Alias).filter(Alias.realname == personid).all()
    # ids = [x.alias for x in aliases]

    # personas = session.query(Person)\
    #     .filter(Person.id.in_(ids))\
    #     .all()

    # retval: List[Dict[str, str]] = []
    # if personas:
    #     for persona in personas:
    #         obj: Dict[str, str] = {'id': persona.id, 'text': persona.name}
    #         retval.append(obj)
    # return Response(json.dumps(retval))


def GetAuthorFirstLetters(target: str) -> Tuple[str, int]:
    retval = ('', 200)
    session = new_session()

    if target == 'works':
        # Substring doesn't really work with unicode names in SQL so have to
        # that manually.
        names = session.query(Work.author_str)\
            .order_by(Work.author_str)\
            .all()
        letters = [s[0][0].upper() for s in names]
        retval = json.dumps(Counter(letters)), 200

    elif target == 'stories':
        letters = session.query(Person)
    else:
        retval = ('', 400)

    return retval


def ListPeople(params: Dict[str, Any]) -> ResponseType:
    d: Dict[str, Union[int, List[str]]] = {}
    session = new_session()
    try:
        people = session.query(Person)
        # Filter
        for field, filters in params.items():
            if type(filters) is dict:
                if field not in _allowed_person_fields:
                    raise APIError('Invalid filter field %s' % field, 405)
                if filters['value']:
                    if field == 'nationality':
                        people = _filter_person_query(
                            Person, people, field, filters, Country)
                    elif field == 'roles':
                        people = _filter_person_query(
                            Person, people, field, filters, ContributorRole)
                    else:
                        people = _filter_person_query(
                            Person, people, field, filters)
        count = len(people.all())

        # Sort
        if 'sortField' in params:
            sort_field = params['sortField']
            if (sort_field == 'name' or
                sort_field == 'dob' or
                    sort_field == 'dod'):
                sort_col = getattr(Person, sort_field, None)
                if params['sortOrder'] == '1':
                    people = people.order_by(sort_col.asc())
                else:
                    people = people.order_by(sort_col.desc())
            if sort_field == 'nationality':
                sort_col = getattr(Country, 'name', None)
                people = people.join(Person.nationality)\
                    .order_by(Country.name.asc())
            elif sort_field == 'workcount':
                people = people.join(Person.works)\
                    .order_by(func.count(Work.id))
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListPeople: ' + str(exp))
        return ResponseType(f'ListPeople: Tietokantavirhe.', 400)

    # Pagination
    if 'rows' in params:
        if not 'page' in params:
            params['page'] = 0
        start = int(params['rows']) * (int(params['page']))
        end = int(params['rows']) * (int(params['page']) + 1)
        app.logger.warn("page: " + str(params['page']) +
                        " rows: " + str(params['rows']) +
                        " start: " + str(start) +
                        " end: " + str(end))
        people = people[start:end]

    # Serialize to JSON
    try:
        schema = PersonBriefSchema(many=True)
        d['people'] = schema.dump(people)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListPeople schema error: ' + str(exp))
        return ResponseType('ListPeople: Skeemavirhe.', 400)

    d['totalRecords'] = count
    return ResponseType(d, 200)


def GetPerson(person_id: int) -> ResponseType:
    session = new_session()
    try:
        aliases = session.query(Alias)\
            .filter(Alias.alias == person_id).all()
        if len(aliases) == 1:
            # This is an alias that has only been used by one person,
            # find out real person.
            real_person = session.query(Person).filter(
                Person.id == aliases[0].realname).first()
            person_id = real_person.id

        person = session.query(Person).filter(
            Person.id == person_id).first()
        if not person:
            return ResponseType(f"Unknown person. Id={person_id}.", 401)

        aliases = session.query(Alias)\
            .filter(Alias.realname == person.id).all()

        if len(aliases) > 0:
            # Person has aliases
            for alias_id in aliases:
                alias = session.query(Person)\
                    .filter(Person.id == alias_id.alias).first()
                person.works = person.works + alias.works
                person.edits = person.edits + alias.edits
                person.translations = person.translations + alias.translations
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetPerson: ' + str(exp))
        return ResponseType(f'GetPerson: Tietokantavirhe.', 400)

    try:
        schema = PersonSchema()
        retval = schema.dump(person)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetPerson schema error: ' + str(exp))
        return ResponseType('GetPerson: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def PersonTagAdd(person_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        person = session.query(Person).filter(
            Person.id == person_id).first()
        if not person:
            app.logger.error(
                f'PersonTagAdd: Person not found. Id = {person_id}.')
            return ResponseType(f'PersonTagAdd: Henkilöä ei löydy. person_id={person_id}, tag_id={tag_id}.', 400)

        personTag = PersonTag()
        personTag.person_id = person_id
        personTag.tag_id = tag_id
        session.add(personTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonTagAdd(): ' + str(exp))
        return ResponseType(f'PersonTagAdd: Tietokantavirhe. person_id={person_id}, tag_id={tag_id}.', 400)

    return retval


def PersonTagRemove(person_id: int, tag_id: int) -> ResponseType:
    retval = ResponseType('', 200)
    session = new_session()

    try:
        personTag = session.query(PersonTag)\
            .filter(PersonTag.person_id == person_id, PersonTag.tag_id == tag_id)\
            .first()
        if not personTag:
            app.logger.error(
                f'PersonTagRemove: Issue has no such tag: issue_id {person_id}, tag {tag_id}.'
            )
            return ResponseType(f'PersonTagRemove: Tagia ei löydy numerolta. person_id={person_id}, tag_id={tag_id}.', 400)
        session.delete(personTag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonTagRemove(): ' + str(exp))
        return ResponseType(f'PersonTagRemove: Tietokantavirhe. person_id={person_id}, tag_id={tag_id}.', 400)

    return retval


def SearchPeople(session: Any, searchwords: List[str]) -> SearchResult:
    retval: SearchResult = []
    found_people: Dict[int, SearchResultFields] = {}

    for searchword in searchwords:
        people = \
            session.query(Person)\
            .filter(Person.name.ilike('%' + searchword + '%') |
                    Person.fullname.ilike('%' + searchword + '%') |
                    Person.other_names.ilike('%' + searchword + '%') |
                    Person.alt_name.ilike('%' + searchword + '%') |
                    Person.bio.ilike('%' + searchword + '%')) \
            .order_by(Person.name) \
            .all()

        for person in people:
            if person.id in found_people:
                found_people[person.id]['score'] *= \
                    searchScore('person', person, searchword)
            else:
                description = ''
                if person.nationality:
                    description = person.nationality.name
                if person.dob or person.dod:
                    description += ' ('
                if person.dob:
                    description += str(person.dob)
                if person.dob or person.dod:
                    description += '-'
                if person.dod:
                    description += str(person.dod)
                if person.dob or person.dod:
                    description += ')'
                item: SearchResultFields = {
                    'id': person.id,
                    'img': '',
                    'header': person.name,
                    'description': description,
                    'type': 'person',
                    'score': searchScore('person', person, searchword)
                }
                found_people[person.id] = item
        retval = [value for _, value in found_people.items()]

    return retval