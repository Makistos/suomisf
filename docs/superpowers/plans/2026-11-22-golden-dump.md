# Golden Test Database Dump Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tests (pytest and the frontend Playwright E2E suite) restore `suomisf_test` from a pinned local dump, so refreshing the dev DB from production no longer breaks them. Refreshing the test data becomes a deliberate two-step command that reports which snapshots would change and how.

**Architecture:** New module `tests/scripts/golden.py` owns the dump file: where it lives, dumping, restoring, comparing snapshots, and the `refresh` / `accept` CLI. `clone_test_database()` in `tests/conftest.py` (also used by `tests/scripts/setup_e2e_db.py` for the frontend E2E suite) restores from the golden dump instead of piping `pg_dump` of the live DB. `update_snapshots.generate_snapshots()` gains an output-dir parameter so `refresh` can render candidate snapshots without touching the committed ones.

**Tech Stack:** Python 3.12, pytest, PostgreSQL 17 (`pg_dump -Fc` / `pg_restore`), pdm scripts, ruff.

**Spec:** No separate spec doc. The requirements are the owner's question and the agreed proposal (assistant session 2026-11-21): pinned dump, a refresh step that runs the data checks and classifies snapshot changes as unchanged / data-only / structure, and replacing the dump and snapshots only on accept.

## Global Constraints

- Lines ≤ 79 chars; `.venv/bin/ruff check .` stays at the current 3 B905 findings and nothing else.
- Never write to the main DB `suomisf`: it is only read, by `pg_dump`. Every restore targets `suomisf_test`, and `restore_dump` refuses `suomisf`.
- The golden dump holds real user data (emails, password hashes). It lives **outside the repo** at `~/.local/share/suomisf/golden.dump` (override: env `SUOMISF_GOLDEN_DUMP`), with file mode `0600` and directory mode `0700`. The repo is public; nothing from the dump goes into git.
- No silent fallback to cloning the live DB when the dump is missing: raise with the fix command.
- Unit tests need no DB and no network. Run them with `--skip-db-setup`.
- Work directly on `master`, with no branches or worktrees. Before each commit the owner runs `/security-pipeline build .` or says skip. Push only on the owner's yes.
- Keep the function name `clone_test_database()`: `setup_e2e_db.py` imports it.

## Review Focus

1. **No golden dump yet** (first run, new machine, wrong `SUOMISF_GOLDEN_DUMP`): pytest and E2E setup fail at once with `GoldenMissingError` naming the path and `pdm run golden-refresh && pdm run golden-accept`. They don't hang and don't clone the live DB. *Test: Task 2, `test_restore_missing_dump_raises_without_running_psql`.*
2. **pg_dump fails halfway** (disk full, DB down): the existing golden and any earlier candidate stay untouched, and no `.partial` file is left behind. *Test: Task 2, `test_dump_failure_leaves_existing_file_and_no_partial`.*
3. **`accept` with no candidate, or with structure changes**: nothing moves, exit 1 or 2, and the message lists the structure-changed snapshots; `--force` overrides. *Tests: Task 3, `test_promote_without_candidate`, `test_promote_refuses_structure_without_force`.*
4. **Snapshot set differs** (an endpoint added to or removed from `ENDPOINTS_TO_SNAPSHOT`): it is classified `added` / `removed` with no crash, and `accept` deletes the removed files. *Tests: Task 1, `test_compare_dirs_added_removed`; Task 3, `test_promote_success`.*
5. **Golden dump older than the code's migrations**: the `_apply_migration_*` calls still run after the restore, as they do after today's clone, so a new migration works against an old dump. *Check: Task 2 Step 6, full pytest run.*

---

### Task 1: Snapshot classification (pure functions)

**Files:**
- Create: `tests/scripts/golden.py`
- Test: `tests/test_golden.py`

**Interfaces:**
- Produces:
  - `SnapshotClass = Literal['unchanged', 'data', 'structure', 'added', 'removed']`
  - `shape(obj: Any, path: str = '') -> Dict[str, Set[str]]`: maps each path (`.a.b[]` style) to the union of dict keys seen there. List elements share the path `<parent>[]`. Only dicts produce entries.
  - `classify_snapshot(old: Dict[str, Any], new: Dict[str, Any]) -> SnapshotClass`: compares only `['response']`, so `metadata` (incl. `generated_at`) is ignored. Equal → `unchanged`. Otherwise `structure` if any path **present in both** shapes has different key sets, else `data`.
  - `compare_snapshot_dirs(old_dir: Path, new_dir: Path) -> Dict[str, SnapshotClass]`: keyed by file stem, over `*.json` minus names starting with `_`.

The rule "only paths present in both" is deliberate: an empty list or `null` on one side carries no shape, so `tags: []` → `tags: [{...}]` counts as data, as the 2026-11-21 snapshot refresh showed.

- [ ] **Step 1: Write the failing tests** in `tests/test_golden.py`

```python
from tests.scripts.golden import classify_snapshot, compare_snapshot_dirs

def snap(resp, ts='2026-01-01'):
    return {'metadata': {'generated_at': ts}, 'response': resp}

def test_unchanged_ignores_metadata():
    assert classify_snapshot(snap({'a': 1}), snap({'a': 1}, ts='x')) == 'unchanged'

def test_value_change_is_data():
    assert classify_snapshot(snap({'a': 1}), snap({'a': 2})) == 'data'

def test_empty_list_filled_is_data():
    old = snap({'tags': []})
    new = snap({'tags': [{'id': 1, 'name': 'x'}]})
    assert classify_snapshot(old, new) == 'data'

def test_null_to_object_is_data():
    assert classify_snapshot(snap({'p': None}), snap({'p': {'id': 1}})) == 'data'

def test_added_key_in_shared_list_is_structure():
    old = snap({'data': [{'id': 1}]})
    new = snap({'data': [{'id': 2, 'subtitle': 's'}]})
    assert classify_snapshot(old, new) == 'structure'

def test_removed_key_is_structure():
    assert classify_snapshot(snap({'a': 1, 'b': 2}), snap({'a': 1})) == 'structure'

def test_compare_dirs_added_removed(tmp_path):
    # old: keep.json, gone.json, _snapshot_summary.json
    # new: keep.json (value changed), new.json, _snapshot_summary.json
    ...  # write files with json.dump(snap(...))
    assert compare_snapshot_dirs(old, new) == {
        'keep': 'data', 'gone': 'removed', 'new': 'added'}
```

- [ ] **Step 2: Run and see the tests fail**

Run: `pdm run pytest tests/test_golden.py --skip-db-setup -q`
Expected: FAIL, `ModuleNotFoundError: tests.scripts.golden`.

- [ ] **Step 3: Implement** `shape`, `classify_snapshot` and `compare_snapshot_dirs` in `tests/scripts/golden.py`. Use the module docstring for the purpose and the CLI usage that Task 3 will add. No `app` imports in this module.

- [ ] **Step 4: Run the tests and see them pass**

Run: `pdm run pytest tests/test_golden.py --skip-db-setup -q` → 7 passed. Then `.venv/bin/ruff check tests/scripts/golden.py tests/test_golden.py` → clean.

- [ ] **Step 5: Commit**

```bash
git add tests/scripts/golden.py tests/test_golden.py
git commit -m "Tests: classify snapshot changes as data or structure"
```

---

### Task 2: Dump, restore, and tests restoring from the golden dump

**Files:**
- Modify: `tests/scripts/golden.py`
- Modify: `tests/conftest.py:95-147` (`clone_test_database`: replace the drop / extension / `pg_dump | psql` block, keep the `_apply_migration_*` calls)
- Modify: `.gitignore` (add `*.dump` as a second line of defence)
- Modify: `tests/TEST_DOCUMENTATION.md:1761` (the "automatically clones the main database" note), `CLAUDE.md` (one line under the testing rules: tests restore from the golden dump; refresh with the two commands)
- Modify (frontend repo): `~/src/suomisf-ui/tests/README.md:4,17-18,91`: "clone of the dev database" becomes "restored from the golden dump (see the backend's TEST_DOCUMENTATION.md)"
- Test: `tests/test_golden.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces, all in `tests/scripts/golden.py`:
  - constants `DB_USER = 'mep'`, `MAIN_DB_NAME = 'suomisf'`, `TEST_DB_NAME = 'suomisf_test'`, `DEFAULT_GOLDEN = '~/.local/share/suomisf/golden.dump'`
  - `class GoldenMissingError(RuntimeError)`
  - `golden_path() -> Path`: `SUOMISF_GOLDEN_DUMP` or `DEFAULT_GOLDEN`, expanded.
  - `candidate_paths(golden: Path) -> Tuple[Path, Path, Path]`: `(golden.candidate.dump, candidate-snapshots/, golden.candidate.json)`, all in `golden.parent`.
  - `dump_database(db_name: str, out: Path) -> None`: creates the parent directory with mode 0700 and runs `pg_dump -U mep -Fc -n suomisf -f <out>.partial <db_name>`. On success it does `chmod 0600` and `os.replace` to `out`. On failure it deletes `.partial` and raises `RuntimeError` with pg_dump's stderr (first 500 chars).
  - `restore_dump(dump: Path, db_name: str = TEST_DB_NAME) -> None`: raises `ValueError` if `db_name == MAIN_DB_NAME`, or `GoldenMissingError` if `dump` doesn't exist. The message is: `No golden dump at <path>. Create it: pdm run golden-refresh && pdm run golden-accept`. Then it runs `psql -c 'DROP SCHEMA IF EXISTS suomisf CASCADE;'`, `psql -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'` (same reason as the current comment in conftest), and `pg_restore -U mep -d <db_name> --no-owner --exit-on-error <dump>`. A non-zero exit raises `RuntimeError` with stderr.
  - `conftest.clone_test_database()` becomes `restore_dump(golden_path())`, then the existing migration calls. Update its docstring and print line to say "Restoring golden dump <path>".

- [ ] **Step 1: Write the failing tests**

```python
def test_golden_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv('SUOMISF_GOLDEN_DUMP', str(tmp_path / 'g.dump'))
    assert golden_path() == tmp_path / 'g.dump'

def test_golden_path_default(monkeypatch):
    monkeypatch.delenv('SUOMISF_GOLDEN_DUMP', raising=False)
    assert golden_path() == Path.home() / '.local/share/suomisf/golden.dump'

def test_restore_missing_dump_raises_without_running_psql(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(golden.subprocess, 'run', lambda *a, **k: calls.append(a))
    with pytest.raises(GoldenMissingError, match='pdm run golden-refresh'):
        restore_dump(tmp_path / 'nope.dump')
    assert calls == []

def test_restore_refuses_main_db(tmp_path):
    f = tmp_path / 'g.dump'; f.write_bytes(b'x')
    with pytest.raises(ValueError):
        restore_dump(f, 'suomisf')

def test_dump_failure_leaves_existing_file_and_no_partial(monkeypatch, tmp_path):
    out = tmp_path / 'golden.dump'; out.write_bytes(b'old')
    def fake_run(cmd, **k):
        Path(cmd[cmd.index('-f') + 1]).write_bytes(b'half')
        return subprocess.CompletedProcess(cmd, 1, '', 'disk full')
    monkeypatch.setattr(golden.subprocess, 'run', fake_run)
    with pytest.raises(RuntimeError, match='disk full'):
        dump_database('suomisf', out)
    assert out.read_bytes() == b'old'
    assert not out.with_name('golden.dump.partial').exists()
```

- [ ] **Step 2: Run and see them fail**: `pdm run pytest tests/test_golden.py --skip-db-setup -q` → 5 new failures (ImportError).
- [ ] **Step 3: Implement** the interfaces above in `golden.py`, then switch `clone_test_database()` in `tests/conftest.py`.
- [ ] **Step 4: Unit tests pass**: same command → 12 passed; ruff is clean.
- [ ] **Step 5: Create the first golden dump by hand.** `refresh` doesn't exist yet. This only reads the main DB:
  `pdm run python -c "from tests.scripts.golden import *; dump_database(MAIN_DB_NAME, golden_path())"`
  Expect `~/.local/share/suomisf/golden.dump` to exist with mode `-rw-------`, at roughly 50–150 MB.
- [ ] **Step 6: Full suite against the golden dump**: `pdm run pytest tests -m 'not network' -p no:cacheprovider -q`. Expect 1170 + 12 passed and 2 skipped, and the setup log saying "Restoring golden dump". If any snapshot test fails, the dev DB changed since 2026-11-21. That isn't a bug in this task; note it and continue.
- [ ] **Step 7: Prove the test run no longer reads the dev DB.** Run the suite with `-s` and check the setup output: it shows "Restoring golden dump" and `grep -c pg_dump` on the output gives 0. `md5sum` of the golden dump is the same before and after.
- [ ] **Step 8: E2E still works**: in `~/src/suomisf-ui`, run `npm run test:e2e`. Expect the same results as on 2026-11-21: only the known Kirjasampo failure, and maybe the flaky Firefox ownership test.
- [ ] **Step 9: Commit both repos**

```bash
cd ~/src/suomisf && git add tests/scripts/golden.py tests/test_golden.py \
  tests/conftest.py .gitignore tests/TEST_DOCUMENTATION.md CLAUDE.md
git commit -m "Tests: restore suomisf_test from a pinned golden dump"
cd ~/src/suomisf-ui && git add tests/README.md
git commit -m "E2E docs: test DB comes from the backend's golden dump"
```

---

### Task 3: `golden-refresh` and `golden-accept`

**Files:**
- Modify: `tests/scripts/update_snapshots.py` (`save_snapshot` and `generate_snapshots` take `out_dir: str = SNAPSHOTS_DIR`, and `_snapshot_summary.json` goes there too; the default behaviour is unchanged)
- Modify: `tests/scripts/golden.py` (CLI)
- Modify: `pyproject.toml` `[tool.pdm.scripts]`
- Modify: `tests/TEST_DOCUMENTATION.md` (the refresh workflow, below)
- Test: `tests/test_golden.py`

**Interfaces:**
- Consumes: Task 1 `compare_snapshot_dirs`; Task 2 `golden_path`, `candidate_paths`, `dump_database`, `restore_dump`; `tests.conftest.create_test_users`, imported inside `refresh()` only, after the dotenv check.
- Produces:
  - `refresh() -> int`:
    1. exits with a message unless `SUOMISF_DOTENV == '.env.e2e'` (same guard and reason as `setup_e2e_db.py`);
    2. `dump_database(MAIN_DB_NAME, cand)`;
    3. `restore_dump(cand)`, then `apply_test_migrations()` and `create_test_users()` from `tests.conftest`;
    4. empties `cand_snaps`, then `generate_snapshots(out_dir=str(cand_snaps))`;
    5. `snapshots = compare_snapshot_dirs(SNAPSHOTS_DIR, cand_snaps)`;
    6. `failed = run_tests_against(cand, cand_snaps)`;
    7. writes the report JSON `{'snapshots': {name: class}, 'failed_tests': [...]}`;
    8. prints the counts per snapshot class with names for everything except `unchanged`, then the failed test ids. Each failed test is a test that depends on the data: fix it before accepting, ideally by making it data-independent, and rerun it alone with the command it prints. Then it prints the next steps: `SUOMISF_GOLDEN_DUMP=<cand> npm run test:e2e` in suomisf-ui (optional), then `pdm run golden-accept`.
    9. returns 0 if there are no failed tests and no `structure` snapshots, else 1.
  - `run_tests_against(dump: Path, snapshots_dir: Path) -> List[str]`: runs `pytest tests -m 'not network' -p no:cacheprovider -q -rf` as a subprocess, with env `SUOMISF_GOLDEN_DUMP=<dump>` and `SUOMISF_SNAPSHOTS_DIR=<snapshots_dir>`. Its output streams through, and it returns the ids from the `FAILED <id>` lines. Pytest restores the candidate itself, so snapshot tests pass by construction against their own data, and anything that fails depends on hard-coded data. Exclusion by name isn't reliable: 10 tests read snapshots without "snapshot" in their name.
  - `parse_failed(output: str) -> List[str]`: the `FAILED <id>` / `ERROR <id>` ids from pytest's `-rf` summary, without the ` - reason` suffix.
  - In `conftest.py`, `SNAPSHOTS_DIR` reads `os.environ.get('SUOMISF_SNAPSHOTS_DIR')`, falling back to today's path. That's the only place tests locate snapshots.
  - `promote_candidate(golden: Path, snapshots_dir: Path, force: bool = False) -> int`:
    - no candidate dump or report → print `No candidate: run pdm run golden-refresh` and return 1;
    - any `structure` snapshot or any `failed_tests` in the report, and not `force` → print them and `--force to accept anyway`, and return 2. Nothing moves.
    - otherwise: `golden` → `golden.previous.dump` (replacing any older one), candidate → `golden`, copy every `*.json` from `cand_snaps` into `snapshots_dir`, delete the `removed` ones from `snapshots_dir`, delete `cand_snaps` and the report, and return 0.
  - `main(argv: List[str]) -> int`: subcommands `refresh` and `accept [--force]` (argparse).
  - In `conftest.py`, `apply_test_migrations() -> None` holds the existing `_apply_migration_*` call list. `clone_test_database()` calls it.
  - pdm scripts:
    ```toml
    golden-refresh = {cmd = "python tests/scripts/golden.py refresh", env = {SUOMISF_DOTENV = ".env.e2e"}}
    golden-accept = "python tests/scripts/golden.py accept"
    ```

- [ ] **Step 1: Write the failing tests** (filesystem only, with `tmp_path`; a helper builds the golden, candidate, `cand_snaps` and report)

```python
def test_promote_without_candidate(tmp_path):
    g = tmp_path / 'golden.dump'; g.write_bytes(b'old')
    assert promote_candidate(g, tmp_path / 'snaps') == 1
    assert g.read_bytes() == b'old'

def test_promote_refuses_structure_without_force(tmp_path):
    g, snaps = make_candidate(tmp_path, report={'works': 'structure'})
    assert promote_candidate(g, snaps) == 2
    assert g.read_bytes() == b'old'
    assert promote_candidate(g, snaps, force=True) == 0

def test_promote_refuses_failed_tests_without_force(tmp_path):
    g, snaps = make_candidate(tmp_path, report={'keep': 'data'},
                              failed=['tests/api/test_misc.py::test_x'])
    assert promote_candidate(g, snaps) == 2
    assert g.read_bytes() == b'old'

def test_parse_failed():
    out = ('FAILED tests/a.py::test_one - AssertionError: x\n'
           'ERROR tests/b.py::test_two - RuntimeError\n'
           '1 failed, 1 error, 10 passed in 3.0s\n')
    assert parse_failed(out) == ['tests/a.py::test_one', 'tests/b.py::test_two']

def test_promote_success(tmp_path):
    g, snaps = make_candidate(
        tmp_path, report={'keep': 'data', 'gone': 'removed', 'new': 'added'})
    assert promote_candidate(g, snaps) == 0
    assert g.read_bytes() == b'new'
    assert g.with_name('golden.previous.dump').read_bytes() == b'old'
    assert sorted(p.stem for p in snaps.glob('*.json')) == ['_snapshot_summary', 'keep', 'new']
    assert not any(p.exists() for p in candidate_paths(g))
```

- [ ] **Step 2: Run and see them fail**: `pdm run pytest tests/test_golden.py --skip-db-setup -q` → 5 new failures.
- [ ] **Step 3: Implement** the `out_dir` parameter, `apply_test_migrations`, `refresh`, `promote_candidate`, `main` and the pdm scripts.
- [ ] **Step 4: Unit tests pass**: → 17 passed; ruff is clean.
- [ ] **Step 5: Real run, expecting no change.** `pdm run golden-refresh`. The golden dump from Task 2 and the committed snapshots both come from the current dev DB, so expect every snapshot to be `unchanged` (or `data` only if the dev DB changed in between), 0 `structure`, and 0 failed tests: the 4 that failed on 2026-11-21 were snapshot drift, fixed by the 9cd0957f refresh. This run takes about 6 minutes, because it includes the full suite. Then `pdm run golden-accept` → 0, and `git status tests/fixtures/snapshots` shows at most `generated_at` changes. If that's all, run `git checkout tests/fixtures/snapshots`.
- [ ] **Step 6: Full suite**: `pdm run pytest tests -m 'not network' -p no:cacheprovider -q` → 1187 passed, 2 skipped.
- [ ] **Step 7: Document the workflow** in `tests/TEST_DOCUMENTATION.md`, as a section "Test data (golden dump)":
  - where the dump lives and why (user data, public repo);
  - what to do after updating the dev DB from production: `pdm run golden-refresh` → read the report (unchanged / data / structure / added / removed; `structure` means a code regression or a migration that is in prod but not in the code; failed tests depend on hard-coded data: make them data-independent, rerunning each one with `SUOMISF_GOLDEN_DUMP=<candidate> SUOMISF_SNAPSHOTS_DIR=<candidate-snapshots> pdm run pytest <id>`) → `pdm run golden-accept` → run the tests and E2E → commit `tests/fixtures/snapshots`;
  - rollback: `mv ~/.local/share/suomisf/golden.previous.dump ~/.local/share/suomisf/golden.dump && git checkout tests/fixtures/snapshots`.
- [ ] **Step 8: Commit**

```bash
git add tests/scripts/golden.py tests/scripts/update_snapshots.py \
  tests/conftest.py tests/test_golden.py pyproject.toml \
  tests/TEST_DOCUMENTATION.md
git commit -m "Tests: golden-refresh / golden-accept for test data updates"
```

---

## Out of scope

- `tests/scripts/setup_test_db.py --clone` (an older sudo-based full-DB clone). It's left unchanged; say so in the final summary and ask whether to remove it.
- Data-sensitive E2E assertions in suomisf-ui (exact award winner lists and so on) are stable against the golden dump and need no change.
