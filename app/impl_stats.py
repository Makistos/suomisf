"""Functions related to statistics."""
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, func, desc, or_
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (
    Genre, Work, WorkGenre, Edition, Part, Publisher,
    Person, Contributor, ContributorRole, Issue, Language, BindingType, Country,
    ShortStory, StoryType
)
from app.model import ShortBriefSchema, WorkBriefSchema
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


def stats_personcounts(count: int = 10,
                       genre: Optional[str] = None,
                       role_id: int = 1) -> ResponseType:
    """
    Get the most productive persons with their work counts per genre.

    Args:
        count: Number of top persons to return. Default is 10.
        genre: Optional genre abbreviation (e.g., "SF", "F") to filter by.
               When set, returns persons with most works in that genre,
               sorted by their work count in that genre.
        role_id: Role ID to filter by. Default is 1 (author).
                 Common values: 1 = author, 2 = translator, 3 = editor, etc.

    Returns:
        ResponseType: List of dicts, each containing:
            - id: Person ID (int or None for "Muut")
            - name: Person name (str)
            - alt_name: Alternative name (str or None)
            - nationality: Person's nationality/country (str or None)
            - genres: Dict with genre abbreviations as keys, each containing
                      a dict of role names to counts
            - total: Total work count for this person

        The last item is always "Muut" (Others) containing aggregated
        counts for all persons not in the top list.

        Example:
        [
            {"id": 1, "name": "Asimov, Isaac", "alt_name": "Isaac Asimov",
             "nationality": "Yhdysvallat",
             "genres": {"SF": {"kirjoittaja": 50}, "F": {"kirjoittaja": 5}},
             "total": 55},
            ...
            {"id": null, "name": "Muut", "alt_name": null,
             "nationality": null, "genres": {...}, "total": 1500}
        ]
    """
    session = new_session()

    try:
        genres = session.query(Genre).all()
        genre_ids = {g.abbr: g.id for g in genres}

        # Get all roles for lookup
        roles = session.query(ContributorRole).all()

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
            Contributor.role_id == role_id,
            Part.shortstory_id.is_(None)  # Only works, not short stories
        ).group_by(
            Person.id
        ).order_by(
            desc('work_count')
        )
        _log_query('stats_personcounts (main)', author_query)
        author_counts = author_query.all()

        # Get country names for lookup
        countries = {c.id: c.name for c in session.query(Country).all()}

        result: List[Dict[str, Any]] = []
        # Initialize other_genres as nested dict: {genre: {role: count}}
        other_genres: Dict[str, Dict[str, int]] = {}
        for g in genres:
            other_genres[g.abbr] = {r.name: 0 for r in roles if r.name}
        other_total = 0

        for idx, author_data in enumerate(author_counts):
            # Get genre + role breakdown for this person
            genre_query = session.query(
                Genre.id.label('genre_id'),
                Genre.abbr.label('genre_abbr'),
                ContributorRole.id.label('role_id'),
                ContributorRole.name.label('role_name'),
                func.count(func.distinct(Work.id)).label('count')
            ).join(
                WorkGenre, WorkGenre.genre_id == Genre.id
            ).join(
                Work, Work.id == WorkGenre.work_id
            ).join(
                Part, Part.work_id == Work.id
            ).join(
                Contributor, Contributor.part_id == Part.id
            ).join(
                ContributorRole, ContributorRole.id == Contributor.role_id
            ).filter(
                Contributor.person_id == author_data.id,
                Part.shortstory_id.is_(None)
            ).group_by(
                Genre.id,
                ContributorRole.id
            )
            if idx == 0:  # Only log for first author to avoid spam
                _log_query('stats_personcounts (genre breakdown)', genre_query)
            author_genres = genre_query.all()

            # Build nested dict: {genre_abbr: {role_name: count}}
            genre_dict: Dict[str, Dict[str, int]] = {}
            for ag in author_genres:
                if ag.genre_abbr and ag.role_name:
                    if ag.genre_abbr not in genre_dict:
                        genre_dict[ag.genre_abbr] = {}
                    genre_dict[ag.genre_abbr][ag.role_name] = ag.count

            if idx < count:
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
                for ag in author_genres:
                    if ag.genre_abbr and ag.role_name:
                        other_genres[ag.genre_abbr][ag.role_name] += ag.count
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


def stats_storypersoncounts(count: int = 10,
                            role_id: int = 1,
                            storytype_id: Optional[int] = None) -> ResponseType:
    """
    Get the most productive persons with their short story counts.

    Args:
        count: Number of top persons to return. Default is 10.
        role_id: Role ID to filter by. Default is 1 (author).
                 Common values: 1 = author, 2 = translator, 3 = editor, etc.
        storytype_id: Optional story type ID to filter by.
                      When set, only counts stories of that type.

    Returns:
        ResponseType: List of dicts, each containing:
            - id: Person ID (int or None for "Muut")
            - name: Person name (str)
            - alt_name: Alternative name (str or None)
            - nationality: Person's nationality/country (str or None)
            - storytypes: Dict with story type names as keys, each containing
                          a dict of role names to counts
            - total: Total short story count for this person

        The last item is always "Muut" (Others) containing aggregated
        counts for all persons not in the top list.

        Example:
        [
            {"id": 1, "name": "Asimov, Isaac", "alt_name": "Isaac Asimov",
             "nationality": "Yhdysvallat",
             "storytypes": {"novelli": {"kirjoittaja": 30}, "kertomus": {"kirjoittaja": 25}},
             "total": 55},
            ...
            {"id": null, "name": "Muut", "alt_name": null,
             "nationality": null, "storytypes": {...}, "total": 1500}
        ]
    """
    session = new_session()

    try:
        # Get all story types for lookup
        storytypes = session.query(StoryType).all()
        storytype_names = {st.id: st.name for st in storytypes}

        # Get all roles for lookup
        roles = session.query(ContributorRole).all()

        # Validate storytype_id if provided
        if storytype_id is not None and storytype_id not in storytype_names:
            return ResponseType(f'Tuntematon tarinatyyppi: {storytype_id}',
                                HttpResponseCode.BAD_REQUEST.value)

        # Get all persons with their short story counts
        person_query = session.query(
            Person.id,
            Person.name,
            Person.alt_name,
            Person.nationality_id,
            func.count(func.distinct(ShortStory.id)).label('story_count')
        ).join(
            Contributor, and_(
                Contributor.person_id == Person.id,
                Contributor.role_id == role_id
            )
        ).join(
            Part, and_(
                Part.id == Contributor.part_id,
                Part.shortstory_id.isnot(None)
            )
        ).join(
            ShortStory, ShortStory.id == Part.shortstory_id
        )

        # Add storytype filter if specified
        if storytype_id is not None:
            person_query = person_query.filter(
                ShortStory.story_type == storytype_id
            )

        person_query = person_query.group_by(
            Person.id
        ).order_by(
            desc('story_count')
        )
        _log_query('stats_storypersoncounts (main)', person_query)
        person_counts = person_query.all()

        # Get country names for lookup
        countries = {c.id: c.name for c in session.query(Country).all()}

        result: List[Dict[str, Any]] = []
        # Initialize other_storytypes as nested dict: {storytype: {role: count}}
        other_storytypes: Dict[str, Dict[str, int]] = {}
        for st in storytypes:
            if st.name:
                other_storytypes[st.name] = {r.name: 0 for r in roles if r.name}
        other_total = 0

        for idx, person_data in enumerate(person_counts):
            # Get storytype + role breakdown for this person
            storytype_query = session.query(
                StoryType.id.label('storytype_id'),
                StoryType.name.label('storytype_name'),
                ContributorRole.id.label('role_id'),
                ContributorRole.name.label('role_name'),
                func.count(func.distinct(ShortStory.id)).label('count')
            ).join(
                ShortStory, ShortStory.story_type == StoryType.id
            ).join(
                Part, Part.shortstory_id == ShortStory.id
            ).join(
                Contributor, Contributor.part_id == Part.id
            ).join(
                ContributorRole, ContributorRole.id == Contributor.role_id
            ).filter(
                Contributor.person_id == person_data.id
            )

            if storytype_id is not None:
                storytype_query = storytype_query.filter(
                    ShortStory.story_type == storytype_id
                )

            storytype_query = storytype_query.group_by(
                StoryType.id,
                ContributorRole.id
            )
            if idx == 0:  # Only log for first person to avoid spam
                _log_query('stats_storypersoncounts (storytype breakdown)',
                           storytype_query)
            person_storytypes = storytype_query.all()

            # Build nested dict: {storytype_name: {role_name: count}}
            storytype_dict: Dict[str, Dict[str, int]] = {}
            for st in person_storytypes:
                if st.storytype_name and st.role_name:
                    if st.storytype_name not in storytype_dict:
                        storytype_dict[st.storytype_name] = {}
                    storytype_dict[st.storytype_name][st.role_name] = st.count

            if idx < count:
                result.append({
                    'id': person_data.id,
                    'name': person_data.name,
                    'alt_name': person_data.alt_name,
                    'nationality': countries.get(person_data.nationality_id),
                    'storytypes': storytype_dict,
                    'total': person_data.story_count
                })
            else:
                # Add to "others" aggregation
                for st in person_storytypes:
                    if st.storytype_name and st.role_name:
                        other_storytypes[st.storytype_name][st.role_name] += st.count
                other_total += person_data.story_count

        # Add "Muut" (Others) entry
        result.append({
            'id': None,
            'name': 'Muut',
            'alt_name': None,
            'nationality': None,
            'storytypes': other_storytypes,
            'total': other_total
        })

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_storypersoncounts: Database error: {exp}')
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
    Get person counts grouped by nationality, with genre and role breakdown.

    Only includes persons who have at least one work in any role
    (in Contributor table, pointing to a Part with shortstory_id = NULL).

    Returns:
        ResponseType: List of dicts, each containing:
            - nationality_id: Country ID (int or None for unknown)
            - nationality: Country name (str or None for unknown)
            - genres: Dict with genre abbreviations as keys, each containing
                      a dict of role names to person counts
            - count: Total person count for this nationality (int)

        Sorted by count descending.

        Example:
        [
            {"nationality_id": 1, "nationality": "Yhdysvallat",
             "genres": {"SF": {"kirjoittaja": 150, "kääntäjä": 30},
                        "F": {"kirjoittaja": 40, "kääntäjä": 10}},
             "count": 200},
            {"nationality_id": 2, "nationality": "Iso-Britannia",
             "genres": {"SF": {"kirjoittaja": 100, "kääntäjä": 20}},
             "count": 120},
            ...
        ]
    """
    session = new_session()

    try:
        # Subquery to check if person has at least one work contribution
        has_work = session.query(Contributor.person_id).join(
            Part, and_(
                Part.id == Contributor.part_id,
                Part.shortstory_id.is_(None)
            )
        ).filter(
            Contributor.person_id == Person.id
        ).exists()

        # Main query to get person counts per nationality (each person counted once)
        query = session.query(
            Country.id.label('nationality_id'),
            Country.name.label('nationality'),
            func.count(Person.id).label('count')
        ).select_from(
            Person
        ).outerjoin(
            Country, Country.id == Person.nationality_id
        ).filter(
            has_work
        ).group_by(
            Country.id,
            Country.name
        ).order_by(
            desc('count')
        )
        _log_query('stats_nationalitycounts', query)
        results = query.all()

        result = []
        for r in results:
            # Get genre + role breakdown for this nationality (person counts)
            genre_query = session.query(
                Genre.id.label('genre_id'),
                Genre.abbr.label('genre_abbr'),
                ContributorRole.id.label('role_id'),
                ContributorRole.name.label('role_name'),
                func.count(func.distinct(Person.id)).label('count')
            ).select_from(
                Person
            ).join(
                Contributor, Contributor.person_id == Person.id
            ).join(
                Part, and_(
                    Part.id == Contributor.part_id,
                    Part.shortstory_id.is_(None)
                )
            ).join(
                Work, Work.id == Part.work_id
            ).join(
                WorkGenre, WorkGenre.work_id == Work.id
            ).join(
                Genre, Genre.id == WorkGenre.genre_id
            ).join(
                ContributorRole, ContributorRole.id == Contributor.role_id
            )

            if r.nationality_id is not None:
                genre_query = genre_query.filter(
                    Person.nationality_id == r.nationality_id
                )
            else:
                genre_query = genre_query.filter(
                    Person.nationality_id.is_(None)
                )

            genre_query = genre_query.group_by(Genre.id, ContributorRole.id)
            genre_results = genre_query.all()

            # Build nested dict: {genre_abbr: {role_name: count}}
            genre_dict: Dict[str, Dict[str, int]] = {}
            for gr in genre_results:
                if gr.genre_abbr and gr.role_name:
                    if gr.genre_abbr not in genre_dict:
                        genre_dict[gr.genre_abbr] = {}
                    genre_dict[gr.genre_abbr][gr.role_name] = gr.count

            result.append({
                'nationality_id': r.nationality_id,
                'nationality': r.nationality,
                'genres': genre_dict,
                'count': r.count
            })

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_nationalitycounts: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_storynationalitycounts() -> ResponseType:
    """
    Get short story counts grouped by author nationality.

    Only includes persons who have at least one short story as an author
    (role_id = 1 in Contributor table, pointing to a Part with
    shortstory_id != NULL).

    Returns:
        ResponseType: List of dicts, each containing:
            - nationality_id: Country ID (int or None for unknown)
            - nationality: Country name (str or None for unknown)
            - storytypes: Dict with story type names as keys, each containing
                          a dict of role names to person counts
            - count: Total persons for this nationality (int)

        Sorted by count descending.

        Example:
        [
            {"nationality_id": 1, "nationality": "Yhdysvallat",
             "storytypes": {"novelli": {"kirjoittaja": 100, "kääntäjä": 20},
                            "kertomus": {"kirjoittaja": 50, "kääntäjä": 10}},
             "count": 180},
            {"nationality_id": 2, "nationality": "Iso-Britannia",
             "storytypes": {"novelli": {"kirjoittaja": 80, "kääntäjä": 15}},
             "count": 120},
            ...
        ]
    """
    session = new_session()

    try:
        # Subquery to check if person has at least one short story contribution
        has_story = session.query(Contributor.person_id).join(
            Part, and_(
                Part.id == Contributor.part_id,
                Part.shortstory_id.isnot(None)
            )
        ).filter(
            Contributor.person_id == Person.id
        ).exists()

        # Main query to get person counts per nationality (each person counted once)
        query = session.query(
            Country.id.label('nationality_id'),
            Country.name.label('nationality'),
            func.count(Person.id).label('count')
        ).select_from(
            Person
        ).outerjoin(
            Country, Country.id == Person.nationality_id
        ).filter(
            has_story
        ).group_by(
            Country.id,
            Country.name
        ).order_by(
            desc('count')
        )
        _log_query('stats_storynationalitycounts', query)
        results = query.all()

        result = []
        for r in results:
            # Get storytype + role breakdown for this nationality (person counts)
            storytype_query = session.query(
                StoryType.id.label('storytype_id'),
                StoryType.name.label('storytype_name'),
                ContributorRole.id.label('role_id'),
                ContributorRole.name.label('role_name'),
                func.count(func.distinct(Person.id)).label('count')
            ).select_from(
                Person
            ).join(
                Contributor, Contributor.person_id == Person.id
            ).join(
                ContributorRole, ContributorRole.id == Contributor.role_id
            ).join(
                Part, and_(
                    Part.id == Contributor.part_id,
                    Part.shortstory_id.isnot(None)
                )
            ).join(
                ShortStory, ShortStory.id == Part.shortstory_id
            ).join(
                StoryType, StoryType.id == ShortStory.story_type
            )

            if r.nationality_id is not None:
                storytype_query = storytype_query.filter(
                    Person.nationality_id == r.nationality_id
                )
            else:
                storytype_query = storytype_query.filter(
                    Person.nationality_id.is_(None)
                )

            storytype_query = storytype_query.group_by(
                StoryType.id,
                ContributorRole.id
            )
            storytype_results = storytype_query.all()

            # Build nested dict: {storytype_name: {role_name: count}}
            storytype_dict: Dict[str, Dict[str, int]] = {}
            for st in storytype_results:
                if st.storytype_name and st.role_name:
                    if st.storytype_name not in storytype_dict:
                        storytype_dict[st.storytype_name] = {}
                    storytype_dict[st.storytype_name][st.role_name] = st.count

            result.append({
                'nationality_id': r.nationality_id,
                'nationality': r.nationality,
                'storytypes': storytype_dict,
                'count': r.count
            })

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_storynationalitycounts: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_filterstories(storytype_id: Optional[int] = None,
                        language_id: Optional[int] = None,
                        pubyear_min: Optional[int] = None,
                        pubyear_max: Optional[int] = None) -> ResponseType:
    """
    Get short stories matching the given filters.

    Args:
        storytype_id: Optional story type ID to filter by.
        language_id: Optional language ID to filter by.
        pubyear_min: Optional minimum publication year (inclusive).
        pubyear_max: Optional maximum publication year (inclusive).

    Returns:
        ResponseType: List of short stories in ShortBriefSchema format.
            Each item contains:
            - id: Short story ID (int)
            - title: Short story title (str)
            - orig_title: Original title (str or None)
            - pubyear: Publication year (int or None)
            - type: Story type object with id and name
            - lang: Language object with id and name
            - authors: List of author objects
            - contributors: List of contributor objects
            - issues: List of magazine issue objects
            - editions: List of edition objects
            - genres: List of genre objects

        Sorted by title ascending.

        Example:
        [
            {
                "id": 123,
                "title": "Tarinan nimi",
                "orig_title": "Original Title",
                "pubyear": 1950,
                "type": {"id": 1, "name": "novelli"},
                "lang": {"id": 2, "name": "englanti"},
                "authors": [{"id": 456, "name": "Asimov, Isaac"}],
                "contributors": [{"person": {...}, "role": {...}}],
                "issues": [...],
                "editions": [...],
                "genres": [{"id": 1, "abbr": "SF"}]
            },
            ...
        ]
    """
    session = new_session()

    try:
        query = session.query(ShortStory)

        if storytype_id is not None:
            query = query.filter(ShortStory.story_type == storytype_id)

        if language_id is not None:
            query = query.filter(ShortStory.language == language_id)

        if pubyear_min is not None:
            query = query.filter(ShortStory.pubyear >= pubyear_min)

        if pubyear_max is not None:
            query = query.filter(ShortStory.pubyear <= pubyear_max)

        query = query.order_by(ShortStory.title)
        _log_query('stats_filterstories', query)
        stories = query.all()

        schema = ShortBriefSchema(many=True)
        result = schema.dump(stories)

    except exceptions.MarshmallowError as exp:
        app.logger.error(f'stats_filterstories: Serialization error: {exp}')
        return ResponseType('Serialisointivirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    except SQLAlchemyError as exp:
        app.logger.error(f'stats_filterstories: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_filterworks(language_id: Optional[int] = None,
                      orig_year_min: Optional[int] = None,
                      orig_year_max: Optional[int] = None,
                      edition_year_min: Optional[int] = None,
                      edition_year_max: Optional[int] = None) -> ResponseType:
    """
    Get works matching the given filters.

    Note: orig_year and edition_year filters are mutually exclusive.
    If both are provided, orig_year takes precedence.

    Args:
        language_id: Optional language ID to filter by.
        orig_year_min: Optional minimum original publication year (inclusive).
        orig_year_max: Optional maximum original publication year (inclusive).
        edition_year_min: Optional minimum first edition year (inclusive).
        edition_year_max: Optional maximum first edition year (inclusive).

    Returns:
        ResponseType: List of works in WorkBriefSchema format.
            Each item contains:
            - id: Work ID (int)
            - title: Work title (str)
            - orig_title: Original title (str or None)
            - author_str: Author string (str or None)
            - pubyear: Original publication year (int or None)
            - contributions: List of contributor objects
            - editions: List of edition objects
            - genres: List of genre objects
            - language_name: Language object

        Sorted by title ascending.

        Example:
        [
            {
                "id": 123,
                "title": "Teoksen nimi",
                "orig_title": "Original Title",
                "author_str": "Asimov, Isaac",
                "contributions": [...],
                "editions": [...],
                "genres": [{"id": 1, "abbr": "SF", "name": "Science Fiction"}],
                "language_name": {"id": 2, "name": "englanti"}
            },
            ...
        ]
    """
    session = new_session()

    try:
        # Determine if we're filtering by orig_year or edition_year
        use_orig_year = orig_year_min is not None or orig_year_max is not None

        if use_orig_year:
            # Filter by original publication year (Work.pubyear)
            query = session.query(Work)

            if language_id is not None:
                query = query.filter(Work.language == language_id)

            if orig_year_min is not None:
                query = query.filter(Work.pubyear >= orig_year_min)

            if orig_year_max is not None:
                query = query.filter(Work.pubyear <= orig_year_max)

            query = query.order_by(Work.title)
        else:
            # Filter by first edition year (Edition.pubyear where editionnum=1)
            query = session.query(Work).join(
                Part, and_(
                    Part.work_id == Work.id,
                    Part.shortstory_id.is_(None)
                )
            ).join(
                Edition, Edition.id == Part.edition_id
            ).filter(
                or_(Edition.editionnum == 1, Edition.editionnum.is_(None)),
                or_(Edition.version == 1, Edition.version.is_(None))
            )

            if language_id is not None:
                query = query.filter(Work.language == language_id)

            if edition_year_min is not None:
                query = query.filter(Edition.pubyear >= edition_year_min)

            if edition_year_max is not None:
                query = query.filter(Edition.pubyear <= edition_year_max)

            query = query.distinct().order_by(Work.title)

        _log_query('stats_filterworks', query)
        works = query.all()

        schema = WorkBriefSchema(many=True)
        result = schema.dump(works)

    except exceptions.MarshmallowError as exp:
        app.logger.error(f'stats_filterworks: Serialization error: {exp}')
        return ResponseType('Serialisointivirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)
    except SQLAlchemyError as exp:
        app.logger.error(f'stats_filterworks: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_storiesbyyear() -> ResponseType:
    """
    Get count of short stories by original publication year, grouped by story type
    and language.

    Returns:
        ResponseType: List of dicts, each containing:
            - year: Original publication year (int)
            - count: Number of short stories published that year (int)
            - storytype_id: Story type ID (int or None)
            - storytype_name: Story type name (str or None)
            - language_id: Original language ID (int or None)
            - language_name: Original language name (str or None)

        Sorted by year ascending, then by story type name, then by language name.

        Example:
        [
            {"year": 1950, "count": 10, "storytype_id": 1, "storytype_name": "novelli",
             "language_id": 2, "language_name": "englanti"},
            {"year": 1950, "count": 5, "storytype_id": 1, "storytype_name": "novelli",
             "language_id": 1, "language_name": "suomi"},
            {"year": 1951, "count": 15, "storytype_id": 1, "storytype_name": "novelli",
             "language_id": 2, "language_name": "englanti"},
            ...
        ]
    """
    session = new_session()

    try:
        query = session.query(
            ShortStory.pubyear,
            func.count(ShortStory.id).label('count'),
            StoryType.id.label('storytype_id'),
            StoryType.name.label('storytype_name'),
            Language.id.label('language_id'),
            Language.name.label('language_name')
        ).outerjoin(
            StoryType, StoryType.id == ShortStory.story_type
        ).outerjoin(
            Language, Language.id == ShortStory.language
        ).filter(
            ShortStory.pubyear.isnot(None),
            ShortStory.pubyear > 0
        ).group_by(
            ShortStory.pubyear,
            StoryType.id,
            Language.id
        ).order_by(
            ShortStory.pubyear,
            StoryType.name,
            Language.name
        )
        _log_query('stats_storiesbyyear', query)
        results = query.all()

        result = [
            {
                'year': r.pubyear,
                'count': r.count,
                'storytype_id': r.storytype_id,
                'storytype_name': r.storytype_name,
                'language_id': r.language_id,
                'language_name': r.language_name
            }
            for r in results
        ]

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_storiesbyyear: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)
