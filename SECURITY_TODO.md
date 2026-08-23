# Security debt

Tracks dependency vulnerabilities investigated but deliberately not fixed
yet, and why. Also tracks non-CVE version debt (exact-pinned deps stuck on
an old major with no security issue, just outdated) since it's the same
kind of "needs a real migration, not a bump" decision.

Last reviewed: 2026-08-23.

## Flask 2.3.2 / Werkzeug (pinned `<3.0.0`) — FIXED 2026-08-23

`pyproject.toml` now pins `Flask==3.1.3` and `werkzeug>=3.1.0` (resolved
to 3.1.8 in `pdm.lock`). This closes all 6 open GitHub dependabot alerts
that were Werkzeug/Flask CVEs, including the Werkzeug debugger RCE
(CVE-2024-34069 / GHSA-2g68-c3qc-8985).

What the migration touched:

- **`Bootstrap-Flask==1.3.1` removed entirely** (from `pyproject.toml`
  and `app/__init__.py`) rather than upgraded. It imports `Markup` from
  Flask's top-level namespace, which Flask 3.0 removed, and turned out
  to be genuinely dead code — no `templates/` directory exists anywhere
  in the project, and it had zero other references. This also resolves
  the Bootstrap-Flask entry that used to be listed under "other
  exact-pinned majors" below.
- All other pinned Flask extensions (`Flask-Login`, `Flask-Migrate`,
  `flask-marshmallow`, `Flask-Cors`, `Flask-JWT-Extended`, `Flask-WTF`)
  confirmed compatible with Flask 3 at their existing resolved versions
  via PyPI `requires_dist` metadata — no version bumps needed, and the
  `pdm.lock` diff confirms zero unexpected transitive changes.
- Verified the app's own code doesn't touch any Werkzeug/Flask API that
  changed behavior or was removed between 2.x and 3.x (no `request.form`
  quirks, no `cache_control`, no `WWWAuthenticate`, no `__version__`
  usage).
- Verified Werkzeug 3's default password-hash algorithm change
  (pbkdf2:sha256 → scrypt) doesn't break existing logins — old-format
  hashes still validate correctly (`check_password_hash` reads the
  algorithm from the hash itself).
- Full pytest run: 859 passed / 13 failed — identical to the
  pre-existing baseline (snapshot-drift failures, unrelated to this
  change). Full Playwright E2E run against the upgraded backend:
  chromium 44/44 passed; firefox flaky under parallel load (different
  failures across repeated runs, all timeouts, no assertion failures) —
  consistent with pre-existing concurrency flakiness documented in
  `../suomisf-ui/tests/README.md`, not a regression from this upgrade.
- Along the way, fixed an unrelated pre-existing bug in
  `tests/conftest.py`: the pytest test-account setup (`create_test_users`)
  was leaking `Test Admin`/`Test User` into the *production* database
  instead of `suomisf_test`, because `app/__init__.py`'s
  `load_dotenv(..., override=True)` call ran before the `app` fixture's
  own DB-engine override and fell back to production's `.env`. Fixed by
  setting `SUOMISF_DOTENV=.env.e2e` alongside `DATABASE_URL` at module
  load, reusing the mechanism already built for the frontend's E2E
  suite.

## SQLAlchemy 1.4.48 (version debt, not a CVE) — FIXED 2026-08-23

`pyproject.toml` now pins `SQLAlchemy==2.0.52`. Not a CVE fix — this was
version debt (the 1.4 install already logged `MovedIn20Warning` at
import time) — but bundled with the raw-SQL fixes below since they're
the same "must fix before 2.0" call sites.

What the migration touched:

- **`declarative_base()` import moved** from the removed
  `sqlalchemy.ext.declarative` shim to `sqlalchemy.orm`
  (`app/orm_decl.py`).
- **One legacy `Query.get()`** in the Flask-Login `load_user()` callback
  → `session.get(User, ...)`. Turned out this callback is likely
  unreachable in practice: nothing in the app ever calls Flask-Login's
  real `login_user()` or bridges JWT identity to it (all real auth goes
  through `jwt_admin_required()`/`jwt_required()`), so `current_user` is
  always anonymous. Fixed it anyway since it's free, but the fix itself
  can't be exercised by any test — noted for whoever eventually decides
  whether that Flask-Login wiring should be removed outright.
- **`sqlalchemy-stubs` removed** — a mypy-plugin stub package for
  SQLAlchemy 1.x with no `[tool.mypy]` config anywhere in the repo to
  ever activate it (same "confirmed genuinely dead, remove rather than
  migrate" pattern as `Bootstrap-Flask` in the Flask 3 upgrade above).
  SQLAlchemy 2.0 ships native inline types that this stub package would
  otherwise shadow/conflict with for pyright.
- **Three raw-SQL functions that built queries via Python string
  concatenation and passed the result straight to `session.execute()`**
  — a hard `ArgumentError` in 2.0 (`Textual SQL expression ... should be
  explicitly declared as text()`). Two of these (`editionowner_getowned`,
  `user_genres`) turned out to be a live, unauthenticated SQL injection,
  not just a 2.0 compatibility issue — see the `Fix SQL injection...`
  commit from the same day for the full writeup; fixed separately,
  before this bump, by parameterizing with `text()` + bind params and
  adding route-level validation. The third (`tag_list_quick`, no user
  input involved) was fixed here by wrapping in `text()`.
- **One `Row` string-key access site** (`user_genres`, e.g.
  `genre['count']`) — SQLAlchemy 2.0's `Row` no longer supports
  dict-style string-key subscripting, only attribute access
  (`genre.count`) or integer indexing. Audited every other
  `session.execute()` result-consumption site in the codebase (~15
  across `impl_works.py`, `api_pageview.py`, `api.py`, `impl_pricing.py`)
  and confirmed this was the only one using the string-key pattern —
  everywhere else already used attribute or integer access, which
  carried over unchanged.
- **A type-consistency bug in `log_changes()`** (`app/impl_logs.py`):
  it only truncated `old_value` when it was already a `str`, so an `int`
  old-value (e.g. a changed `pubyear`) got passed straight through to a
  `String(500)` column unconverted. This "worked" under 1.4's per-row
  INSERT execution, but broke under 2.0's `insertmanyvalues` batching
  (multiple `Log` rows from one multi-field update get combined into a
  single batched INSERT) whenever a batch mixed an int old-value with a
  str old-value for the same column across rows — Postgres then rejected
  the batch with `invalid input syntax for type integer: ""`, breaking
  any multi-field edit that logged more than one changed field
  (surfaced as `test_edition_contributors`, `test_edition_full_lifecycle`,
  `test_short_lifecycle`, `test_work_crud_lifecycle` failures). Fixed by
  coercing every `old_value` to `str(value)`/`None` uniformly before
  constructing the `Log` row, regardless of the original Python type.
- The ~514 `session.query(...)` call sites across `impl_*.py` were left
  as-is — the legacy `Query` API is still fully supported in 2.0, so
  rewriting them to `select()`/`session.execute()` style is a separate,
  much larger stylistic migration, not required for this fix.
- Confirmed no version conflicts: Flask-SQLAlchemy is already 3.0.5
  (supports both 1.4 and 2.0), and `marshmallow-sqlalchemy==1.5.0`
  declares `SQLAlchemy>=1.4.40,<3.0`, which covers 2.0.x.
- Full pytest run: 862 passed / 13 failed — identical to the
  pre-existing baseline (same snapshot-drift failures, unrelated).
  Full Playwright E2E run against the upgraded backend: chromium
  43-44/44 across repeated runs, one flaky failure (ownership/profile/
  read-status racing the same `Test User` account's rating state under
  parallel load) reproduced as passing 3/3 in isolation — the same
  pre-existing flake class already documented for this upgrade sequence,
  not a SQLAlchemy regression.

## marshmallow 3.26.2 (version debt, not a CVE) — FIXED 2026-08-23

`pyproject.toml` now pins `marshmallow==4.3.1`. Not a CVE fix — the 3.26.2
pin already carried CVE-2025-68480's fix — but the 4.x major jump was
deferred version debt until now. `flask-marshmallow` stayed at `1.4.0`
(no bump needed — it declares `marshmallow>=3.0.0` with no upper bound,
so it already supported 4.x; the earlier 2026-08-20 attempt bumped
`flask-marshmallow` *first*, which pulled in 1.5.0's `marshmallow>=4.0.0`
floor and dragged marshmallow along as a side effect — pinning
marshmallow itself directly avoided that). `marshmallow-sqlalchemy`
stayed at `1.5.0` (`marshmallow>=3.18.0`, no upper bound, already fine).

What the migration touched, beyond the previously-identified
`fields.Number()` blocker (all 15 occurrences → `fields.Integer()`,
matching the underlying `Integer`-typed columns):

- **Two genuine no-op bugs surfaced as hard errors.** `only=` restricting
  a nested schema's fields must be passed to the schema's own
  constructor (`TagBriefSchema(only=(...))`), not to the outer
  `ma.List(...)`/`fields.Nested(...)` wrapper. Three call sites in
  `app/model.py` (`WorkBriefSchema.tags` ×2, `MagazineSchema.issues`)
  had `only=` misplaced on the outer field, which marshmallow 3 silently
  absorbed as inert metadata — the restriction never actually applied,
  so every "brief" work/short listing was silently serializing full
  nested `Tag`/`Issue` objects (including their own `works`/`articles`/
  `stories` sub-lists) well beyond what a "Brief" schema is documented
  to do. marshmallow 4 raises `TypeError` on the unrecognized kwarg
  instead of swallowing it. Fixed by moving `only=` onto the nested
  schema's constructor, matching the pattern already used correctly
  everywhere else in the file. For the two `WorkBriefSchema`/
  `ShortSchema.tags` sites, initially restricted to `("id", "name")`
  per the schema's own intent, but the frontend's `TagGroup` component
  (`suomisf-ui/src/features/tag/components/sftag-group.tsx`, used via
  `WorkTooltip`/`work-summary.tsx`) genuinely reads `tag.type` for
  grouping/sorting/styling — so the restriction is `("id", "name",
  "type")` instead, keeping the schema brief (still excludes the heavy
  `works`/`articles`/`stories` recursion) while preserving what the UI
  actually consumes.
- **`IssueContributionSchema.Meta.fields` listed a `'type'` column that
  doesn't exist on the `Issue` model** (copy-paste leftover, no
  `type` field explicitly declared on the schema either). marshmallow
  3 / older marshmallow-sqlalchemy silently tolerated unresolvable
  names in `Meta.fields`; marshmallow 4 raises `KeyError` instead.
  Removed the stray entry.
- The other two `Meta.fields = ('id', 'name')`-style restrictions
  (`MagazineSimpleSchema`, `ShortSearchPersonSchema`) needed no changes
  — both names resolve to real model columns, and this is
  marshmallow-sqlalchemy's own SQLAlchemy-model-driven field-restriction
  mechanism, a different code path from the "implicit field creation"
  marshmallow 4 removed from plain (non-model) `Schema` classes.
- Full pytest run: 862 passed / 13 failed — identical to the
  pre-existing baseline. (A batch of `test_award_import_*` failures on
  the first run turned out to be transient ISFDB network flakiness,
  unrelated to marshmallow — reproduced as passing 8/8 on rerun.) Full
  Playwright E2E run against the upgraded backend: chromium 43-44/44
  across repeated runs, the one flaky failure reproduced as passing 3/3
  in isolation — the same pre-existing `Test User`-account parallel-race
  flake class seen throughout this upgrade sequence, not a marshmallow
  regression. Also manually verified via a direct schema dump that the
  `only=` fix produces the intended trimmed-but-not-broken shape against
  real dev data.

## WTForms 2.3.3 / Flask-WTF (version debt, not a CVE) — FIXED 2026-08-23

Removed both entirely rather than upgraded. Confirmed genuinely dead
code, same pattern as `Bootstrap-Flask` in the Flask 3 upgrade: no
`FlaskForm` subclass anywhere in the codebase, `CSRFProtect(app)` was
commented out in `app/__init__.py`, and the only other trace was a
bare `WTF_CSRF_CHECK_DEFAULT = False` local variable — never assigned
to `app.config`, so it did nothing. This is a JSON API (marshmallow
schemas + JWT), not an HTML-form app; WTForms/Flask-WTF were presumably
leftover from an earlier iteration of the project. Removed both
packages from `pyproject.toml` and the two dead lines from
`app/__init__.py`. `tests/conftest.py`'s
`flask_app.config['WTF_CSRF_ENABLED'] = False` was left alone — also
inert (nothing ever reads it now), but harmless test setup, not worth
touching.

Verified: app imports cleanly with all 193 routes, full pytest run 862
passed / 13 failed (identical pre-existing baseline), full Playwright
E2E suite green (the two flaky failures seen on the first parallel run
reproduced as passing 3/3 in isolation — same pre-existing `Test
User`-account race as every other upgrade in this sequence).

## Operational gaps found alongside the above (2026-08-20)

Not security issues, but worth fixing before they cause a real incident:

- **`pdm.lock` is out of sync with `pyproject.toml`** (and with what's
  actually installed in `.venv` — gunicorn, aiohttp, bleach, etc. are all
  newer than what's locked). Running `pdm lock` in this dev environment
  fails immediately (`Fatal Python error: Failed to import encodings
  module` — pdm's own Python resolution is broken here, unrelated to any
  project dependency). Needs investigating in an environment where `pdm`
  actually works, then a regenerated lockfile committed.
- **`Dockerfile` installs from `requirements.txt`, which is empty** (0
  bytes). The real dependency list lives in `pyproject.toml`. If the
  Docker image is still built and deployed from this Dockerfile as-is,
  it currently installs *no* Python dependencies at all — worth
  confirming whether this path is actually used, and if so, either
  populating `requirements.txt` (e.g. `pdm export`) or switching the
  Dockerfile to install from `pyproject.toml` directly.

See also `../suomisf-ui/SECURITY_TODO.md` for the frontend's remaining
items (react-router v7, vite 8, quill, face-api.js/node-fetch).
