# Changelog

_This list is abbreviated. The project has 1217 commits in total;
268 were made in the two-year period covered here, combined into
~40 significant changes. Internal refactoring, snapshot updates,
cover image saves, and dependency bumps are omitted or grouped._

## 2026-10-01 — Fixes: database sessions and magazine update
**Commits:** `052b81f6`, `091560d7`
Sessions opened per request are now closed at app-context teardown,
fixing a connection leak that surfaced as intermittent 500s. Updating a
magazine with no publisher or type no longer crashes.

## 2026-09-30 — Test and lint tooling
**Commits:** `fb8c4845`…`68e94da8`
The test database clone now includes the pg_trgm extension, so
titles-only search tests run; API response snapshots refreshed. Ruff
linting added (pyproject `[tool.ruff]`) and its findings fixed.
`API_COVERAGE.md` is now generated from coverage data.

## 2026-09-26 — Titles-only search matches alternative names
**Commit:** `25bc4388`
Titles-only site search also matches a person's alt_name and other
names.

## 2026-09-24 — More award winner importers
**Commits:** `54fd15ff`…`18fb7907`
Person awards (SFWA, Skylark and World Horror Grand Master) import from
sfadb. A Wikipedia wikitable importer covers the Nobel Prize in
Literature, Finlandia, Lasten- ja nuortenkirjallisuuden Finlandia,
Topelius, Arvid Lydecken, Kuvastaja, Tähtifantasia, Tähtivaeltaja and
the Booker Prize. Atorox, Portin novellikilpailu and Kosmoskynä import
from new sources after anarres.fi went offline. Award detail responses
include the winner-import source.

## 2026-09-15 — Front page random picks
**Commit:** `01603678`
GET /api/frontpage/random returns one random work with a description
from each genre category (fantasy, sci-fi, horror, youth, children's,
collections), never repeating a work.

## 2026-09-11 — Smaller fixes and schema additions
**Commits:** `729d27f7`…`6cbd916f`
Change-log timestamps are written as timezone-aware UTC; book series
brief responses include the parent series; award winners carry the
work's language; latest editions/works eager-load their relationships.
Assigning a new book series or publisher to an existing work or
edition no longer crashes.

## 2026-09-03 — More price sources and price editing
**Commits:** `c2d79b8d`…`a8a7eccb`
Lukuhetki and Kampin kirjakauppa added as pricing sources (with
ä/ö/å-safe search), Antikvaari supports single-URL scraping, and stored
price rows can be edited. Edition owners can price their own editions;
editing and deleting a price is limited to admins and the row's adder.

## 2026-08-23 — Framework upgrades and security fixes
**Commits:** `db00ae69`…`0d44d654`
Flask 3.1, Werkzeug 3.1, SQLAlchemy 2.0 and marshmallow 4 (including a
marshmallow DoS CVE fix). Fixed an unauthenticated SQL injection in the
wishlist and user genre-stats endpoints. Unused WTForms/Flask-WTF and
the stale Dockerfile and requirements.txt removed; pinned versions and
remaining security debt documented in `SECURITY_TODO.md`.

## 2026-08-20 — Faster work listings and crash fixes
**Commits:** `cf0577d5`…`7644716f`
The large work-listing endpoint went from 11.0 s to 3.1 s for ~1200
works by restricting nested person serialization. GET /api/awards/<id>
no longer crashes on a missing award, and creating an issue with
contributors no longer crashes. E2E support: `SUOMISF_DOTENV`, a test
database setup script and a reset-token minting script.

## 2026-08-19 — Chart drill-down filters and read-based stats
**Commit:** `c45f4665`

## 2026-08-11 — Deletion and ownership fixes
**Commits:** `5c572f07`, `7ac02e5b`, `34bb0d38`
Deleting an edition or work no longer fails on foreign keys from prices,
ownership, read status, awards and links. The edition owners list
includes book condition.

## 2026-07-29 — Collection composition and per-year stats
**Commits:** `7e39c0f0`…`95ef447a`
The user collection endpoint returns composition and per-year
publication data, and stats/filterworks accepts an owner filter.

## 2026-07-28 — Search ranking and titles-only mode
**Commits:** `33274d3f`, `f2976eb5`…`f9b1424f`
Menu search shows author names and deduplicates editions. Results are
ordered by score, with person matches boosted when the name matches and
titles ranked by trigram similarity to the query. Edition and short
story results carry an author line. New `?titles=1` mode limits
matching to titles and names.

## 2026-07-27 — Pluggable price sources and sellers
**Commits:** `5af6ce8e`…`144afbe2`
A source-provider registry (`app/price_providers.py`) adds antikka.net,
antikvariaatti.net and oranssiplaneetta.fi to automatic price search.
Prices record the seller, duplicates are removed across stores and fetch
dates, and saves are serialized per edition to prevent duplicate rows.

## 2026-07-17 — Read status for works
**Commits:** `4e9e9eb5`, `7b0c7088`
Per-user read status with an opinion (userwork table, /api/works/read
endpoints). Book suggestions never include works the user disliked.

## 2026-07-10 — Award creation and winner import
**Commits:** `55a5517c`…`ea551747`
Admin endpoint for creating awards. Award winners can be imported from
ISFDB or sfadb.com (now the default), with a preview that matches each
winner to a work, story or category; category maps cover many
international awards, including Kurd Lasswitz, Imaginaire, Sidewise,
Mythopoeic, Prix Apollo, Shirley Jackson, Prometheus, Ditmar and the
Andre Norton Award.

## 2026-07-08 — Link description autocomplete
**Commit:** `f00c8266`
Suggestions are scoped to the owner type of the link.

## 2026-07-07 — User email and password reset
**Commits:** `af0d7b33`, `ddefadee`, `ca62ac95`
Users have an email address, and password-reset endpoints send a reset
link by email (SMTP setup guide added). Antikvaari listings with a
campaign tag are no longer skipped.

## 2026-07-06 — Book suggestion filters and facets in work search
**Commits:** `724a491d`…`2619ee20`
`search_books` (POST /api/searchworks) extended to power the book
suggestion wizard: tag-group filters (AND across facets, OR within a
group), original-publication decade buckets including a pre-1900 bucket,
edition page-length buckets, award-only, owned/not-owned (via user_id),
list-valued nationality, and random sampling with count and exclude.
Results carry a `has_awards` flag, and a `facets` mode returns the option
ids (with per-tag match counts) that still have matches for the current
filters, so the wizard can constrain later steps.

## 2026-06-28 — Best edition prices per work
**Commit:** `9c9a1fb9`
New endpoint returning the best edition prices for a user within a work.

## 2026-06-17 — Boost FTS ranking for work title matches
**Commit:** `538f04ea`

## 2026-06-07 — Antikvaari/Antikka price scraping and tracking
**Commits:** `d28a5f73`…`3b91f860`
Backend for fetching, storing, and matching second-hand book prices from
Antikvariaatti and Antikka: price source tracking with product page URLs,
edition matching (laitos/painos) with re-match on save, condition flags,
rejected/excluded products, close-edition price fallbacks, and a
price-range distribution in collection stats.

## 2026-05-17 — Edition short stories endpoint
**Commit:** `0f945c64`
PUT /api/editions/<id>/shorts to save the short-story contents of an
edition.

## 2026-05-16 — Visitor analytics and pageview logging
**Commits:** `a4a40659`…`5c4dd743`
Admin-only pageview logging with bot filtering, IP geolocation via
ip-api.com (cached, with operator name), and a paginated, filterable
pageview log endpoint. Routes renamed to avoid ad-blocker filter lists.

## 2026-05-11 — Multi-image support for issues
**Commit:** `3d67be02`
New `IssueImage` table and migration; magazine issues can have multiple
cover images, returned in the issue response.

## 2026-05-10 — Kirjasampo tag import
**Commits:** `76d18496`, `cba9f165`
GET /api/kirjasampo/tags scrapes tags from kirjasampo.fi; POST
/api/work/<id>/tags/import imports them with persistent skip/replace
mappings. Tags are lowercased at scrape and import time.

## 2026-05-06 — Fixes: author_str and refresh token
**Commits:** `93986b03`, `064148c8`
Fix stale `author_str` when updating work contributors; refresh token now
returns the user id as an integer instead of a string.

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
