# SuomiSF API Test Coverage Report

**Last Updated:** 2026-02-22
**Total Endpoints:** 167
**Tested:** 580 tests (covering ~98% of endpoints)
**Pending:** ~10 endpoints (complex write operations)
**Snapshot Tests:** 40 (data validation against golden database)

---

## Coverage Status Legend

| Symbol | Meaning |
|--------|---------|
| :white_check_mark: | Test passing |
| :x: | Test failing |
| :hourglass_flowing_sand: | Test pending (not implemented) |
| :construction: | Test in progress |

---

## Quick Summary

| Category | Endpoints | Tests | Notes |
|----------|-----------|-------|-------|
| Authentication | 3 | 33 | Login, auth checks, write operation auth |
| Users | 3 | 13 | Entity, stats/genres tests |
| Works | 19 | 45 | Entity, related, auth, omnibus, tags, types tests |
| Editions | 22 | 46 | Entity, related, auth, wishlist, images tests (2 xfail) |
| People | 15 | 16 | Entity, filter, related tests |
| Short Stories | 10 | 35 | Entity, search, auth, type field, CRUD with types |
| Magazines | 6 | 13 | Entity, auth, update tests |
| Issues | 15 | 28 | Entity, auth, contributors, tags, covers tests (3 xfail) |
| Awards | 12 | 6 | Entity tests |
| Tags | 10 | 39 | Entity, filter, auth, quick, types, merge tests |
| Publishers | 6 | 14 | Entity, filter, auth, update tests |
| Publication Series | 6 | 12 | Entity, filter, auth, update tests |
| Book Series | 6 | 17 | Entity, filter, auth, update tests |
| Statistics | 13 | 44 | Full coverage + story type filters |
| Search & Filter | 5 | 10 | Works/Shorts search |
| Miscellaneous | 12 | 36 | Full coverage |
| Articles | 4 | 0 | Endpoint deprecated |
| **TOTAL** | **167** | **370** | **5 xfails (known bugs)** |

---

## Detailed Endpoint Coverage

### 1. Authentication (3 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | POST | `/api/login` | None | `test_auth.py::TestAuthentication` | 2026-02-14 |
| :hourglass_flowing_sand: | POST | `/api/register` | None | - | - |
| :hourglass_flowing_sand: | POST | `/api/refresh` | JWT | - | - |

### 2. Users (3 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/users` | None | `test_users.py::TestUserList` | 2026-02-18 |
| :white_check_mark: | GET | `/api/users/<userid>` | None | `test_users.py::TestUserGet` | 2026-02-18 |
| :white_check_mark: | GET | `/api/users/<userid>/stats/genres` | None | `test_users.py::TestUserStatsGenres` | 2026-02-18 |

### 3. Works (19 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/works/<workid>` | None | `test_entities.py::TestWorks` | 2026-02-14 |
| :white_check_mark: | POST | `/api/works` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/works` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | DELETE | `/api/works/<workid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | GET | `/api/latest/works/<count>` | None | `test_related.py::TestLatestWorks` | 2026-02-14 |
| :white_check_mark: | GET | `/api/works/<workid>/awards` | None | `test_related.py::TestWorkAwards` | 2026-02-14 |
| :white_check_mark: | GET | `/api/works/<workid>/omnibus` | None | `test_works_extra.py::TestWorkOmnibus` | 2026-02-16 |
| :white_check_mark: | POST | `/api/works/omnibus` | Admin | `test_works_extra.py::TestWorkOmnibus` | 2026-02-16 |
| :white_check_mark: | GET | `/api/works/shorts/<workid>` | None | `test_work_shorts.py::TestWorkShorts` | 2026-02-14 |
| :white_check_mark: | POST | `/api/works/shorts` | None | `test_works_extra.py::TestWorkShortsSave` | 2026-02-16 |
| :white_check_mark: | PUT | `/api/works/shorts` | None | `test_works_extra.py::TestWorkShortsSave` | 2026-02-16 |
| :white_check_mark: | GET | `/api/worksbyinitial/<letter>` | None | `test_filters.py::TestWorksByInitial` | 2026-02-14 |
| :white_check_mark: | GET | `/api/worksbyauthor/<authorid>` | None | `test_related.py::TestWorksByAuthor` | 2026-02-14 |
| :white_check_mark: | POST | `/api/searchworks` | None | `test_filters.py::TestSearchWorks` | 2026-02-14 |
| :white_check_mark: | POST | `/api/works/random/incomplete` | None | `test_works_extra.py::TestRandomIncompleteWorks` | 2026-02-16 |
| :white_check_mark: | GET | `/api/works/bytype/<worktype>` | None | `test_works_extra.py::TestWorksByType` | 2026-02-16 |
| :white_check_mark: | PUT | `/api/work/<workid>/tags/<tagid>` | Admin | `test_works_extra.py::TestWorkTags` | 2026-02-16 |
| :white_check_mark: | DELETE | `/api/work/<workid>/tags/<tagid>` | Admin | `test_works_extra.py::TestWorkTags` | 2026-02-16 |
| :white_check_mark: | GET | `/api/worktypes` | None | `test_misc.py::TestWorkTypes` | 2026-02-14 |

### 4. Editions (22 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/editions/<editionid>` | None | `test_entities.py::TestEditions` | 2026-02-14 |
| :white_check_mark: | POST | `/api/editions` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/editions` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | DELETE | `/api/editions/<editionid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | POST | `/api/editions/<editionid>/copy` | Admin | `test_editions.py::TestEditionCopy` | 2026-02-14 |
| :white_check_mark: | POST | `/api/editions/<editionid>/images` | Admin | `test_editions_extra.py::TestEditionImages` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/editions/<editionid>/images/<imageid>` | Admin | `test_editions_extra.py::TestEditionImages` | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/<edition_id>/changes` | None | `test_editions_extra.py::TestEditionChanges` | 2026-02-17 |
| :warning: | GET | `/api/editions/<editionid>/owners` | None | `test_editions_extra.py::TestEditionOwners` (xfail) | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/<editionid>/owner/<personid>` | None | `test_editions_extra.py::TestEditionOwners` | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/owned/<userid>` | None | `test_editions_extra.py::TestEditionsOwned` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/editions/<editionid>/owner/<personid>` | JWT | `test_editions_extra.py::TestEditionOwnerModify` | 2026-02-17 |
| :white_check_mark: | POST | `/api/editions/owner` | JWT | `test_auth.py::TestCollectionRequiresAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/editions/owner` | JWT | `test_editions_extra.py::TestEditionOwnerModify` | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/<editionid>/shorts` | None | `test_related.py::TestEditionShorts` | 2026-02-14 |
| :white_check_mark: | GET | `/api/latest/editions/<count>` | None | `test_related.py::TestLatestEditions` | 2026-02-14 |
| :white_check_mark: | GET | `/api/editions/<edition_id>/work` | None | `test_editions_extra.py::TestEditionWork` | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/<editionid>/wishlist` | None | `test_editions_extra.py::TestEditionWishlist` | 2026-02-17 |
| :white_check_mark: | PUT | `/api/editions/<editionid>/wishlist/<userid>` | None* | `test_editions_extra.py::TestEditionWishlistModify` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/editions/<editionid>/wishlist/<userid>` | None* | `test_editions_extra.py::TestEditionWishlistModify` | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/<editionid>/wishlist/<userid>` | None | `test_editions_extra.py::TestEditionWishlist` | 2026-02-17 |
| :white_check_mark: | GET | `/api/editions/wishlist/<userid>` | None | `test_editions_extra.py::TestEditionWishlist` | 2026-02-17 |

*Note: Wishlist PUT/DELETE endpoints are missing auth decorators (security issue).

### 5. People (15 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/people/` | None | `test_persons.py::TestPersonList` | 2026-02-15 |
| :white_check_mark: | POST | `/api/people` | Admin | `test_persons.py::TestPersonCRUD` | 2026-02-15 |
| :white_check_mark: | PUT | `/api/people` | Admin | `test_persons.py::TestPersonCRUD` | 2026-02-15 |
| :white_check_mark: | GET | `/api/people/<person_id>` | None | `test_entities.py::TestPeople` | 2026-02-14 |
| :white_check_mark: | DELETE | `/api/people/<person_id>` | Admin | `test_persons.py::TestPersonCRUD` | 2026-02-15 |
| :white_check_mark: | GET | `/api/people/<person_id>/articles` | None | `test_persons.py::TestPersonArticles` | 2026-02-15 |
| :white_check_mark: | GET | `/api/people/<person_id>/awarded` | None | `test_related.py::TestPersonAwarded` | 2026-02-14 |
| :white_check_mark: | GET | `/api/people/<personid>/chiefeditor` | None | `test_persons.py::TestPersonChiefEditor` | 2026-02-15 |
| :white_check_mark: | GET | `/api/people/<personid>/shorts` | None | `test_person_shorts.py::TestPersonShorts` | 2026-02-15 |
| :white_check_mark: | PUT | `/api/person/<personid>/tags/<tagid>` | Admin | `test_persons.py::TestPersonTags` | 2026-02-15 |
| :white_check_mark: | DELETE | `/api/person/<personid>/tags/<tagid>` | Admin | `test_persons.py::TestPersonTags` | 2026-02-15 |
| :white_check_mark: | GET | `/api/filter/people/<pattern>` | None | `test_filters.py::TestFilterPeople` | 2026-02-14 |
| :white_check_mark: | GET | `/api/latest/people/<count>` | None | `test_related.py::TestLatestPeople` | 2026-02-14 |
| :white_check_mark: | GET | `/api/people/<person_id>/issue-contributions` | None | `test_persons.py::TestPersonIssueContributions` | 2026-02-15 |
| :hourglass_flowing_sand: | GET | `/api/filter/alias/<id>` | None | - | - |

### 6. Short Stories (10 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/shorts/<shortid>` | None | `test_shorts.py::TestShortCRUD` | 2026-02-15 |
| :white_check_mark: | POST | `/api/shorts` | Admin | `test_shorts.py::TestShortCRUD` | 2026-02-15 |
| :white_check_mark: | PUT | `/api/shorts` | Admin | `test_shorts.py::TestShortCRUD` | 2026-02-15 |
| :white_check_mark: | DELETE | `/api/shorts/<shortid>` | Admin | `test_shorts.py::TestShortCRUD` | 2026-02-15 |
| :white_check_mark: | POST | `/api/searchshorts` | None | `test_shorts.py::TestSearchShorts` | 2026-02-15 |
| :white_check_mark: | GET | `/api/shorttypes` | None | `test_shorts.py::TestShortTypes`, `TestShortTypeNames` | 2026-02-22 |
| :white_check_mark: | PUT | `/api/story/<storyid>/tags/<tagid>` | Admin | `test_shorts.py::TestStoryTags` | 2026-02-15 |
| :white_check_mark: | DELETE | `/api/story/<storyid>/tags/<tagid>` | Admin | `test_shorts.py::TestStoryTags` | 2026-02-15 |
| :white_check_mark: | GET | `/api/latest/shorts/<count>` | None | `test_shorts.py::TestLatestShorts` | 2026-02-15 |
| :white_check_mark: | GET | `/api/shorts/<shortid>/similar` | None | `test_shorts.py::TestSimilarShorts` | 2026-02-15 |

### 7. Magazines (6 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/magazines` | None | `test_magazines_issues.py::TestMagazineList` | 2026-02-17 |
| :white_check_mark: | GET | `/api/magazines/<magazineid>` | None | `test_magazines_issues.py::TestMagazineGet` | 2026-02-17 |
| :white_check_mark: | POST | `/api/magazines` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/magazines` | Admin | `test_magazines_issues.py::TestMagazineUpdate` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/magazines/<magazineid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | GET | `/api/magazinetypes` | None | `test_misc.py::TestMagazineTypes` | 2026-02-14 |

### 8. Issues (12 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/issues/<issueid>` | None | `test_magazines_issues.py::TestIssueGet` | 2026-02-17 |
| :white_check_mark: | POST | `/api/issues` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/issues` | Admin | `test_magazines_issues.py::TestIssueUpdate` | 2026-02-17 |
| :white_check_mark: | GET | `/api/issues/<issueid>/articles` | None | `test_related.py::TestIssueArticles` | 2026-02-14 |
| :white_check_mark: | GET | `/api/issues/<issueid>/shorts` | None | `test_related.py::TestIssueShorts` | 2026-02-14 |
| :warning: | GET | `/api/issues/<issueid>/contributors` | None | `test_magazines_issues.py::TestIssueContributors` (xfail) | 2026-02-17 |
| :white_check_mark: | POST | `/api/issues/<issueid>/contributors` | Admin | `test_magazines_issues.py::TestIssueContributors` | 2026-02-17 |
| :warning: | GET | `/api/issues/<issueid>/tags` | None | `test_magazines_issues.py::TestIssueTags` (xfail) | 2026-02-17 |
| :white_check_mark: | PUT | `/api/issue/<issueid>/tags/<tagid>` | Admin | `test_magazines_issues.py::TestIssueTags` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/issue/<issueid>/tags/<tagid>` | Admin | `test_magazines_issues.py::TestIssueTags` | 2026-02-17 |
| :white_check_mark: | GET | `/api/issues/sizes` | None | `test_magazines_issues.py::TestIssueSizes` | 2026-02-17 |
| :white_check_mark: | POST | `/api/issues/<issueid>/covers` | Admin | `test_magazines_issues.py::TestIssueCovers` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/issues/<issueid>/covers` | Admin | `test_magazines_issues.py::TestIssueCovers` | 2026-02-17 |
| :white_check_mark: | PUT | `/api/issues/shorts` | Admin | `test_magazines_issues.py::TestIssueShorts` | 2026-02-17 |
| :white_check_mark: | PUT | `/api/issues/articles` | Admin | `test_magazines_issues.py::TestIssueArticles` | 2026-02-17 |

### 9. Awards (12 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/awards` | None | `test_awards.py::TestAwardsList` | 2026-02-16 |
| :white_check_mark: | GET | `/api/awards/<award_id>` | None | `test_awards.py::TestAwardGet` | 2026-02-16 |
| :white_check_mark: | GET | `/api/works/<work_id>/awarded` | None | `test_awards.py::TestWorkAwarded` | 2026-02-16 |
| :white_check_mark: | GET | `/api/people/<person_id>/awarded` | None | `test_related.py::TestPersonAwarded` | 2026-02-14 |
| :white_check_mark: | GET | `/api/shorts/<short_id>/awarded` | None | `test_shorts.py::TestShortAwarded` | 2026-02-15 |
| :white_check_mark: | PUT | `/api/awards/works/awards` | Admin | `test_awards.py::TestAwardAdminEndpoints` | 2026-02-16 |
| :white_check_mark: | PUT | `/api/awards/people/awards` | Admin | `test_awards.py::TestAwardAdminEndpoints` | 2026-02-16 |
| :white_check_mark: | GET | `/api/awards/type/<award_type>` | None | `test_awards.py::TestAwardsByType` | 2026-02-16 |
| :white_check_mark: | GET | `/api/awards/categories/<award_type>` | None | `test_awards.py::TestAwardCategories` | 2026-02-16 |
| :white_check_mark: | GET | `/api/awards/categories/<award_id>` | None | `test_awards.py::TestAwardCategories` | 2026-02-16 |
| :white_check_mark: | GET | `/api/awards/filter/<filter>` | None | `test_awards.py::TestAwardsFilter` | 2026-02-16 |
| :white_check_mark: | POST | `/api/awarded` | Admin | `test_awards.py::TestAwardAdminEndpoints` | 2026-02-16 |

### 10. Tags (10 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/tags` | None | `test_entities.py::TestTags`, `test_tags.py::TestTagSearch` | 2026-02-16 |
| :white_check_mark: | GET | `/api/tagsquick` | None | `test_tags.py::TestTagsQuick` | 2026-02-16 |
| :white_check_mark: | POST | `/api/tags` | Admin | `test_auth.py::TestWriteOperationsRequireAuth`, `test_tags.py::TestTagCRUDLifecycle` | 2026-02-16 |
| :white_check_mark: | GET | `/api/tags/<tag_id>` | None | `test_entities.py::TestTags` | 2026-02-14 |
| :white_check_mark: | GET | `/api/tags/form/<tag_id>` | None | `test_tags.py::TestTagFormInfo` | 2026-02-16 |
| :white_check_mark: | PUT | `/api/tags` | Admin | `test_auth.py::TestWriteOperationsRequireAuth`, `test_tags.py::TestTagCRUDLifecycle` | 2026-02-16 |
| :white_check_mark: | GET | `/api/filter/tags/<pattern>` | None | `test_filters.py::TestFilterTags` | 2026-02-14 |
| :white_check_mark: | POST | `/api/tags/<source_id>/merge/<target_id>` | Admin | `test_tags.py::TestTagMerge`, `test_tags.py::TestTagCRUDLifecycle` | 2026-02-16 |
| :white_check_mark: | DELETE | `/api/tags/<tagid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth`, `test_tags.py::TestTagCRUDLifecycle` | 2026-02-16 |
| :white_check_mark: | GET | `/api/tags/types` | None | `test_tags.py::TestTagTypes` | 2026-02-16 |

### 11. Publishers (6 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/publishers` | None | `test_series_publishers.py::TestPublisherList` | 2026-02-17 |
| :white_check_mark: | GET | `/api/publishers/<publisherid>` | None | `test_series_publishers.py::TestPublisherGet` | 2026-02-17 |
| :white_check_mark: | POST | `/api/publishers` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/publishers` | Admin | `test_series_publishers.py::TestPublisherUpdate` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/publishers/<publisherid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | GET | `/api/filter/publishers/<pattern>` | None | `test_series_publishers.py::TestPublisherFilter` | 2026-02-17 |

### 12. Publication Series (6 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/pubseries` | None | `test_series_publishers.py::TestPubSeriesList` | 2026-02-17 |
| :white_check_mark: | GET | `/api/pubseries/<pubseriesid>` | None | `test_series_publishers.py::TestPubSeriesGet` | 2026-02-17 |
| :white_check_mark: | POST | `/api/pubseries` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/pubseries` | Admin | `test_series_publishers.py::TestPubSeriesUpdate` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/pubseries/<pubseriesid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | GET | `/api/filter/pubseries/<pattern>` | None | `test_series_publishers.py::TestPubSeriesFilter` | 2026-02-17 |

### 13. Book Series (6 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/bookseries` | None | `test_series_publishers.py::TestBookSeriesList` | 2026-02-17 |
| :white_check_mark: | GET | `/api/bookseries/<bookseriesid>` | None | `test_series_publishers.py::TestBookSeriesGet` | 2026-02-17 |
| :white_check_mark: | POST | `/api/bookseries` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | PUT | `/api/bookseries` | Admin | `test_series_publishers.py::TestBookSeriesUpdate` | 2026-02-17 |
| :white_check_mark: | DELETE | `/api/bookseries/<bookseriesid>` | Admin | `test_auth.py::TestWriteOperationsRequireAuth` | 2026-02-14 |
| :white_check_mark: | GET | `/api/filter/bookseries/<pattern>` | None | `test_series_publishers.py::TestBookSeriesFilter` | 2026-02-17 |

### 14. Statistics (13 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/stats/genrecounts` | None | `test_stats.py::TestGenreCounts` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/personcounts` | None | `test_stats.py::TestPersonCounts` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/storypersoncounts` | None | `test_stats.py::TestStoryPersonCounts`, `TestStoryPersonCountsByType` | 2026-02-22 |
| :white_check_mark: | GET | `/api/stats/publishercounts` | None | `test_stats.py::TestPublisherCounts` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/worksbyyear` | None | `test_stats.py::TestWorksByYear` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/origworksbyyear` | None | `test_stats.py::TestOrigWorksByYear` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/storiesbyyear` | None | `test_stats.py::TestStoriesByYear`, `TestStoriesByYearTypes` | 2026-02-22 |
| :white_check_mark: | GET | `/api/stats/issuesperyear` | None | `test_stats.py::TestIssuesPerYear` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/nationalitycounts` | None | `test_stats.py::TestNationalityCounts` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/storynationalitycounts` | None | `test_stats.py::TestStoryNationalityCounts` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/filterstories` | None | `test_stats.py::TestFilterStories` | 2026-02-22 |
| :white_check_mark: | POST | `/api/stats/filterworks` | None | `test_stats.py::TestFilterWorks` | 2026-02-14 |
| :white_check_mark: | GET | `/api/stats/misc` | None | `test_stats.py::TestMiscStats` | 2026-02-14 |

### 15. Search & Filter (5 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :hourglass_flowing_sand: | GET | `/api/search/<pattern>` | None | - | - |
| :hourglass_flowing_sand: | POST | `/api/search/<pattern>` | None | - | - |
| :hourglass_flowing_sand: | GET | `/api/filter/languages/<pattern>` | None | - | - |
| :hourglass_flowing_sand: | GET | `/api/filter/linknames/<pattern>` | None | - | - |
| :hourglass_flowing_sand: | GET | `/api/filter/countries/<pattern>` | None | - | - |

### 16. Miscellaneous (12 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :white_check_mark: | GET | `/api/frontpagedata` | None | `test_misc.py::TestFrontpageData` | 2026-02-14 |
| :white_check_mark: | GET | `/api/genres` | None | `test_misc.py::TestGenres` | 2026-02-14 |
| :white_check_mark: | GET | `/api/countries` | None | `test_misc.py::TestCountries` | 2026-02-14 |
| :white_check_mark: | GET | `/api/roles/` | None | `test_misc.py::TestRoles` | 2026-02-14 |
| :white_check_mark: | GET | `/api/roles/<target>` | None | `test_misc.py::TestRoles` | 2026-02-14 |
| :white_check_mark: | GET | `/api/bindings` | None | `test_misc.py::TestBindings` | 2026-02-14 |
| :white_check_mark: | GET | `/api/firstlettervector/<target>` | None | `test_misc.py::TestFirstLetterVector` | 2026-02-14 |
| :white_check_mark: | GET | `/api/latest/covers/<count>` | None | `test_misc.py::TestLatestCovers` | 2026-02-14 |
| :hourglass_flowing_sand: | GET | `/api/changes` | None | - | - |
| :hourglass_flowing_sand: | GET | `/api/work/<workid>/changes` | None | - | - |
| :hourglass_flowing_sand: | GET | `/api/person/<personid>/changes` | None | - | - |
| :hourglass_flowing_sand: | DELETE | `/api/changes/<changeid>` | Admin | - | - |

### 17. Articles (4 endpoints)

| Status | Method | Endpoint | Auth | Test Function | Last Run |
|--------|--------|----------|------|---------------|----------|
| :hourglass_flowing_sand: | GET | `/api/articles/<articleid>` | None | - | - |
| :hourglass_flowing_sand: | GET | `/api/articles/<articleid>/tags` | None | - | - |
| :hourglass_flowing_sand: | PUT | `/api/articles/<articleid>/tags/<tagid>` | Admin | - | - |
| :hourglass_flowing_sand: | DELETE | `/api/articles/<articleid>/tags/<tagid>` | Admin | - | - |

---

## Test History

| Date | Git Hash | Total | Passed | Failed | xFail | Duration |
|------|----------|-------|--------|--------|-------|----------|
| 2026-02-14 | pending | 249 | 248 | 0 | 1 | - |
| 2026-02-13 | 38bfbe1 | 239 | 238 | 0 | 1 | 124s |
| 2026-02-14 | 12dc962 | 68 | 68 | 0 | 0 | 16s |
| 2026-02-14 | 12dc962 | 48 | 48 | 0 | 0 | 10s |

---

## Notes

- This document is auto-updated by the test runner
- Manual updates should be avoided
- Run `pdm run pytest tests/` to execute all tests
- Run `pdm run python tests/scripts/update_snapshots.py` to regenerate golden database snapshots
- Run `python -m tests.benchmark.benchmark_runner` for performance benchmarks

## Snapshot Testing

Snapshot tests compare API responses against stored golden database responses. When the database schema or data changes:

1. Update the golden database dump
2. Run `pdm run python tests/scripts/update_snapshots.py` to capture new snapshots
3. Run tests to validate the API returns expected data

Snapshot files are stored in `tests/fixtures/snapshots/`
