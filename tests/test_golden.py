"""Tests for tests/scripts/golden.py (golden test-data dump tooling).

Pure unit tests: no database, no network. Run with --skip-db-setup.
"""
import json
from pathlib import Path

from tests.scripts.golden import classify_snapshot, compare_snapshot_dirs


def snap(resp, ts='2026-01-01'):
    return {'metadata': {'generated_at': ts}, 'response': resp}


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def test_unchanged_ignores_metadata():
    old, new = snap({'a': 1}), snap({'a': 1}, ts='x')
    assert classify_snapshot(old, new) == 'unchanged'


def test_value_change_is_data():
    assert classify_snapshot(snap({'a': 1}), snap({'a': 2})) == 'data'


def test_empty_list_filled_is_data():
    old = snap({'tags': []})
    new = snap({'tags': [{'id': 1, 'name': 'x'}]})
    assert classify_snapshot(old, new) == 'data'


def test_null_to_object_is_data():
    old, new = snap({'p': None}), snap({'p': {'id': 1}})
    assert classify_snapshot(old, new) == 'data'


def test_added_key_in_shared_list_is_structure():
    old = snap({'data': [{'id': 1}]})
    new = snap({'data': [{'id': 2, 'subtitle': 's'}]})
    assert classify_snapshot(old, new) == 'structure'


def test_removed_key_is_structure():
    old, new = snap({'a': 1, 'b': 2}), snap({'a': 1})
    assert classify_snapshot(old, new) == 'structure'


def test_compare_dirs_added_removed(tmp_path):
    old, new = tmp_path / 'old', tmp_path / 'new'
    write(old / 'keep.json', snap({'a': 1}))
    write(old / 'gone.json', snap({'a': 1}))
    write(old / '_snapshot_summary.json', {'x': 1})
    write(new / 'keep.json', snap({'a': 2}))
    write(new / 'new.json', snap({'a': 1}))
    write(new / '_snapshot_summary.json', {'x': 2})
    assert compare_snapshot_dirs(old, new) == {
        'keep': 'data', 'gone': 'removed', 'new': 'added'}
