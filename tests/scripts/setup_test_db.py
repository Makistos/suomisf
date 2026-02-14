#!/usr/bin/env python3
"""
SuomiSF Test Database Setup

Creates and populates a test database for API tests.
Handles PostgreSQL collation fixes, database creation, data cloning, and test user setup.

Usage:
    pdm run python tests/scripts/setup_test_db.py [--clone] [--users-only]

Options:
    --clone       Clone data from main database (default: just create empty db)
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


def clone_data():
    """Clone data from main database to test database."""
    print(f"\n3. Cloning data from '{MAIN_DB_NAME}' to '{TEST_DB_NAME}'...")

    # Use a path in /tmp that postgres can write to directly
    dump_file = f'/tmp/suomisf_dump_{os.getpid()}.sql'

    try:
        # Remove if exists from previous failed run (may be owned by postgres)
        if os.path.exists(dump_file):
            subprocess.run(['sudo', 'rm', '-f', dump_file], capture_output=True)

        # Dump main database to file
        print("   Dumping main database...")
        dump_result = subprocess.run(
            ['sudo', '-u', 'postgres', 'pg_dump', '-f', dump_file, MAIN_DB_NAME],
            capture_output=True,
            text=True
        )

        if dump_result.returncode != 0:
            print(f"   ERROR: pg_dump failed: {dump_result.stderr}")
            return False

        # Check dump file exists and has content
        if not os.path.exists(dump_file):
            print(f"   ERROR: Dump file was not created at {dump_file}")
            return False

        dump_size = os.path.getsize(dump_file)
        print(f"   Dump file created: {dump_size / 1024 / 1024:.1f} MB")

        if dump_size < 1000:
            print(f"   ERROR: Dump file too small, something went wrong")
            return False

        # Restore from file
        print("   Restoring to test database...")
        restore_result = subprocess.run(
            ['sudo', '-u', 'postgres', 'psql', '-d', TEST_DB_NAME, '-f', dump_file],
            capture_output=True,
            text=True
        )

        # Show restore output for debugging
        if restore_result.stderr:
            # Filter out common non-fatal warnings
            errors = [line for line in restore_result.stderr.split('\n')
                      if line and 'NOTICE:' not in line and 'already exists' not in line]
            if errors:
                print(f"   Restore warnings/errors:")
                for err in errors[:10]:  # Show first 10 errors
                    print(f"      {err}")

        # Clean up temp file (owned by postgres, so use sudo)
        subprocess.run(['sudo', 'rm', '-f', dump_file], capture_output=True)

        if restore_result.returncode != 0:
            print(f"   ERROR: psql restore failed (exit code {restore_result.returncode})")
            return False

        # Set search_path to include suomisf schema (matches main database)
        run_psql(
            f"ALTER DATABASE {TEST_DB_NAME} SET search_path TO suomisf, public;",
            TEST_DB_NAME
        )
        print("   Set search_path to suomisf, public")

        # Verify data was actually copied (tables are in 'suomisf' schema)
        success, output = run_psql("SELECT COUNT(*) FROM suomisf.work;", TEST_DB_NAME)
        if success and output:
            print(f"   Data cloned successfully")
            return True
        else:
            print("   WARNING: Clone may have failed - tables not found")
            print(f"   psql output: {output}")
            return False

    except Exception as e:
        print(f"   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_users():
    """Create test users in the database."""
    print("\n4. Creating test users...")

    # Set environment to use test database BEFORE importing app
    os.environ['DATABASE_URL'] = f'postgresql+psycopg2://{DB_USER}@127.0.0.1/{TEST_DB_NAME}'

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
            user = db.session.query(User).filter_by(name=TEST_USER_NAME).first()
            if user:
                print(f"   User '{TEST_USER_NAME}' already exists (id={user.id})")
            else:
                user = User()
                user.name = TEST_USER_NAME  # type: ignore[assignment]
                user.is_admin = False  # type: ignore[assignment]
                user.set_password(TEST_USER_PASSWORD)
                db.session.add(user)
                db.session.commit()
                print(f"   Created user '{TEST_USER_NAME}' (id={user.id})")

            # Create admin test user
            admin = db.session.query(User).filter_by(name=TEST_ADMIN_NAME).first()
            if admin:
                print(f"   Admin '{TEST_ADMIN_NAME}' already exists (id={admin.id})")
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


def verify_setup():
    """Verify the test database is properly set up."""
    print("\n5. Verifying setup...")

    # Use psql directly to verify, avoiding Flask app caching issues
    # Tables are in the 'suomisf' schema
    tables = ['work', 'edition', 'person', 'shortstory']
    for table in tables:
        success, output = run_psql(f"SELECT COUNT(*) FROM suomisf.{table};", TEST_DB_NAME)
        if success and output:
            # Parse count from output
            lines = output.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.isdigit():
                    print(f"   {table}: {line} rows")
                    break
        else:
            print(f"   {table}: NOT FOUND")

    print("   Database verification complete")
    return True


def main():
    parser = argparse.ArgumentParser(description='Set up test database')
    parser.add_argument('--clone', action='store_true',
                        help='Clone data from main database')
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

    if args.clone:
        if not clone_data():
            sys.exit(1)

    if not create_test_users():
        sys.exit(1)

    verify_setup()

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"\nTest database: {TEST_DB_NAME}")
    print(f"Test credentials:")
    print(f"  User:  {TEST_USER_EMAIL} / {TEST_USER_PASSWORD}")
    print(f"  Admin: {TEST_ADMIN_EMAIL} / {TEST_ADMIN_PASSWORD}")
    print(f"\nTo run tests against this database:")
    print(f"  export DATABASE_URL='postgresql+psycopg2://{DB_USER}@127.0.0.1/{TEST_DB_NAME}'")
    print(f"  pdm run pytest tests/api/")


if __name__ == '__main__':
    main()
