"""
SuomiSF Test Database Manager

Utilities for managing the test database and golden database operations.
"""

import os
import subprocess
import sys
from typing import Optional
from datetime import datetime, timezone


class DatabaseManager:
    """Manages test database operations."""

    def __init__(
        self,
        test_db_url: Optional[str] = None,
        golden_db_path: Optional[str] = None
    ):
        self.test_db_url = test_db_url or os.environ.get(
            'TEST_DATABASE_URL',
            'postgresql://test_user:test_pass@localhost:5432/suomisf_test'
        )
        self.golden_db_path = golden_db_path or os.path.join(
            os.path.dirname(__file__), 'fixtures', 'golden_db.sql'
        )

    def create_golden_dump(
        self,
        source_db_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> bool:
        """
        Create a golden database dump from source database.

        Args:
            source_db_url: Database URL to dump from (defaults to DATABASE_URL)
            output_path: Where to save the dump (defaults to golden_db_path)

        Returns:
            True if successful, False otherwise
        """
        source_url = source_db_url or os.environ.get('DATABASE_URL')
        if not source_url:
            print("Error: No source database URL provided")
            return False

        output = output_path or self.golden_db_path

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output), exist_ok=True)

        try:
            result = subprocess.run(
                [
                    'pg_dump',
                    '--clean',
                    '--if-exists',
                    '--no-owner',
                    '--no-privileges',
                    '-f', output,
                    source_url
                ],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Golden database created: {output}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error creating golden dump: {e.stderr}")
            return False

        except FileNotFoundError:
            print("Error: pg_dump not found. Ensure PostgreSQL client tools are installed.")
            return False

    def restore_from_golden(self, target_db_url: Optional[str] = None) -> bool:
        """
        Restore test database from golden dump.

        Args:
            target_db_url: Database URL to restore to (defaults to test_db_url)

        Returns:
            True if successful, False otherwise
        """
        target_url = target_db_url or self.test_db_url

        if not os.path.exists(self.golden_db_path):
            print(f"Error: Golden database not found at {self.golden_db_path}")
            return False

        try:
            result = subprocess.run(
                ['psql', target_url, '-f', self.golden_db_path],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"Database restored from: {self.golden_db_path}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error restoring database: {e.stderr}")
            return False

        except FileNotFoundError:
            print("Error: psql not found. Ensure PostgreSQL client tools are installed.")
            return False

    def reset_database(self) -> bool:
        """
        Drop and recreate test database from golden dump.

        Returns:
            True if successful, False otherwise
        """
        return self.restore_from_golden()

    def verify_connection(self, db_url: Optional[str] = None) -> bool:
        """
        Verify database connection.

        Args:
            db_url: Database URL to verify (defaults to test_db_url)

        Returns:
            True if connection successful, False otherwise
        """
        url = db_url or self.test_db_url

        try:
            result = subprocess.run(
                ['psql', url, '-c', 'SELECT 1;'],
                capture_output=True,
                text=True,
                check=True
            )
            return True

        except subprocess.CalledProcessError:
            return False

        except FileNotFoundError:
            return False

    def get_table_counts(self, db_url: Optional[str] = None) -> dict:
        """
        Get row counts for all tables in database.

        Returns:
            Dictionary of table names to row counts
        """
        url = db_url or self.test_db_url

        query = """
        SELECT schemaname, relname, n_live_tup
        FROM pg_stat_user_tables
        ORDER BY n_live_tup DESC;
        """

        try:
            result = subprocess.run(
                ['psql', url, '-t', '-c', query],
                capture_output=True,
                text=True,
                check=True
            )

            counts = {}
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        table_name = parts[1]
                        count = int(parts[2]) if parts[2] else 0
                        counts[table_name] = count

            return counts

        except Exception as e:
            print(f"Error getting table counts: {e}")
            return {}


def main():
    """CLI interface for database management."""
    import argparse

    parser = argparse.ArgumentParser(description='SuomiSF Test Database Manager')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Create golden dump command
    create_parser = subparsers.add_parser(
        'create-golden',
        help='Create golden database dump from source'
    )
    create_parser.add_argument(
        '--source', '-s',
        help='Source database URL (defaults to DATABASE_URL)'
    )
    create_parser.add_argument(
        '--output', '-o',
        help='Output file path'
    )

    # Restore command
    restore_parser = subparsers.add_parser(
        'restore',
        help='Restore test database from golden dump'
    )
    restore_parser.add_argument(
        '--target', '-t',
        help='Target database URL (defaults to TEST_DATABASE_URL)'
    )

    # Verify command
    verify_parser = subparsers.add_parser(
        'verify',
        help='Verify database connection'
    )
    verify_parser.add_argument(
        '--db', '-d',
        help='Database URL to verify'
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Show table row counts'
    )
    stats_parser.add_argument(
        '--db', '-d',
        help='Database URL'
    )

    args = parser.parse_args()

    manager = DatabaseManager()

    if args.command == 'create-golden':
        success = manager.create_golden_dump(
            source_db_url=args.source,
            output_path=args.output
        )
        sys.exit(0 if success else 1)

    elif args.command == 'restore':
        success = manager.restore_from_golden(target_db_url=args.target)
        sys.exit(0 if success else 1)

    elif args.command == 'verify':
        if manager.verify_connection(db_url=args.db):
            print("Connection successful")
            sys.exit(0)
        else:
            print("Connection failed")
            sys.exit(1)

    elif args.command == 'stats':
        counts = manager.get_table_counts(db_url=args.db)
        if counts:
            print(f"{'Table':<40} {'Rows':>10}")
            print('-' * 52)
            for table, count in sorted(counts.items(), key=lambda x: -x[1]):
                print(f"{table:<40} {count:>10}")
        else:
            print("No table statistics available")
            sys.exit(1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
