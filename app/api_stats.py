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
    stats_authorcounts,
    stats_publishercounts,
    stats_worksbyyear,
    stats_origworksbyyear,
    stats_misc,
    stats_issuesperyear,
    stats_nationalitycounts
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


@app.route('/api/stats/authorcounts', methods=['GET'])
def api_stats_authorcounts() -> Response:
    """
    Get the most productive authors with their work counts per genre.

    Endpoint: GET /api/stats/authorcounts

    Query Parameters:
        count (int, optional): Number of top authors to return. Default: 10.
                               Must be a positive integer.
        genre (string, optional): Genre abbreviation to filter by (e.g., "SF",
                                  "F", "K"). When set, returns authors sorted
                                  by their work count in that specific genre.

    Returns:
        200 OK: JSON array of author objects sorted by total work count
                (descending), or by work count in specified genre if the
                genre parameter is provided. The last item is always "Muut"
                (Others) containing aggregated counts for all authors not
                in top list.

        Response Schema:
        [
            {
                "id": <int|null>,      // Person ID, null for "Muut"
                "name": <string>,      // Author name (Last, First format)
                "alt_name": <string|null>,  // Display name (First Last format)
                "nationality": <string|null>,  // Author's nationality/country
                "genres": {
                    "<genre_abbr>": <count>,  // Work count per genre
                    ...
                },
                "total": <int>         // Total work count
            },
            ...
        ]

        Example Request:
        GET /api/stats/authorcounts?count=5
        GET /api/stats/authorcounts?count=5&genre=SF

        Example Response:
        [
            {
                "id": 123,
                "name": "Asimov, Isaac",
                "alt_name": "Isaac Asimov",
                "nationality": "Yhdysvallat",
                "genres": {"SF": 50, "F": 5},
                "total": 55
            },
            {
                "id": 456,
                "name": "Clarke, Arthur C.",
                "alt_name": "Arthur C. Clarke",
                "nationality": "Iso-Britannia",
                "genres": {"SF": 45},
                "total": 45
            },
            ...
            {
                "id": null,
                "name": "Muut",
                "alt_name": null,
                "nationality": null,
                "genres": {"SF": 1000, "F": 500, "K": 200},
                "total": 1700
            }
        ]

        400 Bad Request: Invalid genre abbreviation provided.
        500 Internal Server Error: Database error occurred.
    """
    author_count = request.args.get('count', default=10, type=int)
    if author_count < 1:
        author_count = 10
    genre = request.args.get('genre', default=None, type=str)
    return make_api_response(stats_authorcounts(author_count, genre))


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
    Get work counts grouped by author nationality.

    Endpoint: GET /api/stats/nationalitycounts

    Parameters: None

    Returns:
        200 OK: JSON array of nationality statistics sorted by work count
                (descending).

        Response Schema:
        [
            {
                "nationality_id": <int|null>,  // Country ID, null for unknown
                "nationality": <string|null>,  // Country name, null for unknown
                "count": <int>                 // Number of works
            },
            ...
        ]

        Example Response:
        [
            {"nationality_id": 1, "nationality": "Yhdysvallat", "count": 500},
            {"nationality_id": 2, "nationality": "Iso-Britannia", "count": 300},
            {"nationality_id": 3, "nationality": "Suomi", "count": 150},
            {"nationality_id": null, "nationality": null, "count": 50}
        ]

        Use Case:
        - Analyze the distribution of works by author nationality
        - Create visualizations showing which countries' authors are most
          represented in the database
        - Compare domestic vs. foreign author representation

        500 Internal Server Error: Database error occurred.
    """
    return make_api_response(stats_nationalitycounts())
