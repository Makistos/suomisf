# Security debt

Tracks dependency vulnerabilities investigated but deliberately not fixed
yet, and why. Also tracks non-CVE version debt (exact-pinned deps stuck on
an old major with no security issue, just outdated) since it's the same
kind of "needs a real migration, not a bump" decision.

Last reviewed: 2026-08-20.

## Flask 2.3.2 / Werkzeug (pinned `<3.0.0`)

`pyproject.toml` pins `Flask==2.3.2` and `werkzeug<3.0.0`. All 6 open
GitHub dependabot alerts on this repo are Werkzeug/Flask CVEs, and every
one of them only has a fix in the 3.x line:

| package | fixed in | current constraint |
|---|---|---|
| Flask | 3.1.3 | `==2.3.2` |
| Werkzeug | 3.1.4 – 3.1.6 (several CVEs) | `<3.0.0` |

Most are `safe_join()` Windows-device-name issues (low real-world risk on
a Linux deployment), but one is a Werkzeug debugger RCE
(CVE-2024-34069 / GHSA-2g68-c3qc-8985, fixed in 3.0.3) — worth
prioritizing even without the full 3.1.x jump. Real-world exposure
depends on whether Flask's debugger is enabled in production
(`debug=True` / `FLASK_DEBUG=1`) — confirm it's off if this stays
unpatched for a while.

**Dashboard caveat (2026-08-20):** GitHub's dependabot UI marked 5 of
these Werkzeug alerts, including the RCE one, as "fixed" the moment
`pdm.lock` was regenerated and pushed — but Werkzeug is still `2.3.8` in
both `pdm.lock` and `.venv` (verified directly, not just via the
dashboard). This looks like a scanner false-negative from re-parsing the
new lockfile format, not a real fix. Don't trust this repo's dependabot
alert *count* for Werkzeug without cross-checking the actual installed
version — the vulnerabilities listed above are still real and open.

This is a major-version bump touching every request the backend handles
(routing, sessions, request parsing all go through Werkzeug). Needs its
own migration pass:

- Read the Flask 2→3 and Werkzeug 2→3 changelogs for breaking changes.
- Check compatibility of the other pinned Flask extensions
  (`Flask-Login`, `Flask-Migrate`, `flask-marshmallow`, `Flask-Cors`,
  `Flask-JWT-Extended`, `Flask-WTF`, `Bootstrap-Flask`) with Flask 3.
- Test the full API surface, not just a typecheck — run against a real
  dev DB and exercise auth, uploads, and session handling specifically
  since those are the areas Werkzeug 3 changed.

Deferred at the user's explicit request during the 2026-08-19 session
rather than attempted blind.

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
- **Bootstrap-Flask `==1.3.1`** — Bootstrap-Flask 2.x dropped Bootstrap 4
  support (requires Bootstrap 5 templates). Frontend-facing risk — a
  bump here means auditing every server-rendered template that uses its
  macros, not just a Python-side change.

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
