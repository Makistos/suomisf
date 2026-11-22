"""Tests for tests/scripts/golden.py (golden test-data dump tooling).

Pure unit tests: no database, no network. Run with --skip-db-setup.
"""
import json
import subprocess
from pathlib import Path

import pytest

from tests.scripts import golden
from tests.scripts.golden import (
    GoldenMissingError,
    classify_snapshot,
    compare_snapshot_dirs,
    dump_database,
    golden_path,
    restore_dump,
)


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


def test_golden_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv('SUOMISF_GOLDEN_DUMP', str(tmp_path / 'g.dump'))
    assert golden_path() == tmp_path / 'g.dump'


def test_golden_path_default(monkeypatch):
    monkeypatch.delenv('SUOMISF_GOLDEN_DUMP', raising=False)
    expected = Path.home() / '.local/share/suomisf/golden.dump'
    assert golden_path() == expected


def test_restore_missing_dump_raises_without_running_psql(
    monkeypatch, tmp_path
):
    calls = []
    monkeypatch.setattr(
        golden.subprocess, 'run', lambda *a, **k: calls.append(a)
    )
    with pytest.raises(GoldenMissingError, match='pdm run golden-refresh'):
        restore_dump(tmp_path / 'nope.dump')
    assert calls == []


def test_restore_refuses_main_db(tmp_path):
    f = tmp_path / 'g.dump'
    f.write_bytes(b'x')
    with pytest.raises(ValueError):
        restore_dump(f, 'suomisf')


def test_dump_failure_leaves_existing_file_and_no_partial(
    monkeypatch, tmp_path
):
    out = tmp_path / 'golden.dump'
    out.write_bytes(b'old')

    def fake_run(cmd, **k):
        Path(cmd[cmd.index('-f') + 1]).write_bytes(b'half')
        return subprocess.CompletedProcess(cmd, 1, '', 'disk full')

    monkeypatch.setattr(golden.subprocess, 'run', fake_run)
    with pytest.raises(RuntimeError, match='disk full'):
        dump_database('suomisf', out)
    assert out.read_bytes() == b'old'
    assert not out.with_name('golden.dump.partial').exists()
