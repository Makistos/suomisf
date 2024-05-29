""" Helper functions. """


from typing import Any, Dict, Optional


def str_differ(str1: Optional[str], str2: Optional[str]) -> bool:
    """
    Check if two strings match. Emptry string and None are considered equal.

    Parameters:
        str1 (str): The first string to compare.
        str2 (str): The second string to compare.

    Returns:
        bool: False if the strings match, True otherwise.
    """
    if str1 is None:
        str1 = ''
    if str2 is None:
        str2 = ''
    if str1 == str2:
        return False
    return True


def objects_differ(
        obj1: Optional[Dict[str, Any]], obj2: Any) -> bool:
    """
    Check if two objects match.

    Parameters:
        obj1 (Any): The first object to compare. This is a dict, None or
                    an empty string.
        obj2 (Any): The second object to compare. This is a Python object.

    Returns:
        bool: False if the objects match, True otherwise.
    """
    if obj1 is None or obj1 == '':
        return obj2 is not None
    if obj2 is None:
        return True
    return obj1['id'] != getattr(obj2, 'id', None)
