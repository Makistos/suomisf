#!/usr/bin/env python3
"""
SuomiSF Test Timing Comparison Tool

Compares per-test durations between two test result files and
reports regressions, improvements, and new/removed tests.

Usage:
    python tests/scripts/compare_test_times.py [BASELINE] [CURRENT]

    BASELINE  Path to the older result JSON (default: latest in history/)
    CURRENT   Path to the newer result JSON (default: test_results.json)

Options:
    --threshold PCT  Regression threshold in percent (default: 20)
    --top N          Show top N slowest tests (default: 20)
    --all            Show all tests, not just changed ones
    --status         Include status column in output

Examples:
    # Compare latest run against previous run
    python tests/scripts/compare_test_times.py

    # Compare two specific files
    python tests/scripts/compare_test_times.py \\
        tests/results/history/results_20260228_100000_abc1234.json \\
        tests/results/test_results.json

    # Show regressions only, threshold 10%
    python tests/scripts/compare_test_times.py --threshold 10

    # Show top 30 slowest tests in current run
    python tests/scripts/compare_test_times.py --top 30
"""

import argparse
import json
import os
import sys

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           'results')
LATEST_PATH = os.path.join(RESULTS_DIR, 'test_results.json')
HISTORY_DIR = os.path.join(RESULTS_DIR, 'history')

# ANSI colours (disabled on non-tty)
_USE_COLOUR = sys.stdout.isatty()


def _c(text: str, code: str) -> str:
    if not _USE_COLOUR:
        return text
    return f'\033[{code}m{text}\033[0m'


RED = '31'
GREEN = '32'
YELLOW = '33'
CYAN = '36'
BOLD = '1'
DIM = '2'


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _previous_history_file() -> str:
    """Return the second-most-recent file in history/."""
    if not os.path.isdir(HISTORY_DIR):
        return ''
    files = sorted(
        [os.path.join(HISTORY_DIR, f)
         for f in os.listdir(HISTORY_DIR)
         if f.endswith('.json')],
        key=os.path.getmtime
    )
    # files[-1] is the current run (same content as test_results.json)
    return files[-2] if len(files) >= 2 else (files[0] if files else '')


def _summary_line(data: dict, label: str) -> str:
    ts = data.get('timestamp', '')[:19].replace('T', ' ')
    gh = data.get('git_hash', '?')
    p = data.get('passed', 0)
    f = data.get('failed', 0)
    s = data.get('skipped', 0)
    ms = data.get('total_duration_ms', 0)
    return (
        f"{label}: {ts}  git={gh}  "
        f"{p} passed / {f} failed / {s} skipped  "
        f"total={ms/1000:.1f}s"
    )


def compare(baseline: dict, current: dict,
            threshold: float, show_all: bool,
            show_status: bool, top_n: int) -> int:
    """
    Print comparison table.  Returns 1 if regressions found, else 0.
    """
    base_tests: dict = baseline.get('tests', {})
    curr_tests: dict = current.get('tests', {})

    all_ids = sorted(set(base_tests) | set(curr_tests))

    regressions = []
    improvements = []
    unchanged = []
    new_tests = []
    removed_tests = []

    for nid in all_ids:
        if nid not in base_tests:
            new_tests.append(nid)
            continue
        if nid not in curr_tests:
            removed_tests.append(nid)
            continue

        b_ms = base_tests[nid]['duration_ms']
        c_ms = curr_tests[nid]['duration_ms']
        if b_ms > 0:
            pct = (c_ms - b_ms) / b_ms * 100
        else:
            pct = 0.0

        entry = (nid, b_ms, c_ms, pct,
                 curr_tests[nid].get('status', '?'))
        if pct >= threshold:
            regressions.append(entry)
        elif pct <= -threshold:
            improvements.append(entry)
        else:
            unchanged.append(entry)

    regressions.sort(key=lambda x: -x[3])
    improvements.sort(key=lambda x: x[3])
    unchanged.sort(key=lambda x: -x[2])

    # --- Header ---
    print()
    print(_c('=' * 72, BOLD))
    print(_c('Test Timing Comparison', BOLD))
    print(_c('=' * 72, BOLD))
    print(_summary_line(baseline, 'Baseline'))
    print(_summary_line(current,  'Current '))
    print(f'Regression threshold: {threshold:.0f}%')
    print(_c('=' * 72, BOLD))

    def _row(nid: str, b: float, c: float, pct: float,
             status: str, colour: str):
        short = nid.split('::')[-1]
        if len(short) > 52:
            short = short[:49] + '...'
        arrow = f'{pct:+.0f}%'
        status_col = f' {status[:7]:<7}' if show_status else ''
        line = (f'  {short:<52} '
                f'{b:7.1f}ms -> {c:7.1f}ms  {arrow:>6}'
                f'{status_col}')
        print(_c(line, colour))

    # --- Regressions ---
    if regressions:
        print()
        print(_c(f'  REGRESSIONS  (>{threshold:.0f}%  slower)  '
                 f'{len(regressions)} test(s)', RED + ';' + BOLD))
        for nid, b, c, pct, st in regressions:
            _row(nid, b, c, pct, st, RED)

    # --- Improvements ---
    if improvements:
        print()
        print(_c(f'  IMPROVEMENTS  (>{threshold:.0f}%  faster)  '
                 f'{len(improvements)} test(s)', GREEN + ';' + BOLD))
        for nid, b, c, pct, st in improvements:
            _row(nid, b, c, pct, st, GREEN)

    # --- New / removed ---
    if new_tests:
        print()
        print(_c(f'  NEW TESTS  {len(new_tests)} test(s)', CYAN))
        for nid in new_tests:
            e = curr_tests[nid]
            print(f'    + {nid.split("::")[-1]}'
                  f'  {e["duration_ms"]:.1f}ms')

    if removed_tests:
        print()
        print(_c(f'  REMOVED TESTS  {len(removed_tests)} test(s)', DIM))
        for nid in removed_tests:
            e = base_tests[nid]
            print(f'    - {nid.split("::")[-1]}'
                  f'  {e["duration_ms"]:.1f}ms')

    # --- Unchanged (optional) ---
    if show_all and unchanged:
        print()
        print(_c(f'  UNCHANGED  {len(unchanged)} test(s)', DIM))
        for nid, b, c, pct, st in unchanged:
            _row(nid, b, c, pct, st, DIM)

    # --- Top N slowest in current run ---
    if top_n > 0:
        print()
        print(_c(f'  TOP {top_n} SLOWEST (current run)', BOLD))
        slowest = sorted(curr_tests.items(),
                         key=lambda kv: -kv[1]['duration_ms'])[:top_n]
        for i, (nid, entry) in enumerate(slowest, 1):
            short = nid.split('::')[-1]
            if len(short) > 52:
                short = short[:49] + '...'
            status_col = (f' {entry.get("status","?")[:7]:<7}'
                          if show_status else '')
            print(f'  {i:>3}. {short:<52} '
                  f'{entry["duration_ms"]:7.1f}ms{status_col}')

    # --- Summary ---
    print()
    print(_c('=' * 72, BOLD))
    reg_str = _c(f'{len(regressions)} regressions', RED) \
        if regressions else f'{len(regressions)} regressions'
    imp_str = _c(f'{len(improvements)} improvements', GREEN) \
        if improvements else f'{len(improvements)} improvements'
    print(f'  {reg_str}   {imp_str}   '
          f'{len(unchanged)} unchanged   '
          f'{len(new_tests)} new   {len(removed_tests)} removed')
    print(_c('=' * 72, BOLD))
    print()

    return 1 if regressions else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compare per-test durations between two test runs'
    )
    parser.add_argument(
        'baseline', nargs='?', default='',
        help='Baseline result JSON (default: second-most-recent in history/)'
    )
    parser.add_argument(
        'current', nargs='?', default=LATEST_PATH,
        help='Current result JSON (default: test_results.json)'
    )
    parser.add_argument(
        '--threshold', type=float, default=20.0,
        help='Regression/improvement threshold in %% (default: 20)'
    )
    parser.add_argument(
        '--top', type=int, default=20,
        help='Show top N slowest tests (0 to disable, default: 20)'
    )
    parser.add_argument(
        '--all', dest='show_all', action='store_true',
        help='Also show unchanged tests'
    )
    parser.add_argument(
        '--status', dest='show_status', action='store_true',
        help='Add a status column (passed/failed/skipped)'
    )
    parser.add_argument(
        '--list', action='store_true',
        help='List available history files and exit'
    )

    args = parser.parse_args()

    if args.list:
        if not os.path.isdir(HISTORY_DIR):
            print('No history directory found.')
            return 0
        files = sorted(os.listdir(HISTORY_DIR))
        for fname in files:
            fpath = os.path.join(HISTORY_DIR, fname)
            try:
                data = load(fpath)
                ts = data.get('timestamp', '')[:19].replace('T', ' ')
                gh = data.get('git_hash', '?')
                p = data.get('passed', 0)
                ms = data.get('total_duration_ms', 0)
                print(f'  {fname:<55} {ts}  {gh}  '
                      f'{p} passed  {ms/1000:.0f}s')
            except Exception:
                print(f'  {fname}  (unreadable)')
        return 0

    # Resolve baseline
    baseline_path = args.baseline
    if not baseline_path:
        baseline_path = _previous_history_file()
    if not baseline_path:
        print('ERROR: No baseline file found. '
              'Run tests at least twice to build history.',
              file=sys.stderr)
        return 2

    # Load files
    for path, label in [(baseline_path, 'baseline'),
                        (args.current, 'current')]:
        if not os.path.exists(path):
            print(f'ERROR: {label} file not found: {path}',
                  file=sys.stderr)
            return 2

    baseline = load(baseline_path)
    current = load(args.current)

    if 'tests' not in baseline or 'tests' not in current:
        print('ERROR: result file missing "tests" key. '
              'Run tests again to regenerate with timing data.',
              file=sys.stderr)
        return 2

    return compare(
        baseline, current,
        threshold=args.threshold,
        show_all=args.show_all,
        show_status=args.show_status,
        top_n=args.top,
    )


if __name__ == '__main__':
    sys.exit(main())
