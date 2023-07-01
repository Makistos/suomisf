from flask import make_response
from flask.wrappers import Response
from app import jwt
import json
from typing import Any, Tuple, NewType, Union, List, Dict, TypedDict
from flask_jwt_extended import get_jwt_identity, jwt_required, verify_jwt_in_request, get_jwt
from functools import wraps
from app.route_helpers import new_session
from app.orm_decl import User
import json


def jwt_admin_required(f: Any) -> Any:
    """
    Check that user has admin rights.

    Adding this decorator in front of an API end-point means that using that
    end-point requires admin rights.

    If user doesn't have rights, a 401 response is returned.
    """
    #@jwt_required(verify_type=False)
    def wrapper(f: Any) -> Any:
        @wraps(f)
        def decorator(*args: Any, **kwargs: Any) -> Any:
            verify_jwt_in_request()
            claims = get_jwt()
            if claims['is_administrator']:
                return f(*args, **kwargs)
            else:
                return make_response(json.dumps({'msg': 'Ei oikeutta toimintoon'}), 401)
        return decorator
    wrapper.__name__ = f.__name__
    return wrapper
