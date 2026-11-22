#!/usr/bin/env python3
"""Golden test-data dump: tests restore suomisf_test from a pinned dump.

Tests (pytest and the frontend E2E suite) no longer clone the live dev
database, so refreshing it from production cannot break them. Refreshing
the test data is a deliberate step that reports what would change.

Usage:
    pdm run golden-refresh    # candidate dump + snapshot/test report
    pdm run golden-accept     # adopt the candidate (--force to override)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Set, Tuple

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


REPO_ROOT = Path(__file__).resolve().parents[2]
_FAILED_RE = re.compile(r'^(?:FAILED|ERROR) (\S+)')


def parse_failed(output: str) -> List[str]:
    """Test ids from pytest's -rfE short summary, reason stripped."""
    return [m.group(1) for line in output.splitlines()
            if (m := _FAILED_RE.match(line))]


def run_tests_against(dump: Path, snapshots_dir: Path) -> List[str]:
    """Run the suite on the candidate data; return the failing test ids.

    Snapshot tests read the candidate's own snapshots, so they pass by
    construction: whatever fails depends on hard-coded data.
    """
    env = dict(os.environ, SUOMISF_GOLDEN_DUMP=str(dump),
               SUOMISF_SNAPSHOTS_DIR=str(snapshots_dir))
    proc = subprocess.Popen(
        [sys.executable, '-m', 'pytest', 'tests', '-m', 'not network',
         '-p', 'no:cacheprovider', '-q', '-rfE'],
        cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True,
    )
    assert proc.stdout is not None
    lines = []
    for line in proc.stdout:
        print(line, end='')
        lines.append(line)
    proc.wait()
    return parse_failed(''.join(lines))


def _report(golden: Path) -> Dict[str, Any]:
    return json.loads(candidate_paths(golden)[2].read_text('utf-8'))


def refresh() -> int:
    """Candidate dump from the dev DB, its snapshots, tests, and a report."""
    if os.environ.get('SUOMISF_DOTENV') != '.env.e2e':
        # Same reason as setup_e2e_db.py: the first `app` import must
        # bind to suomisf_test, not to production's .env.
        print('golden refresh must run with SUOMISF_DOTENV=.env.e2e '
              '(use: pdm run golden-refresh)')
        return 2
    from tests.conftest import apply_test_migrations, create_test_users
    from tests.scripts.update_snapshots import (
        SNAPSHOTS_DIR,
        generate_snapshots,
    )

    golden = golden_path()
    cand, cand_snaps, rep = candidate_paths(golden)
    print(f'[golden] Dumping {MAIN_DB_NAME} -> {cand}')
    dump_database(MAIN_DB_NAME, cand)
    print(f'[golden] Restoring candidate into {TEST_DB_NAME}')
    restore_dump(cand)
    apply_test_migrations()
    create_test_users()
    shutil.rmtree(cand_snaps, ignore_errors=True)
    generate_snapshots(out_dir=str(cand_snaps))
    snapshots = compare_snapshot_dirs(Path(SNAPSHOTS_DIR), cand_snaps)
    print('[golden] Running the test suite against the candidate')
    failed = run_tests_against(cand, cand_snaps)
    rep.write_text(json.dumps(
        {'snapshots': snapshots, 'failed_tests': failed}, indent=2,
    ), encoding='utf-8')

    print('\n[golden] Snapshots compared with tests/fixtures/snapshots:')
    for cls in ('unchanged', 'data', 'structure', 'added', 'removed'):
        names = [n for n, c in snapshots.items() if c == cls]
        shown = '' if cls == 'unchanged' else ' ' + ', '.join(names)
        print(f'  {cls:9} {len(names):3}{shown}')
    if failed:
        print('[golden] Tests failing on the candidate data (they depend '
              'on hard-coded data; make them data-independent):')
        for test_id in failed:
            print(f'  {test_id}')
        print(f'  rerun one: SUOMISF_GOLDEN_DUMP={cand} '
              f'SUOMISF_SNAPSHOTS_DIR={cand_snaps} pdm run pytest <id>')
    print('[golden] Next: optionally, in suomisf-ui: '
          f'SUOMISF_GOLDEN_DUMP={cand} npm run test:e2e')
    print('[golden] Then: pdm run golden-accept')
    blocked = failed or any(c == 'structure' for c in snapshots.values())
    return 1 if blocked else 0


def promote_candidate(
    golden: Path, snapshots_dir: Path, force: bool = False
) -> int:
    """Adopt the candidate dump and its snapshots; keep the old dump."""
    cand, cand_snaps, rep = candidate_paths(golden)
    if not cand.exists() or not rep.exists():
        print('No candidate: run pdm run golden-refresh')
        return 1
    report = _report(golden)
    structure = [n for n, c in report['snapshots'].items()
                 if c == 'structure']
    failed = report['failed_tests']
    if (structure or failed) and not force:
        for name in structure:
            print(f'structure change: {name}')
        for test_id in failed:
            print(f'failing test: {test_id}')
        print('--force to accept anyway')
        return 2
    if golden.exists():
        os.replace(golden, golden.with_name('golden.previous.dump'))
    os.replace(cand, golden)
    for src in cand_snaps.glob('*.json'):
        shutil.copy2(src, snapshots_dir / src.name)
    for name, cls in report['snapshots'].items():
        if cls == 'removed':
            (snapshots_dir / f'{name}.json').unlink(missing_ok=True)
    shutil.rmtree(cand_snaps)
    rep.unlink()
    print(f'[golden] Accepted: {golden} (previous kept as '
          'golden.previous.dump). Run the tests, then commit '
          'tests/fixtures/snapshots.')
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('refresh', help='make a candidate dump and report')
    accept = sub.add_parser('accept', help='adopt the candidate')
    accept.add_argument('--force', action='store_true',
                        help='accept despite structure changes or '
                             'failing tests')
    args = parser.parse_args(argv)
    if args.command == 'refresh':
        return refresh()
    # Not update_snapshots.SNAPSHOTS_DIR: importing it loads the app.
    snapshots = REPO_ROOT / 'tests' / 'fixtures' / 'snapshots'
    return promote_candidate(golden_path(), snapshots, force=args.force)


if __name__ == '__main__':
    sys.path.insert(0, str(REPO_ROOT))
    sys.exit(main(sys.argv[1:]))
