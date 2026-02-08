"""
Contributor role API endpoints.

This module provides endpoints for retrieving contributor roles used in the
database. Roles define the relationship between a person and a work, edition,
short story, or magazine issue (e.g., author, translator, editor).
"""
from flask import Response
from app import app
from app.api_helpers import make_api_response
from app.impl import role_list, role_get


@app.route('/api/roles/', methods=['get'])
def api_roles() -> Response:
    """
    Get all contributor roles.

    Endpoint: GET /api/roles/

    Parameters: None

    Returns:
        200 OK: JSON array of role objects sorted by ID.

        Response Schema:
        [
            {
                "id": <int>,       // Role ID
                "name": <string>   // Role name (Finnish)
            },
            ...
        ]

        Example Response:
        [
            {"id": 1, "name": "kirjoittaja"},
            {"id": 2, "name": "kääntäjä"},
            {"id": 3, "name": "toimittaja"},
            {"id": 4, "name": "kuvittaja"},
            {"id": 5, "name": "kansikuva"},
            ...
        ]

        Common Role IDs:
        - 1: kirjoittaja (author)
        - 2: kääntäjä (translator)
        - 3: toimittaja (editor)
        - 4: kuvittaja (illustrator)
        - 5: kansikuva (cover artist)

        Use Case:
        - Populate role dropdowns in forms
        - Map role IDs to names in statistics displays
        - Filter statistics by role

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(role_list())


@app.route('/api/roles/<target>', methods=['get'])
def api_role(target: str) -> Response:
    """
    Get roles applicable to a specific target type.

    Endpoint: GET /api/roles/<target>

    Path Parameters:
        target (string): The target type to get roles for.
            Valid values:
            - "work": Roles for works (author, editor, subject)
            - "edition": Roles for editions (author, editor, subject)
            - "short": Roles for short stories (author, translator, subject)
            - "issue": Roles for magazine issues (editor-in-chief, cover artist)

    Returns:
        200 OK: JSON array of role objects applicable to the target.

        Response Schema:
        [
            {
                "id": <int>,       // Role ID
                "name": <string>   // Role name (Finnish)
            },
            ...
        ]

        Example Request:
        GET /api/roles/work

        Example Response:
        [
            {"id": 1, "name": "kirjoittaja"},
            {"id": 3, "name": "toimittaja"},
            {"id": 6, "name": "aihe"}
        ]

        Example Request:
        GET /api/roles/short

        Example Response:
        [
            {"id": 1, "name": "kirjoittaja"},
            {"id": 2, "name": "kääntäjä"},
            {"id": 6, "name": "aihe"}
        ]

        Use Case:
        - Populate role dropdowns for specific form types
        - Show only relevant roles when editing works, editions, or stories

        400 Bad Request: Invalid target type provided.
        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(role_get(target))
