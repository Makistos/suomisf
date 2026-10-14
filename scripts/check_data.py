"""
Look for data oddities in the database: impossible values, probable
duplicates, unused records and stray whitespace.

Every check is a read-only query; nothing is changed. Each prints how
many rows it found and the first few of them. See docs/data-checks.md.

Usage:
    python scripts/check_data.py              # all checks, 10 rows each
    python scripts/check_data.py --all        # every row
    python scripts/check_data.py --rows 30    # 30 rows each
    python scripts/check_data.py --only edition_pages person_unused
    python scripts/check_data.py --list       # list the checks
    python scripts/check_data.py --sql edition_pages   # print the query
    python scripts/check_data.py --format markdown --all \\
        > docs/data-check-results.md

Confirmed false positives go in scripts/check_data_ignore.txt.
"""
import argparse
import os
import sys
from datetime import date
from typing import (Any, Dict, List, NamedTuple, Optional, Sequence, Set,
                    Tuple)

import dotenv
from sqlalchemy import create_engine, text

directory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
dotenv.load_dotenv(os.path.join(directory_path, '.env'))
dotenv.load_dotenv(os.path.join(directory_path, '../.env'))


class Check(NamedTuple):
    key: str
    group: str
    title: str
    sql: str
    # How many leading columns identify a row (for the ignore list).
    id_cols: int = 1


# Binding types (bindingtype table).
PAPERBACK = 2
HARDBACK = 3

# Expression that is true when a person takes part in nothing.
_PERSON_UNUSED = """
    NOT EXISTS (SELECT 1 FROM workcontributor c
                WHERE p.id IN (c.person_id, c.real_person_id))
    AND NOT EXISTS (SELECT 1 FROM editioncontributor c
                    WHERE p.id IN (c.person_id, c.real_person_id))
    AND NOT EXISTS (SELECT 1 FROM storycontributor c
                    WHERE p.id IN (c.person_id, c.real_person_id))
    AND NOT EXISTS (SELECT 1 FROM issuecontributor c
                    WHERE c.person_id = p.id)
    AND NOT EXISTS (SELECT 1 FROM issueeditor c WHERE c.person_id = p.id)
    AND NOT EXISTS (SELECT 1 FROM articleauthor c
                    WHERE c.person_id = p.id)
    AND NOT EXISTS (SELECT 1 FROM articleperson c
                    WHERE c.person_id = p.id)
    AND NOT EXISTS (SELECT 1 FROM awarded c WHERE c.person_id = p.id)
    AND NOT EXISTS (SELECT 1 FROM alias c
                    WHERE p.id IN (c.alias, c.realname))
"""

# Columns whose text should have no leading, trailing or double spaces.
_SPACES = "{col} <> btrim({col}) OR {col} LIKE '%  %'"

CHECKS: List[Check] = [
    # --- Wrong values ---------------------------------------------------
    Check('edition_year', 'Wrong values',
          'Editions with a missing or impossible year (before 1850 or '
          'in the future)',
          """SELECT e.id, e.title, e.pubyear, p.name AS publisher
             FROM edition e LEFT JOIN publisher p ON p.id = e.publisher_id
             WHERE e.pubyear IS NULL OR e.pubyear < 1850
                OR e.pubyear > extract(year FROM now()) + 1
             ORDER BY e.pubyear"""),
    Check('edition_pages', 'Wrong values',
          'Editions with fewer than 10 or more than 2000 pages (often a '
          'year typed as pages)',
          """SELECT id, title, pubyear, pages FROM edition
             WHERE pages < 10 OR pages > 2000 ORDER BY pages"""),
    Check('edition_before_work', 'Wrong values',
          'Editions published before the original work',
          """SELECT e.id, e.title, e.pubyear, w.id AS work_id,
                    w.pubyear AS work_year
             FROM edition e JOIN work w ON w.id = e.work_id
             WHERE e.pubyear < w.pubyear"""),
    Check('work_year', 'Wrong values',
          'Works with an impossible original year',
          """SELECT id, title, pubyear FROM work
             WHERE pubyear < -1000
                OR pubyear > extract(year FROM now()) + 1"""),
    Check('isbn_format', 'Wrong values',
          'ISBNs without 10 or 13 digits',
          """SELECT id, title, isbn FROM edition
             WHERE isbn <> ''
               AND length(regexp_replace(isbn, '[^0-9Xx]', '', 'g'))
                   NOT IN (10, 13)"""),
    Check('person_dates', 'Wrong values',
          'People who died before they were born, lived over 110 '
          'years or are born in the future',
          """SELECT id, name, dob, dod FROM person
             WHERE dod < dob OR dod - dob > 110
                OR dob > extract(year FROM now())"""),
    Check('issue_year', 'Wrong values',
          'Magazine issues with a missing or impossible year',
          """SELECT i.id, m.name AS magazine, i.number, i.year
             FROM issue i JOIN magazine m ON m.id = i.magazine_id
             WHERE i.year IS NULL OR i.year < 1850
                OR i.year > extract(year FROM now()) + 1"""),
    Check('lookup_ids', 'Wrong values',
          'Editions pointing to a binding, format or size that does '
          'not exist',
          """SELECT id, title, binding_id, format_id, size FROM edition
             WHERE binding_id NOT IN (SELECT id FROM bindingtype)
                OR format_id NOT IN (SELECT id FROM format)
                OR size NOT IN (SELECT id FROM publicationsize)"""),

    # --- Probable duplicates --------------------------------------------
    Check('edition_number', 'Probable duplicates',
          'Editions of the same work and version sharing an edition '
          'number. Allowed: a paperback and a hardback of the same '
          'year. "same" marks pairs with equal publisher, year, ISBN '
          'and binding: almost certainly one book entered twice',
          f"""SELECT a.id AS id_a, b.id AS id_b, a.title, a.editionnum,
                    a.pubyear AS year_a, b.pubyear AS year_b,
                    (SELECT name FROM bindingtype WHERE id = a.binding_id)
                        AS binding_a,
                    (SELECT name FROM bindingtype WHERE id = b.binding_id)
                        AS binding_b,
                    coalesce(a.isbn, '') AS isbn_a,
                    coalesce(b.isbn, '') AS isbn_b,
                    CASE WHEN a.publisher_id = b.publisher_id
                          AND a.pubyear = b.pubyear
                          AND coalesce(a.isbn, '') = coalesce(b.isbn, '')
                          AND a.binding_id IS NOT DISTINCT FROM
                              b.binding_id
                         THEN 'same' ELSE '' END AS verdict
             FROM edition a
             JOIN edition b ON b.work_id = a.work_id AND b.id > a.id
                AND coalesce(b.version, 1) = coalesce(a.version, 1)
                AND b.editionnum = a.editionnum
             WHERE NOT (a.pubyear = b.pubyear
                        AND least(a.binding_id, b.binding_id) = {PAPERBACK}
                        AND greatest(a.binding_id, b.binding_id)
                            = {HARDBACK})
             ORDER BY verdict DESC, a.title""", 2),
    Check('isbn_shared', 'Probable duplicates',
          'One ISBN on editions of different works (copy-paste errors, '
          'or a set sold under one ISBN)',
          """SELECT e.isbn, e.id, e.title, e.pubyear, e.work_id
             FROM edition e
             WHERE e.isbn IN (SELECT isbn FROM edition WHERE isbn <> ''
                              GROUP BY isbn
                              HAVING count(DISTINCT work_id) > 1)
             ORDER BY e.isbn"""),
    Check('person_name', 'Probable duplicates',
          'People with the same name (ignoring case and spaces)',
          """SELECT string_agg(id::text, ',' ORDER BY id) AS ids,
                    lower(btrim(name)) AS name
             FROM person GROUP BY 2 HAVING count(*) > 1"""),
    Check('story_title', 'Probable duplicates',
          'Translated short stories with the same title, original '
          'title, authors and translators',
          """WITH s AS (
                 SELECT s.id, lower(btrim(s.title)) AS title_key,
                        s.title,
                        lower(btrim(s.orig_title)) AS orig_key,
                        btrim(s.orig_title) AS orig,
                        (SELECT string_agg(c.person_id::text, ','
                                           ORDER BY c.person_id)
                         FROM storycontributor c
                         WHERE c.shortstory_id = s.id
                           AND c.role_id = 1) AS authors,
                        (SELECT string_agg(c.person_id::text, ','
                                           ORDER BY c.person_id)
                         FROM storycontributor c
                         WHERE c.shortstory_id = s.id
                           AND c.role_id = 2) AS translators,
                        (SELECT string_agg(p.name, '; ' ORDER BY p.name)
                         FROM storycontributor c
                         JOIN person p ON p.id = c.person_id
                         WHERE c.shortstory_id = s.id
                           AND c.role_id = 1) AS author_names,
                        (SELECT string_agg(p.name, '; ' ORDER BY p.name)
                         FROM storycontributor c
                         JOIN person p ON p.id = c.person_id
                         WHERE c.shortstory_id = s.id
                           AND c.role_id = 2) AS translator_names
                 FROM shortstory s
                 WHERE coalesce(btrim(s.orig_title), '') <> '')
             SELECT string_agg(id::text, ',' ORDER BY id) AS ids,
                    min(title) AS title, min(orig) AS orig,
                    min(author_names) AS authors,
                    min(translator_names) AS translators
             FROM s GROUP BY title_key, orig_key, authors, translators
             HAVING count(*) > 1 ORDER BY title_key"""),
    Check('tag_name', 'Probable duplicates',
          'Tags with the same name (ignoring case and spaces)',
          """SELECT string_agg(id::text, ',' ORDER BY id) AS ids,
                    lower(btrim(name)) AS name
             FROM tag GROUP BY 2 HAVING count(*) > 1"""),
    Check('publisher_name', 'Probable duplicates',
          'Publishers with the same name (ignoring case and spaces)',
          """SELECT string_agg(id::text, ',' ORDER BY id) AS ids,
                    lower(btrim(name)) AS name
             FROM publisher GROUP BY 2 HAVING count(*) > 1"""),
    Check('link_twice', 'Probable duplicates',
          'The same link twice on one person, work or edition',
          """SELECT 'person' AS kind, person_id AS id, link
             FROM personlink GROUP BY 2, 3 HAVING count(*) > 1
             UNION ALL
             SELECT 'work', work_id, link
             FROM worklink GROUP BY 2, 3 HAVING count(*) > 1
             UNION ALL
             SELECT 'edition', edition_id, link
             FROM editionlink GROUP BY 2, 3 HAVING count(*) > 1""", 2),
    Check('contributor_twice', 'Probable duplicates',
          'The same person twice in the same role on one work, edition '
          'or story',
          """SELECT 'work' AS kind, work_id AS id, person_id, role_id
             FROM workcontributor GROUP BY 2, 3, 4 HAVING count(*) > 1
             UNION ALL
             SELECT 'edition', edition_id, person_id, role_id
             FROM editioncontributor GROUP BY 2, 3, 4
             HAVING count(*) > 1
             UNION ALL
             SELECT 'story', shortstory_id, person_id, role_id
             FROM storycontributor GROUP BY 2, 3, 4
             HAVING count(*) > 1""", 4),
    Check('awarded_twice', 'Probable duplicates',
          'The same award given twice to the same target',
          """SELECT string_agg(id::text, ',' ORDER BY id) AS ids,
                    award_id, category_id, year, person_id, work_id,
                    story_id
             FROM awarded GROUP BY 2, 3, 4, 5, 6, 7
             HAVING count(*) > 1"""),
    Check('issue_twice', 'Probable duplicates',
          'Magazine issues with the same number in the same year',
          """SELECT string_agg(id::text, ',' ORDER BY id) AS ids,
                    magazine_id, year, number, number_extra
             FROM issue WHERE number IS NOT NULL
             GROUP BY 2, 3, 4, 5 HAVING count(*) > 1"""),
    Check('story_order', 'Probable duplicates',
          'Two stories in the same position of one edition or work',
          """SELECT 'edition' AS kind, edition_id AS id, order_num
             FROM editionshortstory WHERE order_num IS NOT NULL
             GROUP BY 2, 3 HAVING count(*) > 1
             UNION ALL
             SELECT 'work', work_id, order_num
             FROM work_shortstory WHERE order_num IS NOT NULL
             GROUP BY 2, 3 HAVING count(*) > 1""", 3),
    Check('alias_loop', 'Probable duplicates',
          'Aliases pointing to themselves or to each other',
          """SELECT a.alias, a.realname FROM alias a
             WHERE a.alias = a.realname
                OR EXISTS (SELECT 1 FROM alias b
                           WHERE b.alias = a.realname
                             AND b.realname = a.alias)""", 2),

    # --- Unused records -------------------------------------------------
    Check('person_unused', 'Unused records',
          'People who take part in nothing',
          f"""SELECT p.id, p.name, p.dob, p.dod FROM person p
              WHERE {_PERSON_UNUSED} ORDER BY p.name"""),
    Check('publisher_unused', 'Unused records',
          'Publishers with no editions, magazines or publisher series',
          """SELECT p.id, p.name FROM publisher p
             WHERE NOT EXISTS (SELECT 1 FROM edition e
                               WHERE e.publisher_id = p.id)
               AND NOT EXISTS (SELECT 1 FROM magazine m
                               WHERE m.publisher_id = p.id)
               AND NOT EXISTS (SELECT 1 FROM pubseries s
                               WHERE s.publisher_id = p.id)
             ORDER BY p.name"""),
    Check('story_unused', 'Unused records',
          'Short stories in no edition, work or magazine issue',
          """SELECT s.id, s.title,
                    (SELECT count(*) FROM storycontributor c
                     WHERE c.shortstory_id = s.id) AS contributors
             FROM shortstory s
             WHERE NOT EXISTS (SELECT 1 FROM editionshortstory x
                               WHERE x.shortstory_id = s.id)
               AND NOT EXISTS (SELECT 1 FROM work_shortstory x
                               WHERE x.shortstory_id = s.id)
               AND NOT EXISTS (SELECT 1 FROM issuecontent x
                               WHERE x.shortstory_id = s.id)"""),
    Check('work_unused', 'Unused records',
          'Works with no editions',
          """SELECT w.id, w.title FROM work w
             WHERE NOT EXISTS (SELECT 1 FROM edition e
                               WHERE e.work_id = w.id)"""),
    Check('pubseries_unused', 'Unused records',
          'Publisher series with no editions',
          """SELECT s.id, s.name FROM pubseries s
             WHERE NOT EXISTS (SELECT 1 FROM edition e
                               WHERE e.pubseries_id = s.id)"""),
    Check('bookseries_unused', 'Unused records',
          'Book series with no works and no sub-series',
          """SELECT s.id, s.name FROM bookseries s
             WHERE NOT EXISTS (SELECT 1 FROM work w
                               WHERE w.bookseries_id = s.id)
               AND NOT EXISTS (SELECT 1 FROM bookseries c
                               WHERE c.parent_id = s.id)"""),
    Check('tag_unused', 'Unused records',
          'Tags on nothing',
          """SELECT t.id, t.name FROM tag t
             WHERE NOT EXISTS (SELECT 1 FROM worktag x
                               WHERE x.tag_id = t.id)
               AND NOT EXISTS (SELECT 1 FROM storytag x
                               WHERE x.tag_id = t.id)
               AND NOT EXISTS (SELECT 1 FROM articletag x
                               WHERE x.tag_id = t.id)
               AND NOT EXISTS (SELECT 1 FROM magazinetag x
                               WHERE x.tag_id = t.id)
               AND NOT EXISTS (SELECT 1 FROM issuetag x
                               WHERE x.tag_id = t.id)
               AND NOT EXISTS (SELECT 1 FROM persontag x
                               WHERE x.tag_id = t.id)"""),
    Check('magazine_empty', 'Unused records',
          'Magazines with no issues',
          """SELECT m.id, m.name FROM magazine m
             WHERE NOT EXISTS (SELECT 1 FROM issue i
                               WHERE i.magazine_id = m.id)"""),
    Check('issue_empty', 'Unused records',
          'Magazine issues with no contents',
          """SELECT i.id, m.name AS magazine, i.year, i.number
             FROM issue i JOIN magazine m ON m.id = i.magazine_id
             WHERE NOT EXISTS (SELECT 1 FROM issuecontent c
                               WHERE c.issue_id = i.id)
             ORDER BY m.name, i.year, i.number"""),

    # --- Whitespace -----------------------------------------------------
    Check('spaces_person', 'Whitespace',
          'Person names with extra spaces',
          f"""SELECT id, '[' || name || ']' AS name FROM person
              WHERE {_SPACES.format(col='name')}"""),
    Check('spaces_work', 'Whitespace',
          'Work titles with extra spaces',
          f"""SELECT id, '[' || title || ']' AS title FROM work
              WHERE {_SPACES.format(col='title')}"""),
    Check('spaces_edition', 'Whitespace',
          'Edition titles with extra spaces',
          f"""SELECT id, '[' || title || ']' AS title FROM edition
              WHERE {_SPACES.format(col='title')}"""),
    Check('spaces_story', 'Whitespace',
          'Short story titles with extra spaces',
          f"""SELECT id, '[' || title || ']' AS title FROM shortstory
              WHERE {_SPACES.format(col='title')}"""),
    Check('spaces_other', 'Whitespace',
          'Publisher, series, tag and magazine names with extra spaces',
          f"""SELECT 'publisher' AS kind, id, '[' || name || ']' AS name
              FROM publisher WHERE {_SPACES.format(col='name')}
              UNION ALL
              SELECT 'pubseries', id, '[' || name || ']'
              FROM pubseries WHERE {_SPACES.format(col='name')}
              UNION ALL
              SELECT 'bookseries', id, '[' || name || ']'
              FROM bookseries WHERE {_SPACES.format(col='name')}
              UNION ALL
              SELECT 'tag', id, '[' || name || ']'
              FROM tag WHERE {_SPACES.format(col='name')}
              UNION ALL
              SELECT 'magazine', id, '[' || name || ']'
              FROM magazine WHERE {_SPACES.format(col='name')}""", 2),
]


IGNORE_FILE = os.path.join(directory_path, 'scripts',
                           'check_data_ignore.txt')


def row_id(check: Check, row: Sequence[Any]) -> str:
    """The id a row has in the ignore list: its id columns, joined."""
    return ','.join(str(v) for v in row[:check.id_cols])


def read_ignores(path: str) -> Dict[Tuple[str, str], str]:
    """
    Read the ignore list: one "KEY ID reason" per line; # starts a
    comment. Returns {(key, id): reason}.
    """
    ignores: Dict[Tuple[str, str], str] = {}
    if not os.path.exists(path):
        return ignores
    with open(path, encoding='utf-8') as f:
        for num, line in enumerate(f, 1):
            line = line.split('#', 1)[0].strip()
            if not line:
                continue
            parts = line.split(None, 2)
            if len(parts) < 2:
                raise SystemExit(f'{path}:{num}: expected "KEY ID reason"')
            reason = parts[2] if len(parts) > 2 else ''
            ignores[(parts[0], parts[1])] = reason
    return ignores


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Look for data oddities. Read-only.')
    parser.add_argument('--only', nargs='+', metavar='KEY',
                        help='run only these checks')
    parser.add_argument('--rows', type=int, default=10,
                        help='rows to print per check (default 10)')
    parser.add_argument('--all', action='store_true',
                        help='print every row')
    parser.add_argument('--list', action='store_true',
                        help='list the checks and exit')
    parser.add_argument('--sql', metavar='KEY',
                        help='print the query of one check and exit')
    parser.add_argument('--ignore', metavar='FILE', default=IGNORE_FILE,
                        help='false positives to leave out (default '
                             'scripts/check_data_ignore.txt)')
    parser.add_argument('--format', choices=('text', 'markdown'),
                        default='text', help='output format (default text)')
    parser.add_argument('--show-ignored', action='store_true',
                        help='print ignored rows too, marked IGNORED')
    args = parser.parse_args()

    by_key = {c.key: c for c in CHECKS}
    if args.list:
        for c in CHECKS:
            print(f'{c.key:24} {c.group}: {c.title}')
        return 0
    if args.sql:
        if args.sql not in by_key:
            parser.error(f'unknown check: {args.sql}')
        print(f'SET search_path = suomisf;\n{by_key[args.sql].sql};')
        return 0
    unknown = [k for k in args.only or [] if k not in by_key]
    if unknown:
        parser.error(f'unknown check: {", ".join(unknown)}')
    checks = [c for c in CHECKS if not args.only or c.key in args.only]

    ignores = read_ignores(args.ignore)
    bad_keys = sorted({k for k, _ in ignores if k not in by_key})
    if bad_keys:
        parser.error(f'{args.ignore}: unknown check: {", ".join(bad_keys)}')

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL is not set (.env).', file=sys.stderr)
        return 2
    engine = create_engine(db_url)
    results: List[Result] = []
    used: Set[Tuple[str, str]] = set()
    with engine.connect() as conn:
        conn.execute(text('SET search_path = suomisf'))
        for c in checks:
            res = conn.execute(text(c.sql))
            result = Result(c, list(res.keys()), [], [])
            for row in res.fetchall():
                ident = (c.key, row_id(c, row))
                if ident in ignores:
                    used.add(ident)
                    result.ignored.append(
                        (row_id(c, row), ignores[ident]))
                else:
                    result.rows.append(tuple(row))
            results.append(result)

    # Ignore entries that matched nothing: fixed, or the id is wrong.
    ran = {c.key for c in checks}
    stale = sorted(k for k in ignores if k[0] in ran and k not in used)
    limit = None if args.all else args.rows
    if args.format == 'markdown':
        write_markdown(results, stale, limit, args.show_ignored)
    else:
        write_text(results, stale, limit, args.show_ignored)
    return 1 if any(r.rows for r in results) else 0


class Result(NamedTuple):
    check: Check
    columns: List[str]
    rows: List[Tuple[Any, ...]]
    # (row id, reason) of the rows left out by the ignore list
    ignored: List[Tuple[str, str]]


def _cell(value: Any) -> str:
    return '' if value is None else str(value)


def write_text(results: List[Result], stale: List[Tuple[str, str]],
               limit: Optional[int], show_ignored: bool) -> None:
    """Plain text: one block per check, rows separated by |."""
    print(f'Data checks {date.today().isoformat()}')
    group = None
    for r in results:
        c = r.check
        if c.group != group:
            group = c.group
            print(f'\n=== {group} ===')
        note = f' ({len(r.ignored)} ignored)' if r.ignored else ''
        print(f'\n[{c.key}] {c.title}: {len(r.rows)}{note}')
        shown = r.rows[:limit]
        for row in shown:
            print('    ' + ' | '.join(_cell(v) for v in row))
        if len(shown) < len(r.rows):
            print(f'    … {len(r.rows) - len(shown)} more '
                  f'(--only {c.key} --all)')
        if show_ignored:
            for ident, reason in r.ignored:
                print(f'    IGNORED {ident}: {reason}')
    if stale:
        print('\nIgnore entries that matched no row (remove them):')
        for key, ident in stale:
            print(f'    {key} {ident}')
    found = sum(bool(r.rows) for r in results)
    print(f'\n{found} of {len(results)} checks found something.')


def _md(value: Any) -> str:
    """A table cell: pipes escaped; text showing spaces in code."""
    cell = _cell(value).replace('|', '\\|').replace('\n', ' ')
    if cell.startswith('[') and cell.endswith(']'):
        return f'`{cell}`'
    return cell


def write_markdown(results: List[Result], stale: List[Tuple[str, str]],
                   limit: Optional[int], show_ignored: bool) -> None:
    """Markdown: a summary table, then a table per check with rows."""
    found = sum(bool(r.rows) for r in results)
    print(f'# Data checks {date.today().isoformat()}\n')
    print('Generated by `scripts/check_data.py --format markdown --all`; '
          'see `docs/data-checks.md` for how to read the checks. '
          f'{found} of {len(results)} checks found something.\n')
    print('| Group | Check | Rows | Ignored |')
    print('|---|---|--:|--:|')
    for r in results:
        key = r.check.key
        name = f'[{key}](#{key})' if r.rows else key
        print(f'| {r.check.group} | {name} | {len(r.rows)} | '
              f'{len(r.ignored) or ""} |')
    if stale:
        print('\n## Stale ignore entries\n')
        print('These entries in `scripts/check_data_ignore.txt` matched '
              'no row; remove them.\n')
        for key, ident in stale:
            print(f'- `{key} {ident}`')
    group = None
    for r in results:
        if not r.rows and not (show_ignored and r.ignored):
            continue
        c = r.check
        if c.group != group:
            group = c.group
            print(f'\n## {group}')
        print(f'\n### {c.key}\n')
        print(f'{c.title}. **{len(r.rows)}** rows'
              + (f', {len(r.ignored)} ignored.' if r.ignored else '.'))
        if r.rows:
            print()
            print('| ' + ' | '.join(r.columns) + ' |')
            print('|' + '---|' * len(r.columns))
            shown = r.rows[:limit]
            for row in shown:
                print('| ' + ' | '.join(_md(v) for v in row) + ' |')
            if len(shown) < len(r.rows):
                print(f'\n… {len(r.rows) - len(shown)} more '
                      f'(`--only {c.key} --all`).')
        if show_ignored and r.ignored:
            print('\nIgnored:\n')
            for ident, reason in r.ignored:
                print(f'- `{ident}`: {reason}')


if __name__ == '__main__':
    sys.exit(main())
