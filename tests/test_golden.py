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
    candidate_paths,
    classify_snapshot,
    compare_snapshot_dirs,
    dump_database,
    golden_path,
    parse_failed,
    promote_candidate,
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


def make_candidate(tmp_path, report, failed=()):
    """golden (b'old') + candidate (b'new') with snapshots and report.

    Committed snapshots: keep, gone. Candidate snapshots: keep, new,
    _snapshot_summary.
    """
    g = tmp_path / 'golden.dump'
    g.write_bytes(b'old')
    cand, cand_snaps, rep = candidate_paths(g)
    cand.write_bytes(b'new')
    for name in ('keep', 'new', '_snapshot_summary'):
        write(cand_snaps / f'{name}.json', snap({'v': 'candidate'}))
    snaps = tmp_path / 'snaps'
    for name in ('keep', 'gone'):
        write(snaps / f'{name}.json', snap({'v': 'committed'}))
    write(rep, {'snapshots': report, 'failed_tests': list(failed)})
    return g, snaps


def test_promote_without_candidate(tmp_path):
    g = tmp_path / 'golden.dump'
    g.write_bytes(b'old')
    assert promote_candidate(g, tmp_path / 'snaps') == 1
    assert g.read_bytes() == b'old'


def test_promote_refuses_structure_without_force(tmp_path):
    g, snaps = make_candidate(tmp_path, report={'works': 'structure'})
    assert promote_candidate(g, snaps) == 2
    assert g.read_bytes() == b'old'
    assert promote_candidate(g, snaps, force=True) == 0
    assert g.read_bytes() == b'new'


def test_promote_refuses_failed_tests_without_force(tmp_path):
    g, snaps = make_candidate(
        tmp_path, report={'keep': 'data'},
        failed=['tests/api/test_misc.py::test_x'],
    )
    assert promote_candidate(g, snaps) == 2
    assert g.read_bytes() == b'old'


def test_parse_failed():
    out = ('FAILED tests/a.py::test_one - AssertionError: x\n'
           'ERROR tests/b.py::test_two - RuntimeError\n'
           '1 failed, 1 error, 10 passed in 3.0s\n')
    assert parse_failed(out) == [
        'tests/a.py::test_one', 'tests/b.py::test_two']


def test_promote_success(tmp_path):
    g, snaps = make_candidate(
        tmp_path,
        report={'keep': 'data', 'gone': 'removed', 'new': 'added'},
    )
    assert promote_candidate(g, snaps) == 0
    assert g.read_bytes() == b'new'
    assert g.with_name('golden.previous.dump').read_bytes() == b'old'
    assert sorted(p.stem for p in snaps.glob('*.json')) == [
        '_snapshot_summary', 'keep', 'new']
    kept = json.loads((snaps / 'keep.json').read_text(encoding='utf-8'))
    assert kept['response'] == {'v': 'candidate'}
    assert not any(p.exists() for p in candidate_paths(g))
