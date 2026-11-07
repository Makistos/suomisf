import json
import os
from typing import Optional
from flask import Response
from app.impl import ResponseType
from app.types import HttpResponseCode

from app import app

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
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ("jpg", "jpeg")


def unique_filename(folder: str, filename: str) -> str:
    """
    Return a name for a new file in folder that doesn't overwrite one.

    Phones often give every photo the same name (iOS: "image.jpg"), so
    a second upload would replace another edition's or issue's cover.
    The name gets _2, _3, ... before the extension until it is free.

    Args:
        folder (str): The directory the file will be saved in.
        filename (str): The wanted (already secured) file name.

    Returns:
        str: filename, or filename with a numeric suffix.
    """
    stem, ext = os.path.splitext(filename)
    candidate = filename
    n = 2
    while os.path.exists(os.path.join(folder, candidate)):
        candidate = f"{stem}_{n}{ext}"
        n += 1
    return candidate


def validate_positive_integer_id(value: str, field_name: str):
    """
    Validate that a string represents a positive integer.

    Returns:
        tuple: (parsed_int, error_response) - one will be None
    """
    if not value:
        error_msg = f'api_deleteowner: Virheellinen {field_name}.'
        app.logger.error(error_msg)
        return None, ResponseType(error_msg,
                                  status=HttpResponseCode.BAD_REQUEST.value)

    if not value.isdigit():
        error_msg = f'api_deleteowner: Virheellinen {field_name} {value}.'
        app.logger.error(error_msg)
        return None, ResponseType(error_msg,
                                  status=HttpResponseCode.BAD_REQUEST.value)

    parsed_value = int(value)
    if parsed_value < 1:
        error_msg = f'api_deleteowner: Virheellinen {field_name} {value}.'
        app.logger.error(error_msg)
        return None, ResponseType(error_msg,
                                  status=HttpResponseCode.BAD_REQUEST.value)

    return parsed_value, None
