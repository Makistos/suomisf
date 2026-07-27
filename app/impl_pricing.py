"""Antikvaari pricing scraper and match quality calculation."""
from typing import Any, Callable, Dict, List, Optional
import datetime
import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from app.impl import ResponseType
from app.orm_decl import (AntikvaariExcludedBook, AntikvaariPrice,
                           AntikvaariWorkProduct, BookCondition,
                           Edition, PriceSource, UserBook, Work)
from app.route_helpers import new_session
from app.types import HttpResponseCode

ANTIKVAARI_BASE = 'https://www.antikvaari.fi'
_SEARCH_URL = f'{ANTIKVAARI_BASE}/api/products/search-v2'
_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

ANTIKKA_BASE = 'https://antikka.net'
ANTIKVARIAATTI_BASE = 'https://www.antikvariaatti.net'


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
        # Only demote to 'close' for year diff when painos is not confirmed.
        # When painos matches, a small year discrepancy is a data-entry artefact.
        if diff > 0 and product_version is None:
            return 'close'

    # When no Antikvaari metadata is provided at all, the edition is already
    # confirmed matched (stored-prices path) — skip ambiguity checks.
    if product_version is None and product_year is None and product_binding is None:
        return 'same'

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


def _antikka_price(el: Any) -> Optional[float]:
    """Parse a WooCommerce price element like '60,00 €' into a float."""
    if not el:
        return None
    raw = (el.get_text(strip=True)
           .replace('\xa0', '').replace('€', '').replace(',', '.').strip())
    try:
        return float(raw)
    except ValueError:
        return None


def antikka_search(q: str, isbn: str = '') -> ResponseType:
    """Search antikka.net (WooCommerce). Each result is a single physical copy.

    Unlike Antikvaari (where a product aggregates many copies), every antikka
    search hit is one listing, so available_count is always 1.
    """
    params = {'s': f'{q} {isbn}'.strip(), 'post_type': 'product'}
    try:
        resp = requests.get(f'{ANTIKKA_BASE}/', params=params,
                            headers={'User-Agent': _UA}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return ResponseType(f'Antikka search failed: {exc}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR)

    soup = BeautifulSoup(resp.text, 'html.parser')

    # WooCommerce redirects a search that matches exactly one product straight
    # to that product's page (no result cards). Treat it as a single result.
    if '/tuote/' in resp.url:
        title_el = soup.select_one('h1.product_title')
        img_el = soup.select_one('img.wp-post-image')
        return ResponseType([{
            'product_id': resp.url.rstrip('/').split('/')[-1],
            'title': title_el.get_text(strip=True) if title_el else q,
            'author': '',
            'year': '',
            'binding': '',
            'url': resp.url,
            'image': img_el.get('src', '') if img_el else '',
            'available_count': 1,
            'price': _antikka_price(soup.select_one('p.price .woocommerce-Price-amount')),
        }], HttpResponseCode.OK)

    products: List[Dict[str, Any]] = []
    seen: set = set()
    for li in soup.select('li.product'):
        link = li.select_one('a.woocommerce-loop-product__link') \
            or li.select_one('a[href*="/tuote/"]')
        if not link or not link.get('href'):
            continue
        url = link['href']
        product_id = url.rstrip('/').split('/')[-1]
        if product_id in seen:
            continue
        seen.add(product_id)
        title_el = li.select_one('.woocommerce-loop-product__title')
        img_el = li.select_one('img')
        products.append({
            'product_id': product_id,
            'title': title_el.get_text(strip=True) if title_el else '',
            'author': '',
            'year': '',
            'binding': '',
            'url': url,
            'image': img_el.get('src', '') if img_el else '',
            'available_count': 1,
            'price': _antikka_price(li.select_one('.price .woocommerce-Price-amount')),
        })
    return ResponseType(products, HttpResponseCode.OK)


def _price_from_text(text: str) -> Optional[float]:
    """Parse a Finnish-formatted price like 'Hinta: 16,00 €' into a float."""
    m = re.search(r'(\d+)[.,](\d{2})',
                  (text or '').replace('\xa0', '').replace(' ', ''))
    return float(f'{m.group(1)}.{m.group(2)}') if m else None


def antikvariaatti_search(q: str, isbn: str = '') -> ResponseType:
    """Search antikvariaatti.net. Each result card is a single physical copy."""
    query = f'{q} {isbn}'.strip()
    try:
        resp = requests.get(f'{ANTIKVARIAATTI_BASE}/haku', params={'q': query},
                            headers={'User-Agent': _UA}, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return ResponseType(f'Antikvariaatti search failed: {exc}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR)

    soup = BeautifulSoup(resp.text, 'html.parser')
    products: List[Dict[str, Any]] = []
    seen: set = set()
    for card in soup.select('.search_result_product'):
        link = card.select_one('a[href*="tuotteet/"]')
        if not link or not link.get('href'):
            continue
        url = urljoin(ANTIKVARIAATTI_BASE + '/', link['href'])
        product_id = url.rstrip('/').split('/')[-1]
        if product_id in seen:
            continue
        seen.add(product_id)
        title = card.select_one('.search_result_product_title')
        issuer = card.select_one('.search_result_product_issuer')
        price_el = card.select_one('.search_result_product_price')
        img = card.select_one('img')
        products.append({
            'product_id': product_id,
            'title': title.get_text(strip=True) if title else '',
            'author': issuer.get_text(strip=True) if issuer else '',
            'year': '',
            'binding': '',
            'url': url,
            'image': img.get('src', '') if img else '',
            'available_count': 1,
            'price': _price_from_text(price_el.get_text()) if price_el else None,
        })
    return ResponseType(products, HttpResponseCode.OK)


# ---------------------------------------------------------------------------
# Public: work-product mapping
# ---------------------------------------------------------------------------

def _resolve_source(session: Any, source: Any) -> Optional[PriceSource]:
    """Resolve a source given by id, name, or None (defaults to Antikvaari)."""
    if source is None:
        return (session.query(PriceSource)
                .filter(PriceSource.name == 'Antikvaari').first())
    if isinstance(source, int) or (isinstance(source, str) and source.isdigit()):
        return session.query(PriceSource).filter(PriceSource.id == int(source)).first()
    return session.query(PriceSource).filter(PriceSource.name == source).first()


def work_products_get(work_id: int, source: Any = None) -> ResponseType:
    """Return product IDs linked to a work for a given source (default Antikvaari)."""
    session = new_session()
    try:
        src = _resolve_source(session, source)
        if not src:
            return ResponseType('Unknown source', HttpResponseCode.BAD_REQUEST)
        rows = (session.query(AntikvaariWorkProduct)
                .filter(AntikvaariWorkProduct.work_id == work_id,
                        AntikvaariWorkProduct.source_id == src.id)
                .all())
        return ResponseType(
            [{'id': r.id, 'antikvaari_product_id': r.antikvaari_product_id,
              'source_id': r.source_id,
              'added': r.added.isoformat() if r.added else None,
              'url': r.url,
              'rejected': bool(r.rejected)}
             for r in rows],
            HttpResponseCode.OK,
        )
    finally:
        session.close()


def work_products_save(work_id: int, products: List[Dict[str, Any]],
                       source: Any = None) -> ResponseType:
    """Link products (id+url) from a source to a work. Existing mappings are preserved."""
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        if not work:
            return ResponseType('Work not found', HttpResponseCode.NOT_FOUND)
        src = _resolve_source(session, source)
        if not src:
            return ResponseType('Unknown source', HttpResponseCode.BAD_REQUEST)

        existing = {
            r.antikvaari_product_id: r
            for r in session.query(AntikvaariWorkProduct)
            .filter(AntikvaariWorkProduct.work_id == work_id,
                    AntikvaariWorkProduct.source_id == src.id)
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
                    source_id=src.id,
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


def work_product_delete(work_id: int, product_id: str,
                        source: Any = None) -> ResponseType:
    """Remove a product link from a work for a given source (default Antikvaari)."""
    session = new_session()
    try:
        src = _resolve_source(session, source)
        if not src:
            return ResponseType('Unknown source', HttpResponseCode.BAD_REQUEST)
        row = (session.query(AntikvaariWorkProduct)
               .filter(AntikvaariWorkProduct.work_id == work_id,
                       AntikvaariWorkProduct.source_id == src.id,
                       AntikvaariWorkProduct.antikvaari_product_id == product_id)
               .first())
        if not row:
            return ResponseType('Product not found', HttpResponseCode.NOT_FOUND)
        session.delete(row)
        session.commit()
        return ResponseType({'deleted': product_id}, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Delete failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


def antikvaari_prices_save_all(work_id: int, rows: List[Dict[str, Any]]) -> ResponseType:
    """Save all fetched price rows for a work, grouped by edition.

    Re-matches each row against work editions using the (possibly user-edited)
    antikvaari_product_version (painos) and antikvaari_product_laitos (laitos)
    values. Rows with user_excluded=True are saved to antikvaari_excluded_book
    instead of antikvaari_price. Rows with user_excluded=False that were
    previously excluded are removed from the exclusion table.
    """
    user_excluded_rows: List[Dict[str, Any]] = []
    included_rows: List[Dict[str, Any]] = []
    for row in rows:
        if row.get('user_excluded'):
            user_excluded_rows.append(row)
        else:
            included_rows.append(row)

    # --- Persist exclusion changes and re-match, all in one session ---
    by_edition: Dict[int, List[Dict[str, Any]]] = {}
    no_edition_rows: List[Dict[str, Any]] = []
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        editions = list(work.editions) if work else []

        # Save newly excluded book IDs
        existing_excluded = {
            r.antikvaari_book_id
            for r in session.query(AntikvaariExcludedBook).all()
        }
        for row in user_excluded_rows:
            bid = row.get('antikvaari_book_id')
            if bid and bid not in existing_excluded:
                session.add(AntikvaariExcludedBook(antikvaari_book_id=bid))

        # Remove un-excluded book IDs (user re-checked a previously excluded copy)
        for row in included_rows:
            bid = row.get('antikvaari_book_id')
            if bid and bid in existing_excluded:
                exc = session.query(AntikvaariExcludedBook).filter_by(
                    antikvaari_book_id=bid
                ).first()
                if exc:
                    session.delete(exc)

        # Re-match while editions are still attached to the session
        for row in included_rows:
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

        session.commit()
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Exclusion save failed: {exc}',
                            HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()

    total_saved = 0
    total_skipped = 0
    detail_rows: List[Dict[str, Any]] = []

    for row in user_excluded_rows:
        detail_rows.append({**row, 'status': 'skipped', 'reason': 'excluded'})
        total_skipped += 1

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

        # Pre-load excluded book IDs for fast lookup
        excluded_ids = {
            r.antikvaari_book_id
            for r in session.query(AntikvaariExcludedBook).all()
        }

        # Map product_url → AntikvaariWorkProduct row for page_exists updates
        work_products: Dict[str, Any] = {
            r.url: r
            for r in session.query(AntikvaariWorkProduct)
            .filter(AntikvaariWorkProduct.work_id == work_id)
            .all()
            if r.url
        }

        rows: List[Dict[str, Any]] = []

        for product_url in product_urls:
            props = _fetch_next_data(product_url)
            if props is None:
                # Mark the product page as gone
                wp = work_products.get(product_url)
                if wp and wp.page_exists:
                    wp.page_exists = False
                continue

            catalog = props.get('catalog', {})
            product_id = catalog.get('_id') or ''
            fallback_year = catalog.get('year', '')
            fallback_binding = catalog.get('binding', '')
            fallback_title = catalog.get('title', '') or ''
            fallback_author = catalog.get('author', '') or ''
            catalog_languages = catalog.get('languages') or []
            language_code = catalog_languages[0] if catalog_languages else None

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
                # Flags appear in nimikeLisatiedot or embedded in sidonta
                # (e.g. "Sidottu, ei kansipapereita (kovakantinen)")
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

                try:
                    product_year = int(str(painovuosi_raw).split('-')[0]) if painovuosi_raw else None
                except (ValueError, TypeError):
                    product_year = None
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
                    'antikvaari_product_page_url': product_url,
                    'antikvaari_product_url': book_url,
                    'antikvaari_product_year': product_year,
                    'antikvaari_product_binding': binding_id,
                    'antikvaari_product_version': product_version,
                    'antikvaari_product_laitos': None,  # not provided by Antikvaari; user may set it
                    'book_title': psp.get('nimi', '') or fallback_title or None,
                    'book_author': psp.get('tekija', '') or fallback_author or None,
                    'book_language': language_code,
                    'seller': psp.get('ynimi') or None,
                    'seller_url': None,  # Antikvaari exposes no vendor page URL
                    'date_listed': date_listed,
                    'last_updated': last_updated.isoformat() if last_updated else None,
                    'condition': condition,
                    'is_library_discard': 'kirjaston poistotuote' in extra_lower,
                    'has_markings': 'merkintöjä' in extra_lower,
                    'missing_dust_cover': ('ei kansipaperia' in extra_lower
                                          or 'ei kansipapereita' in extra_lower),
                    'price': price_val,
                    'match_quality': calculate_match_quality(
                        edition, condition, product_year, product_version,
                        binding_id, target_condition,
                    ) if edition else None,
                    'user_excluded': book_id in excluded_ids,
                })

        session.commit()
        return ResponseType(rows, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Fetch failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


def _single_page_fetch_products(
    product_urls: List[str],
    work_id: int,
    target_condition: Optional[str],
    scrape_fn: Callable[[str], Dict[str, Any]],
    source_name: str,
) -> ResponseType:
    """Fetch prices from shops where each product URL is a single physical copy.

    Shared by antikka.net and antikvariaatti.net: scrapes one page per URL with
    ``scrape_fn`` and produces one row each, in the same shape as
    antikvaari_fetch_products so the same frontend and save path handle all
    sources.
    """
    session = new_session()
    try:
        work = session.query(Work).filter(Work.id == work_id).first()
        if not work:
            return ResponseType('Work not found', HttpResponseCode.NOT_FOUND)

        editions = list(work.editions)

        excluded_ids = {
            r.antikvaari_book_id
            for r in session.query(AntikvaariExcludedBook).all()
        }

        source = (session.query(PriceSource)
                  .filter(PriceSource.name == source_name).first())
        source_id = source.id if source else None

        # Map listing url -> AntikvaariWorkProduct row for page_exists updates
        work_products: Dict[str, Any] = {
            r.url: r
            for r in session.query(AntikvaariWorkProduct)
            .filter(AntikvaariWorkProduct.work_id == work_id,
                    AntikvaariWorkProduct.source_id == source_id)
            .all()
            if r.url
        }

        rows: List[Dict[str, Any]] = []

        for product_url in product_urls:
            try:
                fields = scrape_fn(product_url)
            except requests.RequestException:
                wp = work_products.get(product_url)
                if wp and wp.page_exists:
                    wp.page_exists = False
                continue

            product_id = product_url.rstrip('/').split('/')[-1]
            book_id = fields.get('book_id') or product_id
            product_year = fields.get('year')
            product_version = fields.get('version')
            binding_id = fields.get('binding')
            condition = fields.get('condition') or ''

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
                'antikvaari_product_page_url': product_url,
                'antikvaari_product_url': product_url,
                'antikvaari_product_year': product_year,
                'antikvaari_product_binding': binding_id,
                'antikvaari_product_version': product_version,
                'antikvaari_product_laitos': None,
                'book_title': fields.get('title'),
                'book_author': fields.get('author'),
                'book_language': fields.get('language'),
                'seller': fields.get('seller'),
                'seller_url': fields.get('seller_url'),
                'date_listed': None,
                'last_updated': fields.get('last_updated'),
                'condition': condition,
                'is_library_discard': False,
                'has_markings': False,
                'missing_dust_cover': False,
                'price': fields.get('price'),
                'match_quality': calculate_match_quality(
                    edition, condition, product_year, product_version,
                    binding_id, target_condition,
                ) if edition else None,
                'user_excluded': book_id in excluded_ids,
                'source_id': source_id,
                'source_name': source_name,
            })

        session.commit()
        return ResponseType(rows, HttpResponseCode.OK)
    except Exception as exc:  # pylint: disable=broad-except
        session.rollback()
        return ResponseType(f'Fetch failed: {exc}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


def antikka_fetch_products(
    product_urls: List[str],
    work_id: int,
    target_condition: Optional[str] = None,
) -> ResponseType:
    """Scrape antikka.net listing pages and return price rows with match quality."""
    return _single_page_fetch_products(
        product_urls, work_id, target_condition, _scrape_antikka, 'Antikka')


def antikvariaatti_fetch_products(
    product_urls: List[str],
    work_id: int,
    target_condition: Optional[str] = None,
) -> ResponseType:
    """Scrape antikvariaatti.net product pages and return price rows with match quality."""
    return _single_page_fetch_products(
        product_urls, work_id, target_condition,
        _scrape_antikvariaatti, 'Antikvariaatti')


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

        # Resolve the price source per row (rows carry source_id/source_name
        # from the fetch step). Falls back to Antikvaari for backward
        # compatibility with older callers that don't set a source.
        default_source = (session.query(PriceSource)
                          .filter(PriceSource.name == 'Antikvaari').first())
        default_source_id = default_source.id if default_source else 1
        source_id_by_name = {
            s.name: s.id for s in session.query(PriceSource).all()
        }

        def _resolve_source_id(row: Dict[str, Any]) -> int:
            sid = row.get('source_id')
            if sid:
                return int(sid)
            name = row.get('source_name')
            if name and name in source_id_by_name:
                return source_id_by_name[name]
            return default_source_id

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

        # Cross-store duplicate filter: one seller often lists the same physical
        # copy on several marketplaces. Skip a row when a stored row for this
        # edition (or an earlier row in this batch) already has the same
        # (seller, painos, binding, condition, price) — different painos or
        # binding are genuinely different books. Only applies when the seller is
        # known.
        def _dupe_key(seller: Any, version: Any, binding: Any,
                      condition: Any, price: Any):
            if not seller:
                return None
            try:
                normalized_price = round(float(price), 2)
            except (TypeError, ValueError):
                return None
            return (str(seller).strip().lower(), version, binding,
                    str(condition or '').strip(), normalized_price)

        active_dupe_keys = set()
        seen_books = set()
        for r in (session.query(AntikvaariPrice)
                  .filter(AntikvaariPrice.edition_id == edition_id)
                  .order_by(AntikvaariPrice.date_fetched.desc())
                  .all()):
            if r.antikvaari_book_id in seen_books:
                continue
            seen_books.add(r.antikvaari_book_id)
            key = _dupe_key(r.seller, r.antikvaari_product_version,
                            r.antikvaari_product_binding, r.condition, r.price)
            if key:
                active_dupe_keys.add(key)
        batch_dupe_keys: set = set()

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
                        .filter(AntikvaariPrice.edition_id == edition_id)
                        .order_by(AntikvaariPrice.date_fetched.desc())
                        .first())
            if existing and not _is_changed(existing, new_last_updated, row):
                skipped += 1
                detail_rows.append({**row, 'status': 'skipped', 'reason': 'unchanged'})
                continue

            dupe_key = _dupe_key(row.get('seller'),
                                 row.get('antikvaari_product_version'),
                                 row.get('antikvaari_product_binding'),
                                 row.get('condition'), row.get('price'))
            if dupe_key and (dupe_key in active_dupe_keys
                             or dupe_key in batch_dupe_keys):
                skipped += 1
                detail_rows.append({**row, 'status': 'skipped', 'reason': 'duplicate'})
                continue

            session.add(AntikvaariPrice(
                edition_id=edition_id,
                source_id=_resolve_source_id(row),
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
                url=row.get('antikvaari_product_url') or row.get('url'),
                seller=row.get('seller') or None,
                seller_url=row.get('seller_url') or None,
            ))
            if dupe_key:
                batch_dupe_keys.add(dupe_key)
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

        rows = (
            session.query(AntikvaariPrice, AntikvaariWorkProduct)
            .outerjoin(
                AntikvaariWorkProduct,
                (AntikvaariPrice.antikvaari_product_id == AntikvaariWorkProduct.antikvaari_product_id)
                & (AntikvaariWorkProduct.work_id == edition.work_id),
            )
            .filter(AntikvaariPrice.edition_id == edition_id)
            .order_by(AntikvaariPrice.date_fetched.desc())
            .all()
        )

        result = []
        for p, wp in rows:
            result.append({
                'id': p.id,
                'edition_id': p.edition_id,
                'source_id': p.source_id,
                'source_name': p.source.name if p.source else None,
                'seller': p.seller,
                'seller_url': p.seller_url,
                'book_id': p.antikvaari_book_id,
                'url': p.url,
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
                    None, None, None,
                    target_condition,
                ),
                'product_url': wp.url if wp else None,
                'product_page_exists': wp.page_exists if wp else None,
            })

        return ResponseType(result, HttpResponseCode.OK)
    finally:
        session.close()


def _source_from_url(url: str, session: Any) -> Optional[PriceSource]:
    """Return the PriceSource that matches a URL's domain."""
    checks = [
        ('antikvariaatti.net', 'Antikvariaatti'),
        ('antikka.net',        'Antikka'),
        ('huuto.net',          'Huuto.net'),
        ('antikvaari.fi',      'Antikvaari'),
    ]
    for domain, name in checks:
        if domain in url:
            return session.query(PriceSource).filter(PriceSource.name == name).first()
    return None


def _antikvariaatti_attributes(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract antikvariaatti.net product attribute rows as a {label: value} dict.

    Keeps the first value seen for a label (e.g. 'Kunto' appears twice — the
    first is the 'K3 (Hyvä)' form we want).
    """
    attrs: Dict[str, str] = {}
    for label in soup.find_all('div', class_='product_attribute_label'):
        row = label.find_parent(class_='w-row')
        if not row:
            continue
        value = (row.select_one('.product_attribute_value_container')
                 or row.select_one('.product_attribute_value'))
        name = label.get_text(strip=True).rstrip(':')
        if name and value and name not in attrs:
            attrs[name] = value.get_text(' ', strip=True)
    return attrs


def _scrape_antikvariaatti(url: str) -> Dict[str, Any]:
    """Scrape a single antikvariaatti.net product page and return price fields.

    Returns the fields the manual path needs (book_id, price, condition,
    last_updated) plus edition-matching metadata (year/version/binding,
    title/author/language) and the seller, so the same scraper feeds the
    automatic fetch flow.
    """
    book_id = url.rstrip('/').split('/')[-1]
    resp = requests.get(url, headers={'User-Agent': _UA}, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    price: Optional[float] = None
    for script in soup.find_all('script'):
        text = script.string or ''
        if 'schema.org' in text and 'offers' in text:
            try:
                data = json.loads(text.strip())
                price = float(data['offers']['price'])
                break
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass

    attrs = _antikvariaatti_attributes(soup)

    condition: Optional[str] = None
    cond_match = re.match(r'(K[1-5])', attrs.get('Kunto', ''))
    if cond_match:
        condition = cond_match.group(1)

    year: Optional[int] = None
    year_match = re.search(r'\d{4}', attrs.get('Julkaistu', ''))
    if year_match:
        year = int(year_match.group())

    version = _parse_version(attrs.get('Painos', ''))
    binding = _binding_category(attrs.get('Nidonta', ''))

    # Seller: the anchor in the "Myyjä" attribute row.
    seller: Optional[str] = None
    seller_url: Optional[str] = None
    for label in soup.find_all('div', class_='product_attribute_label'):
        if 'Myyjä' in label.get_text():
            row = label.find_parent(class_='w-row')
            anchor = row.find('a', href=True) if row else None
            if anchor:
                seller = anchor.get_text(strip=True) or None
                seller_url = urljoin(ANTIKVARIAATTI_BASE + '/', anchor['href'])
            break

    title_el = soup.select_one('h1')

    return {
        'book_id': book_id,
        'price': price,
        'condition': condition,
        'year': year,
        'version': version,
        'binding': binding,
        'title': (title_el.get_text(strip=True) if title_el else None),
        'author': attrs.get('Tekijä') or None,
        'language': attrs.get('Kielet') or None,
        'seller': seller,
        'seller_url': seller_url,
        'last_updated': datetime.date.today().isoformat(),
    }


def _antikka_attributes(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract the WooCommerce product attribute table as a {label: value} dict."""
    attrs: Dict[str, str] = {}
    for row in soup.select('tr.woocommerce-product-attributes-item'):
        label = row.find('th')
        value = row.find('td')
        if label and value:
            attrs[label.get_text(strip=True)] = value.get_text(' ', strip=True)
    return attrs


def _scrape_antikka(url: str) -> Dict[str, Any]:
    """Scrape a single antikka.net (WooCommerce) product page and return price fields.

    Returns the fields the manual path needs (book_id, price, condition,
    last_updated) plus the edition-matching metadata parsed from the product
    attribute table (year/version/binding, title/author/language) so the same
    scraper feeds the automatic fetch flow.
    """
    resp = requests.get(url, headers={'User-Agent': _UA}, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')

    price: Optional[float] = None
    price_el = soup.select_one('p.price .woocommerce-Price-amount')
    if price_el:
        raw = price_el.get_text(strip=True).replace('\xa0', '').replace('€', '').replace(',', '.').strip()
        try:
            price = float(raw)
        except ValueError:
            pass

    book_id: Optional[str] = None
    sku_el = soup.select_one('span.sku')
    if sku_el:
        book_id = sku_el.get_text(strip=True) or None

    attrs = _antikka_attributes(soup)

    # Condition: "K3 (hyvä)" -> "K3"
    condition: Optional[str] = None
    kunto = attrs.get('Kuntoluokka', '')
    m = re.match(r'(K[1-5])', kunto)
    if m:
        condition = m.group(1)

    # Year: "1976" (may be "1976-1977" or contain extra text)
    year: Optional[int] = None
    painovuosi = attrs.get('Painovuosi', '')
    ym = re.search(r'\d{4}', painovuosi)
    if ym:
        year = int(ym.group())

    # Painos (print run number): "1.p" -> 1. Absent when the seller omits it.
    version = _parse_version(attrs.get('Painos', ''))

    # Binding from "Sidosasu": "nidottu" / "Sidottu, kuvakansi"
    binding = _binding_category(attrs.get('Sidosasu', ''))

    title_el = soup.select_one('h1.product_title')

    # Seller: the anchor right after the "Myyjä:" label in the product meta.
    seller: Optional[str] = None
    seller_url: Optional[str] = None
    meta = soup.select_one('.product_meta')
    if meta:
        label = meta.find(string=lambda s: bool(s) and 'Myyjä' in s)
        if label:
            seller_a = label.find_next('a')
            if seller_a:
                seller = seller_a.get_text(strip=True) or None
                seller_url = seller_a.get('href') or None

    return {
        'book_id': book_id,
        'price': price,
        'condition': condition,
        'year': year,
        'version': version,
        'binding': binding,
        'title': (title_el.get_text(strip=True) if title_el else None),
        'author': attrs.get('Tekijä') or None,
        'language': attrs.get('Kieli') or None,
        'seller': seller,
        'seller_url': seller_url,
        # Antikka exposes no per-listing date; use the fetch date.
        'last_updated': datetime.date.today().isoformat(),
    }


def scrape_price_from_url(url: str) -> ResponseType:
    """Identify source from URL, scrape price fields, return for user review."""
    session = new_session()
    try:
        source = _source_from_url(url, session)
        if not source:
            return ResponseType('Tunnistamaton lähde', HttpResponseCode.BAD_REQUEST)

        scrapers = {
            'Antikvariaatti': _scrape_antikvariaatti,
            'Antikka': _scrape_antikka,
        }
        scraper = scrapers.get(source.name)
        if not scraper:
            return ResponseType(
                f'Scraperiä ei ole vielä toteutettu lähteelle {source.name}',
                HttpResponseCode.BAD_REQUEST,
            )

        fields = scraper(url)
        return ResponseType(
            {**fields, 'source_id': source.id, 'source_name': source.name},
            HttpResponseCode.OK,
        )
    except requests.RequestException as e:
        return ResponseType(f'Sivun haku epäonnistui: {e}', HttpResponseCode.INTERNAL_SERVER_ERROR)
    finally:
        session.close()


def price_sources_get() -> ResponseType:
    """Return all price sources for use in dropdowns."""
    session = new_session()
    try:
        sources = session.query(PriceSource).order_by(PriceSource.id).all()
        return ResponseType(
            [{'id': s.id, 'name': s.name} for s in sources],
            HttpResponseCode.OK,
        )
    finally:
        session.close()


def price_add_manual(edition_id: int, data: Dict[str, Any]) -> ResponseType:
    """Insert a single manually entered price row."""
    session = new_session()
    try:
        edition = session.query(Edition).filter(Edition.id == edition_id).first()
        if not edition:
            return ResponseType('Edition not found', HttpResponseCode.NOT_FOUND)

        source_id = data.get('source_id')
        if not source_id:
            return ResponseType('source_id required', HttpResponseCode.BAD_REQUEST)
        source = session.query(PriceSource).filter(PriceSource.id == source_id).first()
        if not source:
            return ResponseType('Unknown source', HttpResponseCode.BAD_REQUEST)

        condition = data.get('condition', '')
        if condition not in ('K5', 'K4', 'K3', 'K2', 'K1'):
            return ResponseType('Invalid condition', HttpResponseCode.BAD_REQUEST)

        try:
            price = float(data['price'])
        except (KeyError, TypeError, ValueError):
            return ResponseType('Invalid price', HttpResponseCode.BAD_REQUEST)

        last_updated_raw = data.get('last_updated')
        try:
            last_updated = datetime.datetime.fromisoformat(last_updated_raw) if last_updated_raw else None
            if last_updated and last_updated.tzinfo is not None:
                last_updated = last_updated.replace(tzinfo=None)
        except (ValueError, AttributeError):
            last_updated = None

        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        book_id = data.get('book_id') or None
        url = data.get('url') or None

        session.add(AntikvaariPrice(
            edition_id=edition_id,
            source_id=source_id,
            antikvaari_book_id=book_id,
            antikvaari_product_id=None,
            last_updated=last_updated or now,
            date_fetched=now,
            condition=condition,
            is_library_discard=bool(data.get('is_library_discard', False)),
            has_markings=bool(data.get('has_markings', False)),
            missing_dust_cover=bool(data.get('missing_dust_cover', False)),
            price=price,
            url=url,
            seller=data.get('seller') or None,
            seller_url=data.get('seller_url') or None,
        ))
        session.commit()
        return ResponseType({'saved': 1}, HttpResponseCode.OK)
    except Exception as e:
        session.rollback()
        return ResponseType(str(e), HttpResponseCode.INTERNAL_SERVER_ERROR)
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
    # K0 means wishlisted (not owned) — skip condition comparison
    if our_k is None or our_k == 0:
        return 'Good' if level == 'same' else 'Decent'

    their_k = _condition_int(antikvaari_condition)
    if their_k is None:
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
# Internal: close-edition price fallback
# ---------------------------------------------------------------------------

_QUALITY_RANK: Dict[str, int] = {'Perfect': 0, 'Good': 1, 'Decent': 2, 'Poor': 3}
_QUALITY_ORDER: List[str] = ['Perfect', 'Good', 'Decent', 'Poor']


def _downgrade_quality(q: str, levels: int = 1) -> str:
    """Decrease match quality by `levels` steps (floor: Poor)."""
    idx = _QUALITY_ORDER.index(q) if q in _QUALITY_ORDER else len(_QUALITY_ORDER) - 1
    return _QUALITY_ORDER[min(idx + levels, len(_QUALITY_ORDER) - 1)]


def _closest_sibling_prices(
    owned: Edition,
    siblings: List[Edition],
    prices_by_edition: Dict[int, List['AntikvaariPrice']],
) -> Optional[tuple]:
    """Return (sibling_edition, prices, downgrade_levels) or None.

    A sibling qualifies when it shares edition.version (laitos) with owned
    and has a pubyear within 10 years.  Among qualifying siblings:

    - Same binding_id as owned is preferred (1-level downgrade).
    - Any other binding (different or unknown) is the fallback (2-level downgrade).

    Within each group the sibling with the smallest year difference wins.
    """
    if owned.pubyear is None:
        return None
    same_binding: List[tuple] = []
    other_binding: List[tuple] = []
    for sib in siblings:
        if sib.id == owned.id:
            continue
        if sib.version != owned.version:
            continue
        if sib.pubyear is None:
            continue
        diff = abs(sib.pubyear - owned.pubyear)
        if diff > 10:
            continue
        ps = prices_by_edition.get(sib.id)
        if not ps:
            continue
        same = (
            owned.binding_id is not None
            and sib.binding_id is not None
            and sib.binding_id == owned.binding_id
        )
        (same_binding if same else other_binding).append((diff, sib, ps))
    for group, levels in ((same_binding, 1), (other_binding, 2)):
        if group:
            group.sort(key=lambda x: x[0])
            _, sib_ed, sib_ps = group[0]
            return sib_ed, sib_ps, levels
    return None


# ---------------------------------------------------------------------------
# Public: user collection stats
# ---------------------------------------------------------------------------


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
                'price_distribution': [],
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

        # Load ALL editions per work so close-edition price fallback can look at siblings.
        work_editions: Dict[int, List[Edition]] = {}
        for e in session.query(Edition).filter(Edition.work_id.in_(work_ids)).all():
            work_editions.setdefault(e.work_id, []).append(e)

        # Prices for every edition in those works (not just owned ones).
        all_sib_ids = [e.id for eds in work_editions.values() for e in eds]
        prices_by_edition: Dict[int, List[AntikvaariPrice]] = {}
        for p in (
            session.query(AntikvaariPrice)
            .filter(AntikvaariPrice.edition_id.in_(all_sib_ids))
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

            if not edition:
                dist['not_priced'] += 1
                continue

            price_rows = prices_by_edition.get(eid, [])
            use_close = False
            close_edition: Optional[Edition] = None
            close_levels: int = 1

            if not price_rows:
                sibling = _closest_sibling_prices(
                    edition,
                    work_editions.get(edition.work_id, []),
                    prices_by_edition,
                )
                if sibling:
                    close_edition, price_rows, close_levels = sibling
                    use_close = True
                elif edition.work_id in linked_work_ids:
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
                if not price_rows:
                    continue

            best_q: Optional[str] = None
            best_rank = 999
            best_val = float('inf')
            best_updated = None
            best_seller: Optional[str] = None
            best_seller_url: Optional[str] = None

            for p in price_rows:
                q = calculate_match_quality(
                    close_edition if use_close else edition,
                    p.condition,
                    None, None, None,
                    target,
                )
                if use_close:
                    q = _downgrade_quality(q, close_levels)
                rank = _QUALITY_RANK.get(q, 3)
                pval = float(p.price)
                p_ts = p.last_updated.timestamp() if p.last_updated else 0.0
                b_ts = best_updated.timestamp() if best_updated else 0.0
                if rank < best_rank or (rank == best_rank and (p_ts > b_ts or (p_ts == b_ts and pval < best_val))):
                    best_rank, best_val, best_q, best_updated = rank, pval, q, p.last_updated
                    best_seller, best_seller_url = p.seller, p.seller_url

            if best_q is not None:
                priced_count += 1
                total_value += best_val
                dist[best_q] = dist.get(best_q, 0) + 1
                book_prices.append({
                    'edition_id': eid,
                    'price': best_val,
                    'match_quality': best_q,
                    'condition': target or '',
                    'seller': best_seller,
                    'seller_url': best_seller_url,
                })

        _price_ranges = [
            (0,   5,   '< 5 €'),
            (5,   10,  '5–10 €'),
            (10,  20,  '10–20 €'),
            (20,  30,  '20–30 €'),
            (30,  40,  '30–40 €'),
            (40,  50,  '40–50 €'),
            (50,  60,  '50–60 €'),
            (60,  80,  '60–80 €'),
            (80,  100, '80–100 €'),
            (100, None, '≥ 100 €'),
        ]
        price_distribution = [
            {
                'label': label,
                'count': sum(
                    1 for bp in book_prices
                    if bp['price'] >= lo and (hi is None or bp['price'] < hi)
                ),
            }
            for lo, hi, label in _price_ranges
        ]

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
                'seller': entry.get('seller'),
                'seller_url': entry.get('seller_url'),
            })

        no_price_books.sort(key=lambda x: (x['author_str'], x['title']))

        return ResponseType({
            'total_owned': total_owned,
            'priced_count': priced_count,
            'total_value': round(total_value, 2),
            'quality_distribution': dist,
            'price_distribution': price_distribution,
            'top_expensive': top_expensive,
            'no_price_books': no_price_books,
        }, HttpResponseCode.OK)
    finally:
        session.close()
