Always use line widths less or equal to 79 characters.

Run the app with gunicorn against the `wsgi:app` entrypoint (`gunicorn
wsgi:app`). The `suomisf:app` entrypoint is stale — it fails to import — so
do not use it.

After making backend changes, remember to restart the backend on the
server for them to take effect (the running gunicorn does not auto-reload;
reload it, e.g. `kill -HUP $(cat /tmp/gunicorn.pid)`, or restart the
service on the deployment server).

## Database migrations

Schema changes are hand-written, numbered SQL files in `migrations/NNN_*.sql`
(not Alembic autogenerate). Add the next number in sequence and apply it
manually against the target database, e.g.
`psql -h 127.0.0.1 -U mep -d suomisf -f migrations/NNN_*.sql`. Tables live in
the `suomisf` schema. Keep the SQLAlchemy models in `app/orm_decl.py` in sync
with each migration.

If changing or adding an API function always add tests and update documentation
both for API and tests and document the API.

Always recreate test database and add test user before running tests.
Never run tests against or modify the main database.

When doing database refactoring do not update the snapshots until finished.

## Testing Documentation

When adding or modifying API tests, always update the following files:

1. **tests/TEST_DOCUMENTATION.md** - Document each test with:
   - Test name and description
   - Parameter values used
   - Expected behaviors and assertions
   - Any fixtures or helper functions used

2. **tests/API_COVERAGE.md** - Update the API coverage matrix to reflect:
   - Which endpoints are tested
   - Test coverage status for each HTTP method
   - Any new endpoints or test scenarios added
