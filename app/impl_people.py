""" People related stuff. """
import json
from collections import Counter
from typing import Tuple, Dict, Any, List, Union
from operator import not_
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.impl_logs import log_changes

from app.route_helpers import new_session
from app.model import (ArticleSchema, IssueSchema, LogSchema,
                       PersonBriefSchema)
from app.model_person import (PersonSchema)
from app.model import (ShortBriefestSchema)
from app.orm_decl import (Alias, Article, Country, ContributorRole, Issue, IssueContributor, Log,
                          Work,
                          Contributor,
                          PersonLink, Awarded, PersonLanguage, PersonTag,
                          IssueEditor, ArticlePerson, ArticleAuthor,
                          ShortStory, Part, Person)
from app.impl import (ResponseType, SearchResult, SearchResultFields,
                      searchscore, check_int, get_join_changes)
from app.api_errors import APIError
from app.impl_country import AddCountry
from app.impl_links import links_have_changed
from app.types import HttpResponseCode
from app import app

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
    """
    Filter a person query based on the provided filters.

    Args:
        table (Any): The table to query.
        query (Any): The query object.
        key (str): The key to filter on.
        raw_filters (Dict[str, Any]): The raw filters to apply.
        related_table (Any, optional): The related table to join. Defaults to
                                       None.

    Returns:
        Any: The filtered query object.
    """
    op = raw_filters['matchMode']
    value = raw_filters['value']
    if key in _person_relationships:
        column = getattr(table, key, None)
        related_key = _person_relationships[key]
        related_col = getattr(related_table, related_key, None)
        if related_col:
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
        if column and op == 'in':
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


def _set_nationality(
        session: Any,
        person: Person,
        data: Any,
        old_values: Union[Dict[str, Any], None]) -> Union[ResponseType, None]:
    """
    Set the nationality of a person in the given session.

    Parameters:
        session (Any): The session object.
        person (Person): The person object.
        data (Any): The data object.
        old_values (Union[Dict[str, Any], None]): The old values object.

    Returns:
        Union[ResponseType, None]: The response type or None.
    """
    if data['nationality'] != person.nationality:
        nat_id = None
        if old_values is not None:
            if person.nationality:
                old_values['Kansallisuus'] = person.nationality.name
            else:
                old_values['Kansallisuus'] = ''
        if (isinstance(data['nationality'], str) or
            ('id' not in data['nationality'] and data['nationality'] != '')):
            # Add new nationality to db
            nat_id = AddCountry(session, data['nationality'])
        elif data['nationality'] == '':
            nat_id = None
        else:
            nat_id = check_int(data['nationality']['id'],
                               zeros_allowed=False,
                               negative_values=False)
        if nat_id is not None:
            # Check that nationality exists
            nat = session.query(Country).filter(Country.id == nat_id).first()
            if nat:
                nat_id = nat.id
            else:
                nat_id = None
        person.nationality_id = nat_id
    return None


def filter_people(query: str) -> ResponseType:
    """
    Filters people based on a given query.

    Args:
        query (str): The query string to filter the people by.

    Returns:
        ResponseType: The response containing the filtered people or an error
                      message.
    """
    session = new_session()
    try:
        people = session.query(Person)\
            .filter(Person.name.ilike(query + '%'))\
            .order_by(Person.name)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterPeople (query: {query}): ' + str(exp))
        return ResponseType('FilterPeople: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = PersonBriefSchema(many=True)
        retval = schema.dump(people)
    except exceptions.MarshmallowError as exp:
        app.logger.error(
            f'FilterPeople schema error (query: {query}): ' + str(exp))
        return ResponseType('FilterPeople: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def filter_aliases(person_id: int) -> ResponseType:
    """
    Retrieves aliases for a given person ID.

    Args:
        person_id (int): The ID of the person.

    Returns:
        ResponseType: The response containing the aliases as a list of
                      dictionaries.

    Raises:
        SQLAlchemyError: If there is an error in the database query.
    """
    session = new_session()
    try:
        aliases = session.query(Alias)\
            .filter(Alias.realname == person_id)\
            .all()
        # ids = [x.alias for x in aliases]
    except SQLAlchemyError as exp:
        app.logger.error(
            f'Exception in FilterAliases (åerson_id {person_id}): ' + str(exp))
        return ResponseType('FilterAliases: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

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
    schema = PersonBriefSchema(many=True)
    retval = schema.dump(aliases)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_author_first_letters(target: str) -> Tuple[str, int]:
    """
    Finds all the letters that have any authors starting with it.

    """
    retval = ('', HttpResponseCode.OK.value)
    session = new_session()

    if target == 'works':
        # Substring doesn't really work with unicode names in SQL so have to
        # that manually.
        names = session.query(Work.author_str)\
            .filter(Work.author_str is not None)\
            .order_by(Work.author_str)\
            .distinct()\
            .all()
        letters = sorted(
            list(
                set([s[0][0].upper()
                     for s in names
                     if s[0] is not None and s[0][0].isalpha()])))
        retval = json.dumps(Counter(letters)), HttpResponseCode.OK.value

    elif target == 'stories':
        letters = session.query(Person)
    else:
        retval = ('', HttpResponseCode.BAD_REQUEST.value)

    return retval


def list_people(params: Dict[str, Any]) -> ResponseType:
    """
    List people based on the given parameters and return the response.

    Args:
        params (Dict[str, Any]): A dictionary containing the parameters for
                                 filtering, sorting, and pagination.

    Returns:
        ResponseType: A response object containing the list of people and other
                      metadata.

    Raises:
        APIError: If an invalid filter field is provided.
        SQLAlchemyError: If there is an error in the database query.
        exceptions.MarshmallowError: If there is an error in the serialization
                                     schema.
    """
    d: Dict[str, Union[int, List[str]]] = {}
    session = new_session()
    try:
        people = session.query(Person)\
            .join(Contributor,
                  or_(Contributor.person_id == Person.id,
                      Contributor.real_person_id == Person.id))
        # Filter
        for field, filters in params.items():
            if isinstance(filters, dict):
                if field not in _allowed_person_fields:
                    raise APIError(f'Invalid filter field {field}',
                                   HttpResponseCode.METHOD_NOT_ALLOWED.value)
                if filters['value']:
                    if ((field == 'dob' or field == 'dod')
                        and filters['value'] and len(filters['value']) < 4):
                        filters['value'] = filters['value'].ljust(4, '0')
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
            if (sort_field in ['name', 'dob', 'dod']):
                sort_col = getattr(Person, sort_field, None)
                if sort_col:
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
        return ResponseType('ListPeople: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    # Pagination
    if 'rows' in params:
        if 'page' not in params:
            params['page'] = 0
        start = int(params['rows']) * (int(params['page']))
        end = int(params['rows']) * (int(params['page']) + 1)
        app.logger.warning("page: " + str(params['page']) +
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
        return ResponseType('ListPeople: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    d['totalRecords'] = count
    return ResponseType(d, HttpResponseCode.OK.value)


def get_person(person_id: int) -> ResponseType:
    """
    Retrieves information about a person based on their ID.

    Parameters:
        person_id (int): The ID of the person.

    Returns:
        ResponseType: The response containing the person's information or an
                      error message.
    """
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
            app.logger.error(f'get_person: Unknown person. Id={person_id}.')
            return ResponseType(f"Unknown person. Id={person_id}.",
                                HttpResponseCode.BAD_REQUEST.value)

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
                person.work_contributions = person.works
                person.edit_contributions = person.edits
                person.editions = person.editions + alias.editions
                person.stories = person.stories + alias.stories
                # person.appears_in = person.appears_in + alias.appears_in
                # person.articles = person.articles + alias.articles
                person.links = person.links
                # person.magazine_stories = person.magazine_stories + \
                #    alias.magazine_stories
                person.roles = person.roles + alias.roles

    except SQLAlchemyError as exp:
        app.logger.error(f'get_person exception: {exp}.')
        return ResponseType(f'get_person tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = PersonSchema()
        retval = schema.dump(person)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_person schema error: {exp}.')
        return ResponseType(f'get_person skeemavirhe: {exp}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_person_articles(person_id: int) -> ResponseType:
    """
    Retrieves the articles written by a specific person from the database.

    Args:
        person_id (int): The unique identifier of the person.

    Returns:
        ResponseType: An object containing the retrieved articles and the HTTP
                      response code.
    """
    session = new_session()
    try:
        articles = session.query(Article)\
            .join(ArticleAuthor)\
            .filter(ArticleAuthor.person_id == person_id,
                    ArticleAuthor.article_id == Article.id) \
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_person_articles exception: {exp}.')
        return ResponseType(f'get_person_articles tietokantavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = ArticleSchema(many=True)
        retval = schema.dump(articles)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_person_articles schema error: {exp}.')
        return ResponseType(f'get_person_articles skeemavirhe: {exp}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def person_add(params: Any) -> ResponseType:
    """
    Adds a new person to the system.

    Args:
        params (Any): The parameters for adding a person.

    Returns:
        ResponseType: The response containing the ID of the newly added person.
    """
    session = new_session()
    data = params['data']

    person = Person()
    if 'name' not in data:
        app.logger.error('No name in data.')
        return ResponseType('Nimi puuttuu.',
                            HttpResponseCode.BAD_REQUEST.value)

    person.name = data['name']

    person.alt_name = data['alt_name'] if 'alt_name' in data else person.name
    person.fullname = data['fullname'] if 'fullname' in data else person.name
    person.bio = data['bio'] if 'bio' in data else None
    person.bio_src = data['bio_src'] if 'bio_src' in data else None
    person.first_name = data['first_name'] if 'first_name' in data else None
    person.last_name = data['last_name'] if 'last_name' in data else None
    person.image_src = data['image_src'] if 'image_src' in data else None
    person.dob = data['dob'] if 'dob' in data else None
    person.dod = data['dod'] if 'dod' in data else None
    if ('nationality' in data and data['nationality'] is not None
            and 'id' in data['nationality']):
        person.nationality_id = data['nationality']['id']
    else:
        person.nationality_id = data['nationality_id['] \
            if 'nationality_id' in data else None
    person.other_names = data['other_names'] if 'other_names' in data else None

    try:
        session.add(person)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in person_add: ' + str(exp))
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if 'links' in data:
        for link in data['links']:
            pl = PersonLink(
                person_id=person.id, link=link['link'],
                description=link['description']
            )
            session.add(pl)
    try:
        session.add(person)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in person_add: ' + str(exp))
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(str(person.id), HttpResponseCode.CREATED.value)


def person_update(params: Any) -> ResponseType:
    # pylint: disable=too-many-branches,too-many-statements,too-many-locals,too-many-return-statements  # noqa: E501
    """
    Update a person's information in the database.

    Args:
        params (Any): The parameters for updating the person.
            - data (dict): The data for updating the person.
                - id (int): The ID of the person to update.
                - name (str): The new name of the person.
                - alt_name (str, optional): The new alternative name of the
                                            person.
                - fullname (str, optional): The new full name of the person.
                - other_names (str, optional): The new other names of the
                                               person.
                - first_name (str, optional): The new first name of the person.
                - last_name (str, optional): The new last name of the person.
                - image_src (str, optional): The new image source of the
                                             person.
                - dob (int, optional): The new date of birth of the person.
                - dod (int, optional): The new date of death of the person.
                - bio (str, optional): The new biography of the person.
                - bio_src (str, optional): The new biography source of the
                                           person.
                - nationality (str, optional): The new nationality of the
                                               person.
                - links (list[dict], optional): The new links of the person.
                    - link (str): The URL of the link.
                    - description (str): The description of the link.

    Returns:
        ResponseType: The response indicating the result of the update
                      operation.
    """
    retval = ResponseType('OK', HttpResponseCode.OK.value)
    session = new_session()
    old_values: Dict[str, Any] = {}
    data = params['data']

    person_id = check_int(data['id'],
                          zeros_allowed=False,
                          negative_values=False)
    if person_id is None:
        app.logger.error('PersonUpdate: Invalid id.')
        return ResponseType('PersonUpdate: Virheellinen id.',
                            HttpResponseCode.BAD_REQUEST.value)

    # Check that person exists
    person = session.query(Person).filter(
        Person.id == person_id).first()
    if not person:
        app.logger.error(
            f'PersonUpdate: Person not found. Id = {person_id}.')
        return ResponseType(f'PersonUpdate: Henkilöä ei löydy. \
                            person_id={person_id}.',
                            HttpResponseCode.BAD_REQUEST.value)

    # Check that name is not empty
    # if 'name' not in data:
    #     app.logger.error('PersonUpdate: Name is missing.')
    #     return ResponseType('PersonUpdate: Nimi puuttuu.',
    #                         HttpResponseCode.BAD_REQUEST.value)

    if 'name' in data:
        if data['name'] == '':
            app.logger.error('PersonUpdate: Name is empty.')
            return ResponseType(
                'PersonUpdate: Nimi ei voi olla tyhjä puuttuu.',
                HttpResponseCode.BAD_REQUEST.value)
        name = data['name']
        if data['name'] != person.name:
            old_values['Nimi'] = person.name
            person.name = name

    if 'alt_name' in data:
        alt_name = data['alt_name']
    elif 'name' in data:
        alt_name = name
    else:
        alt_name = ''

    if 'alt_name' in data and alt_name != person.alt_name:
        old_values['Vaihtoehtoinen nimi'] = person.alt_name
        person.alt_name = alt_name

    if 'fullname' in data:
        if data['fullname'] != person.fullname:
            old_values['Koko nimi'] = person.fullname
            person.fullname = data['fullname']

    if 'other_names' in data:
        if data['other_names'] != person.other_names:
            old_values['Muut nimet'] = person.other_names
            person.other_names = data['other_names']

    if 'first_name' in data:
        if data['first_name'] != person.first_name:
            old_values['Etunimi'] = person.first_name
            person.first_name = data['first_name']

    if 'last_name' in data:
        if data['last_name'] != person.last_name:
            old_values['Sukunimi'] = person.last_name
            person.last_name = data['last_name']

    if 'image_src' in data:
        if data['image_src'] != person.image_src:
            old_values['Kuvan lähde'] = person.image_src
            person.image_src = data['image_src']

    if 'dob' in data:
        dob = check_int(data['dob'])
        if dob != person.dob:
            old_values['Syntymävuosi'] = person.dob
            person.dob = dob

    if 'dod' in data:
        dod = check_int(data['dod'])
        if dod != person.dod:
            old_values['Kuolinvuosi'] = person.dod
            person.dod = dod

    if 'bio' in data:
        if data['bio'] != person.bio:
            old_values['Biografia'] = person.bio
            if data['bio'] is None:
                person.bio = None
            else:
                person.bio = data['bio']

    if 'bio_src' in data:
        if data['bio_src'] != person.bio_src:
            old_values['Biografian lähde'] = person.bio_src
            person.bio_src = data['bio_src']

    if 'nationality' in data:
        # pylint: disable-next=assignment-from-none
        result = _set_nationality(session, person, data, old_values)
        if result:
            return result

    if 'links' in data:
        new_links = [x for x in data['links'] if x['link'] != '']
        if links_have_changed(person.links, new_links):
            existing_links = session.query(PersonLink).filter(
                PersonLink.person_id == person_id).all()
            (to_add, to_remove) = get_join_changes(
                [x.link for x in existing_links],
                [x['link'] for x in new_links])
            if len(existing_links) > 0:
                for link in existing_links:
                    session.delete(link)
            for link in new_links:
                if 'link' not in link:
                    app.logger.error('PersonUpdate: Link missing address.')
                    return ResponseType('PersonUpdate: Linkin tiedot \
                                         puutteelliset.',
                                        HttpResponseCode.BAD_REQUEST.value)
                # person_id can't be None here even though Mypy thinks so
                pl = PersonLink(
                    person_id=person_id, link=link['link'],  # type: ignore
                    description=link['description'])
                session.add(pl)
            old_values['Linkit'] = ' -'.join([str(x) for x in to_add])
            old_values['Linkit'] = ' +' + \
                ' -'.join([str(x) for x in to_remove])

    if len(old_values) == 0:
        # Nothing has changed
        return retval

    try:
        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(
            'Exception in PersonUpdate(): ' + str(exp))
        return ResponseType('PersonUpdate: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    log_changes(session,
                obj=person,
                action='Päivitys',
                old_values=old_values)
    # if log_id == 0:
    #     app.logger.error('PersonUpdate: Failed to log changes.')
    session.commit()

    return retval


def person_delete(person_id: int) -> ResponseType:
    # pylint: disable-next=too-many-locals,too-many-return-statements,too-many-branches  # noqa: E501
    """
    Deletes a person from the database.

    Args:
        person_id (int): The ID of the person to be deleted.

    Returns:
        ResponseType: The response indicating the success or failure of the
                      deletion operation.
    """
    session = new_session()
    old_values = {}
    # Check that person exists
    person = session.query(Person).filter(
        Person.id == person_id).first()
    if not person:
        return ResponseType(f'PersonDelete: Henkilöä ei löydy. \
                            person_id={person_id}.',
                            HttpResponseCode.BAD_REQUEST.value)

    # Check that there are no items that reference this person
    contributions = session.query(Contributor).filter(
        Contributor.person_id == person_id).all()
    if len(contributions) > 0:
        return ResponseType('PersonDelete: Henkilöä ei voi poistaa, koska \
                            hänellä on rooleja.',
                            HttpResponseCode.BAD_REQUEST.value)

    aliases = session.query(Alias).filter(
        or_(Alias.alias == person_id, Alias.realname == person_id)).all()

    if len(aliases) > 0:
        return ResponseType('PersonDelete: Henkilöä ei voi poistaa, koska \
                            hänellä on aliaksia.',
                            HttpResponseCode.BAD_REQUEST.value)

    issueeditor = session.query(IssueEditor).filter(
        IssueEditor.person_id == person_id).all()
    if len(issueeditor) > 0:
        return ResponseType('PersonDelete: Henkilöä ei voi poistaa, koska \
                            hänellä on toimittajuuksia.',
                            HttpResponseCode.BAD_REQUEST.value)

    articleperson = session.query(ArticlePerson).filter(
        ArticlePerson.person_id == person_id).all()
    if len(articleperson) > 0:
        return ResponseType('PersonDelete: Henkilöä ei voi poistaa, koska \
                            hänestä on artikkeleita.',
                            HttpResponseCode.BAD_REQUEST.value)

    articleauthor = session.query(ArticleAuthor).filter(
        ArticleAuthor.person_id == person_id).all()
    if len(articleauthor) > 0:
        return ResponseType('PersonDelete: Henkilöä ei voi poistaa, koska \
                            hänestä on artikkeleita.',
                            HttpResponseCode.BAD_REQUEST.value)

    awarded = session.query(Awarded).filter(
        Awarded.person_id == person_id).all()
    if len(awarded) > 0:
        return ResponseType('PersonDelete: Henkilöä ei voi poistaa, koska \
                            hänelle on annettu palkintoja.',
                            HttpResponseCode.BAD_REQUEST.value)

    # Delete person
    personlink = session.query(PersonLink).filter(
        PersonLink.person_id == person_id).all()
    try:
        for link in personlink:
            session.delete(link)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonDelete(): ' + str(exp))
        return ResponseType('PersonDelete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    persontags = session.query(PersonTag).filter(
        PersonTag.person_id == person_id).all()
    try:
        for tag in persontags:
            session.delete(tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonDelete(): ' + str(exp))
        return ResponseType('PersonDelete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    personlanguage = session.query(PersonLanguage).filter(
        PersonLanguage.person_id == person_id).all()
    try:
        for lang in personlanguage:
            session.delete(lang)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonDelete(): ' + str(exp))
        return ResponseType('PersonDelete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        old_values['Nimi'] = person.name
        log_changes(session,
                    obj=person,
                    action='Poisto',
                    old_values=old_values)
        session.delete(person)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonDelete(): ' + str(exp))
        return ResponseType('PersonDelete: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def person_tag_add(person_id: int, tag_id: int) -> ResponseType:
    """
    Add a tag to a person.

    Parameters:
        person_id (int): The ID of the person.
        tag_id (int): The ID of the tag.

    Returns:
        ResponseType: An object containing the response data and status code.
    """
    session = new_session()

    try:
        person = session.query(Person).filter(
            Person.id == person_id).first()
        if not person:
            app.logger.error(
                f'PersonTagAdd: Person not found. Id = {person_id}.')
            return ResponseType(f'PersonTagAdd: Henkilöä ei löydy. \
                                person_id={person_id}, tag_id={tag_id}.',
                                HttpResponseCode.BAD_REQUEST.value)

        person_tag = PersonTag()
        person_tag.person_id = person_id
        person_tag.tag_id = tag_id
        session.add(person_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonTagAdd(): ' + str(exp))
        return ResponseType(f'PersonTagAdd: Tietokantavirhe. \
                            person_id={person_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def person_tag_remove(person_id: int, tag_id: int) -> ResponseType:
    """
    Removes a tag from a person.

    Args:
        person_id (int): The ID of the person.
        tag_id (int): The ID of the tag to be removed.

    Returns:
        ResponseType: The response object containing the result of the
                      operation.
    """
    session = new_session()

    try:
        person_tag = session.query(PersonTag)\
            .filter(PersonTag.person_id == person_id,
                    PersonTag.tag_id == tag_id)\
            .first()
        if not person_tag:
            app.logger.error(
                f'PersonTagRemove: Issue has no such tag: \
                issue_id {person_id}, tag {tag_id}.'
            )
            return ResponseType(f'PersonTagRemove: Tagia ei löydy numerolta. \
                                person_id={person_id}, tag_id={tag_id}.',
                                HttpResponseCode.BAD_REQUEST.value)
        session.delete(person_tag)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonTagRemove(): ' + str(exp))
        return ResponseType(f'PersonTagRemove: Tietokantavirhe. \
                            person_id={person_id}, tag_id={tag_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType('OK', HttpResponseCode.OK.value)


def search_people(session: Any, searchwords: List[str]) -> SearchResult:
    """
    Search for people based on given search words.

    Args:
        session (Any): The session object for the database connection.
        searchwords (List[str]): The list of search words to use for searching
                                 people.

    Returns:
        SearchResult: The list of search results containing information about
                      the found people.

    """
    retval: SearchResult = []
    found_people: Dict[int, SearchResultFields] = {}

    for searchword in searchwords:
        lower_search = searchword.lower()
        people = \
            session.query(Person)\
            .join(Contributor,
                  or_(Person.id == Contributor.person_id,
                      Person.id == Contributor.real_person_id))\
            .filter(Person.name.ilike('%' + lower_search + '%') |
                    Person.fullname.ilike('%' + lower_search + '%') |
                    Person.other_names.ilike('%' + lower_search + '%') |
                    Person.alt_name.ilike('%' + lower_search + '%') |
                    Person.bio.ilike('%' + lower_search + '%')) \
            .order_by(Person.name) \
            .distinct()\
            .all()

        for person in people:
            if person.id in found_people:
                found_people[person.id]['score'] *= \
                    searchscore('person', person, lower_search)
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
                if len(description) > 0:
                    description += '<br />'
                if person.bio:
                    description += person.bio
                if lower_search in description.lower():
                    start = description.lower().index(lower_search)
                    description = (
                        description[:start] + '<b>' +
                        description[start:start + len(lower_search)] +
                        '</b>' + description[start + len(lower_search):]
                        )
                item: SearchResultFields = {
                    'id': person.id,
                    'author': '',
                    'img': '',
                    'header': person.name,
                    'description': description,
                    'type': 'person',
                    'score': searchscore('person', person, lower_search)
                }
                found_people[person.id] = item

        retval = [value for _, value in found_people.items()]

    return retval


def person_shorts(person_id: int) -> ResponseType:
    """
    Retrieves a list of short stories associated with a given person ID.

    Args:
        person_id (int): The ID of the person whose short stories are being
                         retrieved.

    Returns:
        ResponseType: The response object containing the list of short stories
                      in JSON format.
    """
    session = new_session()

    try:
        shorts = session.query(ShortStory)\
            .join(Part)\
            .filter(Part.shortstory_id == ShortStory.id)\
            .join(Contributor)\
            .filter(Contributor.part_id == Part.id, Contributor.role_id == 1,
                    Contributor.person_id == person_id)\
            .distinct()\
            .all()
        # ashorts = session.query(ShortStory)\
        #     .join(IssueContent)\
        #     .filter(ShortStory.id == IssueContent.shortstory_id)\
        #     .join(Part)\
        #     .filter(IssueContent.shortstory_id == Part.id)\
        #     .join(Contributor)\
        #     .filter(Part.id == Contributor.part_id)\
        #     .filter(Contributor.person_id == id)\
        #     .filter(Contributor.role_id == 1)\
        #     .distinct()\
        #     .all()

        # shorts = {...shorts, ...ashorts}

    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in PersonShorts(): ' + str(exp))
        return ResponseType('PersonShorts: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = ShortBriefestSchema(many=True)
        retval = schema.dump(shorts)
    except exceptions.MarshmallowError as exp:
        app.logger.error('PersonShorts schema error: ' + str(exp))
        return ResponseType('PersonShorts: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def get_latest_people(count: int) -> ResponseType:
    """
    Retrieves a list of the latest people from the database.

    Args:
        count (int): The number of people to retrieve.

    Returns:
        ResponseType: The response object containing the list of latest people
                      in JSON format.
    """
    session = new_session()

    try:
        people = session.query(Person)\
            .order_by(Person.id.desc())\
            .limit(count)\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(
            'Exception in get_latest_people(): ' + str(exp))
        return ResponseType('get_latest_people: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    try:
        schema = PersonBriefSchema(many=True)
        retval = schema.dump(people)
    except exceptions.MarshmallowError as exp:
        app.logger.error('get_latest_people schema error: ' + str(exp))
        return ResponseType('get_latest_people: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def person_chiefeditor(person_id: int) -> ResponseType:
    """
    Retrieves the chief editor for a given person ID.

    Args:
        person_id (int): The ID of the person.

    Returns:
        ResponseType: The response object containing the chief editor in JSON
                      format.

    Tests:
        get_chief_editor_empty: Get editor-in-chief info for person with no
                                info.
        get_chief_editor_unknown_id: Try to get editor-in-chief info for
                                     non-existing person.
    """
    session = new_session()

    try:
        person = session.query(Person)\
            .filter(Person.id == person_id)\
            .first()
        if not person:
            app.logger.error(
                f'Person not found. Id = {person_id}.')
            return ResponseType(f'Henkilöä ei löydy. \
                                person_id={person_id}.',
                                HttpResponseCode.BAD_REQUEST.value)

        chiefeditor = session.query(Issue)\
            .join(IssueEditor)\
            .filter(IssueEditor.person_id == person_id)\
            .filter(IssueEditor.issue_id == Issue.id)\
            .first()

    except SQLAlchemyError as exp:
        app.logger.error(exp)
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = IssueSchema()
        retval = schema.dump(chiefeditor)
    except exceptions.MarshmallowError as exp:
        app.logger.error('Schema error: ' + str(exp))
        return ResponseType('Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_person_changes(personid: int) -> ResponseType:
    """
    Retrieves the changes made to the work and its editions with the given ID.

    Args:
        workid: The ID of the work to retrieve changes for.

    Returns:
        ResponseType: The response object containing the list of changes.
    """
    session = new_session()

    try:
        changes = session.query(Log)\
            .filter(Log.table_id == personid,
                    Log.table_name == 'Henkilö')\
            .order_by(Log.id.desc())\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'Db error: {exp}.')
        return ResponseType('get_work_changes: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = LogSchema(many=True)
        retval = schema.dump(changes)
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'Schema error: {exp}.')
        return ResponseType(f'Skeemavirhe: {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    session.close()

    return ResponseType(retval, HttpResponseCode.OK.value)


def get_person_issue_contributions(person_id: int) -> ResponseType:
    """
    Retrieves the contributions of a person to issues.

    Args:
        person_id (int): The ID of the person.

    Returns:
        ResponseType: The response object containing the contributions in JSON
                      format.
    """
    session = new_session()

    try:
        contributions = session.query(Issue)\
            .join(IssueContributor)\
            .filter(IssueContributor.person_id == person_id,
                    IssueContributor.issue_id == Issue.id)\
            .distinct()\
            .all()
    except SQLAlchemyError as exp:
        app.logger.error(f'get_person_issue_contributions exception: {exp}.')
        return ResponseType(f'get_person_issue_contributions tietokantavirhe: \
                            {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        from app.model import IssueContributionSchema
        schema = IssueContributionSchema(many=True)
        retval = schema.dump(contributions)
        app.logger.info(
            f'get_person_issue_contributions: {retval}')
    except exceptions.MarshmallowError as exp:
        app.logger.error(f'get_person_issue_contributions schema error: {exp}.')
        return ResponseType(f'get_person_issue_contributions skeemavirhe: {exp}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)
