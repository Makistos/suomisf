"""
Tests for GET /api/search/<pattern>, the main site search endpoint.

Covers the titles-only ('Vain nimet') mode's handling of Person's
alt_name and other_names fields ("Vaihtoehtoinen nimi" / "Muut nimet"):
these hold real names of pseudonyms and other alternate name forms, and
should be searchable even when titles_only restricts matching to
title/name fields, since general full-text search (person.fts) already
includes them and titles_only must not become a stricter no-match
regression against that.
"""

import json


def _results(response):
    # /api/search returns a raw json.dumps(...) body without a JSON
    # mimetype (it predates make_api_response), so the generic
    # APIResponse.json/.data helpers (which rely on Flask's get_json())
    # can't parse it - decode the raw body directly instead.
    return json.loads(response.response.get_data(as_text=True))


class TestSearchTitlesOnlyPersonAltNames:
    """A titles-only search for a person's alt_name/other_names should
    still find them, since these are name fields too."""

    def test_other_names_match_is_found_titles_only(self, api_client):
        # Person 290 "Wolverton, Dave" has other_names "David Farland" -
        # a completely different pen name, not a substring of the primary
        # name, so this can only match via other_names.
        response = api_client.get('/api/search/Farland?titles=1')
        response.assert_success()
        ids = [r['id'] for r in _results(response) if r['type'] == 'person']
        assert 290 in ids

    def test_alt_name_match_is_found_titles_only(self, api_client):
        # alt_name is "Firstname Lastname" derived from name "Lastname,
        # Firstname" - use a person whose alt_name word doesn't already
        # appear in name's own tokenization.
        response = api_client.get('/api/search/Wolverton?titles=1')
        response.assert_success()
        ids = [r['id'] for r in _results(response) if r['type'] == 'person']
        assert 290 in ids

    def test_unrelated_term_is_not_found_titles_only(self, api_client):
        response = api_client.get(
            '/api/search/Xyzzyfoobarnonexistent12345?titles=1')
        response.assert_success()
        assert _results(response) == []


class TestSearchLimit:
    """The number of results: 50 by default (the menu's suggestions),
    more with ?limit= (the search results page), at most 500."""

    # "maailma" matches well over 50 items (works, stories, tags, ...).
    TERM = 'maailma'

    def test_default_is_50(self, api_client):
        response = api_client.get(f'/api/search/{self.TERM}')
        response.assert_success()
        assert len(_results(response)) == 50

    def test_limit_returns_more(self, api_client):
        response = api_client.get(f'/api/search/{self.TERM}?limit=200')
        response.assert_success()
        results = _results(response)
        assert 50 < len(results) <= 200
        # The first 50 are the same ones the default search gives.
        default = _results(api_client.get(f'/api/search/{self.TERM}'))
        assert [(r['type'], r['id']) for r in results[:50]] == \
            [(r['type'], r['id']) for r in default]

    def test_limit_is_capped(self, api_client):
        response = api_client.get(f'/api/search/{self.TERM}?limit=100000')
        response.assert_success()
        assert len(_results(response)) <= 500

    def test_invalid_limit_falls_back_to_default(self, api_client):
        response = api_client.get(f'/api/search/{self.TERM}?limit=abc')
        response.assert_success()
        assert len(_results(response)) == 50
