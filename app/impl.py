import json
from os import sched_get_priority_max

from flask.globals import session

from app.route_helpers import new_session
from app.orm_decl import (Issue, Magazine, Publisher, User, Work)
from app.model import (IssueSchema, MagazineSchema,
                       PublisherSchema, UserSchema, WorkSchema)
from app import ma


def GetIssueForMagazine(options):
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


def PostIssue(options):
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


def UpdateIssue(options, body):
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


def GetIssueArticles(options):
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


def GetIssue(options):
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
    return schema.dump(issue), 200


def GetIssueShorts(options):
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


def GetIssueTags(options):
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


def ListMagazines():
    """

    """
    session = new_session()

    magazines = session.query(Magazine).all()
    schema = MagazineSchema()

    retval = json.dumps([schema.dump(x) for x in magazines])
    return retval, 200
    # return schema.dump(magazines), 200

    # Implement your business logic here
    # All the parameters are present in the options argument


def GetMagazine(options):
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


def UpdateMagazine(options, body):
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["magazineId"]: ID of the magazine

    :param body: The parsed body of the request
    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return '', 200


def GetMagazineIssues(options):
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


def GetMagazinePublisher(options):
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


def GetMagazineTags(options):
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


def GetPublisher(options):
    session = new_session()

    publisher = session.query(Publisher)\
                       .filter(Publisher.id == options['publisherId'])\
                       .first()
    schema = PublisherSchema()

    return schema.dump(publisher), 200


def ListUser(options):
    """
    :param options: A dictionary containing all the paramters for the Operations
        options["id"]: ID of the user

    """

    # Implement your business logic here
    # All the parameters are present in the options argument

    return json.dumps({
        "id": "<int64>",
        "name": "<string>",
        "uri": "<string>",
    }), 200


def GetUser(options):
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


def ListWork(options):
    session = new_session()
    work = session.query(Work).filter(Work.id == options['workId']).first()
    schema = WorkSchema()
    return schema.dump(work), 200
