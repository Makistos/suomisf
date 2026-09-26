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
