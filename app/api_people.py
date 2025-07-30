""" API related functions for people. """

import json
from typing import Any, Dict
import bleach
from flask import Response, request
from app.api import fix_operator
from app.api_errors import APIError
from app.api_helpers import make_api_response

from app.impl import ResponseType
from app.impl_people import (filter_people, get_latest_people,
                             get_person_articles, get_person_issue_contributions, list_people,
                             person_add,
                             person_chiefeditor,
                             person_update, get_person, person_delete,
                             person_tag_add, person_tag_remove,
                             person_shorts)
from app.impl_awards import get_person_awards
from app.types import HttpResponseCode
from app.api_jwt import jwt_admin_required

from app import app


@app.route('/api/people', methods=['post', 'put'], strict_slashes=False)
@jwt_admin_required()  # type: ignore
def api_createupdateperson() -> Response:
    """
    Create or update a person in the API.

    This function is responsible for handling the POST and PUT requests to the
    '/api/people' endpoint. It expects a JSON payload containing the person's
    information.

    Parameters:
        None

    Returns:
        Response: The response object containing the result of the API request.

    Raises:
        TypeError: If the request data is not a valid JSON.
        ValueError: If the JSON payload is invalid.
        jsonschema.exceptions.ValidationError: If the JSON payload does not
                                               conform to the PersonSchema.

    Note:
        - This function requires the request method to be either 'POST' or
          'PUT'.
        - The request data should be a valid JSON string.
        - The JSON payload should conform to the PersonSchema.
        - The function logs any errors encountered during the process.

    Tests:
        create_author: Create a person
        create_translator: Create a person
        create_editor: Create a person
        update_author: Update a person's info
    """
    try:
        params = json.loads(request.data.decode('utf-8'))
    except (TypeError, ValueError):
        app.logger.error('Invalid JSON.')
        return make_api_response(
            ResponseType('Virheelliset parametrit.',
                         status=HttpResponseCode.BAD_REQUEST.value))
    # try:
    #     validate(instance=params, schema=PersonSchema)
    # except jsonschema.exceptions.ValidationError as exp:
    #     app.logger.error(f'api_CreateUpdatePerson: Invalid JSON {exp}.')
    #     return make_api_response(
    #         ResponseType('api_CreateUpdatePerson: Virheelliset parametrit.',
    #                      status=HttpResponseCode.BAD_REQUEST.value))
    if request.method == 'POST':
        retval = make_api_response(person_add(params))
    elif request.method == 'PUT':
        retval = make_api_response(person_update(params))

    return retval


@app.route('/api/people/', methods=['get'])
def api_getpeople() -> Response:

    """
    This function receives parameters in the form of
    first=50&...filters_name_operator=1&filters_name_constraints_value=null..
    I.e. the original dictionary has been translated into variables. The
    Javascript dictionary looks like this:
    {
        first: 0,
        rows: 50,
        page: 0,
        sortField: "name",
        sortOrder: 1,
        multiSortMeta: null,
        filters: {
            global: { value: null, matchMode: FilterMatchMode.CONTAINS },
            name: { operator: FilterOperator.AND,
                    constraints: [
                      { value: null,
                        matchMode: FilterMatchMode.STARTS_WITH
                      }
                    ]
                  },
            dob: { operator: FilterOperator.AND,
                   constraints: [
                     { value: null,
                       matchMode: FilterMatchMode.EQUALS
                     }
                   ]
                  },
            dod: { operator: FilterOperator.AND,
                   constraints: [
                      { value: null,
                        matchMode: FilterMatchMode.EQUALS
                      }
                   ]
                 },
            nationality: { value: null, matchMode: FilterMatchMode.EQUALS },
            work_count: { value: null, matchMode: FilterMatchMode.EQUALS },
            story_count: { value: null, matchMode: FilterMatchMode.EQUALS },
            roles: { value: null, matchMode: FilterMatchMode.EQUALS }
        }
    }
    This function will translate the parameter list back to a similar Python
    dict.
    Those constants in the list are explained in the implementation function,
    but they are simple self-explaining strings.
    """

    url_params = request.args.to_dict()
    params: Dict[str, Any] = {}
    for (param, value) in url_params.items():
        # param, value = p.split('=')
        if value in ('null', 'undefined'):
            value = None
        if '_' not in param and param != 'filters':
            # This takes care of the first six parameters.
            params[param] = value
        else:
            # In effect we have two situations here: either a parameter that
            # has a simple value, like filters_global_value=null or a
            # constraint e.g. filters_name_constraints_0_value=null.
            parts = param.split('_')
            # Filters is the only word these parameters
            # start with so we can skip that
            filter_field = parts[1]  # global, name, dob, etc.
            filter_name = parts[2]   # value, operator, constraints, etc.
            if filter_field not in params:
                params[filter_field] = {}
            if filter_name == 'constraints':
                constraint_num = int(parts[3])  # 0, 1...
                constraint_name = parts[4]  # value or matchmode
                if 'constraints' not in params[filter_field]:
                    params[filter_field]['constraints'] = [{}]
                if len(params[filter_field]['constraints']) < constraint_num:
                    # Array values might be in wrong order
                    len_inc = constraint_num - \
                        len(params[filter_field]['constraints'])
                    for _ in range(len_inc):
                        params[filter_field]['constraints'].append([{}])
                params[filter_field][
                    'constraints'][constraint_num][constraint_name] = value
            else:
                if filter_name == 'matchMode':
                    input_value = params[filter_field]['value']
                    try:
                        (value, input_value) = fix_operator(value, input_value)
                    except APIError as exp:
                        return make_api_response(
                            ResponseType(exp.message, exp.code))
                    params[filter_field]['value'] = input_value
                params[filter_field][filter_name] = value
    try:
        retval = list_people(params)
    except APIError as exp:
        print(exp.message)
        return make_api_response(ResponseType(exp.message, exp.code))
    return make_api_response(retval)


@app.route('/api/people/<person_id>', methods=['get'], strict_slashes=False)
def api_getperson(person_id: str) -> Response:
    """
    Retrieves a person's information based on the provided person ID.

    Parameters:
        person_id (str): The ID of the person to retrieve.

    Returns:
        Response: The response containing the person's information.

    Raises:
        TypeError: If the person ID is not an integer.
        ValueError: If the person ID is not a valid integer.

    Tests:
        get_person: Get existing person
        get_person_bad_id: Try id which is not a number
        get_person_unknown_id: Try id not existing in db
    """
    # app.logger.error(app.url_map)
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error(f'api_getperson: Invalid id {person_id}.')
        response = ResponseType(
            f'api_getperson: Virheellinen tunniste {person_id}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_person(int_id))


@app.route('/api/people/<person_id>', methods=['delete'])
@jwt_admin_required()  # type: ignore
def api_deleteperson(person_id: str) -> Response:
    """
    Delete a person from the API.

    Args:
        person_id (str): The ID of the person to be deleted.

    Returns:
        Response: The response object containing the result of the deletion.

    Tests:
        delete_author: Delete an existing person
        delete_editor: Delete an existing person
        delete_translator: Delete an existing person
        delete_person_bad_id: Try id which is not a number
        delete_person_unknown_id: Try id not existing in db
        delete_person_not_authorized: Try to delete without authorization
    """
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {person_id}.')
        response = ResponseType(
            f'Virheellinen tunniste {person_id}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(person_delete(int_id))


@app.route('/api/people/<person_id>/articles', methods=['get'])
def api_personarticles(person_id: str) -> Response:
    """
    Retrieves a list of articles for a specific person.

    Args:
        person_id (str): The ID of the person.

    Returns:
        Response: The response object containing the list of articles.
    """
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error('Invalid id %s.', person_id)
        response = ResponseType(
            f'Virheellinen tunniste {person_id}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_person_articles(int_id))


@app.route('/api/people/<person_id>/awarded', methods=['get'])
def api_personawards(person_id: str) -> Response:
    """
    Retrieves a list of awards for a specific person.

    Args:
        person_id (str): The ID of the person.

    Returns:
        Response: The response object containing the list of awards.
    """
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error('Invalid id %s.', person_id)
        response = ResponseType(
            f'Virheellinen tunniste {person_id}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_person_awards(int_id))


@app.route('/api/people/<personid>/chiefeditor', methods=['get'])
def api_chiefeditor(personid: int) -> Response:
    """
    Retrieves issues person is editor in chief.

    Args:
        id (int): The ID of the person.

    Returns:
        Response: The response object containing the issues.
    """
    try:
        int_id = int(personid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {personid}.')
        response = ResponseType(
            f'Virheellinen tunniste {personid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(person_chiefeditor(int_id))


@app.route('/api/people/<personid>/shorts', methods=['get'])
def api_listshorts(personid: int) -> Response:
    """
    Retrieves a list of shorts for a specific person.

    Args:
        id (int): The ID of the person.

    Returns:
        Response: The response object containing the list of shorts.
    """
    try:
        int_id = int(personid)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {personid}.')
        response = ResponseType(
            f'Virheellinen tunniste {personid}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(person_shorts(int_id))


@app.route('/api/person/<personid>/tags/<tagid>', methods=['put', 'delete'])
@jwt_admin_required()  # type: ignore
def api_tagtoperson(personid: int, tagid: int) -> Response:
    """
    Handles the API endpoint for adding or removing a tag from a person.

    Args:
        id (int): The ID of the person.
        tagid (int): The ID of the tag.

    Returns:
        Response: The API response.

    Raises:
        None
    """
    if request.method == 'PUT':
        func = person_tag_add
    elif request.method == 'DELETE':
        func = person_tag_remove

    try:
        person_id = int(personid)
        tag_id = int(tagid)
    except (TypeError, ValueError):
        app.logger.error(
            f'{func.__name__}: Invalid id. id={personid}, tagid={tagid}.')
        response = ResponseType('Virheellinen tunniste',
                                status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    retval = func(person_id, tag_id)

    return make_api_response(retval)


@app.route('/api/filter/people/<pattern>', methods=['get'])
def api_filterpeople(pattern: str) -> Response:
    """
    Filter people list.

    Pattern has to be at least three characters long. Matching is done
    from start of the name field.

    Parameters
    ----------
    pattern: str
        Pattern to search for.

    Returns
    -------

    """
    pattern = bleach.clean(pattern)
    if len(pattern) < 2:
        app.logger.error('Pattern too short.')
        response = ResponseType(
            'Liian lyhyt hakuehto', status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    retval = filter_people(pattern)
    return make_api_response(retval)


@app.route('/api/latest/people/<count>', methods=['get'])
def api_latestpeople(count: int) -> Response:
    """
    Get the latest people.

    Args:
        count (int): The number of people to return.

    Returns:
        Response: The response object containing the list of latest people.

    Raises:
        ValueError: If the count is not an integer.
    """
    try:
        count = int(count)
    except (ValueError, TypeError):
        app.logger.error(f'api_latestpeople: Invalid count {count}.')
        response = ResponseType(
            f'api_latestpeople: Virheellinen maara {count}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)
    return make_api_response(get_latest_people(count))


@app.route('/api/people/<person_id>/issue-contributions', methods=['get'])
def api_issue_contributors(person_id: str) -> Response:
    """
    Retrieves issue contributors for a specific person.

    Args:
        person_id (str): The ID of the person.

    Returns:
        Response: The response object containing the issue contributors.
    """
    try:
        int_id = int(person_id)
    except (TypeError, ValueError):
        app.logger.error(f'Invalid id {person_id}.')
        response = ResponseType(
            f'Virheellinen tunniste {person_id}.',
            status=HttpResponseCode.BAD_REQUEST.value)
        return make_api_response(response)

    return make_api_response(get_person_issue_contributions(int_id))
