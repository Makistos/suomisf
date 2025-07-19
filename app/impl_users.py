""" Functions related to users. """
import json
from typing import Dict
from flask.wrappers import Response
from flask import make_response, jsonify
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                get_jwt_identity)
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import (User)
from app.model import (UserSchema)
from app.impl import ResponseType
from app.types import (HttpResponseCode)
from app import app


def create_token(user: User, password: str) -> Response:
    """
    Creates a token for the given username.

    Args:
        user (User): The user for which to create the token.
        password (str): The password of the user.

    Returns:
        Response: The response containing the access token, refresh token,
                  user name, role, and user ID. If the login fails, a response
                  with a code of 401 and an error message is returned.
    """
    token = user.validate_user(password)
    if token:
        if user.is_admin:
            role = 'admin'
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={"is_administrator": True,
                                   "role": "admin",
                                   "name": user.name})
        elif user.name == 'demo_admin':
            role = 'demo_admin'
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={"is_administrator": True,
                                   "role": "demo_admin",
                                   "name": user.name})
        else:
            role = 'user'
            access_token = create_access_token(
                identity=str(user.id),
                additional_claims={"is_administrator": False,
                                   "role": "user",
                                   "name": user.name})
        refreshtoken = create_refresh_token(identity=str(user.id))
        data = jsonify(access_token=access_token,
                       refresh_token=refreshtoken,
                       name=user.name,
                       role=role,
                       id=user.id)
        resp = make_response(data, HttpResponseCode.OK.value)
        resp.headers['Content-Type'] = 'application/json'
        return resp

    app.logger.warning(f'Failed login for {user.name}.')
    return make_response(
        json.dumps({'msg': 'Väärä salasana'}),
        HttpResponseCode.UNAUTHORIZED.value)


def login_user(options: Dict[str, str]) -> Response:
    """
    Logs in a user with the provided options.

    Args:
        options (Dict[str, str]): A dictionary containing the user's login
                                  options.
            - 'username' (str): The username of the user.
            - 'password' (str): The password of the user.

    Returns:
        Response: The response containing the token for the logged-in user.
    """
    session = new_session()
    name = options['username']
    password = options['password']

    user = session.query(User).filter(User.name == name).first()
    if not user:
        return make_response(
            json.dumps({'msg': 'Tuntematon käyttäjä'}),
            HttpResponseCode.UNAUTHORIZED.value)

    resp = create_token(user, password)
    return resp


def register_user(options: Dict[str, str]) -> Response:
    """
    Registers a new user with the provided options.

    Args:
        options (Dict[str, str]): A dictionary containing the user's
                                    registration options.
                - 'username' (str): The username of the user.
                - 'password' (str): The password of the user.
    Returns:
        Response: The response containing the token for the registered user.
    """
    session = new_session()
    name = options['username']
    password = options['password']

    user = session.query(User).filter(User.name == name).first()
    if user:
        return make_response(
            json.dumps({'msg': 'Käyttäjä on jo olemassa'}),
            HttpResponseCode.UNAUTHORIZED.value)

    user = User(name=name)  # type: ignore
    user.set_password(password)
    try:
        session.add(user)
        session.commit()
    except SQLAlchemyError as exp:
        app.logger.error('RegisterUser: ' + str(exp))
        return make_response(
            json.dumps({'msg': 'Tietokantavirhe'}),
            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    resp = create_token(user, password)
    return resp


def refresh_token(options: Dict[str, str]) -> Response:
    """
    Refreshes the access token and returns a response.

    Args:
        options (Dict[str, str]): A dictionary containing options for
                                  refreshing the token.

    Returns:
        Response: The response object containing the access token and other
                  information.
    """
    session = new_session()
    userid = get_jwt_identity()
    user = session.query(User).filter_by(id=userid).first()
    if not user or user.name != options['username']:
        return make_response(
            json.dumps({'msg': f'Tuntematon käyttäjä \
                            {options["username"]}'}),
            HttpResponseCode.UNAUTHORIZED.value)
    if user.is_admin:
        role = 'admin'
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"is_administrator": True,
                               "role": "admin",
                               "name": user.name})
    elif user.name == 'demo_admin':
        role = 'admin'
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"is_administrator": True,
                               "role": "demo_admin",
                               "name": user.name})
    else:
        role = 'user'
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={"is_administrator": False,
                               "role": "user",
                               "name": user.name})
    refreshtoken = create_refresh_token(identity=str(user.id))
    data = jsonify(access_token=access_token,
                   refresh_token=refreshtoken,
                   name=user.name,
                   role=role,
                   id=user.id)
    resp = make_response(data, HttpResponseCode.OK.value)
    return resp


def get_user(user_id: int) -> ResponseType:
    """
    Retrieves a user from the database based on the specified user ID.

    Parameters:
        user_id (int): The ID of the user to retrieve.

    Returns:
        ResponseType: The response object containing the user data if found, or
                      an error message if not found or an exception occurred.
    """
    session = new_session()
    try:
        user = session.query(User)\
            .filter(User.id == user_id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetUser: ' + str(exp))
        return ResponseType(f'GetUser: Tietokantavirhe. id={user_id}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    if not user:
        app.logger.error(f'GetUser: Unknown user {user_id}.')
        return ResponseType(f'Käyttäjää ei löytynyt. id={user_id}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = UserSchema()
        retval = schema.dump(user)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetUser schema error: ' + str(exp))
        return ResponseType('GetUser: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(retval, HttpResponseCode.OK.value)


def list_users() -> ResponseType:
    """
    Retrieves a list of all users from the database.

    Returns:
        ResponseType: The response object containing the list of users if
                      successful, or an error message and status code if an
                      error occurs.
    """
    session = new_session()

    try:
        users = session.query(User).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListUsers: ' + str(exp))
        return ResponseType('ListUsers: Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    try:
        schema = UserSchema(many=True)
        retval = schema.dump(users)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListUsers schema error: ' + str(exp))
        return ResponseType('ListUsers: Skeemavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    return ResponseType(retval, HttpResponseCode.OK.value)


def user_genres(user_id: int) -> ResponseType:
    """
    Retrieves the genre counts associated with the specified user.

    Parameters:
        user_id (int): The ID of the user whose genres to retrieve.

    Returns:
        ResponseType: The response object containing the list of genres if
                      successful, or an error message and status code if an
                      error occurs.
    """
    session = new_session()
    try:
        # genres = session.query(Genre.name, Genre.abbr, Genre.id,
        #                        func.count(Genre.id).label("count"))\
        #     .join(WorkGenre)\
        #     .filter(WorkGenre.work_id == Work.id)\
        #     .join(Work)\
        #     .filter(Work.id == WorkGenre.work_id)\
        #     .join(Part)\
        #     .filter(Part.work_id == Work.id)\
        #     .join(Edition)\
        #     .filter(Edition.id == Part.edition_id)\
        #     .join(UserBook)\
        #     .filter(UserBook.user_id == user_id)\
        #     .filter(UserBook.edition_id == Edition.id)\
        #     .group_by(Genre.id)\
        #     .all()
        stmt = 'SELECT genre.name, genre.abbr, genre.id, '
        stmt += 'count(work.id) as count '
        stmt += 'FROM genre '
        stmt += 'INNER JOIN workgenre ON workgenre.genre_id = genre.id '
        stmt += 'INNER JOIN work ON work.id = workgenre.work_id '
        stmt += 'INNER JOIN part ON part.work_id = work.id '
        stmt += 'and part.shortstory_id is null '
        stmt += 'INNER JOIN edition ON edition.id = part.edition_id '
        stmt += 'INNER JOIN userbook ON userbook.edition_id = edition.id '
        stmt += f'WHERE userbook.user_id = {user_id} '
        stmt += 'GROUP BY genre.id, genre.name, genre.abbr'
        genres = session.execute(stmt).all()
    except SQLAlchemyError as exp:
        app.logger.error(f"user_genres: {str(exp)}")
        return ResponseType("user_genres: Tietokantavirhe.",
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    retval = []
    if genres:
        for genre in genres:
            retval.append({'count': int(genre['count']),
                           'abbr': str(genre['abbr']),
                           'id': int(genre['id']),
                           'name': str(genre['name'])})

    return ResponseType(retval, HttpResponseCode.OK.value)
