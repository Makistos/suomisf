#!/bin/bash
#
# Restore Test Database from Golden Dump
#
# Restores the test database from a golden database dump.
#
# Usage:
#   ./restore_test_db.sh [test_db_url] [dump_file]
#
# Arguments:
#   test_db_url - PostgreSQL connection URL (defaults to TEST_DATABASE_URL env var)
#   dump_file   - SQL dump file path (defaults to fixtures/golden_db.sql)
#
# Examples:
#   ./restore_test_db.sh
#   ./restore_test_db.sh "postgresql://test:test@localhost:5432/suomisf_test"
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"

TEST_DB="${1:-$TEST_DATABASE_URL}"
DUMP_FILE="${2:-$TESTS_DIR/fixtures/golden_db.sql}"

if [ -z "$TEST_DB" ]; then
    echo "Error: No test database URL provided."
    echo "Usage: $0 <test_db_url> [dump_file]"
    echo "Or set TEST_DATABASE_URL environment variable."
    exit 1
fi

if [ ! -f "$DUMP_FILE" ]; then
    echo "Error: Dump file not found: $DUMP_FILE"
    echo "Run create_golden_db.sh first to create a golden dump."
    exit 1
fi

echo "Restoring test database..."
echo "Target: $TEST_DB"
echo "Source: $DUMP_FILE"

# Restore the dump
psql "$TEST_DB" -f "$DUMP_FILE" > /dev/null 2>&1

echo ""
echo "Test database restored successfully!"
echo ""
echo "Verify with:"
echo "  psql \$TEST_DATABASE_URL -c 'SELECT COUNT(*) FROM work;'"
