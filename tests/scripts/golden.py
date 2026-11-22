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
from pathlib import Path
from typing import Any, Dict, Literal, Set

SnapshotClass = Literal['unchanged', 'data', 'structure', 'added', 'removed']


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
