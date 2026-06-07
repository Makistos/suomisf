"""Antikvaari pricing scraper and match quality calculation."""
from typing import Any, Dict, List, Optional
import datetime
import json
import re

import requests
from bs4 import BeautifulSoup

from app.impl import ResponseType
from app.orm_decl import AntikvaariPrice, AntikvaariWorkProduct, Edition, Work
from app.route_helpers import new_session
from app.types import HttpResponseCode

ANTIKVAARI_BASE = 'https://www.antikvaari.fi'
_SEARCH_URL = f'{ANTIKVAARI_BASE}/api/products/search-v2'
_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_version(painos: str) -> Optional[int]:
    """Parse edition number from '2', '3. painos', etc. Returns None if unparseable."""
    if not painos:
        return None
    painos = painos.strip()
    try:
        return int(painos)
    except ValueError:
        m = re.match(r'^(\d+)', painos)
        return int(m.group(1)) if m else None


def _parse_condition(kunto: str) -> str:
    """Normalise condition string: strip trailing +/-, map 'Uusi' to 'K5'."""
    kunto = (kunto or '').strip()
    if kunto.lower() == 'uusi':
        return 'K5'
    return re.sub(r'[+-]$', '', kunto)


def _condition_int(condition: str) -> Optional[int]:
    """Return the numeric part of a condition string: 'K3' -> 3."""
    m = re.match(r'^K(\d)', condition or '')
    return int(m.group(1)) if m else None


def _binding_category(sidonta: str) -> Optional[int]:
    """Map Antikvaari binding string to bindingtype ID: 2=Nidottu, 3=Sidottu, None=unknown."""
    if not sidonta:
        return None
    low = sidonta.lower()
    if 'sidottu' in low:
        return 3
    if 'nidottu' in low or 'pokkari' in low:
        return 2
    return None


def _fetch_next_data(url: str) -> Optional[Dict[str, Any]]:
    """Fetch a Next.js page and return pageProps from __NEXT_DATA__, or None on failure."""
    try:
        resp = requests.get(url, headers={'User-Agent': _UA}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    soup = BeautifulSoup(resp.text, 'html.parser')
    script = soup.find('script', id='__NEXT_DATA__')
    if not script or not script.string:
        return None
    try:
        return json.loads(script.string)['props']['pageProps']
    except (json.JSONDecodeError, KeyError):
        return None


def _edition_match_level(
    edition: Edition,
    product_year: Optional[int],
    product_version: Optional[int],
    product_binding: Optional[int],
) -> str:
    """Return 'same', 'close', or 'not_close' comparing our edition to Antikvaari product metadata."""
    # Version: must match exactly when both are known
    if product_version is not None and edition.version is not None:
        if product_version != edition.version:
            return 'not_close'

    # Binding: must match when both sides have a known binding (>1 means not 'Ei tietoa')
    if product_binding is not None and product_binding > 1 and edition.binding_id and edition.binding_id > 1:
        if product_binding != edition.binding_id:
            return 'not_close'

    # Year
    if product_year is not None and edition.pubyear:
        diff = abs(product_year - edition.pubyear)
        if diff > 10:
            return 'not_close'
        if diff > 0:
            return 'close'

    return 'same'


# ---------------------------------------------------------------------------
# Public: search
# ---------------------------------------------------------------------------

def antikvaari_search(q: str, isbn: str = '') -> ResponseType:
    """Proxy Antikvaari product search. Returns all matching products."""
    params = {
        'q': q, 'added': '', 'author': '', 'binding': '', 'campaign': 'false',
        'campaign_id': '', 'category_ids': '', 'category_main_id': '', 'isbn': isbn,
        'language_codes': '', 'new_only': '0', 'price': '0:500', 'publisher': '',
        'title': '', 'vendor_ids': '', 'year': '', 'year_min': '', 'year_max': '',
        'sort': '', 'page': '1',
    }
    try:
        resp = requests.get(_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        docs = resp.json().get('data', {}).get('docs', [])
    except (requests.RequestException, ValueError) as exc:
        return ResponseType(f'Antikvaari search failed: {exc}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR)

    products = [
        {
            'product_id': d['_id'],
            'title': d.get('title', ''),
            'author': d.get('author', ''),
            'year': d.get('year', ''),
            'binding': d.get('binding', ''),
            'url': ANTIKVAARI_BASE + d.get('path', ''),
            'image': d.get('image', ''),
            'available_count': d.get('availableCount', 0),
        }
        for d in docs
    ]
    return ResponseType(products, HttpResponseCode.OK)


# ---------------------------------------------------------------------------
# Public: work-product mapping
# ---------------------------------------------------------------------------

def work_products_get(work_id: int) -> ResponseType:
    """Return Antikvaari product IDs linked to a work."""
    session = new_session()
    try:
        rows = (session.query(AntikvaariWorkProduct)
                .filter(AntikvaariWorkProduct.work_id == work_id)
                .all())
        return ResponseType(
            [{'id': r.id, 'antikvaari_product_id': r.antikvaari_product_id,
              'added': r.added.isoformat() if r.added else None,
              'url': r.url}
             for r in rows],
            HttpResponseCode.OK,
        )
    finally:
        session.close()


def work_products_save(work_id: int, products: List[Dict[str, Any]]) -> ResponseType:
    """Link Antikvaari products (id+url) to a work. Existing mappings are preserved."""
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        if not work:
            return ResponseType('Work not found', HttpResponseCode.NOT_FOUND)

        existing = {
            r.antikvaari_product_id
            for r in session.query(AntikvaariWorkProduct)
            .filter(AntikvaariWorkProduct.work_id == work_id)
            .all()
        }
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        added = 0
        for item in products:
            pid = item.get('product_id', '') if isinstance(item, dict) else item
            url = item.get('url') if isinstance(item, dict) else None
            if pid and pid not in existing:
                session.add(AntikvaariWorkProduct(
                    work_id=work_id,
                    antikvaari_product_id=pid,
                    added=now,
                    url=url,
                ))
                added += 1
        session.commit()
        return ResponseType({'added': added}, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Save failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


def antikvaari_prices_save_all(_work_id: int, rows: List[Dict[str, Any]]) -> ResponseType:
    """Save all fetched price rows for a work, grouped by edition."""
    by_edition: Dict[int, List[Dict[str, Any]]] = {}
    for row in rows:
        eid = row.get('edition_id')
        if eid is not None:
            by_edition.setdefault(int(eid), []).append(row)

    total_saved = 0
    total_skipped = 0
    for edition_id, edition_rows in by_edition.items():
        result = antikvaari_prices_save(edition_id, edition_rows)
        if result.status == HttpResponseCode.OK and isinstance(result.response, dict):
            total_saved += result.response.get('saved', 0)
            total_skipped += result.response.get('skipped', 0)

    return ResponseType({'saved': total_saved, 'skipped': total_skipped}, HttpResponseCode.OK)


# ---------------------------------------------------------------------------
# Public: fetch product pages
# ---------------------------------------------------------------------------

def antikvaari_fetch_products(
    product_urls: List[str],
    work_id: int,
    target_condition: Optional[str] = None,
) -> ResponseType:
    """Scrape Antikvaari product pages and return price rows with match quality.

    All physical book copies found across all product pages are returned. The
    best-matching edition within the work is determined for each copy and used
    for match quality. The caller selects which rows to persist.

    Args:
        product_urls: Antikvaari product page URLs to scrape.
        work_id: Our work ID — used to find editions for match quality.
        target_condition: User's copy condition (e.g. 'K3') for condition comparison.
    Returns:
        ResponseType with list of price row dicts, each including 'match_quality'
        and 'edition_id' of the best-matching edition.
    """
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        if not work:
            return ResponseType('Work not found', HttpResponseCode.NOT_FOUND)

        editions = list(work.editions)
        rows: List[Dict[str, Any]] = []

        for product_url in product_urls:
            props = _fetch_next_data(product_url)
            if props is None:
                continue

            catalog = props.get('catalog', {})
            product_id = catalog.get('_id', '')
            fallback_year = catalog.get('year', '')
            fallback_binding = catalog.get('binding', '')

            feed_elements = props.get('dataFeed', {}).get('dataFeedElement', [])
            book_el = next((el for el in feed_elements if el.get('@type') == 'Book'), None)
            work_examples = book_el.get('workExample', []) if book_el else []

            for we in work_examples:
                action = we.get('potentialAction', {})
                book_url = action.get('target', {}).get('urlTemplate', '')
                if not book_url:
                    continue

                book_props = _fetch_next_data(book_url)
                if book_props is None:
                    continue

                psp = book_props.get('preSelectedProduct', {})
                book_id = psp.get('_id', '') or book_url.rstrip('/').split('/')[-1]

                painos_raw = psp.get('painos', '') or we.get('bookEdition', '')
                painovuosi_raw = psp.get('painovuosi', '') or fallback_year
                sidonta = psp.get('sidonta') or fallback_binding
                extra = psp.get('nimikeLisatiedot', '') or ''
                extra_lower = extra.lower()

                price_val = psp.get('hinta')
                if price_val is None:
                    price_str = action.get('expectsAcceptanceOf', {}).get('price')
                    price_val = float(price_str) if price_str else None

                # date_listed: decoded from MongoDB ObjectID first 4 bytes
                date_listed = None
                if book_id and len(book_id) >= 8:
                    try:
                        ts = int(book_id[:8], 16)
                        date_listed = datetime.datetime.fromtimestamp(
                            ts, datetime.timezone.utc
                        ).date().isoformat()
                    except (ValueError, OSError):
                        pass

                # last_updated: pvm field = when seller last modified the listing
                last_updated = None
                pvm_str = psp.get('pvm', '')
                if pvm_str:
                    try:
                        last_updated = datetime.datetime.fromisoformat(
                            pvm_str.replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                    except ValueError:
                        pass

                product_year = int(painovuosi_raw) if painovuosi_raw else None
                product_version = _parse_version(painos_raw)
                condition = _parse_condition(psp.get('kunto', ''))
                binding_id = _binding_category(sidonta)

                edition = _best_matching_edition(
                    editions, product_year, product_version, binding_id
                )

                rows.append({
                    'edition_id': edition.id if edition else None,
                    'edition_pubyear': edition.pubyear if edition else None,
                    'edition_version': edition.version if edition else None,
                    'antikvaari_book_id': book_id,
                    'antikvaari_product_id': product_id,
                    'antikvaari_product_year': product_year,
                    'antikvaari_product_binding': binding_id,
                    'antikvaari_product_version': product_version,
                    'date_listed': date_listed,
                    'last_updated': last_updated.isoformat() if last_updated else None,
                    'condition': condition,
                    'is_library_discard': 'kirjaston poistotuote' in extra_lower,
                    'has_markings': 'merkintöjä' in extra_lower,
                    'missing_dust_cover': 'ei kansipaperia' in extra_lower,
                    'price': price_val,
                    'match_quality': calculate_match_quality(
                        edition, condition, product_year, product_version,
                        binding_id, target_condition,
                    ) if edition else None,
                })

        return ResponseType(rows, HttpResponseCode.OK)
    finally:
        session.close()


def _best_matching_edition(
    editions: List[Edition],
    product_year: Optional[int],
    product_version: Optional[int],
    product_binding: Optional[int],
) -> Optional[Edition]:
    """Return the edition that best matches Antikvaari product metadata."""
    if not editions:
        return None
    level_rank = {'same': 0, 'close': 1, 'not_close': 2}

    def score(ed: Edition) -> int:
        return level_rank[_edition_match_level(ed, product_year, product_version, product_binding)]

    return min(editions, key=score)


# ---------------------------------------------------------------------------
# Internal: change detection
# ---------------------------------------------------------------------------

def _is_changed(existing: 'AntikvaariPrice', new_last_updated: Optional[datetime.datetime],
                row: Dict[str, Any]) -> bool:
    """Return True if any tracked field differs from the most recently stored row."""
    def _trunc(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        return dt.replace(tzinfo=None, microsecond=0) if dt is not None else None

    if _trunc(existing.last_updated) != _trunc(new_last_updated):
        return True
    try:
        if float(existing.price) != float(row.get('price') or 0):
            return True
    except (TypeError, ValueError):
        pass
    if existing.condition != row.get('condition', ''):
        return True
    if existing.is_library_discard != bool(row.get('is_library_discard', False)):
        return True
    if existing.has_markings != bool(row.get('has_markings', False)):
        return True
    if existing.missing_dust_cover != bool(row.get('missing_dust_cover', False)):
        return True
    return False


# ---------------------------------------------------------------------------
# Public: save prices (change-detected, append-only)
# ---------------------------------------------------------------------------

def antikvaari_prices_save(edition_id: int, rows: List[Dict[str, Any]]) -> ResponseType:
    """Insert price rows for an edition only when data has changed since the last fetch.

    Each inserted row is permanent — prices are never updated or deleted.
    A row is skipped when the most recent stored row for that book has identical
    last_updated, condition, price and flag values.
    """
    session = new_session()
    try:
        edition = session.query(Edition).filter(Edition.id == edition_id).first()
        if not edition:
            return ResponseType('Edition not found', HttpResponseCode.NOT_FOUND)

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        saved = 0
        skipped = 0
        for row in rows:
            if not row.get('antikvaari_book_id'):
                continue

            date_listed = None
            if row.get('date_listed'):
                try:
                    date_listed = datetime.date.fromisoformat(row['date_listed'])
                except ValueError:
                    pass

            new_last_updated = None
            lu_raw = row.get('last_updated')
            if lu_raw:
                try:
                    new_last_updated = datetime.datetime.fromisoformat(
                        lu_raw if isinstance(lu_raw, str) else lu_raw.isoformat()
                    ).replace(tzinfo=None)
                except (ValueError, AttributeError):
                    pass

            existing = (session.query(AntikvaariPrice)
                        .filter(AntikvaariPrice.antikvaari_book_id == row['antikvaari_book_id'])
                        .order_by(AntikvaariPrice.date_fetched.desc())
                        .first())
            if existing and not _is_changed(existing, new_last_updated, row):
                skipped += 1
                continue

            session.add(AntikvaariPrice(
                edition_id=edition_id,
                antikvaari_book_id=row['antikvaari_book_id'],
                antikvaari_product_id=row.get('antikvaari_product_id', ''),
                antikvaari_product_year=row.get('antikvaari_product_year'),
                antikvaari_product_binding=row.get('antikvaari_product_binding'),
                antikvaari_product_version=row.get('antikvaari_product_version'),
                date_listed=date_listed,
                last_updated=new_last_updated or now,
                date_fetched=now,
                condition=row.get('condition', ''),
                is_library_discard=row.get('is_library_discard', False),
                has_markings=row.get('has_markings', False),
                missing_dust_cover=row.get('missing_dust_cover', False),
                price=row.get('price', 0),
            ))
            saved += 1

        session.commit()
        return ResponseType({'saved': saved, 'skipped': skipped}, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Save failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Public: retrieve stored prices
# ---------------------------------------------------------------------------

def edition_prices_get(
    edition_id: int,
    target_condition: Optional[str] = None,
) -> ResponseType:
    """Return stored price rows for an edition, each with calculated match quality."""
    session = new_session()
    try:
        edition = session.query(Edition).filter(Edition.id == edition_id).first()
        if not edition:
            return ResponseType('Edition not found', HttpResponseCode.NOT_FOUND)

        prices = (session.query(AntikvaariPrice)
                  .filter(AntikvaariPrice.edition_id == edition_id)
                  .order_by(AntikvaariPrice.date_fetched.desc())
                  .all())

        result = []
        for p in prices:
            result.append({
                'id': p.id,
                'edition_id': p.edition_id,
                'antikvaari_book_id': p.antikvaari_book_id,
                'antikvaari_product_id': p.antikvaari_product_id,
                'antikvaari_product_year': p.antikvaari_product_year,
                'antikvaari_product_binding': p.antikvaari_product_binding,
                'antikvaari_product_version': p.antikvaari_product_version,
                'date_listed': p.date_listed.isoformat() if p.date_listed else None,
                'last_updated': p.last_updated.isoformat() if p.last_updated else None,
                'date_fetched': p.date_fetched.isoformat() if p.date_fetched else None,
                'condition': p.condition,
                'is_library_discard': p.is_library_discard,
                'has_markings': p.has_markings,
                'missing_dust_cover': p.missing_dust_cover,
                'price': float(p.price),
                'match_quality': calculate_match_quality(
                    edition, p.condition,
                    p.antikvaari_product_year,
                    p.antikvaari_product_version,
                    p.antikvaari_product_binding,
                    target_condition,
                ),
            })

        return ResponseType(result, HttpResponseCode.OK)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Public: match quality
# ---------------------------------------------------------------------------

def calculate_match_quality(
    edition: Edition,
    antikvaari_condition: str,
    antikvaari_product_year: Optional[int],
    antikvaari_product_version: Optional[int],
    antikvaari_product_binding: Optional[int],
    target_condition: Optional[str] = None,
) -> str:
    """Calculate match quality for one Antikvaari price row against an edition.

    Args:
        edition: Our Edition ORM object.
        antikvaari_condition: Condition of the Antikvaari book, e.g. 'K3'.
        antikvaari_product_year: Year from painovuosi field.
        antikvaari_product_version: Edition number parsed from painos field.
        antikvaari_product_binding: Bindingtype ID (2=Nidottu, 3=Sidottu, None=unknown).
        target_condition: User's copy condition. When None, only edition closeness
                          contributes (condition assumed equal — best case).
    Returns:
        One of 'Perfect', 'Good', 'Decent', 'Poor'.
    """
    level = _edition_match_level(
        edition,
        antikvaari_product_year,
        antikvaari_product_version,
        antikvaari_product_binding,
    )

    if level == 'not_close':
        return 'Poor'

    if target_condition is None:
        return 'Good' if level == 'same' else 'Decent'

    our_k = _condition_int(_parse_condition(target_condition))
    their_k = _condition_int(antikvaari_condition)

    if our_k is None or their_k is None:
        return 'Decent' if level == 'same' else 'Poor'

    diff = abs(our_k - their_k)

    if level == 'same':
        if diff == 0:
            return 'Perfect'
        if diff == 1:
            return 'Good'
        return 'Decent'

    # level == 'close': downgrade by one step
    if diff == 0:
        return 'Good'
    if diff == 1:
        return 'Decent'
    return 'Poor'
