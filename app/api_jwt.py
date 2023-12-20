""" JWT authentication stuff. """
import json
from functools import wraps
from typing import Any
from flask import make_response
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.orm_decl import User
from app.route_helpers import new_session
from app.types import HttpResponseCode

# @app.after_request
# def refresh_existing(response: Response) -> Response:
#     try:
#         exp_timestamp = get_jwt()["exp"]
#         now = datetime.now(timezone.utc)
#         target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
#         if target_timestamp > exp_timestamp:
#             access_token = create_access_token(
#                               identity=str(get_jwt_identity()))
#             set_access_cookies(response, access_token)
#         app.logger.info('refresh_existing')
#         return response
#     except (RuntimeError, KeyError):
#         return response


def jwt_admin_required() -> Any:
    """
    Check that user has admin rights.

    Adding this decorator in front of an API end-point means that using that
    end-point requires admin rights.

    If user doesn't have rights, a 401 response is returned.
    """
    def wrapper(f: Any) -> Any:
        """
        A decorator that verifies the JWT in the request and checks if the
        user is an admin.

        Parameters:
            f (Any): The function to be decorated.

        Returns:
            Any: The decorated function.
        """
        @wraps(f)
        def decorator(*args: Any, **kwargs: Any) -> Any:
            verify_jwt_in_request()
            jwt_id = get_jwt_identity()
            session = new_session()
            user = session.query(User).filter_by(id=jwt_id).first()
            if user and user.is_admin:
                return f(*args, **kwargs)
            if user:
                return make_response(
                    json.dumps({'msg':
                                'Toiminto vaatii ylläpitäjän oikeudet'}),
                    HttpResponseCode.FORBIDDEN.value)
            return make_response(
                json.dumps({'msg': 'Ei käyttöoikeutta'}),
                HttpResponseCode.UNAUTHORIZED.value
            )
        return decorator
    return wrapper
