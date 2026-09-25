"""
Unit tests for the Wikipedia wikitable award scraper
(parse_award_wikipedia_table).

Pure logic tests (no network, no database): feed small hand-built wikitable
HTML snippets replicating the real quirks found scraping the actual pages
(a rowspan'd year cell for a jointly-awarded year, footnote markers baked
into cell text, Nobel's irregular two-row header where the header's own
column count doesn't match its data rows) and check the resulting
ScrapedWinner list.
"""

from unittest.mock import MagicMock, patch

from app.impl_award_import import (
    WikipediaTableSource,
    parse_award_wikipedia_heading_list,
    parse_award_wikipedia_table,
)


def _resp(html: str) -> MagicMock:
    return MagicMock(content=html.encode("utf-8"))


SIMPLE_TABLE = """
<html><body>
<table class="wikitable">
<tr><th>Vuosi</th><th>Kirjailija</th><th>Teos</th><th>Muut ehdokkaat</th></tr>
<tr><td>2001</td><td>Johanna Sinisalo</td><td>Ennen päivänlaskua ei voi</td><td></td></tr>
<tr><td>2002</td><td>Sari Peltoniemi</td><td>Hirvi</td><td></td></tr>
</table>
</body></html>
"""


@patch("app.impl_award_import._get")
def test_simple_four_column_table(mock_get):
    mock_get.return_value = _resp(SIMPLE_TABLE)
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="work",
        author_col=1, title_col=2)
    winners = parse_award_wikipedia_table(source)
    assert [(w.year, w.title, w.author) for w in winners] == [
        (2001, "Ennen päivänlaskua ei voi", "Johanna Sinisalo"),
        (2002, "Hirvi", "Sari Peltoniemi"),
    ]


ROWSPAN_JOINT_YEAR_TABLE = """
<html><body>
<table class="wikitable">
<tr><th>Vuosi</th><th>Palkinnonsaaja</th><th>Teos</th><th>Muut ehdokkaat</th></tr>
<tr><td rowspan="2">1973</td><td>Kirsi Kunnas</td><td>Puupuu ja Kärypoika</td><td></td></tr>
<tr><td>Paavo Rintala</td><td>Uu ja Poikanen</td><td></td></tr>
<tr><td>1974</td><td>Someone Else</td><td>Some Title</td><td></td></tr>
</table>
</body></html>
"""


@patch("app.impl_award_import._get")
def test_rowspan_joint_year_row_inherits_pending_year(mock_get):
    # The second 1973 row has only 3 cells (missing the rowspan'd year
    # cell), so its real columns are shifted left by one relative to the
    # 4-cell header/full-row shape.
    mock_get.return_value = _resp(ROWSPAN_JOINT_YEAR_TABLE)
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="work",
        author_col=1, title_col=2)
    winners = parse_award_wikipedia_table(source)
    assert [(w.year, w.title, w.author) for w in winners] == [
        (1973, "Puupuu ja Kärypoika", "Kirsi Kunnas"),
        (1973, "Uu ja Poikanen", "Paavo Rintala"),
        (1974, "Some Title", "Someone Else"),
    ]


FOOTNOTE_AND_TRAILING_PUNCTUATION_TABLE = """
<html><body>
<table class="wikitable">
<tr><th>Vuosi</th><th>Kirjailija</th><th>Teos</th></tr>
<tr><td>2026 <sup>[27]</sup></td><td>Mirjam Polkunen:</td><td>Some Title <sup>[63]</sup></td></tr>
</table>
</body></html>
"""


@patch("app.impl_award_import._get")
def test_footnotes_and_trailing_punctuation_are_stripped(mock_get):
    mock_get.return_value = _resp(FOOTNOTE_AND_TRAILING_PUNCTUATION_TABLE)
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="work",
        author_col=1, title_col=2)
    winners = parse_award_wikipedia_table(source)
    assert len(winners) == 1
    assert winners[0].year == 2026
    assert winners[0].author == "Mirjam Polkunen"
    assert winners[0].title == "Some Title"


# Nobel-shaped table: a two-row header (row 0 has 4 cells, row 1 - the
# "Image | Name" sub-header - has 2), then 5-cell data rows (an empty
# leading "image" cell), a rowspan'd joint year, and a "Not awarded" gap
# whose continuation rows have only a single (year) cell.
NOBEL_SHAPED_TABLE = """
<html><body>
<table class="wikitable">
<tr><th>Year</th><th>Laureate</th><th>Country</th><th>Citation</th></tr>
<tr><th>Image</th><th>Name</th></tr>
<tr><td>1901</td><td></td><td>Sully Prudhomme (1839-1907)</td><td>France</td><td>"citation"</td></tr>
<tr><td rowspan="2">1904</td><td></td><td>Frédéric Mistral (1830-1914)</td><td>France</td><td>"citation"</td></tr>
<tr><td></td><td>José Echegaray (1832-1916)</td><td>Spain</td><td>"citation"</td></tr>
<tr><td>1940</td><td colspan="4">Not awarded</td></tr>
<tr><td>1941</td></tr>
<tr><td>1949</td><td></td><td>William Faulkner (1897-1962)</td><td>United States</td><td>"citation"</td></tr>
</table>
</body></html>
"""


@patch("app.impl_award_import._get")
def test_nobel_shaped_table_with_joint_year_and_not_awarded_gap(mock_get):
    mock_get.return_value = _resp(NOBEL_SHAPED_TABLE)
    source = WikipediaTableSource(
        url="https://example.invalid/nobel", match_kind="person",
        name_col=2, skip_rows=2)
    winners = parse_award_wikipedia_table(source)
    # 1940/1941 (no laureate at all) must be silently skipped; the lifespan
    # suffix must be stripped from each name.
    assert [(w.year, w.title) for w in winners] == [
        (1901, "Sully Prudhomme"),
        (1904, "Frédéric Mistral"),
        (1904, "José Echegaray"),
        (1949, "William Faulkner"),
    ]
    assert all(w.author == "" for w in winners)


TRAILING_MISSING_COLUMN_TABLE = """
<html><body>
<table class="wikitable">
<tr><th>Vuosi</th><th>Tekijä</th><th>Novelli</th><th>Julkaistu</th><th>Lisätietoa</th></tr>
<tr><td>2023</td><td>Hanna-Kaisa Kärpinlehto</td><td>Asuttajat</td><td></td><td></td></tr>
<tr><td>2024</td><td>Anssi Vartiainen</td><td>Patinamorsian</td><td></td></tr>
</table>
</body></html>
"""


@patch("app.impl_award_import._get")
def test_row_missing_an_unused_trailing_column_is_not_treated_as_a_rowspan_continuation(mock_get):
    # Regression: the newest entry on the real Portti page has no
    # "Lisätietoa" cell filled in yet, so its row has one fewer cell than
    # every other row - by cell-count alone this looks identical to a
    # rowspan continuation (which is also short by one cell), but here
    # nothing has a rowspan at all, and the missing cell is an unused
    # trailing column, not the leading year cell. Wrongly treating this as
    # a continuation would misread "2024" as the year cell shifted out and
    # try to reuse the previous row's year (2023) instead.
    mock_get.return_value = _resp(TRAILING_MISSING_COLUMN_TABLE)
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="short",
        author_col=1, title_col=2)
    winners = parse_award_wikipedia_table(source)
    assert [(w.year, w.title, w.author) for w in winners] == [
        (2023, "Asuttajat", "Hanna-Kaisa Kärpinlehto"),
        (2024, "Patinamorsian", "Anssi Vartiainen"),
    ]


@patch("app.impl_award_import._get")
def test_missing_wikitable_returns_empty_list(mock_get):
    mock_get.return_value = _resp("<html><body>no tables here</body></html>")
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="work",
        author_col=1, title_col=2)
    assert parse_award_wikipedia_table(source) == []


# Modern Wikipedia wraps each heading in a <div class="mw-heading">, with
# the <ul> as that div's sibling (with a <p> or two often in between) - not
# a sibling of the heading tag itself, as an older/simpler layout would be.
HEADING_LIST_PAGE = """
<html><body><div class="mw-parser-output">
<div class="mw-heading mw-heading2"><h2 id="Toiminta">Toiminta</h2></div>
<p>Some unrelated paragraph.</p>
<div class="mw-heading mw-heading2"><h2 id="Kosmoskynä-palkinto">Kosmoskynä-palkinto</h2></div>
<p>Intro paragraph before the list.</p>
<ul>
<li>1985: Kari Mäentaka</li>
<li>1987: Tom Ölander</li>
<li>1996: Turun science fiction -seura</li>
<li>2018 <sup>[9]</sup>: Jukka Halme</li>
</ul>
<div class="mw-heading mw-heading2"><h2 id="Lähteet">Lähteet</h2></div>
<ul><li>Some unrelated reference, not part of the award list.</li></ul>
</div></body></html>
"""


@patch("app.impl_award_import._get")
def test_heading_list_reads_only_its_own_sections_list(mock_get):
    mock_get.return_value = _resp(HEADING_LIST_PAGE)
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="person",
        layout="heading_list", heading_id="Kosmoskynä-palkinto")
    winners = parse_award_wikipedia_heading_list(source)
    assert [(w.year, w.title) for w in winners] == [
        (1985, "Kari Mäentaka"),
        (1987, "Tom Ölander"),
        (1996, "Turun science fiction -seura"),
        (2018, "Jukka Halme"),
    ]


@patch("app.impl_award_import._get")
def test_heading_list_missing_heading_returns_empty_list(mock_get):
    mock_get.return_value = _resp(HEADING_LIST_PAGE)
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="person",
        layout="heading_list", heading_id="No-Such-Heading")
    assert parse_award_wikipedia_heading_list(source) == []
