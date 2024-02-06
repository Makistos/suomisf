""" API related functions for magazines.
"""

from typing import Tuple
from flask import Response
from app.api_helpers import make_api_response
from app.impl import ResponseType
from app.impl_magazines import (list_magazines, get_magazine)
from app.types import HttpResponseCode

from app import app

###
# Magazine related functions


@ app.route('/api/magazines', methods=['get'])
def api_listmagazines() -> Response:
    """
    Retrieves a list of magazines from the API.

    Returns:
        Response: The response object containing the list of magazines.
    """

    return make_api_response(list_magazines())


@ app.route('/api/magazines/<magazineid>', methods=['get'])
def api_getmagazine(magazineid: str) -> Response:
    """
    Get a magazine by its ID.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Response: The response object containing the magazine data.

    Raises:
        ValueError: If the magazine ID is invalid.
    """

    try:
        int_id = int(magazineid)
    except (ValueError, TypeError):
        app.logger.error(f'api_GetMagazine: Invalid id {magazineid}.')
        response = ResponseType(
            f'api_GetMagazine: Virheellinen tunniste {magazineid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_magazine(int_id))


@ app.route('/api/magazines/<magazineid>', methods=['patch'])
def api_updatemagazine(magazineid: str) -> Tuple[str, int]:
    """
    Updates a magazine with the given `magazineId`.

    Args:
        magazineId (str): The ID of the magazine to update.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        status code.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)

    # return UpdateMagazine(options, "")


@ app.route('/api/magazines/<magazineid>/issues', methods=['get'])
def api_getmagazineissues(magazineid: str) -> Tuple[str, int]:
    """
    Retrieves the issues of a specific magazine.

    Args:
        magazineId (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
                         value.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazineIssues(options)


@ app.route('/api/magazines/<magazineid>/publisher', methods=['get'])
def api_getmagazinepublisher(magazineid: str) -> Tuple[str, int]:
    """
    Get the publisher of a magazine.

    Args:
        magazineid (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazinePublisher(options)


@ app.route('/api/magazines/<magazineid>/tags', methods=['get'])
def api_getmagazinetags(magazineid: str) -> Tuple[str, int]:
    """
    Get the tags associated with a specific magazine.

    Args:
        magazineid (str): The ID of the magazine.

    Returns:
        Tuple[str, int]: A tuple containing an empty string and an integer
        value.
    """

    options = {}
    options["magazineId"] = magazineid

    return ("", 0)
    # return GetMagazineTags(options)
