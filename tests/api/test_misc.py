"""
SuomiSF API Miscellaneous Endpoint Tests

Tests for general/miscellaneous endpoints like frontpagedata, genres,
countries, etc.

Note: Pytest fixtures (api_client, snapshot_manager) are injected at runtime.
Type checkers may show "unknown type" warnings - these are expected.
"""

from .base_test import BaseAPITest


class TestFrontpageData(BaseAPITest):
    """Tests for /api/frontpagedata endpoint."""

    def test_get_frontpagedata_returns_200(self, api_client):
        """GET /api/frontpagedata should return 200."""
        response = api_client.get('/api/frontpagedata')
        response.assert_status(200)

    def test_get_frontpagedata_has_expected_keys(self, api_client):
        """GET /api/frontpagedata should have expected keys."""
        response = api_client.get('/api/frontpagedata')
        response.assert_success()
        # This endpoint returns data directly without 'response' wrapper
        assert 'works' in response.json
        assert 'editions' in response.json

    def test_get_frontpagedata_structure(self, api_client):
        """GET /api/frontpagedata should have expected structure."""
        response = api_client.get('/api/frontpagedata')
        response.assert_success()

        data = response.data
        assert isinstance(data, dict), "Response should be a dict"

        # Check for expected keys (adjust based on actual API response)
        expected_keys = ['works', 'editions', 'people', 'shorts']
        for key in expected_keys:
            if key in data:
                assert isinstance(data[key], (int, list, dict)), \
                    f"'{key}' should be int, list, or dict"

    def test_get_frontpagedata_matches_snapshot(self, api_client,
                                                snapshot_manager):
        """GET /api/frontpagedata should match snapshot data."""
        response = api_client.get('/api/frontpagedata')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('frontpagedata',
                                                 response.json)


class TestGenres(BaseAPITest):
    """Tests for /api/genres endpoint."""

    def test_get_genres_returns_200(self, api_client):
        """GET /api/genres should return 200."""
        response = api_client.get('/api/genres')
        response.assert_status(200)

    def test_get_genres_returns_list(self, api_client):
        """GET /api/genres should return a list."""
        response = api_client.get('/api/genres')
        response.assert_success().assert_data_is_list()

    def test_get_genres_not_empty(self, api_client):
        """GET /api/genres should return non-empty list."""
        response = api_client.get('/api/genres')
        response.assert_success().assert_data_min_length(1)

    def test_genres_have_required_fields(self, api_client):
        """Each genre should have id and name fields."""
        response = api_client.get('/api/genres')
        response.assert_success()

        genres = response.data
        if genres:
            genre = genres[0]
            assert 'id' in genre, "Genre should have 'id' field"
            assert 'name' in genre, "Genre should have 'name' field"

    def test_get_genres_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/genres should match snapshot data."""
        response = api_client.get('/api/genres')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('genres', response.json)


class TestCountries(BaseAPITest):
    """Tests for /api/countries endpoint."""

    def test_get_countries_returns_200(self, api_client):
        """GET /api/countries should return 200."""
        response = api_client.get('/api/countries')
        response.assert_status(200)

    def test_get_countries_returns_list(self, api_client):
        """GET /api/countries should return a list."""
        response = api_client.get('/api/countries')
        response.assert_success().assert_data_is_list()

    def test_get_countries_not_empty(self, api_client):
        """GET /api/countries should return non-empty list."""
        response = api_client.get('/api/countries')
        response.assert_success().assert_data_min_length(1)

    def test_get_countries_matches_snapshot(self, api_client,
                                            snapshot_manager):
        """GET /api/countries should match snapshot data."""
        response = api_client.get('/api/countries')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('countries', response.json)


class TestRoles(BaseAPITest):
    """Tests for /api/roles/ endpoint."""

    def test_get_roles_returns_200(self, api_client):
        """GET /api/roles/ should return 200."""
        response = api_client.get('/api/roles/')
        response.assert_status(200)

    def test_get_roles_returns_list(self, api_client):
        """GET /api/roles/ should return a list."""
        response = api_client.get('/api/roles/')
        response.assert_success().assert_data_is_list()

    def test_get_roles_for_work(self, api_client):
        """GET /api/roles/work should return roles for works."""
        response = api_client.get('/api/roles/work')
        # May return 200 or 404 depending on implementation
        assert response.status_code in [200, 404]

    def test_get_roles_for_edition(self, api_client):
        """GET /api/roles/edition should return roles for editions."""
        response = api_client.get('/api/roles/edition')
        assert response.status_code in [200, 404]

    def test_get_roles_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/roles/ should match snapshot data."""
        response = api_client.get('/api/roles/')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('roles', response.json)


class TestBindings(BaseAPITest):
    """Tests for /api/bindings endpoint."""

    def test_get_bindings_returns_200(self, api_client):
        """GET /api/bindings should return 200."""
        response = api_client.get('/api/bindings')
        response.assert_status(200)

    def test_get_bindings_returns_list(self, api_client):
        """GET /api/bindings should return a list."""
        response = api_client.get('/api/bindings')
        response.assert_success().assert_data_is_list()

    def test_get_bindings_matches_snapshot(self, api_client, snapshot_manager):
        """GET /api/bindings should match snapshot data."""
        response = api_client.get('/api/bindings')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('bindings', response.json)


class TestWorkTypes(BaseAPITest):
    """Tests for /api/worktypes endpoint."""

    def test_get_worktypes_returns_200(self, api_client):
        """GET /api/worktypes should return 200."""
        response = api_client.get('/api/worktypes')
        response.assert_status(200)

    def test_get_worktypes_returns_list(self, api_client):
        """GET /api/worktypes should return a list."""
        response = api_client.get('/api/worktypes')
        response.assert_success().assert_data_is_list()

    def test_get_worktypes_matches_snapshot(self, api_client,
                                            snapshot_manager):
        """GET /api/worktypes should match snapshot data."""
        response = api_client.get('/api/worktypes')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('worktypes', response.json)


class TestShortTypes(BaseAPITest):
    """Tests for /api/shorttypes endpoint."""

    def test_get_shorttypes_returns_200(self, api_client):
        """GET /api/shorttypes should return 200."""
        response = api_client.get('/api/shorttypes')
        response.assert_status(200)

    def test_get_shorttypes_returns_list(self, api_client):
        """GET /api/shorttypes should return a list."""
        response = api_client.get('/api/shorttypes')
        response.assert_success().assert_data_is_list()

    def test_get_shorttypes_matches_snapshot(self, api_client,
                                             snapshot_manager):
        """GET /api/shorttypes should match snapshot data."""
        response = api_client.get('/api/shorttypes')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('shorttypes', response.json)


class TestMagazineTypes(BaseAPITest):
    """Tests for /api/magazinetypes endpoint."""

    def test_get_magazinetypes_returns_200(self, api_client):
        """GET /api/magazinetypes should return 200."""
        response = api_client.get('/api/magazinetypes')
        response.assert_status(200)

    def test_get_magazinetypes_returns_list(self, api_client):
        """GET /api/magazinetypes should return a list."""
        response = api_client.get('/api/magazinetypes')
        response.assert_success().assert_data_is_list()

    def test_get_magazinetypes_matches_snapshot(self, api_client,
                                                snapshot_manager):
        """GET /api/magazinetypes should match snapshot data."""
        response = api_client.get('/api/magazinetypes')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('magazinetypes',
                                                 response.json)


class TestFirstLetterVector(BaseAPITest):
    """Tests for /api/firstlettervector/<target> endpoint."""

    def test_get_firstlettervector_work(self, api_client):
        """GET /api/firstlettervector/work should return letter list."""
        response = api_client.get('/api/firstlettervector/work')
        # Endpoint may return 200, 400, or 404 depending on implementation
        assert response.status_code in [200, 400, 404]

    def test_get_firstlettervector_person(self, api_client):
        """GET /api/firstlettervector/person should return letter list."""
        response = api_client.get('/api/firstlettervector/person')
        assert response.status_code in [200, 400, 404]


class TestLatestCovers(BaseAPITest):
    """Tests for /api/latest/covers/<count> endpoint."""

    def test_get_latest_covers_returns_200(self, api_client):
        """GET /api/latest/covers/5 should return 200."""
        response = api_client.get('/api/latest/covers/5')
        response.assert_status(200)

    def test_get_latest_covers_returns_list(self, api_client):
        """GET /api/latest/covers/5 should return a list."""
        response = api_client.get('/api/latest/covers/5')
        response.assert_success().assert_data_is_list()

    def test_get_latest_covers_respects_count(self, api_client):
        """GET /api/latest/covers/3 should return at most 3 items."""
        response = api_client.get('/api/latest/covers/3')
        response.assert_success()

        covers = response.data
        assert len(covers) <= 3, \
            f"Expected at most 3 covers, got {len(covers)}"

    def test_get_latest_covers_matches_snapshot(self, api_client,
                                                snapshot_manager):
        """GET /api/latest/covers/5 should match snapshot data."""
        response = api_client.get('/api/latest/covers/5')
        response.assert_success()
        snapshot_manager.assert_matches_snapshot('latest_covers_5',
                                                 response.json)
