"""
Trim extra spaces from names and titles: leading and trailing spaces
go, runs of spaces become one. These are the rows the spaces_* checks
of scripts/check_data.py find.

Without --apply nothing is changed; the script lists what it would do.
With --apply every change is written in one transaction and logged in
the change log (Päivitys, old value kept) under --user.

Usage:
    python scripts/trim_names.py                  # dry run, local
    python scripts/trim_names.py --apply --user mep
    python scripts/trim_names.py --prod           # dry run, production
    python scripts/trim_names.py --prod --apply --user mep

The database is DATABASE_URL from .env; --prod uses DATABASE_URL_PROD
and --db URL any other database.

A person or publisher whose trimmed name already belongs to another row
is left alone and reported: the names are unique, so the two are
probably the same and need merging by hand.
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, List, NamedTuple, Optional

import dotenv
from sqlalchemy import create_engine, text

directory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
dotenv.load_dotenv(os.path.join(directory_path, '.env'))
dotenv.load_dotenv(os.path.join(directory_path, '../.env'))


class Target(NamedTuple):
    table: str
    column: str
    # Names used in the change log (see table_locals in impl_logs.py).
    log_table: str
    log_field: str
    # The column has a unique index: a clash is skipped, not written.
    unique: bool = False


TARGETS: List[Target] = [
    Target('person', 'name', 'Henkilö', 'Nimi', unique=True),
    Target('work', 'title', 'Teos', 'Nimeke'),
    Target('edition', 'title', 'Painos', 'Nimeke'),
    Target('shortstory', 'title', 'Novelli', 'Nimi'),
    Target('publisher', 'name', 'Kustantaja', 'Nimi', unique=True),
    Target('pubseries', 'name', 'Julkaisusarja', 'Nimi'),
    Target('bookseries', 'name', 'Kirjasarja', 'Nimi'),
    Target('tag', 'name', 'Asiasana', 'Nimi'),
    Target('magazine', 'name', 'Lehti', 'Nimi'),
]

# Same condition as _SPACES in check_data.py.
_SPACES = "{col} <> btrim({col}) OR {col} LIKE '%  %'"


class Change(NamedTuple):
    target: Target
    id: int
    old: str
    new: str
    # Id of the row that already has the new name, if any.
    clash: Optional[int]


def clean(value: str) -> str:
    """Strip leading and trailing spaces and collapse runs of them."""
    return re.sub(' {2,}', ' ', value).strip(' ')


def find_changes(conn: Any) -> List[Change]:
    """Every name that needs trimming, with unique-name clashes."""
    changes: List[Change] = []
    for t in TARGETS:
        rows = conn.execute(text(
            f'SELECT id, {t.column} FROM {t.table} '
            f'WHERE {_SPACES.format(col=t.column)} ORDER BY id')).fetchall()
        for row_id, old in rows:
            new = clean(old)
            clash = None
            if t.unique:
                clash = conn.execute(text(
                    f'SELECT id FROM {t.table} '
                    f'WHERE {t.column} = :new AND id <> :id'),
                    {'new': new, 'id': row_id}).scalar()
            changes.append(Change(t, row_id, old, new, clash))
    return changes


def apply_changes(conn: Any, changes: List[Change],
                  user_id: Optional[int]) -> int:
    """Write the changes that don't clash and log each. Returns count."""
    now = datetime.now(timezone.utc)
    done = 0
    for c in changes:
        if c.clash is not None:
            continue
        t = c.target
        conn.execute(text(
            f'UPDATE {t.table} SET {t.column} = :new WHERE id = :id'),
            {'new': c.new, 'id': c.id})
        conn.execute(text(
            'INSERT INTO log (table_name, field_name, table_id, '
            'object_name, action, user_id, old_value, date) '
            "VALUES (:table, :field, :id, :name, 'Päivitys', :user, "
            ':old, :date)'),
            {'table': t.log_table, 'field': t.log_field, 'id': c.id,
             'name': c.new[:200], 'user': user_id, 'old': c.old[:500],
             'date': now})
        done += 1
    return done


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Trim extra spaces from names and titles.')
    parser.add_argument('--apply', action='store_true',
                        help='write the changes (default: dry run)')
    parser.add_argument('--user', metavar='NAME',
                        help='user the changes are logged under '
                             '(required with --apply)')
    where = parser.add_mutually_exclusive_group()
    where.add_argument('--prod', action='store_true',
                       help='use the production database '
                            '(DATABASE_URL_PROD in .env)')
    where.add_argument('--db', metavar='URL',
                       help='use this database (default DATABASE_URL '
                            'in .env)')
    args = parser.parse_args()
    if args.apply and not args.user:
        parser.error('--apply needs --user')

    var = 'DATABASE_URL_PROD' if args.prod else 'DATABASE_URL'
    db_url = args.db or os.environ.get(var)
    if not db_url:
        print(f'{var} is not set (.env).', file=sys.stderr)
        return 2
    engine = create_engine(db_url)
    # One transaction: either every change and its log row, or nothing.
    with engine.begin() as conn:
        conn.execute(text('SET search_path = suomisf'))
        user_id = None
        if args.user:
            user_id = conn.execute(
                text('SELECT id FROM "user" WHERE name = :name'),
                {'name': args.user}).scalar()
            if user_id is None:
                print(f'Unknown user: {args.user}', file=sys.stderr)
                return 2
        changes = find_changes(conn)
        for c in changes:
            note = (f'  SKIPPED: id {c.clash} already has this name'
                    if c.clash is not None else '')
            print(f'{c.target.table} {c.id}: [{c.old}] -> [{c.new}]{note}')
        clashes = sum(c.clash is not None for c in changes)
        if args.apply:
            done = apply_changes(conn, changes, user_id)
            print(f'\nTrimmed {done} names, skipped {clashes}.')
        else:
            print(f'\n{len(changes) - clashes} names to trim, {clashes} '
                  'to skip. Dry run: nothing changed (--apply writes).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
