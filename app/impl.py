import datetime
import decimal
import json
from operator import ne
from os import sched_get_priority_max
from flask.globals import session
from flask.wrappers import Response

from app.route_helpers import new_session
from app.orm_decl import (Article, Country, Issue, Magazine, Person,
                          Publisher, ShortStory, User, Work)
from app.model import (ArticleSchema, CountryBriefSchema, CountrySchema, IssueSchema, MagazineSchema,
                       PersonBriefSchema, PersonSchema,
                       PublisherSchema, ShortSchema, UserSchema, WorkSchema)
from app import ma
from typing import Dict, Tuple, List


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
    schema = PublisherSchema()

    return schema.dump(publisher), 200


def alchemyencoder(obj):
    """JSON encoder function for SQLAlchemy special classes."""
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)


def ListPeople() -> Tuple[str, int]:
    session = new_session()

    people = session.query(Person).filter(Person.id < 500).all()
    #retval = json.dumps([dict(x) for x in people], default=alchemyencoder)
    schema = PersonBriefSchema()
    retval = json.dumps([schema.dump(x) for x in people])
    #retval = tuple(schema.dump(people))
    return retval, 200


def GetPerson(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()
    person = session.query(Person).filter(
        Person.id == options['personId']).first()
    schema = PersonBriefSchema()
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


def ListWork(options: Dict[str, str]) -> Tuple[str, int]:
    session = new_session()
    work = session.query(Work).filter(Work.id == options['workId']).first()
    schema = WorkSchema()
    return schema.dump(work), 200


def ListCountries() -> Tuple[str, str]:
    session = new_session()
    countries = session.query(Country).all()
    schema = CountrySchema()
    retval = json.dumps([schema.dump(x) for x in countries])
    return retval, 200
