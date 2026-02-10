#!/bin/bash
#
# Create Golden Database Dump
#
# Creates a golden database dump from the source database for use in testing.
#
# Usage:
#   ./create_golden_db.sh [source_db_url] [output_file]
#
# Arguments:
#   source_db_url - PostgreSQL connection URL (defaults to DATABASE_URL env var)
#   output_file   - Output SQL file path (defaults to fixtures/golden_db.sql)
#
# Examples:
#   ./create_golden_db.sh
#   ./create_golden_db.sh "postgresql://user:pass@localhost:5432/suomisf"
#   ./create_golden_db.sh "$DATABASE_URL" "../fixtures/golden_db.sql"
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(dirname "$SCRIPT_DIR")"

SOURCE_DB="${1:-$DATABASE_URL}"
DUMP_FILE="${2:-$TESTS_DIR/fixtures/golden_db.sql}"

if [ -z "$SOURCE_DB" ]; then
    echo "Error: No source database URL provided."
    echo "Usage: $0 <source_db_url> [output_file]"
    echo "Or set DATABASE_URL environment variable."
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$DUMP_FILE")"

echo "Creating golden database dump..."
echo "Source: $SOURCE_DB"
echo "Output: $DUMP_FILE"

pg_dump \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    --no-comments \
    -f "$DUMP_FILE" \
    "$SOURCE_DB"

# Get file size
SIZE=$(ls -lh "$DUMP_FILE" | awk '{print $5}')

echo ""
echo "Golden database created successfully!"
echo "File: $DUMP_FILE"
echo "Size: $SIZE"
echo ""
echo "To restore to test database:"
echo "  ./restore_test_db.sh \$TEST_DATABASE_URL $DUMP_FILE"
