from app.orm_decl import WorkLink

from typing import Any, List

def linksHaveChanged(old_values: List[WorkLink], new_values: List[Any]) -> bool:
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.description != new_values[idx]['description'] or \
         old_value.link != new_values[idx]['link']:
            return True
    return False

