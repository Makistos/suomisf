"""
SuomiSF API Statistics Endpoint Tests

Tests for /api/stats/* endpoints with snapshot comparison.
"""

import pytest

from .base_test import BaseAPITest


class TestGenreCounts(BaseAPITest):
    """Tests for /api/stats/genrecounts endpoint."""

    def test_get_genrecounts_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/genrecounts should return 200.

        Also checks:
        - GET /api/stats/genrecounts should return genre data.
        - GET /api/stats/genrecounts should match snapshot data.
        """
        response = api_client.get('/api/stats/genrecounts')
        response.assert_status(200)
        response.assert_success()
        # Returns data directly without 'response' wrapper
        assert response.json is not None
        assert len(response.json) > 0
        snapshot_manager.assert_matches_snapshot('stats_genrecounts',
                                                 response.json)


class TestPersonCounts(BaseAPITest):
    """Tests for /api/stats/personcounts endpoint."""

    def test_get_personcounts_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/personcounts should return 200.

        Also checks:
        - GET /api/stats/personcounts should return a list.
        - GET /api/stats/personcounts should match snapshot data.
        """
        response = api_client.get('/api/stats/personcounts')
        response.assert_status(200)
        response.assert_success().assert_data_is_list()
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_personcounts',
                                                 response.json)


class TestStoryPersonCounts(BaseAPITest):
    """Tests for /api/stats/storypersoncounts endpoint."""

    def test_get_storypersoncounts_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/storypersoncounts should return 200.

        Also checks:
        - GET /api/stats/storypersoncounts should match snapshot data.
        """
        response = api_client.get('/api/stats/storypersoncounts')
        response.assert_status(200)
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_storypersoncounts',
                                                 response.json)


class TestPublisherCounts(BaseAPITest):
    """Tests for /api/stats/publishercounts endpoint."""

    def test_get_publishercounts_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/publishercounts should return 200.

        Also checks:
        - GET /api/stats/publishercounts should return a list.
        - GET /api/stats/publishercounts should match snapshot data.
        """
        response = api_client.get('/api/stats/publishercounts')
        response.assert_status(200)
        response.assert_success().assert_data_is_list()
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_publishercounts',
                                                 response.json)


class TestWorksByYear(BaseAPITest):
    """Tests for /api/stats/worksbyyear endpoint."""

    def test_get_worksbyyear_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/worksbyyear should return 200.

        Also checks:
        - GET /api/stats/worksbyyear should return a list.
        - Each entry should have year and count fields.
        - GET /api/stats/worksbyyear should match snapshot data.
        """
        response = api_client.get('/api/stats/worksbyyear')
        response.assert_status(200)
        response.assert_success().assert_data_is_list()
        response.assert_success()

        data = response.data
        if data and len(data) > 0:
            entry = data[0]
            # Check for common year statistics fields
            assert 'year' in entry or 'count' in entry or \
                isinstance(entry, (int, list)), \
                f"Unexpected entry format: {entry}"
        snapshot_manager.assert_matches_snapshot('stats_worksbyyear',
                                                 response.json)


class TestPublishersByYear(BaseAPITest):
    """Tests for /api/stats/publishersbyyear endpoint."""

    def test_get_publishersbyyear(self, api_client):
        """GET /api/stats/publishersbyyear returns per-publisher year counts.

        Also checks:
        - Each (year, publisher) pair appears once.
        - Drilling down with publisher_first=1 lists as many works as the
          count says.
        """
        response = api_client.get('/api/stats/publishersbyyear')
        response.assert_status(200)
        data = response.json
        assert isinstance(data, list)
        if not data:
            return
        assert set(data[0]) == {'year', 'count', 'publisher_id',
                                'publisher_name'}
        pairs = [(d['year'], d['publisher_id']) for d in data]
        assert len(pairs) == len(set(pairs))

        row = max(data, key=lambda d: d['count'])
        works = api_client.get(
            f"/api/stats/filterworks?publisher={row['publisher_id']}"
            f"&edition_year_min={row['year']}&edition_year_max={row['year']}"
            "&publisher_first=1")
        works.assert_status(200)
        assert len(works.json) == row['count']

    def test_get_publishersbyyear_unknown_genre(self, api_client):
        """GET /api/stats/publishersbyyear with unknown genre returns 400."""
        response = api_client.get('/api/stats/publishersbyyear?genre=XXX')
        response.assert_status(400)


class TestOrigWorksByYear(BaseAPITest):
    """Tests for /api/stats/origworksbyyear endpoint."""

    def test_get_origworksbyyear_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/origworksbyyear should return 200.

        Also checks:
        - GET /api/stats/origworksbyyear should match snapshot data.
        """
        response = api_client.get('/api/stats/origworksbyyear')
        response.assert_status(200)
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_origworksbyyear',
                                                 response.json)


class TestStoriesByYear(BaseAPITest):
    """Tests for /api/stats/storiesbyyear endpoint."""

    def test_get_storiesbyyear_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/storiesbyyear should return 200.

        Also checks:
        - GET /api/stats/storiesbyyear should match snapshot data.
        """
        response = api_client.get('/api/stats/storiesbyyear')
        response.assert_status(200)
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_storiesbyyear',
                                                 response.json)


class TestIssuesPerYear(BaseAPITest):
    """Tests for /api/stats/issuesperyear endpoint."""

    def test_get_issuesperyear_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/issuesperyear should return 200.

        Also checks:
        - GET /api/stats/issuesperyear should match snapshot data.
        """
        response = api_client.get('/api/stats/issuesperyear')
        response.assert_status(200)
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_issuesperyear',
                                                 response.json)


class TestNationalityCounts(BaseAPITest):
    """Tests for /api/stats/nationalitycounts endpoint."""

    def test_get_nationalitycounts_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/nationalitycounts should return 200.

        Also checks:
        - GET /api/stats/nationalitycounts should return a list.
        - GET /api/stats/nationalitycounts should match snapshot data.
        """
        response = api_client.get('/api/stats/nationalitycounts')
        response.assert_status(200)
        response.assert_success().assert_data_is_list()
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('stats_nationalitycounts',
                                                 response.json)


class TestStoryNationalityCounts(BaseAPITest):
    """Tests for /api/stats/storynationalitycounts endpoint."""

    def test_get_storynationalitycounts_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/storynationalitycounts should return 200.

        Also checks:
        - GET /api/stats/storynationalitycounts should match snapshot data.
        """
        response = api_client.get('/api/stats/storynationalitycounts')
        response.assert_status(200)
        response.assert_success()
        snapshot_manager.assert_matches_snapshot(
            'stats_storynationalitycounts', response.json)


class TestFilterStories(BaseAPITest):
    """Tests for GET /api/stats/filterstories endpoint.

    This endpoint filters short stories by story type,
    language, and publication year range.
    """

    @pytest.mark.parametrize('path', [
        '/api/stats/filterstories', '/api/stats/filterstories?role=1',
        '/api/stats/filterworks', '/api/stats/filterworks?role=1'])
    def test_filter_without_filters_is_400(self, api_client, path):
        """Unfiltered, these returned every story (~100 MB, 100 s) or every
        work (~22 MB); role alone only refines a nationality filter."""
        response = api_client.get(path)
        assert response.status_code == 400

    def test_filterstories_by_novelli(self, api_client):
        """GET filterstories?storytype=1 returns novellit.
        """
        response = api_client.get(
            '/api/stats/filterstories?storytype=1'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) > 0, (
            "Should return novelli stories"
        )
        for short in data:
            if 'type' in short and short['type']:
                assert short['type']['id'] == 1, (
                    f"Short {short['id']} type "
                    f"{short['type']['id']} != 1"
                )

    def test_filterstories_by_runo(self, api_client):
        """GET filterstories?storytype=4 returns runot."""
        response = api_client.get(
            '/api/stats/filterstories?storytype=4'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) > 0, (
            "Should return runo stories"
        )
        for short in data:
            if 'type' in short and short['type']:
                assert short['type']['id'] == 4, (
                    f"Short {short['id']} type "
                    f"{short['type']['id']} != 4"
                )

    def test_filterstories_by_artikkeli(
        self, api_client
    ):
        """GET filterstories?storytype=7 returns articles.
        """
        response = api_client.get(
            '/api/stats/filterstories?storytype=7'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) > 0, (
            "Should return artikkeli stories"
        )
        for short in data:
            if 'type' in short and short['type']:
                assert short['type']['id'] == 7

    def test_filterstories_nonexistent_type(
        self, api_client
    ):
        """GET filterstories?storytype=999 returns empty.
        """
        response = api_client.get(
            '/api/stats/filterstories?storytype=999'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) == 0

    def test_filterstories_combined_type_and_year(
        self, api_client
    ):
        """GET filterstories with type and year range."""
        response = api_client.get(
            '/api/stats/filterstories'
            '?storytype=1'
            '&pubyear_min=2000'
            '&pubyear_max=2020'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        for short in data:
            if 'type' in short and short['type']:
                assert short['type']['id'] == 1
            if 'pubyear' in short and short['pubyear']:
                assert 2000 <= short['pubyear'] <= 2020


class TestStoryPersonCountsByType(BaseAPITest):
    """Tests for storypersoncounts with storytype filter.

    GET /api/stats/storypersoncounts?storytype=N filters
    person counts to only include the specified type.
    """

    def test_storypersoncounts_by_novelli(
        self, api_client
    ):
        """GET storypersoncounts?storytype=1."""
        response = api_client.get(
            '/api/stats/storypersoncounts?storytype=1'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) > 0, (
            "Should have person counts for novellit"
        )

    def test_storypersoncounts_by_artikkeli(
        self, api_client
    ):
        """GET storypersoncounts?storytype=7."""
        response = api_client.get(
            '/api/stats/storypersoncounts?storytype=7'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) > 0, (
            "Should have person counts for artikkelit"
        )

    def test_storypersoncounts_nonexistent_type(
        self, api_client
    ):
        """GET storypersoncounts?storytype=999."""
        response = api_client.get(
            '/api/stats/storypersoncounts?storytype=999'
        )
        assert response.status_code == 400


class TestStoriesByYearTypes(BaseAPITest):
    """Tests for storiesbyyear story type grouping.

    GET /api/stats/storiesbyyear returns stories grouped
    by year, story type, and language. Verify the type
    fields are present and correct.
    """

    def test_storiesbyyear_multiple_types(self, api_client):
        """Entries should have storytype_id and name.

        Also checks:
        - Response should include multiple story types.
        - All storytype_name values should be valid.
        """
        response = api_client.get(
            '/api/stats/storiesbyyear'
        )
        response.assert_success()

        data = response.data
        assert isinstance(data, list)
        assert len(data) > 0

        # Check first entry has type fields
        entry = data[0]
        assert 'storytype_id' in entry, (
            "Missing storytype_id"
        )
        assert 'storytype_name' in entry, (
            "Missing storytype_name"
        )

        type_ids = {
            e['storytype_id'] for e in data
            if e.get('storytype_id') is not None
        }
        assert len(type_ids) >= 3, (
            f"Expected at least 3 story types, "
            f"got {len(type_ids)}: {type_ids}"
        )

        valid_names = {
            'Novelli', 'Pitkä novelli',
            'Pienoisromaani', 'Runo', 'Raapale',
            'Filk-laulu', 'Artikkeli', 'Esipuhe',
            'Jälkisanat',
        }
        for entry in response.data:
            name = entry.get('storytype_name')
            if name is not None:
                assert name in valid_names, (
                    f"Unknown type name: '{name}'"
                )


class TestFilterWorks(BaseAPITest):
    """Tests for /api/stats/filterworks endpoint (POST)."""

    def test_post_filterworks_empty_filter(self, api_client):
        """POST /api/stats/filterworks with empty filter."""
        response = api_client.post('/api/stats/filterworks', data={})
        assert response.status_code == 405


class TestMiscStats(BaseAPITest):
    """Tests for /api/stats/misc endpoint."""

    def test_get_misc_stats_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/stats/misc should return 200.

        Also checks:
        - GET /api/stats/misc should return statistics data.
        - GET /api/stats/misc should match snapshot data.
        """
        response = api_client.get('/api/stats/misc')
        response.assert_status(200)
        response.assert_success()
        # Returns data directly without 'response' wrapper
        assert response.json is not None
        assert 'total_works' in response.json or \
            'total_editions' in response.json
        snapshot_manager.assert_matches_snapshot('stats_misc', response.json)


class TestStatsPageParameters(BaseAPITest):
    """Parameters added for the redesigned statistics page."""

    def test_misc_has_overview_counts(self, api_client):
        """GET /api/stats/misc includes the counts for the overview tiles."""
        response = api_client.get('/api/stats/misc')
        response.assert_status(200)
        for key in ('total_stories', 'total_people', 'total_publishers',
                    'total_magazines', 'total_issues', 'total_awarded'):
            assert isinstance(response.json[key], int), key

    def test_issuesperyear_by_magazine(self, api_client):
        """GET /api/stats/issuesperyear?by=magazine splits years by magazine.

        Also checks:
        - Rows sum to the yearly totals (years with a known year).
        """
        response = api_client.get('/api/stats/issuesperyear?by=magazine')
        response.assert_status(200)
        rows = response.json
        assert isinstance(rows, list)
        if not rows:
            return
        assert set(rows[0]) == {'year', 'count', 'magazine_id',
                                'magazine_name'}
        totals = api_client.get('/api/stats/issuesperyear').json
        by_year = {r['year']: r['count'] for r in totals if r['year']}
        summed: dict = {}
        for r in rows:
            summed[r['year']] = summed.get(r['year'], 0) + r['count']
        assert summed == by_year

    def test_origworksbyyear_genre(self, api_client):
        """GET /api/stats/origworksbyyear?genre=SF counts fewer works."""
        all_works = api_client.get('/api/stats/origworksbyyear').json
        sf = api_client.get('/api/stats/origworksbyyear?genre=SF')
        sf.assert_status(200)
        assert sum(r['count'] for r in sf.json) <= \
            sum(r['count'] for r in all_works)

    def test_origworksbyyear_unknown_genre(self, api_client):
        """GET /api/stats/origworksbyyear with unknown genre returns 400."""
        response = api_client.get('/api/stats/origworksbyyear?genre=XXX')
        response.assert_status(400)


class TestStatsEditionsAndWorks(BaseAPITest):
    """Edition and work statistics (stats page, phase 2)."""

    ENDPOINTS = ('translationlag', 'editiontypes', 'editionsperwork',
                 'retranslations', 'bindingsbyyear', 'pagesbyyear',
                 'pagehistogram', 'sizehistogram')

    @pytest.mark.parametrize('name', ENDPOINTS)
    def test_unknown_genre(self, api_client, name):
        """Every endpoint returns 400 for an unknown genre."""
        response = api_client.get(f'/api/stats/{name}?genre=XXX')
        response.assert_status(400)

    @pytest.mark.parametrize('name', ENDPOINTS)
    def test_genre_filter(self, api_client, name):
        """Every endpoint accepts a known genre."""
        response = api_client.get(f'/api/stats/{name}?genre=SF')
        response.assert_status(200)

    def test_translationlag(self, api_client):
        """Histogram sums to the total; quartiles are ordered.

        Also checks:
        - start/end narrow the works counted.
        """
        data = api_client.get('/api/stats/translationlag').json
        assert sum(h['count'] for h in data['histogram']) == data['total']
        assert [h['lag'] for h in data['histogram']] == \
            list(range(len(data['histogram'])))
        assert sum(d['count'] for d in data['by_decade']) == data['total']
        for d in data['by_decade']:
            assert d['q1'] <= d['median'] <= d['q3']
        narrow = api_client.get(
            '/api/stats/translationlag?start=2000&end=2009').json
        assert narrow['total'] <= data['total']
        assert all(d['decade'] == 2000 for d in narrow['by_decade'])

    def test_editiontypes_sum_to_editions(self, api_client):
        """First editions + new versions + reprints = editions with a year."""
        rows = api_client.get('/api/stats/editiontypes').json
        bindings = api_client.get('/api/stats/bindingsbyyear').json
        total = sum(r['first'] + r['new_version'] + r['reprint']
                    for r in rows)
        assert total == sum(b['count'] for b in bindings)

    def test_editionsperwork(self, api_client):
        """Histogram is sorted; top list is ordered by edition count."""
        data = api_client.get('/api/stats/editionsperwork').json
        sizes = [h['editions'] for h in data['histogram']]
        assert sizes == sorted(sizes)
        counts = [t['editions'] for t in data['top']]
        assert counts == sorted(counts, reverse=True)
        assert len(data['top']) <= 20

    def test_retranslations(self, api_client):
        """Every listed work has 2+ translations in year order."""
        data = api_client.get('/api/stats/retranslations').json
        assert data['retranslated_works'] == len(data['works'])
        assert data['retranslated_works'] <= data['translated_works']
        for work in data['works']:
            years = [t['year'] for t in work['translations']]
            assert len(years) >= 2
            assert years == sorted(years)
        assert sum(r['count'] for r in data['by_year']) == \
            sum(len(w['translations']) - 1 for w in data['works'])

    def test_pagesbyyear_by_decade(self, api_client):
        """Decade rows start on a decade and match yearly counts."""
        yearly = api_client.get('/api/stats/pagesbyyear').json
        decades = api_client.get('/api/stats/pagesbyyear?by=decade').json
        assert all(r['year'] % 10 == 0 for r in decades)
        assert sum(r['count'] for r in decades) == \
            sum(r['count'] for r in yearly)
        for r in decades:
            assert r['q1'] <= r['median'] <= r['q3']

    def test_page_and_size_histograms(self, api_client):
        """Buckets are contiguous; thickest list is in page order."""
        pages = api_client.get('/api/stats/pagehistogram').json
        starts = [h['pages'] for h in pages['histogram']]
        assert starts == list(range(0, len(starts) * pages['bucket'],
                                    pages['bucket']))
        thick = [t['pages'] for t in pages['thickest']]
        assert thick == sorted(thick, reverse=True)
        sizes = [h['size'] for h in
                 api_client.get('/api/stats/sizehistogram').json]
        if sizes:
            assert sizes == list(range(sizes[0], sizes[-1] + 1))

    def test_histograms_year_range(self, api_client):
        """start/end narrow the page and size histograms."""
        def total(path):
            data = api_client.get(path).json
            rows = data['histogram'] if isinstance(data, dict) else data
            return sum(r['count'] for r in rows)
        for name in ('pagehistogram', 'sizehistogram'):
            assert total(f'/api/stats/{name}?start=1950&end=1959') <= \
                total(f'/api/stats/{name}')
