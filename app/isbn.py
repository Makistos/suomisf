"""
ISBN related functions
"""
from isbnlib import is_isbn10, is_isbn13  # type: ignore


def check_isbn(isbn: str) -> bool:
    """
    Check if given string is a valid ISBN.

    Parameters
    ----------
    isbn : str
      String to check if it is a valid ISBN.

    Returns
    -------
    bool : True if string is a valid ISBN, False otherwise.
    """

    # Check with isbnlib that the string is a valid ISBN
    return is_isbn10(isbn) or is_isbn13(isbn)
