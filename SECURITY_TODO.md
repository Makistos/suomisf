# Security debt

Tracks dependency vulnerabilities investigated but deliberately not fixed
yet, and why.

Last reviewed: 2026-08-19.

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
(CVE-2024-34069, fixed in 3.0.3) — worth prioritizing even without the
full 3.1.x jump.

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

See also `../suomisf-ui/SECURITY_TODO.md` for the frontend's remaining
items (react-router v7, vite 8, quill, face-api.js/node-fetch).
