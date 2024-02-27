""" Link related functions. """

from typing import Any, List


def links_have_changed(old_values: List[Any],
                       new_values: List[Any]) -> bool:
    """
    Check if the old and new values of links have changed.

    Args:
        old_values (List[Any]): The list of old values.
        new_values (List[Any]): The list of new values.

    Returns:
        bool: True if the values have changed, False otherwise.
    """
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.description != new_values[idx]['description'] or \
         old_value.link != new_values[idx]['link']:
            return True
    return False
