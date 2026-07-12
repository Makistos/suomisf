"""
Unit tests for the award-import match resolution (_resolve_matches).

These are pure logic tests (no network, no database): they verify how the
importer decides between candidate works/stories, in particular that an
ambiguous title is resolved to a candidate that already holds THIS award.
"""

from types import SimpleNamespace

from app.impl_award_import import (
    STATUS_AMBIGUOUS,
    STATUS_AWARDED,
    STATUS_NEW,
    STATUS_NOT_FOUND,
    _resolve_matches,
)


def _c(item_id, title="Title"):
    """A stand-in for a matched work/story row."""
    return SimpleNamespace(id=item_id, title=title)


def test_single_match_is_new():
    status, match_type, _, matched, cands = _resolve_matches(
        [("work", 1, set(), [_c(10)])])
    assert status == STATUS_NEW
    assert match_type == "work"
    assert matched.id == 10
    assert cands == []


def test_single_match_already_awarded_is_awarded():
    status, _, _, matched, _ = _resolve_matches(
        [("work", 1, {10}, [_c(10)])])
    assert status == STATUS_AWARDED
    assert matched.id == 10


def test_multiple_candidates_without_this_award_is_ambiguous():
    status, match_type, _, matched, cands = _resolve_matches(
        [("work", 1, set(), [_c(10), _c(20)])])
    assert status == STATUS_AMBIGUOUS
    assert match_type == "work"
    assert matched is None
    assert set(cands) == {10, 20}


def test_multiple_candidates_resolves_to_the_one_holding_this_award():
    # Two works share the title; work 20 already holds this award, so the
    # ambiguity resolves to it rather than being flagged ambiguous.
    status, match_type, _, matched, cands = _resolve_matches(
        [("work", 1, {20}, [_c(10), _c(20)])])
    assert status == STATUS_AWARDED
    assert match_type == "work"
    assert matched.id == 20
    assert cands == []


def test_existing_award_resolves_across_types():
    # A new work match exists, but a short story already holds this award;
    # the existing award (any type) wins, so we point at the short story.
    status, match_type, _, matched, _ = _resolve_matches([
        ("work", 1, set(), [_c(10)]),
        ("short", 2, {30}, [_c(30)]),
    ])
    assert status == STATUS_AWARDED
    assert match_type == "short"
    assert matched.id == 30


def test_award_check_precedes_ambiguity_across_types():
    # Work side is ambiguous (no award), short side has the award: the
    # existing award must still resolve it instead of reporting ambiguous.
    status, match_type, _, matched, _ = _resolve_matches([
        ("work", 1, set(), [_c(10), _c(11)]),
        ("short", 2, {30}, [_c(30)]),
    ])
    assert status == STATUS_AWARDED
    assert match_type == "short"
    assert matched.id == 30


def test_no_candidates_is_not_found():
    status, match_type, _, matched, cands = _resolve_matches([])
    assert status == STATUS_NOT_FOUND
    assert match_type is None
    assert matched is None
    assert cands == []
