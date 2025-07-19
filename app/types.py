"""
This module contains common definitions for the application.

It defines the following:

- `ContributorTargets`: An enumeration representing the possible targets
  for contributors, such as "WORK", "EDITION", and "SHORT".

- `ContributorRole`: An enumeration representing the different roles that a
  contributor can have, such as "AUTHOR", "TRANSLATOR", "EDITOR", etc.

These definitions are used throughout the application to provide a consistent
set of values for specific purposes.

Note:
- This module relies on the `Enum` class from the `enum` module.
- You can import `ContributorTarget` and `ContributorRole` from this module
  to use them in other parts of your code.
"""
from enum import Enum, IntEnum


class ContributorTarget(Enum):
    """ Contains all the contributor targets in the database."""
    WORK = 1
    EDITION = 2
    SHORT = 3


class ContributorType(IntEnum):
    """ Contains all the contributor roles in the database.
    """
    AUTHOR = 1
    TRANSLATOR = 2
    EDITOR = 3
    COVER_ARTIST = 4
    ILLUSTRATOR = 5
    SUBJECT = 6
    EDITOR_IN_CHIEF = 7


class HttpResponseCode(IntEnum):
    """A class that defines the HTTP response codes used in the application.

    Fields:
        OK (int): The HTTP status code for a successful response (200).
        CREATED (int): The HTTP status code for a resource creation (201).
        BAD_REQUEST (int): The HTTP status code for a client error (400).
        UNAUTHORIZED (int): The HTTP status code for an unauthorized request
                            (401).
        NOT_FOUND (int): The HTTP status code for a resource not found (404).
        INTERNAL_SERVER_ERROR (int): The HTTP status code for an internal
                                     server error (500).
    """
    OK = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    INTERNAL_SERVER_ERROR = 500
