#!/usr/bin/env python3
"""
Compare award-winner import results between ISFDB and sfadb.

The two sources format titles/authors differently, so we don't compare
scraped text. Instead we compare what would actually be written to the
database: the set of matched winners as (match_type, target_id,
category_id, year) tuples produced by the shared matcher. Both sources
should resolve to the same local works/stories, categories and years.

Workflow (two phases):

  1. Now, while the ISFDB scraper still works, capture the reference:

         python scripts/compare_award_sources.py save --out isfdb_ref.json

     (Run this somewhere ISFDB is reachable, e.g. dev.)

  2. Once the sfadb parser is ready (preview_import scraping sfadb, or
     accepting source="sfadb"), verify it matches the reference:

         python scripts/compare_award_sources.py compare --ref isfdb_ref.json

     Exit code is 0 when every award's saved-row set matches, else 1.

Comparison is stable across changes to the awarded table (an item counts
as "matched" whether it is new or already awarded), so the reference does
not go stale if winners get imported in between.
"""

import argparse
import datetime
import json
import os
import sys

# Make the app package importable when run as a plain script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.impl_award_import import (  # noqa: E402
    STATUS_AWARDED,
    STATUS_NEW,
    preview_import,
)

# A representative mix: single/multi-category, work/short, and foreign
# (original-language title) awards.
DEFAULT_AWARDS = [
    2,   # Hugo
    3,   # Nebula
    4,   # Locus
    31,  # Imaginaire  (French-language + foreign categories)
    32,  # Kurd Lasswitz Preis (German-language + foreign categories)
]


def _preview(award_id: int, source: str):
    """Call preview_import, passing source= if that param exists yet."""
    try:
        return preview_import(award_id, source=source)  # type: ignore[call-arg]
    except TypeError:
        # Current signature has no source param (ISFDB only).
        return preview_import(award_id)


def _saved_rows(award_id: int, source: str):
    """The DB rows an import would ensure for this award.

    Returns a sorted list of [match_type, target_id, category_id, year]
    for every winner that matched a local work/story (status new or
    awarded). Returns None if the award has no import sources / errors.
    """
    resp = _preview(award_id, source)
    if resp.status != 200:
        return None, str(resp.response)
    data = resp.response
    rows = []
    for e in data["entries"]:
        if e["status"] in (STATUS_NEW, STATUS_AWARDED):
            rows.append([e["match_type"], e["target_id"],
                         e["category_id"], e["year"]])
    rows.sort(key=lambda r: (r[0], r[1] or 0, r[2] or 0, r[3] or 0))
    return {"name": data["award_name"], "rows": rows,
            "errors": data.get("errors", [])}, None


def cmd_save(args):
    result = {
        "source": args.source,
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "awards": {},
    }
    for award_id in args.awards:
        data, err = _saved_rows(award_id, args.source)
        if data is None:
            print(f"  award {award_id}: skipped ({err})", file=sys.stderr)
            continue
        result["awards"][str(award_id)] = data
        print(f"  award {award_id} {data['name']!r}: {len(data['rows'])} "
              f"saved rows"
              + (f" ({len(data['errors'])} scrape errors)"
                 if data["errors"] else ""))
    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(result, fp, ensure_ascii=False, indent=2)
    print(f"\nWrote {args.out} ({len(result['awards'])} awards, "
          f"source={args.source}).")


def cmd_compare(args):
    with open(args.ref, encoding="utf-8") as fp:
        ref = json.load(fp)
    ref_source = ref.get("source", "?")
    print(f"Reference source: {ref_source}  |  current source: {args.source}\n")

    overall_ok = True
    for award_id_str, ref_data in ref["awards"].items():
        award_id = int(award_id_str)
        cur, err = _saved_rows(award_id, args.source)
        name = ref_data["name"]
        if cur is None:
            print(f"award {award_id} {name!r}: CURRENT FAILED ({err})")
            overall_ok = False
            continue

        ref_set = {tuple(r) for r in ref_data["rows"]}
        cur_set = {tuple(r) for r in cur["rows"]}
        missing = ref_set - cur_set   # ISFDB found, current source missed
        extra = cur_set - ref_set     # current source found, ISFDB didn't

        if not missing and not extra:
            print(f"award {award_id} {name!r}: OK "
                  f"({len(ref_set)} saved rows match)")
            continue

        overall_ok = False
        print(f"award {award_id} {name!r}: MISMATCH "
              f"(ref={len(ref_set)} cur={len(cur_set)})")
        for r in sorted(missing):
            print(f"    only in {ref_source} (ref): {list(r)}")
        for r in sorted(extra):
            print(f"    only in {args.source} (cur): {list(r)}")

    print("\n" + ("ALL MATCH" if overall_ok else "DIFFERENCES FOUND"))
    return 0 if overall_ok else 1


def _award_list(value: str):
    return [int(x) for x in value.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_save = sub.add_parser("save", help="capture reference results")
    p_save.add_argument("--out", default="award_source_ref.json")
    p_save.add_argument("--source", default="isfdb")
    p_save.add_argument("--awards", type=_award_list, default=DEFAULT_AWARDS)
    p_save.set_defaults(func=cmd_save)

    p_cmp = sub.add_parser("compare", help="compare current source to ref")
    p_cmp.add_argument("--ref", default="award_source_ref.json")
    p_cmp.add_argument("--source", default="sfadb")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    rc = args.func(args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
