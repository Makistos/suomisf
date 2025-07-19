###
# Role related functions

from flask import Response
from app import app
from app.api_helpers import make_api_response
from app.impl import role_list, role_get


@app.route('/api/roles/', methods=['get'])
def api_roles() -> Response:
    """
    Returns a list of contributor roles in the system in the order they are
    in the database (i.e. by id).
    """
    return make_api_response(role_list())


@app.route('/api/roles/<target>', methods=['get'])
def api_role(target: str) -> Response:
    """
    Return a list of roles for a given target.

    Parameters:
        target (str): Target to request roles for, either 'work', 'short',
                      'edition' or 'issue.

    Returns:
        Response: Requested roles.
    """
    return make_api_response(role_get(target))
