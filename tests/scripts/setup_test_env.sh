#!/bin/bash
#
# Setup Test Environment
#
# Sets up the complete test environment including:
# - Creating test database (if not exists)
# - Restoring from golden dump
# - Installing test dependencies
#
# Usage:
#   ./setup_test_env.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$TESTS_DIR")"

echo "=========================================="
echo "SuomiSF Test Environment Setup"
echo "=========================================="
echo ""

# Check for required environment variables
if [ -z "$TEST_DATABASE_URL" ]; then
    echo "Warning: TEST_DATABASE_URL not set"
    echo "Using default: postgresql://test_user:test_pass@localhost:5432/suomisf_test"
    export TEST_DATABASE_URL="postgresql://test_user:test_pass@localhost:5432/suomisf_test"
fi

# Step 1: Install test dependencies
echo "Step 1: Installing test dependencies..."
if [ -f "$PROJECT_DIR/.venv/bin/pip" ]; then
    "$PROJECT_DIR/.venv/bin/pip" install -r "$TESTS_DIR/requirements-test.txt" --quiet
    echo "  Dependencies installed."
else
    echo "  Warning: Virtual environment not found at $PROJECT_DIR/.venv"
    echo "  Install manually: pip install -r tests/requirements-test.txt"
fi

# Step 2: Verify database connection
echo ""
echo "Step 2: Verifying database connection..."
if psql "$TEST_DATABASE_URL" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "  Database connection successful."
else
    echo "  Error: Cannot connect to test database."
    echo "  Create the database first:"
    echo "    createdb suomisf_test"
    exit 1
fi

# Step 3: Restore golden database (if exists)
echo ""
echo "Step 3: Checking for golden database dump..."
GOLDEN_DB="$TESTS_DIR/fixtures/golden_db.sql"
if [ -f "$GOLDEN_DB" ]; then
    echo "  Found golden database: $GOLDEN_DB"
    echo "  Restoring..."
    "$SCRIPT_DIR/restore_test_db.sh" "$TEST_DATABASE_URL" "$GOLDEN_DB"
else
    echo "  No golden database found at $GOLDEN_DB"
    echo "  Create one with:"
    echo "    ./scripts/create_golden_db.sh \$DATABASE_URL"
fi

# Step 4: Verify setup
echo ""
echo "Step 4: Verifying setup..."
TABLE_COUNT=$(psql "$TEST_DATABASE_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')

if [ -n "$TABLE_COUNT" ] && [ "$TABLE_COUNT" -gt 0 ]; then
    echo "  Found $TABLE_COUNT tables in test database."
else
    echo "  Warning: No tables found. Database may be empty."
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Run tests with:"
echo "  cd $PROJECT_DIR"
echo "  pytest tests/"
echo ""
echo "Run benchmarks with:"
echo "  python -m tests.benchmark.benchmark_runner"
