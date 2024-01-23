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
                       user=user.name,
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
                   user=user.name,
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
