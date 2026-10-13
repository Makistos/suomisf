"""Functions related to statistics."""
from typing import Any, Dict, List, Optional
from sqlalchemy import (and_, func, desc, or_, select, union, union_all,
                        literal, case, String)
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import exceptions

from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (
    Genre, Work, WorkGenre, WorkContributor, EditionContributor, Edition,
    Publisher, Person, ContributorRole, Issue, Language, BindingType,
    Country, ShortStory, StoryContributor, StoryType, UserBook, UserWork,
    Magazine, Awarded, EditionShortStory, IssueContent, Tag, TagType,
    WorkTag, WorkType, Bookseries, Pubseries, MagazineType, Award,
    EditionImage, PersonImage
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
            WorkContributor, WorkContributor.person_id == Person.id
        ).join(
            Work, Work.id == WorkContributor.work_id
        )

        # Add genre filter if specified
        if filter_genre_id:
            author_query = author_query.join(
                WorkGenre, WorkGenre.work_id == Work.id
            ).filter(
                WorkGenre.genre_id == filter_genre_id
            )

        author_query = author_query.filter(
            WorkContributor.role_id == role_id
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

        # Genre + role breakdown for every listed person in one query (it
        # used to be one query per person: ~2,600 for authors).
        genre_query = session.query(
            WorkContributor.person_id.label('person_id'),
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
            WorkContributor, WorkContributor.work_id == Work.id
        ).join(
            ContributorRole,
            ContributorRole.id == WorkContributor.role_id
        ).filter(
            WorkContributor.person_id.in_([a.id for a in author_counts])
        ).group_by(
            WorkContributor.person_id,
            Genre.id,
            ContributorRole.id
        )
        _log_query('stats_personcounts (genre breakdown)', genre_query)
        genres_by_person: Dict[int, List[Any]] = {}
        for row in genre_query.all():
            genres_by_person.setdefault(row.person_id, []).append(row)

        for idx, author_data in enumerate(author_counts):
            author_genres = genres_by_person.get(author_data.id, [])

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
            func.count(
                func.distinct(ShortStory.id)
            ).label('story_count')
        ).join(
            StoryContributor, and_(
                StoryContributor.person_id == Person.id,
                StoryContributor.role_id == role_id
            )
        ).join(
            ShortStory,
            ShortStory.id == StoryContributor.shortstory_id
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

        # Story type + role breakdown for every listed person in one query
        # (it used to be one query per person: ~2,900).
        storytype_query = session.query(
            StoryContributor.person_id.label('person_id'),
            StoryType.id.label('storytype_id'),
            StoryType.name.label('storytype_name'),
            ContributorRole.id.label('role_id'),
            ContributorRole.name.label('role_name'),
            func.count(
                func.distinct(ShortStory.id)
            ).label('count')
        ).join(
            ShortStory, ShortStory.story_type == StoryType.id
        ).join(
            StoryContributor,
            StoryContributor.shortstory_id == ShortStory.id
        ).join(
            ContributorRole,
            ContributorRole.id == StoryContributor.role_id
        ).filter(
            StoryContributor.person_id.in_([p.id for p in person_counts])
        )
        if storytype_id is not None:
            storytype_query = storytype_query.filter(
                ShortStory.story_type == storytype_id
            )
        storytype_query = storytype_query.group_by(
            StoryContributor.person_id,
            StoryType.id,
            ContributorRole.id
        )
        _log_query('stats_storypersoncounts (storytype breakdown)',
                   storytype_query)
        storytypes_by_person: Dict[int, List[Any]] = {}
        for row in storytype_query.all():
            storytypes_by_person.setdefault(row.person_id, []).append(row)

        for idx, person_data in enumerate(person_counts):
            person_storytypes = storytypes_by_person.get(person_data.id, [])

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


def stats_publishercounts(pub_count: Optional[int] = 10) -> ResponseType:
    """
    Get the biggest publishers with their work counts per genre.

    Args:
        pub_count: Number of top publishers to return. Default is 10.
            None returns every publisher.

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
                Edition, Edition.work_id == Work.id
            ).filter(
                Edition.publisher_id == pub_data.id
            ).group_by(
                Genre.id
            )
            if idx == 0:  # Only log for first publisher to avoid spam
                _log_query('stats_publishercounts (genre breakdown)',
                           genre_query)
            pub_genres = genre_query.all()

            genre_dict = {genre_abbrs[pg.id]: pg.count for pg in pub_genres}

            if pub_count is None or idx < pub_count:
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


def stats_worksbyyear(genre: Optional[str] = None) -> ResponseType:
    """
    Get count of first editions published by year, grouped by language.

    Args:
        genre: Optional genre abbreviation (e.g., "SF", "F") to filter by.
               When set, only counts works belonging to that genre.

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
        filter_genre_id = None
        if genre:
            genre_obj = session.query(Genre).filter(Genre.abbr == genre).first()
            if genre_obj is None:
                return ResponseType(f'Tuntematon genre: {genre}',
                                    HttpResponseCode.BAD_REQUEST.value)
            filter_genre_id = genre_obj.id

        # Get first editions (editionnum = 1 or version = 1) by year and language
        query = session.query(
            Edition.pubyear,
            func.count(Edition.id).label('count'),
            Language.id.label('language_id'),
            Language.name.label('language_name')
        ).outerjoin(
            Work, Work.id == Edition.work_id
        ).outerjoin(
            Language, Language.id == Work.language
        ).filter(
            or_(Edition.editionnum == 1, Edition.editionnum.is_(None)),  # First editions
            or_(Edition.version == 1, Edition.version.is_(None))      # First version
        )

        if filter_genre_id:
            query = query.join(
                WorkGenre, WorkGenre.work_id == Work.id
            ).filter(
                WorkGenre.genre_id == filter_genre_id
            )

        query = query.group_by(
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


def stats_publishersbyyear(genre: Optional[str] = None) -> ResponseType:
    """
    Get count of works published by year, grouped by publisher.

    Each work is counted once per publisher, in the year of that publisher's
    earliest edition of it. Later printings or versions from the same
    publisher are not counted again, but a version of the work published by
    a different publisher is.

    Args:
        genre: Optional genre abbreviation (e.g., "SF", "F") to filter by.

    Returns:
        ResponseType: List of dicts, each containing:
            - year: Year of the publisher's first edition of the work (int)
            - count: Number of works (int)
            - publisher_id: Publisher ID (int)
            - publisher_name: Publisher short name (str)

        Sorted by year ascending, then by publisher name. Editions without a
        publisher are left out.
    """
    session = new_session()

    try:
        filter_genre_id = None
        if genre:
            genre_obj = session.query(Genre).filter(Genre.abbr == genre).first()
            if genre_obj is None:
                return ResponseType(f'Tuntematon genre: {genre}',
                                    HttpResponseCode.BAD_REQUEST.value)
            filter_genre_id = genre_obj.id

        # Earliest edition year for each (work, publisher) pair.
        firsts = session.query(
            Edition.work_id.label('work_id'),
            Edition.publisher_id.label('publisher_id'),
            func.min(Edition.pubyear).label('year')
        ).filter(
            Edition.work_id.isnot(None),
            Edition.publisher_id.isnot(None)
        )
        if filter_genre_id:
            firsts = firsts.join(
                WorkGenre, WorkGenre.work_id == Edition.work_id
            ).filter(
                WorkGenre.genre_id == filter_genre_id
            )
        firsts_sq = firsts.group_by(
            Edition.work_id, Edition.publisher_id
        ).subquery()

        query = session.query(
            firsts_sq.c.year,
            func.count().label('count'),
            Publisher.id.label('publisher_id'),
            Publisher.name.label('publisher_name')
        ).join(
            Publisher, Publisher.id == firsts_sq.c.publisher_id
        ).group_by(
            firsts_sq.c.year,
            Publisher.id,
            Publisher.name
        ).order_by(
            firsts_sq.c.year,
            Publisher.name
        )
        _log_query('stats_publishersbyyear', query)
        results = query.all()

        result = [
            {
                'year': r.year,
                'count': r.count,
                'publisher_id': r.publisher_id,
                'publisher_name': r.publisher_name
            }
            for r in results if r.year is not None
        ]

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_publishersbyyear: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_origworksbyyear(genre: Optional[str] = None) -> ResponseType:
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
        filter_genre_id = None
        if genre:
            genre_obj = (session.query(Genre)
                         .filter(Genre.abbr == genre).first())
            if genre_obj is None:
                return ResponseType(f'Tuntematon genre: {genre}',
                                    HttpResponseCode.BAD_REQUEST.value)
            filter_genre_id = genre_obj.id

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
        )
        if filter_genre_id:
            query = query.join(
                WorkGenre, WorkGenre.work_id == Work.id
            ).filter(
                WorkGenre.genre_id == filter_genre_id
            )
        query = query.group_by(
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

        # Headline counts for the overview tiles.
        total_stories = session.query(func.count(ShortStory.id)).scalar() or 0
        total_people = session.query(func.count(Person.id)).scalar() or 0
        # Publishers of at least one edition, as on the publishers tab;
        # magazine-only and unused publishers are left out.
        total_publishers = (session.query(
            func.count(func.distinct(Edition.publisher_id))).scalar() or 0)
        total_magazines = session.query(func.count(Magazine.id)).scalar() or 0
        total_issues = session.query(func.count(Issue.id)).scalar() or 0
        total_awarded = session.query(func.count(Awarded.id)).scalar() or 0

        result = {
            'total_pages': total_pages,
            'stack_height_meters': stack_height_meters,
            'hardback_count': hardback_count,
            'paperback_count': paperback_count,
            'total_editions': total_editions,
            'total_works': total_works,
            'total_stories': total_stories,
            'total_people': total_people,
            'total_publishers': total_publishers,
            'total_magazines': total_magazines,
            'total_issues': total_issues,
            'total_awarded': total_awarded
        }

    except SQLAlchemyError as exp:
        app.logger.error(f'stats_misc: Database error: {exp}')
        return ResponseType('Tietokantavirhe.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType(result, HttpResponseCode.OK.value)


def stats_issuesperyear(by_magazine: bool = False) -> ResponseType:
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
        if by_magazine:
            # One row per (year, magazine); year 0 marks an unknown year.
            mag_query = session.query(
                Issue.year,
                Magazine.id.label('magazine_id'),
                Magazine.name.label('magazine_name'),
                func.count(Issue.id).label('count')
            ).join(
                Magazine, Magazine.id == Issue.magazine_id
            ).filter(
                Issue.year.isnot(None),
                Issue.year > 0
            ).group_by(
                Issue.year, Magazine.id, Magazine.name
            ).order_by(
                Issue.year, Magazine.name
            )
            _log_query('stats_issuesperyear (by magazine)', mag_query)
            return ResponseType([
                {'year': r.year, 'count': r.count,
                 'magazine_id': r.magazine_id,
                 'magazine_name': r.magazine_name}
                for r in mag_query.all()
            ], HttpResponseCode.OK.value)

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
        has_work = session.query(WorkContributor.person_id).filter(
            WorkContributor.person_id == Person.id
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
                WorkContributor, WorkContributor.person_id == Person.id
            ).join(
                Work, Work.id == WorkContributor.work_id
            ).join(
                WorkGenre, WorkGenre.work_id == Work.id
            ).join(
                Genre, Genre.id == WorkGenre.genre_id
            ).join(
                ContributorRole,
                ContributorRole.id == WorkContributor.role_id
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
        # Subquery to check if person has at least one short story
        has_story = session.query(StoryContributor.person_id).filter(
            StoryContributor.person_id == Person.id
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
                func.count(
                    func.distinct(Person.id)
                ).label('count')
            ).select_from(
                Person
            ).join(
                StoryContributor,
                StoryContributor.person_id == Person.id
            ).join(
                ContributorRole,
                ContributorRole.id == StoryContributor.role_id
            ).join(
                ShortStory,
                ShortStory.id == StoryContributor.shortstory_id
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


# What the drill-down dialog's ShortsList/ShortSummary reads. The full
# ShortBriefSchema nests whole editions, works and author records (~10 KB
# per story; 72 MB and 105,117 queries for all novellas).
STATS_STORY_FIELDS = (
    'id', 'title', 'orig_title', 'pubyear', 'type', 'lang', 'genres',
    'contributors', 'editions.id', 'editions.work.id', 'editions.work.title',
    'editions.work.pubyear', 'issues.id', 'issues.cover_number',
    'issues.magazine.id', 'issues.magazine.name',
)


def stats_filterstories(storytype_id: Optional[int] = None,
                        language_id: Optional[int] = None,
                        pubyear_min: Optional[int] = None,
                        pubyear_max: Optional[int] = None,
                        nationality_id: Optional[int] = None,
                        contributor_role_id: Optional[int] = None) -> ResponseType:
    """
    Get short stories matching the given filters.

    Args:
        storytype_id: Optional story type ID to filter by.
        language_id: Optional language ID to filter by.
        pubyear_min: Optional minimum publication year (inclusive).
        pubyear_max: Optional maximum publication year (inclusive).
        nationality_id: Optional nationality (Country) ID to filter by —
            matches stories with at least one contributor of that nationality.
        contributor_role_id: Optional contributor role ID, narrowing the
            nationality_id match above to contributors in that role.
            Ignored if nationality_id is not given.

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

        if nationality_id is not None:
            query = (query.join(StoryContributor,
                                 StoryContributor.shortstory_id == ShortStory.id)
                     .join(Person, Person.id == StoryContributor.person_id)
                     .filter(Person.nationality_id == nationality_id))
            if contributor_role_id is not None:
                query = query.filter(StoryContributor.role_id == contributor_role_id)
            query = query.distinct()

        query = query.order_by(ShortStory.title).options(
            selectinload(ShortStory.type),
            selectinload(ShortStory.lang),
            selectinload(ShortStory.genres),
            selectinload(ShortStory.contributors).selectinload(StoryContributor.person),
            selectinload(ShortStory.contributors).selectinload(StoryContributor.real_person),
            selectinload(ShortStory.contributors).selectinload(StoryContributor.role),
            selectinload(ShortStory.editions).selectinload(Edition.work),
            selectinload(ShortStory.issues).selectinload(Issue.magazine))
        _log_query('stats_filterstories', query)
        stories = query.all()

        schema = ShortBriefSchema(many=True, only=STATS_STORY_FIELDS)
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
                      edition_year_max: Optional[int] = None,
                      owner_id: Optional[int] = None,
                      worktype_id: Optional[int] = None,
                      genre_id: Optional[int] = None,
                      publisher_id: Optional[int] = None,
                      nationality_id: Optional[int] = None,
                      contributor_role_id: Optional[int] = None,
                      read_user_id: Optional[int] = None,
                      publisher_first: bool = False) -> ResponseType:
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
        worktype_id: Optional work type ID to filter by.
        genre_id: Optional genre ID to filter by.
        publisher_id: Optional publisher ID to filter by (matched against the
            edition, so it applies to whichever edition set the year filter
            above is already restricting to).
        nationality_id: Optional nationality (Country) ID to filter by — matches
            works with at least one contributor of that nationality.
        contributor_role_id: Optional contributor role ID, narrowing the
            nationality_id match above to contributors in that role.
            Ignored if nationality_id is not given.
        read_user_id: Optional user ID — restrict to works that user has
            marked read (userwork table). Work-level, independent of
            owner_id/editions.
        publisher_first: With publisher_id and an edition year filter (and
            no owner_id), match works whose earliest edition from that
            publisher falls in the year range, instead of matching first
            editions. Mirrors stats_publishersbyyear.

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
            edition_joined = False

            if owner_id is not None:
                # Restrict to works the user owns.
                query = (query.join(Edition, Edition.work_id == Work.id)
                         .join(UserBook, UserBook.edition_id == Edition.id)
                         .filter(UserBook.user_id == owner_id,
                                 UserBook.condition_id >= 1,
                                 UserBook.condition_id <= 5))
                edition_joined = True

            if language_id is not None:
                query = query.filter(Work.language == language_id)

            if worktype_id is not None:
                query = query.filter(Work.type == worktype_id)

            if genre_id is not None:
                query = (query.join(WorkGenre, WorkGenre.work_id == Work.id)
                         .filter(WorkGenre.genre_id == genre_id))

            if publisher_id is not None:
                if not edition_joined:
                    query = query.join(Edition, Edition.work_id == Work.id)
                    edition_joined = True
                query = query.filter(Edition.publisher_id == publisher_id)

            if nationality_id is not None:
                query = query.filter(Work.id.in_(_works_by_nationality(
                    nationality_id, contributor_role_id)))

            if read_user_id is not None:
                query = (query.join(UserWork, UserWork.work_id == Work.id)
                         .filter(UserWork.user_id == read_user_id))

            if orig_year_min is not None:
                query = query.filter(Work.pubyear >= orig_year_min)

            if orig_year_max is not None:
                query = query.filter(Work.pubyear <= orig_year_max)

            query = query.distinct().order_by(Work.title)
        elif publisher_first and publisher_id is not None and owner_id is None:
            # Works whose earliest edition from this publisher is in range.
            first_year = func.min(Edition.pubyear)
            firsts = session.query(Edition.work_id).filter(
                Edition.publisher_id == publisher_id
            ).group_by(Edition.work_id)
            if edition_year_min is not None:
                firsts = firsts.having(first_year >= edition_year_min)
            if edition_year_max is not None:
                firsts = firsts.having(first_year <= edition_year_max)
            query = session.query(Work).filter(Work.id.in_(firsts))

            if language_id is not None:
                query = query.filter(Work.language == language_id)

            if worktype_id is not None:
                query = query.filter(Work.type == worktype_id)

            if genre_id is not None:
                query = (query.join(WorkGenre, WorkGenre.work_id == Work.id)
                         .filter(WorkGenre.genre_id == genre_id))

            if read_user_id is not None:
                query = (query.join(UserWork, UserWork.work_id == Work.id)
                         .filter(UserWork.user_id == read_user_id))

            query = query.distinct().order_by(Work.title)
        else:
            query = session.query(Work).join(
                Edition, Edition.work_id == Work.id
            )

            if owner_id is not None:
                # Match the owned editions in that year (any owned edition,
                # not just first editions).
                query = (query.join(UserBook, UserBook.edition_id == Edition.id)
                         .filter(UserBook.user_id == owner_id,
                                 UserBook.condition_id >= 1,
                                 UserBook.condition_id <= 5))
            else:
                # Filter by first edition year (Edition.pubyear where editionnum=1)
                query = query.filter(
                    or_(Edition.editionnum == 1, Edition.editionnum.is_(None)),
                    or_(Edition.version == 1, Edition.version.is_(None))
                )

            if language_id is not None:
                query = query.filter(Work.language == language_id)

            if worktype_id is not None:
                query = query.filter(Work.type == worktype_id)

            if genre_id is not None:
                query = (query.join(WorkGenre, WorkGenre.work_id == Work.id)
                         .filter(WorkGenre.genre_id == genre_id))

            if publisher_id is not None:
                query = query.filter(Edition.publisher_id == publisher_id)

            if nationality_id is not None:
                query = query.filter(Work.id.in_(_works_by_nationality(
                    nationality_id, contributor_role_id)))

            if read_user_id is not None:
                query = (query.join(UserWork, UserWork.work_id == Work.id)
                         .filter(UserWork.user_id == read_user_id))

            if edition_year_min is not None:
                query = query.filter(Edition.pubyear >= edition_year_min)

            if edition_year_max is not None:
                query = query.filter(Edition.pubyear <= edition_year_max)

            query = query.distinct().order_by(Work.title)

        # Batch-load everything WorkBriefSchema touches so serializing a
        # large result set doesn't issue a lazy-load query per relationship
        # per row (see SECURITY_TODO.md-adjacent perf notes — this endpoint
        # took ~11s for ~1200 works before this).
        query = query.options(
            selectinload(Work.contributions).selectinload(WorkContributor.person),
            selectinload(Work.contributions).selectinload(WorkContributor.real_person),
            selectinload(Work.contributions).selectinload(WorkContributor.role),
            selectinload(Work.editions).selectinload(Edition.editors),
            selectinload(Work.editions).selectinload(Edition.translators),
            selectinload(Work.editions).selectinload(Edition.contributions)
                .selectinload(EditionContributor.person),
            selectinload(Work.editions).selectinload(Edition.contributions)
                .selectinload(EditionContributor.real_person),
            selectinload(Work.editions).selectinload(Edition.contributions)
                .selectinload(EditionContributor.role),
            selectinload(Work.editions).selectinload(Edition.images),
            selectinload(Work.editions).selectinload(Edition.publisher),
            selectinload(Work.editions).selectinload(Edition.owners),
            selectinload(Work.editions).selectinload(Edition.wishlisted),
            selectinload(Work.genres),
            selectinload(Work.bookseries),
            selectinload(Work.tags),
            selectinload(Work.language_name),
        )

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


# --- Statistics page, phase 2: editions and works over time -------------

TRANSLATOR_ROLE_ID = 2
TOP_LIST_LENGTH = 20


class _UnknownGenre(Exception):
    """Raised for a genre abbreviation that does not exist."""


def _genre_id(session: Any, genre: Optional[str]) -> Optional[int]:
    """Genre id for an abbreviation, None for no filter."""
    if not genre:
        return None
    genre_obj = session.query(Genre).filter(Genre.abbr == genre).first()
    if genre_obj is None:
        raise _UnknownGenre(genre)
    return genre_obj.id


def _filter_editions_by_genre(query: Any, genre_id: Optional[int]) -> Any:
    """Restrict a query that has Edition in it to works of a genre."""
    if genre_id is None:
        return query
    return (query.join(WorkGenre, WorkGenre.work_id == Edition.work_id)
            .filter(WorkGenre.genre_id == genre_id))


def _filter_edition_years(query: Any, year_min: Optional[int],
                          year_max: Optional[int]) -> Any:
    """Restrict a query that has Edition in it to a range of years."""
    if year_min is not None:
        query = query.filter(Edition.pubyear >= year_min)
    if year_max is not None:
        query = query.filter(Edition.pubyear <= year_max)
    return query


def _quartiles(values: List[int]) -> Dict[str, float]:
    """Lower quartile, median and upper quartile, interpolated linearly
    between data points (as PostgreSQL's percentile_cont)."""
    data = sorted(values)

    def percentile(p: float) -> float:
        pos = (len(data) - 1) * p
        low = int(pos)
        high = min(low + 1, len(data) - 1)
        return data[low] + (data[high] - data[low]) * (pos - low)

    return {'q1': percentile(0.25), 'median': percentile(0.5),
            'q3': percentile(0.75)}


def _stats_error(name: str, exp: Exception) -> ResponseType:
    """Response for a failed stats query."""
    if isinstance(exp, _UnknownGenre):
        return ResponseType(f'Tuntematon genre: {exp}',
                            HttpResponseCode.BAD_REQUEST.value)
    app.logger.error(f'{name}: Database error: {exp}')
    return ResponseType('Tietokantavirhe.',
                        HttpResponseCode.INTERNAL_SERVER_ERROR.value)


def stats_translationlag(genre: Optional[str] = None,
                         year_min: Optional[int] = None,
                         year_max: Optional[int] = None) -> ResponseType:
    """
    Years from a work's original publication to its first Finnish edition.

    Counts translated works only (original language known and not Finnish,
    original year known). Works whose first edition predates the original
    year (data errors) are left out. year_min and year_max limit the year
    of the first Finnish edition (inclusive).

    Returns:
        ResponseType: Dict containing:
            - total: Number of works counted (int)
            - median: Median delay in years (float or None)
            - histogram: [{"lag": years, "count": works}], every lag from
              0 to the largest, empty ones included
            - by_decade: [{"decade", "count", "q1", "median", "q3"}] by
              the decade of the first Finnish edition
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        finnish_id = (session.query(Language.id)
                      .filter(Language.name == 'suomi').scalar())
        first = (session.query(
            Edition.work_id.label('work_id'),
            func.min(Edition.pubyear).label('year'))
            .group_by(Edition.work_id).subquery())
        query = (session.query(Work.pubyear, first.c.year)
                 .join(first, first.c.work_id == Work.id)
                 .filter(Work.pubyear > 0,
                         Work.language.isnot(None),
                         first.c.year >= Work.pubyear))
        if finnish_id is not None:
            query = query.filter(Work.language != finnish_id)
        if year_min is not None:
            query = query.filter(first.c.year >= year_min)
        if year_max is not None:
            query = query.filter(first.c.year <= year_max)
        if genre_id is not None:
            query = (query.join(WorkGenre, WorkGenre.work_id == Work.id)
                     .filter(WorkGenre.genre_id == genre_id))
        _log_query('stats_translationlag', query)
        rows = query.all()
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_translationlag', exp)

    lags = [r.year - r.pubyear for r in rows]
    counts: Dict[int, int] = {}
    decades: Dict[int, List[int]] = {}
    for r, lag in zip(rows, lags):
        counts[lag] = counts.get(lag, 0) + 1
        decades.setdefault(r.year // 10 * 10, []).append(lag)
    histogram = [{'lag': lag, 'count': counts.get(lag, 0)}
                 for lag in range(max(lags) + 1 if lags else 0)]
    by_decade = [{'decade': d, 'count': len(v), **_quartiles(v)}
                 for d, v in sorted(decades.items())]
    result = {
        'total': len(lags),
        'median': _quartiles(lags)['median'] if lags else None,
        'histogram': histogram,
        'by_decade': by_decade,
    }
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_editiontypes(genre: Optional[str] = None) -> ResponseType:
    """
    Editions per year split into first editions, new versions and reprints.

    - first: first printing of a work's first version (version and
      editionnum empty or 1)
    - new_version: first printing of a later version (version > 1), e.g.
      a new or revised translation
    - reprint: any later printing (editionnum > 1)

    Returns:
        ResponseType: [{"year", "first", "new_version", "reprint"}] sorted
        by year.
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        first_print = or_(Edition.editionnum.is_(None),
                          Edition.editionnum <= 1)
        query = session.query(
            Edition.pubyear,
            func.count(Edition.id).filter(
                and_(first_print, or_(Edition.version.is_(None),
                                      Edition.version <= 1)))
            .label('first'),
            func.count(Edition.id).filter(
                and_(first_print, Edition.version > 1)).label('new_version'),
            func.count(Edition.id).filter(
                Edition.editionnum > 1).label('reprint'))
        query = _filter_editions_by_genre(query, genre_id)
        query = (query.filter(Edition.pubyear > 0)
                 .group_by(Edition.pubyear).order_by(Edition.pubyear))
        _log_query('stats_editiontypes', query)
        result = [{'year': r.pubyear, 'first': r.first,
                   'new_version': r.new_version, 'reprint': r.reprint}
                  for r in query.all()]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_editiontypes', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_editionsperwork(genre: Optional[str] = None) -> ResponseType:
    """
    How many editions (printings of any version) works have.

    Returns:
        ResponseType: Dict containing:
            - histogram: [{"editions": n, "works": works with n editions}]
            - top: the TOP_LIST_LENGTH works with most editions,
              [{"work_id", "title", "author", "year", "editions"}]
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        counts = session.query(Edition.work_id,
                               func.count(Edition.id).label('n'))
        counts = _filter_editions_by_genre(counts, genre_id)
        counts = (counts.filter(Edition.work_id.isnot(None))
                  .group_by(Edition.work_id).subquery())
        hist_query = (session.query(counts.c.n,
                                    func.count().label('works'))
                      .group_by(counts.c.n).order_by(counts.c.n))
        _log_query('stats_editionsperwork (histogram)', hist_query)
        histogram = [{'editions': r.n, 'works': r.works}
                     for r in hist_query.all()]
        top_query = (session.query(Work.id, Work.title, Work.author_str,
                                   Work.pubyear, counts.c.n)
                     .join(counts, counts.c.work_id == Work.id)
                     .order_by(desc(counts.c.n), Work.title)
                     .limit(TOP_LIST_LENGTH))
        _log_query('stats_editionsperwork (top)', top_query)
        top = [{'work_id': r.id, 'title': r.title, 'author': r.author_str,
                'year': r.pubyear, 'editions': r.n}
               for r in top_query.all()]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_editionsperwork', exp)
    return ResponseType({'histogram': histogram, 'top': top},
                        HttpResponseCode.OK.value)


def _translations(editions: List[Any]) -> List[Dict[str, Any]]:
    """Group a work's translated editions into translations.

    Editions sharing a translator belong to the same translation (a
    revision by the original translator plus a co-translator stays one
    translation). Returns [{"year", "translators"}] by first year.
    """
    groups: List[Dict[str, Any]] = []
    for edition in editions:
        people = set(edition['translators'])
        touching = [g for g in groups if g['people'] & people]
        merged = {'people': people, 'year': edition['year'],
                  'names': dict(edition['names'])}
        for g in touching:
            merged['people'] |= g['people']
            merged['year'] = min(merged['year'], g['year'])
            merged['names'].update(g['names'])
            groups.remove(g)
        groups.append(merged)
    groups.sort(key=lambda g: g['year'])
    return [{'year': g['year'],
             'translators': sorted(g['names'].values())} for g in groups]


def stats_retranslations(genre: Optional[str] = None) -> ResponseType:
    """
    Works translated into Finnish more than once.

    A work's editions are grouped into translations by their translators:
    editions that share a translator are the same translation. A work with
    two or more groups has been retranslated.

    Returns:
        ResponseType: Dict containing:
            - translated_works: Works with a known translator (int)
            - retranslated_works: Works with 2+ translations (int)
            - by_year: [{"year", "count"}] new translations (each work's
              second and later) by first edition year
            - works: [{"work_id", "title", "author", "year",
              "translations": [{"year", "translators"}]}], most
              translations first, then by title
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        query = (session.query(Edition.work_id, Edition.id, Edition.pubyear,
                               Person.id.label('person_id'), Person.name)
                 .join(EditionContributor,
                       EditionContributor.edition_id == Edition.id)
                 .join(Person, Person.id == EditionContributor.person_id)
                 .filter(EditionContributor.role_id == TRANSLATOR_ROLE_ID,
                         Edition.work_id.isnot(None)))
        query = _filter_editions_by_genre(query, genre_id)
        _log_query('stats_retranslations', query)
        editions: Dict[int, Dict[int, Dict[str, Any]]] = {}
        for r in query.all():
            edition = editions.setdefault(r.work_id, {}).setdefault(
                r.id, {'year': r.pubyear, 'translators': [], 'names': {}})
            edition['translators'].append(r.person_id)
            edition['names'][r.person_id] = r.name

        retranslated = {}
        for work_id, work_editions in editions.items():
            translations = _translations(
                sorted(work_editions.values(), key=lambda e: e['year']))
            if len(translations) > 1:
                retranslated[work_id] = translations

        works_query = (session.query(Work.id, Work.title, Work.author_str,
                                     Work.pubyear)
                       .filter(Work.id.in_(list(retranslated))))
        works = [{'work_id': w.id, 'title': w.title, 'author': w.author_str,
                  'year': w.pubyear, 'translations': retranslated[w.id]}
                 for w in works_query.all()]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_retranslations', exp)

    works.sort(key=lambda w: (-len(w['translations']), w['title']))
    by_year: Dict[int, int] = {}
    for w in works:
        for t in w['translations'][1:]:
            by_year[t['year']] = by_year.get(t['year'], 0) + 1
    result = {
        'translated_works': len(editions),
        'retranslated_works': len(works),
        'by_year': [{'year': y, 'count': c}
                    for y, c in sorted(by_year.items())],
        'works': works,
    }
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_bindingsbyyear(genre: Optional[str] = None) -> ResponseType:
    """
    Editions per year by binding (all printings, not just first editions).

    Returns:
        ResponseType: [{"year", "count", "binding_id", "binding_name"}]
        sorted by year, then binding id.
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        query = session.query(Edition.pubyear,
                              func.count(Edition.id).label('count'),
                              BindingType.id.label('binding_id'),
                              BindingType.name.label('binding_name'))
        query = query.outerjoin(BindingType,
                                BindingType.id == Edition.binding_id)
        query = _filter_editions_by_genre(query, genre_id)
        query = (query.filter(Edition.pubyear > 0)
                 .group_by(Edition.pubyear, BindingType.id)
                 .order_by(Edition.pubyear, BindingType.id))
        _log_query('stats_bindingsbyyear', query)
        result = [{'year': r.pubyear, 'count': r.count,
                   'binding_id': r.binding_id,
                   'binding_name': r.binding_name}
                  for r in query.all()]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_bindingsbyyear', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_pagesbyyear(genre: Optional[str] = None,
                      by_decade: bool = False) -> ResponseType:
    """
    Page count quartiles of editions (all printings) per year or decade.

    Returns:
        ResponseType: [{"year", "count", "q1", "median", "q3"}] sorted by
        year; with by_decade, "year" is the first year of the decade.
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        year = (Edition.pubyear // 10 * 10 if by_decade
                else Edition.pubyear).label('year')

        def percentile(p: float) -> Any:
            return func.percentile_cont(p).within_group(Edition.pages)

        query = session.query(year, func.count(Edition.id).label('count'),
                              percentile(0.25).label('q1'),
                              percentile(0.5).label('median'),
                              percentile(0.75).label('q3'))
        query = _filter_editions_by_genre(query, genre_id)
        query = (query.filter(Edition.pubyear > 0, Edition.pages > 0)
                 .group_by(year).order_by(year))
        _log_query('stats_pagesbyyear', query)
        result = [{'year': r.year, 'count': r.count, 'q1': r.q1,
                   'median': r.median, 'q3': r.q3} for r in query.all()]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_pagesbyyear', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


PAGE_BUCKET = 50


def stats_pagehistogram(genre: Optional[str] = None,
                        year_min: Optional[int] = None,
                        year_max: Optional[int] = None) -> ResponseType:
    """
    Distribution of edition page counts (all printings) and the thickest
    editions, optionally for editions published in a range of years.

    Returns:
        ResponseType: Dict containing:
            - bucket: Bucket width in pages (int)
            - histogram: [{"pages": bucket start, "count"}], every bucket
              from 0 to the largest, empty ones included
            - thickest: [{"edition_id", "work_id", "title", "author",
              "year", "pages"}], TOP_LIST_LENGTH thickest editions
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        bucket = (Edition.pages // PAGE_BUCKET * PAGE_BUCKET).label('bucket')
        query = session.query(bucket, func.count(Edition.id).label('count'))
        query = _filter_editions_by_genre(query, genre_id)
        query = _filter_edition_years(query, year_min, year_max)
        query = (query.filter(Edition.pages > 0)
                 .group_by(bucket).order_by(bucket))
        _log_query('stats_pagehistogram', query)
        counts = {r.bucket: r.count for r in query.all()}

        thick = (session.query(Edition.id, Edition.work_id, Edition.title,
                               Edition.pubyear, Edition.pages,
                               Work.author_str)
                 .outerjoin(Work, Work.id == Edition.work_id))
        thick = _filter_editions_by_genre(thick, genre_id)
        thick = _filter_edition_years(thick, year_min, year_max)
        thick = (thick.filter(Edition.pages > 0)
                 .order_by(desc(Edition.pages), Edition.title)
                 .limit(TOP_LIST_LENGTH))
        _log_query('stats_pagehistogram (thickest)', thick)
        thickest = [{'edition_id': r.id, 'work_id': r.work_id,
                     'title': r.title, 'author': r.author_str,
                     'year': r.pubyear, 'pages': r.pages}
                    for r in thick.all()]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_pagehistogram', exp)

    last = max(counts) if counts else -PAGE_BUCKET
    histogram = [{'pages': b, 'count': counts.get(b, 0)}
                 for b in range(0, last + 1, PAGE_BUCKET)]
    return ResponseType({'bucket': PAGE_BUCKET, 'histogram': histogram,
                         'thickest': thickest}, HttpResponseCode.OK.value)


def stats_sizehistogram(genre: Optional[str] = None,
                        year_min: Optional[int] = None,
                        year_max: Optional[int] = None) -> ResponseType:
    """
    Distribution of edition heights in centimetres (all printings),
    optionally for editions published in a range of years.

    Returns:
        ResponseType: [{"size": cm, "count"}] sorted by size, every
        centimetre from the smallest to the largest included.
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        query = session.query(Edition.size,
                              func.count(Edition.id).label('count'))
        query = _filter_editions_by_genre(query, genre_id)
        query = _filter_edition_years(query, year_min, year_max)
        query = (query.filter(Edition.size > 0)
                 .group_by(Edition.size).order_by(Edition.size))
        _log_query('stats_sizehistogram', query)
        counts = {r.size: r.count for r in query.all()}
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_sizehistogram', exp)
    result = ([{'size': s, 'count': counts.get(s, 0)}
               for s in range(min(counts), max(counts) + 1)]
              if counts else [])
    return ResponseType(result, HttpResponseCode.OK.value)


# --- Statistics page, phase 3: people and content -----------------------

MATERIALS = ('books', 'stories', 'all')


class _BadParameter(Exception):
    """Raised for an invalid query parameter value."""


def _check_material(material: str) -> None:
    if material not in MATERIALS:
        raise _BadParameter(f'Tuntematon aineisto: {material}')


def _contributions(material: str, role_id: Optional[int],
                   genre_id: Optional[int],
                   storytype_id: Optional[int]) -> Any:
    """Who contributed to what, as a subquery (kind, item_id, person_id).

    kind is 'w' for works, 's' for short stories. A work's contributors
    come from both the work (authors, editors) and its editions
    (translators, cover artists, illustrators). genre_id filters works,
    storytype_id filters stories; role_id None means any role.
    """
    parts = []
    if material in ('books', 'all'):
        sources = [
            (select(literal('w', String).label('kind'),
                    WorkContributor.work_id.label('item_id'),
                    WorkContributor.person_id.label('person_id')),
             WorkContributor.work_id, WorkContributor.role_id),
            (select(literal('w', String), Edition.work_id,
                    EditionContributor.person_id)
             .join(Edition, Edition.id == EditionContributor.edition_id)
             .where(Edition.work_id.isnot(None)),
             Edition.work_id, EditionContributor.role_id),
        ]
        for part, work_id, role in sources:
            if role_id is not None:
                part = part.where(role == role_id)
            parts.append(_where_genre(part, work_id, genre_id))
    if material in ('stories', 'all'):
        part = select(literal('s', String).label('kind'),
                      StoryContributor.shortstory_id.label('item_id'),
                      StoryContributor.person_id.label('person_id'))
        if role_id is not None:
            part = part.where(StoryContributor.role_id == role_id)
        if storytype_id is not None:
            part = (part.join(ShortStory, ShortStory.id ==
                              StoryContributor.shortstory_id)
                    .where(ShortStory.story_type == storytype_id))
        parts.append(part)
    # union drops the duplicates of a person in several roles or editions.
    return union(*parts).subquery()


def _works_by_nationality(nationality_id: int,
                          role_id: Optional[int]) -> Any:
    """Ids of works with a contributor of a nationality (in a role),
    counting edition roles such as translators too."""
    c = _contributions('books', role_id, None, None)
    return (select(c.c.item_id)
            .join(Person, Person.id == c.c.person_id)
            .where(Person.nationality_id == nationality_id))


def _item_years(material: str) -> Any:
    """First Finnish publication year of each item, as a subquery
    (kind, item_id, year): a work's earliest edition, a story's earliest
    edition or magazine issue."""
    parts = []
    if material in ('books', 'all'):
        parts.append(
            select(literal('w', String).label('kind'),
                   Edition.work_id.label('item_id'),
                   func.min(Edition.pubyear).label('year'))
            .where(Edition.work_id.isnot(None), Edition.pubyear > 0)
            .group_by(Edition.work_id))
    if material in ('stories', 'all'):
        places = union_all(
            select(EditionShortStory.shortstory_id.label('story_id'),
                   Edition.pubyear.label('year'))
            .join(Edition, Edition.id == EditionShortStory.edition_id),
            select(IssueContent.shortstory_id, Issue.year)
            .join(Issue, Issue.id == IssueContent.issue_id)
            .where(IssueContent.shortstory_id.isnot(None))).subquery()
        parts.append(
            select(literal('s', String).label('kind'),
                   places.c.story_id.label('item_id'),
                   func.min(places.c.year).label('year'))
            .where(places.c.year > 0)
            .group_by(places.c.story_id))
    return union_all(*parts).subquery()


def _item_key(sub: Any) -> Any:
    """One value per item across works and stories, for count(distinct)."""
    return func.concat(sub.c.kind, sub.c.item_id)


def _people_error(name: str, exp: Exception) -> ResponseType:
    if isinstance(exp, _BadParameter):
        return ResponseType(str(exp), HttpResponseCode.BAD_REQUEST.value)
    return _stats_error(name, exp)


def stats_contributornationalities(material: str = 'books',
                                   role_id: Optional[int] = None,
                                   genre: Optional[str] = None,
                                   storytype_id: Optional[int] = None
                                   ) -> ResponseType:
    """
    People and the works/stories they contributed to, by nationality.

    Args:
        material: 'books', 'stories' or 'all'.
        role_id: Contributor role; None counts any role.
        genre: Genre abbreviation, filters works.
        storytype_id: Story type, filters stories.

    Returns:
        ResponseType: [{"nationality_id", "nationality", "people",
        "items"}], most people first. people counts each person once;
        items counts each work or story once per nationality among its
        contributors. Unknown nationality has nationality_id None.
    """
    session = new_session()
    try:
        _check_material(material)
        genre_id = _genre_id(session, genre)
        c = _contributions(material, role_id, genre_id, storytype_id)
        query = (select(Country.id.label('nationality_id'),
                        Country.name.label('nationality'),
                        func.count(func.distinct(c.c.person_id))
                        .label('people'),
                        func.count(func.distinct(_item_key(c)))
                        .label('items'))
                 .select_from(c)
                 .join(Person, Person.id == c.c.person_id)
                 .outerjoin(Country, Country.id == Person.nationality_id)
                 .group_by(Country.id, Country.name)
                 .order_by(desc('people'), Country.name))
        _log_query('stats_contributornationalities', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre, _BadParameter) as exp:
        return _people_error('stats_contributornationalities', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_topcontributors(material: str = 'books',
                          role_id: Optional[int] = None,
                          genre: Optional[str] = None,
                          storytype_id: Optional[int] = None,
                          count: int = 10) -> ResponseType:
    """
    People with the most works/stories in a role.

    Returns:
        ResponseType: [{"id", "name", "alt_name", "nationality",
        "count"}], most first, at most count rows.
    """
    session = new_session()
    try:
        _check_material(material)
        genre_id = _genre_id(session, genre)
        c = _contributions(material, role_id, genre_id, storytype_id)
        total = func.count(func.distinct(_item_key(c))).label('count')
        query = (select(Person.id, Person.name, Person.alt_name,
                        Country.name.label('nationality'), total)
                 .select_from(c)
                 .join(Person, Person.id == c.c.person_id)
                 .outerjoin(Country, Country.id == Person.nationality_id)
                 .group_by(Person.id, Country.name)
                 .order_by(desc('count'), Person.name)
                 .limit(count))
        _log_query('stats_topcontributors', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre, _BadParameter) as exp:
        return _people_error('stats_topcontributors', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_nationalitiesbydecade(material: str = 'books',
                                role_id: Optional[int] = None,
                                genre: Optional[str] = None,
                                storytype_id: Optional[int] = None
                                ) -> ResponseType:
    """
    Works/stories per decade of first Finnish publication, by contributor
    nationality. An item counts once for each nationality among its
    contributors in the role.

    Returns:
        ResponseType: [{"year" (first year of the decade), "count",
        "nationality_id", "nationality"}] sorted by decade.
    """
    session = new_session()
    try:
        _check_material(material)
        genre_id = _genre_id(session, genre)
        c = _contributions(material, role_id, genre_id, storytype_id)
        y = _item_years(material)
        decade = (y.c.year // 10 * 10).label('year')
        query = (select(decade,
                        func.count(func.distinct(_item_key(c)))
                        .label('count'),
                        Country.id.label('nationality_id'),
                        Country.name.label('nationality'))
                 .select_from(c)
                 .join(y, and_(y.c.kind == c.c.kind,
                               y.c.item_id == c.c.item_id))
                 .join(Person, Person.id == c.c.person_id)
                 .outerjoin(Country, Country.id == Person.nationality_id)
                 .group_by(decade, Country.id, Country.name)
                 .order_by(decade))
        _log_query('stats_nationalitiesbydecade', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre, _BadParameter) as exp:
        return _people_error('stats_nationalitiesbydecade', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_birthdecades(material: str = 'books',
                       role_id: Optional[int] = None,
                       genre: Optional[str] = None,
                       storytype_id: Optional[int] = None) -> ResponseType:
    """
    Contributors by decade of birth.

    Returns:
        ResponseType: Dict containing:
            - people: Contributors counted (int)
            - with_birth_year: Of those, people with a known birth year
            - decades: [{"decade", "count"}] sorted by decade
    """
    session = new_session()
    try:
        _check_material(material)
        genre_id = _genre_id(session, genre)
        c = _contributions(material, role_id, genre_id, storytype_id)
        people = (select(func.count(func.distinct(c.c.person_id)),
                         func.count(func.distinct(c.c.person_id))
                         .filter(Person.dob > 0))
                  .select_from(c)
                  .join(Person, Person.id == c.c.person_id))
        total, with_dob = session.execute(people).one()
        decade = (Person.dob // 10 * 10).label('decade')
        query = (select(decade, func.count(func.distinct(Person.id))
                        .label('count'))
                 .select_from(c)
                 .join(Person, Person.id == c.c.person_id)
                 .where(Person.dob > 0)
                 .group_by(decade).order_by(decade))
        _log_query('stats_birthdecades', query)
        decades = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre, _BadParameter) as exp:
        return _people_error('stats_birthdecades', exp)
    return ResponseType({'people': total, 'with_birth_year': with_dob,
                         'decades': decades}, HttpResponseCode.OK.value)


TRANSLATOR_COUNT = 20


def stats_translatorlanguages(material: str = 'books',
                              genre: Optional[str] = None,
                              storytype_id: Optional[int] = None,
                              count: int = TRANSLATOR_COUNT
                              ) -> ResponseType:
    """
    The most productive translators and the original languages of what
    they translated.

    Returns:
        ResponseType: [{"person_id", "name", "alt_name", "language_id",
        "language_name", "count"}] for the count translators with most
        works/stories; language None when not recorded.
    """
    session = new_session()
    try:
        _check_material(material)
        genre_id = _genre_id(session, genre)
        c = _contributions(material, TRANSLATOR_ROLE_ID, genre_id,
                           storytype_id)
        top = (select(c.c.person_id)
               .group_by(c.c.person_id)
               .order_by(desc(func.count(func.distinct(_item_key(c)))))
               .limit(count))
        languages = union_all(
            select(literal('w', String).label('kind'),
                   Work.id.label('item_id'),
                   Work.language.label('language_id')),
            select(literal('s', String).label('kind'),
                   ShortStory.id.label('item_id'),
                   ShortStory.language.label('language_id'))).subquery()
        query = (select(Person.id.label('person_id'), Person.name,
                        Person.alt_name, Language.id.label('language_id'),
                        Language.name.label('language_name'),
                        func.count(func.distinct(_item_key(c)))
                        .label('count'))
                 .select_from(c)
                 .join(languages, and_(languages.c.kind == c.c.kind,
                                       languages.c.item_id == c.c.item_id))
                 .join(Person, Person.id == c.c.person_id)
                 .outerjoin(Language,
                            Language.id == languages.c.language_id)
                 .where(c.c.person_id.in_(top))
                 .group_by(Person.id, Language.id, Language.name))
        _log_query('stats_translatorlanguages', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre, _BadParameter) as exp:
        return _people_error('stats_translatorlanguages', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def _first_years() -> Any:
    """Year of each work's earliest edition: subquery (work_id, year)."""
    return (select(Edition.work_id.label('work_id'),
                   func.min(Edition.pubyear).label('year'))
            .where(Edition.work_id.isnot(None), Edition.pubyear > 0)
            .group_by(Edition.work_id).subquery())


def _where_genre(query: Any, work_id: Any, genre_id: Optional[int]) -> Any:
    """Restrict a select to works of a genre."""
    if genre_id is None:
        return query
    return query.where(select(WorkGenre.work_id).where(
        WorkGenre.work_id == work_id,
        WorkGenre.genre_id == genre_id).exists())


def stats_worktypecounts(genre: Optional[str] = None) -> ResponseType:
    """
    Works per work type (romaani, kokoelma…).

    Returns:
        ResponseType: [{"id", "name", "count"}], most first.
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        query = (select(WorkType.id, WorkType.name,
                        func.count(Work.id).label('count'))
                 .join(Work, Work.type == WorkType.id))
        query = _where_genre(query, Work.id, genre_id)
        query = (query.group_by(WorkType.id, WorkType.name)
                 .order_by(desc('count')))
        _log_query('stats_worktypecounts', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_worktypecounts', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_genresbyyear() -> ResponseType:
    """
    Works per genre by the year of their earliest edition. A work counts
    in each of its genres.

    Returns:
        ResponseType: [{"year", "count", "genre_id", "genre_abbr"}] sorted
        by year.
    """
    session = new_session()
    try:
        first = _first_years()
        query = (select(first.c.year,
                        func.count(first.c.work_id).label('count'),
                        Genre.id.label('genre_id'),
                        Genre.abbr.label('genre_abbr'))
                 .select_from(first)
                 .join(WorkGenre, WorkGenre.work_id == first.c.work_id)
                 .join(Genre, Genre.id == WorkGenre.genre_id)
                 .group_by(first.c.year, Genre.id, Genre.abbr)
                 .order_by(first.c.year))
        _log_query('stats_genresbyyear', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except SQLAlchemyError as exp:
        return _stats_error('stats_genresbyyear', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


TAG_COUNT = 30


def stats_tagcounts(type_id: Optional[int] = None,
                    genre: Optional[str] = None,
                    count: Optional[int] = TAG_COUNT) -> ResponseType:
    """
    The most common work tags, optionally of one tag type. count None
    returns every tag.

    Returns:
        ResponseType: Dict containing:
            - types: [{"id", "name"}] all tag types
            - tags: [{"id", "name", "count"}] works per tag, most first,
              at most count rows
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        types = [{'id': t.id, 'name': t.name} for t in
                 session.query(TagType).order_by(TagType.id).all()]
        query = (select(Tag.id, Tag.name,
                        func.count(func.distinct(WorkTag.work_id))
                        .label('count'))
                 .join(WorkTag, WorkTag.tag_id == Tag.id))
        if type_id is not None:
            query = query.where(Tag.type_id == type_id)
        query = _where_genre(query, WorkTag.work_id, genre_id)
        query = (query.group_by(Tag.id, Tag.name)
                 .order_by(desc('count'), Tag.name).limit(count))
        _log_query('stats_tagcounts', query)
        tags = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_tagcounts', exp)
    return ResponseType({'types': types, 'tags': tags},
                        HttpResponseCode.OK.value)


def stats_tagsbydecade(type_id: Optional[int] = None,
                       genre: Optional[str] = None,
                       count: int = 20) -> ResponseType:
    """
    Works per tag and decade of their earliest edition, for the count
    most common tags (of one type, if given).

    Returns:
        ResponseType: [{"year" (first year of the decade), "count",
        "tag_id", "tag_name"}] sorted by decade.
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        top = (select(WorkTag.tag_id)
               .join(Tag, Tag.id == WorkTag.tag_id))
        if type_id is not None:
            top = top.where(Tag.type_id == type_id)
        top = _where_genre(top, WorkTag.work_id, genre_id)
        top = (top.group_by(WorkTag.tag_id)
               .order_by(desc(func.count(WorkTag.work_id))).limit(count))
        first = _first_years()
        decade = (first.c.year // 10 * 10).label('year')
        query = (select(decade,
                        func.count(func.distinct(first.c.work_id))
                        .label('count'),
                        Tag.id.label('tag_id'), Tag.name.label('tag_name'))
                 .select_from(first)
                 .join(WorkTag, WorkTag.work_id == first.c.work_id)
                 .join(Tag, Tag.id == WorkTag.tag_id)
                 .where(Tag.id.in_(top)))
        query = _where_genre(query, first.c.work_id, genre_id)
        query = (query.group_by(decade, Tag.id, Tag.name)
                 .order_by(decade))
        _log_query('stats_tagsbydecade', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_tagsbydecade', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_bookseries(genre: Optional[str] = None,
                     count: Optional[int] = TOP_LIST_LENGTH) -> ResponseType:
    """
    Book series: the longest, and the share of works in a series by the
    year of their earliest edition.

    Returns:
        ResponseType: Dict containing:
            - longest: [{"id", "name", "works"}] the count series with
              most works (every series if count is None)
            - by_year: [{"year", "total", "in_series"}] sorted by year
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        longest = (select(Bookseries.id, Bookseries.name,
                          func.count(Work.id).label('works'))
                   .join(Work, Work.bookseries_id == Bookseries.id))
        longest = _where_genre(longest, Work.id, genre_id)
        longest = (longest.group_by(Bookseries.id, Bookseries.name)
                   .order_by(desc('works'), Bookseries.name)
                   .limit(count))
        _log_query('stats_bookseries (longest)', longest)
        first = _first_years()
        by_year = (select(first.c.year,
                          func.count(Work.id).label('total'),
                          func.count(Work.bookseries_id).label('in_series'))
                   .select_from(first)
                   .join(Work, Work.id == first.c.work_id))
        by_year = _where_genre(by_year, Work.id, genre_id)
        by_year = by_year.group_by(first.c.year).order_by(first.c.year)
        _log_query('stats_bookseries (by_year)', by_year)
        result = {
            'longest': [dict(r._mapping) for r in session.execute(longest)],
            'by_year': [dict(r._mapping) for r in session.execute(by_year)],
        }
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_bookseries', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


# --- Statistics page, phase 4: publishers, stories and magazines -------

def stats_pubseriescounts(genre: Optional[str] = None,
                          count: Optional[int] = TOP_LIST_LENGTH
                          ) -> ResponseType:
    """
    Publisher series: how many editions belong to one, and the largest.

    Returns:
        ResponseType: Dict containing:
            - editions: Editions counted (int)
            - in_series: Of those, editions in a publisher series (int)
            - series: [{"id", "name", "publisher_id", "publisher_name",
              "editions"}] the count largest series (every series if
              count is None)
    """
    session = new_session()
    try:
        genre_id = _genre_id(session, genre)
        totals = select(func.count(Edition.id),
                        func.count(Edition.pubseries_id))
        totals = _where_genre(totals, Edition.work_id, genre_id)
        editions, in_series = session.execute(totals).one()
        query = (select(Pubseries.id, Pubseries.name,
                        Publisher.id.label('publisher_id'),
                        Publisher.name.label('publisher_name'),
                        func.count(Edition.id).label('editions'))
                 .join(Edition, Edition.pubseries_id == Pubseries.id)
                 .outerjoin(Publisher, Publisher.id == Pubseries.publisher_id))
        query = _where_genre(query, Edition.work_id, genre_id)
        query = (query.group_by(Pubseries.id, Publisher.id)
                 .order_by(desc('editions'), Pubseries.name)
                 .limit(count))
        _log_query('stats_pubseriescounts', query)
        series = [dict(r._mapping) for r in session.execute(query)]
    except (SQLAlchemyError, _UnknownGenre) as exp:
        return _stats_error('stats_pubseriescounts', exp)
    return ResponseType({'editions': editions, 'in_series': in_series,
                         'series': series}, HttpResponseCode.OK.value)


def stats_storychannels(storytype_id: Optional[int] = None) -> ResponseType:
    """
    Stories by where they first appeared in Finnish: a magazine, a
    single-author collection or an anthology (a book with stories by
    several authors), by the year of that first appearance. When a story
    first appeared in a magazine and a book in the same year, the magazine
    counts.

    Returns:
        ResponseType: [{"year", "channel" ("magazine", "collection" or
        "anthology"), "count"}] sorted by year.
    """
    session = new_session()
    try:
        # Books whose stories have more than one author are anthologies.
        authors = (select(EditionShortStory.edition_id.label('edition_id'),
                          func.count(func.distinct(StoryContributor.person_id))
                          .label('authors'))
                   .join(StoryContributor,
                         StoryContributor.shortstory_id ==
                         EditionShortStory.shortstory_id)
                   .where(StoryContributor.role_id == 1)
                   .group_by(EditionShortStory.edition_id).subquery())
        places = union_all(
            select(EditionShortStory.shortstory_id.label('story_id'),
                   Edition.pubyear.label('year'),
                   # 0 = magazine, 1 = collection, 2 = anthology; lowest
                   # wins in a tie.
                   case((authors.c.authors > 1, 2), else_=1)
                   .label('channel'))
            .join(Edition, Edition.id == EditionShortStory.edition_id)
            .outerjoin(authors,
                       authors.c.edition_id == EditionShortStory.edition_id),
            select(IssueContent.shortstory_id, Issue.year, literal(0))
            .join(Issue, Issue.id == IssueContent.issue_id)
            .where(IssueContent.shortstory_id.isnot(None))).subquery()
        first = (select(places.c.story_id,
                        func.min(places.c.year).label('year'))
                 .where(places.c.year > 0)
                 .group_by(places.c.story_id).subquery())
        firsts = (select(first.c.story_id, first.c.year,
                         func.min(places.c.channel).label('channel'))
                  .join(places, and_(places.c.story_id == first.c.story_id,
                                     places.c.year == first.c.year))
                  .group_by(first.c.story_id, first.c.year))
        if storytype_id is not None:
            firsts = (firsts.join(ShortStory,
                                  ShortStory.id == first.c.story_id)
                      .where(ShortStory.story_type == storytype_id))
        firsts = firsts.subquery()
        query = (select(firsts.c.year, firsts.c.channel,
                        func.count().label('count'))
                 .group_by(firsts.c.year, firsts.c.channel)
                 .order_by(firsts.c.year, firsts.c.channel))
        _log_query('stats_storychannels', query)
        names = {0: 'magazine', 1: 'collection', 2: 'anthology'}
        result = [{'year': r.year, 'channel': names[r.channel],
                   'count': r.count} for r in session.execute(query)]
    except SQLAlchemyError as exp:
        return _stats_error('stats_storychannels', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_magazinestats() -> ResponseType:
    """
    Every magazine with issues: years published, issue and story counts.

    Returns:
        ResponseType: [{"id", "name", "type", "first", "last", "issues",
        "stories"}], most issues first. first/last are the earliest and
        latest issue year (None when no issue has a year).
    """
    session = new_session()
    try:
        stories = (select(Issue.magazine_id.label('magazine_id'),
                          func.count(func.distinct(
                              IssueContent.shortstory_id)).label('stories'))
                   .join(IssueContent, IssueContent.issue_id == Issue.id)
                   .group_by(Issue.magazine_id).subquery())
        year = func.nullif(Issue.year, 0)
        query = (select(Magazine.id, Magazine.name,
                        MagazineType.name.label('type'),
                        func.min(year).label('first'),
                        func.max(year).label('last'),
                        func.count(Issue.id).label('issues'),
                        func.coalesce(func.max(stories.c.stories), 0)
                        .label('stories'))
                 .join(Issue, Issue.magazine_id == Magazine.id)
                 .outerjoin(MagazineType, MagazineType.id == Magazine.type_id)
                 .outerjoin(stories, stories.c.magazine_id == Magazine.id)
                 .group_by(Magazine.id, MagazineType.name)
                 .order_by(desc('issues'), Magazine.name))
        _log_query('stats_magazinestats', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except SQLAlchemyError as exp:
        return _stats_error('stats_magazinestats', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_magazinecontents() -> ResponseType:
    """
    Magazine contents (stories, articles, flash fiction…) by issue year
    and story type. A text in several issues counts in each.

    Returns:
        ResponseType: [{"year", "count", "storytype_id",
        "storytype_name"}] sorted by year.
    """
    session = new_session()
    try:
        query = (select(Issue.year, func.count(IssueContent.id)
                        .label('count'),
                        StoryType.id.label('storytype_id'),
                        StoryType.name.label('storytype_name'))
                 .join(IssueContent, IssueContent.issue_id == Issue.id)
                 .join(ShortStory,
                       ShortStory.id == IssueContent.shortstory_id)
                 .outerjoin(StoryType, StoryType.id == ShortStory.story_type)
                 .where(Issue.year > 0)
                 .group_by(Issue.year, StoryType.id, StoryType.name)
                 .order_by(Issue.year))
        _log_query('stats_magazinecontents', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except SQLAlchemyError as exp:
        return _stats_error('stats_magazinecontents', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


# --- Statistics page, phase 5: awards -----------------------------------
#
# Only winners that are in this database are recorded (the importer saves
# matched works and stories), so every awarded work or story has been
# published in Finnish.

def stats_awardcounts() -> ResponseType:
    """
    Recorded winners per award.

    Returns:
        ResponseType: [{"id", "name", "domestic", "works", "stories",
        "people", "total"}], most first. people are personal awards
        (e.g. lifetime achievement).
    """
    session = new_session()
    try:
        query = (select(Award.id, Award.name, Award.domestic,
                        func.count(Awarded.work_id).label('works'),
                        func.count(Awarded.story_id).label('stories'),
                        func.count(Awarded.person_id).label('people'),
                        func.count(Awarded.id).label('total'))
                 .join(Awarded, Awarded.award_id == Award.id)
                 .group_by(Award.id)
                 .order_by(desc('total'), Award.name))
        _log_query('stats_awardcounts', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except SQLAlchemyError as exp:
        return _stats_error('stats_awardcounts', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_awardlag() -> ResponseType:
    """
    Years from a foreign award to the winner's first Finnish publication
    (works: earliest edition; stories: earliest edition or magazine
    issue). Negative when the Finnish edition came first.

    Returns:
        ResponseType: Dict containing:
            - total: Awarded works/stories counted (int)
            - median: Median years (float or None)
            - lags: [{"lag", "count"}] sorted by lag
            - by_award: [{"id", "name", "count", "q1", "median", "q3"}],
              most winners first
    """
    session = new_session()
    try:
        years = _item_years('all')
        item = union_all(
            select(Awarded.id.label('awarded_id'),
                   literal('w', String).label('kind'),
                   Awarded.work_id.label('item_id'))
            .where(Awarded.work_id.isnot(None)),
            select(Awarded.id, literal('s', String), Awarded.story_id)
            .where(Awarded.story_id.isnot(None))).subquery()
        query = (select(Award.id, Award.name,
                        (years.c.year - Awarded.year).label('lag'))
                 .select_from(item)
                 .join(Awarded, Awarded.id == item.c.awarded_id)
                 .join(Award, Award.id == Awarded.award_id)
                 .join(years, and_(years.c.kind == item.c.kind,
                                   years.c.item_id == item.c.item_id))
                 .where(Award.domestic.isnot(True), Awarded.year > 0))
        _log_query('stats_awardlag', query)
        rows = session.execute(query).all()
    except SQLAlchemyError as exp:
        return _stats_error('stats_awardlag', exp)

    lags = [r.lag for r in rows]
    counts: Dict[int, int] = {}
    awards: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        counts[r.lag] = counts.get(r.lag, 0) + 1
        awards.setdefault(r.id, {'id': r.id, 'name': r.name, 'lags': []})
        awards[r.id]['lags'].append(r.lag)
    by_award = sorted(
        ({'id': a['id'], 'name': a['name'], 'count': len(a['lags']),
          **_quartiles(a['lags'])} for a in awards.values()),
        key=lambda a: (-a['count'], a['name']))
    result = {
        'total': len(lags),
        'median': _quartiles(lags)['median'] if lags else None,
        'lags': [{'lag': k, 'count': v} for k, v in sorted(counts.items())],
        'by_award': by_award,
    }
    return ResponseType(result, HttpResponseCode.OK.value)


def stats_topawarded(count: int = TOP_LIST_LENGTH) -> ResponseType:
    """
    People with most recorded awards: personal awards plus awards for
    works and stories they wrote (each awarded row once per person).

    Returns:
        ResponseType: [{"id", "name", "alt_name", "awards", "personal",
        "works", "stories"}], most awards first, at most count rows.
    """
    session = new_session()
    try:
        winners = union(
            select(Awarded.id.label('awarded_id'),
                   Awarded.person_id.label('person_id'),
                   literal('p', String).label('kind'))
            .where(Awarded.person_id.isnot(None)),
            select(Awarded.id, WorkContributor.person_id, literal('w', String))
            .join(WorkContributor,
                  WorkContributor.work_id == Awarded.work_id)
            .where(WorkContributor.role_id == 1),
            select(Awarded.id, StoryContributor.person_id,
                   literal('s', String))
            .join(StoryContributor,
                  StoryContributor.shortstory_id == Awarded.story_id)
            .where(StoryContributor.role_id == 1)).subquery()
        query = (select(Person.id, Person.name, Person.alt_name,
                        func.count(func.distinct(winners.c.awarded_id))
                        .label('awards'),
                        func.count().filter(winners.c.kind == 'p')
                        .label('personal'),
                        func.count().filter(winners.c.kind == 'w')
                        .label('works'),
                        func.count().filter(winners.c.kind == 's')
                        .label('stories'))
                 .select_from(winners)
                 .join(Person, Person.id == winners.c.person_id)
                 .group_by(Person.id)
                 .order_by(desc('awards'), Person.name)
                 .limit(count))
        _log_query('stats_topawarded', query)
        result = [dict(r._mapping) for r in session.execute(query)]
    except SQLAlchemyError as exp:
        return _stats_error('stats_topawarded', exp)
    return ResponseType(result, HttpResponseCode.OK.value)


# --- Statistics page, phase 6: coverage ---------------------------------

def stats_coverage() -> ResponseType:
    """
    How complete the bibliography's data is: for editions, works, people
    and short stories, the total and how many have each detail recorded.

    Returns:
        ResponseType: Dict of groups, each {"total": int, <detail>: int}:
            - editions: image, pages, isbn, size, binding, verified
            - works: description, tags, genre, orig_year, language,
              translator (translated works with a known translator;
              translated = translated_works)
            - people: birth_year, nationality, image, bio
            - stories: year, language
    """
    session = new_session()
    try:
        def has(column: Any) -> Any:
            return func.count(column).filter(column.isnot(None))

        def exists_for(column: Any, key: Any, *extra: Any) -> Any:
            return func.count().filter(
                select(column).where(column == key, *extra).exists())

        editions = session.execute(select(
            func.count(Edition.id),
            exists_for(EditionImage.edition_id, Edition.id,
                       EditionImage.image_src != ''),
            func.count().filter(Edition.pages > 0),
            func.count().filter(func.coalesce(Edition.isbn, '') != ''),
            func.count().filter(Edition.size > 0),
            func.count().filter(Edition.binding_id > 1),
            func.count().filter(Edition.verified.is_(True)))).one()

        finnish_id = (session.query(Language.id)
                      .filter(Language.name == 'suomi').scalar())
        translated = and_(Work.language.isnot(None),
                          Work.language != finnish_id)
        translator_known = (
            select(Edition.id)
            .join(EditionContributor,
                  EditionContributor.edition_id == Edition.id)
            .where(Edition.work_id == Work.id,
                   EditionContributor.role_id == TRANSLATOR_ROLE_ID)
            .exists())
        works = session.execute(select(
            func.count(Work.id),
            func.count().filter(func.coalesce(Work.description, '') != ''),
            exists_for(WorkTag.work_id, Work.id),
            exists_for(WorkGenre.work_id, Work.id),
            func.count().filter(Work.pubyear > 0),
            has(Work.language),
            func.count().filter(translated),
            func.count().filter(and_(translated, translator_known)))).one()

        people = session.execute(select(
            func.count(Person.id),
            func.count().filter(Person.dob > 0),
            has(Person.nationality_id),
            exists_for(PersonImage.person_id, Person.id,
                       PersonImage.src != ''),
            func.count().filter(func.coalesce(Person.bio, '') != ''))).one()

        stories = session.execute(select(
            func.count(ShortStory.id),
            func.count().filter(ShortStory.pubyear > 0),
            has(ShortStory.language))).one()
        _log_query('stats_coverage', 'coverage counts')
    except SQLAlchemyError as exp:
        return _stats_error('stats_coverage', exp)

    def group(names: List[str], values: Any) -> Dict[str, int]:
        return dict(zip(['total'] + names, (int(v) for v in values)))

    result = {
        'editions': group(['image', 'pages', 'isbn', 'size', 'binding',
                           'verified'], editions),
        'works': group(['description', 'tags', 'genre', 'orig_year',
                        'language', 'translated_works', 'translator'],
                       works),
        'people': group(['birth_year', 'nationality', 'image', 'bio'],
                        people),
        'stories': group(['year', 'language'], stories),
    }
    return ResponseType(result, HttpResponseCode.OK.value)
