""" Cleaning of names and titles before they are saved or looked up. """
import re
from typing import Any


def clean_name(value: Any) -> Any:
    """
    Strip leading and trailing spaces and collapse runs of spaces.

    Anything that isn't a string (None included) is returned as is.
    scripts/trim_names.py applies the same rule to existing rows.
    """
    if not isinstance(value, str):
        return value
    return re.sub(' {2,}', ' ', value).strip(' ')
