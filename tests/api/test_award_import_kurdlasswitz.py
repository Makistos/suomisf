"""
Kurd Lasswitz Preis ISFDB import test.

Regression test for title matching that tolerates a leading article. Work
4843 is stored with orig_title "The Speaker for the Dead", but ISFDB (and
the actual original title) is "Speaker for the Dead". The winner must still
match despite the leading "The".

Skips gracefully when ISFDB is unreachable or when the Kurd Lasswitz import
sources have not been seeded.
"""

import pytest

from app.impl_award_import import STATUS_NOT_FOUND, preview_import

# Award 32 is the Kurd Lasswitz Preis.
KURD_LASSWITZ_AWARD_ID = 32
SPEAKER_WORK_ID = 4843


@pytest.mark.network
@pytest.mark.slow
class TestKurdLasswitzLeadingArticle:
    """A leading article difference must not break title matching."""

    def test_leading_article_title_still_matches(self, app):
        result = preview_import(KURD_LASSWITZ_AWARD_ID)

        if result.status == 400:
            pytest.skip("Kurd Lasswitz has no ISFDB import sources seeded")
        assert result.status == 200

        data = result.response
        if not data["entries"] and data["errors"]:
            pytest.skip(f"ISFDB unreachable: {data['errors']}")

        matches = [
            e for e in data["entries"]
            if "speaker for the dead" in e["title"].lower()
        ]
        assert matches, "'Speaker for the Dead' not found in the scrape"
        entry = matches[0]
        assert entry["status"] != STATUS_NOT_FOUND, (
            "leading-article difference wrongly blocked the match")
        assert entry["match_type"] == "work"
        assert entry["target_id"] == SPEAKER_WORK_ID
