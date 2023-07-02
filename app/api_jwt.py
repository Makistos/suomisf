from flask import make_response  # type: ignore
from flask.wrappers import Response  # type: ignore
from app import jwt
import json
from typing import Any
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity, create_access_token, set_access_cookies  # type: ignore
from functools import wraps
from app.orm_decl import User
import json
from datetime import datetime, timedelta, timezone
from app import app

@app.after_request
def refresh_existing(response: Response) -> Response:
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=str(get_jwt_identity()))
            set_access_cookies(response, access_token)
        app.logger.info('refresh_existing')
        return response
    except (RuntimeError, KeyError):
        return response


def jwt_admin_required() -> Any:
    """
    Check that user has admin rights.

    Adding this decorator in front of an API end-point means that using that
    end-point requires admin rights.

    If user doesn't have rights, a 401 response is returned.
    """
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
    return wrapper
