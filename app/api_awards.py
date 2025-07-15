import json
from flask import Response, request
from app.api_helpers import make_api_response
from app.impl_awards import (get_award, get_awards_by_filter,
                             get_awards_for_short,
                             get_awards_for_type,
                             get_awards_for_work, get_categories_for_award,
                             get_categories_for_type,
                             get_person_awards, list_awards, save_awarded,
                             save_person_awards, save_work_awards)
from app.api_jwt import jwt_admin_required

from app import app


@app.route('/api/awards', methods=['get'])
def api_listawards() -> Response:
    """
    This function is a route handler for the '/api/awards' endpoint. It
    accepts GET requests and returns a Response object.

    Parameters:
        None

    Returns:
        Response: The response object containing the list of awards.
    """
    return make_api_response(list_awards())


@app.route('/api/awards/<award_id>', methods=['get'])
def api_getaward(award_id: int) -> Response:
    """
    This function is a route handler for the '/api/awards/<award_id>' endpoint.
    It accepts GET requests and returns a Response object.

    Parameters:
        award_id (int): The ID of the award to retrieve.

    Returns:
        Response: The response object containing the award data.
    """
    return make_api_response(get_award(award_id))


@app.route('/api/works/<int:work_id>/awarded', methods=['GET'])
def api_get_work_awards(work_id: int) -> Response:
    """
    Get all awards for a given work.

    Args:
        work_id (int): The ID of the work to get the awards for.

    Returns:
        Response: The response object containing the awards for the given work.
    """
    response = get_awards_for_work(work_id)
    return make_api_response(response)


@app.route('/api/people/<int:person_id>/awarded', methods=['GET'])
def api_get_awards_for_person(person_id: int) -> Response:
    """
    Get all awards for a given person.

    Args:
        person_id (int): The ID of the person to get the awards for.

    Returns:
        Response: The response object containing the awards for the given
        person.
    """
    response = get_person_awards(person_id)
    return make_api_response(response)


@app.route('/api/shorts/<int:short_id>/awarded', methods=['GET'])
def api_get_awards_for_short(short_id: int) -> Response:
    """
    Get all awards for a given short.

    Args:
        short_id (int): The ID of the short to get the awards for.

    Returns:
        Response: The response object containing the awards for the given
        short.
    """
    response = get_awards_for_short(short_id)
    return make_api_response(response)


@jwt_admin_required()  # type: ignore
@app.route('/api/awards/works/awards', methods=['put'])
def api_add_awards_to_work() -> Response:
    """
    Add awards to a work.

    Args:
        work_id (int): The ID of the work to add the awards to.

    Returns:
        Response: The response object containing the status of the request.
    """
    params = json.loads(request.data.decode('utf-8'))
    response = save_work_awards(params)
    return make_api_response(response)


@jwt_admin_required()  # type: ignore
@app.route('/api/awards/people/awards', methods=['put'])
def api_add_awards_to_person() -> Response:
    """
    Add awards to a person.

    Args:
        person_id (int): The ID of the person to add the awards to.

    Returns:
        Response: The response object containing the status of the request.
    """
    params = json.loads(request.data.decode('utf-8'))
    response = save_person_awards(params)
    return make_api_response(response)


@app.route('/api/awards/type/<string:award_type>', methods=['GET'])
def api_get_awards_by_type(award_type: str) -> Response:
    """
    Get all awards of a given type.

    Args:
        award_type (str): The type of award to get.

    Returns:
        Response: The response object containing the awards of the given type.
    """
    response = get_awards_for_type(award_type)
    return make_api_response(response)


@app.route('/api/awards/categories/<string:award_type>', methods=['GET'])
def api_get_all_award_categories(award_type: str) -> Response:
    """
    Get all award categories.

    Returns:
        Response: The response object containing all award categories.
    """
    response = get_categories_for_type(award_type)
    return make_api_response(response)


@app.route('/api/awards/categories/<award_id>', methods=['GET'])
def api_get_award_categories(award_id: int) -> Response:
    """
    Get all categories for a given award.

    Args:
        award_id (int): The ID of the award to get the categories for.

    Returns:
        Response: The response object containing the categories for the given
        award.
    """
    response = get_categories_for_award(award_id)
    return make_api_response(response)


@app.route('/api/awards/filter/<string:filter>', methods=['GET'])
def api_get_awards_by_filter(filter: str) -> Response:
    """
    Get all awards that match a given filter.

    Args:
        filter (str): The filter to apply to the awards.

    Returns:
        Response: The response object containing the awards that match the
        given filter.
    """
    response = get_awards_by_filter(filter)
    return make_api_response(response)


@jwt_admin_required()  # type: ignore
@app.route('/api/awarded', methods=['POST'])
def api_awarded() -> Response:
    """
    Get all awards that match a given filter.

    Args:
        filter (str): The filter to apply to the awards.

    Returns:
        Response: The response object containing the awards that match the
        given filter.
    """
    params = json.loads(request.data.decode('utf-8'))
    response = save_awarded(params)
    return make_api_response(response)
