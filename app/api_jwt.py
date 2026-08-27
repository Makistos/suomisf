""" JWT authentication stuff. """
import json
from functools import wraps
from typing import Any, Optional
from flask import make_response
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from app.types import HttpResponseCode
from app import app

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
            try:
                verify_jwt_in_request()
            except Exception as e:
                app.logger.info(
                    f'jwt_admin_required: token verification failed '
                    f'endpoint={f.__name__} error={e}'
                )
                raise
            claims = get_jwt()
            app.logger.info(
                f'jwt_admin_required: endpoint={f.__name__} '
                f'is_administrator={claims.get("is_administrator")} '
                f'role={claims.get("role")} '
                f'name={claims.get("name")}'
            )
            if "is_administrator" not in claims:
                app.logger.info(
                    f'jwt_admin_required: FORBIDDEN for '
                    f'{claims.get("name")} — '
                    f'is_administrator claim missing from token'
                )
            elif not claims["is_administrator"]:
                app.logger.info(
                    f'jwt_admin_required: FORBIDDEN for '
                    f'{claims.get("name")} — '
                    f'is_administrator is False'
                )
            else:
                return f(*args, **kwargs)
            return make_response(
                json.dumps({'msg':
                            'Toiminto vaatii ylläpitäjän oikeudet'}),
                HttpResponseCode.FORBIDDEN.value
            )
        return decorator
    return wrapper


def _user_owns_edition(user_id: int, edition_id: int) -> bool:
    """Check whether user_id has a userbook row for edition_id."""
    from app.orm_decl import UserBook
    from app.route_helpers import new_session
    session = new_session()
    try:
        return session.query(UserBook).filter(
            UserBook.user_id == user_id,
            UserBook.edition_id == edition_id,
        ).first() is not None
    finally:
        session.close()


def _edition_id_for_price(price_id: int) -> Optional[int]:
    """Look up the edition_id an antikvaari_price row belongs to."""
    from app.orm_decl import AntikvaariPrice
    from app.route_helpers import new_session
    session = new_session()
    try:
        row = session.query(AntikvaariPrice.edition_id).filter(
            AntikvaariPrice.id == price_id
        ).first()
        return row[0] if row else None
    finally:
        session.close()


def jwt_admin_or_edition_owner_required(edition_id_kwarg: str = 'edition_id') -> Any:
    """
    Allow admins, or the logged-in user who owns the edition identified by
    the `edition_id_kwarg` URL parameter, to call this endpoint.

    If user doesn't qualify, a 403 response is returned.
    """
    def wrapper(f: Any) -> Any:
        @wraps(f)
        def decorator(*args: Any, **kwargs: Any) -> Any:
            try:
                verify_jwt_in_request()
            except Exception as e:
                app.logger.info(
                    f'jwt_admin_or_edition_owner_required: token verification '
                    f'failed endpoint={f.__name__} error={e}'
                )
                raise
            claims = get_jwt()
            if claims.get('is_administrator'):
                return f(*args, **kwargs)
            edition_id = kwargs.get(edition_id_kwarg)
            user_id = get_jwt_identity()
            if edition_id is not None and user_id is not None \
                    and _user_owns_edition(int(user_id), int(edition_id)):
                return f(*args, **kwargs)
            app.logger.info(
                f'jwt_admin_or_edition_owner_required: FORBIDDEN for '
                f'{claims.get("name")} on edition={edition_id} '
                f'endpoint={f.__name__}'
            )
            return make_response(
                json.dumps({'msg':
                            'Toiminto vaatii ylläpitäjän oikeudet tai '
                            'painoksen omistuksen'}),
                HttpResponseCode.FORBIDDEN.value
            )
        return decorator
    return wrapper


def jwt_admin_or_price_owner_required(price_id_kwarg: str = 'price_id') -> Any:
    """
    Allow admins, or the logged-in user who owns the edition that a stored
    antikvaari_price row (identified by the `price_id_kwarg` URL parameter)
    belongs to, to call this endpoint.

    If user doesn't qualify, a 403 response is returned.
    """
    def wrapper(f: Any) -> Any:
        @wraps(f)
        def decorator(*args: Any, **kwargs: Any) -> Any:
            try:
                verify_jwt_in_request()
            except Exception as e:
                app.logger.info(
                    f'jwt_admin_or_price_owner_required: token verification '
                    f'failed endpoint={f.__name__} error={e}'
                )
                raise
            claims = get_jwt()
            if claims.get('is_administrator'):
                return f(*args, **kwargs)
            price_id = kwargs.get(price_id_kwarg)
            user_id = get_jwt_identity()
            edition_id = _edition_id_for_price(int(price_id)) if price_id is not None else None
            if edition_id is not None and user_id is not None \
                    and _user_owns_edition(int(user_id), edition_id):
                return f(*args, **kwargs)
            app.logger.info(
                f'jwt_admin_or_price_owner_required: FORBIDDEN for '
                f'{claims.get("name")} on price={price_id} '
                f'endpoint={f.__name__}'
            )
            return make_response(
                json.dumps({'msg':
                            'Toiminto vaatii ylläpitäjän oikeudet tai '
                            'painoksen omistuksen'}),
                HttpResponseCode.FORBIDDEN.value
            )
        return decorator
    return wrapper
