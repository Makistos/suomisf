"""
British Science Fiction Award ISFDB import test.

Regression test for the rule that short fiction is sometimes published as a
stand-alone *work* in Finnish (recorded in the work table, not the
shortstory table). The importer must therefore match short-story award
categories against works as well.

Concrete case: "This Is How You Lose the Time War" is stored as work 6057
("Tällä tavalla hävitään aikasota") and appears in the BSFA "Best Short
Fiction" (short-story) category on ISFDB.

Skips gracefully when ISFDB is unreachable or when the BSFA import sources
have not been seeded.
"""

import pytest

from app.impl_award_import import STATUS_NOT_FOUND, preview_import

# Award 6 is the British Science Fiction Award.
BSFA_AWARD_ID = 6
TIME_WAR_WORK_ID = 6057
TIME_WAR_TITLE_FRAGMENT = "time war"


@pytest.mark.network
@pytest.mark.slow
class TestBsfaShortFictionAsWork:
    """Short fiction published as a work must still be matched."""

    def test_short_fiction_published_as_work_is_matched(self, app):
        result = preview_import(BSFA_AWARD_ID)

        if result.status == 400:
            pytest.skip("BSFA has no ISFDB import sources seeded")
        assert result.status == 200

        data = result.response
        if not data["entries"] and data["errors"]:
            pytest.skip(f"ISFDB unreachable: {data['errors']}")

        matches = [
            e for e in data["entries"]
            if TIME_WAR_TITLE_FRAGMENT in e["title"].lower()
        ]
        assert matches, (
            "'This Is How You Lose the Time War' not found in the BSFA scrape")

        entry = matches[0]
        # It is a short-fiction category winner but exists as a WORK in the DB.
        assert entry["status"] != STATUS_NOT_FOUND, (
            "short fiction published as a work was not matched")
        assert entry["match_type"] == "work"
        assert entry["target_id"] == TIME_WAR_WORK_ID
        # A short-fiction category should resolve to a category id.
        assert entry["category_id"] is not None

    def test_author_mismatch_is_not_matched(self, app):
        """
        A same-title item by a different author must not match.

        Nina Allan is not in the database at all, so none of her scraped
        BSFA entries may match a local work/story, even when another
        author's item shares the original title.
        """
        result = preview_import(BSFA_AWARD_ID)

        if result.status == 400:
            pytest.skip("BSFA has no ISFDB import sources seeded")
        assert result.status == 200

        data = result.response
        if not data["entries"] and data["errors"]:
            pytest.skip(f"ISFDB unreachable: {data['errors']}")

        nina_entries = [
            e for e in data["entries"] if e["author"] == "Nina Allan"
        ]
        assert nina_entries, "expected Nina Allan entries in the BSFA scrape"
        for e in nina_entries:
            assert e["status"] == STATUS_NOT_FOUND, (
                f"{e['title']!r} by Nina Allan wrongly matched "
                f"{e['target_title']!r}")
