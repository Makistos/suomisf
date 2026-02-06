"""Functions related to statistics."""
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, func, desc, or_
from sqlalchemy.exc import SQLAlchemyError

from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (
    Genre, Work, WorkGenre, Edition, Part, Publisher,
    Person, Contributor, Issue, Language, BindingType, Country
)
from app.types import HttpResponseCode
from app import app


def _log_query(name: str, query: Any) -> None:
    """Log the SQL query for debugging purposes with parameter values inline."""
    try:
        if hasattr(query, 'statement'):
            from sqlalchemy.dialects import mysql
            compiled = query.statement.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True}
            )
            app.logger.info(f'{name}: {str(compiled)}')
        else:
            app.logger.info(f'{name}: {str(query)}')
    except Exception as exp:
        # Fallback to basic string representation if literal_binds fails
        app.logger.info(f'{name}: {str(query)}')
        app.logger.error(f'{name}: Could not compile with literal_binds: {exp}')


def stats_genrecounts() -> ResponseType:
    """
    Get work counts for each genre.

    Returns:
        ResponseType: Dict with genre abbreviations as keys and counts as values.
            Example: {"SF": 1234, "F": 567, "K": 89, ...}
    """
    session = new_session()

    try:
        genres = session.query(Genre).all()
        genre_counts: Dict[str, int] = {}

        for genre in genres:
            query = session.query(WorkGenre)\
                .filter(WorkGenre.genre_id == genre.id)
            _log_query(f'stats_genrecounts ({genre.abbr})', query)
            count = query.count()
            genre_counts[genre.abbr] = count

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_genrecounts: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(genre_counts, HttpResponseCode.OK.value)


def stats_authorcounts(author_count: int = 10,
                       genre: Optional[str] = None) -> ResponseType:
    """
    Get the most productive authors with their work counts per genre.

    Args:
        author_count: Number of top authors to return. Default is 10.
        genre: Optional genre abbreviation (e.g., "SF", "F") to filter by.
               When set, returns authors with most works in that genre,
               sorted by their work count in that genre.

    Returns:
        ResponseType: List of dicts, each containing:
            - id: Person ID (int or None for "Muut")
            - name: Author name (str)
            - alt_name: Alternative name (str or None)
            - nationality: Author's nationality/country (str or None)
            - genres: Dict with genre abbreviations as keys and work counts as values
            - total: Total work count for this author

        The last item is always "Muut" (Others) containing aggregated
        counts for all authors not in the top list.

        Example:
        [
            {"id": 1, "name": "Asimov, Isaac", "alt_name": "Isaac Asimov",
             "nationality": "Yhdysvallat", "genres": {"SF": 50, "F": 5}, "total": 55},
            ...
            {"id": null, "name": "Muut", "alt_name": null,
             "nationality": null, "genres": {"SF": 1000, "F": 500}, "total": 1500}
        ]
    """
    session = new_session()

    try:
        genres = session.query(Genre).all()
        genre_abbrs = {g.id: g.abbr for g in genres}
        genre_ids = {g.abbr: g.id for g in genres}

        # Validate genre parameter if provided
        filter_genre_id = None
        if genre:
            filter_genre_id = genre_ids.get(genre)
            if filter_genre_id is None:
                return ResponseType(f'Tuntematon genre: {genre}',
                                    HttpResponseCode.BAD_REQUEST.value)

        # Get all authors with their work counts
        # Authors are those with role_id = 1 (author) in Contributor table
        author_query = session.query(
            Person.id,
            Person.name,
            Person.alt_name,
            Person.nationality_id,
            func.count(func.distinct(Work.id)).label('work_count')
        ).join(
            Contributor, Contributor.person_id == Person.id
        ).join(
            Part, Part.id == Contributor.part_id
        ).join(
            Work, Work.id == Part.work_id
        )

        # Add genre filter if specified
        if filter_genre_id:
            author_query = author_query.join(
                WorkGenre, WorkGenre.work_id == Work.id
            ).filter(
                WorkGenre.genre_id == filter_genre_id
            )

        author_query = author_query.filter(
            Contributor.role_id == 1,  # Author role
            Part.shortstory_id.is_(None)  # Only works, not short stories
        ).group_by(
            Person.id
        ).order_by(
            desc('work_count')
        )
        _log_query('stats_authorcounts (main)', author_query)
        author_counts = author_query.all()

        # Get country names for lookup
        countries = {c.id: c.name for c in session.query(Country).all()}

        result: List[Dict[str, Any]] = []
        other_genres: Dict[str, int] = {g.abbr: 0 for g in genres}
        other_total = 0

        for idx, author_data in enumerate(author_counts):
            # Get genre breakdown for this author
            genre_query = session.query(
                Genre.id,
                func.count(func.distinct(Work.id)).label('count')
            ).join(
                WorkGenre, WorkGenre.genre_id == Genre.id
            ).join(
                Work, Work.id == WorkGenre.work_id
            ).join(
                Part, Part.work_id == Work.id
            ).join(
                Contributor, Contributor.part_id == Part.id
            ).filter(
                Contributor.person_id == author_data.id,
                Contributor.role_id == 1,
                Part.shortstory_id.is_(None)
            ).group_by(
                Genre.id
            )
            if idx == 0:  # Only log for first author to avoid spam
                _log_query('stats_authorcounts (genre breakdown)', genre_query)
            author_genres = genre_query.all()

            genre_dict = {genre_abbrs[ag.id]: ag.count for ag in author_genres}

            if idx < author_count:
                result.append({
                    'id': author_data.id,
                    'name': author_data.name,
                    'alt_name': author_data.alt_name,
                    'nationality': countries.get(author_data.nationality_id),
                    'genres': genre_dict,
                    'total': author_data.work_count
                })
            else:
                # Add to "others" aggregation
                for genre_id, count in [(ag.id, ag.count) for ag in author_genres]:
                    other_genres[genre_abbrs[genre_id]] += count
                other_total += author_data.work_count

        # Add "Muut" (Others) entry
        result.append({
            'id': None,
            'name': 'Muut',
            'alt_name': None,
            'nationality': None,
            'genres': other_genres,
            'total': other_total
        })

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_authorcounts: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_publishercounts(pub_count: int = 10) -> ResponseType:
    """
    Get the biggest publishers with their work counts per genre.

    Args:
        pub_count: Number of top publishers to return. Default is 10.

    Returns:
        ResponseType: List of dicts, each containing:
            - id: Publisher ID (int or None for "Muut")
            - name: Publisher short name (str)
            - fullname: Publisher full name (str or None)
            - genres: Dict with genre abbreviations as keys and edition counts
            - total: Total edition count for this publisher

        The last item is always "Muut" (Others) containing aggregated
        counts for all publishers not in the top list.

        Example:
        [
            {"id": 1, "name": "WSOY", "fullname": "Werner Söderström Oy",
             "genres": {"SF": 200, "F": 150}, "total": 350},
            ...
            {"id": null, "name": "Muut", "fullname": null,
             "genres": {"SF": 500, "F": 300}, "total": 800}
        ]
    """
    session = new_session()

    try:
        genres = session.query(Genre).all()
        genre_abbrs = {g.id: g.abbr for g in genres}

        # Get all publishers with their edition counts
        publisher_query = session.query(
            Publisher.id,
            Publisher.name,
            Publisher.fullname,
            func.count(func.distinct(Edition.id)).label('edition_count')
        ).join(
            Edition, Edition.publisher_id == Publisher.id
        ).group_by(
            Publisher.id
        ).order_by(
            desc('edition_count')
        )
        _log_query('stats_publishercounts (main)', publisher_query)
        publisher_counts = publisher_query.all()

        result: List[Dict[str, Any]] = []
        other_genres: Dict[str, int] = {g.abbr: 0 for g in genres}
        other_total = 0

        for idx, pub_data in enumerate(publisher_counts):
            # Get genre breakdown for this publisher
            genre_query = session.query(
                Genre.id,
                func.count(func.distinct(Edition.id)).label('count')
            ).join(
                WorkGenre, WorkGenre.genre_id == Genre.id
            ).join(
                Work, Work.id == WorkGenre.work_id
            ).join(
                Part, Part.work_id == Work.id
            ).join(
                Edition, Edition.id == Part.edition_id
            ).filter(
                Edition.publisher_id == pub_data.id,
                Part.shortstory_id.is_(None)
            ).group_by(
                Genre.id
            )
            if idx == 0:  # Only log for first publisher to avoid spam
                _log_query('stats_publishercounts (genre breakdown)',
                           genre_query)
            pub_genres = genre_query.all()

            genre_dict = {genre_abbrs[pg.id]: pg.count for pg in pub_genres}

            if idx < pub_count:
                result.append({
                    'id': pub_data.id,
                    'name': pub_data.name,
                    'fullname': pub_data.fullname,
                    'genres': genre_dict,
                    'total': pub_data.edition_count
                })
            else:
                # Add to "others" aggregation
                for genre_id, count in [(pg.id, pg.count) for pg in pub_genres]:
                    other_genres[genre_abbrs[genre_id]] += count
                other_total += pub_data.edition_count

        # Add "Muut" (Others) entry
        result.append({
            'id': None,
            'name': 'Muut',
            'fullname': None,
            'genres': other_genres,
            'total': other_total
        })

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_publishercounts: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_worksbyyear() -> ResponseType:
    """
    Get count of first editions published by year, grouped by language.

    Returns:
        ResponseType: List of dicts, each containing:
            - year: Publication year (int)
            - count: Number of first editions published that year (int)
            - language_id: Language ID (int or None)
            - language_name: Language name (str or None)

        Sorted by year ascending, then by language name.

        Example:
        [
            {"year": 1950, "count": 5, "language_id": 1, "language_name": "suomi"},
            {"year": 1950, "count": 2, "language_id": 2, "language_name": "englanti"},
            {"year": 1951, "count": 8, "language_id": 1, "language_name": "suomi"},
            ...
        ]
    """
    session = new_session()

    try:
        # Get first editions (editionnum = 1 or version = 1) by year and language
        query = session.query(
            Edition.pubyear,
            func.count(Edition.id).label('count'),
            Language.id.label('language_id'),
            Language.name.label('language_name')
        ).outerjoin(
            Part, and_(Part.edition_id == Edition.id,
                       Part.shortstory_id.is_(None))
        ).outerjoin(
            Work, Work.id == Part.work_id
        ).outerjoin(
            Language, Language.id == Work.language
        ).filter(
            or_(Edition.editionnum == 1, Edition.editionnum.is_(None)),  # First editions
            or_(Edition.version == 1, Edition.version.is_(None))      # First version
        ).group_by(
            Edition.pubyear,
            Language.id
        ).order_by(
            Edition.pubyear,
            Language.name
        )
        _log_query('stats_worksbyyear', query)
        results = query.all()

        result = [
            {
                'year': r.pubyear,
                'count': r.count,
                'language_id': r.language_id,
                'language_name': r.language_name
            }
            for r in results if r.pubyear is not None
        ]

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_worksbyyear: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_origworksbyyear() -> ResponseType:
    """
    Get count of original work publications by year, grouped by language.

    This counts the original publication year of works (Work.pubyear),
    not the Finnish edition publication year.

    Returns:
        ResponseType: List of dicts, each containing:
            - year: Original publication year (int)
            - count: Number of works originally published that year (int)
            - language_id: Language ID (int or None)
            - language_name: Language name (str or None)

        Sorted by year ascending, then by language name.

        Example:
        [
            {"year": 1920, "count": 3, "language_id": 2, "language_name": "englanti"},
            {"year": 1921, "count": 5, "language_id": 2, "language_name": "englanti"},
            ...
        ]
    """
    session = new_session()

    try:
        query = session.query(
            Work.pubyear,
            func.count(Work.id).label('count'),
            Language.id.label('language_id'),
            Language.name.label('language_name')
        ).outerjoin(
            Language, Language.id == Work.language
        ).filter(
            Work.pubyear.isnot(None),
            Work.pubyear > 0
        ).group_by(
            Work.pubyear,
            Language.id
        ).order_by(
            Work.pubyear,
            Language.name
        )
        _log_query('stats_origworksbyyear', query)
        results = query.all()

        result = [
            {
                'year': r.pubyear,
                'count': r.count,
                'language_id': r.language_id,
                'language_name': r.language_name
            }
            for r in results
        ]

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_origworksbyyear: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_misc() -> ResponseType:
    """
    Get miscellaneous statistics about the database.

    Returns:
        ResponseType: Dict containing:
            - total_pages: Total number of pages in all first editions (int)
            - stack_height_meters: Height in meters if all first editions were
              stacked (float). Calculated assuming 100 pages = 15mm.
            - hardback_count: Number of hardback first editions (int)
            - paperback_count: Number of paperback first editions (int)
            - total_editions: Total number of editions (int)
            - total_works: Total number of works (int)

        Example:
        {
            "total_pages": 1234567,
            "stack_height_meters": 185.19,
            "hardback_count": 500,
            "paperback_count": 2500,
            "total_editions": 3500,
            "total_works": 2800
        }
    """
    session = new_session()

    try:
        # Get total pages from first editions
        page_query = session.query(
            func.sum(Edition.pages)
        ).filter(
            Edition.editionnum.in_([None, 1]),
            Edition.version.in_([None, 1]),
            Edition.pages.isnot(None)
        )
        _log_query('stats_misc (total_pages)', page_query)
        page_result = page_query.scalar()

        total_pages = int(page_result) if page_result else 0

        # Calculate stack height (100 pages = 15mm = 0.015m)
        stack_height_meters = round((total_pages / 100) * 0.015, 2)

        # Count hardback and paperback (binding_id: 2 = hardback, 3 = paperback typically)
        # Need to check actual binding types in database
        bindings = session.query(BindingType).all()
        binding_map = {b.id: b.name.lower() if b.name else '' for b in bindings}

        hardback_ids = [bid for bid, name in binding_map.items()
                        if 'kovakantinen' in name or 'sidottu' in name or
                        'hardback' in name or 'hard' in name]
        paperback_ids = [bid for bid, name in binding_map.items()
                         if 'pehmeäkantinen' in name or 'nidottu' in name or
                         'paperback' in name or 'soft' in name or 'pokkari' in name]

        hardback_query = session.query(func.count(Edition.id)).filter(
            Edition.editionnum.in_([None, 1]),
            Edition.version.in_([None, 1]),
            Edition.binding_id.in_(hardback_ids) if hardback_ids else False
        )
        _log_query('stats_misc (hardback_count)', hardback_query)
        hardback_count = hardback_query.scalar() or 0

        paperback_query = session.query(func.count(Edition.id)).filter(
            Edition.editionnum.in_([None, 1]),
            Edition.version.in_([None, 1]),
            Edition.binding_id.in_(paperback_ids) if paperback_ids else False
        )
        _log_query('stats_misc (paperback_count)', paperback_query)
        paperback_count = paperback_query.scalar() or 0

        editions_query = session.query(func.count(Edition.id))
        _log_query('stats_misc (total_editions)', editions_query)
        total_editions = editions_query.scalar() or 0

        works_query = session.query(func.count(Work.id))
        _log_query('stats_misc (total_works)', works_query)
        total_works = works_query.scalar() or 0

        result = {
            'total_pages': total_pages,
            'stack_height_meters': stack_height_meters,
            'hardback_count': hardback_count,
            'paperback_count': paperback_count,
            'total_editions': total_editions,
            'total_works': total_works
        }

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_misc: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_issuesperyear() -> ResponseType:
    """
    Get count of magazine issues published per year.

    Returns:
        ResponseType: List of dicts, each containing:
            - year: Publication year (int)
            - count: Number of magazine issues published that year (int)

        Sorted by year ascending.

        Example:
        [
            {"year": 1980, "count": 12},
            {"year": 1981, "count": 15},
            ...
        ]
    """
    session = new_session()

    try:
        query = session.query(
            Issue.year,
            func.count(Issue.id).label('count')
        ).filter(
            Issue.year.isnot(None)
        ).group_by(
            Issue.year
        ).order_by(
            Issue.year
        )
        _log_query('stats_issuesperyear', query)
        results = query.all()

        result = [
            {'year': r.year, 'count': r.count}
            for r in results
        ]

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_issuesperyear: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_nationalitycounts() -> ResponseType:
    """
    Get work counts grouped by author nationality.

    Returns:
        ResponseType: List of dicts, each containing:
            - nationality_id: Country ID (int or None for unknown)
            - nationality: Country name (str or None for unknown)
            - count: Number of works by authors of this nationality (int)

        Sorted by count descending.

        Example:
        [
            {"nationality_id": 1, "nationality": "Yhdysvallat", "count": 500},
            {"nationality_id": 2, "nationality": "Iso-Britannia", "count": 300},
            {"nationality_id": null, "nationality": null, "count": 50},
            ...
        ]
    """
    session = new_session()

    try:
        query = session.query(
            Country.id.label('nationality_id'),
            Country.name.label('nationality'),
            func.count(func.distinct(Work.id)).label('count')
        ).select_from(
            Person
        ).outerjoin(
            Country, Country.id == Person.nationality_id
        ).join(
            Contributor, Contributor.person_id == Person.id
        ).join(
            Part, Part.id == Contributor.part_id
        ).join(
            Work, Work.id == Part.work_id
        ).filter(
            Contributor.role_id == 1,  # Author role
            Part.shortstory_id.is_(None)  # Only works, not short stories
        ).group_by(
            Country.id,
            Country.name
        ).order_by(
            desc('count')
        )
        _log_query('stats_nationalitycounts', query)
        results = query.all()

        result = [
            {
                'nationality_id': r.nationality_id,
                'nationality': r.nationality,
                'count': r.count
            }
            for r in results
        ]

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_nationalitycounts: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)
