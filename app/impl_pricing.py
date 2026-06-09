"""Antikvaari pricing scraper and match quality calculation."""
from typing import Any, Dict, List, Optional
import datetime
import json
import re

import requests
from bs4 import BeautifulSoup

from app.impl import ResponseType
from app.orm_decl import (AntikvaariPrice, AntikvaariWorkProduct, BookCondition,
                           Edition, UserBook, Work)
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
    product_laitos: Optional[int] = None,
    edition_effective_editionnum: Optional[int] = None,
) -> str:
    """Return 'same', 'close', or 'not_close' comparing our edition to Antikvaari product metadata.

    Antikvaari's 'painos' field is the print-run number, which maps to our
    edition.editionnum (not edition.version/laitos).
    product_laitos is the laitos/version number (not scraped from Antikvaari;
    supplied by the user when correcting mismatches).

    edition_effective_editionnum overrides edition.editionnum when provided (used by
    _best_matching_edition to pass a chronologically-inferred editionnum for
    editions that have no stored editionnum).
    """
    eff_editionnum = (
        edition_effective_editionnum
        if edition_effective_editionnum is not None
        else edition.editionnum
    )

    # Laitos (version): must match exactly when both are known
    if product_laitos is not None and edition.version is not None:
        if product_laitos != edition.version:
            return 'not_close'

    # Editionnum (painos): must match exactly when both are known
    if product_version is not None and eff_editionnum is not None:
        if product_version != eff_editionnum:
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

    # When no edition number is provided by Antikvaari, require both year and
    # binding to be confirmed before calling it 'same'. Without version info a
    # year-only or binding-only match is too ambiguous.
    if product_version is None:
        year_confirmed = (
            product_year is not None
            and bool(edition.pubyear)
            and product_year == edition.pubyear
        )
        binding_confirmed = (
            product_binding is not None and product_binding > 1
            and edition.binding_id is not None and edition.binding_id > 1
            and product_binding == edition.binding_id
        )
        if not (year_confirmed and binding_confirmed):
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
              'url': r.url,
              'rejected': bool(r.rejected)}
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
            r.antikvaari_product_id: r
            for r in session.query(AntikvaariWorkProduct)
            .filter(AntikvaariWorkProduct.work_id == work_id)
            .all()
        }
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        added = 0
        for item in products:
            pid = item.get('product_id', '') if isinstance(item, dict) else item
            url = item.get('url') if isinstance(item, dict) else None
            rejected = bool(item.get('rejected', False)) if isinstance(item, dict) else False
            if not pid:
                continue
            if pid in existing:
                # If previously rejected and now being added as linked, un-reject it
                existing_row = existing[pid]
                if not rejected and existing_row.rejected:
                    existing_row.rejected = False
                    added += 1
            else:
                session.add(AntikvaariWorkProduct(
                    work_id=work_id,
                    antikvaari_product_id=pid,
                    added=now,
                    url=url,
                    rejected=rejected,
                ))
                if not rejected:
                    added += 1
        session.commit()
        return ResponseType({'added': added}, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Save failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


def antikvaari_prices_save_all(work_id: int, rows: List[Dict[str, Any]]) -> ResponseType:
    """Save all fetched price rows for a work, grouped by edition.

    Re-matches each row against work editions using the (possibly user-edited)
    antikvaari_product_version (painos) and antikvaari_product_laitos (laitos)
    values, so corrections made in the UI are honoured.
    """
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        editions = list(work.editions) if work else []
    finally:
        session.close()

    by_edition: Dict[int, List[Dict[str, Any]]] = {}
    no_edition_rows: List[Dict[str, Any]] = []
    for row in rows:
        product_version = row.get('antikvaari_product_version')
        product_laitos = row.get('antikvaari_product_laitos')
        product_year = row.get('antikvaari_product_year')
        product_binding = row.get('antikvaari_product_binding')
        edition, match_level = _best_matching_edition(
            editions, product_year, product_version, product_binding, product_laitos
        )
        updated_row = {
            **row,
            'edition_id': edition.id if edition else None,
            'edition_match_level': match_level,
        }
        if edition is None or match_level == 'not_close':
            no_edition_rows.append(updated_row)
        else:
            by_edition.setdefault(edition.id, []).append(updated_row)

    total_saved = 0
    total_skipped = 0
    detail_rows: List[Dict[str, Any]] = []

    for row in no_edition_rows:
        reason = 'no_edition' if row.get('edition_id') is None else 'edition_missing'
        detail_rows.append({**row, 'status': 'skipped', 'reason': reason})
        total_skipped += 1

    for edition_id, edition_rows in by_edition.items():
        result = antikvaari_prices_save(edition_id, edition_rows)
        if result.status == HttpResponseCode.OK and isinstance(result.response, dict):
            total_saved += result.response.get('saved', 0)
            total_skipped += result.response.get('skipped', 0)
            detail_rows.extend(result.response.get('rows', []))
        else:
            for row in edition_rows:
                detail_rows.append({**row, 'status': 'error', 'reason': str(result.response)})

    return ResponseType({
        'saved': total_saved,
        'skipped': total_skipped,
        'rows': detail_rows,
    }, HttpResponseCode.OK)


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
            product_id = catalog.get('_id') or ''
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

                if psp.get('kampanja'):
                    continue

                painos_raw = psp.get('painos', '') or we.get('bookEdition', '')
                painovuosi_raw = psp.get('painovuosi', '') or fallback_year
                sidonta = psp.get('sidonta') or fallback_binding
                extra = psp.get('nimikeLisatiedot', '') or ''
                # Flags appear in nimikeLisatiedot or embedded in sidonta
                # (e.g. "Sidottu, ei kansipaperia")
                extra_lower = f"{extra} {sidonta}".lower()

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

                edition, edition_match_level = _best_matching_edition(
                    editions, product_year, product_version, binding_id
                )

                rows.append({
                    'edition_id': edition.id if edition else None,
                    'edition_pubyear': edition.pubyear if edition else None,
                    'edition_version': edition.version if edition else None,
                    'edition_match_level': edition_match_level,
                    'antikvaari_book_id': book_id,
                    'antikvaari_product_id': product_id,
                    'antikvaari_product_url': book_url,
                    'antikvaari_product_year': product_year,
                    'antikvaari_product_binding': binding_id,
                    'antikvaari_product_version': product_version,
                    'antikvaari_product_laitos': None,  # not provided by Antikvaari; user may set it
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
    product_laitos: Optional[int] = None,
) -> tuple:
    """Return (edition, match_level) for the best-matching edition.

    match_level is 'same', 'close', or 'not_close'.
    Returns (None, 'not_close') when editions is empty.

    product_laitos is the laitos/version number — None means unknown (Antikvaari
    doesn't provide it), in which case no laitos filtering is done.

    When the Antikvaari product carries a version number but our editions have
    no stored version, we infer a rank by chronological order of pubyear so
    that e.g. '1. painos' maps to the earliest edition rather than whichever
    edition happens to share the same printing year.
    """
    if not editions:
        return None, 'not_close'
    level_rank = {'same': 0, 'close': 1, 'not_close': 2}
    rank_level = {0: 'same', 1: 'close', 2: 'not_close'}

    # Build inferred-editionnum map for editions whose editionnum is NULL.
    inferred: Dict[int, int] = {}
    if product_version is not None:
        null_enum = [e for e in editions if e.editionnum is None]
        for rank, ed in enumerate(
            sorted(null_enum, key=lambda e: (e.pubyear or 9999, e.id)), start=1
        ):
            inferred[ed.id] = rank

    def score(ed: Edition) -> int:
        eff_enum = inferred.get(ed.id) if ed.editionnum is None else None
        return level_rank[_edition_match_level(
            ed, product_year, product_version, product_binding, product_laitos, eff_enum
        )]

    best = min(editions, key=score)
    return best, rank_level[score(best)]


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
        detail_rows: List[Dict[str, Any]] = []
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
                detail_rows.append({**row, 'status': 'skipped', 'reason': 'unchanged'})
                continue

            session.add(AntikvaariPrice(
                edition_id=edition_id,
                antikvaari_book_id=row['antikvaari_book_id'],
                antikvaari_product_id=row.get('antikvaari_product_id') or '',
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
            detail_rows.append({**row, 'status': 'saved', 'reason': None})

        session.commit()
        return ResponseType({'saved': saved, 'skipped': skipped, 'rows': detail_rows}, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Save failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Public: retrieve stored prices
# ---------------------------------------------------------------------------

def edition_prices_count(edition_id: int) -> ResponseType:
    """Return the number of stored price rows for an edition."""
    session = new_session()
    try:
        count = (session.query(AntikvaariPrice)
                 .filter(AntikvaariPrice.edition_id == edition_id)
                 .count())
        return ResponseType({'count': count}, HttpResponseCode.OK)
    finally:
        session.close()


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


def antikvaari_price_delete(price_id: int) -> ResponseType:
    """Delete a single stored price row by its primary key."""
    session = new_session()
    try:
        row = session.query(AntikvaariPrice).filter(AntikvaariPrice.id == price_id).first()
        if not row:
            return ResponseType('Price not found', HttpResponseCode.NOT_FOUND)
        session.delete(row)
        session.commit()
        return ResponseType({'deleted': price_id}, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Delete failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
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


# ---------------------------------------------------------------------------
# Public: user collection stats
# ---------------------------------------------------------------------------

_QUALITY_RANK: Dict[str, int] = {'Perfect': 0, 'Good': 1, 'Decent': 2, 'Poor': 3}


def user_collection_stats(user_id: int) -> ResponseType:
    """Return Antikvaari pricing statistics for all editions owned by user_id."""
    session = new_session()
    try:
        owned = (
            session.query(UserBook)
            .filter(
                UserBook.user_id == user_id,
                UserBook.condition_id >= 1,
                UserBook.condition_id <= 5,
            )
            .all()
        )

        total_owned = len(owned)
        if total_owned == 0:
            return ResponseType({
                'total_owned': 0,
                'priced_count': 0,
                'total_value': 0.0,
                'quality_distribution': {
                    'Perfect': 0, 'Good': 0, 'Decent': 0, 'Poor': 0, 'not_priced': 0
                },
                'top_expensive': [],
                'no_price_books': [],
            }, HttpResponseCode.OK)

        # condition_id → "K{value}" string
        cond_ids = list({ub.condition_id for ub in owned})
        condition_map: Dict[int, str] = {
            c.id: f'K{c.value}'
            for c in session.query(BookCondition)
            .filter(BookCondition.id.in_(cond_ids))
            .all()
        }

        edition_ids = [ub.edition_id for ub in owned]

        editions_map: Dict[int, Edition] = {
            e.id: e
            for e in session.query(Edition)
            .filter(Edition.id.in_(edition_ids))
            .all()
        }

        work_ids = list({e.work_id for e in editions_map.values() if e.work_id})
        linked_work_ids: set = set(
            row[0]
            for row in session.query(AntikvaariWorkProduct.work_id)
            .filter(AntikvaariWorkProduct.work_id.in_(work_ids))
            .distinct()
            .all()
        )

        prices_by_edition: Dict[int, List[AntikvaariPrice]] = {}
        for p in (
            session.query(AntikvaariPrice)
            .filter(AntikvaariPrice.edition_id.in_(edition_ids))
            .all()
        ):
            prices_by_edition.setdefault(p.edition_id, []).append(p)

        dist: Dict[str, int] = {
            'Perfect': 0, 'Good': 0, 'Decent': 0, 'Poor': 0, 'not_priced': 0
        }
        priced_count = 0
        total_value = 0.0
        book_prices: List[Dict[str, Any]] = []
        no_price_books: List[Dict[str, Any]] = []

        for ub in owned:
            eid = ub.edition_id
            target = condition_map.get(ub.condition_id)
            edition = editions_map.get(eid)
            price_rows = prices_by_edition.get(eid, [])

            if not price_rows or not edition:
                if edition and edition.work_id in linked_work_ids:
                    w = edition.work
                    no_price_books.append({
                        'edition_id': eid,
                        'work_id': edition.work_id,
                        'title': w.title if w else '',
                        'author_str': w.author_str if w else '',
                        'pubyear': edition.pubyear,
                        'version': edition.version,
                    })
                else:
                    dist['not_priced'] += 1
                continue

            best_q: Optional[str] = None
            best_rank = 999
            best_val = float('inf')

            for p in price_rows:
                q = calculate_match_quality(
                    edition,
                    p.condition,
                    p.antikvaari_product_year,
                    p.antikvaari_product_version,
                    p.antikvaari_product_binding,
                    target,
                )
                rank = _QUALITY_RANK.get(q, 3)
                pval = float(p.price)
                if rank < best_rank or (rank == best_rank and pval < best_val):
                    best_rank, best_val, best_q = rank, pval, q

            if best_q is not None:
                priced_count += 1
                total_value += best_val
                dist[best_q] = dist.get(best_q, 0) + 1
                book_prices.append({
                    'edition_id': eid,
                    'price': best_val,
                    'match_quality': best_q,
                    'condition': target or '',
                })

        book_prices.sort(key=lambda x: x['price'], reverse=True)

        top_expensive = []
        for entry in book_prices[:10]:
            e = editions_map.get(entry['edition_id'])
            if not e:
                continue
            w = e.work
            top_expensive.append({
                'edition_id': entry['edition_id'],
                'work_id': e.work_id,
                'title': w.title if w else '',
                'author_str': w.author_str if w else '',
                'pubyear': e.pubyear,
                'version': e.version,
                'price': entry['price'],
                'match_quality': entry['match_quality'],
                'condition': entry['condition'],
            })

        no_price_books.sort(key=lambda x: (x['author_str'], x['title']))

        return ResponseType({
            'total_owned': total_owned,
            'priced_count': priced_count,
            'total_value': round(total_value, 2),
            'quality_distribution': dist,
            'top_expensive': top_expensive,
            'no_price_books': no_price_books,
        }, HttpResponseCode.OK)
    finally:
        session.close()
