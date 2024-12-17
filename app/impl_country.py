from sqlalchemy.exc import SQLAlchemyError
from app.route_helpers import new_session
from app.orm_decl import Country
from typing import Any, Union
from app import app

def AddCountry(session, name: str) -> Union[int, None]:
    """
    Adds a country to the database if it doesn't already exist, and returns
    the country's ID.

    Args:
        session (Any): The database session.
        name (str): The name of the country to add.

    Returns:
        Union[int, None]: The ID of the country if it already exists, or None
        if an exception occurs.
    """

    try:
        country = Country(name=name)
        session.add(country)
        session.flush()
        return country.id
    except SQLAlchemyError as exp:
        app.logger.error('Exception in AddCountry: ' + str(exp))
        return None
