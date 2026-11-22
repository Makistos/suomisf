#!/usr/bin/env python3
"""
SuomiSF Test Database Setup

Creates the test database for API tests (first-time setup on a machine):
fixes PostgreSQL collation, creates suomisf_test and sets its search_path.
Its data comes from the golden dump (tests/scripts/golden.py), which the
test runner restores before every session.

Usage:
    pdm run python tests/scripts/setup_test_db.py [--users-only]

Options:
    --users-only  Only create test users (skip database creation)
"""

import argparse
import os
import subprocess
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


# Test database configuration
TEST_DB_NAME = 'suomisf_test'
MAIN_DB_NAME = 'suomisf'
DB_USER = 'mep'

# Test user credentials
TEST_USER_EMAIL = 'testuser@example.com'
TEST_USER_PASSWORD = 'testpassword123'
TEST_USER_NAME = 'Test User'

TEST_ADMIN_EMAIL = 'testadmin@example.com'
TEST_ADMIN_PASSWORD = 'testadminpass123'
TEST_ADMIN_NAME = 'Test Admin'


def run_psql(sql: str, database: str = 'postgres') -> "tuple[bool, str]":
    """Run a SQL command via psql as postgres user."""
    try:
        result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-d', database, '-c', sql],
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr or ""


def fix_collation():
    """Fix PostgreSQL collation version mismatch."""
    print("\n1. Fixing collation version mismatch...")

    databases = ['template1', 'postgres', MAIN_DB_NAME]
    for db in databases:
        success, _ = run_psql(
            f"ALTER DATABASE {db} REFRESH COLLATION VERSION;",
            database=db
        )
        if success:
            print(f"   Fixed collation for {db}")
        # Ignore errors - db might not need fixing


def check_database_exists(db_name: str) -> bool:
    """Check if a database exists."""
    success, output = run_psql(
        f"SELECT 1 FROM pg_database WHERE datname = '{db_name}';"
    )
    return success and output is not None and '1' in output


def create_database():
    """Create the test database."""
    print(f"\n2. Creating test database '{TEST_DB_NAME}'...")

    if check_database_exists(TEST_DB_NAME):
        print(f"   Database '{TEST_DB_NAME}' already exists")

        # Ask to drop and recreate
        response = input("   Drop and recreate? [y/N]: ").strip().lower()
        if response == 'y':
            success, _ = run_psql(f"DROP DATABASE {TEST_DB_NAME};")
            if not success:
                print("   ERROR: Failed to drop database")
                return False
        else:
            return True

    # Create database
    try:
        subprocess.run(
            ['sudo', '-u', 'postgres', 'createdb', TEST_DB_NAME],
            check=True,
            capture_output=True
        )
        print(f"   Created database '{TEST_DB_NAME}'")
    except subprocess.CalledProcessError as e:
        print(f"   ERROR: Failed to create database: {e.stderr.decode()}")
        return False

    # Grant privileges
    success, _ = run_psql(
        f"GRANT ALL PRIVILEGES ON DATABASE {TEST_DB_NAME} TO {DB_USER};",
        database=TEST_DB_NAME
    )
    if success:
        print(f"   Granted privileges to {DB_USER}")

    return True


def create_test_users():
    """Create test users in the database."""
    print("\n4. Creating test users...")

    # app/__init__.py loads its dotenv with override=True: with the
    # default .env, DATABASE_URL below is overwritten and the users land
    # in the main database. Only .env.e2e points at suomisf_test.
    if os.environ.get('SUOMISF_DOTENV') != '.env.e2e':
        print("   ERROR: run with SUOMISF_DOTENV=.env.e2e, e.g.\n"
              "   SUOMISF_DOTENV=.env.e2e pdm run python "
              "tests/scripts/setup_test_db.py --users-only")
        return False

    # Set environment to use test database BEFORE importing app
    os.environ['DATABASE_URL'] = (
        f'postgresql+psycopg2://{DB_USER}@127.0.0.1/{TEST_DB_NAME}'
    )

    try:
        # Import inside function after setting env var
        # Need to reload if already imported
        if 'app' in sys.modules:
            # Clear cached imports to pick up new DATABASE_URL
            for mod_name in list(sys.modules.keys()):
                if mod_name.startswith('app'):
                    del sys.modules[mod_name]

        from app import app, db
        from app.orm_decl import User

        with app.app_context():
            # Create regular test user
            user = (
                db.session.query(User).filter_by(name=TEST_USER_NAME).first()
            )
            if user:
                print(
                    f"   User '{TEST_USER_NAME}' already exists (id={user.id})"
                )
            else:
                user = User()
                user.name = TEST_USER_NAME  # type: ignore[assignment]
                user.is_admin = False  # type: ignore[assignment]
                user.set_password(TEST_USER_PASSWORD)
                db.session.add(user)
                db.session.commit()
                print(f"   Created user '{TEST_USER_NAME}' (id={user.id})")

            # Create admin test user
            admin = (
                db.session.query(User).filter_by(name=TEST_ADMIN_NAME).first()
            )
            if admin:
                print(
                    f"   Admin '{TEST_ADMIN_NAME}' already exists "
                    f"(id={admin.id})"
                )
            else:
                admin = User()
                admin.name = TEST_ADMIN_NAME  # type: ignore[assignment]
                admin.is_admin = True  # type: ignore[assignment]
                admin.set_password(TEST_ADMIN_PASSWORD)
                db.session.add(admin)
                db.session.commit()
                print(f"   Created admin '{TEST_ADMIN_NAME}' (id={admin.id})")

        return True

    except Exception as e:
        print(f"   ERROR: Failed to create users: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Set up test database')
    parser.add_argument('--users-only', action='store_true',
                        help='Only create test users')
    args = parser.parse_args()

    print("=" * 60)
    print("SuomiSF Test Database Setup")
    print("=" * 60)

    if args.users_only:
        # Just create users in existing database
        if create_test_users():
            print("\n" + "=" * 60)
            print("Test users created!")
            print("=" * 60)
        else:
            sys.exit(1)
        return

    # Full setup
    fix_collation()

    if not create_database():
        sys.exit(1)

    # Restored dumps keep the schema, not database-level settings.
    success, _ = run_psql(
        f"ALTER DATABASE {TEST_DB_NAME} SET search_path TO suomisf, "
        "public;",
        TEST_DB_NAME,
    )
    if not success:
        print("   ERROR: Failed to set search_path")
        sys.exit(1)
    print("   Set search_path to suomisf, public")

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"\nTest database: {TEST_DB_NAME}")
    print("Test credentials:")
    print(f"  User:  {TEST_USER_EMAIL} / {TEST_USER_PASSWORD}")
    print(f"  Admin: {TEST_ADMIN_EMAIL} / {TEST_ADMIN_PASSWORD}")
    print("\nNext, first time on this machine (needs the dev DB):")
    print("  pdm run golden-refresh && pdm run golden-accept")
    print("Then run tests (they restore the golden dump themselves):")
    print("  pdm run pytest tests -m 'not network'")

if __name__ == '__main__':
    main()
