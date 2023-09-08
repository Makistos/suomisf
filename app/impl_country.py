from sqlalchemy.exc import SQLAlchemyError
from app.route_helpers import new_session
from app.orm_decl import Country
from typing import Any, Union
from app import app

def AddCountry(name: str) -> Union[int, None]:
    session = new_session()
    try:
        country = Country(name=name)
        session.add(country)
        session.commit()
        return country.id
    except SQLAlchemyError as exp:
        app.logger.error('Exception in AddCountry: ' + str(exp))
        return None
