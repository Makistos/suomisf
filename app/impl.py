import time
import datetime
import decimal
import json
#from marshmallow import Schema, fields

from operator import and_, ne, or_, not_
from os import sched_get_priority_max
from webbrowser import get
from flask.globals import session
from flask.wrappers import Response
from sqlalchemy import inspect, func
from app.api_errors import APIError
from app.route_helpers import new_session
from app.orm_decl import (Alias, Article, Bookseries, ContributorRole, Country, Issue, Magazine, Person,
                          Publisher, ShortStory, User, Work, Log, Pubseries)
from app.model import (ArticleSchema, BookseriesSchema, CountryBriefSchema, CountryBriefSchema, IssueSchema, MagazineSchema,
                       PersonBriefSchema, PersonSchema, LogSchema,
                       PublisherBriefSchema, ShortSchema, UserSchema, WorkSchema, PubseriesSchema)
#from app import ma
from typing import Dict, Tuple, List, Union, Any, TypedDict
from app import app
from collections import Counter


class SearchResultFields(TypedDict):
    id: str
    img: str
    header: str
    description: str
    type: str
    score: int


SearchResult = List[SearchResultFields]
SearchResults = Dict[str, SearchResult]


def LoginUser(options: Dict[str, str]) -> Tuple[str, int]:

    session = new_session()
    name = options['username']
    password = options['password']

    user = session.query(User).filter(User.name == name).first()

    if user:
        token = user.validate_user(password)
        if token:
            if user.is_admin:
                role = 'admin'
            elif user.name == 'demo_admin':
                role = 'demo_admin'
            else:
                role = 'user'
            return json.dumps({'username': user.name,
                               'role': role,
                               'accessToken': token}), 200
    return json.dumps({'code': 401,
                       'message': 'Kirjautuminen ei onnistunut'}), 401


def GetArticle(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()

    article = session.query(Article).filter(
        Article.id == options['articleId']).first()

    schema = ArticleSchema()
    retval = schema.dump(article)
    return schema.dump(article), 200


def GetBookseries(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()

    bookseries = session.query(Bookseries).filter(
        Bookseries.id == options['bookseriesId']).first()

    schema = BookseriesSchema()
    retval = schema.dump(bookseries)
    return schema.dump(bookseries), 200


def GetPubseries(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()

    pubseries = session.query(Pubseries).filter(
        Pubseries.id == options['pubseriesId']).first()

    schema = PubseriesSchema()
    retval = schema.dump(pubseries)
    return schema.dump(pubseries), 200


def GetShort(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()

    short = session.query(ShortStory).filter(
        ShortStory.id == options['shortId']).first()

    schema = ShortSchema()
    retval = schema.dump(short)
    return schema.dump(short), 200


def GetIssueForMagazine(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id of issue

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps({
        "count": "<integer>",
        "id": "<integer>",
        "link": "<string>",
        "magazine": "<Magazine>",
        "notes": "<string>",
        "number": "<integer>",
        "numberExtra": "<string>",
        "pages": "<integer>",
        "size": "<string>",
        "title": "<string>",
        "uri": "<string>",
        "year": "<integer>",
    }), 200


def PostIssue(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id of issue

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps({
        "count": "<integer>",
        "id": "<integer>",
        "link": "<string>",
        "magazine": "<Magazine>",
        "notes": "<string>",
        "number": "<integer>",
        "numberExtra": "<string>",
        "pages": "<integer>",
        "size": "<string>",
        "title": "<string>",
        "uri": "<string>",
        "year": "<integer>",
    }), 200


def UpdateIssue(options: Dict[str, str], body: List[str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id of issue

    :param body: The parsed body of the request
    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps({
        "count": "<integer>",
        "id": "<integer>",
        "link": "<string>",
        "magazine": "<Magazine>",
        "notes": "<string>",
        "number": "<integer>",
        "numberExtra": "<string>",
        "pages": "<integer>",
        "size": "<string>",
        "title": "<string>",
        "uri": "<string>",
        "year": "<integer>",
    }), 200


def GetIssueArticles(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id for issue

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps([{
        "authors": "<array>",
        "id": "<integer>",
        "issue": "<Issue>",
        "peopleInArticle": "<array>",
        "title": "<string>",
    }]), 200


def GetIssue(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id for issue

    """

    # Implement your business logic here
    # All the parameters are present in the options argument
    session = new_session()
    issue = session.query(Issue)\
                   .filter(Issue.id == options['issueId'])\
                   .first()
    schema = IssueSchema()
    retval = schema.dump(issue)
    return schema.dump(issue), 200


def GetIssueShorts(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id for issue

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps([{
        "authors": "<array>",
        "id": "<integer>",
        "orig_title": "<string>",
        "pubyear": "<integer>",
        "title": "<string>",
    }]), 200


def GetIssueTags(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["issueId"]: Id for issue

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps([{
        "id": "<integer>",
        "name": "<string>",
        "uri": "<string>",
    }]), 200


def ListMagazines() -> Tuple[str, int]:
    """

    """
    session = new_session()

    magazines = session.query(Magazine).all()
    retval = []
    for magazine in magazines:
        retval.append({'id': magazine.id, 'name': magazine.name})
    return json.dumps(retval), 200


def GetMagazine(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["magazineId"]: ID of the magazine

    """

    # Implement your business logic here
    # All the parameters are present in the options argument
    session = new_session()

    magazine = session.query(Magazine)\
                      .filter(Magazine.id == options['magazineId'])\
                      .first()
    schema = MagazineSchema()

    retval = schema.dump(magazine)
    return schema.dump(magazine), 200

    # return json.dumps({
    #     "description": "<string>",
    #     "id": "<integer>",
    #     "issn": "<string>",
    #     "issues": "<array>",
    #     "link": "<string>",
    #     "name": "<string>",
    #     "type": "<integer>",
    #     "uri": "<string>",
    # }), 200


def UpdateMagazine(options: Dict[str, str], body: List[str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["magazineId"]: ID of the magazine

    :param body: The parsed body of the request
    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return '', 200


def GetMagazineIssues(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["magazineId"]: ID of the magazine

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps([{
        "count": "<integer>",
        "id": "<integer>",
        "link": "<string>",
        "magazine": "<Magazine>",
        "notes": "<string>",
        "number": "<integer>",
        "numberExtra": "<string>",
        "pages": "<integer>",
        "size": "<string>",
        "title": "<string>",
        "uri": "<string>",
        "year": "<integer>",
    }]), 200


def GetMagazinePublisher(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["magazineId"]: ID of the magazine

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps({
        "Magazines": "<array>",
        "description": "<string>",
        "fullname": "<string>",
        "id": "<integer>",
        "name": "<string>",
        "uri": "<string>",
    }), 200


def GetMagazineTags(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["magazineId"]: ID of the magazine

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps([{
        "id": "<integer>",
        "name": "<string>",
        "uri": "<string>",
    }]), 200


def GetPublisher(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()

    publisher = session.query(Publisher)\
                       .filter(Publisher.id == options['publisherId'])\
                       .first()
    schema = PublisherBriefSchema()

    return schema.dump(publisher), 200


def alchemyencoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)


def _strMatchMode(value: str, mode: str) -> str:
    if mode == 'startsWith':
        return value + '%'
    if mode == 'contains':
        return '%' + value + '%'
    if mode == 'notContains':
        return ''
    if mode == 'endsWith':
        return '%' + value


person_relationships = {'nationality': 'name',
                        'roles': 'name'}


def filter_person_query(table: Any,
                        query: Any,
                        key: str,
                        raw_filters: Dict[str, Any],
                        related_table: Any = None) -> Any:
    op = raw_filters['matchMode']
    value = raw_filters['value']
    if key in person_relationships:
        column = getattr(table, key, None)
        related_key = person_relationships[key]
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


_allowed_person_fields = ['name', 'dob', 'dod',
                          'nationality',
                          'workcount', 'storycount',
                          'roles',
                          'global']


def ListPeople(params: Dict[str, Any]) -> Tuple[str, int]:
    d: Dict[str, Union[int, List[str]]] = {}
    retval: Tuple[str, int]
    session = new_session()
    people = session.query(Person)
    value = "Suomi"
    # Filter
    for field, filters in params.items():
        if type(filters) is dict:
            if field not in _allowed_person_fields:
                raise APIError('Invalid filter field %s' % field, 405)
            if filters['value']:
                if field == 'nationality':
                    people = filter_person_query(
                        Person, people, field, filters, Country)
                elif field == 'roles':
                    people = filter_person_query(
                        Person, people, field, filters, ContributorRole)
                else:
                    people = filter_person_query(
                        Person, people, field, filters)
    count = len(people.all())

    # Sort
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
    schema = PersonBriefSchema(many=True)
    d['people'] = schema.dump(people)
    d['totalRecords'] = count
    retval = json.dumps(d)
    return retval, 200


def GetPerson(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()
    person_id = options['personId']
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
        return "Unknown person", 401
    schema = PersonSchema()
    retval = schema.dump(person)
    return retval, 200


def ListUsers() -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["id"]: ID of the user

    """

    # Implement your business logic here
    # All the parameters are present in the options argument
    session = new_session()

    users = session.query(User).all()
    schema = UserSchema()
    retval = json.dumps([schema.dump(x) for x in users])
    return retval, 200


def GetUser(options: Dict[str, str]) -> Tuple[str, int]:
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["userId"]: ID of user

    """

    session = new_session()
    user = session.query(User)\
        .filter(User.id == options['userId'])\
        .first()
    schema = UserSchema()
    return schema.dump(user), 200


def GetWork(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()
    work = session.query(Work).filter(Work.id == options['workId']).first()
    schema = WorkSchema()
    return schema.dump(work), 200


def GetWorksByAuthor(author: str) -> Tuple[str, int]:
    session = new_session()


def ListCountries() -> Tuple[str, str]:
    session = new_session()
    countries = session.query(Country).all()
    schema = CountryBriefSchema(many=True)
    retval = json.dumps(schema.dump(countries))
    return retval, 200


PERSON_NAME = 20
PERSON_OTHER = 10
WORK_TITLE = 19
WORK_OTHER = 9
STORY_NAME = 18
STORY_OTHER = 8
ARTICLE_TITLE = 17
ARTICLE_OTHER = 7
PUBLISHER_NAME = 16
PUBLISHER_OTHER = 6


def searchScore(table: str, item, word: str) -> int:
    retval: int = 0

    if table == 'work':
        if word in item.title.lower():
            return WORK_TITLE
        else:
            return WORK_OTHER
    if table == 'person':
        if item.fullname:
            if word in item.fullname.lower():
                return PERSON_NAME
        if item.name:
            if word in item.name.lower():
                return PERSON_NAME
        if item.alt_name.lower():
            if word in item.alt_name:
                return PERSON_NAME
        else:
            return PERSON_OTHER
    return retval


def SearchWorks(session: Any, searchwords: List[str]) -> SearchResult:
    retval: SearchResult = []
    found_works: Dict[int, SearchResultFields] = {}

    for searchword in searchwords:
        works = session.query(Work)\
            .filter(Work.title.ilike('%' + searchword + '%') |
                    Work.subtitle.ilike('%' + searchword + '%') |
                    Work.orig_title.ilike('%' + searchword + '%') |
                    Work.misc.ilike('%' + searchword + '%') |
                    Work.description.ilike('%' + searchword + '%')) \
            .order_by(Work.title)\
            .all()

        for work in works:
            if work.id in found_works:
                found_works[work.id]['score'] *= searchScore(
                    'work', work, searchword)
            else:
                if work.description:
                    description = work.description
                else:
                    description = ''

                item: SearchResultFields = {
                    'id': work.id,
                    'img': '',
                    'header': work.title,
                    'description': description,
                    'type': 'work',
                    'score': searchScore('work', work, searchword)
                }
                found_works[work.id] = item
        retval = [value for _, value in found_works.items()]
        # for key, item in found_works:
        #     retval.append(item)

    return retval


def SearchPeople(session, searchwords: List[str]) -> SearchResult:
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


def GetChanges(params: Dict[str, Any]) -> Tuple[str, int]:
    # Get changes made to the database.
    #
    # Defaults to all changes made in the last 30 days.
    #
    retval = ''
    period_length: int = 30
    session = new_session()
    if 'period' in params:
        try:
            period_length = int(params['period'])
        except TypeError as exp:
            raise APIError

    cutoff_date = datetime.datetime.now() - datetime.timedelta(period_length)
    changes = session.query(Log).filter(
        Log.date >= cutoff_date).order_by(Log.date.desc()).all()
    schema = LogSchema(many=True)
    retval = schema.dump(changes)

    return retval, 200


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
