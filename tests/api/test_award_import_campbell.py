"""
Campbell Memorial Award ISFDB import test.

Regression test for author matching that tolerates a differing/absent
middle name or initial. "Helliconia Spring" is stored as work 4351 with
author "Brian Aldiss", but ISFDB lists the author as "Brian W. Aldiss".
The winner must still match.

Skips gracefully when ISFDB is unreachable or when the Campbell import
sources have not been seeded.
"""

import pytest

from app.impl_award_import import STATUS_NOT_FOUND, preview_import

# Award 10 is the John W. Campbell Memorial Award.
CAMPBELL_AWARD_ID = 10
HELLICONIA_WORK_ID = 4351


@pytest.mark.network
@pytest.mark.slow
class TestCampbellMiddleInitial:
    """Author middle-initial differences must not break matching."""

    def test_middle_initial_author_still_matches(self, app):
        result = preview_import(CAMPBELL_AWARD_ID)

        if result.status == 400:
            pytest.skip("Campbell has no ISFDB import sources seeded")
        assert result.status == 200

        data = result.response
        if not data["entries"] and data["errors"]:
            pytest.skip(f"ISFDB unreachable: {data['errors']}")

        matches = [
            e for e in data["entries"]
            if "helliconia spring" in e["title"].lower()
        ]
        assert matches, "'Helliconia Spring' not found in the Campbell scrape"
        entry = matches[0]
        assert entry["status"] != STATUS_NOT_FOUND, (
            "middle-initial author difference wrongly blocked the match")
        assert entry["match_type"] == "work"
        assert entry["target_id"] == HELLICONIA_WORK_ID
