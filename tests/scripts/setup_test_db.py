#!/usr/bin/env python3
"""
SuomiSF Test Database Setup

Creates a test user and prepares the database for write operation tests.
Run this before running tests that require authentication.

Usage:
    pdm run python tests/scripts/setup_test_db.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from app import app, db
from app.orm_decl import User


# Test user credentials - also defined in conftest.py
TEST_USER_EMAIL = 'testuser@example.com'
TEST_USER_PASSWORD = 'testpassword123'
TEST_USER_NAME = 'Test User'

TEST_ADMIN_EMAIL = 'testadmin@example.com'
TEST_ADMIN_PASSWORD = 'testadminpass123'
TEST_ADMIN_NAME = 'Test Admin'


def create_test_user(email: str, password: str, name: str,
                     is_admin: bool = False) -> User:
    """Create a test user if it doesn't exist."""
    with app.app_context():
        user = User.query.filter_by(email=email).first()

        if user:
            print(f"  User '{email}' already exists (id={user.id})")
            return user

        user = User(
            name=name,
            email=email,
            is_admin=is_admin
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        print(f"  Created user '{email}' (id={user.id}, admin={is_admin})")
        return user


def setup_test_database():
    """Set up the test database with required test data."""
    print("=" * 60)
    print("SuomiSF Test Database Setup")
    print("=" * 60)

    with app.app_context():
        print("\n1. Creating test users...")
        create_test_user(TEST_USER_EMAIL, TEST_USER_PASSWORD,
                         TEST_USER_NAME, is_admin=False)
        create_test_user(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD,
                         TEST_ADMIN_NAME, is_admin=True)

        print("\n2. Verifying database connection...")
        try:
            result = db.session.execute(db.text("SELECT 1"))
            result.fetchone()
            print("  Database connection OK")
        except Exception as e:
            print(f"  Database connection FAILED: {e}")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print(f"\nTest credentials:")
    print(f"  User:  {TEST_USER_EMAIL} / {TEST_USER_PASSWORD}")
    print(f"  Admin: {TEST_ADMIN_EMAIL} / {TEST_ADMIN_PASSWORD}")


if __name__ == '__main__':
    setup_test_database()
