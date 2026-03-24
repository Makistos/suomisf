# Changelog

_This list is abbreviated. The project has 1217 commits in total;
268 were made in the two-year period covered here, combined into
~40 significant changes. Internal refactoring, snapshot updates,
cover image saves, and dependency bumps are omitted or grouped._

## 2026-03-23 — Migration 007: merge log tables
**Commit:** `768213c0`
Move `public."Log"` rows into `suomisf.log`. Fix ORM to target the
new table and replace raw SQL in `get_changes` with ORM filters.

## 2026-03-22 — Fix token refresh losing admin claims
**Commit:** `f4eafb85`
Token refresh was dropping admin claims after the first refresh cycle.
Fixed claims propagation through the refresh path.

## 2026-03-19 — Add GET /api/me endpoint
**Commit:** `942f459c`
New endpoint returning the current user's name and admin status.

## 2026-03-16 — JWT auth rewrite: claims-based admin, refresh without DB
**Commit:** `1178b6d9`
Admin check moved to JWT claims instead of DB lookup. Token refresh no
longer requires a DB round-trip. Debug logging added.

## 2026-03-16 — Person links: replace duplicate URL instead of rejecting
**Commit:** `339de077`
`person_link_add` now replaces an existing link that shares the same
description rather than returning an error.

## 2026-03-15 — Wikimedia image search with face detection
**Commit:** `438b5975`
Automated image finder using Wikimedia: QID resolution, face
deduplication, name matching, and auto-selection when a QID is saved.

## 2026-03-14 — Person QID field and image upload endpoint
**Commit:** `755a0002`
Added `Person.qid` (TEXT), `PersonImage` table, and
`POST /api/person/<id>/images`. Accepts QID in image upload. Existing
image is replaced on upload.

## 2026-03-03 — Database documentation and ER diagrams
**Commit:** `c37ca129`
Added `docs/` with full database documentation and ER diagrams.

## 2026-03-02 — Migration 005: drop Part and Contributor tables
**Commit:** `96941b40`
Completed schema migration: removed legacy `Part` and `Contributor`
tables. All contributor data now lives in `WorkContributor`,
`EditionContributor`, and `StoryContributor`. Fixed `Person.roles`
to include contributions from alias persons.

## 2026-03-02 — Migration 004: Edition.work_id direct FK
**Commit:** `d82e8477`
Replaced the `Part`-mediated Work↔Edition link with a direct
`Edition.work_id` foreign key. Eight orphan editions (no Part row)
retain `NULL` work_id.

## 2026-03-01 — Migration 003: WorkContributor table
**Commit:** `c39fb966`
Moved work contributors out of the legacy `Contributor` table into the
new `WorkContributor` table with explicit role tracking.

## 2026-03-01 — Migration 002: EditionContributor table
**Commit:** `748aa3d7`
Moved edition contributors to a dedicated `EditionContributor` table.

## 2026-02-28 — Fix Work.stories ordering
**Commit:** `bdb2540c`
Stories within a work were not returned in the correct order. Added
order-preservation test.

## 2026-02-26 — Migration 001 Phase 3+4: ShortStory refactoring complete
**Commit:** `f72d7723`
Completed migration of the work-to-short-story path to use the new
`EditionShortStory` and `StoryContributor` tables. Added
`work_shortstory` database VIEW.

## 2026-02-23 — Remove legacy Jinja2 routes and templates
**Commit:** `12dc962a`
Deleted all remaining server-side rendered routes and template files.
The application is now fully API-only.

## 2026-02-22 — Comprehensive API test suite with snapshot testing
**Commit:** `274101e9`
Added parameterized tests, snapshot comparison tests, auth/auth tests,
CRUD lifecycle tests, and per-test timing tooling. Test DB setup
automated (clone + migrate + seed before each run).

## 2026-02-17 — Expand test coverage across all endpoint groups
**Commit:** `9525f8bb`
Added tests for person, short story, award, tag, work, edition (CRUD,
copy, extras), magazine, issue, publisher, pubseries, and bookseries
endpoints. Fixed issue-tags parameter name mismatch and null-check
for missing short story.

## 2026-02-08 — Statistics endpoints: stories by year, nationality counts
**Commit:** `b0c12eadb`
Added `storiesbyyear`, `storypersoncounts`, `storynationalitycounts`,
and `nationalitycounts` endpoints with genre/storytype and role
breakdowns.

## 2026-02-07 — Generalise personcounts endpoint
**Commit:** `613e0bcc`
Refactored `personcounts` to accept arbitrary grouping; fixed
nationality calculation bugs.

## 2026-01-28 — First version of stats functions
**Commit:** `2b7ae9d6`
Initial `worksbyyear` and related stats queries. Fixed first-edition
selection bug and `worksbyyear` query bug.

## 2026-01-25 — Works-by-type endpoint and person "appears in"
**Commit:** `c529dbfa`
Added `GET /api/works/bytype`. Person's works list now includes
"appears in" anthology entries. Fixed missing contributor
`appears_in` info.

## 2025-04-06 — Fix missing language info on works
**Commit:** `047e9ff4`
Language field was absent from work responses in some query paths.

## 2025-04-04 — Fix story reordering losing contributors
**Commit:** `2781c46c`
Changing story order within a work was silently dropping contributor
rows. Converted commits to flushes in story-saving logic.

## 2025-04-02 — Tag form-data endpoint
**Commit:** `19af5984`
New route exposing tag form data for the frontend editor.

## 2025-03-31 — Tag description field and award updates
**Commit:** `c05d02a2`
Added `description` column to the `tag` table. Minor award-handling
fixes.

## 2025-02-23 — User registration
**Commit:** `4dbba767`
Added user self-registration endpoint and supporting logic.

## 2025-02-16 — Optimise tags page query
**Commit:** `f88e1180`
Replaced slow per-row queries on the tags list page with a single
aggregated query.

## 2024-12-17 — Fix adding new countries and languages
**Commit:** `12880f47`
Creating a new country or language record failed silently; fixed.

## 2024-12-08 — Wishlist feature
**Commit:** `d7c09765`
Users can add editions to a personal wishlist. Wishlist and owned-book
fields added to the person-page edition list.

## 2024-11-24 — Issue content API
**Commit:** `219faea6`
Added API endpoints for managing magazine issue content (stories,
articles, and their contributors).

## 2024-10-15 — Issue administration functions
**Commit:** `157c6f60`
CRUD functions for magazine issue management, including cover image
upload.

## 2024-09-22 — Edition ownership
**Commit:** `31fcf0c0`
Users can mark editions as owned. Added `GET /api/owned` and related
queries; fixed collection-ownership edge cases.

## 2024-08-18 — Switch dependency management to PDM
**Commit:** `8fdaac38`
Replaced the legacy requirements file with PDM for reproducible
dependency resolution.

## 2024-08-06 — Publisher list sorted by name
**Commit:** `ed9315a3`
Publisher listing endpoint now returns results ordered by name.

## 2024-07-31 — GET /api/editions/<id> endpoint
**Commit:** `1d8e7b40`
Added missing endpoint for fetching a single edition by ID.

## 2024-07-13 — Case-insensitive search order fix
**Commit:** `230c6961`
Search results were mis-ordered when the query contained uppercase
letters.

## 2024-06-12 — Fix person creation: links and new-person-in-work form
**Commit:** `af80b1dd`
Links were dropped when saving a new person. Creating a person
directly from the new-work form also failed; both fixed.

## 2024-05-30 — Fix tag creation during work save
**Commit:** `36d6e97e`
New tags entered on the work form were not persisted. Added TagType
table and type defaulting.

## 2024-05-05 — Rename JWT "user" claim to "name"
**Commit:** `59b8ba4a`
JWT payload field renamed from `user` to `name` for clarity. Token
refresh updated to match.

## 2024-04-28 — Changes API improvements
**Commit:** `10464676`
Extended the changes/log API: richer payloads, logging fixes for work
tags, and language/publisher field handling.

## 2024-04-01 — ShortStory language field
**Commit:** `485b737c`
Language was missing from all ShortStory model schemas; added.

## 2024-03-26 — Dependency security updates
**Commit:** `50fab04de5`
Bulk upgrade of `cryptography`, `werkzeug`, `jinja2`, `flask`,
`gunicorn`, `uwsgi`, `urllib3`, and related packages to address
published CVEs.
