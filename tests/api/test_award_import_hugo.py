"""
Hugo award ISFDB import test.

Scrapes the Hugo award winners from ISFDB and compares them against what
is stored in the database, exercising the import preview pipeline
(app.impl_award_import).

These tests hit isfdb.org over the network and are marked accordingly;
they skip gracefully when ISFDB is unreachable or when the Hugo import
sources have not been seeded (award_import_source, migration 029).

The tests call the impl functions directly, so they depend on the `app`
fixture, which redirects new_session() to the test database.
"""

import pytest

from app.impl_award_import import (
    STATUS_AMBIGUOUS,
    STATUS_AWARDED,
    STATUS_NEW,
    STATUS_NOT_FOUND,
    parse_award_category,
    preview_import,
)
from app.route_helpers import new_session
from app.orm_decl import Awarded

# Award 2 is "Hugo"; ISFDB category 261 is Hugo "Best Novel".
HUGO_AWARD_ID = 2
HUGO_BEST_NOVEL_CATEGORY = 261
# 1961 Best Novel winner; author name has a "Jr." suffix whose punctuation
# differs between ISFDB ("Walter M. Miller, Jr.") and the DB alt_name
# ("Walter M. Miller Jr."). Stored as work 1789, already awarded.
CANTICLE_WORK_ID = 1789


@pytest.mark.network
@pytest.mark.slow
class TestHugoIsfdbImport:
    """Scrape Hugo winners from ISFDB and compare against the database."""

    def test_scrape_hugo_best_novel(self, app):
        """The ISFDB Best Novel page parses into Hugo winners."""
        try:
            scraped = parse_award_category(HUGO_BEST_NOVEL_CATEGORY, 0)
        except Exception as exc:  # noqa: BLE001 - network flakiness -> skip
            pytest.skip(f"ISFDB unreachable: {exc}")

        assert scraped.award_type == "Hugo Award"
        assert scraped.category == "Best Novel"
        # Hugo Best Novel has been awarded since 1953; expect many winners.
        assert len(scraped.winners) > 50

        titles = {w.title for w in scraped.winners}
        # First-ever Hugo Best Novel (1953); a stable historical fixture.
        assert "The Demolished Man" in titles

        # Winner rows are well-formed.
        for w in scraped.winners:
            assert w.title
            assert w.year is None or 1950 <= w.year <= 2100

    def test_preview_matches_database(self, app):
        """
        The import preview for Hugo is consistent with the awarded rows
        already in the database.
        """
        result = preview_import(HUGO_AWARD_ID)

        # Skip if the Hugo import sources have not been seeded.
        if result.status == 400:
            pytest.skip("Hugo has no ISFDB import sources seeded")
        assert result.status == 200

        data = result.response
        assert data["award_name"] == "Hugo"

        entries = data["entries"]
        # If every source failed to fetch, treat as a network skip.
        if not entries and data["errors"]:
            pytest.skip(f"ISFDB unreachable: {data['errors']}")
        assert len(entries) > 50

        # Reported counts add up to the number of entries.
        counts = data["counts"]
        assert set(counts) == {
            STATUS_NEW, STATUS_AWARDED, STATUS_NOT_FOUND, STATUS_AMBIGUOUS,
        }
        assert sum(counts.values()) == len(entries)

        # Build the set of works/stories already awarded the Hugo in the DB.
        session = new_session()
        rows = session.query(Awarded.work_id, Awarded.story_id).filter(
            Awarded.award_id == HUGO_AWARD_ID).all()
        db_work_ids = {r.work_id for r in rows if r.work_id is not None}
        db_story_ids = {r.story_id for r in rows if r.story_id is not None}

        awarded_entries = 0
        for e in entries:
            status = e["status"]
            db_ids = db_work_ids if e["match_type"] == "work" else db_story_ids

            if status == STATUS_AWARDED:
                # An "awarded" entry must correspond to a real DB row.
                awarded_entries += 1
                assert e["target_id"] in db_ids, (
                    f"{e['title']!r} marked awarded but no matching "
                    f"awarded row exists in the database")
            elif status == STATUS_NEW:
                # A "new" entry must NOT already be awarded (no duplicates).
                assert e["target_id"] not in db_ids, (
                    f"{e['title']!r} marked new but is already awarded")
            elif status == STATUS_NOT_FOUND:
                assert e["match_type"] is None
                assert e["target_id"] is None
            elif status == STATUS_AMBIGUOUS:
                assert len(e["candidates"]) > 1

        # ISFDB and the database share at least some Hugo winners; if this
        # is zero, matching (orig_title) is broken.
        assert awarded_entries > 0, (
            "No scraped Hugo winner matched an existing awarded row")

    def test_hugo_2017plus_short_fiction_authors_are_real(self, app):
        """
        Hugo pages from 2017 on use a voting-statistics layout; the scraper
        must read the winner's real author, not a numeric vote-count cell.
        Uses Best Novelette (category 262).
        """
        try:
            scraped = parse_award_category(262, 2)
        except Exception as exc:  # noqa: BLE001 - network flakiness -> skip
            pytest.skip(f"ISFDB unreachable: {exc}")

        recent = [w for w in scraped.winners
                  if w.year is not None and w.year >= 2017]
        assert recent, "no Hugo Best Novelette winners from 2017 on"
        for w in recent:
            assert w.author, f"{w.year}: missing author"
            assert not w.author.isdigit(), (
                f"{w.year}: author is numeric ({w.author!r})")

        # 2017 Best Novelette: stable historical fixture.
        by_year = {w.year: w for w in recent}
        assert 2017 in by_year
        assert by_year[2017].title == "The Tomato Thief"
        assert by_year[2017].author == "Ursula Vernon"

    def test_author_name_punctuation_still_matches(self, app):
        """
        A winner whose author name differs only in punctuation still
        matches. "A Canticle for Leibowitz" (1961) is work 1789, already
        awarded; ISFDB author "Walter M. Miller, Jr." vs DB "Walter M.
        Miller Jr." must not defeat the match.
        """
        result = preview_import(HUGO_AWARD_ID)
        if result.status == 400:
            pytest.skip("Hugo has no ISFDB import sources seeded")
        assert result.status == 200

        data = result.response
        if not data["entries"] and data["errors"]:
            pytest.skip(f"ISFDB unreachable: {data['errors']}")

        canticle = [
            e for e in data["entries"]
            if "canticle for leibowitz" in e["title"].lower()
        ]
        assert canticle, "'A Canticle for Leibowitz' not found in Hugo scrape"
        entry = canticle[0]
        assert entry["match_type"] == "work"
        assert entry["target_id"] == CANTICLE_WORK_ID
        assert entry["status"] == STATUS_AWARDED
