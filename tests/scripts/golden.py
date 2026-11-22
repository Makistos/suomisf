#!/usr/bin/env python3
"""Golden test-data dump: tests restore suomisf_test from a pinned dump.

Tests (pytest and the frontend E2E suite) no longer clone the live dev
database, so refreshing it from production cannot break them. Refreshing
the test data is a deliberate step that reports what would change.

Usage:
    pdm run golden-refresh    # candidate dump + snapshot/test report
    pdm run golden-accept     # adopt the candidate (--force to override)
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Literal, Set, Tuple

SnapshotClass = Literal['unchanged', 'data', 'structure', 'added', 'removed']

DB_USER = 'mep'
MAIN_DB_NAME = 'suomisf'
TEST_DB_NAME = 'suomisf_test'
# Outside the repo on purpose: the dump holds real user data (emails,
# password hashes) and the repo is public.
DEFAULT_GOLDEN = '~/.local/share/suomisf/golden.dump'


class GoldenMissingError(RuntimeError):
    """No golden dump: tests must not silently fall back to the live DB."""


def golden_path() -> Path:
    return Path(
        os.environ.get('SUOMISF_GOLDEN_DUMP', DEFAULT_GOLDEN)
    ).expanduser()


def candidate_paths(golden: Path) -> Tuple[Path, Path, Path]:
    """(candidate dump, candidate snapshots dir, candidate report)."""
    d = golden.parent
    return (d / 'golden.candidate.dump', d / 'candidate-snapshots',
            d / 'golden.candidate.json')


def dump_database(db_name: str, out: Path) -> None:
    """pg_dump the suomisf schema of db_name to out, atomically."""
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = out.with_name(out.name + '.partial')
    result = subprocess.run(
        ['pg_dump', '-U', DB_USER, '-Fc', '-n', 'suomisf',
         '-f', str(partial), db_name],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f'pg_dump failed: {result.stderr[:500]}')
    partial.chmod(0o600)
    os.replace(partial, out)


def _run(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f'{cmd[0]} failed (exit {result.returncode}): '
            f'{result.stderr[:500]}'
        )


def restore_dump(dump: Path, db_name: str = TEST_DB_NAME) -> None:
    """Replace the suomisf schema of db_name with the dump's contents."""
    if db_name == MAIN_DB_NAME:
        raise ValueError(f'refusing to restore into {MAIN_DB_NAME}')
    if not dump.exists():
        raise GoldenMissingError(
            f'No golden dump at {dump}. Create it: '
            'pdm run golden-refresh && pdm run golden-accept'
        )
    psql = ['psql', '-U', DB_USER, '-d', db_name, '-c']
    _run(psql + ['DROP SCHEMA IF EXISTS suomisf CASCADE;'])
    # Extensions live outside the suomisf schema, so the dump doesn't
    # carry them. pg_trgm (migration 038) is needed by word_similarity().
    _run(psql + ['CREATE EXTENSION IF NOT EXISTS pg_trgm;'])
    _run(['pg_restore', '-U', DB_USER, '-d', db_name, '--no-owner',
          '--exit-on-error', str(dump)])


def shape(obj: Any, path: str = '') -> Dict[str, Set[str]]:
    """Map each path to the union of dict keys seen there.

    List elements share the path '<parent>[]'; only dicts produce
    entries, so an empty list or a null carries no shape.
    """
    out: Dict[str, Set[str]] = {}

    def walk(o: Any, p: str) -> None:
        if isinstance(o, dict):
            out.setdefault(p, set()).update(o.keys())
            for k, v in o.items():
                walk(v, f'{p}.{k}')
        elif isinstance(o, list):
            for v in o:
                walk(v, f'{p}[]')

    walk(obj, path)
    return out


def classify_snapshot(
    old: Dict[str, Any], new: Dict[str, Any]
) -> SnapshotClass:
    """Classify a snapshot change; metadata (generated_at) is ignored.

    Key sets are compared only at paths present on both sides: a list
    that was empty, or a value that was null, has no shape to differ.
    """
    a, b = old.get('response'), new.get('response')
    if a == b:
        return 'unchanged'
    sa, sb = shape(a), shape(b)
    if any(sa[p] != sb[p] for p in sa.keys() & sb.keys()):
        return 'structure'
    return 'data'


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def compare_snapshot_dirs(
    old_dir: Path, new_dir: Path
) -> Dict[str, SnapshotClass]:
    """Classify every snapshot by file stem; '_'-prefixed files skipped."""
    def stems(d: Path) -> Set[str]:
        return {p.stem for p in d.glob('*.json')
                if not p.name.startswith('_')}

    old, new = stems(old_dir), stems(new_dir)
    result: Dict[str, SnapshotClass] = {}
    for name in sorted(old | new):
        if name not in new:
            result[name] = 'removed'
        elif name not in old:
            result[name] = 'added'
        else:
            result[name] = classify_snapshot(
                _load(old_dir / f'{name}.json'),
                _load(new_dir / f'{name}.json'),
            )
    return result
