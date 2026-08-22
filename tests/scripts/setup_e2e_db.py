#!/usr/bin/env python3
"""
Clone the dev database into suomisf_test and ensure the E2E test accounts
(Test Admin / Test User) exist there, for the frontend Playwright suite's
global setup (suomisf-ui/tests/global-setup.ts).

Must be run with SUOMISF_DOTENV=.env.e2e in the environment. app/__init__.py
calls load_dotenv(..., override=True), which unconditionally sets
DATABASE_URL from whichever dotenv file it's told to read - if that's the
default .env (production), the *first* import of the `app` package in this
process (triggered inside create_test_users(), via clone_test_database's
sibling function) would bind to the production database instead of
suomisf_test. Pointing SUOMISF_DOTENV at .env.e2e (DATABASE_URL ->
suomisf_test) makes that first bind land on the right database instead.

Usage:
    SUOMISF_DOTENV=.env.e2e pdm run python tests/scripts/setup_e2e_db.py
"""

import os
import sys

if os.environ.get('SUOMISF_DOTENV') != '.env.e2e':
    sys.exit(
        "setup_e2e_db.py must be run with SUOMISF_DOTENV=.env.e2e set - "
        "see the module docstring for why."
    )

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from tests.conftest import clone_test_database, create_test_users  # noqa: E402

# .invalid is reserved by RFC 2606 to never resolve - safe for a fixture
# email that only needs to exist for the password-reset spec's lookup.
TEST_USER_EMAIL = 'test-user-e2e@example.invalid'


def ensure_test_user_email():
    from app import app, db
    from app.orm_decl import User

    with app.app_context():
        user = db.session.query(User).filter_by(name='Test User').first()
        if user and user.email != TEST_USER_EMAIL:
            user.email = TEST_USER_EMAIL  # type: ignore[assignment]
            db.session.commit()


if __name__ == '__main__':
    clone_test_database()
    create_test_users()
    ensure_test_user_email()
    print("[setup_e2e_db] suomisf_test ready with E2E test accounts")
