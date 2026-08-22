#!/usr/bin/env python3
"""
Mint a valid password-reset token for a user, for the frontend Playwright
suite's password-reset spec (suomisf-ui/tests/user/password-reset.spec.ts).

The reset token is deterministic - a signed hash of the user's id and a
fingerprint of their current password hash (see app/impl_users.py's
_reset_serializer/_password_fingerprint) - so a test can mint one directly
instead of needing to intercept an email.

Must be run with SUOMISF_DOTENV=.env.e2e in the environment, same as
setup_e2e_db.py, so this binds to suomisf_test rather than production.

Usage:
    SUOMISF_DOTENV=.env.e2e pdm run python tests/scripts/mint_reset_token.py "Test User"

Prints only the token to stdout.
"""

import os
import sys

if os.environ.get('SUOMISF_DOTENV') != '.env.e2e':
    sys.exit(
        "mint_reset_token.py must be run with SUOMISF_DOTENV=.env.e2e set - "
        "see the module docstring for why."
    )

if len(sys.argv) != 2:
    sys.exit("Usage: mint_reset_token.py <username>")

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app import app  # noqa: E402
from app.orm_decl import User  # noqa: E402
from app.route_helpers import new_session  # noqa: E402
from app.impl_users import _reset_serializer, _password_fingerprint  # noqa: E402

username = sys.argv[1]

with app.app_context():
    session = new_session()
    user = session.query(User).filter(User.name == username).first()
    if not user:
        sys.exit(f"No user named {username!r} in {app.config['SQLALCHEMY_DATABASE_URI']}")
    token = _reset_serializer().dumps(
        {'uid': user.id, 'fp': _password_fingerprint(user)})
    print(token)
