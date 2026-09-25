"""
Unit tests for ITEM_PERSON award-import matching (_build_person_entry).

Pure logic tests (no network, no database): verify that a scraped
person-award winner (a name, not a title) resolves against a set of local
Person stand-ins the same way title matching resolves against works/
stories - new / awarded / ambiguous / not_found - and that a scraped name
with no match at all doesn't crash (regression: _resolve_matches indexes
matches[0] once ambiguity is ruled out, so the caller must never hand it
a non-empty candidate_sets entry wrapping an empty match list).
"""

from types import SimpleNamespace

from app.impl_award_import import (
    STATUS_AMBIGUOUS,
    STATUS_AWARDED,
    STATUS_NEW,
    STATUS_NOT_FOUND,
    ScrapedWinner,
    _build_person_entry,
    _person_name_variants,
)


def _person(person_id, alt_name=None, name=None):
    """A stand-in for a Person row, shaped for _person_name_variants."""
    return SimpleNamespace(id=person_id, alt_name=alt_name, name=name)


def _index(*people):
    return [(p, _person_name_variants(p)) for p in people]


def _winner(name, year=2024):
    return ScrapedWinner(year=year, title=name, author="")


# A minimal category_lookup with just the one category person-award
# entries resolve to (mirrors the real "Elämäntyöpalkinto" row).
_CATEGORY_LOOKUP = {("elämäntyöpalkinto", 0): 12}


def test_no_match_is_not_found():
    person_index = _index(_person(1, alt_name="Jane Doe", name="Doe, Jane"))
    entry = _build_person_entry(
        _winner("Someone Else"), person_index, set(), _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_NOT_FOUND
    assert entry["target_id"] is None
    assert entry["candidates"] == []


def test_empty_index_is_not_found():
    # Regression: an empty person_index (or no match at all) must not crash
    # _resolve_matches by handing it a non-empty candidate_sets entry
    # wrapping zero matches.
    entry = _build_person_entry(
        _winner("N. K. Jemisin"), [], set(), _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_NOT_FOUND


def test_single_match_is_new():
    person_index = _index(_person(42, alt_name="N. K. Jemisin",
                                  name="Jemisin, N. K."))
    entry = _build_person_entry(
        _winner("N. K. Jemisin"), person_index, set(), _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_NEW
    assert entry["match_type"] == "person"
    assert entry["target_id"] == 42
    assert entry["target_title"] == "N. K. Jemisin"
    assert entry["our_category"] == "Elämäntyöpalkinto"
    assert entry["category_id"] == 12


def test_matches_via_lastname_comma_firstname_variant():
    # No alt_name at all - falls back to deriving "Firstname Lastname" from
    # the stored "Lastname, Firstname" primary name.
    person_index = _index(_person(7, alt_name=None, name="Heinlein, Robert A."))
    entry = _build_person_entry(
        _winner("Robert A. Heinlein"), person_index, set(), _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_NEW
    assert entry["target_id"] == 7


def test_already_awarded_person_is_awarded():
    person_index = _index(_person(42, alt_name="N. K. Jemisin"))
    entry = _build_person_entry(
        _winner("N. K. Jemisin"), person_index, {42}, _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_AWARDED
    assert entry["target_id"] == 42


def test_two_people_with_the_same_name_is_ambiguous():
    person_index = _index(
        _person(1, alt_name="John Smith"),
        _person(2, alt_name="John Smith"),
    )
    entry = _build_person_entry(
        _winner("John Smith"), person_index, set(), _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_AMBIGUOUS
    assert entry["target_id"] is None
    assert set(entry["candidates"]) == {1, 2}


def test_ambiguous_name_resolves_to_the_one_already_holding_this_award():
    person_index = _index(
        _person(1, alt_name="John Smith"),
        _person(2, alt_name="John Smith"),
    )
    entry = _build_person_entry(
        _winner("John Smith"), person_index, {2}, _CATEGORY_LOOKUP)
    assert entry["status"] == STATUS_AWARDED
    assert entry["target_id"] == 2
