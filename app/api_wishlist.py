
from flask import Response
from flask_jwt_extended import jwt_required
from app import app
from app.impl_editions import (
    editionwishlist_get, editionwishlist_add, editionwishlist_remove,
    editionwishlist_user, editionowner_getowned)
from app.api_helpers import make_api_response


@app.route('/api/editions/<editionid>/wishlist', methods=['get'])
def api_editionwishlist(editionid: str) -> Response:
    """
    Get the wishlist for a specific edition.

    Args:
        editionid (str): The ID of the edition.

    Returns:
        Response: The API response containing the wishlist for the edition.
    """
    return make_api_response(editionwishlist_get(editionid))


@jwt_required()  # type: ignore
@app.route('/api/editions/<editionid>/wishlist/<userid>', methods=['put'])
def api_editionwishlist_add(editionid: str, userid: str) -> Response:
    """
    Add an edition to a user's wishlist.

    Args:
        editionid (str): The ID of the edition.
        userid (str): The ID of the user.

    Returns:
        Response: The API response containing the result of the operation.
    """
    return make_api_response(editionwishlist_add(editionid, userid))


@jwt_required()  # type: ignore
@app.route('/api/editions/<editionid>/wishlist/<userid>', methods=['delete'])
def api_editionwishlist_remove(editionid: str, userid: str) -> Response:
    """
    Remove an edition from a user's wishlist.

    Args:
        editionid (str): The ID of the edition.
        userid (str): The ID of the user.

    Returns:
        Response: The API response containing the result of the operation.
    """
    return make_api_response(editionwishlist_remove(editionid, userid))


@app.route('/api/editions/<editionid>/wishlist/<userid>', methods=['get'])
def api_editionwishlist_user_status(editionid: str, userid: str) -> Response:
    """
    Checks if given user (userid) has given edition (editionid) in their
    wishlist.

    Args:
    editionid (str): The id of the edition.
    userid (str): The id of the user.

    Returns:
    Response: A JSON response containing a boolean value indicating if the
    edition is in the users wishlist.
    """
    return editionwishlist_user(editionid, userid)


@app.route('/api/editions/wishlist/<userid>', methods=['get'])
def api_editionwishlist_user_list(userid: str) -> Response:
    """
    Gets the wishlist for a specific user.

    Args:
        userid (str): The ID of the user.

    Returns:
        Response: The API response containing the wishlist for the user.
    """
    return make_api_response(editionowner_getowned(userid, True))
