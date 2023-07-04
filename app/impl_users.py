import json
from typing import Dict, Tuple
from flask.wrappers import Response
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, get_jwt_identity, get_jwt)
from flask import make_response, jsonify
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions
from app.route_helpers import new_session
from app.orm_decl import (User)
from app.model import (UserSchema)
from app.impl import ResponseType
from app import app


def create_token(username: str) -> Response:
    session = new_session()
    user = session.query(User).filter(User.name == username).first()
    token = user.validate_user(user.password_hash)
    if token:
        if user.is_admin:
            role = 'admin'
            access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": True, "role": "admin", "name": user.name})
        elif user.name == 'demo_admin':
            role = 'demo_admin'
            access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": True, "role": "demo_admin", "name": user.name})
        else:
            role = 'user'
            access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": False, "role": "user", "name": user.name})
        refresh_token = create_refresh_token(identity=str(user.id))
        #data = json.dumps({'access_token': access_token, 'refresh_token': refresh_token, 'role': role})
        data = jsonify(access_token=access_token,
                        refresh_token=refresh_token,
                        user=user.name,
                        role=role,
                        id=user.id)
        resp = make_response(data, 200)
        resp.headers['Content-Type'] = 'application/json'
        return resp

    app.logger.warn('Failed login for {name}.')
    return make_response(
        json.dumps({'code': 401,
                    'message': 'Kirjautuminen ei onnistunut'}), 401)

def LoginUser(options: Dict[str, str]) -> Response:
    session = new_session()
    name = options['username']
    password = options['password']

    user = session.query(User).filter(User.name == name).first()

    resp = create_token(user.name)
    return resp
    #     token = user.validate_user(password)
    #     if token:
    #         if user.is_admin:
    #             role = 'admin'
    #             access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": True})
    #         elif user.name == 'demo_admin':
    #             role = 'demo_admin'
    #             access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": True})
    #         else:
    #             role = 'user'
    #             access_token = create_access_token(identity=str(user.id))
    #         refresh_token = create_refresh_token(identity=str(user.id))
    #         # data = json.dumps({'role': role,
    #         #                    'name': user.name,
    #         #                    'id': user.id,
    #         #                    'accessToken': access_token,
    #         #                    'refreshToken': refresh_token})
    #         data = jsonify(access_token=access_token,
    #                        refresh_token=refresh_token,
    #                        user=user.name,
    #                        role=role,
    #                        id=user.id)
    #         resp = make_response(data, 200)
    #         # set_access_cookies(resp, access_token)
    #         # set_refresh_cookies(resp, refresh_token)


    # app.logger.warn('Failed login for {name}.')
    # return make_response(
    #     json.dumps({'code': 401,
    #                 'message': 'Kirjautuminen ei onnistunut'}), 401)

#@jwt_required(refresh=True)  # type: ignore
def RefreshToken(options: Dict[str, str]) -> Response:
    session = new_session()
    userid = get_jwt_identity()
    user = session.query(User).filter_by(id=userid).first()
    if not user:
        return make_response(
            json.dumps({'code': 401,
                        'message': 'Tuntematon käyttäjä'}), 401)
    if user.is_admin:
        role = 'admin'
        access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": True, "role": "admin", "name": user.name})
    elif user.name == 'demo_admin':
        role = 'admin'
        access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": True, "role": "demo_admin", "name": user.name})
    else:
        role = 'user'
        access_token = create_access_token(identity=str(user.id), additional_claims={"is_administrator": False, "role": "user", "name": user.name})
    refresh_token = create_refresh_token(identity=str(user.id))
    data = jsonify(access_token=access_token,
                    refresh_token=refresh_token,
                    user=user.name,
                    role=role,
                    id=user.id)
    resp = make_response(data, 200)
    return resp


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
