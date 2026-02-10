# SuomiSF API Comprehensive Test Plan

## Overview

This document outlines the complete test strategy for the SuomiSF API. The primary goal is to create a comprehensive test suite that validates API behavior before and after migrating from SQLAlchemy to a more performant database layer.

**Created:** 2026-02-10
**Project:** SuomiSF - Finnish Science Fiction Bibliography API
**Framework:** Flask 2.3.2 with SQLAlchemy 1.4.48
**Database:** PostgreSQL (production), SQLite (development)

---

## Table of Contents

1. [Implementation Phases](#implementation-phases)
2. [Test Database Management](#test-database-management)
3. [API Endpoint Coverage](#api-endpoint-coverage)
4. [Performance Benchmarking](#performance-benchmarking)
5. [Directory Structure](#directory-structure)
6. [Tools Required](#tools-required)

---

## Implementation Phases

### Phase 1: Infrastructure Setup
- [ ] Create test configuration class (`TestConfig`)
- [ ] Set up pytest fixtures for database management
- [ ] Create golden database dump/restore scripts
- [ ] Set up `conftest.py` with shared fixtures

### Phase 2: API Test Framework
- [ ] Create base test client class with authentication support
- [ ] Create response validation helpers
- [ ] Create test result storage system (JSON/SQLite)
- [ ] Generate API endpoint coverage markdown

### Phase 3: Public Endpoint Tests
- [ ] Implement tests for all GET endpoints (no auth required)
- [ ] Implement tests for all search endpoints
- [ ] Implement tests for all filter endpoints
- [ ] Implement tests for statistics endpoints

### Phase 4: Authenticated Endpoint Tests
- [ ] Implement authentication flow tests
- [ ] Implement admin CRUD operation tests
- [ ] Implement user-specific endpoint tests

### Phase 5: Performance Benchmarking Tool
- [ ] Create standalone benchmark runner
- [ ] Implement result storage with git hash tracking
- [ ] Create performance comparison reports
- [ ] Add regression detection

---

## Test Database Management

### Golden Database Setup

The golden database serves as a consistent baseline for all tests.

#### Scripts to Create

**`tests/scripts/create_golden_db.sh`**
```bash
#!/bin/bash
# Creates a golden database dump from the current production/staging database
# Usage: ./create_golden_db.sh <source_db_url> <dump_file>

SOURCE_DB=${1:-$DATABASE_URL}
DUMP_FILE=${2:-"tests/fixtures/golden_db.sql"}

pg_dump --clean --if-exists --no-owner --no-privileges \
    -f "$DUMP_FILE" "$SOURCE_DB"

echo "Golden database created: $DUMP_FILE"
```

**`tests/scripts/restore_test_db.sh`**
```bash
#!/bin/bash
# Restores the test database from golden dump
# Usage: ./restore_test_db.sh <test_db_url> <dump_file>

TEST_DB=${1:-$TEST_DATABASE_URL}
DUMP_FILE=${2:-"tests/fixtures/golden_db.sql"}

psql "$TEST_DB" -f "$DUMP_FILE"

echo "Test database restored from: $DUMP_FILE"
```

#### Python Database Manager

Create `tests/db_manager.py`:
- `create_test_database()` - Create empty test database
- `restore_from_golden()` - Restore from golden dump
- `reset_database()` - Drop and recreate from golden
- `get_test_connection()` - Get connection to test database

### Test Configuration

Add to `app/config.py`:
```python
class TestConfig(Config):
    """Testing configuration class."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'postgresql://test_user:test_pass@localhost:5432/suomisf_test'
    WTF_CSRF_ENABLED = False
    JWT_SECRET_KEY = 'test-jwt-secret-key'
```

---

## API Endpoint Coverage

### Coverage Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Test passing |
| ❌ | Test failing |
| ⏳ | Test pending (not implemented) |
| 🚧 | Test in progress |

---

### 1. Authentication Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| POST | `/api/login` | None | ⏳ | `test_auth.py` |
| POST | `/api/register` | None | ⏳ | `test_auth.py` |
| POST | `/api/refresh` | JWT | ⏳ | `test_auth.py` |

### 2. Users Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/users` | None | ⏳ | `test_users.py` |
| GET | `/api/users/<userid>` | None | ⏳ | `test_users.py` |
| GET | `/api/users/<userid>/stats/genres` | None | ⏳ | `test_users.py` |

### 3. Works Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/works/<workid>` | None | ⏳ | `test_works.py` |
| POST | `/api/works` | Admin | ⏳ | `test_works.py` |
| PUT | `/api/works` | Admin | ⏳ | `test_works.py` |
| DELETE | `/api/works/<workid>` | Admin | ⏳ | `test_works.py` |
| GET | `/api/latest/works/<count>` | None | ⏳ | `test_works.py` |
| GET | `/api/works/<workid>/awards` | None | ⏳ | `test_works.py` |
| GET | `/api/works/<workid>/omnibus` | None | ⏳ | `test_works.py` |
| POST | `/api/works/omnibus` | Admin | ⏳ | `test_works.py` |
| GET | `/api/works/shorts/<workid>` | None | ⏳ | `test_works.py` |
| POST | `/api/works/shorts` | Admin | ⏳ | `test_works.py` |
| PUT | `/api/works/shorts` | Admin | ⏳ | `test_works.py` |
| GET | `/api/worksbyinitial/<letter>` | None | ⏳ | `test_works.py` |
| GET | `/api/worksbyauthor/<authorid>` | None | ⏳ | `test_works.py` |
| POST | `/api/searchworks` | None | ⏳ | `test_works.py` |
| POST | `/api/works/random/incomplete` | None | ⏳ | `test_works.py` |
| GET | `/api/works/bytype/<worktype>` | None | ⏳ | `test_works.py` |
| PUT | `/api/work/<workid>/tags/<tagid>` | Admin | ⏳ | `test_works.py` |
| DELETE | `/api/work/<workid>/tags/<tagid>` | Admin | ⏳ | `test_works.py` |
| GET | `/api/worktypes` | None | ⏳ | `test_works.py` |

### 4. Editions Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/editions/<editionid>` | None | ⏳ | `test_editions.py` |
| POST | `/api/editions` | Admin | ⏳ | `test_editions.py` |
| PUT | `/api/editions` | Admin | ⏳ | `test_editions.py` |
| DELETE | `/api/editions/<editionid>` | Admin | ⏳ | `test_editions.py` |
| POST | `/api/editions/<editionid>/copy` | Admin | ⏳ | `test_editions.py` |
| POST | `/api/editions/<editionid>/images` | Admin | ⏳ | `test_editions.py` |
| DELETE | `/api/editions/<editionid>/images/<imageid>` | Admin | ⏳ | `test_editions.py` |
| GET | `/api/editions/<edition_id>/changes` | None | ⏳ | `test_editions.py` |
| GET | `/api/editions/<editionid>/owners` | None | ⏳ | `test_editions.py` |
| GET | `/api/editions/<editionid>/owner/<personid>` | None | ⏳ | `test_editions.py` |
| GET | `/api/editions/owned/<userid>` | None | ⏳ | `test_editions.py` |
| DELETE | `/api/editions/<editionid>/owner/<personid>` | JWT | ⏳ | `test_editions.py` |
| POST | `/api/editions/owner` | JWT | ⏳ | `test_editions.py` |
| PUT | `/api/editions/owner` | JWT | ⏳ | `test_editions.py` |
| GET | `/api/editions/<editionid>/shorts` | None | ⏳ | `test_editions.py` |
| GET | `/api/latest/editions/<count>` | None | ⏳ | `test_editions.py` |
| GET | `/api/editions/<edition_id>/work` | None | ⏳ | `test_editions.py` |
| GET | `/api/editions/<editionid>/wishlist` | None | ⏳ | `test_editions.py` |
| PUT | `/api/editions/<editionid>/wishlist/<userid>` | JWT | ⏳ | `test_editions.py` |
| DELETE | `/api/editions/<editionid>/wishlist/<userid>` | JWT | ⏳ | `test_editions.py` |
| GET | `/api/editions/<editionid>/wishlist/<userid>` | None | ⏳ | `test_editions.py` |
| GET | `/api/editions/wishlist/<userid>` | None | ⏳ | `test_editions.py` |

### 5. People Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/people/` | None | ⏳ | `test_people.py` |
| POST | `/api/people` | Admin | ⏳ | `test_people.py` |
| PUT | `/api/people` | Admin | ⏳ | `test_people.py` |
| GET | `/api/people/<person_id>` | None | ⏳ | `test_people.py` |
| DELETE | `/api/people/<person_id>` | Admin | ⏳ | `test_people.py` |
| GET | `/api/people/<person_id>/articles` | None | ⏳ | `test_people.py` |
| GET | `/api/people/<person_id>/awarded` | None | ⏳ | `test_people.py` |
| GET | `/api/people/<personid>/chiefeditor` | None | ⏳ | `test_people.py` |
| GET | `/api/people/<personid>/shorts` | None | ⏳ | `test_people.py` |
| PUT | `/api/person/<personid>/tags/<tagid>` | Admin | ⏳ | `test_people.py` |
| DELETE | `/api/person/<personid>/tags/<tagid>` | Admin | ⏳ | `test_people.py` |
| GET | `/api/filter/people/<pattern>` | None | ⏳ | `test_people.py` |
| GET | `/api/latest/people/<count>` | None | ⏳ | `test_people.py` |
| GET | `/api/people/<person_id>/issue-contributions` | None | ⏳ | `test_people.py` |
| GET | `/api/filter/alias/<id>` | None | ⏳ | `test_people.py` |

### 6. Short Stories Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/shorts/<shortid>` | None | ⏳ | `test_shorts.py` |
| POST | `/api/shorts` | Admin | ⏳ | `test_shorts.py` |
| PUT | `/api/shorts` | Admin | ⏳ | `test_shorts.py` |
| DELETE | `/api/shorts/<shortid>` | Admin | ⏳ | `test_shorts.py` |
| POST | `/api/searchshorts` | None | ⏳ | `test_shorts.py` |
| GET | `/api/shorttypes` | None | ⏳ | `test_shorts.py` |
| PUT | `/api/story/<storyid>/tags/<tagid>` | Admin | ⏳ | `test_shorts.py` |
| DELETE | `/api/story/<storyid>/tags/<tagid>` | Admin | ⏳ | `test_shorts.py` |
| GET | `/api/latest/shorts/<count>` | None | ⏳ | `test_shorts.py` |
| GET | `/api/shorts/<shortid>/similar` | None | ⏳ | `test_shorts.py` |

### 7. Magazines & Issues Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/magazines` | None | ⏳ | `test_magazines.py` |
| GET | `/api/magazines/<magazineid>` | None | ⏳ | `test_magazines.py` |
| POST | `/api/magazines` | Admin | ⏳ | `test_magazines.py` |
| PUT | `/api/magazines` | Admin | ⏳ | `test_magazines.py` |
| DELETE | `/api/magazines/<magazineid>` | Admin | ⏳ | `test_magazines.py` |
| GET | `/api/magazinetypes` | None | ⏳ | `test_magazines.py` |
| GET | `/api/issues/<issueid>` | None | ⏳ | `test_issues.py` |
| POST | `/api/issues` | Admin | ⏳ | `test_issues.py` |
| PUT | `/api/issues` | Admin | ⏳ | `test_issues.py` |
| GET | `/api/issues/<issueid>/articles` | None | ⏳ | `test_issues.py` |
| GET | `/api/issues/<issueid>/shorts` | None | ⏳ | `test_issues.py` |
| GET | `/api/issues/<issueid>/contributors` | None | ⏳ | `test_issues.py` |
| GET | `/api/issues/<issueid>/images` | None | ⏳ | `test_issues.py` |

### 8. Awards Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/awards` | None | ⏳ | `test_awards.py` |
| GET | `/api/awards/<award_id>` | None | ⏳ | `test_awards.py` |
| GET | `/api/works/<work_id>/awarded` | None | ⏳ | `test_awards.py` |
| GET | `/api/people/<person_id>/awarded` | None | ⏳ | `test_awards.py` |
| GET | `/api/shorts/<short_id>/awarded` | None | ⏳ | `test_awards.py` |
| PUT | `/api/awards/works/awards` | Admin | ⏳ | `test_awards.py` |
| PUT | `/api/awards/people/awards` | Admin | ⏳ | `test_awards.py` |
| GET | `/api/awards/type/<award_type>` | None | ⏳ | `test_awards.py` |
| GET | `/api/awards/categories/<award_type>` | None | ⏳ | `test_awards.py` |
| GET | `/api/awards/categories/<award_id>` | None | ⏳ | `test_awards.py` |
| GET | `/api/awards/filter/<filter>` | None | ⏳ | `test_awards.py` |
| POST | `/api/awarded` | Admin | ⏳ | `test_awards.py` |

### 9. Tags Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/tags` | None | ⏳ | `test_tags.py` |
| GET | `/api/tagsquick` | None | ⏳ | `test_tags.py` |
| POST | `/api/tags` | Admin | ⏳ | `test_tags.py` |
| GET | `/api/tags/<tag_id>` | None | ⏳ | `test_tags.py` |
| GET | `/api/tags/form/<tag_id>` | None | ⏳ | `test_tags.py` |
| PUT | `/api/tags` | Admin | ⏳ | `test_tags.py` |
| GET | `/api/filter/tags/<pattern>` | None | ⏳ | `test_tags.py` |
| POST | `/api/tags/<source_id>/merge/<target_id>` | Admin | ⏳ | `test_tags.py` |
| DELETE | `/api/tags/<tagid>` | Admin | ⏳ | `test_tags.py` |
| GET | `/api/tags/types` | None | ⏳ | `test_tags.py` |

### 10. Publishers & Series Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/publishers` | None | ⏳ | `test_publishers.py` |
| GET | `/api/publishers/<publisherid>` | None | ⏳ | `test_publishers.py` |
| POST | `/api/publishers` | Admin | ⏳ | `test_publishers.py` |
| PUT | `/api/publishers` | Admin | ⏳ | `test_publishers.py` |
| DELETE | `/api/publishers/<publisherid>` | Admin | ⏳ | `test_publishers.py` |
| GET | `/api/filter/publishers/<pattern>` | None | ⏳ | `test_publishers.py` |
| GET | `/api/pubseries` | None | ⏳ | `test_pubseries.py` |
| GET | `/api/pubseries/<pubseriesid>` | None | ⏳ | `test_pubseries.py` |
| POST | `/api/pubseries` | Admin | ⏳ | `test_pubseries.py` |
| PUT | `/api/pubseries` | Admin | ⏳ | `test_pubseries.py` |
| DELETE | `/api/pubseries/<pubseriesid>` | Admin | ⏳ | `test_pubseries.py` |
| GET | `/api/filter/pubseries/<pattern>` | None | ⏳ | `test_pubseries.py` |
| GET | `/api/bookseries` | None | ⏳ | `test_bookseries.py` |
| GET | `/api/bookseries/<bookseriesid>` | None | ⏳ | `test_bookseries.py` |
| POST | `/api/bookseries` | Admin | ⏳ | `test_bookseries.py` |
| PUT | `/api/bookseries` | Admin | ⏳ | `test_bookseries.py` |
| DELETE | `/api/bookseries/<bookseriesid>` | Admin | ⏳ | `test_bookseries.py` |
| GET | `/api/filter/bookseries/<pattern>` | None | ⏳ | `test_bookseries.py` |

### 11. Statistics Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/stats/genrecounts` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/personcounts` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/storypersoncounts` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/publishercounts` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/worksbyyear` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/origworksbyyear` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/storiesbyyear` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/issuesperyear` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/nationalitycounts` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/storynationalitycounts` | None | ⏳ | `test_stats.py` |
| POST | `/api/stats/filterstories` | None | ⏳ | `test_stats.py` |
| POST | `/api/stats/filterworks` | None | ⏳ | `test_stats.py` |
| GET | `/api/stats/misc` | None | ⏳ | `test_stats.py` |

### 12. Search & Filter Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/search/<pattern>` | None | ⏳ | `test_search.py` |
| POST | `/api/search/<pattern>` | None | ⏳ | `test_search.py` |
| GET | `/api/filter/languages/<pattern>` | None | ⏳ | `test_filters.py` |
| GET | `/api/filter/linknames/<pattern>` | None | ⏳ | `test_filters.py` |
| GET | `/api/filter/countries/<pattern>` | None | ⏳ | `test_filters.py` |

### 13. Miscellaneous Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/frontpagedata` | None | ⏳ | `test_misc.py` |
| GET | `/api/genres` | None | ⏳ | `test_misc.py` |
| GET | `/api/countries` | None | ⏳ | `test_misc.py` |
| GET | `/api/roles/` | None | ⏳ | `test_misc.py` |
| GET | `/api/roles/<target>` | None | ⏳ | `test_misc.py` |
| GET | `/api/bindings` | None | ⏳ | `test_misc.py` |
| GET | `/api/firstlettervector/<target>` | None | ⏳ | `test_misc.py` |
| GET | `/api/latest/covers/<count>` | None | ⏳ | `test_misc.py` |
| GET | `/api/changes` | None | ⏳ | `test_changes.py` |
| GET | `/api/work/<workid>/changes` | None | ⏳ | `test_changes.py` |
| GET | `/api/person/<personid>/changes` | None | ⏳ | `test_changes.py` |
| DELETE | `/api/changes/<changeid>` | Admin | ⏳ | `test_changes.py` |

### 14. Articles Endpoints

| Method | Endpoint | Auth | Status | Test File |
|--------|----------|------|--------|-----------|
| GET | `/api/articles/<articleid>` | None | ⏳ | `test_articles.py` |
| GET | `/api/articles/<articleid>/tags` | None | ⏳ | `test_articles.py` |
| PUT | `/api/articles/<articleid>/tags/<tagid>` | Admin | ⏳ | `test_articles.py` |
| DELETE | `/api/articles/<articleid>/tags/<tagid>` | Admin | ⏳ | `test_articles.py` |

---

## Performance Benchmarking

### Benchmark Tool Design

Create `tests/benchmark/benchmark_runner.py`:

```python
"""
SuomiSF API Performance Benchmark Tool

Standalone tool to measure and track API performance.
Run after tests pass and changes are committed.

Usage:
    python -m tests.benchmark.benchmark_runner [--endpoints FILE] [--iterations N]
"""
```

### Key Features

1. **Endpoint Timing**
   - Measure response time for each endpoint
   - Run multiple iterations (default: 10)
   - Calculate min, max, avg, p95, p99 times

2. **Result Storage**
   - Store results in `tests/benchmark/results/`
   - JSON format with git hash, timestamp, and metrics
   - Filename: `benchmark_<git_hash>_<timestamp>.json`

3. **Comparison Reports**
   - Compare current run against baseline
   - Highlight regressions (>10% slower)
   - Highlight improvements (>10% faster)

4. **Best Results Tracking**
   - Maintain `tests/benchmark/best_results.json`
   - Update when new bests are achieved
   - Track git hash for each best result

### Result Storage Format

**`tests/benchmark/results/benchmark_<hash>_<timestamp>.json`**
```json
{
  "git_hash": "abc123def",
  "git_branch": "feature/new-db",
  "timestamp": "2026-02-10T14:30:00Z",
  "test_database": "suomisf_test",
  "iterations": 10,
  "endpoints": {
    "GET /api/works/1": {
      "min_ms": 12.5,
      "max_ms": 45.2,
      "avg_ms": 18.3,
      "p95_ms": 35.1,
      "p99_ms": 42.8,
      "iterations": 10,
      "errors": 0
    }
  }
}
```

**`tests/benchmark/best_results.json`**
```json
{
  "GET /api/works/1": {
    "best_avg_ms": 15.2,
    "git_hash": "abc123def",
    "timestamp": "2026-02-10T14:30:00Z"
  }
}
```

### Benchmark Workflow

```bash
# 1. Ensure tests pass
pytest tests/

# 2. Commit changes
git add . && git commit -m "Implement new query optimization"

# 3. Run benchmarks
python -m tests.benchmark.benchmark_runner

# 4. View comparison report
python -m tests.benchmark.compare_results --baseline HEAD~1
```

---

## Directory Structure

```
tests/
├── TEST_PLAN.md                    # This document
├── conftest.py                     # Pytest fixtures and configuration
├── pytest.ini                      # Pytest configuration
├── requirements-test.txt           # Test dependencies
│
├── fixtures/
│   ├── golden_db.sql               # Golden database dump
│   ├── test_data.json              # Additional test fixtures
│   └── auth_fixtures.py            # Authentication test data
│
├── scripts/
│   ├── create_golden_db.sh         # Create golden DB dump
│   ├── restore_test_db.sh          # Restore test DB
│   └── setup_test_env.sh           # Full test environment setup
│
├── api/
│   ├── __init__.py
│   ├── base_test.py                # Base test class with helpers
│   ├── test_auth.py                # Authentication tests
│   ├── test_users.py               # User endpoint tests
│   ├── test_works.py               # Works endpoint tests
│   ├── test_editions.py            # Editions endpoint tests
│   ├── test_people.py              # People endpoint tests
│   ├── test_shorts.py              # Short stories endpoint tests
│   ├── test_magazines.py           # Magazines endpoint tests
│   ├── test_issues.py              # Issues endpoint tests
│   ├── test_awards.py              # Awards endpoint tests
│   ├── test_tags.py                # Tags endpoint tests
│   ├── test_publishers.py          # Publishers endpoint tests
│   ├── test_pubseries.py           # Publication series tests
│   ├── test_bookseries.py          # Book series tests
│   ├── test_stats.py               # Statistics endpoint tests
│   ├── test_search.py              # Search endpoint tests
│   ├── test_filters.py             # Filter endpoint tests
│   ├── test_misc.py                # Miscellaneous endpoint tests
│   ├── test_changes.py             # Change log endpoint tests
│   └── test_articles.py            # Articles endpoint tests
│
├── results/
│   ├── test_results.json           # Latest test results
│   └── history/                    # Historical test results
│       └── results_<timestamp>.json
│
├── benchmark/
│   ├── __init__.py
│   ├── benchmark_runner.py         # Main benchmark tool
│   ├── compare_results.py          # Comparison tool
│   ├── best_results.json           # Best performance records
│   └── results/                    # Benchmark results
│       └── benchmark_<hash>_<ts>.json
│
└── db_manager.py                   # Database management utilities
```

---

## Tools Required

### Python Packages

Add to `pyproject.toml` or create `tests/requirements-test.txt`:

```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-xdist>=3.3.0        # Parallel test execution
pytest-timeout>=2.1.0      # Test timeouts
pytest-json-report>=1.5.0  # JSON test reports
requests>=2.31.0           # HTTP client
factory-boy>=3.3.0         # Test fixtures
freezegun>=1.2.0           # Time mocking
responses>=0.23.0          # HTTP mocking (optional)
```

### System Requirements

- PostgreSQL 14+ (for test database)
- Python 3.12+
- Git (for hash tracking in benchmarks)

### Environment Variables

```bash
# Test database connection
TEST_DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/suomisf_test

# Test admin credentials (for authenticated tests)
TEST_ADMIN_USERNAME=testadmin
TEST_ADMIN_PASSWORD=testpass123

# Test user credentials
TEST_USER_USERNAME=testuser
TEST_USER_PASSWORD=userpass123

# Benchmark configuration
BENCHMARK_ITERATIONS=10
BENCHMARK_WARMUP=2
```

---

## Running Tests

### Full Test Suite
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run in parallel
pytest tests/ -n auto

# Run specific test file
pytest tests/api/test_works.py

# Run tests matching pattern
pytest tests/ -k "test_get"
```

### Generate Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
```

### Run Benchmarks
```bash
# Run full benchmark suite
python -m tests.benchmark.benchmark_runner

# Compare with previous commit
python -m tests.benchmark.compare_results --baseline HEAD~1

# Compare specific hashes
python -m tests.benchmark.compare_results --baseline abc123 --current def456
```

---

## Test Result Storage

### Test Results Format

**`tests/results/test_results.json`**
```json
{
  "timestamp": "2026-02-10T14:30:00Z",
  "git_hash": "abc123def",
  "total_tests": 150,
  "passed": 148,
  "failed": 2,
  "skipped": 0,
  "duration_seconds": 45.2,
  "coverage_percent": 85.3,
  "tests": {
    "test_works.py::test_get_work_by_id": {
      "status": "passed",
      "duration_ms": 125
    },
    "test_works.py::test_create_work_admin": {
      "status": "failed",
      "duration_ms": 89,
      "error": "AssertionError: Expected 201, got 403"
    }
  }
}
```

---

## Coverage Summary

| Category | Total Endpoints | Tested | Pending |
|----------|-----------------|--------|---------|
| Authentication | 3 | 0 | 3 |
| Users | 3 | 0 | 3 |
| Works | 19 | 0 | 19 |
| Editions | 22 | 0 | 22 |
| People | 15 | 0 | 15 |
| Shorts | 10 | 0 | 10 |
| Magazines | 6 | 0 | 6 |
| Issues | 6 | 0 | 6 |
| Awards | 12 | 0 | 12 |
| Tags | 10 | 0 | 10 |
| Publishers & Series | 18 | 0 | 18 |
| Statistics | 13 | 0 | 13 |
| Search & Filter | 5 | 0 | 5 |
| Miscellaneous | 12 | 0 | 12 |
| Articles | 4 | 0 | 4 |
| **TOTAL** | **158** | **0** | **158** |

---

## Next Steps

1. **Phase 1**: Set up test infrastructure (config, fixtures, db manager)
2. **Phase 2**: Implement base test class and helpers
3. **Phase 3**: Implement public GET endpoint tests (easiest, no auth)
4. **Phase 4**: Implement search and filter tests
5. **Phase 5**: Implement authenticated endpoint tests
6. **Phase 6**: Implement benchmark tool
7. **Phase 7**: CI/CD integration

---

## Notes

- All test results should be gitignored except for documentation
- Golden database should be versioned and updated when schema changes
- Benchmark baselines should be established before starting migration work
- Consider running benchmarks on consistent hardware for reliable comparisons
