"""
ISFDB award-import helpers.

Scrapes award winners from ISFDB (isfdb.org) award-category pages and
matches them against the local database. Used by the per-award "import
winners from ISFDB" workflow.

Item type convention (matches award_import_source.item_type):
    0 = Work, 1 = Short story, 2 = Both (novella).
This is the ISFDB scraper convention and is distinct from
awardcategory.type (0 = personal, 1 = novel, 2 = short story).
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from sqlalchemy import func
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
    """A single winner row scraped from an ISFDB award-category page."""
    year: Optional[int]
    title: str
    author: str


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
                      ) -> Tuple[set, set]:
    """Return (work_ids, story_ids) already recorded for this award.

    These are treated as authoritative: the importer never duplicates,
    replaces or removes them.
    """
    rows = session.query(Awarded.work_id, Awarded.story_id).filter(
        Awarded.award_id == award_id).all()
    work_ids = {r.work_id for r in rows if r.work_id is not None}
    story_ids = {r.story_id for r in rows if r.story_id is not None}
    return work_ids, story_ids


_LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+")


def _strip_leading_article(title: str) -> str:
    """Lowercase a title and drop a leading English article."""
    return _LEADING_ARTICLE_RE.sub("", title.lower().strip()).strip()


def _title_match_variants(title: str) -> set:
    """Title forms to match, tolerating a leading article on either side.

    The database sometimes stores a leading article the original title
    lacks (or vice versa), e.g. 'The Speaker for the Dead' vs 'Speaker for
    the Dead', so we match the raw title, the article-stripped form and the
    article-prefixed forms.
    """
    low = title.lower().strip()
    stripped = _strip_leading_article(low)
    variants = {low, stripped, f"the {stripped}", f"a {stripped}",
                f"an {stripped}"}
    variants.discard("")
    return variants


def _match_title(session: Any, model: Any, title: str) -> List[Any]:
    """Match on orig_title, case-insensitively and ignoring a leading
    article. Returns matching rows."""
    variants = _title_match_variants(title)
    return session.query(model).filter(
        func.lower(model.orig_title).in_(variants)).all()


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
_WORK_CATEGORY_TYPE = 1
_SHORT_CATEGORY_TYPE = 2


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
                 work_ids: set, story_ids: set) -> Dict[str, Any]:
    """Match one scraped winner and build a preview entry dict."""
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
            m for m in _match_title(session, model, winner.title)
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
    if matched is not None and cat_type is not None:
        entry["target_id"] = matched.id
        entry["target_title"] = matched.title
        entry["category_id"] = _resolve_category_id(
            category_lookup, our_category, cat_type)

    return entry


def preview_import(award_id: int) -> ResponseType:
    """
    Scrape an award's ISFDB sources and match winners against the DB.

    Returns a preview: every scraped winner with its match status
    (new / awarded / not_found / ambiguous). Nothing is written.
    """
    session = new_session()

    award = session.query(Award).filter(Award.id == award_id).first()
    if not award:
        return ResponseType('Palkintoa ei löydy.',
                            HttpResponseCode.NOT_FOUND.value)

    sources = session.query(AwardImportSource).filter(
        AwardImportSource.award_id == award_id).order_by(
        AwardImportSource.id).all()
    if not sources:
        return ResponseType(
            'Tälle palkinnolle ei ole ISFDB-tuontilähdettä.',
            HttpResponseCode.BAD_REQUEST.value)

    category_lookup = _category_lookup(session)
    work_ids, story_ids = _existing_awarded(session, award_id)

    entries: List[Dict[str, Any]] = []
    errors: List[str] = []
    for source in sources:
        try:
            scraped = parse_award_category(source.isfdb_category_id,
                                           source.item_type)
        except requests.RequestException as exc:
            errors.append(
                f'ISFDB {source.isfdb_category_id}: {exc}')
            continue
        for winner in scraped.winners:
            entries.append(_build_entry(
                session, winner, source.item_type, scraped.category,
                source.our_category, category_lookup, work_ids, story_ids))

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

    Only adds rows: an item already awarded for this award (by work_id or
    story_id) is skipped, never duplicated or replaced. Person awards are
    never touched.

    Request body: {"data": {"winners": [
        {"match_type": "work"|"short", "target_id": <int>,
         "category_id": <int|null>, "year": <int|null>}, ...]}}
    """
    session = new_session()

    award = session.query(Award).filter(Award.id == award_id).first()
    if not award:
        return ResponseType('Palkintoa ei löydy.',
                            HttpResponseCode.NOT_FOUND.value)

    data = params.get('data', {})
    winners = data.get('winners', [])

    work_ids, story_ids = _existing_awarded(session, award_id)

    created = 0
    skipped = 0
    try:
        for w in winners:
            match_type = w.get('match_type')
            target_id = w.get('target_id')
            if match_type not in ('work', 'short') or not target_id:
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
            else:
                if target_id in story_ids:
                    skipped += 1
                    continue
                awarded.story_id = target_id
                story_ids.add(target_id)

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
