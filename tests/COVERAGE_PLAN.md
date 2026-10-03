# Backend test quality and coverage plan

Written 2026-10-03. Tick items off here as they land; keep the numbers in
"Baseline" unchanged so progress stays comparable.

## Baseline (2026-10-03, master at `c6556e22`)

- 927 tests (813 test functions plus parametrized cases), all passing.
- Line coverage 49.7 % (12,363 statements, 5,698 never run); measured with
  `pdm run pytest tests -m "not network" --cov=app --cov-branch`.
- Run time about 7.5 min, about 11 min with coverage on.

### How the findings were measured

- **Per-test coverage**: the suite was run with `--cov-context=test`, and
  each test's set of executed app lines was compared with every other's.
- **Static scan** of `tests/api/*.py` for repeated requests, permissive
  status assertions and tests without assertions.

## Findings

### Redundant tests

- 182 groups of tests execute exactly the same app lines; 511 tests add
  nothing to what another test in their group already runs. 783 of 917
  tests reach no line that no other test reaches.
- One request is often split into 3-4 tests: `*_returns_200` (98),
  `*_returns_list` (57), `*_has_required_fields` (24) and
  `*_matches_snapshot` (30). Where a snapshot test exists it already checks
  everything the others do.
- This costs time: the 12 slowest tests take 466 of 636 s, and several repeat
  the same slow request (`works/bytype` three times at ~32 s each,
  `searchworks[Vuosi]` twice at ~48 s each). `filterstories` with no filters
  takes 97 s alone (with coverage on), which also suggests a slow endpoint.
- Auth checks are duplicated: 57 `*_requires_auth` and 8
  `*_without_auth_fails` tests, with the same routes checked both in
  `test_auth.py` and in per-entity files. The per-route check itself is
  worth keeping: it catches a route that lost its auth decorator.

### Tests that can't catch bugs

- 45 assertions accept a 500, e.g. `status_code in [200, 400, 500]`, so they
  pass when the server crashes.
- 68 accept 200 together with an error code, so they pass whether the
  operation worked or failed.
- 5 fixtures are named `test_work`, `test_edition` etc., so they read like
  tests without assertions.

### Code that no test runs

- Users' data: read status (`work_read_set/_remove/_list`), ownership
  (`editionowner_add`), wishlist, price save/delete (`work_products_save`,
  `work_product_delete`, `antikvaari_prices_save_all`),
  `user_collection_stats`.
- Admin create/delete: `issue_add`, `issue_delete`, `publisher_add`,
  `publisher_delete`, `bookseries_create`, `edition_image_upload`,
  `save_edition_shorts`, `update_awarded`, `person_link_add`, person and
  issue tag add/remove.
- Scrapers: every price source's search and scrape function, and the award
  import parsers (`parse_award_sfadb*`, `parse_award_category`,
  `preview_import`, `save_import`).
- Public reads: `get_frontpage_random_picks`, `get_changes`, `searchscore`,
  language and country filters.
- Analytics: `api_pageview` and the location lookup.
- Dead code: about 500 lines, mostly 27 functions in `route_helpers.py` left
  from the old server-rendered site.

## Plan

### Part A - clean up the existing tests

- [x] **A1. Tighten permissive assertions** (141): each test asserts the one
  status it should get. Where the backend answers wrongly (400/500 for a
  missing record, 500 on bad input), fix the backend.
- [ ] **A2. Merge same-request tests**: one test per endpoint and parameter
  checking status, shape and snapshot together; checks that really differ
  stay as assertions inside it. Target about 250 fewer tests and 2-3 min off
  each run.
- [ ] **A3. One auth table**: a single parametrized test in `test_auth.py`,
  one row per protected route, asserting the exact status. Remove the
  duplicates from other files.
- [ ] **A4. Rename fixtures** named `test_*` to `created_work`,
  `created_edition`, ...
- [ ] **A5. Delete dead code** (~500 lines). ORM table classes stay even if
  unreferenced.

### Part B - cover the untested code

Each step on its own branch. Tests that create data remove it afterwards
(left-over rows have broken snapshot counts before).

- [ ] **B1. Users' data**: read status, ownership, wishlist, price
  save/delete, collection stats.
- [ ] **B2. Admin round trips**: create -> read -> update -> delete for
  issues, publishers, book series, edition images and shorts, awarded items,
  person links and tags.
- [ ] **B3. Scrapers from saved pages** under `tests/fixtures/html/`: one
  product and one search page per price source, plus sfadb, ISFDB and
  Wikipedia award pages. No network at test time; refreshing a saved page
  shows exactly which fields a site change broke.
- [ ] **B4. Public read paths**: front-page random picks, change log, search
  scoring, filters.
- [ ] **B5. Analytics**: pageview logging with the ip-api lookup mocked.

### Part C - keep it from sliding back

- [ ] **C1. Coverage floor**: `--cov-fail-under` in the local test command,
  raised after each step.
- [x] **C2. Assertion check**: fail the test run on `status_code in [...]`
  lists that contain 500.

## Expected result

| | Baseline | After A | After B |
|---|---|---|---|
| Tests | 927 | ~680 | ~800 |
| Run time (no coverage) | 7.5 min | ~5 min | ~6 min |
| Line coverage | 49.7 % | ~52 % | ~68 % |
| Assertions passing on a crash | 45 | 0 | 0 |

Coverage gains are estimates from the never-run lines in each area.

## Progress log

<!-- Add a line per merged step: date, step, tests, run time, coverage. -->

- 2026-10-03, security fix found while starting A1 (merged and pushed
  separately as `b65ca665`): five endpoints had their auth decorator above
  `@app.route` and were open to anyone (award saves, wishlist add/remove),
  `/api/works/shorts` had no auth, and user-data endpoints didn't check the
  user id. Guards: `test_auth_user_data.py`, `test_route_auth.py`.
- 2026-10-04, A1 + C2: every status assertion now names one status
  (`test_test_hygiene.py` fails on lists accepting 5xx or both 2xx and 4xx).
  Backend bugs the tightening exposed and fixed:
  - `POST /api/works/random/incomplete` without filters always 500
    (`SELECT DISTINCT ... ORDER BY RANDOM()`); filtered results could
    repeat a work (unused edition join).
  - `GET /api/awards/type/<type>` always 400 (parameter overwritten) and
    used the wrong schema.
  - Tag add for works, people, stories and issues: missing tag -> 500
    (foreign key); now 404. Work tag add said "Novellia ei löydy".
  - `POST /api/editions/<id>/copy`, tag merge, edition/issue image delete,
    person chief-editor: missing record -> 500/400; now 404.
  - Tests that checked nothing: `/api/collection` (route doesn't exist,
    removed); first-letter tests used invalid targets (`work`, `person`).
  - `GET /api/firstlettervector/<target>` sent JSON as `text/html`, and the
    `stories` target was never implemented (empty 200); now JSON, and only
    `works` is supported (others 400).
  - Result: 959 passed, 0 loose status assertions.
