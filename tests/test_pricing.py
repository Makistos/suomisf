"""
Tests for Antikvaari pricing scraper (impl_pricing module).

Unit tests cover all parsing helpers and match quality calculation.
Scraper tests mock HTTP and DB to verify field extraction from page data.

Test data sourced from manually verified Antikvaari product pages.
"""
import datetime
import json
from unittest.mock import MagicMock, patch

from app.impl_pricing import (
    _is_changed,
    _parse_condition,
    _parse_version,
    _binding_category,
    _best_matching_edition,
    _condition_int,
    calculate_match_quality,
    antikvaari_fetch_products,
    antikvaari_prices_save,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _mock_edition(edition_id, pubyear=None, version=None, binding_id=1, editionnum=None):
    ed = MagicMock()
    ed.id = edition_id
    ed.pubyear = pubyear
    ed.version = version
    ed.editionnum = editionnum
    ed.binding_id = binding_id
    return ed


def _mock_work_session(mock_new_session, editions):
    session = MagicMock()
    mock_new_session.return_value = session
    work = MagicMock()
    work.editions = editions
    session.query.return_value.filter.return_value.first.return_value = work
    return session


def _product_props(product_id, book_urls, year='1982', binding='Sidottu'):
    return {
        'catalog': {'_id': product_id, 'year': year, 'binding': binding},
        'dataFeed': {
            'dataFeedElement': [{
                '@type': 'Book',
                'workExample': [
                    {'potentialAction': {'target': {'urlTemplate': u}}}
                    for u in book_urls
                ],
            }]
        },
    }


def _book_props(book_id, kunto, hinta, painos, painovuosi, sidonta, pvm, extra=''):
    return {
        'preSelectedProduct': {
            '_id': book_id,
            'kunto': kunto,
            'hinta': hinta,
            'painos': painos,
            'painovuosi': painovuosi,
            'sidonta': sidonta,
            'pvm': pvm,
            'nimikeLisatiedot': extra,
        }
    }


def _resp(page_props):
    r = MagicMock()
    r.text = (
        '<html><body><script id="__NEXT_DATA__">'
        + json.dumps({'props': {'pageProps': page_props}})
        + '</script></body></html>'
    )
    r.raise_for_status.return_value = None
    return r


BASE = 'https://www.antikvaari.fi'


# ---------------------------------------------------------------------------
# _parse_condition
# ---------------------------------------------------------------------------

class TestParseCondition:
    def test_strips_minus(self):
        assert _parse_condition('K4-') == 'K4'

    def test_strips_plus(self):
        assert _parse_condition('K5+') == 'K5'

    def test_no_suffix_unchanged(self):
        assert _parse_condition('K3') == 'K3'

    def test_uusi_maps_to_k5(self):
        assert _parse_condition('Uusi') == 'K5'

    def test_uusi_lowercase(self):
        assert _parse_condition('uusi') == 'K5'

    def test_empty_string(self):
        assert _parse_condition('') == ''

    def test_none(self):
        assert _parse_condition(None) == ''

    def test_k1(self):
        assert _parse_condition('K1') == 'K1'

    def test_k2_minus(self):
        assert _parse_condition('K2-') == 'K2'


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------

class TestParseVersion:
    def test_bare_digit(self):
        assert _parse_version('2') == 2

    def test_dot_suffix(self):
        assert _parse_version('1.') == 1

    def test_painos_suffix(self):
        assert _parse_version('3. painos') == 3

    def test_p_dot_suffix(self):
        assert _parse_version('1.p.') == 1

    def test_fourth_edition(self):
        assert _parse_version('4.') == 4

    def test_none_returns_none(self):
        assert _parse_version(None) is None

    def test_empty_returns_none(self):
        assert _parse_version('') is None

    def test_non_numeric_returns_none(self):
        assert _parse_version('painos') is None


# ---------------------------------------------------------------------------
# _binding_category
# ---------------------------------------------------------------------------

class TestBindingCategory:
    def test_sidottu(self):
        assert _binding_category('Sidottu') == 3

    def test_sidottu_kuvakansi(self):
        assert _binding_category('Sidottu, kuvakansi') == 3

    def test_nidottu(self):
        assert _binding_category('Nidottu') == 2

    def test_nidottu_kansikuva(self):
        assert _binding_category('Nidottu, kansikuva') == 2

    def test_pokkari_is_nidottu(self):
        assert _binding_category('Pokkari') == 2

    def test_empty_returns_none(self):
        assert _binding_category('') is None

    def test_none_returns_none(self):
        assert _binding_category(None) is None

    def test_unknown_returns_none(self):
        assert _binding_category('Kierreselkä') is None


# ---------------------------------------------------------------------------
# _condition_int
# ---------------------------------------------------------------------------

class TestConditionInt:
    def test_k1(self):
        assert _condition_int('K1') == 1

    def test_k2(self):
        assert _condition_int('K2') == 2

    def test_k3(self):
        assert _condition_int('K3') == 3

    def test_k4(self):
        assert _condition_int('K4') == 4

    def test_k5(self):
        assert _condition_int('K5') == 5

    def test_empty_returns_none(self):
        assert _condition_int('') is None

    def test_none_returns_none(self):
        assert _condition_int(None) is None


# ---------------------------------------------------------------------------
# date_listed derived from MongoDB ObjectID
# ---------------------------------------------------------------------------

class TestObjectIdDateListed:
    """date_listed is the creation timestamp from the first 4 bytes of _id."""

    @staticmethod
    def _decode(book_id):
        ts = int(book_id[:8], 16)
        return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).date()

    def test_6197d6fe_is_2021_11_19(self):
        assert self._decode('6197d6feb8b7303195c91487') == datetime.date(2021, 11, 19)

    def test_65c34426_is_2024_02_07(self):
        assert self._decode('65c34426b1311b23ec82131d') == datetime.date(2024, 2, 7)

    def test_672e0b51_is_2024_11_08(self):
        assert self._decode('672e0b5151f2ad0a9bb33b7c') == datetime.date(2024, 11, 8)

    def test_6737ae37_is_2024_11_15(self):
        assert self._decode('6737ae37254745df8aaa9007') == datetime.date(2024, 11, 15)

    def test_68a1a84e_is_2025_08_17(self):
        assert self._decode('68a1a84e7d36eb8405722d3e') == datetime.date(2025, 8, 17)

    def test_69037c5a_is_2025_10_30(self):
        assert self._decode('69037c5a5d37a4c948eaa49c') == datetime.date(2025, 10, 30)

    def test_6895d135_is_2025_08_08(self):
        assert self._decode('6895d135d9fceb5ff77847ef') == datetime.date(2025, 8, 8)

    def test_68bd7ddb_is_2025_09_07(self):
        assert self._decode('68bd7ddb532965878261c0e4') == datetime.date(2025, 9, 7)

    def test_69ce0802_is_2026_04_02(self):
        assert self._decode('69ce08025c22336bb3fc1e36') == datetime.date(2026, 4, 2)

    def test_69f14ee2_is_2026_04_29(self):
        assert self._decode('69f14ee2852c31277c813c9a') == datetime.date(2026, 4, 29)


# ---------------------------------------------------------------------------
# calculate_match_quality
# ---------------------------------------------------------------------------

class TestCalculateMatchQuality:
    """
    Match quality matrix:
      same  + diff=0  → Perfect
      same  + diff=1  → Good
      same  + diff≥2  → Decent
      close + diff=0  → Good
      close + diff=1  → Decent
      close + diff≥2  → Poor
      not_close       → Poor  (regardless of condition)
    """

    def _ed(self, pubyear=1982, editionnum=1, binding_id=3):
        return _mock_edition(1, pubyear=pubyear, editionnum=editionnum, binding_id=binding_id)

    # same edition

    def test_same_diff0_is_perfect(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, 1, 3, 'K3') == 'Perfect'

    def test_same_diff1_is_good(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, 1, 3, 'K2') == 'Good'

    def test_same_diff2_is_decent(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, 1, 3, 'K1') == 'Decent'

    # close edition (year diff 1–10, same version+binding)

    def test_close_diff0_is_good(self):
        assert calculate_match_quality(self._ed(), 'K3', 1985, 1, 3, 'K3') == 'Good'

    def test_close_diff1_is_decent(self):
        assert calculate_match_quality(self._ed(), 'K3', 1985, 1, 3, 'K2') == 'Decent'

    def test_close_diff2_is_poor(self):
        assert calculate_match_quality(self._ed(), 'K3', 1985, 1, 3, 'K1') == 'Poor'

    # not_close

    def test_year_diff_over_10_is_poor(self):
        assert calculate_match_quality(self._ed(), 'K3', 2000, 1, 3, 'K3') == 'Poor'

    def test_wrong_version_is_poor(self):
        assert calculate_match_quality(self._ed(editionnum=1), 'K3', 1982, 2, 3, 'K3') == 'Poor'

    def test_wrong_binding_is_poor(self):
        ed = self._ed(binding_id=3)  # sidottu
        assert calculate_match_quality(ed, 'K3', 1982, 1, 2, 'K3') == 'Poor'  # 2=nidottu

    # no target condition

    def test_no_target_same_edition_is_good(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, 1, 3, None) == 'Good'

    def test_no_target_close_edition_is_decent(self):
        assert calculate_match_quality(self._ed(), 'K3', 1985, 1, 3, None) == 'Decent'

    def test_no_target_not_close_is_poor(self):
        assert calculate_match_quality(self._ed(), 'K3', 2000, 1, 3, None) == 'Poor'

    # uusi = K5
    def test_uusi_condition_in_antikvaari_treated_as_k5(self):
        # book is K5 (Uusi), we want K4 → diff=1 on same edition → Good
        assert calculate_match_quality(self._ed(), 'K5', 1982, 1, 3, 'K4') == 'Good'

    # no version from Antikvaari (painos field empty) -------------------------
    # year+binding both confirmed → 'same' → can reach Perfect/Good/Decent
    def test_no_version_year_and_binding_match_same_condition_is_perfect(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, None, 3, 'K3') == 'Perfect'

    def test_no_version_year_and_binding_match_diff1_is_good(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, None, 3, 'K2') == 'Good'

    # year matches but binding unknown → 'close' → best is Good
    def test_no_version_year_match_binding_unknown_is_good_on_same_condition(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, None, None, 'K3') == 'Good'

    # year matches but binding unknown, condition diff=1 → 'close' + diff=1 → Decent
    def test_no_version_year_match_binding_unknown_diff1_is_decent(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, None, None, 'K2') == 'Decent'

    # year matches but Antikvaari binding is 'Ei tietoa' (1) → not confirmed → 'close'
    def test_no_version_binding_ei_tietoa_is_close(self):
        assert calculate_match_quality(self._ed(), 'K3', 1982, None, 1, 'K3') == 'Good'

    # no year and no version → 'close' → best is Good
    def test_no_version_no_year_is_close(self):
        assert calculate_match_quality(self._ed(), 'K3', None, None, 3, 'K3') == 'Good'


# ---------------------------------------------------------------------------
# _best_matching_edition — inferred version ranking
# ---------------------------------------------------------------------------

class TestBestMatchingEdition:
    """When editions have no stored editionnum, infer rank by chronological pubyear."""

    def _ed(self, edition_id, pubyear, editionnum=None, binding_id=2):
        return _mock_edition(edition_id, pubyear=pubyear, editionnum=editionnum, binding_id=binding_id)

    def test_first_edition_product_matches_earliest_edition_when_editionnums_null(self):
        # Two editions with no stored editionnum; product says "1. painos" → should pick 2016
        ed_2016 = self._ed(1, 2016)
        ed_2018 = self._ed(2, 2018)
        result, _ = _best_matching_edition([ed_2016, ed_2018],
                                           product_year=2018, product_version=1, product_binding=2)
        assert result.id == 1  # 2016 edition = inferred editionnum 1

    def test_second_edition_product_matches_later_edition_when_editionnums_null(self):
        ed_2016 = self._ed(1, 2016)
        ed_2018 = self._ed(2, 2018)
        result, _ = _best_matching_edition([ed_2016, ed_2018],
                                           product_year=2016, product_version=2, product_binding=2)
        assert result.id == 2  # 2018 edition = inferred editionnum 2

    def test_explicit_editionnum_takes_precedence_over_inferred(self):
        # Edition has explicit editionnum=2; product says version=1 → not_close for this one
        ed_e2 = _mock_edition(1, pubyear=2018, editionnum=2, binding_id=2)
        ed_null = _mock_edition(2, pubyear=2016, editionnum=None, binding_id=2)
        result, _ = _best_matching_edition([ed_e2, ed_null],
                                           product_year=2016, product_version=1, product_binding=2)
        # ed_null gets inferred editionnum 1 (earliest year 2016) and matches
        assert result.id == 2

    def test_no_product_version_uses_year_matching_as_before(self):
        ed_2016 = self._ed(1, 2016)
        ed_2018 = self._ed(2, 2018)
        result, _ = _best_matching_edition([ed_2016, ed_2018],
                                           product_year=2018, product_version=None, product_binding=2)
        # No version from Antikvaari → no inferred ranking; year=2018 exact match wins
        assert result.id == 2


# ---------------------------------------------------------------------------
# antikvaari_fetch_products — mocked HTTP + DB
# ---------------------------------------------------------------------------

class TestAntikvaariScraper:

    WORK_ID = 4355

    # --- helpers ---

    @staticmethod
    def _single_product_call(mock_get, mock_new_session, edition,
                              product_id, book_id, kunto, hinta, painos,
                              painovuosi, sidonta, pvm, extra='',
                              product_binding='Sidottu', product_year=None):
        _mock_work_session(mock_new_session, [edition])
        book_url = f'{BASE}/k/test/{book_id}'
        product_url = f'{BASE}/teos/test/{product_id}'
        mock_get.side_effect = [
            _resp(_product_props(product_id, [book_url],
                                 year=product_year or painovuosi,
                                 binding=product_binding)),
            _resp(_book_props(book_id, kunto, hinta, painos,
                              painovuosi, sidonta, pvm, extra)),
        ]
        return antikvaari_fetch_products([product_url], TestAntikvaariScraper.WORK_ID)

    # --- basic field extraction ---

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_basic_fields_first_book(self, mock_get, mock_new_session):
        """Pimeät valovuodet book 6197d6fe: K3, 10€, sidottu, no flags."""
        ed = _mock_edition(4987, pubyear=1982, version=1, binding_id=3)
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a38f38eaa1ec176c40b868',
            book_id='6197d6feb8b7303195c91487',
            kunto='K3', hinta=10, painos='1.', painovuosi='1982',
            sidonta='Sidottu, kuvakansi',
            pvm='2022-11-05T20:17:10.942Z',
        )
        assert result.status == 200
        row = result.response[0]
        assert row['condition'] == 'K3'
        assert float(row['price']) == 10.0
        assert row['antikvaari_book_id'] == '6197d6feb8b7303195c91487'
        assert row['edition_id'] == 4987
        assert row['is_library_discard'] is False
        assert row['has_markings'] is False
        assert row['missing_dust_cover'] is False
        assert row['date_listed'] == '2021-11-19'
        assert row['last_updated'] is not None
        assert row['last_updated'][:10] == '2022-11-05'

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_condition_minus_stripped(self, mock_get, mock_new_session):
        """K4- is stored as K4."""
        ed = _mock_edition(4987, pubyear=1982, version=1, binding_id=3)
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a38f38eaa1ec176c40b868',
            book_id='6974d8364680bdafb31eb10f',
            kunto='K4-', hinta=17, painos='1.', painovuosi='1982',
            sidonta='Sidottu, kuvakansi',
            pvm='2026-01-24T00:00:00.000Z',
        )
        assert result.response[0]['condition'] == 'K4'
        assert result.response[0]['date_listed'] == '2026-01-24'

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_uusi_stored_as_k5(self, mock_get, mock_new_session):
        """'Uusi' condition is stored as K5."""
        ed = _mock_edition(2062, pubyear=1985, version=2, binding_id=2)
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a4ad1aeaa1ec176c5017ee',
            book_id='69037c5a5d37a4c948eaa49c',
            kunto='Uusi', hinta=19, painos='2.', painovuosi='1985',
            sidonta='Nidottu',
            pvm='2026-02-24T00:00:00.000Z',
            product_binding='Nidottu',
        )
        assert result.response[0]['condition'] == 'K5'
        assert result.response[0]['date_listed'] == '2025-10-30'

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_library_discard_and_markings(self, mock_get, mock_new_session):
        """'kirjaston poistotuote' and 'merkintöjä' set the correct flags."""
        ed = _mock_edition(4987, pubyear=1982, version=1, binding_id=3)
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a38f38eaa1ec176c40b868',
            book_id='687109dc4b0c838f7706130b',
            kunto='K2', hinta=12, painos='1.', painovuosi='1982',
            sidonta='Sidottu, kuvakansi',
            pvm='2025-07-11T00:00:00.000Z',
            extra='kirjaston poistotuote, merkintöjä',
        )
        row = result.response[0]
        assert row['is_library_discard'] is True
        assert row['has_markings'] is True
        assert row['missing_dust_cover'] is False

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_missing_dust_cover(self, mock_get, mock_new_session):
        """'ei kansipaperia' sets missing_dust_cover=True."""
        ed = _mock_edition(5736, pubyear=1990, version=2, binding_id=3)
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a65ff6eaa1ec176c63eb9b',
            book_id='672e0b5151f2ad0a9bb33b7c',
            kunto='K3', hinta=15, painos='2.', painovuosi='1990',
            sidonta='Sidottu, kuvakansi',
            pvm='2024-11-08T00:00:00.000Z',
            extra='ei kansipaperia',
        )
        row = result.response[0]
        assert row['missing_dust_cover'] is True
        assert row['is_library_discard'] is False
        assert row['has_markings'] is False
        assert row['date_listed'] == '2024-11-08'

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_pokkari_matches_nidottu_edition(self, mock_get, mock_new_session):
        """Pokkari binding matches a nidottu edition → Perfect on same year+version."""
        ed = _mock_edition(6170, pubyear=2000, version=4, binding_id=2)  # nidottu
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a33bb4eaa1ec176c3aee27',
            book_id='68bd7ddb532965878261c0e4',
            kunto='K3', hinta=9, painos='4.', painovuosi='2000',
            sidonta='Pokkari',
            pvm='2025-09-07T00:00:00.000Z',
            product_binding='Pokkari', product_year='2000',
        )
        row = result.response[0]
        # Pokkari = nidottu → binding matches edition → 'same' level
        # No target_condition supplied → max is 'Good' (not 'Perfect')
        assert row['match_quality'] == 'Good'

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_last_updated_differs_from_date_listed(self, mock_get, mock_new_session):
        """When pvm differs from creation date, both fields reflect correct values."""
        ed = _mock_edition(4987, pubyear=1982, version=1, binding_id=3)
        result = self._single_product_call(
            mock_get, mock_new_session, ed,
            product_id='62a38f38eaa1ec176c40b868',
            book_id='68a1a84e7d36eb8405722d3e',  # date_listed = 2025-08-17
            kunto='K4', hinta=20, painos='1.', painovuosi='1982',
            sidonta='Sidottu, kuvakansi',
            pvm='2026-01-04T00:00:00.000Z',     # last_updated = 2026-01-04
        )
        row = result.response[0]
        assert row['date_listed'] == '2025-08-17'
        assert row['last_updated'][:10] == '2026-01-04'

    @patch('app.impl_pricing.new_session')
    @patch('app.impl_pricing.requests.get')
    def test_multiple_books_in_product(self, mock_get, mock_new_session):
        """All books in a multi-copy product are returned as separate rows."""
        ed = _mock_edition(4987, pubyear=1982, version=1, binding_id=3)
        _mock_work_session(mock_new_session, [ed])

        product_id = '62a38f38eaa1ec176c40b868'
        books = [
            ('6197d6feb8b7303195c91487', 'K3', 10),
            ('6737ae37254745df8aaa9007', 'K3', 12),
        ]
        book_urls = [f'{BASE}/k/test/{bid}' for bid, _, _ in books]
        product_url = f'{BASE}/teos/test/{product_id}'

        mock_get.side_effect = [
            _resp(_product_props(product_id, book_urls)),
            _resp(_book_props(books[0][0], books[0][1], books[0][2],
                              '1.', '1982', 'Sidottu', '2022-11-05T00:00:00.000Z')),
            _resp(_book_props(books[1][0], books[1][1], books[1][2],
                              '1.', '1982', 'Sidottu', '2024-11-15T00:00:00.000Z')),
        ]

        result = antikvaari_fetch_products([product_url], self.WORK_ID)
        assert result.status == 200
        assert len(result.response) == 2
        ids = {r['antikvaari_book_id'] for r in result.response}
        assert ids == {books[0][0], books[1][0]}


# ---------------------------------------------------------------------------
# _is_changed — change detection
# ---------------------------------------------------------------------------

def _existing_price(condition='K3', price=10.0, is_library_discard=False,
                    has_markings=False, missing_dust_cover=False,
                    last_updated=None):
    """Build a mock AntikvaariPrice with the given field values."""
    p = MagicMock()
    p.condition = condition
    p.price = price
    p.is_library_discard = is_library_discard
    p.has_markings = has_markings
    p.missing_dust_cover = missing_dust_cover
    p.last_updated = last_updated
    return p


_DT = datetime.datetime(2022, 11, 5, 20, 17, 10)
_ROW = {
    'condition': 'K3',
    'price': 10.0,
    'is_library_discard': False,
    'has_markings': False,
    'missing_dust_cover': False,
}


class TestIsChanged:

    def test_identical_row_is_not_changed(self):
        existing = _existing_price(last_updated=_DT)
        assert _is_changed(existing, _DT, _ROW) is False

    def test_same_last_updated_with_microseconds_is_not_changed(self):
        dt_with_ms = _DT.replace(microsecond=942000)
        existing = _existing_price(last_updated=_DT)
        assert _is_changed(existing, dt_with_ms, _ROW) is False

    def test_different_last_updated_is_changed(self):
        newer = datetime.datetime(2023, 6, 1, 12, 0, 0)
        existing = _existing_price(last_updated=_DT)
        assert _is_changed(existing, newer, _ROW) is True

    def test_price_change_is_detected(self):
        existing = _existing_price(price=10.0, last_updated=_DT)
        row = {**_ROW, 'price': 12.0}
        assert _is_changed(existing, _DT, row) is True

    def test_condition_change_is_detected(self):
        existing = _existing_price(condition='K3', last_updated=_DT)
        row = {**_ROW, 'condition': 'K2'}
        assert _is_changed(existing, _DT, row) is True

    def test_library_discard_flag_change_is_detected(self):
        existing = _existing_price(is_library_discard=False, last_updated=_DT)
        row = {**_ROW, 'is_library_discard': True}
        assert _is_changed(existing, _DT, row) is True

    def test_markings_flag_change_is_detected(self):
        existing = _existing_price(has_markings=False, last_updated=_DT)
        row = {**_ROW, 'has_markings': True}
        assert _is_changed(existing, _DT, row) is True

    def test_missing_dust_cover_change_is_detected(self):
        existing = _existing_price(missing_dust_cover=False, last_updated=_DT)
        row = {**_ROW, 'missing_dust_cover': True}
        assert _is_changed(existing, _DT, row) is True

    def test_both_last_updated_none_is_not_changed(self):
        existing = _existing_price(last_updated=None)
        assert _is_changed(existing, None, _ROW) is False

    def test_new_last_updated_none_existing_not_none_is_changed(self):
        existing = _existing_price(last_updated=_DT)
        assert _is_changed(existing, None, _ROW) is True


class TestAntikvaariPricesSave:
    """Tests for change-detected append-only save logic."""

    @staticmethod
    def _make_session(mock_new_session, existing_price=None):
        session = MagicMock()
        mock_new_session.return_value = session
        edition = MagicMock()
        edition.id = 4987
        # edition query: .filter().first()
        session.query.return_value.filter.return_value.first.return_value = edition
        # price query: .filter().filter().order_by().first()
        (session.query.return_value.filter.return_value
         .filter.return_value.order_by.return_value.first.return_value) = existing_price
        return session

    @patch('app.impl_pricing.new_session')
    def test_new_book_is_saved(self, mock_new_session):
        """No existing row → row is inserted."""
        session = self._make_session(mock_new_session, existing_price=None)
        result = antikvaari_prices_save(4987, [
            {**_ROW, 'antikvaari_book_id': 'abc123',
             'antikvaari_product_id': 'prod1',
             'last_updated': _DT, 'date_listed': '2022-01-01'},
        ])
        assert result.status == 200
        assert result.response['saved'] == 1
        assert result.response['skipped'] == 0
        session.add.assert_called_once()

    @patch('app.impl_pricing.new_session')
    def test_unchanged_book_is_skipped(self, mock_new_session):
        """Existing row with identical data → skipped."""
        existing = _existing_price(last_updated=_DT)
        self._make_session(mock_new_session, existing_price=existing)
        result = antikvaari_prices_save(4987, [
            {**_ROW, 'antikvaari_book_id': 'abc123',
             'antikvaari_product_id': 'prod1',
             'last_updated': _DT, 'date_listed': '2022-01-01'},
        ])
        assert result.response['saved'] == 0
        assert result.response['skipped'] == 1

    @patch('app.impl_pricing.new_session')
    def test_changed_book_creates_new_row(self, mock_new_session):
        """Existing row with different price → new row inserted."""
        existing = _existing_price(price=10.0, last_updated=_DT)
        self._make_session(mock_new_session, existing_price=existing)
        newer = datetime.datetime(2023, 6, 1)
        result = antikvaari_prices_save(4987, [
            {**_ROW, 'price': 15.0, 'antikvaari_book_id': 'abc123',
             'antikvaari_product_id': 'prod1',
             'last_updated': newer, 'date_listed': '2022-01-01'},
        ])
        assert result.response['saved'] == 1
        assert result.response['skipped'] == 0
