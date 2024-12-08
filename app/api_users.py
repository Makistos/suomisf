"""
API functions related to users.
"""
from flask import Response
from app import app

from app.api_helpers import make_api_response
from app.impl_users import user_genres


@app.route('/api/users/<userid>/stats/genres', methods=['get'])
def api_userstatsgenres(userid: str) -> Response:
    """
    Retrieves the genre counts associated with the specified user.

    Parameters:
        userid (str): The ID of the user whose genres to retrieve.

    Returns:
        Response: The response object containing the list of genres if
                  successful, or an error message and status code if an
                  error occurs.
    """

    return make_api_response(user_genres(userid))
