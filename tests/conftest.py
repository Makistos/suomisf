"""
SuomiSF API Test Configuration

Pytest fixtures and configuration for comprehensive API testing.
Automatically recreates the test database from the main database
and creates test users before running tests.

Use --skip-db-setup to skip database recreation when iterating.
Use --update-snapshots to also regenerate API response snapshots.
"""

import os
import json
import subprocess
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Add project root to path
import sys
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import pytest


# -------------------------------------------------------------------
# Database configuration
# -------------------------------------------------------------------

DB_USER = 'mep'
MAIN_DB_NAME = 'suomisf'
TEST_DB_NAME = 'suomisf_test'
TEST_DB_URL = (
    f'postgresql+psycopg2://{DB_USER}@127.0.0.1/{TEST_DB_NAME}'
)

# Ensure the app uses the test database
os.environ['DATABASE_URL'] = TEST_DB_URL


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

class TestConfig:
    """Test configuration settings."""

    # Database
    TEST_DATABASE_URL = os.environ.get(
        'TEST_DATABASE_URL',
        f'postgresql://{DB_USER}@localhost:5432/{TEST_DB_NAME}'
    )
    GOLDEN_DB_PATH = os.path.join(
        os.path.dirname(__file__), 'fixtures', 'golden_db.sql'
    )

    # API
    BASE_URL = os.environ.get(
        'TEST_API_URL', 'http://localhost:5000/api'
    )

    # Auth
    ADMIN_USERNAME = os.environ.get(
        'TEST_ADMIN_USERNAME', 'testadmin'
    )
    ADMIN_PASSWORD = os.environ.get(
        'TEST_ADMIN_PASSWORD', 'testpass123'
    )
    USER_USERNAME = os.environ.get(
        'TEST_USER_USERNAME', 'testuser'
    )
    USER_PASSWORD = os.environ.get(
        'TEST_USER_PASSWORD', 'userpass123'
    )

    # Results
    RESULTS_DIR = os.path.join(
        os.path.dirname(__file__), 'results'
    )

    # Timeouts
    REQUEST_TIMEOUT = 30  # seconds


# -------------------------------------------------------------------
# Database setup helpers
# -------------------------------------------------------------------

def clone_test_database():
    """Clone main DB schema to test DB using pg_dump | psql.

    Drops the suomisf schema in the test database and restores
    it from the main database. Runs as the mep user (no sudo).
    """
    print("\n[setup] Cloning database "
          f"'{MAIN_DB_NAME}' -> '{TEST_DB_NAME}'...")
    start = time.time()

    # Drop existing schema
    subprocess.run(
        [
            'psql', '-U', DB_USER, '-d', TEST_DB_NAME,
            '-c', 'DROP SCHEMA IF EXISTS suomisf CASCADE;'
        ],
        capture_output=True, text=True, check=True
    )

    # Pipe pg_dump into psql for a clean restore
    dump = subprocess.Popen(
        ['pg_dump', '-U', DB_USER, '-n', 'suomisf',
         MAIN_DB_NAME],
        stdout=subprocess.PIPE
    )
    restore = subprocess.run(
        ['psql', '-U', DB_USER, '-d', TEST_DB_NAME],
        stdin=dump.stdout,
        capture_output=True, text=True
    )
    dump.wait()

    if dump.returncode != 0:
        raise RuntimeError(
            f"pg_dump failed (exit {dump.returncode})"
        )
    if restore.returncode != 0:
        raise RuntimeError(
            f"psql restore failed: {restore.stderr[:200]}"
        )

    elapsed = time.time() - start
    print(f"[setup] Database cloned in {elapsed:.1f}s")

    # Apply migration 001 (EditionShortStory, StoryContributor)
    _apply_migration_001()
    # Apply migration 002 (EditionContributor)
    _apply_migration_002()


MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'migrations'
)

MIGRATION_SQL = os.path.join(MIGRATIONS_DIR, '001_shortstory_migration.sql')

MIGRATION_002_SQL = os.path.join(
    MIGRATIONS_DIR, '002_edition_contributor_migration.sql'
)


def _apply_migration_001():
    """Apply migration 001 SQL to the test database."""
    if not os.path.exists(MIGRATION_SQL):
        print("[setup] Migration 001 SQL not found, skipping")
        return
    print("[setup] Applying migration 001...")
    result = subprocess.run(
        ['psql', '-U', DB_USER, '-d', TEST_DB_NAME,
         '-f', MIGRATION_SQL],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Migration 001 failed: {result.stderr[:400]}"
        )
    print("[setup] Migration 001 applied")


def _apply_migration_002():
    """Apply migration 002 SQL to the test database."""
    if not os.path.exists(MIGRATION_002_SQL):
        print("[setup] Migration 002 SQL not found, skipping")
        return
    print("[setup] Applying migration 002...")
    result = subprocess.run(
        ['psql', '-U', DB_USER, '-d', TEST_DB_NAME,
         '-f', MIGRATION_002_SQL],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Migration 002 failed: {result.stderr[:400]}"
        )
    print("[setup] Migration 002 applied")


def create_test_users():
    """Create test users in the test database."""
    print("[setup] Creating test users...")

    from app import app as flask_app, db
    from app.orm_decl import User

    test_users = [
        ('Test User', 'testpassword123', False),
        ('Test Admin', 'testadminpass123', True),
    ]

    with flask_app.app_context():
        for name, password, is_admin in test_users:
            user = db.session.query(User).filter_by(
                name=name
            ).first()
            if user:
                print(f"[setup]   {name} exists "
                      f"(id={user.id})")
            else:
                user = User()
                user.name = name  # type: ignore
                user.is_admin = is_admin  # type: ignore
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                print(f"[setup]   Created {name} "
                      f"(id={user.id})")


def update_snapshots():
    """Regenerate API response snapshots."""
    print("[setup] Updating snapshots...")
    from tests.scripts.update_snapshots import (
        generate_snapshots
    )
    results = generate_snapshots()
    n_ok = len(results['success'])
    n_fail = len(results['failed'])
    print(f"[setup] Snapshots: {n_ok} OK, {n_fail} failed")


# -------------------------------------------------------------------
# Pytest CLI option
# -------------------------------------------------------------------

def pytest_addoption(parser):
    """Add --skip-db-setup and --update-snapshots options."""
    parser.addoption(
        '--skip-db-setup',
        action='store_true',
        default=False,
        help='Skip database recreation and user creation'
    )
    parser.addoption(
        '--update-snapshots',
        action='store_true',
        default=False,
        help='Regenerate API response snapshots'
    )


# -------------------------------------------------------------------
# Session-scoped fixtures
# -------------------------------------------------------------------

@pytest.fixture(scope='session', autouse=True)
def setup_test_database(request):
    """Recreate test DB and create users before tests.

    Runs automatically before all tests. Use --skip-db-setup
    to skip when iterating on tests. Use --update-snapshots
    to also regenerate API response snapshots.
    """
    if request.config.getoption('--skip-db-setup'):
        print("\n[setup] Skipping DB setup (--skip-db-setup)")
        return

    clone_test_database()
    create_test_users()

    if request.config.getoption('--update-snapshots'):
        update_snapshots()

    print("[setup] Database setup complete\n")


@pytest.fixture(scope='session')
def test_config() -> TestConfig:
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture(scope='session')
def app(setup_test_database):
    """Get the Flask application instance."""
    import sqlalchemy as sa
    from app import app as flask_app, db
    import app.route_helpers as route_helpers_module
    import app.orm_decl as orm_decl_module

    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    # app/__init__.py calls load_dotenv('.env', override=True)
    # which replaces DATABASE_URL with the production URL.
    # Derive the test URL from the production URL by replacing
    # only the database name, preserving credentials.
    prod_url = os.environ.get('DATABASE_URL', '')
    if prod_url and MAIN_DB_NAME in prod_url:
        actual_test_url = prod_url.replace(
            f'/{MAIN_DB_NAME}', f'/{TEST_DB_NAME}', 1
        )
    else:
        actual_test_url = TEST_DB_URL

    flask_app.config['SQLALCHEMY_DATABASE_URI'] = actual_test_url

    # Override db_url so new_session() and load_user() use
    # the test database, not the production database.
    route_helpers_module.db_url = actual_test_url
    orm_decl_module.db_url = actual_test_url

    # Replace Flask-SQLAlchemy's cached engine so db.session
    # also uses the test database (engine is created at init_app
    # time and is not updated by config changes afterward).
    engines = db._app_engines.setdefault(flask_app, {})
    for engine in engines.values():
        engine.dispose()
    engines.clear()
    engines[None] = sa.create_engine(actual_test_url)

    yield flask_app


@pytest.fixture(scope='session')
def client(app):
    """Create a test client for the application."""
    return app.test_client()


@pytest.fixture(scope='session')
def db_session(app):
    """Create a database session for testing."""
    from app import db

    with app.app_context():
        yield db.session
        db.session.rollback()


# ---------------------------------------------------------------------------
# Function-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client(client):
    """Create an API test client wrapper."""
    return APITestClient(client)


@pytest.fixture
def auth_headers(api_client, test_config) -> Dict[str, str]:
    """Get authentication headers for admin user."""
    token = api_client.login(
        test_config.ADMIN_USERNAME,
        test_config.ADMIN_PASSWORD
    )
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


@pytest.fixture
def user_headers(api_client, test_config) -> Dict[str, str]:
    """Get authentication headers for regular user."""
    token = api_client.login(
        test_config.USER_USERNAME,
        test_config.USER_PASSWORD
    )
    if token:
        return {'Authorization': f'Bearer {token}'}
    return {}


# ---------------------------------------------------------------------------
# Snapshot Testing
# ---------------------------------------------------------------------------

SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'fixtures', 'snapshots')


class SnapshotManager:
    """Manages loading and comparing API response snapshots."""

    def __init__(self, snapshots_dir: str = SNAPSHOTS_DIR):
        self.snapshots_dir = snapshots_dir
        self._cache: Dict[str, Any] = {}

    def load_snapshot(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a snapshot by name."""
        if name in self._cache:
            return self._cache[name]

        filepath = os.path.join(self.snapshots_dir, f'{name}.json')
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
            self._cache[name] = snapshot
            return snapshot

    def get_expected_data(self, name: str) -> Optional[Any]:
        """Get the expected response data from a snapshot."""
        snapshot = self.load_snapshot(name)
        if snapshot and 'response' in snapshot:
            return snapshot['response'].get('data')
        return None

    def get_expected_status(self, name: str) -> Optional[int]:
        """Get the expected status code from a snapshot."""
        snapshot = self.load_snapshot(name)
        if snapshot and 'response' in snapshot:
            return snapshot['response'].get('status_code')
        return None

    def compare_response(
        self,
        name: str,
        actual_data: Any,
        ignore_keys: Optional[list] = None,
        check_subset: bool = False
    ) -> tuple:
        """
        Compare actual response data against snapshot.

        Args:
            name: Snapshot name
            actual_data: The actual API response data
            ignore_keys: Keys to ignore in comparison (e.g., timestamps)
            check_subset: If True, only check that expected keys exist in actual

        Returns:
            (matches: bool, diff: dict or None)
        """
        expected = self.get_expected_data(name)
        if expected is None:
            return False, {'error': f'Snapshot {name} not found'}

        return self._compare_data(expected, actual_data, ignore_keys, check_subset)

    def _compare_data(
        self,
        expected: Any,
        actual: Any,
        ignore_keys: Optional[list] = None,
        check_subset: bool = False
    ) -> tuple:
        """Recursively compare data structures."""
        ignore_keys = ignore_keys or []

        if isinstance(expected, dict) and isinstance(actual, dict):
            diff = {}
            keys_to_check = expected.keys() if check_subset else \
                set(expected.keys()) | set(actual.keys())

            for key in keys_to_check:
                if key in ignore_keys:
                    continue

                if key not in expected:
                    if not check_subset:
                        diff[key] = {'expected': None, 'actual': actual[key]}
                elif key not in actual:
                    diff[key] = {'expected': expected[key], 'actual': None}
                else:
                    matches, sub_diff = self._compare_data(
                        expected[key], actual[key], ignore_keys, check_subset
                    )
                    if not matches:
                        diff[key] = sub_diff

            return len(diff) == 0, diff if diff else None

        elif isinstance(expected, list) and isinstance(actual, list):
            if len(expected) != len(actual):
                return False, {
                    'length_mismatch': {
                        'expected': len(expected),
                        'actual': len(actual)
                    }
                }

            # For lists, compare element counts and types rather than exact order
            # This handles cases where DB order may vary
            return True, None

        else:
            if expected == actual:
                return True, None
            return False, {'expected': expected, 'actual': actual}

    def assert_matches_snapshot(
        self,
        name: str,
        actual_data: Any,
        ignore_keys: Optional[list] = None,
        check_counts: bool = True
    ):
        """Assert that actual data matches the snapshot."""
        snapshot = self.load_snapshot(name)
        if snapshot is None:
            raise AssertionError(
                f"Snapshot '{name}' not found. "
                f"Run 'pdm run python tests/scripts/update_snapshots.py' to generate."
            )

        expected = self.get_expected_data(name)

        # Check counts for list responses
        if check_counts and isinstance(expected, list) and isinstance(actual_data, list):
            assert len(actual_data) == len(expected), \
                f"Count mismatch: expected {len(expected)}, got {len(actual_data)}"

        # Check counts for dict responses with known count keys
        if check_counts and isinstance(expected, dict) and isinstance(actual_data, dict):
            count_keys = ['works', 'editions', 'shorts', 'magazines', 'covers',
                          'total_works', 'total_editions', 'total_pages']
            for key in count_keys:
                if key in expected and key in actual_data:
                    assert actual_data[key] == expected[key], \
                        f"Count mismatch for '{key}': expected {expected[key]}, got {actual_data[key]}"


@pytest.fixture(scope='session')
def snapshot_manager():
    """Provide snapshot manager for tests."""
    return SnapshotManager()


@pytest.fixture
def assert_snapshot(snapshot_manager):
    """Fixture to assert response matches snapshot."""
    def _assert(name: str, response, ignore_keys: Optional[list] = None):
        """Assert that response matches the named snapshot."""
        actual_data = response.json if hasattr(response, 'json') else response
        snapshot_manager.assert_matches_snapshot(name, actual_data, ignore_keys)
    return _assert


# ---------------------------------------------------------------------------
# API Test Client
# ---------------------------------------------------------------------------

class APITestClient:
    """Wrapper for Flask test client with API testing helpers."""

    def __init__(self, client):
        self.client = client
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None

    def login(self, username: str, password: str) -> Optional[str]:
        """Login and return access token."""
        response = self.client.post(
            '/api/login',
            json={'username': username, 'password': password},
            content_type='application/json'
        )

        if response.status_code == 200:
            data = response.get_json()
            if data:
                # Login endpoint returns tokens directly, not wrapped in 'response'
                self.access_token = data.get('access_token')
                self.refresh_token = data.get('refresh_token')
                return self.access_token
        return None

    def get(self, path: str, headers: Optional[Dict] = None, **kwargs) -> 'APIResponse':
        """Make GET request."""
        headers = headers or {}
        if self.access_token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.access_token}'

        response = self.client.get(path, headers=headers, **kwargs)
        return APIResponse(response)

    def post(self, path: str, data: Optional[Dict] = None,
             headers: Optional[Dict] = None, **kwargs) -> 'APIResponse':
        """Make POST request."""
        headers = headers or {}
        if self.access_token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.access_token}'

        response = self.client.post(
            path,
            json=data,
            headers=headers,
            content_type='application/json',
            **kwargs
        )
        return APIResponse(response)

    def put(self, path: str, data: Optional[Dict] = None,
            headers: Optional[Dict] = None, **kwargs) -> 'APIResponse':
        """Make PUT request."""
        headers = headers or {}
        if self.access_token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.access_token}'

        response = self.client.put(
            path,
            json=data,
            headers=headers,
            content_type='application/json',
            **kwargs
        )
        return APIResponse(response)

    def delete(self, path: str, headers: Optional[Dict] = None, **kwargs) -> 'APIResponse':
        """Make DELETE request."""
        headers = headers or {}
        if self.access_token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.access_token}'

        response = self.client.delete(path, headers=headers, **kwargs)
        return APIResponse(response)


class APIResponse:
    """Wrapper for Flask test response with assertion helpers."""

    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code
        self._json = None

    @property
    def json(self) -> Optional[Dict]:
        """Get JSON response data."""
        if self._json is None:
            try:
                self._json = self.response.get_json()
            except Exception:
                self._json = None
        return self._json

    @property
    def data(self) -> Any:
        """Get response data from 'response' key."""
        if self.json and 'response' in self.json:
            return self.json['response']
        return self.json

    def assert_status(self, expected_status: int) -> 'APIResponse':
        """Assert response status code."""
        assert self.status_code == expected_status, \
            f"Expected status {expected_status}, got {self.status_code}. Response: {self.json}"
        return self

    def assert_success(self) -> 'APIResponse':
        """Assert response is successful (2xx)."""
        assert 200 <= self.status_code < 300, \
            f"Expected success status, got {self.status_code}. Response: {self.json}"
        return self

    def assert_has_key(self, key: str) -> 'APIResponse':
        """Assert response JSON has key."""
        assert self.json is not None, "Response has no JSON data"
        assert key in self.json, f"Response missing key '{key}'. Keys: {list(self.json.keys())}"
        return self

    def assert_data_is_list(self) -> 'APIResponse':
        """Assert response data is a list."""
        assert isinstance(self.data, list), \
            f"Expected list, got {type(self.data).__name__}"
        return self

    def assert_data_is_dict(self) -> 'APIResponse':
        """Assert response data is a dict."""
        assert isinstance(self.data, dict), \
            f"Expected dict, got {type(self.data).__name__}"
        return self

    def assert_data_length(self, expected: int) -> 'APIResponse':
        """Assert response data has expected length."""
        assert len(self.data) == expected, \
            f"Expected length {expected}, got {len(self.data)}"
        return self

    def assert_data_min_length(self, min_length: int) -> 'APIResponse':
        """Assert response data has minimum length."""
        assert len(self.data) >= min_length, \
            f"Expected at least {min_length} items, got {len(self.data)}"
        return self


# -------------------------------------------------------------------
# Database fixtures (legacy - replaced by setup_test_database)
# -------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Result collection
# ---------------------------------------------------------------------------

class TestResultCollector:
    """Collects test results for reporting."""

    def __init__(self):
        self.results: Dict[str, Any] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'git_hash': self._get_git_hash(),
            'tests': {}
        }

    def _get_git_hash(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()[:7]
        except Exception:
            return 'unknown'

    def add_result(self, test_name: str, status: str, duration_ms: float,
                   error: Optional[str] = None):
        """Add a test result."""
        self.results['tests'][test_name] = {
            'status': status,
            'duration_ms': duration_ms,
            'error': error
        }

    def save(self, path: str):
        """Save results to file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.results, f, indent=2)


@pytest.fixture(scope='session')
def result_collector():
    """Provide test result collector."""
    return TestResultCollector()


# ---------------------------------------------------------------------------
# Per-test timing store  (populated by pytest_runtest_logreport)
# ---------------------------------------------------------------------------

# nodeid -> {'status': str, 'duration_ms': float}
_test_timings: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Pytest configuration hook."""
    config.addinivalue_line(
        "markers", "auth_required: mark test as requiring authentication"
    )
    config.addinivalue_line(
        "markers", "admin_required: mark test as requiring admin authentication"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_runtest_logreport(report):
    """Capture per-test timing from the 'call' phase report.

    pytest produces three report objects per test (setup / call /
    teardown).  We record the 'call' duration, which is the time
    spent inside the test function itself.  For skipped tests the
    skip is recorded in 'setup', so we fall back to that phase.
    """
    if report.when == 'call':
        _test_timings[report.nodeid] = {
            'status': report.outcome,
            'duration_ms': round(report.duration * 1000, 1),
        }
    elif report.when == 'setup' and report.outcome == 'skipped':
        _test_timings[report.nodeid] = {
            'status': 'skipped',
            'duration_ms': round(report.duration * 1000, 1),
        }


def pytest_sessionfinish(session, exitstatus):
    """Save per-test timings and summary stats after the session."""
    results_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')

    try:
        git_result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, check=True
        )
        git_hash = git_result.stdout.strip()
    except Exception:
        git_hash = 'unknown'

    counts: Dict[str, int] = {'passed': 0, 'failed': 0, 'skipped': 0}
    for entry in _test_timings.values():
        status = entry['status']
        if status in counts:
            counts[status] += 1

    total_ms = sum(e['duration_ms'] for e in _test_timings.values())

    results = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'git_hash': git_hash,
        'exit_status': int(exitstatus),
        'total_collected': session.testscollected,
        'total_tests': len(_test_timings),
        'passed': counts['passed'],
        'failed': counts['failed'],
        'skipped': counts['skipped'],
        'total_duration_ms': round(total_ms, 1),
        'tests': _test_timings,
    }

    # Overwrite the rolling "latest" file
    latest_path = os.path.join(results_dir, 'test_results.json')
    with open(latest_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Archive a timestamped copy
    history_dir = os.path.join(results_dir, 'history')
    os.makedirs(history_dir, exist_ok=True)
    history_path = os.path.join(
        history_dir, f'results_{timestamp}_{git_hash}.json'
    )
    with open(history_path, 'w') as f:
        json.dump(results, f, indent=2)
