"""setup_test_db.py must never create test users in the production DB.

app/__init__.py loads its dotenv with override=True, so DATABASE_URL alone
cannot keep the app off production's .env: SUOMISF_DOTENV must be .env.e2e.
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent / 'scripts' / 'setup_test_db.py'


def test_users_only_refuses_without_e2e_dotenv():
    # conftest sets SUOMISF_DOTENV for this process; the script must not
    # inherit it here.
    env = {k: v for k, v in os.environ.items() if k != 'SUOMISF_DOTENV'}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), '--users-only'],
        env=env, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode != 0
    assert 'SUOMISF_DOTENV=.env.e2e' in result.stdout + result.stderr
    assert 'Created' not in result.stdout
