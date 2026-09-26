"""
ISFDB award-import helpers.

Scrapes award winners from ISFDB (isfdb.org) award-category pages and
matches them against the local database. Used by the per-award "import
winners from ISFDB" workflow.

Item type convention (matches award_import_source.item_type):
    0 = Work, 1 = Short story, 2 = Both (novella).
This is the ISFDB scraper convention and is distinct from
awardcategory.type (0 = personal, 1 = novel, 2 = short story).

A fourth item type, 3 = Person, exists only for sfadb-sourced awards given
to a person for a body of work rather than to a specific title (e.g. the
SFWA Grand Master Award) - see SFADB_PERSON_AWARD_SLUGS. This is a
deliberate, narrow exception to the "never touch person_id rows" rule that
otherwise applies throughout this module: that rule exists to protect
manually-entered personal-achievement winners on MIXED awards like Sidewise
and World Fantasy (which are mostly title-based, with a personal award
bolted on) from being clobbered by an ordinary title-matching import. It
does not preclude deliberately supporting awards that are *entirely*
person-based, where there is no title to match at all.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from app import app
from app.impl import ResponseType
from app.route_helpers import new_session
from app.orm_decl import (Award, AwardCategory, AwardImportSource, Awarded,
                          Person, ShortStory, StoryContributor, Work,
                          WorkContributor)
from app.types import HttpResponseCode

# Item type constants (award_import_source.item_type).
ITEM_WORK = 0
ITEM_SHORT = 1
ITEM_BOTH = 2
ITEM_PERSON = 3  # sfadb-only; see module docstring.

ISFDB_CATEGORY_URL = "https://www.isfdb.org/cgi-bin/award_category.cgi"

_HEADERS = {
    "User-Agent": "suomisf-award-import/1.0 (+https://www.sf-bibliografia.fi)"
}

# Canonical map: ISFDB award-category name -> local award category name.
# Source of truth for category mapping (ported from scripts/check-awards.py).
# Empty string means intentionally unmapped.
CATEGORY_MAP: Dict[str, str] = {
    "Prix Apollo": "Paras romaani",
    "Superior Achievement in a Novel": "Paras romaani",
    "Superior Achievement in a First Novel": "Paras ensiromaani",
    "Superior Achievement in a Young Adult Novel": "Paras nuortenkirja",
    "Superior Achievement in a Work for Young Readers": "Paras nuortenkirja",
    "Superior Achievement in Long Fiction": "Paras pitkä fiktio",
    "Superior Achievement in a Novella": "Paras pienoisromaani",
    "Superior Achievement in a Novelet": "Paras pitkä novelli",
    "Superior Achievement in Short Fiction": "Paras lyhyt fiktio",
    "Superior Achievement in a Fiction Collection": "Paras kokoelma",
    "Superior Achievement in an Anthology": "Paras antologia",
    "Best Science Fiction Novel": "Paras sf-romaani",
    "Carnegie Medal": "Carnegie-mitali",
    "August Derleth Award for Best Horror Novel": "Paras kauhuromaani",
    "August Derleth Fantasy Award (Best Novel)": "Paras romaani",
    "Robert Holdstock Award for Best Fantasy Novel": "Paras fantasiaromaani",
    "Best Novella": "Paras pienoisromaani",
    "Best Short Fiction": "Paras lyhyt fiktio",
    "Best Short Story": "Paras novelli",
    "Best Collection": "Paras kokoelma",
    "Best Anthology": "Paras antologia",
    "Best Novel": "Paras romaani",
    "Best Book for Younger Readers": "Paras nuortenkirja",
    "Best Fiction for Younger Readers": "Paras nuortenkirja",
    "Science Fiction": "Paras scifi-romaani",
    "Fantasy": "Paras fantasiaromaani",
    "Paranormal Fantasy": "Paras paranormaali fantasia -romaani",
    "Horror": "Paras kauhuromaani",
    "Young Adult Fantasy & Science Fiction": "Paras nuorten sf-romaani",
    "Young Adult Fantasy": "Paras nuorten sf-romaani",
    "Young Adult Fiction": "Paras nuortenkirja",
    "Middle Grade & Children's": "Paras lastenkirja",
    "Best Novelette": "Paras pitkä novelli",
    "Best SF Novel": "Paras scifi-romaani",
    "Best Fantasy Novel": "Paras fantasiaromaani",
    "Best Horror Novel": "Paras kauhuromaani",
    "Best Horror/Dark Fantasy Novel": "Paras kauhu/synkkä fantasia -romaani",
    "Best First Novel": "Paras ensiromaani",
    "Best Young Adult Book": "Paras nuortenkirja",
    "Best Single Author Collection": "Paras kokoelma",
    "Mythopoeic Fantasy Award": "Paras romaani",
    "Mythopoeic Fantasy Award for Adult Literature": "Paras romaani",
    "Mythopoeic Fantasy Award for Young Adult Literature": "Paras nuortenkirja",
    "Mythopoeic Fantasy Award for Children's Literature": "Paras lastenkirja",
    "Novel": "Paras romaani",
    "Novella": "Paras pienoisromaani",
    "Novelette": "Paras pitkä novelli",
    "Short Story": "Paras novelli",
    "Philip K. Dick Award": "Paras romaani",
    "Best Long Form Alternate History":
        "Paras vaihtoehtoishistoria (pitkä muoto)",
    "Best Short Form Alternate History":
        "Paras vaihtoehtoishistoria (lyhyt muoto)",
    "Best Short Science Fiction": "Paras scifi-novelli",
    "Best Long Fiction": "Paras pitkä fiktio",
    "Best Anthology/Collection (old)": "Paras kokoelma",
    "Andre Norton Award": "Paras nuorten sf-romaani",
    "Andre Norton Nebula Award for Middle Grade and Young Adult Fiction":
        "Paras nuorten sf-romaani",
    # Grand Prix de l'Imaginaire foreign categories.
    "Roman étranger": "Paras ulkomainen romaani",
    "Nouvelle étrangère": "Paras ulkomainen novelli",
    "Roman jeunesse étranger": "Paras ulkomainen nuortenromaani",
    # Grand Prix de l'Imaginaire French-language (domestic) categories.
    "Roman francophone": "Paras romaani",
    "Nouvelle francophone": "Paras novelli",
    "Roman jeunesse": "Paras nuortenkirja",
    "Roman jeunesse francophone": "Paras nuortenkirja",
    "Bester ausländischer SF-Roman": "Paras ulkomainen romaani",
    "Bestes ausländisches Werk": "Paras ulkomainen romaani",
    # Kurd Lasswitz German-language (domestic) categories.
    "Bester deutschsprachiger Roman": "Paras romaani",
    "Beste deutschsprachige Kurzgeschichte (short story)": "Paras novelli",
    "Beste deutschsprachige Kurzgeschichte (all short fiction)":
        "Paras novelli",
    "Beste deutschsprachige Erzählung (all short fiction)":
        "Paras lyhyt fiktio",
    "Beste deutschsprachige Erzählung (novelette/novella)":
        "Paras pienoisromaani",
    "Mejor novela - Best Novel": "Paras romaani",
    "Mejor novela extranjera - Best Foreign Novel": "Paras ulkomainen romaani",
    "Mejor cuento extranjero - Best Foreign Story": "Paras ulkomainen novelli",
}


@dataclass
class ScrapedWinner:
    """A single scraped award winner.

    alt_title holds an alternative form of the title (e.g. the original-
    language edition title that sfadb lists next to the English one); the
    matcher tries both against orig_title.
    """
    year: Optional[int]
    title: str
    author: str
    alt_title: Optional[str] = None


@dataclass
class ScrapedCategory:
    """Result of scraping one ISFDB award-category page."""
    isfdb_category_id: int
    award_type: str = ""
    category: str = ""
    winners: List[ScrapedWinner] = field(default_factory=list)


def category_url(isfdb_category_id: int) -> str:
    """Return the ISFDB award-category URL for the given category id."""
    return f"{ISFDB_CATEGORY_URL}?{isfdb_category_id}+0"


def _extract_year(text: str) -> Optional[int]:
    match = re.search(r"\d{4}", text or "")
    return int(match.group()) if match else None


# ISFDB rate-limits bursts of requests (returns 403). Batch callers can
# retry with backoff; web callers must not (it exceeds the worker timeout).
_RETRY_STATUSES = {403, 429, 500, 502, 503, 504}
_RETRY_BASE_DELAY = 5  # seconds; doubles each retry
# Attempts for offline/batch use (the seed); web requests use 1 (no retry).
SEED_MAX_ATTEMPTS = 4


def _get(url: str, max_attempts: int = 1) -> requests.Response:
    """GET a URL, optionally retrying with backoff on rate-limit responses.

    max_attempts defaults to 1 (fail fast, no retry) so this is safe to
    call from within a web request — the retry backoff would otherwise
    exceed the gunicorn worker timeout. Batch/offline callers (the seed)
    pass a higher value to tolerate ISFDB rate-limiting.
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(max_attempts):
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code not in _RETRY_STATUSES:
            break
        if attempt < max_attempts - 1:
            app.logger.warning(
                'ISFDB %s for %s; retry %d/%d in %ds',
                resp.status_code, url, attempt + 1, max_attempts - 1, delay)
            time.sleep(delay)
            delay *= 2
    resp.raise_for_status()
    return resp


def parse_award_category(isfdb_category_id: int,
                         item_type: int,
                         max_attempts: int = 1) -> ScrapedCategory:
    """
    Fetch and parse a single ISFDB award-category page.

    Args:
        isfdb_category_id: ISFDB award_category.cgi id.
        item_type: 0 = Work, 1 = Short story, 2 = Both. Only used by
            callers to decide which local tables to match against; the
            parse itself is type-agnostic.
        max_attempts: how many times to try the request (1 = fail fast,
            for web requests; higher tolerates rate-limiting in batch jobs).

    Returns:
        ScrapedCategory with award_type, category name and the list of
        winners. Winners list is empty if the page has no results table.
    """
    result = ScrapedCategory(isfdb_category_id=isfdb_category_id)

    resp = _get(category_url(isfdb_category_id), max_attempts=max_attempts)
    soup = BeautifulSoup(resp.content, "html.parser")

    for li in soup.find_all("li"):
        b = li.find("b")
        if not b:
            continue
        label = b.get_text()
        if "Award Category:" in label:
            sibling = b.next_sibling
            if sibling:
                result.category = sibling.strip().split("\n")[0].strip()
        elif "Award Type:" in label:
            a = b.find_next("a")
            if a:
                result.award_type = a.get_text(strip=True)

    table = soup.find("table")
    if not table:
        return result

    year: Optional[int] = None
    for row in table.find_all("tr"):
        th = row.find("th")
        if th:
            a = th.find("a")
            if a and re.search(r"\d{4}", a.get_text()):
                year = _extract_year(a.get_text(strip=True))
            continue
        tds = row.find_all("td")
        if len(tds) != 3:
            continue
        if "translation of" in tds[1].get_text(strip=True).lower():
            anchors = tds[1].find_all("a")
            title_tag = anchors[1] if len(anchors) > 1 else tds[1].find("a")
        else:
            title_tag = tds[1].find("a")
        author_tag = tds[2].find("a")
        title = (title_tag.get_text(strip=True) if title_tag
                 else tds[1].get_text(strip=True))
        author = (author_tag.get_text(strip=True) if author_tag
                  else tds[2].get_text(strip=True))
        if title:
            result.winners.append(ScrapedWinner(year=year, title=title,
                                                author=author))

    # ISFDB's Hugo Award pages from 2017 on embed a per-year voting-
    # statistics block (full of numeric columns) instead of a simple
    # winner row, so the loop above misses them. Within each year's block
    # the winner is the first linked title + author (top of the stats
    # table); selecting by ISFDB link type avoids the numeric columns.
    if result.award_type == "Hugo Award":
        existing_years = {w.year for w in result.winners}
        current_year: Optional[int] = None
        for row in table.find_all("tr"):
            th = row.find("th")
            if th:
                year_match = re.search(r"\d{4}", th.get_text())
                if year_match:
                    current_year = int(year_match.group())
            if current_year is None or current_year < 2017:
                continue
            if current_year in existing_years:
                continue
            title_link = row.find("a", href=re.compile(r"title\.cgi"))
            author_link = row.find("a", href=re.compile(r"ea\.cgi"))
            if title_link and author_link:
                title = title_link.get_text(strip=True)
                author = author_link.get_text(strip=True)
                if title:
                    result.winners.append(ScrapedWinner(
                        year=current_year, title=title, author=author))
                    existing_years.add(current_year)

    return result


# ---------------------------------------------------------------------------
# sfadb.com scraper (parallel to ISFDB; ISFDB blocks datacenter IPs)
# ---------------------------------------------------------------------------

SFADB_BASE_URL = "https://www.sfadb.com"

# Local award name -> sfadb award slug. sfadb's "<slug>_Winners_By_Category"
# page holds every winner for the award in one request.
SFADB_AWARD_SLUGS = {
    "Andre Norton Award": "Andre_Norton_Award",
    "Apollo": "Prix_Apollo",
    "Arthur C. Clarke -palkinto": "Arthur_C_Clarke_Award",
    "Bram Stoker Award": "Bram_Stoker_Awards",
    "British Fantasy Award": "British_Fantasy_Awards",
    "British Science Fiction Award": "British_SF_Association_Awards",
    "Campbell Memorial Award": "John_W_Campbell_Memorial_Award",
    # Carnegie-mitali and Goodreads Choice Awards: sfadb does not track them
    # (no page at all), so they have no import source.
    "Hugo": "Hugo_Awards",
    "Imaginaire": "Grand_Prix_de_lImaginaire",
    "Kurd Lasswitz Preis": "Kurd_Lasswitz_Preis",
    "Locus": "Locus_Awards",
    "Mythopoeic": "Mythopoeic_Awards",
    "Nebula": "Nebula_Awards",
    "Philip K. Dick Award": "Philip_K_Dick_Award",
    "Premio Ignotus": "Ignotus_Awards",
    "Retro Hugo": "Retro_Hugo_Awards",
    "Sidewise": "Sidewise_Awards",
    "Theodore Sturgeon Award": "Theodore_Sturgeon_Memorial_Award",
    "World Fantasy Award": "World_Fantasy_Awards",
    "Shirley Jackson Award": "Shirley_Jackson_Awards",
    "Prometheus Award": "Prometheus_Awards",
    "Ditmar Award": "Ditmar_Awards",
}

# sfadb category name (normalized: lowercased, whitespace collapsed) ->
# (local category name, item_type). item_type: 0 = Work, 1 = Short story,
# 2 = Both (novella). Categories not listed here are skipped (non-fiction,
# or not yet mapped). sfadb uses compound slash-separated labels.
SFADB_CATEGORY_MAP = {
    # Novels (domestic / general)
    "novel": ("Paras romaani", 0),
    "novel / novel or novelette": ("Paras romaani", 0),
    "novel/sf novel": ("Paras scifi-romaani", 0),
    "sf novel": ("Paras scifi-romaani", 0),
    "fantasy novel": ("Paras fantasiaromaani", 0),
    "horror novel": ("Paras kauhuromaani", 0),
    "horror/dark fantasy novel": ("Paras kauhu/synkkä fantasia -romaani", 0),
    "first novel": ("Paras ensiromaani", 0),
    "young adult book": ("Paras nuortenkirja", 0),
    "young adult novel": ("Paras nuortenkirja", 0),
    "young adult literature": ("Paras nuortenkirja", 0),
    # Mythopoeic fantasy categories
    "adult fantasy": ("Paras romaani", 0),
    "children's fantasy": ("Paras lastenkirja", 0),
    # Short fiction (domestic / general)
    "novella": ("Paras pienoisromaani", 2),
    "novelette": ("Paras pitkä novelli", 1),
    "short story": ("Paras novelli", 1),
    "short story / short fiction": ("Paras novelli", 1),
    "short story/short fiction": ("Paras novelli", 1),
    "short fiction": ("Paras lyhyt fiktio", 1),
    # Alternate history (Sidewise)
    "long form": ("Paras vaihtoehtoishistoria (pitkä muoto)", 0),
    "short form": ("Paras vaihtoehtoishistoria (lyhyt muoto)", 1),
    # Collections / anthologies
    "collection": ("Paras kokoelma", 0),
    "single-author collection": ("Paras kokoelma", 0),
    "collected work": ("Paras kokoelma", 0),
    "anthology": ("Paras antologia", 0),
    "edited anthology": ("Paras antologia", 0),
    # Ditmar (Australian) categories
    "australian long fiction/novel": ("Paras romaani", 0),
    "australian novella or novelette": ("Paras pienoisromaani", 2),
    "australian short fiction": ("Paras novelli", 1),
    "international fiction": ("Paras ulkomainen romaani", 0),
    # Foreign (from the award's perspective)
    "foreign novel": ("Paras ulkomainen romaani", 0),
    "foreign work": ("Paras ulkomainen romaani", 0),
    "foreign short fiction": ("Paras ulkomainen novelli", 1),
    "foreign short fiction or collection": ("Paras ulkomainen novelli", 1),
    "foreign short story": ("Paras ulkomainen novelli", 1),
    "foreign young adult novel": ("Paras ulkomainen nuortenromaani", 0),
    "foreign ya novel": ("Paras ulkomainen nuortenromaani", 0),
}

# Single-category awards that have no sfadb "winners by category" page.
# Their winners are read from the flat "winners by year" page and all get
# the mapped local category. award name -> (local category, item_type).
SFADB_SINGLE_CATEGORY = {
    # Andre Norton Award (best YA book); sfadb has only a By-Name page.
    "Andre Norton Award": ("Paras nuortenkirja", 0),
    "Philip K. Dick Award": ("Paras romaani", 0),
    "Arthur C. Clarke -palkinto": ("Paras romaani", 0),
    "Campbell Memorial Award": ("Paras romaani", 0),
    "Theodore Sturgeon Award": ("Paras novelli", 1),
    # Prix Apollo (best novel); sfadb has only a By-Name page, no By-Category.
    "Apollo": ("Paras romaani", 0),
}

# Awards given to a PERSON for a body of work, not to a specific title.
# sfadb tracks these on a plain "<slug>" page (no _Winners_By_... suffix),
# a flat one-row-per-year list with no title at all - see
# parse_award_sfadb_person_list. award name -> sfadb slug.
SFADB_PERSON_AWARD_SLUGS = {
    "Damon Knight Memorial Grand Master Award": "SFWA_Grand_Master_Award",
    "Skylark": "Skylark_Award",
    "WHC Grand Master": "World_Horror_Grandmaster",
}


def _norm_sfadb_category(name: str) -> str:
    """Normalize a sfadb category label for map lookup."""
    return " ".join(name.lower().split())


def sfadb_url(sfadb_slug: str, page: str = "Winners_By_Category") -> str:
    """Return a sfadb aggregate URL for an award slug."""
    return f"{SFADB_BASE_URL}/{sfadb_slug}_{page}"


def _parse_sfadb_winner(rightcol: Any,
                        year: Optional[int]) -> Optional[ScrapedWinner]:
    """Parse one sfadb winner cell: 'Title ( Original ), Author'."""
    text = rightcol.get_text(" ", strip=True)
    if not text or text.startswith("—"):
        return None
    # Co-winners are separate rows prefixed with "(tie)"; drop the marker.
    text = re.sub(r"^\(tie\)\s*", "", text, flags=re.IGNORECASE)
    links = rightcol.find_all("a")
    author = links[0].get_text(" ", strip=True) if links else ""
    if author and author in text:
        title_portion = text[:text.rfind(author)]
    else:
        title_portion, _, author = text.rpartition(",")
    title_portion = title_portion.strip().rstrip(",").strip().strip("“”")
    alt = None
    match = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", title_portion)
    if match:
        title = match.group(1).strip().strip("“”").strip()
        alt = match.group(2).strip()
    else:
        title = title_portion
    if not title:
        return None
    return ScrapedWinner(year=year, title=title, author=author.strip(),
                         alt_title=alt)


def parse_award_sfadb(sfadb_slug: str,
                      max_attempts: int = 1) -> List[ScrapedCategory]:
    """
    Fetch and parse an award's sfadb "winners by category" page.

    Returns one ScrapedCategory per sfadb super-category, each populated
    with its winners. Category names are the sfadb category labels; the
    caller maps them to local categories via SFADB_CATEGORY_MAP.
    """
    resp = _get(sfadb_url(sfadb_slug), max_attempts=max_attempts)
    soup = BeautifulSoup(resp.content, "html.parser")
    main = soup.find(class_="pagemain") or soup

    # Category sections are delimited by a '— category —' header row (in a
    # catwinsrightcol); the leading <a class="supercat"> elements are just a
    # menu. Within a section, catwinsleftcol=year, catwinsrightcol=winner.
    categories: List[ScrapedCategory] = []
    current: Optional[ScrapedCategory] = None
    pending_year: Optional[int] = None

    for el in main.find_all(True):
        classes = " ".join(el.get("class") or [])
        if "catwinsleftcol" in classes:
            pending_year = _extract_year(el.get_text())
        elif "catwinsrightcol" in classes:
            text = el.get_text(" ", strip=True)
            header = re.match(r"^[—–-]\s*(.+?)\s*[—–-]$", text)
            if header:
                current = ScrapedCategory(isfdb_category_id=0,
                                          category=header.group(1).strip())
                categories.append(current)
                pending_year = None
            elif current is not None:
                winner = _parse_sfadb_winner(el, pending_year)
                if winner:
                    current.winners.append(winner)
                pending_year = None

    return categories


def parse_award_sfadb_flat(sfadb_slug: str,
                           max_attempts: int = 1) -> List[ScrapedWinner]:
    """
    Parse all winners from an award's sfadb "winners by name" page as one
    flat list.

    Used for single-category awards with no "winners by category" page
    (e.g. Philip K. Dick, Arthur C. Clarke, Theodore Sturgeon); the caller
    assigns the fixed category. Layout: each 'nomineeblock' has a 'nominee'
    author ("Last, First"), then 'dateleftindent' (year) + 'titlemid'
    (title in <b>, with a 'win' marker for actual winners).
    """
    resp = _get(sfadb_url(sfadb_slug, "Winners_By_Name"),
                max_attempts=max_attempts)
    soup = BeautifulSoup(resp.content, "html.parser")
    main = soup.find(class_="pagemain") or soup

    winners: List[ScrapedWinner] = []
    for block in main.find_all(class_="nomineeblock"):
        nominee = block.find(class_="nominee")
        author = ""
        if nominee:
            for a in nominee.find_all("a"):
                if a.get("href"):
                    author = a.get_text(" ", strip=True)
                    break
        # By-Name lists authors as "Last, First"; flip to "First Last" to
        # match the stored alt_name form.
        if "," in author:
            last, _, first = author.partition(",")
            author = f"{first.strip()} {last.strip()}"
        pending_year: Optional[int] = None
        for el in block.find_all(True):
            classes = " ".join(el.get("class") or [])
            if "dateleftindent" in classes:
                pending_year = _extract_year(el.get_text())
            elif "titlemid" in classes:
                if el.find(class_="win"):
                    # Title is the text before the "— winner" marker (works
                    # for both bolded novels and quoted short fiction).
                    text = el.get_text(" ", strip=True)
                    title = re.sub(r"\s*[—–-]\s*winner.*$", "", text,
                                   flags=re.IGNORECASE).strip().strip("“”")
                    if title:
                        winners.append(ScrapedWinner(
                            year=pending_year, title=title, author=author))
                pending_year = None
    return winners


def parse_award_sfadb_person_list(sfadb_slug: str,
                                  max_attempts: int = 1) -> List[ScrapedWinner]:
    """
    Parse a sfadb "person award" page (one recipient per year, no title) -
    e.g. SFWA_Grand_Master_Award, Skylark_Award, World_Horror_Grandmaster.

    Layout: a <table> of <tr>s, each with a 'winslistleftcol' cell holding
    the year (in a 'winslistheader' span, "— YEAR —") and a
    'winslistrightcol' cell holding one <a> per recipient (more than one
    for a tied/joint year). The recipient's name goes in ScrapedWinner.title
    (there is no separate title/author for a person award - see ITEM_PERSON
    in the module docstring).
    """
    resp = _get(f"{SFADB_BASE_URL}/{sfadb_slug}", max_attempts=max_attempts)
    soup = BeautifulSoup(resp.content, "html.parser")
    main = soup.find(class_="pagemain") or soup

    winners: List[ScrapedWinner] = []
    pending_year: Optional[int] = None
    for el in main.find_all(True):
        classes = " ".join(el.get("class") or [])
        if "winslistleftcol" in classes:
            pending_year = _extract_year(el.get_text())
        elif "winslistrightcol" in classes:
            for a in el.find_all("a"):
                name = a.get_text(" ", strip=True)
                if name:
                    winners.append(ScrapedWinner(
                        year=pending_year, title=name, author=""))
            pending_year = None
    return winners


# ---------------------------------------------------------------------------
# Wikipedia wikitable scraper (domestic Finnish awards, and any award with
# no ISFDB/sfadb coverage at all - e.g. the Nobel Prize in Literature)
# ---------------------------------------------------------------------------

@dataclass
class WikipediaTableSource:
    """Where and how to read one award's winner history off Wikipedia.

    layout is "table" (default - see parse_award_wikipedia_table) or
    "heading_list": a plain "Year: Name" bullet list under a given heading
    rather than a wikitable, used for person awards with no dedicated
    article of their own (e.g. Kosmoskynä, a paragraph-and-list section on
    its granting organization's page rather than a "List of X winners"
    article) - see parse_award_wikipedia_heading_list.

    Column indices (table layout) are into a *full, non-continuation* data
    row - see parse_award_wikipedia_table for how a joint-year row (a
    rowspan'd year cell, so the following <tr> omits it and every column
    shifts left) is handled, by reading the year cell's own rowspan
    attribute directly rather than comparing cell counts (which a row
    simply missing an unused *trailing* column - e.g. Portti's newest
    entry has no "Lisätietoa" filled in yet - would be indistinguishable
    from). match_kind is "work" or "short" (year_col/author_col/title_col)
    or "person" (year_col/name_col for the table layout; heading_list is
    always a person award and needs neither).
    """
    url: str
    match_kind: str
    layout: str = "table"
    year_col: int = 0
    author_col: Optional[int] = None
    title_col: Optional[int] = None
    name_col: Optional[int] = None
    skip_rows: int = 1
    table_index: int = 0
    heading_id: Optional[str] = None
    heading_tag: str = "h2"


# Local award name -> where to scrape it. All the Finnish awards share the
# same simple "Vuosi | Kirjailija | Teos | ..." layout; only Nobel (English
# Wikipedia, a person award, an irregular two-row header) needs the extra
# fields.
WIKIPEDIA_AWARD_SOURCES: Dict[str, WikipediaTableSource] = {
    "Nobelin kirjallisuuspalkinto": WikipediaTableSource(
        url="https://en.wikipedia.org/wiki/List_of_Nobel_laureates_in_Literature",
        match_kind="person", year_col=0, name_col=2, skip_rows=2),
    "Finlandia-palkinto": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Finlandia-palkinto",
        match_kind="work", author_col=1, title_col=2),
    "Lasten- ja nuortenkirjallisuuden Finlandia": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Lasten-_ja_nuortenkirjallisuuden_Finlandia",
        match_kind="work", author_col=1, title_col=2),
    "Topelius-palkinto": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Topelius-palkinto",
        match_kind="work", author_col=1, title_col=2),
    "Arvid Lydecken -palkinto": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Arvid_Lydecken_-palkinto",
        match_kind="work", author_col=1, title_col=2),
    "Kuvastaja": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Kuvastaja",
        match_kind="work", author_col=1, title_col=2),
    "Tähtifantasia": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/T%C3%A4htifantasia-palkinto",
        match_kind="work", author_col=1, title_col=2),
    "Tähtivaeltaja": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/T%C3%A4htivaeltaja-palkinto",
        match_kind="work", author_col=1, title_col=2),
    "Atorox": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Atorox-palkinto",
        match_kind="short", author_col=1, title_col=2),
    "Portin novellikilpailu": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Portti_(lehti)",
        match_kind="short", author_col=1, title_col=2),
    # Kosmoskynä has no dedicated "list of winners" article - its granting
    # organization's own page has a plain "Year: Name" bullet list under a
    # "Kosmoskynä-palkinto" heading instead of a wikitable. anarres.fi used
    # to be the reference for this (and for Atorox/Portti above, and the
    # Finnish SF-genre awards further up) but has gone offline entirely;
    # this Wikipedia section is the replacement source found for it.
    "Kosmoskynä": WikipediaTableSource(
        url="https://fi.wikipedia.org/wiki/Suomen_tieteis-_ja_fantasiakirjoittajat",
        match_kind="person", layout="heading_list",
        heading_id="Kosmoskynä-palkinto"),
    "Booker-palkinto": WikipediaTableSource(
        url="https://en.wikipedia.org/wiki/Booker_Prize",
        match_kind="work", author_col=1, title_col=2),
}

# The local category assigned to each work-based Wikipedia-table award's
# winners (all a single best-novel/best-book category per award; unlike
# sfadb's multi-category pages, these tables have no per-category grouping
# to read a category label from). Awards not listed here (Nobel, a person
# award) get no category - see _PERSON_AWARD_CATEGORY instead.
WIKIPEDIA_AWARD_CATEGORY = {
    "Finlandia-palkinto": "Paras romaani",
    "Lasten- ja nuortenkirjallisuuden Finlandia": "Paras nuortenkirja",
    "Topelius-palkinto": "Paras nuortenkirja",
    "Arvid Lydecken -palkinto": "Paras lastenkirja",
    "Kuvastaja": "Paras romaani",
    "Tähtifantasia": "Paras romaani",
    "Tähtivaeltaja": "Paras romaani",
    "Atorox": "Paras novelli",
    "Portin novellikilpailu": "Paras novelli",
    "Booker-palkinto": "Paras romaani",
}

# Wikipedia-table awards given for a FOREIGN work translated into Finnish:
# the table's title column is the Finnish edition's own title (Work.title),
# not the original-language one (Work.orig_title) ISFDB/sfadb always supply
# and _match_title matches by default - see also_local_title there. The
# other Wikipedia-table awards (Finlandia, Topelius, Lydecken, Kuvastaja)
# are for domestic Finnish-authored works, where title == orig_title.
WIKIPEDIA_TRANSLATED_WORK_AWARDS = {"Tähtivaeltaja", "Tähtifantasia"}

_FOOTNOTE_RE = re.compile(r"\[\s*\d+\s*\]")
# Strips a trailing "(1839-1907)"-style lifespan off a Wikipedia laureate
# name (must contain a 4-digit year so it doesn't eat a genuine parenthetical
# like "(Firstname Lastname)").
_LIFESPAN_SUFFIX_RE = re.compile(r"\s*\([^)]*\d{4}[^)]*\)\s*$")


def parse_award_wikipedia_table(source: WikipediaTableSource,
                                max_attempts: int = 1) -> List[ScrapedWinner]:
    """
    Parse a Wikipedia award-history wikitable into a flat list of winners.

    Handles the two irregularities this kind of table commonly has:
      - A year cell with rowspan > 1 for a jointly-awarded year: the
        following <tr>(s) omit it entirely, so every column from year_col
        onward is shifted left by one in those rows. Detected by reading
        the year cell's own `rowspan` attribute and counting down over the
        rows that follow - not by comparing each row's cell count to a
        "full" row's, which also misfires on an unrelated, harmless
        irregularity: a row simply missing an unused *trailing* column
        (e.g. Portti's newest entry has no "Lisätietoa" cell filled in
        yet) looks identical to a rowspan continuation by cell count alone,
        but must NOT be treated as one.
      - Trailing footnote markers baked into cell text ("2026 [ 27 ]",
        "Title [ 63 ]") - stripped before use.
    A row with no name/title text (the award wasn't given that year, e.g.
    Nobel 1940-1943, where a *different* cell - "Not awarded" - carries the
    rowspan instead of the year) is silently skipped; such a row is simply
    missing the name/title cell entirely regardless of column arithmetic.
    """
    resp = _get(source.url, max_attempts=max_attempts)
    soup = BeautifulSoup(resp.content, "html.parser")
    tables = soup.find_all("table", class_="wikitable")
    if source.table_index >= len(tables):
        return []
    rows = tables[source.table_index].find_all("tr")[source.skip_rows:]

    def clean(text: str) -> str:
        # A trailing ":" turns up occasionally (e.g. a wikilinked name
        # immediately followed by a now-empty explanatory note that got
        # edited out on Wikipedia's end, leaving just the colon behind) -
        # harmless to strip since a real title/name never ends in one.
        return _FOOTNOTE_RE.sub("", text).strip().rstrip(":;,").strip()

    winners: List[ScrapedWinner] = []
    pending_year: Optional[int] = None
    # >0 while later rows still owe a year cell carried over by an earlier
    # row's rowspan (decremented once per row consumed).
    year_rowspan_remaining = 0
    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        if year_rowspan_remaining > 0:
            col_offset = source.year_col + 1
            year_rowspan_remaining -= 1
        else:
            col_offset = 0
            year_cell = cells[source.year_col] if source.year_col < len(cells) else None
            if year_cell is not None:
                rowspan = int(year_cell.get("rowspan", 1) or 1)
                if rowspan > 1:
                    year_rowspan_remaining = rowspan - 1
                year = _extract_year(clean(year_cell.get_text(" ", strip=True)))
                if year is not None:
                    pending_year = year

        def cell_text(idx: int, _cells=cells, _offset=col_offset) -> str:
            real_idx = idx - _offset
            if real_idx < 0 or real_idx >= len(_cells):
                return ""
            return clean(_cells[real_idx].get_text(" ", strip=True))

        if pending_year is None:
            continue

        if source.match_kind == "person":
            name = _LIFESPAN_SUFFIX_RE.sub("", cell_text(source.name_col)).strip()
            if not name:
                continue
            winners.append(ScrapedWinner(year=pending_year, title=name, author=""))
        else:
            title = cell_text(source.title_col)
            if not title:
                continue
            author = cell_text(source.author_col)
            winners.append(ScrapedWinner(year=pending_year, title=title, author=author))

    return winners


# A bullet-list line reads "1985: Kari Mäentaka" or "1996: Turun science
# fiction -seura" (an organization, not a person - _build_person_entry
# simply won't find a matching Person row for it, the same safe outcome as
# any other unmatched name).
_HEADING_LIST_LINE_RE = re.compile(r"^\s*(\d{4})\s*:\s*(.+?)\s*$")


def parse_award_wikipedia_heading_list(source: WikipediaTableSource,
                                       max_attempts: int = 1) -> List[ScrapedWinner]:
    """
    Parse a plain "Year: Name" bullet list under a Wikipedia section
    heading (source.heading_id) into a flat list of person-award winners -
    for an award with no dedicated "list of winners" article of its own,
    just a paragraph-and-list section on its granting organization's page
    (e.g. Kosmoskynä on Suomen tieteis- ja fantasiakirjoittajat's page).

    Modern Wikipedia wraps each heading in a <div class="mw-heading">; the
    <ul> is that div's next sibling (with a <p> or two sometimes in
    between), not the heading tag's own sibling.
    """
    resp = _get(source.url, max_attempts=max_attempts)
    soup = BeautifulSoup(resp.content, "html.parser")
    content = soup.find(class_="mw-parser-output") or soup
    heading = content.find(source.heading_tag, id=source.heading_id)
    if heading is None:
        return []

    container = heading.parent if heading.parent and heading.parent.name == "div" else heading
    node = container
    winners: List[ScrapedWinner] = []
    while True:
        node = node.find_next_sibling()
        if node is None:
            break
        if node.name == "div" and "mw-heading" in (node.get("class") or []):
            break  # reached the next section
        if node.name != "ul":
            continue
        for li in node.find_all("li", recursive=False):
            # Strip footnote markers from the whole line first - one can
            # land between the year and the colon (e.g. "2018 [9]: Name").
            line = _FOOTNOTE_RE.sub("", li.get_text(" ", strip=True))
            match = _HEADING_LIST_LINE_RE.match(line)
            if not match:
                continue
            name = match.group(2).strip()
            if name:
                winners.append(ScrapedWinner(
                    year=int(match.group(1)), title=name, author=""))
        break  # one list is the whole section's content here

    return winners


def parse_wikipedia_award_source(source: WikipediaTableSource,
                                 max_attempts: int = 1) -> List[ScrapedWinner]:
    """Dispatch to the right parser for source.layout."""
    if source.layout == "heading_list":
        return parse_award_wikipedia_heading_list(source, max_attempts)
    return parse_award_wikipedia_table(source, max_attempts)


# ---------------------------------------------------------------------------
# Matching scraped winners against the local database
# ---------------------------------------------------------------------------

# Preview entry statuses.
STATUS_NEW = "new"              # matched a local work/story, not yet awarded
STATUS_AWARDED = "awarded"      # already recorded in the awarded table
STATUS_NOT_FOUND = "not_found"  # no local work/story matches the title
STATUS_AMBIGUOUS = "ambiguous"  # several local works/stories match the title


def _category_lookup(session: Any) -> Dict[Tuple[str, int], int]:
    """Map (lowercased category name, awardcategory.type) -> category id."""
    lookup: Dict[Tuple[str, int], int] = {}
    for cat in session.query(AwardCategory).all():
        lookup[(cat.name.lower(), cat.type)] = cat.id
    return lookup


def _existing_awarded(session: Any, award_id: int
                      ) -> Tuple[set, set, set]:
    """Return (work_ids, story_ids, person_ids) already recorded for this
    award.

    These are treated as authoritative: the importer never duplicates,
    replaces or removes them. person_ids is only ever populated/consulted
    for ITEM_PERSON awards (see module docstring) - a normal title-matching
    import never touches it.
    """
    rows = session.query(
        Awarded.work_id, Awarded.story_id, Awarded.person_id).filter(
        Awarded.award_id == award_id).all()
    work_ids = {r.work_id for r in rows if r.work_id is not None}
    story_ids = {r.story_id for r in rows if r.story_id is not None}
    person_ids = {r.person_id for r in rows if r.person_id is not None}
    return work_ids, story_ids, person_ids


_LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+")
# Quotation marks stripped from both sides so curly/straight/single/double
# variants compare equal (sfadb “...” / ‘...’ vs stored "...").
_TITLE_QUOTE_CHARS = "“”‘’\"'"


def _strip_leading_article(title: str) -> str:
    """Lowercase a title and drop a leading English article."""
    return _LEADING_ARTICLE_RE.sub("", title.lower().strip()).strip()


def _strip_quotes(text: str) -> str:
    for q in _TITLE_QUOTE_CHARS:
        text = text.replace(q, "")
    return text


def _title_match_variants(title: str) -> set:
    """Title forms to match, tolerating a leading article on either side and
    a subtitle (': ...') / quote characters on either side.

    The database sometimes stores a leading article the original title lacks
    (or vice versa), a subtitle sfadb omits ('The Dispossessed: An Ambiguous
    Utopia' vs 'The Dispossessed'), or different quote marks. Variants are
    quote-stripped; the caller also matches the DB title's before-colon form.
    """
    variants: set = set()
    for base in (title, title.split(":", 1)[0]):
        low = _strip_quotes(base.lower().strip())
        stripped = _strip_leading_article(low)
        variants |= {low, stripped, f"the {stripped}", f"a {stripped}",
                     f"an {stripped}"}
    variants.discard("")
    return variants


def _title_field_exprs(field):
    """SQL expressions for matching one title-like column: quote-stripped
    full text and quote-stripped part before a subtitle colon."""
    expr = func.lower(field)
    for q in _TITLE_QUOTE_CHARS:
        expr = func.replace(expr, q, "")
    before_colon = func.trim(func.split_part(expr, ":", 1))
    return expr, before_colon


def _match_title(session: Any, model: Any, *titles: Optional[str],
                 also_local_title: bool = False) -> List[Any]:
    """Match on orig_title, tolerating leading articles, subtitles and quote
    characters. Accepts several title forms (e.g. English and original) and
    matches any of them. Returns matching rows.

    also_local_title additionally matches model.title (the work's own
    Finnish-edition title, as opposed to orig_title, the title in its
    original language). ISFDB/sfadb always supply an English/original title,
    so the default (orig_title only) is correct there - but a Wikipedia
    table of a FOREIGN-work award translated into Finnish (e.g.
    Tähtivaeltaja, Tähtifantasia) gives the Finnish edition's own title,
    which lives in Work.title, not Work.orig_title (e.g. work 1164 "The
    Best of Cordwainer Smith" / "Planeetta nimeltä Shajol").
    """
    variants: set = set()
    for title in titles:
        if title:
            variants |= _title_match_variants(title)
    if not variants:
        return []
    fields = [model.orig_title]
    if also_local_title:
        fields.append(model.title)
    conditions = []
    for field in fields:
        full, before_colon = _title_field_exprs(field)
        conditions.extend([full.in_(variants), before_colon.in_(variants)])
    return session.query(model).filter(or_(*conditions)).all()


# contributorrole.id for the author ("Kirjoittaja").
_AUTHOR_ROLE_ID = 1


# Name suffixes ignored when comparing author names.
_NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def _name_tokens(name: Optional[str]) -> Tuple[str, ...]:
    """Tokenize a person name for comparison.

    Lowercases, treats '.' and ',' as separators (so 'Walter M. Miller,
    Jr.' == 'Walter M. Miller Jr.') and drops name suffixes like 'Jr.'.
    """
    if not name:
        return ()
    cleaned = name.lower().replace(".", " ").replace(",", " ")
    return tuple(t for t in cleaned.split() if t not in _NAME_SUFFIXES)


def _names_match(a: Tuple[str, ...], b: Tuple[str, ...]) -> bool:
    """Whether two tokenized names refer to the same person.

    Matches on an exact token match, or when the first and last tokens
    agree, so that a differing/absent middle name or initial does not
    prevent a match (e.g. ISFDB 'Brian W. Aldiss' vs stored 'Brian
    Aldiss'). Requiring both first and last to agree keeps different
    people apart.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    return a[0] == b[0] and a[-1] == b[-1]


def _person_name_variants(person: Any) -> List[Tuple[str, ...]]:
    """Tokenized name forms for a person.

    ISFDB gives authors as 'Firstname Lastname', which matches the stored
    alt_name. We also derive 'Firstname Lastname' from the 'Lastname,
    Firstname' primary name as a fallback.
    """
    variants = []
    if person.alt_name:
        variants.append(_name_tokens(person.alt_name))
    if person.name:
        if ',' in person.name:
            last, _, first = person.name.partition(',')
            variants.append(_name_tokens(f'{first} {last}'))
        else:
            variants.append(_name_tokens(person.name))
    return [v for v in variants if v]


def _author_name_variants(session: Any, match_type: str,
                          item_id: int) -> List[Tuple[str, ...]]:
    """Tokenized author names (role = author) for a work or short story."""
    if match_type == "work":
        query = session.query(Person).join(
            WorkContributor, WorkContributor.person_id == Person.id).filter(
            WorkContributor.work_id == item_id,
            WorkContributor.role_id == _AUTHOR_ROLE_ID)
    else:
        query = session.query(Person).join(
            StoryContributor,
            StoryContributor.person_id == Person.id).filter(
            StoryContributor.shortstory_id == item_id,
            StoryContributor.role_id == _AUTHOR_ROLE_ID)
    variants: List[Tuple[str, ...]] = []
    for person in query.all():
        variants.extend(_person_name_variants(person))
    return variants


def _author_matches(session: Any, match_type: str, item_id: int,
                    scraped_author: str) -> bool:
    """
    Whether the scraped author matches an author of the candidate item.

    Titles alone are ambiguous: different authors can share an original
    title, so we require the ISFDB author to match one of the item's
    authors. If the scrape provides no author, we cannot verify and treat
    it as a match (rare).
    """
    scraped = _name_tokens(scraped_author)
    if not scraped:
        return True
    return any(_names_match(scraped, variant)
               for variant in _author_name_variants(
                   session, match_type, item_id))


# awardcategory.type used when resolving our_category for each match kind.
_PERSON_CATEGORY_TYPE = 0
_WORK_CATEGORY_TYPE = 1
_SHORT_CATEGORY_TYPE = 2

# Every existing ITEM_PERSON award row in the DB (SFWA/Skylark/WHC Grand
# Master) uses this one category, and there is no source that would ever
# suggest a different one for an award given for a body of work - so it's a
# plain constant rather than a per-award config value.
_PERSON_AWARD_CATEGORY = "Elämäntyöpalkinto"

# A short-fiction category (e.g. "short story / short fiction") is ambiguous:
# the winner may be a short story or a stand-alone work. When it matches a
# work, use the work-length short-fiction category instead.
_SHORT_FICTION_WORK_CATEGORY = {
    "Paras novelli": "Paras lyhyt fiktio",
}


def _resolve_category_id(category_lookup: Dict[Tuple[str, int], int],
                         name: Optional[str],
                         preferred_type: int) -> Optional[int]:
    """Resolve a local category name to an id.

    The same category name can exist as both a novel category (type 1) and
    a short-story category (type 2), so we try the preferred type first and
    then fall back to the other. This matters when short fiction is
    published as a work: the winner matches a work but the category is a
    short-fiction one (or vice versa).
    """
    if not name:
        return None
    key = name.lower()
    for cat_type in (preferred_type, _WORK_CATEGORY_TYPE, _SHORT_CATEGORY_TYPE):
        cid = category_lookup.get((key, cat_type))
        if cid is not None:
            return cid
    return None


def _resolve_matches(candidate_sets: List[Tuple[str, int, set, List[Any]]]
                     ) -> Tuple[str, Optional[str], Optional[int],
                                Optional[Any], List[int]]:
    """Decide the outcome from author-verified candidate matches.

    ``candidate_sets`` is a list of (match_type, category type, already-
    awarded id set, matched rows), in preference order. Each matched row
    has ``.id`` and ``.title``.

    Rules:
      1. If any candidate already holds THIS award (its id is in that
         kind's already-awarded set), assume the admin previously selected
         it and use it (status 'awarded'). Checked across all kinds/types
         first, so an existing award resolves any ambiguity.
      2. Otherwise take the first kind with matches: a single match is
         'new', several is 'ambiguous'.
      3. No candidates at all is 'not_found'.

    Returns (status, match_type, category type, matched row, candidate ids).
    """
    for match_type, cat_type, awarded_ids, matches in candidate_sets:
        for matched in matches:
            if matched.id in awarded_ids:
                return (STATUS_AWARDED, match_type, cat_type, matched, [])

    for match_type, cat_type, awarded_ids, matches in candidate_sets:
        if len(matches) > 1:
            return (STATUS_AMBIGUOUS, match_type, cat_type, None,
                    [m.id for m in matches])
        return (STATUS_NEW, match_type, cat_type, matches[0], [])

    return (STATUS_NOT_FOUND, None, None, None, [])


def _build_entry(session: Any, winner: ScrapedWinner, item_type: int,
                 isfdb_category: str, our_category: Optional[str],
                 category_lookup: Dict[Tuple[str, int], int],
                 work_ids: set, story_ids: set,
                 also_local_title: bool = False) -> Dict[str, Any]:
    """Match one scraped winner and build a preview entry dict.

    also_local_title is passed straight through to _match_title - see its
    docstring. Only set for Wikipedia-table awards for a foreign work
    translated into Finnish (Tähtivaeltaja, Tähtifantasia), where the
    scraped title is the Finnish edition's own title rather than the
    original-language one ISFDB/sfadb always supply.
    """
    entry: Dict[str, Any] = {
        "year": winner.year,
        "title": winner.title,
        "author": winner.author,
        "isfdb_category": isfdb_category,
        "our_category": our_category,
        "item_type": item_type,
        "match_type": None,
        "target_id": None,
        "target_title": None,
        "category_id": None,
        "status": STATUS_NOT_FOUND,
        "candidates": [],
    }

    # Which local kinds to try, in order, as (match_type, model,
    # preferred category type, already-awarded id set).
    #   0 = Work  -> works only (a novel is always a work)
    #   1 = Short -> short stories first, then works, because short fiction
    #                is sometimes published as a stand-alone work in Finnish
    #                (e.g. work 6057) and recorded in the work table
    #   2 = Both  -> works first, then short stories
    kinds = []
    if item_type in (ITEM_WORK, ITEM_BOTH):
        kinds.append(("work", Work, _WORK_CATEGORY_TYPE, work_ids))
    if item_type in (ITEM_SHORT, ITEM_BOTH):
        kinds.append(("short", ShortStory, _SHORT_CATEGORY_TYPE, story_ids))
    if item_type == ITEM_SHORT:
        kinds.append(("work", Work, _SHORT_CATEGORY_TYPE, work_ids))

    # Gather author-verified title matches per kind. Author matching is
    # required because different authors can share an original title.
    candidate_sets = []
    for match_type, model, cat_type, awarded_ids in kinds:
        matches = [
            m for m in _match_title(session, model, winner.title,
                                    winner.alt_title,
                                    also_local_title=also_local_title)
            if _author_matches(session, match_type, m.id, winner.author)
        ]
        if matches:
            candidate_sets.append((match_type, cat_type, awarded_ids, matches))

    status, match_type, cat_type, matched, candidate_ids = _resolve_matches(
        candidate_sets)
    entry["status"] = status
    entry["candidates"] = candidate_ids
    if match_type is not None:
        entry["match_type"] = match_type
    if matched is not None:
        entry["target_id"] = matched.id
        entry["target_title"] = matched.title
        # Resolve the category by what the winner actually is: a work gets a
        # work-length category (including the short-fiction-as-work override).
        if match_type == "work":
            resolved = _SHORT_FICTION_WORK_CATEGORY.get(our_category or "",
                                                        our_category)
            preferred_type = _WORK_CATEGORY_TYPE
        else:
            resolved = our_category
            preferred_type = _SHORT_CATEGORY_TYPE
        # Reflect the resolved category in the entry so the preview shows
        # what will actually be saved.
        entry["our_category"] = resolved
        entry["category_id"] = _resolve_category_id(
            category_lookup, resolved, preferred_type)

    return entry


def _person_name_index(session: Any) -> List[Tuple[Any, List[Tuple[str, ...]]]]:
    """(person, tokenized name variants) for every person in the DB, built
    once per preview request for ITEM_PERSON awards. Reuses
    _person_name_variants, the same tokenization already used to verify a
    title match's author - a full-table scan is fine here since this only
    runs for the rare person-only award and person is a few thousand rows."""
    return [(p, _person_name_variants(p)) for p in session.query(Person).all()]


def _build_person_entry(winner: ScrapedWinner,
                        person_index: List[Tuple[Any, List[Tuple[str, ...]]]],
                        person_ids: set,
                        category_lookup: Dict[Tuple[str, int], int]
                        ) -> Dict[str, Any]:
    """Match one scraped person-award winner (by name, not title) and build
    a preview entry. See ITEM_PERSON in the module docstring."""
    entry: Dict[str, Any] = {
        "year": winner.year,
        "title": winner.title,
        "author": "",
        "isfdb_category": winner.title,
        "our_category": _PERSON_AWARD_CATEGORY,
        "item_type": ITEM_PERSON,
        "match_type": None,
        "target_id": None,
        "target_title": None,
        "category_id": _resolve_category_id(
            category_lookup, _PERSON_AWARD_CATEGORY, _PERSON_CATEGORY_TYPE),
        "status": STATUS_NOT_FOUND,
        "candidates": [],
    }

    scraped = _name_tokens(winner.title)
    matches = [person for person, variants in person_index
              if any(_names_match(scraped, variant) for variant in variants)]

    # _resolve_matches assumes a non-empty match list per candidate set
    # (it unconditionally indexes matches[0] once ambiguity is ruled out) -
    # same convention _build_entry follows for its own candidate_sets.
    candidate_sets = [("person", None, person_ids, matches)] if matches else []
    status, match_type, _, matched, candidate_ids = _resolve_matches(
        candidate_sets)
    entry["status"] = status
    entry["candidates"] = candidate_ids
    if match_type is not None:
        entry["match_type"] = match_type
    if matched is not None:
        entry["target_id"] = matched.id
        entry["target_title"] = matched.alt_name or matched.name

    return entry


def _collect_isfdb(session: Any, award_id: int, errors: List[str]):
    """Yield (item_type, our_category, label, winners) from ISFDB sources."""
    sources = session.query(AwardImportSource).filter(
        AwardImportSource.award_id == award_id).order_by(
        AwardImportSource.id).all()
    if not sources:
        return None
    collected = []
    for source in sources:
        try:
            scraped = parse_award_category(source.isfdb_category_id,
                                           source.item_type)
        except requests.RequestException as exc:
            errors.append(f'ISFDB {source.isfdb_category_id}: {exc}')
            continue
        collected.append((source.item_type, source.our_category,
                          scraped.category, scraped.winners))
    return collected


def _collect_sfadb(award: Any, errors: List[str]):
    """Yield (item_type, our_category, label, winners) from sfadb."""
    person_slug = SFADB_PERSON_AWARD_SLUGS.get(award.name)
    if person_slug:
        try:
            winners = parse_award_sfadb_person_list(person_slug)
        except requests.RequestException as exc:
            errors.append(f'sfadb {person_slug}: {exc}')
            return []
        return [(ITEM_PERSON, None, award.name, winners)]

    slug = SFADB_AWARD_SLUGS.get(award.name)
    if not slug:
        return None

    # Single-category awards have no "winners by category" page; read the
    # flat "winners by year" list and apply the configured category.
    single = SFADB_SINGLE_CATEGORY.get(award.name)
    if single is not None:
        our_category, item_type = single
        try:
            winners = parse_award_sfadb_flat(slug)
        except requests.RequestException as exc:
            errors.append(f'sfadb {slug}: {exc}')
            return []
        return [(item_type, our_category, award.name, winners)]

    try:
        scraped_cats = parse_award_sfadb(slug)
    except requests.RequestException as exc:
        errors.append(f'sfadb {slug}: {exc}')
        return []
    collected = []
    for cat in scraped_cats:
        mapping = SFADB_CATEGORY_MAP.get(_norm_sfadb_category(cat.category))
        if mapping is None:
            # Non-fiction or not-yet-mapped category: skip it.
            continue
        our_category, item_type = mapping
        collected.append((item_type, our_category, cat.category, cat.winners))
    return collected


_WIKIPEDIA_MATCH_KIND_TO_ITEM_TYPE = {
    "work": ITEM_WORK,
    "short": ITEM_SHORT,
    "person": ITEM_PERSON,
}


def _collect_wikipedia(award: Any, errors: List[str]):
    """Yield (item_type, our_category, label, winners) from a Wikipedia
    source (a wikitable or a heading_list, see WikipediaTableSource) -
    used for domestic Finnish awards and any other award with no ISFDB/
    sfadb coverage (e.g. the Nobel Prize in Literature)."""
    wiki_source = WIKIPEDIA_AWARD_SOURCES.get(award.name)
    if not wiki_source:
        return None
    try:
        winners = parse_wikipedia_award_source(wiki_source)
    except requests.RequestException as exc:
        errors.append(f'wikipedia {wiki_source.url}: {exc}')
        return []
    item_type = _WIKIPEDIA_MATCH_KIND_TO_ITEM_TYPE[wiki_source.match_kind]
    if item_type == ITEM_PERSON:
        return [(item_type, None, award.name, winners)]
    our_category = WIKIPEDIA_AWARD_CATEGORY.get(award.name)
    return [(item_type, our_category, award.name, winners)]


def get_import_source_info(award_name: str) -> Optional[Dict[str, str]]:
    """Return {"label": ..., "url": ...} for the source an award's "Tuo
    voittajat" import reads from, or None if it has no import source.

    Checks the exact same three places, in the same priority order, that
    _collect_sfadb/_collect_wikipedia (via preview_import's default
    source="sfadb") and impl_awards.get_award's has_import_source flag do -
    so this always agrees with whether the import button is shown, and
    with which source it would actually use. ISFDB is deliberately not
    included: every award ISFDB tracks that this app actually imports from
    is also in SFADB_AWARD_SLUGS, and sfadb is the source preview_import
    uses by default (ISFDB blocks datacenter/production IPs), so sfadb is
    the honest answer to "where do new imports for this award come from".
    """
    person_slug = SFADB_PERSON_AWARD_SLUGS.get(award_name)
    if person_slug:
        return {"label": "sfadb.com", "url": f"{SFADB_BASE_URL}/{person_slug}"}
    slug = SFADB_AWARD_SLUGS.get(award_name)
    if slug:
        return {"label": "sfadb.com", "url": f"{SFADB_BASE_URL}/{slug}"}
    wiki_source = WIKIPEDIA_AWARD_SOURCES.get(award_name)
    if wiki_source:
        return {"label": "Wikipedia", "url": wiki_source.url}
    return None


def preview_import(award_id: int, source: str = "sfadb") -> ResponseType:
    """
    Scrape an award's winners from a source and match them against the DB.

    source is 'sfadb' (default) or 'isfdb'. sfadb is the default because
    ISFDB blocks datacenter (production) IPs. Returns a preview: every
    scraped winner with its match status (new / awarded / not_found /
    ambiguous). Nothing is written.
    """
    session = new_session()

    award = session.query(Award).filter(Award.id == award_id).first()
    if not award:
        return ResponseType('Palkintoa ei löydy.',
                            HttpResponseCode.NOT_FOUND.value)

    category_lookup = _category_lookup(session)
    work_ids, story_ids, person_ids = _existing_awarded(session, award_id)

    entries: List[Dict[str, Any]] = []
    errors: List[str] = []

    if source == "sfadb":
        collected = _collect_sfadb(award, errors)
        if collected is None:
            collected = _collect_wikipedia(award, errors)
    else:
        collected = _collect_isfdb(session, award_id, errors)
    if collected is None:
        return ResponseType(
            f'Tälle palkinnolle ei ole {source}-tuontilähdettä.',
            HttpResponseCode.BAD_REQUEST.value)

    person_index = None  # built lazily; only ITEM_PERSON awards need it
    for item_type, our_category, label, winners in collected:
        for winner in winners:
            if item_type == ITEM_PERSON:
                if person_index is None:
                    person_index = _person_name_index(session)
                entries.append(_build_person_entry(
                    winner, person_index, person_ids, category_lookup))
            else:
                entries.append(_build_entry(
                    session, winner, item_type, label,
                    our_category, category_lookup, work_ids, story_ids,
                    also_local_title=award.name in WIKIPEDIA_TRANSLATED_WORK_AWARDS))

    counts = {
        STATUS_NEW: sum(1 for e in entries if e["status"] == STATUS_NEW),
        STATUS_AWARDED: sum(1 for e in entries
                            if e["status"] == STATUS_AWARDED),
        STATUS_NOT_FOUND: sum(1 for e in entries
                              if e["status"] == STATUS_NOT_FOUND),
        STATUS_AMBIGUOUS: sum(1 for e in entries
                              if e["status"] == STATUS_AMBIGUOUS),
    }

    return ResponseType({
        "award_id": award_id,
        "award_name": award.name,
        "counts": counts,
        "errors": errors,
        "entries": entries,
    }, HttpResponseCode.OK.value)


def save_import(award_id: int, params: Any) -> ResponseType:
    """
    Save selected scraped winners as new Awarded rows.

    Only adds rows: an item already awarded for this award (by work_id,
    story_id or person_id) is skipped, never duplicated or replaced. A
    'person' match_type is only ever produced by an ITEM_PERSON award's own
    preview (see module docstring) - a normal title-matching import never
    emits one, so this does not open the door to an ordinary import
    clobbering a mixed award's manually-entered personal winner.

    Request body: {"data": {"winners": [
        {"match_type": "work"|"short"|"person", "target_id": <int>,
         "category_id": <int|null>, "year": <int|null>}, ...]}}
    """
    session = new_session()

    award = session.query(Award).filter(Award.id == award_id).first()
    if not award:
        return ResponseType('Palkintoa ei löydy.',
                            HttpResponseCode.NOT_FOUND.value)

    data = params.get('data', {})
    winners = data.get('winners', [])

    work_ids, story_ids, person_ids = _existing_awarded(session, award_id)

    created = 0
    skipped = 0
    try:
        for w in winners:
            match_type = w.get('match_type')
            target_id = w.get('target_id')
            if match_type not in ('work', 'short', 'person') or not target_id:
                skipped += 1
                continue

            awarded = Awarded(
                award_id=award_id,
                category_id=w.get('category_id'),
                year=w.get('year'),
            )
            if match_type == 'work':
                if target_id in work_ids:
                    skipped += 1
                    continue
                awarded.work_id = target_id
                work_ids.add(target_id)
            elif match_type == 'short':
                if target_id in story_ids:
                    skipped += 1
                    continue
                awarded.story_id = target_id
                story_ids.add(target_id)
            else:
                if target_id in person_ids:
                    skipped += 1
                    continue
                awarded.person_id = target_id
                person_ids.add(target_id)

            session.add(awarded)
            created += 1

        session.commit()
    except SQLAlchemyError as exp:
        session.rollback()
        app.logger.error(f'save_import: Tietokantavirhe. {exp}.')
        return ResponseType(f'save_import: Tietokantavirhe. {exp}.',
                            HttpResponseCode.INTERNAL_SERVER_ERROR.value)

    return ResponseType({"created": created, "skipped": skipped},
                        HttpResponseCode.OK.value)
