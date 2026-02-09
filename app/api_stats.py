"""
Statistics API endpoints.

This module provides endpoints for retrieving various statistics about the
database content, including work counts by genre, author productivity,
publisher statistics, publication trends over time, and miscellaneous metrics.

All endpoints return JSON responses with appropriate HTTP status codes.
"""
from flask import request
from flask.wrappers import Response
from app.api_helpers import make_api_response
from app.impl_stats import (
    stats_genrecounts,
    stats_personcounts,
    stats_storypersoncounts,
    stats_publishercounts,
    stats_worksbyyear,
    stats_origworksbyyear,
    stats_storiesbyyear,
    stats_filterstories,
    stats_filterworks,
    stats_misc,
    stats_issuesperyear,
    stats_nationalitycounts,
    stats_storynationalitycounts
)
from app import app


@app.route('/api/stats/genrecounts', methods=['GET'])
def api_stats_genrecounts() -> Response:
    """
    Get work counts for each genre.

    Endpoint: GET /api/stats/genrecounts

    Parameters: None

    Returns:
        200 OK: JSON object with genre abbreviations as keys and work counts
                as values.

        Response Schema:
        {
            "<genre_abbr>": <count>,  // e.g., "SF": 1234
            ...
        }

        Example Response:
        {
            "SF": 1234,
            "F": 567,
            "K": 89,
            "nSF": 45,
            "nF": 23
        }

        Genre abbreviations:
        - SF: Science Fiction
        - F: Fantasy
        - K: Horror (Kauhu)
        - nSF: Domestic Science Fiction
        - nF: Domestic Fantasy

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_genrecounts())


@app.route('/api/stats/personcounts', methods=['GET'])
def api_stats_personcounts() -> Response:
    """
    Get the most productive persons by role with their work counts per genre.

    Endpoint: GET /api/stats/personcounts

    Query Parameters:
        count (int, optional): Number of top persons to return. Default: 10.
                               Must be a positive integer.
        genre (string, optional): Genre abbreviation to filter by (e.g., "SF",
                                  "F", "K"). When set, returns persons sorted
                                  by their work count in that specific genre.
        role (int, optional): Role ID to filter by. Default: 1 (author).
                              Common values: 1 = author, 2 = translator,
                              3 = editor, etc.

    Returns:
        200 OK: JSON array of person objects sorted by total work count
                (descending), or by work count in specified genre if the
                genre parameter is provided. The last item is always "Muut"
                (Others) containing aggregated counts for all persons not
                in top list.

        Response Schema:
        [
            {
                "id": <int|null>,      // Person ID, null for "Muut"
                "name": <string>,      // Person name (Last, First format)
                "alt_name": <string|null>,  // Display name (First Last format)
                "nationality": <string|null>,  // Person's nationality/country
                "genres": {
                    "<genre_abbr>": {
                        "<role_name>": <count>,  // Work count per role
                        ...
                    },
                    ...
                },
                "total": <int>         // Total work count (for filtered role)
            },
            ...
        ]

        Example Request:
        GET /api/stats/personcounts?count=5
        GET /api/stats/personcounts?count=5&genre=SF
        GET /api/stats/personcounts?count=5&role=2

        Example Response:
        [
            {
                "id": 123,
                "name": "Asimov, Isaac",
                "alt_name": "Isaac Asimov",
                "nationality": "Yhdysvallat",
                "genres": {
                    "SF": {"kirjoittaja": 45, "kääntäjä": 5},
                    "F": {"kirjoittaja": 5}
                },
                "total": 55
            },
            ...
            {
                "id": null,
                "name": "Muut",
                "alt_name": null,
                "nationality": null,
                "genres": {
                    "SF": {"kirjoittaja": 1000, "kääntäjä": 500},
                    "F": {"kirjoittaja": 400, "kääntäjä": 100}
                },
                "total": 1700
            }
        ]

        400 Bad Request: Invalid genre abbreviation provided.
        500 Internal Server Error: Database error occurred.
    """
    count = request.args.get('count', default=10, type=int)
    if count < 1:
        count = 10
    genre = request.args.get('genre', default=None, type=str)
    role_id = request.args.get('role', default=1, type=int)
    return make_api_response(stats_personcounts(count, genre, role_id))


@app.route('/api/stats/storypersoncounts', methods=['GET'])
def api_stats_storypersoncounts() -> Response:
    """
    Get the most productive persons by role with their short story counts.

    Endpoint: GET /api/stats/storypersoncounts

    Query Parameters:
        count (int, optional): Number of top persons to return. Default: 10.
                               Must be a positive integer.
        role (int, optional): Role ID to filter by. Default: 1 (author).
                              Common values: 1 = author, 2 = translator,
                              3 = editor, etc.
        storytype (int, optional): Story type ID to filter by.
                                   When set, only counts stories of that type.

    Returns:
        200 OK: JSON array of person objects sorted by total short story count
                (descending). The last item is always "Muut" (Others)
                containing aggregated counts for all persons not in top list.

        Response Schema:
        [
            {
                "id": <int|null>,      // Person ID, null for "Muut"
                "name": <string>,      // Person name (Last, First format)
                "alt_name": <string|null>,  // Display name (First Last format)
                "nationality": <string|null>,  // Person's nationality/country
                "storytypes": {
                    "<storytype_name>": {
                        "<role_name>": <count>,  // Story count per role
                        ...
                    },
                    ...
                },
                "total": <int>         // Total short story count (for filtered role)
            },
            ...
        ]

        Example Request:
        GET /api/stats/storypersoncounts?count=5
        GET /api/stats/storypersoncounts?count=5&role=2
        GET /api/stats/storypersoncounts?count=5&storytype=1

        Example Response:
        [
            {
                "id": 123,
                "name": "Asimov, Isaac",
                "alt_name": "Isaac Asimov",
                "nationality": "Yhdysvallat",
                "storytypes": {
                    "novelli": {"kirjoittaja": 80, "kääntäjä": 20},
                    "kertomus": {"kirjoittaja": 50, "kääntäjä": 10}
                },
                "total": 160
            },
            ...
            {
                "id": null,
                "name": "Muut",
                "alt_name": null,
                "nationality": null,
                "storytypes": {
                    "novelli": {"kirjoittaja": 2000, "kääntäjä": 1000},
                    "kertomus": {"kirjoittaja": 1500, "kääntäjä": 500}
                },
                "total": 5000
            }
        ]

        400 Bad Request: Invalid storytype ID provided.
        500 Internal Server Error: Database error occurred.
    """
    count = request.args.get('count', default=10, type=int)
    if count < 1:
        count = 10
    role_id = request.args.get('role', default=1, type=int)
    storytype_id = request.args.get('storytype', default=None, type=int)
    return make_api_response(stats_storypersoncounts(count, role_id, storytype_id))


@app.route('/api/stats/publishercounts', methods=['GET'])
def api_stats_publishercounts() -> Response:
    """
    Get the biggest publishers with their edition counts per genre.

    Endpoint: GET /api/stats/publishercounts

    Query Parameters:
        count (int, optional): Number of top publishers to return. Default: 10.
                               Must be a positive integer.

    Returns:
        200 OK: JSON array of publisher objects sorted by total edition count
                (descending). The last item is always "Muut" (Others)
                containing aggregated counts for publishers not in top list.

        Response Schema:
        [
            {
                "id": <int|null>,       // Publisher ID, null for "Muut"
                "name": <string>,       // Publisher short name
                "fullname": <string|null>,  // Publisher full name
                "genres": {
                    "<genre_abbr>": <count>,  // Edition count per genre
                    ...
                },
                "total": <int>          // Total edition count
            },
            ...
        ]

        Example Request:
        GET /api/stats/publishercounts?count=5

        Example Response:
        [
            {
                "id": 1,
                "name": "WSOY",
                "fullname": "Werner Söderström Osakeyhtiö",
                "genres": {"SF": 200, "F": 150, "K": 50},
                "total": 400
            },
            {
                "id": 2,
                "name": "Tammi",
                "fullname": "Kustannusosakeyhtiö Tammi",
                "genres": {"SF": 180, "F": 120},
                "total": 300
            },
            ...
            {
                "id": null,
                "name": "Muut",
                "fullname": null,
                "genres": {"SF": 500, "F": 300, "K": 150},
                "total": 950
            }
        ]

        500 Internal Server Error: Database error occurred.
    """
    pub_count = request.args.get('count', default=10, type=int)
    if pub_count < 1:
        pub_count = 10
    return make_api_response(stats_publishercounts(pub_count))


@app.route('/api/stats/worksbyyear', methods=['GET'])
def api_stats_worksbyyear() -> Response:
    """
    Get count of first editions published by year, grouped by language.

    This counts Finnish editions (when they were published in Finland),
    not the original publication year of the works.

    Endpoint: GET /api/stats/worksbyyear

    Parameters: None

    Returns:
        200 OK: JSON array of year statistics sorted by year (ascending),
                then by language name.

        Response Schema:
        [
            {
                "year": <int>,              // Publication year
                "count": <int>,             // Number of first editions
                "language_id": <int|null>,  // Original work's language ID
                "language_name": <string|null>  // Original work's language name
            },
            ...
        ]

        Example Response:
        [
            {"year": 1950, "count": 5, "language_id": 1, "language_name": "suomi"},
            {"year": 1950, "count": 12, "language_id": 2, "language_name": "englanti"},
            {"year": 1951, "count": 8, "language_id": 1, "language_name": "suomi"},
            {"year": 1951, "count": 15, "language_id": 2, "language_name": "englanti"},
            ...
        ]

        Use Case:
        - Visualize publication trends over time
        - Compare domestic vs. translated works by year
        - Create stacked bar charts showing language distribution

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_worksbyyear())


@app.route('/api/stats/origworksbyyear', methods=['GET'])
def api_stats_origworksbyyear() -> Response:
    """
    Get count of original work publications by year, grouped by language.

    This counts when works were originally published (in any country),
    not when they were translated/published in Finland.

    Endpoint: GET /api/stats/origworksbyyear

    Parameters: None

    Returns:
        200 OK: JSON array of year statistics sorted by year (ascending),
                then by language name.

        Response Schema:
        [
            {
                "year": <int>,              // Original publication year
                "count": <int>,             // Number of works
                "language_id": <int|null>,  // Language ID
                "language_name": <string|null>  // Language name
            },
            ...
        ]

        Example Response:
        [
            {"year": 1920, "count": 3, "language_id": 2, "language_name": "englanti"},
            {"year": 1921, "count": 5, "language_id": 2, "language_name": "englanti"},
            {"year": 1922, "count": 2, "language_id": 1, "language_name": "suomi"},
            ...
        ]

        Use Case:
        - Analyze the "golden ages" of SF/Fantasy literature
        - See which decades produced most translated works
        - Compare publication patterns across languages

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_origworksbyyear())


@app.route('/api/stats/misc', methods=['GET'])
def api_stats_misc() -> Response:
    """
    Get miscellaneous statistics about the database.

    Provides various fun and interesting metrics about the collection.

    Endpoint: GET /api/stats/misc

    Parameters: None

    Returns:
        200 OK: JSON object containing various statistics.

        Response Schema:
        {
            "total_pages": <int>,           // Total pages in all first editions
            "stack_height_meters": <float>, // Stack height if all books piled up
            "hardback_count": <int>,        // Number of hardback first editions
            "paperback_count": <int>,       // Number of paperback first editions
            "total_editions": <int>,        // Total editions in database
            "total_works": <int>            // Total unique works in database
        }

        Example Response:
        {
            "total_pages": 1234567,
            "stack_height_meters": 185.19,
            "hardback_count": 500,
            "paperback_count": 2500,
            "total_editions": 3500,
            "total_works": 2800
        }

        Notes:
        - stack_height_meters is calculated assuming 100 pages = 15mm thickness
        - Only first editions (editionnum = 1) are counted for page/binding stats
        - Binding counts may not add up to total due to unknown binding types

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_misc())


@app.route('/api/stats/issuesperyear', methods=['GET'])
def api_stats_issuesperyear() -> Response:
    """
    Get count of magazine issues published per year.

    Endpoint: GET /api/stats/issuesperyear

    Parameters: None

    Returns:
        200 OK: JSON array of year statistics sorted by year (ascending).

        Response Schema:
        [
            {
                "year": <int>,   // Publication year
                "count": <int>   // Number of magazine issues
            },
            ...
        ]

        Example Response:
        [
            {"year": 1980, "count": 12},
            {"year": 1981, "count": 15},
            {"year": 1982, "count": 18},
            ...
        ]

        Use Case:
        - Track magazine publishing activity over time
        - Identify peak years for fanzine/magazine publishing
        - Visualize magazine issue counts as a time series

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_issuesperyear())


@app.route('/api/stats/nationalitycounts', methods=['GET'])
def api_stats_nationalitycounts() -> Response:
    """
    Get person counts grouped by nationality, with genre and role breakdown.

    Endpoint: GET /api/stats/nationalitycounts

    Parameters: None

    Returns:
        200 OK: JSON array of nationality statistics sorted by person count
                (descending).

        Response Schema:
        [
            {
                "nationality_id": <int|null>,  // Country ID, null for unknown
                "nationality": <string|null>,  // Country name, null for unknown
                "genres": {
                    "<genre_abbr>": {
                        "<role_name>": <count>,  // Person count per role
                        ...
                    },
                    ...
                },
                "count": <int>                 // Total person count
            },
            ...
        ]

        Example Request:
        GET /api/stats/nationalitycounts

        Example Response:
        [
            {
                "nationality_id": 1,
                "nationality": "Yhdysvallat",
                "genres": {
                    "SF": {"kirjoittaja": 150, "kääntäjä": 30},
                    "F": {"kirjoittaja": 40, "kääntäjä": 10}
                },
                "count": 200
            },
            {
                "nationality_id": 2,
                "nationality": "Iso-Britannia",
                "genres": {
                    "SF": {"kirjoittaja": 100, "kääntäjä": 20}
                },
                "count": 120
            },
            {
                "nationality_id": null,
                "nationality": null,
                "genres": {"SF": {"kirjoittaja": 15, "kääntäjä": 5}},
                "count": 20
            }
        ]

        Use Case:
        - Analyze the distribution of persons by nationality
        - Filter by role within each genre (e.g., all who translated fantasy)
        - Create visualizations showing which countries' contributors are most
          represented in the database

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_nationalitycounts())


@app.route('/api/stats/storynationalitycounts', methods=['GET'])
def api_stats_storynationalitycounts() -> Response:
    """
    Get person counts (short story contributors) grouped by nationality.

    Endpoint: GET /api/stats/storynationalitycounts

    Parameters: None

    Returns:
        200 OK: JSON array of nationality statistics sorted by person
                count (descending).

        Response Schema:
        [
            {
                "nationality_id": <int|null>,  // Country ID, null for unknown
                "nationality": <string|null>,  // Country name, null for unknown
                "storytypes": {
                    "<storytype_name>": {
                        "<role_name>": <count>,  // Person count per role
                        ...
                    },
                    ...
                },
                "count": <int>                 // Total persons
            },
            ...
        ]

        Example Response:
        [
            {
                "nationality_id": 1,
                "nationality": "Yhdysvallat",
                "storytypes": {
                    "novelli": {"kirjoittaja": 100, "kääntäjä": 20},
                    "kertomus": {"kirjoittaja": 50, "kääntäjä": 10}
                },
                "count": 180
            },
            {
                "nationality_id": 2,
                "nationality": "Iso-Britannia",
                "storytypes": {
                    "novelli": {"kirjoittaja": 80, "kääntäjä": 15}
                },
                "count": 120
            },
            {
                "nationality_id": null,
                "nationality": null,
                "storytypes": {"novelli": {"kirjoittaja": 10, "kääntäjä": 5}},
                "count": 20
            }
        ]

        Use Case:
        - Analyze the distribution of short story contributors by nationality
        - Filter by story type and role (e.g., all who translated novellas)
        - Compare domestic vs. foreign representation by story type

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_storynationalitycounts())


@app.route('/api/stats/filterstories', methods=['GET'])
def api_stats_filterstories() -> Response:
    """
    Get short stories matching the given filters.

    Endpoint: GET /api/stats/filterstories

    Query Parameters:
        storytype (int, optional): Story type ID to filter by.
                                   Use /api/shorttypes to get available types.
        language (int, optional): Language ID to filter by.
                                  Use /api/languages to get available languages.
        pubyear_min (int, optional): Minimum publication year (inclusive).
        pubyear_max (int, optional): Maximum publication year (inclusive).
                                     Can be used with pubyear_min for ranges.

    Returns:
        200 OK: JSON array of short story objects in ShortBriefestSchema format,
                sorted by title (ascending).

        Response Schema:
        [
            {
                "id": <int>,                // Short story ID
                "title": <string>,          // Finnish title
                "orig_title": <string|null>,// Original title
                "pubyear": <int|null>,      // Original publication year
                "type": {                   // Story type object
                    "id": <int>,
                    "name": <string>
                },
                "lang": {                   // Language object
                    "id": <int>,
                    "name": <string>
                },
                "contributors": [           // List of contributors
                    {
                        "person": {
                            "id": <int>,
                            "name": <string>,
                            "alt_name": <string|null>
                        },
                        "role": {
                            "id": <int>,
                            "name": <string>
                        }
                    },
                    ...
                ]
            },
            ...
        ]

        Example Requests:
        GET /api/stats/filterstories?storytype=1
        GET /api/stats/filterstories?language=2&pubyear_min=1950&pubyear_max=1960
        GET /api/stats/filterstories?storytype=1&language=1

        Example Response:
        [
            {
                "id": 123,
                "title": "Avaruuden valloittajat",
                "orig_title": "Space Conquerors",
                "pubyear": 1955,
                "type": {"id": 1, "name": "novelli"},
                "lang": {"id": 2, "name": "englanti"},
                "contributors": [
                    {
                        "person": {"id": 456, "name": "Asimov, Isaac", "alt_name": "Isaac Asimov"},
                        "role": {"id": 1, "name": "kirjoittaja"}
                    }
                ]
            }
        ]

        Use Case:
        - Browse short stories by type (novellas, tales, poems, etc.)
        - Find stories from a specific language or time period
        - Build filtered views for short story statistics pages

        500 Internal Server Error: Database or serialization error occurred.
    """
    storytype_id = request.args.get('storytype', default=None, type=int)
    language_id = request.args.get('language', default=None, type=int)
    pubyear_min = request.args.get('pubyear_min', default=None, type=int)
    pubyear_max = request.args.get('pubyear_max', default=None, type=int)
    return make_api_response(stats_filterstories(
        storytype_id, language_id, pubyear_min, pubyear_max))


@app.route('/api/stats/filterworks', methods=['GET'])
def api_stats_filterworks() -> Response:
    """
    Get works matching the given filters.

    Endpoint: GET /api/stats/filterworks

    Query Parameters:
        language (int, optional): Language ID to filter by.
                                  Use /api/languages to get available languages.
        orig_year_min (int, optional): Minimum original publication year (inclusive).
        orig_year_max (int, optional): Maximum original publication year (inclusive).
        edition_year_min (int, optional): Minimum first Finnish edition year (inclusive).
        edition_year_max (int, optional): Maximum first Finnish edition year (inclusive).

    Note: orig_year and edition_year filters are mutually exclusive.
          If both are provided, orig_year takes precedence.

    Returns:
        200 OK: JSON array of work objects in WorkBriefSchema format,
                sorted by title (ascending).

        Response Schema:
        [
            {
                "id": <int>,                 // Work ID
                "title": <string>,           // Finnish title
                "orig_title": <string|null>, // Original title
                "author_str": <string|null>, // Author string
                "pubyear": <int|null>,       // Original publication year
                "contributions": [           // List of contributors
                    {
                        "person": {
                            "id": <int>,
                            "name": <string>,
                            "alt_name": <string|null>
                        },
                        "role": {
                            "id": <int>,
                            "name": <string>
                        }
                    },
                    ...
                ],
                "editions": [                // List of editions
                    {
                        "id": <int>,
                        "title": <string>,
                        "pubyear": <int|null>
                    },
                    ...
                ],
                "genres": [                  // List of genres
                    {
                        "id": <int>,
                        "abbr": <string>,
                        "name": <string>
                    },
                    ...
                ],
                "language_name": {           // Language object
                    "id": <int>,
                    "name": <string>
                }
            },
            ...
        ]

        Example Requests:
        GET /api/stats/filterworks?language=2
        GET /api/stats/filterworks?orig_year_min=1950&orig_year_max=1960
        GET /api/stats/filterworks?edition_year_min=1980&edition_year_max=1989
        GET /api/stats/filterworks?language=1&orig_year_min=1900

        Example Response:
        [
            {
                "id": 123,
                "title": "Säätiö",
                "orig_title": "Foundation",
                "author_str": "Asimov, Isaac",
                "pubyear": 1951,
                "contributions": [
                    {
                        "person": {"id": 456, "name": "Asimov, Isaac", "alt_name": "Isaac Asimov"},
                        "role": {"id": 1, "name": "kirjoittaja"}
                    }
                ],
                "editions": [
                    {"id": 789, "title": "Säätiö", "pubyear": 1975}
                ],
                "genres": [{"id": 1, "abbr": "SF", "name": "Science Fiction"}],
                "language_name": {"id": 2, "name": "englanti"}
            }
        ]

        Use Case:
        - Browse works by original language
        - Find works from a specific time period (original publication)
        - Find works first published in Finland during a specific period
        - Build filtered views for work statistics pages

        500 Internal Server Error: Database or serialization error occurred.
    """
    language_id = request.args.get('language', default=None, type=int)
    orig_year_min = request.args.get('orig_year_min', default=None, type=int)
    orig_year_max = request.args.get('orig_year_max', default=None, type=int)
    edition_year_min = request.args.get('edition_year_min', default=None, type=int)
    edition_year_max = request.args.get('edition_year_max', default=None, type=int)
    return make_api_response(stats_filterworks(
        language_id, orig_year_min, orig_year_max, edition_year_min, edition_year_max))


@app.route('/api/stats/storiesbyyear', methods=['GET'])
def api_stats_storiesbyyear() -> Response:
    """
    Get count of short stories by original publication year.

    Endpoint: GET /api/stats/storiesbyyear

    Parameters: None

    Returns:
        200 OK: JSON array of year statistics sorted by year (ascending),
                then by story type, then by language.

        Response Schema:
        [
            {
                "year": <int>,                    // Original publication year
                "count": <int>,                   // Number of short stories
                "storytype_id": <int|null>,       // Story type ID
                "storytype_name": <string|null>,  // Story type name
                "language_id": <int|null>,        // Original language ID
                "language_name": <string|null>    // Original language name
            },
            ...
        ]

        Example Response:
        [
            {
                "year": 1950,
                "count": 10,
                "storytype_id": 1,
                "storytype_name": "novelli",
                "language_id": 2,
                "language_name": "englanti"
            },
            {
                "year": 1950,
                "count": 5,
                "storytype_id": 1,
                "storytype_name": "novelli",
                "language_id": 1,
                "language_name": "suomi"
            },
            {
                "year": 1951,
                "count": 15,
                "storytype_id": 2,
                "storytype_name": "kertomus",
                "language_id": 2,
                "language_name": "englanti"
            }
        ]

        Use Case:
        - Visualize short story publication trends over time
        - Compare story types by year
        - Analyze domestic vs. translated short fiction by year

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_storiesbyyear())
