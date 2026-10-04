"""
Price scrapers and award importers against recorded pages (coverage plan
step B3).

The pages in tests/fixtures/html were fetched once from the live sites by
tests/scripts/record_scraper_pages.py. Here requests.get is replaced by a
replay of those files, so the tests never use the network and an unknown
URL fails the test instead of reaching the internet. When a site changes
its layout, re-record, and the pinned values below show exactly which
fields the change broke.
"""
import gzip
import json
import os

import pytest
import requests

import app.impl_award_import as award_import
import app.impl_pricing as pricing
from app.orm_decl import Awarded
from app.route_helpers import new_session

FIXTURES = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'html')
INDEX = json.load(open(os.path.join(FIXTURES, 'index.json'), encoding='utf-8'))
QUERY = INDEX['query']
PRODUCT_URLS = INDEX['product_urls']


def _key(url, params=None):
    if not params:
        return url
    return url + '?' + json.dumps(
        params, sort_keys=True, ensure_ascii=False,
        default=lambda v: v.decode('latin-1') if isinstance(v, bytes) else str(v))


class RecordedResponse:
    """The parts of requests.Response the scrapers use."""

    def __init__(self, entry, content=None):
        if content is None:
            with gzip.open(os.path.join(FIXTURES, entry['file'])) as fh:
                content = fh.read()
        self.content = content
        self.status_code = entry['status']
        self.url = entry['url']
        self.encoding = entry.get('encoding') or 'utf-8'
        self.headers = {'Content-Type': entry.get('content_type', '')}
        self.ok = self.status_code < 400

    @property
    def text(self):
        return self.content.decode(self.encoding, errors='replace')

    def json(self):
        return json.loads(self.content)

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f'{self.status_code} for {self.url}')


@pytest.fixture
def recorded_web(monkeypatch):
    """Replay recorded pages; `overrides` maps a URL to replacement bytes."""
    overrides = {}

    def fake_get(url, *args, params=None, **kwargs):
        key = _key(url, params)
        entry = INDEX['pages'].get(key)
        if entry is None:
            raise AssertionError(f'no recorded page for {key}')
        return RecordedResponse(entry, overrides.get(url))

    monkeypatch.setattr(pricing.requests, 'get', fake_get)
    monkeypatch.setattr(award_import.requests, 'get', fake_get)
    return overrides


# ---------------------------------------------------------------------------
# Price sources
# ---------------------------------------------------------------------------

SEARCHES = [
    ('antikvaari', pricing.antikvaari_search, QUERY),
    ('antikvariaatti', pricing.antikvariaatti_search, QUERY),
    ('antikka', pricing.antikka_search, QUERY),
    # These two find nothing for the full query; recorded with 'Asimov'.
    ('kampinkirjakauppa', pricing.kampinkirjakauppa_search, 'Asimov'),
    ('lukuhetki', pricing.lukuhetki_search, 'Asimov'),
]


@pytest.mark.parametrize('name,search,query', SEARCHES, ids=[s[0] for s in SEARCHES])
def test_search_returns_products(recorded_web, name, search, query):
    result = search(query)
    assert result.status == 200
    rows = result.response
    assert rows, f'{name}: no results'
    for row in rows:
        assert row['url'].startswith('http'), row
        assert row.get('title'), row
    assert PRODUCT_URLS[name] in [row['url'] for row in rows]


@pytest.mark.parametrize('search', [pricing.kampinkirjakauppa_search,
                                    pricing.lukuhetki_search])
def test_search_without_results_is_empty_list(recorded_web, search):
    result = search(QUERY)
    assert result.status == 200
    assert result.response == []


# What each shop's product page parses to. last_updated is left out: where
# the page shows no date it is the day of the scrape.
SCRAPED = {
    'antikka': {
        'book_id': 'SCI-260207153549-657', 'price': 140.0, 'condition': 'K3',
        'year': 1976, 'version': 1, 'binding': 3, 'title': 'Säätiö',
        'author': 'Asimov Isaac', 'language': 'Suomi', 'seller': 'Ilkan Kirja Ay',
        'seller_url': 'https://antikka.net/ilkan-kirja/',
        'source_id': 3, 'source_name': 'Antikka'},
    'antikvaari': {
        'book_id': '002c18c0df7e793858e64b44', 'price': 45, 'condition': 'K4',
        'year': 1986, 'version': 2, 'binding': 2, 'title': 'Säätiö',
        'author': 'Asimov Isaac', 'language': 'suomi',
        'seller': 'Divari & Antikvariaatti Kummisetä', 'seller_url': None,
        'source_id': 1, 'source_name': 'Antikvaari'},
    'antikvariaatti': {
        'book_id': '2518465', 'price': 150.0, 'condition': 'K3', 'year': 1991,
        'version': 1, 'binding': None, 'title': 'Säätiö ja Maa',
        'author': 'Isaac Asimov', 'language': 'Suomi', 'seller': 'Finlandia Kirja Oy',
        'seller_url': 'https://www.antikvariaatti.net/kauppiaat/finlandia-kirja-oy',
        'source_id': 2, 'source_name': 'Antikvariaatti'},
    'kampinkirjakauppa': {
        'book_id': '40201', 'price': 35.0, 'condition': 'K4', 'year': 1994,
        'version': None, 'binding': 2, 'title': 'Yö saapuu',
        'author': 'Asimov Isaac & Silverberg, Robert', 'language': None,
        'seller': 'Kampin kirjakauppa', 'seller_url': 'https://www.kampinkirjakauppa.fi/',
        'source_id': 7, 'source_name': 'Kampin kirjakauppa'},
    'lukuhetki': {
        'book_id': '664', 'price': 8.0, 'condition': None, 'year': 1990,
        'version': 1, 'binding': 3, 'title': 'Norby, seonnut robotti',
        'author': 'Asimov Janet & Isaac', 'language': 'Suomi',
        'seller': 'Antikvariaatti Lukuhetki', 'seller_url': 'https://www.lukuhetki.fi/',
        'source_id': 6, 'source_name': 'Lukuhetki'},
}


@pytest.mark.parametrize('name', sorted(SCRAPED))
def test_scrape_product_page(recorded_web, name):
    result = pricing.scrape_price_from_url(PRODUCT_URLS[name])
    assert result.status == 200, result.response
    row = dict(result.response)
    assert row.pop('last_updated')
    assert row == SCRAPED[name]


def test_scrape_unknown_site_is_400(recorded_web):
    result = pricing.scrape_price_from_url('https://example.invalid/kirja/1')
    assert result.status == 400


# ---------------------------------------------------------------------------
# Award import
# ---------------------------------------------------------------------------

AWARDS = {'philip_k_dick': 11, 'grand_master': 1, 'atorox': 13}
AWARD_WINNERS = {'philip_k_dick': 47, 'grand_master': 42, 'atorox': 42}


@pytest.mark.parametrize('name', sorted(AWARDS))
def test_award_preview(recorded_web, app, name):
    result = award_import.preview_import(AWARDS[name])
    assert result.status == 200, result.response
    body = result.response
    assert body['errors'] == []
    # How many winners each recorded page lists. The new/awarded split
    # depends on the database, so only the total is pinned.
    assert len(body['entries']) == AWARD_WINNERS[name]
    assert sum(body['counts'].values()) == len(body['entries'])


def test_award_preview_reports_empty_source(recorded_web, app):
    """sfadb.com served an 'Account Suspended' page in 2026-10; the preview
    must say the source gave nothing rather than show an empty list."""
    url = 'https://www.sfadb.com/SFWA_Grand_Master_Award'
    with gzip.open(os.path.join(FIXTURES, 'sfadb.com', 'account-suspended.gz')) as fh:
        recorded_web[url] = fh.read()
    body = award_import.preview_import(AWARDS['grand_master']).response
    assert body['entries'] == []
    assert len(body['errors']) == 1 and url in body['errors'][0]


def test_award_save_import_creates_and_skips(app):
    award_id = AWARDS['atorox']
    winner = {'match_type': 'work', 'target_id': 1, 'year': 2099, 'category_id': None}
    try:
        result = award_import.save_import(award_id, {'data': {'winners': [
            winner, dict(winner), {'match_type': 'bogus', 'target_id': 1}]}})
        assert result.status == 200, result.response
        # the duplicate and the unknown match type are skipped
        assert result.response == {'created': 1, 'skipped': 2}
        session = new_session()
        try:
            rows = session.query(Awarded).filter_by(award_id=award_id, work_id=1,
                                                    year=2099).count()
        finally:
            session.close()
        assert rows == 1
    finally:
        session = new_session()
        try:
            session.query(Awarded).filter_by(award_id=award_id, work_id=1,
                                             year=2099).delete()
            session.commit()
        finally:
            session.close()
