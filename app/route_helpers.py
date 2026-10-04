"""
    This module contains the functions related to routes that are not directly
    route definitions.
"""

from typing import List, Dict, Any, Optional, Tuple, Set, Union
from functools import wraps
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from flask_login import current_user  # type: ignore
from flask import abort, g, has_app_context
from app import app, db_url


def new_session() -> Any:
    ''' Create a new SQLAlchemy database session handle.

    Sessions created while handling a request are closed automatically when
    the request ends (see close_request_sessions), so callers don't need to
    close them. Outside a request (scripts), the caller must close it.

    Returns:
        Any: Session handler.
    '''
    engine = create_engine(db_url, poolclass=NullPool)
    # engine = create_engine(db_url, poolclass=NullPool, echo=True)
    # app.config['SQLALCHEMY_DATABASE_URI'], poolclass=NullPool)
    session_obj = sessionmaker(bind=engine)
    session = session_obj()
    if has_app_context():
        g.setdefault('db_sessions', []).append(session)
    return session


@app.teardown_appcontext
def close_request_sessions(_exc: Optional[BaseException]) -> None:
    ''' Close every session new_session() handed out during the request.

    Most callers never closed their session; with NullPool each one held a
    PostgreSQL connection until garbage collection, which ran the server
    out of connection slots under concurrent load.
    '''
    for session in g.pop('db_sessions', []):
        session.close()


def admin_required(f: Any) -> Any:
    """
    Decorator that checks if the current user is an admin before allowing
    access to a function.

    Parameters:
        f (Any): The function to be wrapped.

    Returns:
        Any: The wrapped function.

    Raises:
        HTTPException: If the current user is not an admin (status code 401).
    """
    @wraps(f)
    def wrap(*args: Any, **kwargs: Any) -> Any:
        if current_user.is_admin:
            return f(*args, **kwargs)
        abort(401)
    return wrap


table_locals = {'article': 'Artikkeli',
                'edition': 'Painos',
                'issue': 'Irtonumero',
                'magazine': 'Lehti',
                'person': 'Henkilö',
                'publisher': 'Kustantaja',
                'shortstory': 'Novelli',
                'work': 'Teos'}


def get_select_ids(form: Any, item_field: str = 'itemId') -> Tuple[int, List[Dict[str, str]]]:
    ''' Read parameters from  a front end request for a select component.

        Each request has the parent id (work id etc) and a list of item ids
        corresponding to the items selected in a select component. This
        function parses these fields and returns parent id and a list containing
        the ids as ints.

        Args:
            form (request.form): Form that contains the values.
            item_field (str): Name for the parent id field. Default: "itemId".

        Returns:
            Tuple[int, List[int]]: A tuple of parent id and list of item ids.
    '''
    if ('items' not in form or item_field not in form):
        abort(400)

    parentid = int(json.loads(form[item_field]))
    items = json.loads(form['items'])
    # items = {int(x['id']): x['text']} for x in items]

    return(parentid, items)


def get_join_changes(existing: Union[List[int], Set[int]],
                     new: List[int]) -> Tuple[List[int], List[int]]:
    to_add: List[int] = new
    to_delete: List[int] = []

    if existing:
        for id in existing:
            if id in new:
                to_add.remove(id)
            else:
                to_delete.append(id)

    return (to_add, to_delete)

# ArticleTag.article


# Called when a person's name field is changed. This requires updating all
# author strings in works.
