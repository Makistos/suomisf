"""
Tests for scripts/trim_names.py: the cleaning rule, and a run against
the test database inside a transaction that is rolled back.
"""
import importlib.util
import os

import pytest
from sqlalchemy import create_engine, text

_PATH = os.path.join(os.path.dirname(__file__), '..', 'scripts',
                     'trim_names.py')
_spec = importlib.util.spec_from_file_location('trim_names', _PATH)
assert _spec and _spec.loader
trim_names = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trim_names)


@pytest.mark.parametrize('value, expected', [
    ('  Luella Miller', 'Luella Miller'),
    ('Kuolinmessu ', 'Kuolinmessu'),
    ('Daniel Dark  -trilogia', 'Daniel Dark -trilogia'),
    ('  a   b  c ', 'a b c'),
    ('Ei muutosta', 'Ei muutosta'),
])
def test_clean(value, expected):
    assert trim_names.clean(value) == expected


def test_trim_and_log(app):  # pylint: disable=unused-argument
    """Names are trimmed, logged, and unique clashes are skipped."""
    # The app fixture points DATABASE_URL at the test database.
    url = os.environ['DATABASE_URL']
    assert 'suomisf_test' in url
    engine = create_engine(url)
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text('SET search_path = suomisf'))
            tag_id = conn.execute(text(
                "INSERT INTO tag (name) VALUES ('  trim  testi ') "
                'RETURNING id')).scalar()
            # A person whose trimmed name is already taken.
            taken = conn.execute(text(
                "INSERT INTO person (name) VALUES ('Trim Testi') "
                'RETURNING id')).scalar()
            clash_id = conn.execute(text(
                "INSERT INTO person (name) VALUES ('Trim  Testi') "
                'RETURNING id')).scalar()

            changes = trim_names.find_changes(conn)
            by_id = {(c.target.table, c.id): c for c in changes}
            assert by_id[('tag', tag_id)].new == 'trim testi'
            assert by_id[('person', clash_id)].clash == taken

            done = trim_names.apply_changes(conn, changes, None)
            assert done == sum(c.clash is None for c in changes)

            assert conn.execute(text(
                'SELECT name FROM tag WHERE id = :id'),
                {'id': tag_id}).scalar() == 'trim testi'
            assert conn.execute(text(
                'SELECT name FROM person WHERE id = :id'),
                {'id': clash_id}).scalar() == 'Trim  Testi'
            log = conn.execute(text(
                "SELECT field_name, action, old_value FROM log "
                "WHERE table_name = 'Asiasana' AND table_id = :id"),
                {'id': tag_id}).one()
            assert tuple(log) == ('Nimi', 'Päivitys', '  trim  testi ')
            # Nothing is left to trim but the skipped clash.
            left = trim_names.find_changes(conn)
            assert [(c.target.table, c.id) for c in left] == \
                [('person', clash_id)]
        finally:
            trans.rollback()
    engine.dispose()
