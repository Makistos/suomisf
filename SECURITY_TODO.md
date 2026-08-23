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

## Other exact-pinned majors (not CVEs, just version debt)

Found while bumping the rest of the dependencies on 2026-08-20. None of
these have an open dependabot alert — they're just stuck on an old major
because the pin was never revisited, and each one carries real
breaking-change risk if bumped blind:

- **SQLAlchemy `==1.4.48`** — already logs `MovedIn20Warning` at import
  time (`app/orm_decl.py`'s `declarative_base()` call). The warning
  itself says the codebase uses 1.x-only APIs; a 2.0 bump needs a real
  migration pass (`Query` vs `select()` patterns, session handling
  changes across the whole `impl_*.py` layer), not a version bump.
- **marshmallow `===3.26.2`** (bumped 2026-08-20, was `3.22.0` — this was
  a genuine CVE fix, not just version debt: CVE-2025-68480, DoS in
  `Schema.load(many)`, fixed in 3.26.2, still marshmallow 3.x so no
  breaking-change risk. Verified with a full pytest run: 859 passed / 13
  failed, same pre-existing snapshot-drift failures as always, nothing
  new). The 4.x major jump is the part still deferred — marshmallow 4
  changed field APIs (confirmed directly: bumping `flask-marshmallow` to
  its latest silently pulled marshmallow to 4.x as a side effect, since
  flask-marshmallow 1.5.0 dropped marshmallow 3.x support entirely, and
  it broke `app/model.py`'s `fields.Number()` usage — `TypeError: Can't
  instantiate abstract class Number without an implementation for
  num_type`. Reverted both to marshmallow 3.x / flask-marshmallow
  1.4.0, the last pairing that supports marshmallow 3.x). A marshmallow 4
  migration would need every schema in `app/model.py` audited.
- **WTForms `==2.3.3`** — WTForms 3.x changed validator APIs. Used via
  `Flask-WTF` for forms; needs template/validator review before bumping.

User's call on 2026-08-20: document these for now, don't attempt the
migrations in this pass.

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
