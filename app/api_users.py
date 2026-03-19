"""
API functions related to users.
"""
from flask import Response
from flask_jwt_extended import jwt_required
from app import app

from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_users import (get_current_user, get_user, list_users,
                             user_genres)
from app.types import HttpResponseCode


@app.route('/api/users', methods=['get'])
def api_listusers() -> Response:
    """
    This function is an API endpoint that returns a list of users. It is
    decorated with the `@app.route` decorator, which maps the URL `/api/users`
    to this function. The function accepts GET requests and returns a tuple
    containing a string and an integer. The string represents the response
    body, and the integer represents the HTTP status code. The function calls
    the `make_api_response` function, passing the result of the `list_users`
    function as an argument.
    """

    return make_api_response(list_users())


@app.route('/api/users/<userid>', methods=['get'])
def api_getuser(userid: str) -> Response:
    """
    Get a user by their ID.

    Args:
        userId (str): The ID of the user.

    Returns:
        Response: The response object containing the user information.
    """

    try:
        int_id = int(userid)
    except (TypeError, ValueError):
        app.logger.error(f'api_GetUser: Invalid id {userid}.')
        response = ResponseType(f'Virheellinen tunniste: {userid}.',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_user(int_id))


@app.route('/api/me', methods=['get'])
@jwt_required()
def api_me() -> Response:
    """
    Returns the currently authenticated user's name and admin status.

    Requires a valid JWT Bearer token in the Authorization header.

    **Request**
    ```
    GET /api/me
    Authorization: Bearer <access_token>
    ```

    **Response 200 OK**
    ```json
    {
        "name": "string",
        "is_admin": boolean
    }
    ```
    - `name` — the username of the logged-in user
    - `is_admin` — true if the user has administrator rights

    **Response 401 Unauthorized**
    Returned when no valid JWT token is provided.

    **Frontend usage example (JavaScript)**
    ```js
    const resp = await fetch('/api/me', {
        headers: { 'Authorization': `Bearer ${accessToken}` }
    });
    const { name, is_admin } = await resp.json();
    ```
    """
    return make_api_response(get_current_user())


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
