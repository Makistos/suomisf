"""
SuomiSF API Collection Tests

Snapshot-based regression tests for anthology works and their
short stories. Each test verifies that the API returns the
correct set of shorts — including full author information —
after migration 001 (EditionShortStory / StoryContributor).

Tested collections
------------------
work_27   "Yön ja päivän tarinoita" (Vainonen, 12 shorts, 1 author)
          endpoint: GET /api/works/27  (stories field)
          endpoint: GET /api/works/shorts/27

work_1378  omnibus anthology (22 shorts, multiple authors)
           endpoint: GET /api/works/shorts/1378

edition_1585  omnibus anthology (22 shorts, multiple authors)
              endpoint: GET /api/editions/1585/shorts

issue_92  Alienisti 1/2017 (16 stories, multiple authors)
          endpoint: GET /api/issues/92  (stories field)

Snapshots are stored in tests/fixtures/snapshots/ and generated
by tests/scripts/update_snapshots.py.
"""

from typing import Dict, List, Set, Tuple

from .base_test import BaseAPITest


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _author_ids(short: Dict) -> Set[int]:
    """Return the set of author IDs for a short story."""
    return {int(a['id']) for a in short.get('authors', [])}


def _author_id_name_pairs(short: Dict) -> Set[Tuple[int, str]]:
    """Return (id, name) pairs for all authors of a short story."""
    return {
        (int(a['id']), a['name'])
        for a in short.get('authors', [])
    }


def _check_shorts_match_snapshot(
    actual_shorts: List[Dict],
    expected_shorts: List[Dict],
    label: str
) -> None:
    """
    Assert that actual_shorts match expected_shorts.

    Checks:
    - total count
    - every expected short ID is present
    - title matches for each short
    - author IDs match for each short
    - author names match for each short
    """
    assert len(actual_shorts) == len(expected_shorts), (
        f"{label}: expected {len(expected_shorts)} shorts, "
        f"got {len(actual_shorts)}"
    )

    actual_by_id = {int(s['id']): s for s in actual_shorts}
    expected_by_id = {int(s['id']): s for s in expected_shorts}

    for short_id, exp in expected_by_id.items():
        assert short_id in actual_by_id, (
            f"{label}: short {short_id} "
            f"({exp['title']!r}) missing from response"
        )
        act = actual_by_id[short_id]

        assert act['title'] == exp['title'], (
            f"{label} short {short_id}: title mismatch — "
            f"expected {exp['title']!r}, got {act['title']!r}"
        )

        exp_authors = _author_id_name_pairs(exp)
        act_authors = _author_id_name_pairs(act)
        assert act_authors == exp_authors, (
            f"{label} short {short_id} ({exp['title']!r}): "
            f"author mismatch — "
            f"expected {exp_authors}, got {act_authors}"
        )


# -------------------------------------------------------------------
# Test classes
# -------------------------------------------------------------------

class TestWorkCollection(BaseAPITest):
    """
    Tests for GET /api/works/{id} for anthology works.

    Verifies that the 'stories' field in the work response
    contains the correct shorts with their authors after migration.
    """

    def test_work_27_stories_match_snapshot(
            self, api_client, snapshot_manager):
        """
        GET /api/works/27 'Yön ja päivän tarinoita' should contain
        12 short stories, all authored by Vainonen, Jyrki (id 21).

        Snapshot: work_27.json (captured from production before
        migration).

        This test detects the regression where shorts disappeared
        from the work response after migration.
        """
        response = api_client.get('/api/works/27')
        response.assert_success()

        work = response.data
        assert isinstance(work, dict), "Response should be a dict"
        assert 'stories' in work, (
            "Work response should have 'stories' field"
        )

        actual_stories = work['stories']
        assert isinstance(actual_stories, list), (
            "'stories' should be a list"
        )

        snapshot = snapshot_manager.load_snapshot('work_27')
        assert snapshot is not None, (
            "Snapshot 'work_27' not found — run update_snapshots.py"
        )

        expected_stories = snapshot['response']['data']['stories']
        _check_shorts_match_snapshot(
            actual_stories, expected_stories, 'work_27'
        )

    def test_work_27_stories_have_required_fields(self, api_client):
        """
        Each story in GET /api/works/27 should have id, title,
        authors, and type fields.
        """
        response = api_client.get('/api/works/27')
        response.assert_success()

        stories = response.data.get('stories', [])
        assert len(stories) > 0, "Work 27 should have stories"

        for story in stories:
            for field in ('id', 'title', 'authors'):
                assert field in story, (
                    f"Story {story.get('id')} missing '{field}'"
                )

    def test_work_27_stories_author_fields(self, api_client):
        """
        Authors in work 27 stories should have id and name.
        """
        response = api_client.get('/api/works/27')
        response.assert_success()

        for story in response.data.get('stories', []):
            for author in story.get('authors', []):
                assert 'id' in author, (
                    f"Story {story['id']}: author missing 'id'"
                )
                assert 'name' in author, (
                    f"Story {story['id']}: author missing 'name'"
                )


class TestWorkShortsEndpointCollections(BaseAPITest):
    """
    Tests for GET /api/works/shorts/{id} for anthology works.

    Verifies counts, IDs, titles, and author data match snapshots.
    """

    def test_work_27_shorts_match_snapshot(
            self, api_client, snapshot_manager):
        """
        GET /api/works/shorts/27 should return 12 shorts,
        all authored by Vainonen, Jyrki (id 21).

        Snapshot: work_shorts_27.json
        """
        response = api_client.get('/api/works/shorts/27')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"

        snapshot = snapshot_manager.load_snapshot('work_shorts_27')
        assert snapshot is not None, (
            "Snapshot 'work_shorts_27' not found"
        )

        expected = snapshot['response']['data']
        _check_shorts_match_snapshot(shorts, expected, 'work_shorts_27')

    def test_work_1378_shorts_match_snapshot(
            self, api_client, snapshot_manager):
        """
        GET /api/works/shorts/1378 should return 22 shorts
        with multiple different authors.

        Snapshot: work_shorts_1378.json
        """
        response = api_client.get('/api/works/shorts/1378')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"

        snapshot = snapshot_manager.load_snapshot('work_shorts_1378')
        assert snapshot is not None, (
            "Snapshot 'work_shorts_1378' not found"
        )

        expected = snapshot['response']['data']
        _check_shorts_match_snapshot(
            shorts, expected, 'work_shorts_1378'
        )


class TestEditionShortsCollections(BaseAPITest):
    """
    Tests for GET /api/editions/{id}/shorts for anthology editions.

    Verifies counts, IDs, titles, and author data match snapshots.
    """

    def test_edition_28_shorts_match_snapshot(
            self, api_client, snapshot_manager):
        """
        GET /api/editions/28/shorts ('Yön ja päivän tarinoita')
        should return 12 shorts, all by Vainonen, Jyrki (id 21).

        Snapshot: edition_shorts_28.json
        """
        response = api_client.get('/api/editions/28/shorts')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"

        snapshot = snapshot_manager.load_snapshot('edition_shorts_28')
        assert snapshot is not None, (
            "Snapshot 'edition_shorts_28' not found"
        )

        expected = snapshot['response']['data']
        _check_shorts_match_snapshot(
            shorts, expected, 'edition_shorts_28'
        )

    def test_edition_1585_shorts_match_snapshot(
            self, api_client, snapshot_manager):
        """
        GET /api/editions/1585/shorts should return 22 shorts
        with multiple different authors.

        Snapshot: edition_shorts_1585.json
        """
        response = api_client.get('/api/editions/1585/shorts')
        response.assert_success()

        shorts = response.data
        assert isinstance(shorts, list), "Response should be a list"

        snapshot = snapshot_manager.load_snapshot('edition_shorts_1585')
        assert snapshot is not None, (
            "Snapshot 'edition_shorts_1585' not found"
        )

        expected = snapshot['response']['data']
        _check_shorts_match_snapshot(
            shorts, expected, 'edition_shorts_1585'
        )

    def test_edition_1585_shorts_author_ids(self, api_client):
        """
        Spot-check specific author IDs for edition 1585.

        Short 3202 'Hanna' should be by Sinisalo, Johanna (id 368).
        Short 1805 'Napoleonin vaihtoviikot' should be
        by Elo, Eija (id 3238).
        """
        response = api_client.get('/api/editions/1585/shorts')
        response.assert_success()

        by_id = {int(s['id']): s for s in response.data}

        # 'Hanna' by Sinisalo
        assert 3202 in by_id, "Short 3202 'Hanna' should be present"
        author_ids = _author_ids(by_id[3202])
        assert 368 in author_ids, (
            "Short 3202: expected author id 368 (Sinisalo)"
        )

        # 'Napoleonin vaihtoviikot' by Elo
        assert 1805 in by_id, (
            "Short 1805 'Napoleonin vaihtoviikot' should be present"
        )
        author_ids = _author_ids(by_id[1805])
        assert 3238 in author_ids, (
            "Short 1805: expected author id 3238 (Elo)"
        )


class TestIssueCollection(BaseAPITest):
    """
    Tests for GET /api/issues/{id} for magazine issues.

    Verifies that the 'stories' field in the issue response
    contains the correct items with their authors.

    Issue 92 is Alienisti 1/2017 "Brave New world of #42"
    with 16 stories by various Finnish SF authors.
    """

    def test_issue_92_stories_match_snapshot(
            self, api_client, snapshot_manager):
        """
        GET /api/issues/92 should contain 16 stories.

        Snapshot: issue_92.json (captured from production).

        Checks count, IDs, titles, and author id+name for
        every story in the issue.
        """
        response = api_client.get('/api/issues/92')
        response.assert_success()

        issue = response.data
        assert isinstance(issue, dict), \
            "Response should be a dict"
        assert 'stories' in issue, \
            "Issue response should have 'stories' field"

        actual_stories = issue['stories']
        assert isinstance(actual_stories, list), \
            "'stories' should be a list"

        snapshot = snapshot_manager.load_snapshot('issue_92')
        assert snapshot is not None, (
            "Snapshot 'issue_92' not found — "
            "run update_snapshots.py"
        )

        expected_stories = snapshot['response']['data']['stories']
        _check_shorts_match_snapshot(
            actual_stories, expected_stories, 'issue_92'
        )

    def test_issue_92_stories_have_required_fields(
            self, api_client):
        """
        Each story in GET /api/issues/92 should have
        id, title, and authors fields.
        """
        response = api_client.get('/api/issues/92')
        response.assert_success()

        stories = response.data.get('stories', [])
        assert len(stories) > 0, "Issue 92 should have stories"

        for story in stories:
            for field in ('id', 'title', 'authors'):
                assert field in story, (
                    f"Story {story.get('id')} missing '{field}'"
                )

    def test_issue_92_multi_author_story(self, api_client):
        """
        Story 9132 'Kuvakavalkadi Worldconista' has two authors:
        Kuskelin, Jari (id 3976) and Vainikainen, Jussi (id 3889).
        """
        response = api_client.get('/api/issues/92')
        response.assert_success()

        by_id = {
            int(s['id']): s
            for s in response.data.get('stories', [])
        }
        assert 9132 in by_id, (
            "Story 9132 'Kuvakavalkadi Worldconista' "
            "should be present"
        )
        author_ids = _author_ids(by_id[9132])
        assert 3976 in author_ids, (
            "Story 9132: expected author 3976 (Kuskelin)"
        )
        assert 3889 in author_ids, (
            "Story 9132: expected author 3889 (Vainikainen)"
        )

    def test_issue_92_issue_metadata(self, api_client):
        """
        GET /api/issues/92 should return correct issue metadata.

        Issue 92 is Alienisti no. 1, year 2017.
        Editor is Ranta, Lasse (id 367).
        """
        response = api_client.get('/api/issues/92')
        response.assert_success()

        issue = response.data
        assert issue['id'] == 92, "id should be 92"
        assert issue['year'] == 2017, "year should be 2017"
        assert issue['number'] == 1, "number should be 1"

        editor_ids = {
            int(e['id']) for e in issue.get('editors', [])
        }
        assert 367 in editor_ids, (
            "Issue 92: expected editor 367 (Ranta, Lasse)"
        )
