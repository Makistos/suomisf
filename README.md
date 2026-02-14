# SuomiSF

This is Flask-based collection manager for Finnish Science Fiction, Fantasy and Horror books.
Contents and database schema is based on "The Bibliography of of Finnish Sf-, Fantasy- and Horror Literature".
This is why interface is also only in Finnish. There are errors in the data as
it was impossible to import everything correctly.

There is an importer (bib_import.py) which can fill the database with the data
from the bibliography. Because it will be possible to add and edit everything
in the database it could also be possible to add books by hand in the future.

Application uses Flask framework and SQLAlchemy ORM. Bootstrap css files are
missing from this package at the moment.

## Examples on how to store books
The database has been designed in such a way it can store different kinds of
books but this might also make the structure less obvious. As the import data
includes Finnish books only (original and translations) I will use those as
examples on how to deal with some situations. This chapter talks mainly about
the trinity of Work, Edition and Part.

Work is the original work and does not really represent anything concrete.
It's the work done by one or several authors and covers every version printed.

Edition is a single edition of the book in one language. So for instance,
every edition in English has their own row in this table.

Part is whatever parts an edition and/or work contains. Short stories can be
listed as parts allowing collections where some edition is not based strictly
on some work but could be either a combination or just part of one. Sometimes
works are also split into several volumes and in some cases multiple works
are combined into one book. This table allows expressing these cases. Title is
always the name in the edition.

There must always be at least one row in each of these three tables for any
book.

1. The simple case: First edition of a book: There should be one row in each
   of Work, Edition and Part and nothing else.
2. Another edition of a book: There should be another row in Edition and Part
   but only the original row in Work.
3. A work split into multiple parts. For example Frank Herbert's Dune was
   split into three parts in Finland. This would be represented as one row in
   Work and three rows in Edition and Part.
4. Two works combined into one edition, e.g. a compendum of Shakespeare's
   plays. This should have one Work and Part row for each play and one row in
   Edition for the compendum.
5. A collection translated into another language. Edition and Work both have
   one row while every short story has a row in Part and also the ShortStory
   table. Title in the Part row has the translated name while Title in
   ShortStory holds the original name of the story.

## API Design

This is not implemented yet. Also very WIP anyways and lacks descriptions for
return values.

Strings used as search parameters are always used with ilike operator. So to
search using a part of a string, you can use the percentage sign, e.g. using
"Asimov%" as the person's full name will find all the names starting with
Asimov (case independent).

All replies are in JSON.

### Authentication

POST /api/1.0/auth

Parameters:
* *username*
* *password*

### Getting list of works

GET /api/works

Parameters:
* workid
* title
* authorid
* language

Returns works that match the search criteria which can be any of the
parameters.

### Getting list of editions

GET /api/editions

Parameters_
* workid
* editionid
* title
* authorid
* language

### Getting info for a work

GET /api/work/{workid}

#### Getting info for an edition

GET /api/edition/{editionid}

### Getting a list of persons

GET /api/persons

Parameters:
* fullname
* last_name
* first_name
* dob
* dod
* birthplace
* type (A = author, T = translator, E = editor)

### Getting info on a person

GET /api/person/{personid}

### Getting your collection

Requires authentication.

GET /api/collection

## Testing

The project includes a comprehensive API test suite with 238 tests covering 158 endpoints.

### Prerequisites

Install development dependencies:

```bash
pdm install -d
```

### Test Database Setup

Create a dedicated test database with cloned data from the main database:

```bash
pdm run python tests/scripts/setup_test_db.py --clone
```

Options:
- `--clone` - Clone data from main database (recommended for first setup)
- `--users-only` - Only create test users (skip database creation)

This script:
1. Fixes PostgreSQL collation version mismatches
2. Creates the `suomisf_test` database
3. Clones data from the main database
4. Sets up the correct schema search path
5. Creates test users (regular and admin)

### Running Tests

Run all tests:

```bash
pdm run pytest tests/
```

Run tests with verbose output:

```bash
pdm run pytest tests/ -v
```

Run specific test file:

```bash
pdm run pytest tests/api/test_stats.py -v
```

### Snapshot Testing

Snapshot tests compare API responses against stored "golden" responses from the database. This ensures API behavior remains consistent after code changes.

**Generating/Updating Snapshots:**

After database schema or data changes, regenerate the snapshots:

```bash
pdm run python tests/scripts/update_snapshots.py
```

This captures responses from all configured endpoints and stores them in `tests/fixtures/snapshots/`.

**Listing Endpoints:**

To see which endpoints are configured for snapshot testing:

```bash
pdm run python tests/scripts/update_snapshots.py --list
```

### Golden Database

The test suite uses a golden database dump for consistent test data.

**Creating a Golden Database Dump:**

```bash
bash tests/scripts/create_golden_db.sh
```

This creates a dump at `tests/fixtures/golden_db.sql`.

**Restoring the Test Database:**

```bash
bash tests/scripts/restore_test_db.sh
```

### Performance Benchmarking

Run API performance benchmarks:

```bash
pdm run python -m tests.benchmark.benchmark_runner
```

Benchmark results are stored in `tests/benchmark/results/` with git hash tracking.

### API Coverage Report

The test coverage status is tracked in `tests/API_COVERAGE.md`, which includes:

- Status of all 158 API endpoints
- Test history with git hashes
- Pass/fail statistics

### Test Directory Structure

```
tests/
├── api/                        # API endpoint tests
│   ├── base_test.py            # Base test class with helpers
│   ├── test_auth.py            # Authentication & authorization (33 tests)
│   ├── test_entities.py        # Entity CRUD endpoints
│   ├── test_filters.py         # Filter and search endpoints
│   ├── test_related.py         # Nested/related endpoints
│   ├── test_stats.py           # Statistics endpoints (32 tests)
│   └── test_misc.py            # Miscellaneous endpoints (36 tests)
├── fixtures/
│   ├── snapshots/              # API response snapshots (~35 files)
│   ├── test_params.json        # Parameterized test data
│   └── golden_db.sql           # Golden database dump
├── scripts/
│   ├── setup_test_db.py        # Test database setup (create, clone, users)
│   ├── update_snapshots.py     # Snapshot generator
│   ├── create_golden_db.sh     # DB dump script
│   └── restore_test_db.sh      # DB restore script
├── benchmark/
│   └── benchmark_runner.py     # Performance benchmarks
├── results/                    # Test run results
├── conftest.py                 # Pytest fixtures
└── API_COVERAGE.md             # Coverage tracking (238 tests, 158 endpoints)
```
