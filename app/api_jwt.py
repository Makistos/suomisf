from flask import make_response
from flask.wrappers import Response
from app import jwt
import json
from typing import Any, Tuple, NewType, Union, List, Dict, TypedDict
from flask_jwt_extended import get_jwt_identity, jwt_required
from functools import wraps
from app.route_helpers import new_session
from app.orm_decl import User
import json


def user_is_admin(id: int) -> bool:
    session = new_session()
    user = session.query(User).filter(User.id == id).first()

    if not user:
        return False
    return bool(user.is_admin)


@jwt.unauthorized_loader
def unauthorized_callback(callback):
    resp = make_response(json.dumps({'code': 401,
                                     'message': 'Ei oikeutta'}), 401)
    return resp


@jwt.expired_token_loader
def expired_token_callback(callback):
    resp = make_response(json.dumps({'code': 401,
                                     'message': 'Istunto on vanhentunut'}), 401)
    return resp


@jwt.invalid_token_loader
def invalid_token_callback(callback):
    resp = make_response(json.dumps({'code': 401,
                                     'message': 'Virheellinen kirjautuminen'}), 401)
    return resp


def jwt_admin_required(f: Any) -> Any:
    """
    Check that user has admin rights.

    Adding this decorator in front of an API end-point means that using that
    end-point requires admin rights.

    If user doesn't have rights, a 401 response is returned.
    """
    @jwt_required(verify_type=False)
    @wraps(f)
    def wrap(*args: Any, **kwargs: Any) -> Any:
        user_id = get_jwt_identity()
        if user_is_admin(user_id):
            return f(*args, **kwargs)
        else:
            return make_response(json.dumps({'msg': 'Ei oikeutta toimintoon'}), 401)

    return wrap
