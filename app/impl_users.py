import json
from typing import Dict, Tuple
from flask.wrappers import Response
from flask_jwt_extended import (create_access_token, create_refresh_token)
from flask import make_response
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import (User)
from app.model import (UserSchema)
from app.impl import ResponseType
from app import app


def LoginUser(options: Dict[str, str]) -> Response:
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
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            data = json.dumps({'role': role,
                               'name': user.name,
                               'id': user.id,
                               'accessToken': access_token,
                               'refreshToken': refresh_token})
            resp = make_response(data, 200)
            # set_access_cookies(resp, access_token)
            # set_refresh_cookies(resp, refresh_token)

            return resp

    app.logger.warn('Failed login for {name}.')
    return make_response(
        json.dumps({'code': 401,
                    'message': 'Kirjautuminen ei onnistunut'}), 401)


def GetUser(id: int) -> ResponseType:
    session = new_session()
    try:
        user = session.query(User)\
            .filter(User.id == id)\
            .first()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in GetUser: ' + str(exp))
        return ResponseType(f'GetUser: Tietokantavirhe. id={id}', 400)

    if not user:
        app.logger.error(f'GetUser: Unknown user {id}.')
        return ResponseType(f'Käyttäjää ei löytynyt. id={id}.', 400)

    try:
        schema = UserSchema()
        retval = schema.dump(user)
    except exceptions.MarshmallowError as exp:
        app.logger.error('GetUser schema error: ' + str(exp))
        return ResponseType('GetUser: Skeemavirhe.', 400)

    return ResponseType(retval, 200)


def ListUsers() -> ResponseType:
    session = new_session()

    try:
        users = session.query(User).all()
    except SQLAlchemyError as exp:
        app.logger.error('Exception in ListUsers: ' + str(exp))
        return ResponseType('ListUsers: Tietokantavirhe.', 400)

    try:
        schema = UserSchema(many=True)
        retval = schema.dump(users)
    except exceptions.MarshmallowError as exp:
        app.logger.error('ListUsers schema error: ' + str(exp))
        return ResponseType('ListUsers: Skeemavirhe.', 400)
    return ResponseType(retval, 200)
