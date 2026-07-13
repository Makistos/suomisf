"""
Seed the award_import_source table (migration 029).

Scrape-to-discover: for each award below we know which ISFDB
award-category ids to fetch and their item type (0=Work, 1=Short story,
2=Both). We scrape each page to read its ISFDB category name, map it to a
local category via impl_award_import.CATEGORY_MAP, and upsert a row.

The award -> ISFDB category grouping is transcribed from
scripts/get-awards.py (its comment groups), keyed by the exact local
award name. Awards that ISFDB tracks but this database does not (Andre
Norton Award, Shirley Jackson Award) are intentionally omitted.

Run once (idempotent):
    python -m scripts.seed_award_import_sources
"""

import sys
import time

from app.route_helpers import new_session
from app.orm_decl import Award, AwardImportSource
from app.impl_award_import import CATEGORY_MAP, parse_award_category

# Local award name -> list of (isfdb_category_id, item_type).
# item_type: 0 = Work, 1 = Short story, 2 = Both (novella).
AWARD_SOURCES = {
    "Apollo": [(16, 0)],
    "Bram Stoker Award": [
        (498, 0), (497, 0), (632, 0), (503, 0), (507, 0),
        (500, 2), (499, 1), (510, 1), (496, 0), (505, 0),
    ],
    "Arthur C. Clarke -palkinto": [(140, 0)],
    "Campbell Memorial Award": [(130, 0)],
    "Carnegie-mitali": [(618, 0)],
    "British Fantasy Award": [
        (586, 0), (75, 0), (585, 0), (88, 2), (89, 1),
        (90, 1), (80, 0), (76, 0),
    ],
    "British Science Fiction Award": [(120, 0), (1028, 0), (121, 1), (1096, 0)],
    "Goodreads Choice Awards": [
        (731, 0), (730, 0), (736, 0), (732, 0), (733, 0),
        (735, 0), (738, 0), (734, 0),
    ],
    "Hugo": [(261, 0), (262, 2)],
    "Imaginaire": [
        (290, 0), (287, 1), (699, 0),  # foreign novel / short / youth
        (292, 0),                      # French-language novel
        (288, 1),                      # French-language short story
        (286, 0), (698, 0),            # youth novel (general / French)
    ],
    "Kurd Lasswitz Preis": [
        (686, 0), (685, 0),          # foreign novel / work
        (677, 0),                    # German-language novel
        (678, 1), (691, 1), (680, 1),  # German-language short fiction
        (679, 2),                    # German-language novelette/novella
    ],
    "Locus": [
        (375, 0), (347, 0), (350, 0), (351, 0), (349, 0), (382, 0),
        (361, 2), (360, 1), (378, 1), (377, 1), (338, 0), (379, 0), (329, 0),
    ],
    "Mythopoeic": [(400, 0), (401, 0), (1110, 0), (402, 0)],
    "Nebula": [(413, 0), (415, 2), (414, 1), (418, 1), (1029, 0)],
    "Philip K. Dick Award": [(423, 0)],
    "Premio Ignotus": [(748, 0), (749, 1), (745, 0)],
    "Retro Hugo": [(439, 0), (441, 2), (440, 1), (446, 1)],
    "Sidewise": [(520, 0), (521, 1)],
    "Theodore Sturgeon Award": [(768, 1)],
    "World Fantasy Award": [
        (532, 0), (667, 0), (533, 2), (534, 1), (531, 0), (528, 0), (529, 0),
    ],
}

# Be polite to ISFDB between requests.
REQUEST_DELAY_SECONDS = 0.5


def seed():
    session = new_session()

    awards = {a.name: a.id for a in session.query(Award).all()}

    inserted = 0
    updated = 0
    unmapped = []
    errors = []

    for award_name, sources in AWARD_SOURCES.items():
        award_id = awards.get(award_name)
        if award_id is None:
            errors.append(f"Award not found in DB: {award_name!r}")
            continue

        for isfdb_category_id, item_type in sources:
            try:
                scraped = parse_award_category(isfdb_category_id, item_type)
            except Exception as exc:  # noqa: BLE001 - report and continue
                errors.append(
                    f"{award_name} cat {isfdb_category_id}: fetch failed: {exc}")
                continue
            time.sleep(REQUEST_DELAY_SECONDS)

            our_category = CATEGORY_MAP.get(scraped.category) or None
            if our_category is None:
                unmapped.append(
                    f"{award_name}: ISFDB category {scraped.category!r} "
                    f"(id {isfdb_category_id}) is unmapped")

            existing = session.query(AwardImportSource).filter(
                AwardImportSource.award_id == award_id,
                AwardImportSource.isfdb_category_id == isfdb_category_id,
            ).first()

            if existing:
                if (existing.item_type != item_type
                        or existing.our_category != our_category):
                    existing.item_type = item_type
                    existing.our_category = our_category
                    updated += 1
            else:
                session.add(AwardImportSource(
                    award_id=award_id,
                    isfdb_category_id=isfdb_category_id,
                    item_type=item_type,
                    our_category=our_category,
                ))
                inserted += 1
            print(f"  {award_name} <- ISFDB {isfdb_category_id} "
                  f"{scraped.category!r} -> {our_category!r} "
                  f"({len(scraped.winners)} winners)")

    session.commit()

    print(f"\nInserted: {inserted}, Updated: {updated}")
    if unmapped:
        print(f"\nUnmapped categories ({len(unmapped)}):")
        for u in unmapped:
            print(f"  - {u}")
    if errors:
        print(f"\nErrors ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)


if __name__ == "__main__":
    seed()
