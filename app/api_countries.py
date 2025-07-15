###
# Country related functions

import bleach
from flask import Response
from app import app
from app.api_helpers import make_api_response
from app.impl import ResponseType, country_list, filter_countries
from app.types import HttpResponseCode


@app.route('/api/countries', methods=['get'])
def countries() -> Response:
    """
    Returns a list of all of the countries in the system ordered by name.
    """
    return make_api_response(country_list())


@app.route('/api/filter/countries/<pattern>', methods=['get'])
def api_filtercountries(pattern: str) -> Response:
    """
    Filter countries based on a given pattern.

    Args:
        pattern (str): The pattern to filter the countries.

    Returns:
        Response: The response object containing the filtered countries.

    Raises:
        None
    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('FilterCountries: Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    retval = filter_countries(pattern)
    return make_api_response(retval)
