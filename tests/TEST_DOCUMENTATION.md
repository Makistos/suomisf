# SuomiSF API Test Documentation

This document provides detailed descriptions of all API tests, including
what they test, their parameter values, and expected behaviors.

**Last Updated:** 2026-02-15

---

## Table of Contents

1. [Test File Overview](#test-file-overview)
2. [Test Infrastructure](#test-infrastructure)
3. [Authentication Tests (test_auth.py)](#authentication-tests)
4. [Entity Tests (test_entities.py)](#entity-tests)
5. [Filter & Search Tests (test_filters.py)](#filter--search-tests)
6. [Related Data Tests (test_related.py)](#related-data-tests)
7. [Statistics Tests (test_stats.py)](#statistics-tests)
8. [Miscellaneous Tests (test_misc.py)](#miscellaneous-tests)
9. [Works CRUD Tests (test_works.py)](#works-crud-tests)
10. [Editions CRUD Tests (test_editions.py)](#editions-crud-tests)
11. [Work Shorts Tests (test_work_shorts.py)](#work-shorts-tests)
12. [Edition Shorts Tests (test_edition_shorts.py)](#edition-shorts-tests)
13. [Person Shorts Tests (test_person_shorts.py)](#person-shorts-tests)
14. [Person Tests (test_persons.py)](#person-tests)
15. [Short Story Tests (test_shorts.py)](#short-story-tests)

---

## Test File Overview

| File | Purpose | Test Count |
|------|---------|------------|
| test_auth.py | Authentication & authorization | 28 |
| test_entities.py | Entity CRUD read operations | 38 |
| test_filters.py | Filter & search endpoints | 22 |
| test_related.py | Related/nested data endpoints | 30 |
| test_stats.py | Statistics endpoints | 32 |
| test_misc.py | Miscellaneous endpoints | 36 |
| test_works.py | Work lifecycle CRUD | 9 |
| test_editions.py | Edition lifecycle CRUD | 12 |
| test_work_shorts.py | Work shorts (omnibus) endpoint | 4 |
| test_edition_shorts.py | Edition-short relationships | 10 |
| test_person_shorts.py | Person-short relationships | 8 |
| test_persons.py | Person endpoints (list, CRUD, related) | 26 |
| test_shorts.py | Short story endpoints (types, CRUD, related) | 34 |

---

## Test Infrastructure

### Configuration Files

- **conftest.py**: Pytest fixtures and configuration
  - `api_client`: Flask test client wrapper with auth support
  - `snapshot_manager`: Manages snapshot comparisons
  - `app`, `client`, `db_session`: Flask app fixtures

- **test_parameters.json**: Parameterized test data
  - Contains entity IDs from the database
  - Defines filter patterns and search queries
  - Includes notes describing each test case

- **base_test.py**: Base test class with assertion helpers
  - `assert_response_format()`: Validates API response structure
  - `assert_list_response()`: Validates list responses
  - `assert_dict_response()`: Validates dict responses

### Test Credentials

```python
TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'
```

---

## Authentication Tests

**File:** `tests/api/test_auth.py`

### TestAuthentication

Tests for login endpoint behavior.

| Test | Endpoint | Description |
|------|----------|-------------|
| `test_login_with_valid_credentials` | POST /api/login | Verifies login returns token for valid email/password |
| `test_login_with_invalid_credentials` | POST /api/login | Verifies 401 for wrong credentials |
| `test_login_missing_fields` | POST /api/login | Verifies error for missing email/password |

### TestWriteOperationsRequireAuth

Tests that all write operations require authentication (returns 401/403).

| Test | Endpoint | Entity |
|------|----------|--------|
| `test_create_work_requires_auth` | POST /api/works | Works |
| `test_update_work_requires_auth` | PUT /api/works | Works |
| `test_delete_work_requires_auth` | DELETE /api/works/{id} | Works |
| `test_create_edition_requires_auth` | POST /api/editions | Editions |
| `test_update_edition_requires_auth` | PUT /api/editions | Editions |
| `test_delete_edition_requires_auth` | DELETE /api/editions/{id} | Editions |
| `test_create_person_requires_auth` | POST /api/people | People |
| `test_update_person_requires_auth` | PUT /api/people | People |
| `test_delete_person_requires_auth` | DELETE /api/people/{id} | People |
| `test_create_short_requires_auth` | POST /api/shorts | Shorts |
| `test_update_short_requires_auth` | PUT /api/shorts | Shorts |
| `test_delete_short_requires_auth` | DELETE /api/shorts/{id} | Shorts |
| `test_create_tag_requires_auth` | POST /api/tags | Tags |
| `test_update_tag_requires_auth` | PUT /api/tags | Tags |
| `test_delete_tag_requires_auth` | DELETE /api/tags/{id} | Tags |
| `test_create_publisher_requires_auth` | POST /api/publishers | Publishers |
| `test_delete_publisher_requires_auth` | DELETE /api/publishers/{id} | Publishers |
| `test_create_bookseries_requires_auth` | POST /api/bookseries | Book Series |
| `test_delete_bookseries_requires_auth` | DELETE /api/bookseries/{id} | Book Series |
| `test_create_pubseries_requires_auth` | POST /api/pubseries | Pub Series |
| `test_delete_pubseries_requires_auth` | DELETE /api/pubseries/{id} | Pub Series |
| `test_create_magazine_requires_auth` | POST /api/magazines | Magazines |
| `test_delete_magazine_requires_auth` | DELETE /api/magazines/{id} | Magazines |
| `test_create_issue_requires_auth` | POST /api/issues | Issues |
| `test_delete_issue_requires_auth` | DELETE /api/issues/{id} | Issues |

### TestCollectionRequiresAuth

| Test | Endpoint | Description |
|------|----------|-------------|
| `test_get_collection_requires_auth` | GET /api/collection | Collection requires auth |
| `test_add_to_collection_requires_auth` | POST /api/editions/owner | Adding to collection requires auth |

---

## Entity Tests

**File:** `tests/api/test_entities.py`

Parameterized tests using IDs from `test_parameters.json`.

### TestWorks

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_work_returns_200` | id: 1, 4471, 4668, 67 | GET /api/works/{id} returns 200 |
| `test_get_work_has_required_fields` | id: 1, 4471, 4668, 67 | Response has id field |
| `test_get_work_matches_snapshot` | id: 1 | Compares against stored snapshot |
| `test_get_work_not_found` | id: 999999999 | Returns 404 for invalid ID |

**Parameter Details:**
- id=1: First work in database
- id=4471: "Itse jumalat" (awarded work)
- id=4668: "Kuvitettu mies" (collection)
- id=67: "Ilmojen valloittaja" (multiple editions)

### TestEditions

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_edition_returns_200` | id: 1, 6734 | GET /api/editions/{id} returns 200 |
| `test_get_edition_has_required_fields` | id: 1, 6734 | Response has id field |
| `test_get_edition_matches_snapshot` | id: 1 | Compares against stored snapshot |
| `test_get_edition_not_found` | id: 999999999 | Returns 400/404 for invalid ID |

**Parameter Details:**
- id=1: First edition, single edition for work
- id=6734: "Hobitti", 2nd edition 14th printing

### TestPeople

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_person_returns_200` | id: 1, 2820, 1826 | GET /api/people/{id} returns 200 |
| `test_get_person_has_required_fields` | id: 1, 2820, 1826 | Response has id field |
| `test_get_person_matches_snapshot` | id: 1 | Compares against stored snapshot |
| `test_get_person_not_found` | id: 999999999 | Returns 400/404 for invalid ID |

**Parameter Details:**
- id=1: Barry Unsworth (first person)
- id=2820: Ray Bradbury (prolific, awarded)
- id=1826: Jyrki Ijäs (editor, short stories, award)

### TestShorts

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_short_returns_200` | id: 1, 3561, 1009, 8596, 644 | Returns 200 |
| `test_get_short_has_required_fields` | id: 1, 3561, 1009, 8596, 644 | Has id field |
| `test_get_short_matches_snapshot` | id: 1 | Compares snapshot |
| `test_get_short_not_found` | id: 999999999 | **xfail**: API crashes |

**Parameter Details:**
- id=1: First short story
- id=3561: Verronen "Bansheen kutsu"
- id=1009: Le Guin "Jäljittäjä" (awarded)
- id=8596: Länsikunnas "Profetioita maan alta" (genre)
- id=644: Howard "Kummittelevat pylväät" (poem)

### TestMagazines

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_magazine_returns_200` | id: 12, 30 | Returns 200 |
| `test_get_magazine_has_required_fields` | id: 12, 30 | Has id field |
| `test_get_magazines_list_matches_snapshot` | - | List matches snapshot |

**Parameter Details:**
- id=12: Finncon-lehti (no issues)
- id=30: Legolas

### TestIssues

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_issue_returns_200` | id: 75 | Returns 200 |
| `test_get_issue_has_required_fields` | id: 75 | Has id field |

**Parameter Details:**
- id=75: Alienisti 1/2008

### TestAwards

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_award_returns_200` | id: 1, 2, 16 | Returns 200 |
| `test_get_award_has_required_fields` | id: 1, 2, 16 | Has id field |
| `test_get_awards_list_matches_snapshot` | - | List matches snapshot |

**Parameter Details:**
- id=1: Damon Knight (personal award)
- id=2: Hugo
- id=16: Portin novellikilpailu

### TestTags

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_tag_returns_200` | id: 554, 1040, 1995, 1347, 1631, 2388 | Returns 200 |
| `test_get_tag_has_required_fields` | Same IDs | Has id field |
| `test_get_tags_list_matches_snapshot` | - | List matches snapshot |

**Parameter Details:**
- id=554: "miekka ja magia"
- id=1040: "filosofinen"
- id=1995: "kuningaskunnat"
- id=1347: "keski-ikäiset"
- id=1631: "1950-luku"
- id=2388: "korvat"

### TestPublishers

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_publisher_returns_200` | id: 150, 446 | Returns 200 |
| `test_get_publisher_has_required_fields` | id: 150, 446 | Has id field |
| `test_get_publishers_list_matches_snapshot` | - | List matches snapshot |

**Parameter Details:**
- id=150: Kirjayhtymä (large publisher)
- id=446: Hertta-kustannus (small publisher)

### TestBookSeries

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_bookseries_returns_200` | id: 410, 519 | Returns 200 |
| `test_get_bookseries_has_required_fields` | id: 410, 519 | Has id field |
| `test_get_bookseries_list_matches_snapshot` | - | List matches snapshot |

**Parameter Details:**
- id=410: Tarzan (many books, one author)
- id=519: Hitchhiker's Guide (multiple authors)

### TestPubSeries

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_pubseries_returns_200` | id: 1, 33 | Returns 200 |
| `test_get_pubseries_has_required_fields` | id: 1, 33 | Has id field |
| `test_get_pubseries_list_matches_snapshot` | - | List matches snapshot |

**Parameter Details:**
- id=1: "10mk:n romaaneja"
- id=33: "GALAXY Scifi"

---

## Filter & Search Tests

**File:** `tests/api/test_filters.py`

### TestFilterPeople

| Test | Parameters | Description |
|------|------------|-------------|
| `test_filter_people_returns_200` | "Asi", "Lem" | Returns 200 |
| `test_filter_people_returns_list` | "Asi", "Lem" | Returns list |
| `test_filter_people_pattern_too_short` | "a" | Returns 400 (min 2 chars) |

**Parameter Details:**
- "Asi": Matches Asimov
- "Lem": Matches Lem

### TestFilterTags

| Test | Parameters | Description |
|------|------------|-------------|
| `test_filter_tags_returns_200` | "sci", "fan", "1900" | Returns 200 |
| `test_filter_tags_returns_list` | "sci", "fan", "1900" | Returns list |

**Parameter Details:**
- "sci": Science fiction
- "fan": Fantasia
- "1900": 1900-luku

### TestFilterPublishers

| Test | Parameters | Description |
|------|------------|-------------|
| `test_filter_publishers_returns_200` | "Tam", "WSO", "Ääres" | Returns 200 |
| `test_filter_publishers_returns_list` | Same | Returns list |
| `test_filter_publishers_pattern_too_short` | "a" | Returns 400 |

**Parameter Details:**
- "Tam": Tammi
- "WSO": WSOY
- "Ääres": Ääres (tests UTF-8)

### TestFilterBookSeries

| Test | Parameters | Description |
|------|------------|-------------|
| `test_filter_bookseries_returns_200` | "5. " | Returns 200 |
| `test_filter_bookseries_returns_list` | "5. " | Returns list |

**Parameter Details:**
- "5. ": Matches "5. aalto"

### TestFilterPubSeries

| Test | Parameters | Description |
|------|------------|-------------|
| `test_filter_pubseries_returns_200` | "10" | Returns 200 |
| `test_filter_pubseries_returns_list` | "10" | Returns list |

**Parameter Details:**
- "10": Matches two "10mk" series

### TestWorksByInitial

| Test | Parameters | Description |
|------|------------|-------------|
| `test_worksbyinitial_returns_200` | "A", "Z" | Returns 200 |
| `test_worksbyinitial_returns_list` | "A", "Z" | Returns list |

**Parameter Details:**
- "A": Common starting letter
- "Z": Uncommon letter

### TestSearchWorks (POST)

| Test | Parameters | Description |
|------|------------|-------------|
| `test_searchworks_returns_200` | title, author, year | Returns 200 |
| `test_searchworks_returns_list` | Same | Returns list |

**Parameter Details:**
- `{"title": "Dyyni"}`: Search by title
- `{"author": "Asimov"}`: Search by author
- `{"year": 2000}`: Search by year

### TestSearchShorts (POST)

| Test | Parameters | Description |
|------|------------|-------------|
| `test_searchshorts_returns_200` | title, author | Returns 200 |
| `test_searchshorts_returns_list` | Same | Returns list |

**Parameter Details:**
- `{"title": "Muodonmuutos"}`: Published in many books
- `{"author": "Kafka"}`: Search by author

---

## Related Data Tests

**File:** `tests/api/test_related.py`

### TestWorksByAuthor

| Test | Parameters | Description |
|------|------------|-------------|
| `test_worksbyauthor_returns_200` | 2687, 3016 | Returns 200 |
| `test_worksbyauthor_returns_list` | Same | Returns list |

**Parameter Details:**
- 2687: Isaac Asimov
- 3016: E.T.A Hoffmann

### TestWorkAwards

| Test | Parameters | Description |
|------|------------|-------------|
| `test_work_awards_returns_200` | 1125 | Returns 200 |
| `test_work_awards_returns_list` | 1125 | Returns list |

**Parameter Details:**
- 1125: "Ennen päivänlaskua ei voi" (awarded)

### TestPersonShorts

| Test | Parameters | Description |
|------|------------|-------------|
| `test_person_shorts_returns_200` | 730 | Returns 200 |
| `test_person_shorts_returns_list` | 730 | Returns list |

**Parameter Details:**
- 730: Robert Silverberg

### TestPersonAwarded

| Test | Parameters | Description |
|------|------------|-------------|
| `test_person_awarded_returns_200` | 1943 | Returns 200 |
| `test_person_awarded_returns_list` | 1943 | Returns list |

**Parameter Details:**
- 1943: Robert Heinlein

### TestEditionShorts

| Test | Parameters | Description |
|------|------------|-------------|
| `test_edition_shorts_returns_200` | 4558 | Returns 200 |
| `test_edition_shorts_returns_list` | 4558 | Returns list |

**Parameter Details:**
- 4558: "Maameren tarinoita" (anthology)

### TestIssueShorts

| Test | Parameters | Description |
|------|------------|-------------|
| `test_issue_shorts_returns_200` | 92 | Returns 200 |
| `test_issue_shorts_returns_list` | 92 | Returns list |

**Parameter Details:**
- 92: Alienisti 1/2017

### TestIssueArticles

| Test | Parameters | Description |
|------|------------|-------------|
| `test_issue_articles_returns_200` | 27 | Returns 200 |
| `test_issue_articles_returns_list` | 27 | Returns list |

**Parameter Details:**
- 27: Aikakone 3/1988

### TestLatestWorks/Editions/People/Shorts

| Test | Parameters | Description |
|------|------------|-------------|
| `test_latest_*_returns_200` | 5, 10, 50 | Returns 200 |
| `test_latest_*_returns_list` | Same | Returns list |
| `test_latest_works_respects_count` | Same | At most N items |

**Parameter Details:**
- 5: Small batch
- 10: Medium batch
- 50: Large batch

---

## Statistics Tests

**File:** `tests/api/test_stats.py`

All stats endpoints return data and are compared against snapshots.

| Test Class | Endpoint | Tests |
|------------|----------|-------|
| TestGenreCounts | /api/stats/genrecounts | 200, has data, snapshot |
| TestPersonCounts | /api/stats/personcounts | 200, list, snapshot |
| TestStoryPersonCounts | /api/stats/storypersoncounts | 200, snapshot |
| TestPublisherCounts | /api/stats/publishercounts | 200, list, snapshot |
| TestWorksByYear | /api/stats/worksbyyear | 200, list, fields, snapshot |
| TestOrigWorksByYear | /api/stats/origworksbyyear | 200, snapshot |
| TestStoriesByYear | /api/stats/storiesbyyear | 200, snapshot |
| TestIssuesPerYear | /api/stats/issuesperyear | 200, snapshot |
| TestNationalityCounts | /api/stats/nationalitycounts | 200, list, snapshot |
| TestStoryNationalityCounts | /api/stats/storynationalitycounts | 200, snapshot |
| TestFilterStories | POST /api/stats/filterstories | empty, year filter |
| TestFilterWorks | POST /api/stats/filterworks | empty filter |
| TestMiscStats | /api/stats/misc | 200, has data, snapshot |

---

## Miscellaneous Tests

**File:** `tests/api/test_misc.py`

### TestFrontpageData

| Test | Description |
|------|-------------|
| `test_get_frontpagedata_returns_200` | Returns 200 |
| `test_get_frontpagedata_has_expected_keys` | Has works, editions keys |
| `test_get_frontpagedata_structure` | Dict with expected structure |
| `test_get_frontpagedata_matches_snapshot` | Matches snapshot |

### TestGenres

| Test | Description |
|------|-------------|
| `test_get_genres_returns_200` | Returns 200 |
| `test_get_genres_returns_list` | Returns list |
| `test_get_genres_not_empty` | At least 1 item |
| `test_genres_have_required_fields` | Has id, name |
| `test_get_genres_matches_snapshot` | Matches snapshot |

### TestCountries

| Test | Description |
|------|-------------|
| `test_get_countries_returns_200` | Returns 200 |
| `test_get_countries_returns_list` | Returns list |
| `test_get_countries_not_empty` | At least 1 item |
| `test_get_countries_matches_snapshot` | Matches snapshot |

### TestRoles

| Test | Description |
|------|-------------|
| `test_get_roles_returns_200` | Returns 200 |
| `test_get_roles_returns_list` | Returns list |
| `test_get_roles_for_work` | /api/roles/work |
| `test_get_roles_for_edition` | /api/roles/edition |
| `test_get_roles_matches_snapshot` | Matches snapshot |

### TestBindings, TestWorkTypes, TestShortTypes, TestMagazineTypes

Each has: returns_200, returns_list, matches_snapshot

### TestFirstLetterVector

| Test | Description |
|------|-------------|
| `test_get_firstlettervector_work` | /api/firstlettervector/work |
| `test_get_firstlettervector_person` | /api/firstlettervector/person |

### TestLatestCovers

| Test | Parameters | Description |
|------|------------|-------------|
| `test_get_latest_covers_returns_200` | 5 | Returns 200 |
| `test_get_latest_covers_returns_list` | 5 | Returns list |
| `test_get_latest_covers_respects_count` | 3 | At most 3 items |
| `test_get_latest_covers_matches_snapshot` | 5 | Matches snapshot |

---

## Works CRUD Tests

**File:** `tests/api/test_works.py`

### Helper Functions

```python
create_test_work(admin_client, person_id, genre_id=None,
                 title='Test Work', orig_title=None, pubyear=2025)
delete_test_work(admin_client, work_id)
```

### TestWorksCRUD

| Test | Description |
|------|-------------|
| `test_work_crud_lifecycle` | Full create/read/update/delete cycle |

**Lifecycle Steps:**
1. Save initial work count
2. Create work with title, author, genre
3. Verify work created with correct data
4. Update work (title, subtitle, description, misc)
5. Verify updates applied
6. Delete work
7. Verify count restored

### TestWorksCreateValidation

| Test | Description |
|------|-------------|
| `test_create_work_without_title_fails` | Empty title returns 400 |
| `test_create_work_without_author_fails` | Empty contributions returns 400 |
| `test_create_work_without_auth_fails` | No auth returns 401/403/422 |

### TestWorksRead

| Test | Description |
|------|-------------|
| `test_get_existing_work` | Work 1 returns 200 with data |
| `test_get_nonexistent_work` | Invalid ID returns 400/404 |
| `test_get_work_has_expected_fields` | Has id, title, orig_title, pubyear, editions, contributions |

### TestWorksDelete

| Test | Description |
|------|-------------|
| `test_delete_work_without_auth_fails` | No auth returns 401/403/404/405 |
| `test_delete_nonexistent_work` | Invalid ID returns 400/404/500 |

---

## Editions CRUD Tests

**File:** `tests/api/test_editions.py`

### Helper Functions

```python
create_test_edition(admin_client, work_id, title='Test Edition',
                    pubyear=2025, editionnum=1, publisher_id=1)
update_test_edition(admin_client, edition_id, **fields)
delete_test_edition(admin_client, edition_id)
get_work_editions(admin_client, work_id)
```

### TestEditionsCRUD

| Test | Description |
|------|-------------|
| `test_edition_full_lifecycle` | Full edition CRUD with validation |

**Lifecycle Steps:**
1. Create work (auto-creates first edition)
2. Verify work has exactly 1 edition
3. Edit first edition (title, subtitle, pubyear)
4. Verify edits persisted
5. Add second edition
6. Verify work has 2 editions
7. Edit second edition (title, pages)
8. Verify edits persisted
9. Delete first edition
10. Verify work has 1 edition
11. Try to delete last edition (should fail with 400)
12. Delete work (cleanup)

### TestEditionsCreateValidation

| Test | Description |
|------|-------------|
| `test_create_edition_without_work_id_fails` | Missing work_id returns 400 |
| `test_create_edition_with_invalid_work_id_fails` | Invalid work_id returns 400 |
| `test_create_edition_without_auth_fails` | No auth returns 401/403/422 |

### TestEditionsRead

| Test | Description |
|------|-------------|
| `test_get_existing_edition` | Edition 1 returns 200 with data |
| `test_get_nonexistent_edition` | Invalid ID returns 400/404 |
| `test_get_edition_has_expected_fields` | Has id, title, pubyear, work |

### TestEditionsDelete

| Test | Description |
|------|-------------|
| `test_delete_edition_without_auth_fails` | No auth returns 401/403/404/405 |
| `test_delete_nonexistent_edition` | Invalid ID returns 400/404/500 |

### TestEditionsCopy

| Test | Description |
|------|-------------|
| `test_copy_edition_and_verify_fields` | Copy edition 86 and verify all fields |
| `test_copy_edition_without_auth_fails` | No auth returns 401/403/422 |
| `test_copy_nonexistent_edition_fails` | Invalid ID returns 400/404/500 |

**Copy Lifecycle Steps:**
1. Get edition 86 to capture original values
2. Copy edition via POST /api/editions/86/copy
3. Verify all fields were copied correctly:
   - Basic fields: title, subtitle, pubyear, editionnum, version, isbn,
     printedin, pubseriesnum, coll_info, pages, size, dustcover,
     coverimage, misc
   - Related entities: publisher, pubseries, binding, format
   - Work associations (via parts)
   - Contributions
4. Delete the copy to clean up

**Parameter Values:**
- Source edition ID: 86
- Expected response: New edition ID (different from source)

---

## Work Shorts Tests

**File:** `tests/api/test_work_shorts.py`

Tests for the `/api/works/shorts/<workid>` endpoint that retrieves short
stories contained in an omnibus or anthology work.

### TestWorkShorts

| Test | Description |
|------|-------------|
| `test_get_work_shorts_omnibus_1378` | Verify 22 shorts with correct data |
| `test_get_work_shorts_has_required_fields` | Verify required fields present |
| `test_get_work_shorts_nonexistent_work` | Handle nonexistent work ID |
| `test_get_work_shorts_work_without_shorts` | Work without shorts returns list |

**Snapshot Test Details (test_get_work_shorts_omnibus_1378):**

Uses snapshot: `work_shorts_1378.json`

- Work ID: 1378 (Finnish SF omnibus)
- Expected count: 22 short stories
- Verifies for each short:
  - ID matches snapshot
  - Title matches snapshot
  - Original title matches snapshot
  - Publication year matches snapshot
  - Story type (id and name) matches snapshot
  - Author IDs and names match snapshot

**Sample Short Stories in Work 1378:**
| ID | Title | Author(s) | Year |
|----|-------|-----------|------|
| 1805 | Napoleonin vaihtoviikot | Elo, Eija | 1983 |
| 2965 | Ran palvelija | Oja, Heikki; Ranta, Matias | 1986 |
| 3202 | Hanna | Sinisalo, Johanna | 1988 |
| 3449 | Suklaalaput | Sinisalo, Johanna | 1985 |
| 3451 | Perhosen lento | Tervonen, Ari | 1988 |

---

## Edition Shorts Tests

**File:** `tests/api/test_edition_shorts.py`

Tests for edition-to-shortstory relationships. These tests ensure API
responses remain unchanged after migration 001 (ShortStory refactoring).

### TestEditionShorts

| Test | Description |
|------|-------------|
| `test_edition_shorts_count_and_ids` | Verify 22 shorts in edition 1585 |
| `test_edition_shorts_has_required_fields` | Verify id, title, authors |
| `test_edition_shorts_author_fields` | Verify author id and name |
| `test_edition_without_shorts` | Edition 86 returns empty list |
| `test_edition_shorts_nonexistent_edition` | Handle invalid edition ID |

**Snapshot:** `edition_shorts_1585.json`
- Edition 1585: "Atoroxin perilliset" (1988)
- Expected count: 22 short stories
- Verifies IDs, titles, authors match snapshot

### TestShortEditions

| Test | Description |
|------|-------------|
| `test_short_has_editions` | Short 1805 has editions list |
| `test_short_editions_have_required_fields` | Editions have id, title |
| `test_short_authors_preserved` | Author IDs match snapshot |

**Snapshot:** `short_1805.json`
- Short 1805: "Napoleonin vaihtoviikot" by Elo, Eija (1983)
- Editions: 1585 (1988), 2820 (2013)

### TestEditionShortsBackwardCompat

| Test | Description |
|------|-------------|
| `test_edition_shorts_response_format` | Verify response structure |
| `test_short_response_format` | Verify editions list format |

**Purpose:** Ensure API clients don't break after schema migration.

---

## Person Shorts Tests

**File:** `tests/api/test_person_shorts.py`

Tests for person-to-shortstory relationships via `/api/people/{id}/shorts`.

### TestPersonShorts

| Test | Description |
|------|-------------|
| `test_person_shorts_count_and_ids` | Person 3238 has 44 shorts |
| `test_person_shorts_has_required_fields` | id, title, contributors present |
| `test_person_shorts_contributor_structure` | Contributor has person/role |
| `test_person_shorts_includes_person_as_contributor` | Person in contributors |
| `test_person_shorts_nonexistent_person` | Handle invalid person ID |
| `test_person_without_shorts` | Person without shorts returns list |

**Snapshot:** `person_shorts_3238.json`
- Person 3238: Elo, Eija (Finnish SF author)
- Expected count: 44 short stories
- Verifies IDs, titles, contributors match

### TestPersonShortsBackwardCompat

| Test | Description |
|------|-------------|
| `test_person_shorts_response_format` | Response structure valid |
| `test_person_shorts_contributor_roles` | Role assignments preserved |

**Purpose:** Ensure contributor relationships preserved after migration.

---

## Person Tests

**File:** `tests/api/test_persons.py`

Tests for person-related endpoints not covered by other test files.
Includes list, articles, chiefeditor, issue-contributions, tags, and CRUD.

### TestPersonList

| Test | Description |
|------|-------------|
| `test_list_people_returns_200` | GET /api/people/ returns 200 |
| `test_list_people_returns_paginated_data` | Response has pagination fields |
| `test_list_people_with_sort` | Sorting parameters work |
| `test_list_people_with_rows_limit` | Row limit returns data |

### TestPersonChiefEditor

| Test | Description |
|------|-------------|
| `test_chiefeditor_returns_200` | GET /api/people/{id}/chiefeditor returns 200 |
| `test_chiefeditor_returns_issue_data` | Returns issue info for chief editor |
| `test_chiefeditor_nonexistent_person` | Handle invalid person ID |
| `test_chiefeditor_person_without_issues` | Handle person not chief editor |

**Test Data:**
- Person 900: Nikkonen, Raimo (chief editor for 172 issues)

### TestPersonIssueContributions

| Test | Description |
|------|-------------|
| `test_issue_contributions_returns_200` | GET returns 200 |
| `test_issue_contributions_returns_list` | Returns list format |
| `test_issue_contributions_has_fields` | Contributions have expected fields |
| `test_issue_contributions_nonexistent_person` | Handle invalid ID |
| `test_issue_contributions_person_without_contribs` | Handle no contributions |

**Test Data:**
- Person 8: Selkala, Ulla (167 issue contributions)

### TestPersonArticles

| Test | Description |
|------|-------------|
| `test_articles_returns_200` | GET /api/people/{id}/articles returns 200 |
| `test_articles_returns_list` | Returns list format |
| `test_articles_nonexistent_person` | Handle invalid person ID |

### TestPersonTags

| Test | Description |
|------|-------------|
| `test_add_tag_requires_auth` | PUT /api/person/{id}/tags/{tagid} requires auth |
| `test_remove_tag_requires_auth` | DELETE requires authentication |
| `test_add_tag_invalid_ids` | Invalid IDs return error |
| `test_remove_tag_invalid_ids` | Invalid IDs return error |

### TestPersonCRUD

| Test | Description |
|------|-------------|
| `test_create_person` | POST /api/people creates person |
| `test_create_person_without_auth_fails` | No auth returns 401/403/422 |
| `test_update_person_without_auth_fails` | No auth returns 401/403/422 |
| `test_delete_person_without_auth_fails` | No auth returns 401/403/404/405 |
| `test_delete_nonexistent_person` | Invalid ID returns error |

**Person Create Format:**
```json
{
  "data": {
    "name": "Last, First",
    "first_name": "First",
    "last_name": "Last",
    "dob": 1990,
    "nationality": {"id": 1}
  }
}
```

### TestPersonCRUDLifecycle

| Test | Description |
|------|-------------|
| `test_person_lifecycle` | Create -> update -> delete cycle |

**Lifecycle Steps:**
1. Create person with POST /api/people
2. Verify person exists with GET /api/people/{id}
3. Update person with PUT /api/people
4. Delete person with DELETE /api/people/{id}

---

## Short Story Tests

**File:** `tests/api/test_shorts.py`

Tests for short story endpoints not covered by other test files.
Includes story types, tags, latest, similar, awarded, and CRUD.

### TestShortTypes

| Test | Description |
|------|-------------|
| `test_shorttypes_returns_200` | GET /api/shorttypes returns 200 |
| `test_shorttypes_returns_list` | Returns list format |
| `test_shorttypes_has_expected_count` | Returns 9 story types |
| `test_shorttypes_has_required_fields` | Types have id and name |
| `test_shorttypes_includes_novelli` | Includes 'Novelli' type |

### TestLatestShorts

| Test | Description |
|------|-------------|
| `test_latest_shorts_returns_200` | GET /api/latest/shorts/{count} returns 200 |
| `test_latest_shorts_returns_list` | Returns list format |
| `test_latest_shorts_respects_count` | Respects count limit |
| `test_latest_shorts_has_required_fields` | Shorts have id and title |
| `test_latest_shorts_invalid_count` | Invalid count returns error |

### TestSimilarShorts

| Test | Description |
|------|-------------|
| `test_similar_shorts_returns_200` | GET /api/shorts/{id}/similar returns 200 |
| `test_similar_shorts_returns_list` | Returns list format |
| `test_similar_shorts_nonexistent` | Handle nonexistent short |

### TestShortAwarded

| Test | Description |
|------|-------------|
| `test_short_awarded_returns_200` | GET /api/shorts/{id}/awarded returns 200 |
| `test_short_awarded_returns_list` | Returns list format |
| `test_short_awarded_has_awards` | Short 4918 has awards |
| `test_short_awarded_has_fields` | Awards have expected fields |
| `test_short_awarded_nonexistent` | Handle nonexistent short |
| `test_short_without_awards` | Handle short without awards |

**Test Data:**
- Short 4918: "Taivaan ja helvetin avoliitto" (3 awards)

### TestStoryTags

| Test | Description |
|------|-------------|
| `test_add_tag_requires_auth` | PUT /api/story/{id}/tags/{tagid} requires auth |
| `test_remove_tag_requires_auth` | DELETE requires authentication |
| `test_add_tag_invalid_ids` | Invalid IDs return error |
| `test_remove_tag_invalid_ids` | Invalid IDs return error |

### TestShortCRUD

| Test | Description |
|------|-------------|
| `test_create_short_requires_auth` | POST /api/shorts requires auth |
| `test_update_short_requires_auth` | PUT /api/shorts requires auth |
| `test_delete_short_requires_auth` | DELETE requires auth |
| `test_delete_nonexistent_short` | Invalid ID returns error |
| `test_get_short_returns_200` | GET /api/shorts/{id} returns 200 |
| `test_get_short_has_fields` | Short has id and title |
| `test_get_nonexistent_short` | Handle nonexistent short |

### TestShortCRUDLifecycle

| Test | Description |
|------|-------------|
| `test_short_lifecycle` | Create -> update -> delete cycle |

### TestSearchShorts

| Test | Description |
|------|-------------|
| `test_search_shorts_returns_200` | POST /api/searchshorts returns 200 |
| `test_search_shorts_returns_data` | Returns search results |
| `test_search_shorts_empty_query` | Handle empty query |

---

## Adding New Tests

When adding or modifying tests, update these files:

1. **tests/TEST_DOCUMENTATION.md** (this file)
   - Add test descriptions
   - Document parameter values
   - Explain expected behaviors

2. **tests/API_COVERAGE.md**
   - Update endpoint coverage status
   - Add test function references
   - Update test counts

3. **tests/fixtures/test_parameters.json**
   - Add new parameter sets for parameterized tests
   - Include descriptive notes

---

## Running Tests

```bash
# Run all API tests
pdm run pytest tests/api/ -v

# Run specific test file
pdm run pytest tests/api/test_works.py -v

# Run specific test class
pdm run pytest tests/api/test_works.py::TestWorksCRUD -v

# Run with coverage
pdm run pytest tests/api/ --cov=app --cov-report=html
```
