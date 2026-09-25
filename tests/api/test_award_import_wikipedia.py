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
        name_col=2, data_col_count=5, skip_rows=2)
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


@patch("app.impl_award_import._get")
def test_missing_wikitable_returns_empty_list(mock_get):
    mock_get.return_value = _resp("<html><body>no tables here</body></html>")
    source = WikipediaTableSource(
        url="https://example.invalid/x", match_kind="work",
        author_col=1, title_col=2)
    assert parse_award_wikipedia_table(source) == []
