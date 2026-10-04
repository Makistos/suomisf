"""
Record the pages the price scrapers and award importers fetch, for replay
in tests/api/test_scrapers.py.

Calls the real search/scrape functions and award previews against the live
sites (read-only, through the dev database) and saves every page fetched,
gzipped, under the output folder with an index.json mapping each request to
its file. Re-run it when a site changes its layout, then update the values
pinned in test_scrapers.py.

    PYTHONPATH=. pdm run python tests/scripts/record_scraper_pages.py tests/fixtures/html

sfadb.com was down ("Account Suspended") on 2026-10-04; its two pages in
the fixtures are archived copies from web.archive.org, and
sfadb.com/account-suspended.gz is the suspension page itself.
"""
import gzip
import hashlib
import json
import os
import sys
from urllib.parse import urlparse
import requests

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
INDEX = {}
real_get = requests.get

def key_of(url, params=None):
    return url if not params else url + '?' + json.dumps(params, sort_keys=True, ensure_ascii=False,
        default=lambda v: v.decode('latin-1') if isinstance(v, bytes) else str(v))

def recording_get(url, *args, params=None, **kwargs):
    resp = real_get(url, *args, params=params, **kwargs)
    key = key_of(url, params)
    host = urlparse(url).netloc.replace('www.', '')
    name = f"{host}/{hashlib.sha1(key.encode()).hexdigest()[:12]}.gz"
    os.makedirs(os.path.join(OUT, host), exist_ok=True)
    with gzip.open(os.path.join(OUT, name), 'wb') as fh:
        fh.write(resp.content)
    INDEX[key] = {'file': name, 'status': resp.status_code, 'url': resp.url,
                  'encoding': resp.encoding,
                  'content_type': resp.headers.get('Content-Type', '')}
    print(f'  {resp.status_code} {len(resp.content):>8} B  {key[:110]}')
    return resp

requests.get = recording_get
from app import app  # noqa: E402
import app.impl_pricing as pricing  # noqa: E402
import app.impl_award_import as awards  # noqa: E402
pricing.requests.get = recording_get
awards.requests.get = recording_get

QUERY = 'Asimov Säätiö'
first_urls = {}
with app.app_context():
    for name, fn in [('antikvaari', pricing.antikvaari_search),
                     ('antikvariaatti', pricing.antikvariaatti_search),
                     ('lukuhetki', pricing.lukuhetki_search),
                     ('kampinkirjakauppa', pricing.kampinkirjakauppa_search),
                     ('antikka', getattr(pricing, 'antikka_search', None))]:
        if fn is None:
            continue
        print(name)
        rows = []
        for q in (QUERY, 'Asimov'):
            result = fn(q)
            rows = result.response if isinstance(result.response, list) else []
            if rows:
                break
        print(f'  -> {result.status}, {len(rows)} results')
        url = next((r.get('url') for r in rows if isinstance(r, dict) and r.get('url')), None)
        if url:
            first_urls[name] = url
    for name, url in first_urls.items():
        print('scrape', name, url)
        r = pricing.scrape_price_from_url(url)
        print('  ->', r.status, str(r.response)[:150])
    for award_id in (11, 1, 13):
        print('award', award_id)
        r = awards.preview_import(award_id)
        n = len(r.response.get('entries', [])) if isinstance(r.response, dict) else r.response
        print('  ->', r.status, n)

with open(os.path.join(OUT, 'index.json'), 'w') as fh:
    json.dump({'query': QUERY, 'product_urls': first_urls, 'pages': INDEX}, fh,
              indent=1, ensure_ascii=False, sort_keys=True)
