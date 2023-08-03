from typing import Any, List
from app.orm_decl import Genre

def genresHaveChanged(old_values: List[Any], new_values: List[Any]) -> bool:
    """
    Returns a boolean indicating whether or not the list of new values is
    different from the list of old values
    :param old_values: list of previous genres
    :param new_values: list of new genres
    :return: boolean indicating whether or not the list of new values is
    different from the list of old values
    """
    if len(old_values) != len(new_values):
        return True
    for idx, old_value in enumerate(old_values):
        if old_value.id != new_values[idx]['id']:
            return True
    return False

def checkGenreField(session: Any, genre: Any) -> bool:
    """
    Check that the genre field is valid.
    :param session: database session
    :param genre: genre field
    :return: True if valid, False otherwise
    """
    if not 'id' in genre:
        return False
    genre = session.query(Genre).filter(Genre.id == genre['id']).first()
    if not genre:
        return False
    return True