from typing import Any, List

def genresHaveChanged(old_values: List[Any], new_values: List[Any]) -> bool:
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.id != new_values[idx]['id']:
            return True
    return False
