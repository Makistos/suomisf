"""
Unit tests for get_import_source_info, the helper behind the "source of
the information" attribution shown at the bottom of an award page.

Pure logic (no network, no database): checks that the three lookups it
performs match has_import_source's own checks, in the same priority order.
"""

from app.impl_award_import import (
    SFADB_AWARD_SLUGS,
    SFADB_BASE_URL,
    SFADB_PERSON_AWARD_SLUGS,
    WIKIPEDIA_AWARD_SOURCES,
    get_import_source_info,
)


def test_title_based_sfadb_award_points_at_sfadb():
    name = next(iter(SFADB_AWARD_SLUGS))
    info = get_import_source_info(name)
    assert info == {"label": "sfadb.com",
                    "url": f"{SFADB_BASE_URL}/{SFADB_AWARD_SLUGS[name]}"}


def test_person_sfadb_award_points_at_sfadb():
    name = next(iter(SFADB_PERSON_AWARD_SLUGS))
    info = get_import_source_info(name)
    assert info == {"label": "sfadb.com",
                    "url": f"{SFADB_BASE_URL}/{SFADB_PERSON_AWARD_SLUGS[name]}"}


def test_wikipedia_only_award_points_at_wikipedia():
    # Pick an award present in WIKIPEDIA_AWARD_SOURCES but not in either
    # sfadb dict, so the fallback branch is what's actually exercised.
    name = next(n for n in WIKIPEDIA_AWARD_SOURCES
                if n not in SFADB_AWARD_SLUGS
                and n not in SFADB_PERSON_AWARD_SLUGS)
    info = get_import_source_info(name)
    assert info == {"label": "Wikipedia", "url": WIKIPEDIA_AWARD_SOURCES[name].url}


def test_award_with_no_import_source_returns_none():
    assert get_import_source_info("Some award with no importer at all") is None
