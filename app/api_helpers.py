
import json
from typing import Optional
from flask import Response
from app.impl import ResponseType


DEFAULT_MIMETYPE = 'application/json'  # Data is always returned as JSON


def make_api_error(response: ResponseType) -> Response:
    """
    Generate a response object for an API error.

    Args:
        response (ResponseType): The response object containing the error
                                  message.

    Returns:
        Response: The response object with the error message, status code, and
                   mimetype.
    """
    return Response(response=list(json.dumps({'msg': response.response})),
                    status=response.status,
                    mimetype=DEFAULT_MIMETYPE)


def make_api_response(response: ResponseType) -> Response:
    """
    Generate a Flask Response object from a given ResponseType object.

    Args:
        response (ResponseType): The ResponseType object to be converted into a
                                 Flask Response object.

    Returns:
        Response: The Flask Response object generated from the given
                  ResponseType object.
    """
    # Response is made into a list for performance as per Flask documentation
    if response.status >= 400 and response.status <= 511:
        return make_api_error(response)

    return Response(response=json.dumps(response.response),
                    status=response.status,
                    mimetype=DEFAULT_MIMETYPE)


def allowed_image(filename: Optional[str]) -> bool:
    """
    Check if the given filename is an allowed image.

    Args:
        filename (Optional[str]): The name of the file to check.

    Returns:
        bool: True if the file is an allowed image, False otherwise.
    """
    if not filename:
        return False
    if "." not in filename:
        return False

    ext = filename.rsplit(".", 10)[1]
    return ext.upper() in ["jpg", "JPG"]
