# Changelog

_This list is abbreviated. The project has 1217 commits in total;
268 were made in the two-year period covered here, combined into
~40 significant changes. Internal refactoring, snapshot updates,
cover image saves, and dependency bumps are omitted or grouped._

## 2026-03-23 — Migration 007: merge log tables
**Commit:** `768213c0`
Move `public."Log"` rows into `suomisf.log`; fix ORM target and
replace raw SQL in `get_changes` with ORM filters.

## 2026-03-22 — Fix token refresh losing admin claims
**Commit:** `f4eafb85`
Admin claims were dropped after the first refresh cycle; fixed
claims propagation through the refresh path.

## 2026-03-19 — Add GET /api/me endpoint
**Commit:** `942f459c`
New endpoint returning the current user's name and admin status.

## 2026-03-16 — JWT auth rewrite: claims-based admin, stateless refresh
**Commit:** `1178b6d9`
Admin check moved to JWT claims; token refresh no longer requires
a DB round-trip.

## 2026-03-16 — Person links: replace duplicate instead of rejecting
**Commit:** `339de077`
`person_link_add` replaces an existing link with the same
description rather than returning an error.

## 2026-03-15 — Wikimedia image search with face detection
**Commit:** `438b5975`
Automated image finder: QID resolution, face deduplication, name
matching, and auto-selection on QID save.

## 2026-03-14 — Person QID field and image upload endpoint
**Commit:** `755a0002`
Added `Person.qid` (TEXT), `PersonImage` table, and
`POST /api/person/<id>/images`. Existing image replaced on upload.

## 2026-03-03 — Database documentation and ER diagrams
**Commit:** `c37ca129`
Added `docs/` with full database documentation and ER diagrams.

## 2026-03-02 — Migration 005: drop Part and Contributor tables
**Commit:** `96941b40`
Removed legacy `Part` and `Contributor` tables. All contributor
data now lives in `WorkContributor`, `EditionContributor`, and
`StoryContributor`. Fixed `Person.roles` to include alias persons.

## 2026-03-02 — Migration 004: Edition.work_id direct FK
**Commit:** `d82e8477`
Replaced the `Part`-mediated Work↔Edition link with a direct
`Edition.work_id` FK. Eight orphan editions retain `NULL` work_id.

## 2026-03-01 — Migration 003: WorkContributor table
**Commit:** `c39fb966`
Moved work contributors from the legacy `Contributor` table to the
new `WorkContributor` table with explicit role tracking.

## 2026-03-01 — Migration 002: EditionContributor table
**Commit:** `748aa3d7`
Moved edition contributors to a dedicated `EditionContributor` table.

## 2026-02-28 — Fix Work.stories ordering
**Commit:** `bdb2540c`
Stories within a work were not returned in the correct order.

## 2026-02-26 — Migration 001: ShortStory refactoring complete
**Commit:** `f72d7723`
Migrated the work-to-short-story path to `EditionShortStory` and
`StoryContributor`. Added `work_shortstory` database VIEW.

## 2026-02-23 — Remove legacy Jinja2 routes and templates
**Commit:** `12dc962a`
Deleted all server-side rendered routes and templates; application
is now fully API-only.

## 2026-02-22 — Comprehensive API test suite with snapshot testing
**Commit:** `274101e9`
Parameterized tests, snapshot comparison, auth tests, CRUD
lifecycle tests, and automated test DB setup.

## 2026-02-17 — Expand test coverage across all endpoint groups
**Commit:** `9525f8bb`
Tests added for person, short story, award, tag, work, edition,
magazine, issue, publisher, pubseries, and bookseries endpoints.

## 2026-02-08 — Statistics endpoints
**Commit:** `b0c12eadb`
Added `storiesbyyear`, `storypersoncounts`, `storynationalitycounts`,
and `nationalitycounts` with genre/storytype and role breakdowns.

## 2026-01-28 — First version of stats functions
**Commit:** `2b7ae9d6`
Initial `worksbyyear` and related stats queries.

## 2026-01-25 — Works-by-type endpoint and person "appears in"
**Commit:** `c529dbfa`
Added `GET /api/works/bytype`. Person's works list now includes
"appears in" anthology entries.

## 2025-04-06 — Fix missing language info on works
**Commit:** `047e9ff4`
Language field was absent from work responses in some query paths.

## 2025-04-04 — Fix story reordering losing contributors
**Commit:** `2781c46c`
Changing story order within a work was silently dropping contributor
rows.

## 2025-04-02 — Tag form-data endpoint and description field
**Commit:** `19af5984`
New route for tag form data. Added `description` column to `tag`.

## 2025-02-23 — User registration
**Commit:** `4dbba767`
Added user self-registration endpoint.

## 2025-02-16 — Optimise tags page query
**Commit:** `f88e1180`
Replaced slow per-row queries with a single aggregated query.

## 2024-12-17 — Fix adding new countries and languages
**Commit:** `12880f47`
Creating a new country or language record failed silently; fixed.

## 2024-12-08 — Wishlist and edition ownership features
**Commit:** `d7c09765`
Users can mark editions as owned or add them to a wishlist. Added
`GET /api/owned` and related queries.

## 2024-11-24 — Issue content API and administration
**Commit:** `219faea6`
CRUD endpoints for magazine issue content (stories, articles,
contributors) and cover image upload.

## 2024-08-18 — Switch dependency management to PDM
**Commit:** `8fdaac38`
Replaced the legacy requirements file with PDM.

## 2024-07-31 — GET /api/editions/<id> endpoint
**Commit:** `1d8e7b40`
Added missing endpoint for fetching a single edition by ID.

## 2024-07-13 — Case-insensitive search order fix
**Commit:** `230c6961`
Search results were mis-ordered when the query contained uppercase
letters.

## 2024-06-12 — Fix person creation bugs
**Commit:** `af80b1dd`
Links dropped when saving a new person; creating a person from the
new-work form also failed; both fixed.

## 2024-05-30 — Fix tag creation and add TagType table
**Commit:** `36d6e97e`
New tags entered on the work form were not persisted. Added
`TagType` table and type defaulting.

## 2024-05-05 — Rename JWT "user" claim to "name"
**Commit:** `59b8ba4a`
JWT payload field renamed from `user` to `name` for clarity.

## 2024-04-28 — Changes API improvements
**Commit:** `10464676`
Richer change log payloads; logging fixes for tags, language, and
publisher fields.

## 2024-04-01 — ShortStory language field
**Commit:** `485b737c`
Language was missing from all ShortStory model schemas; added.

## 2024-03-26 — Dependency security updates
**Commit:** `50fab04de5`
Bulk upgrade of `cryptography`, `werkzeug`, `jinja2`, `flask`,
`gunicorn`, `uwsgi`, and `urllib3` to address published CVEs.
