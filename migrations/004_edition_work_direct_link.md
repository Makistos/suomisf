# Migration 004: Edition–Work Direct Link

**Migration ID:** 004
**Created:** 2026-03-01
**Status:** Planning

---

## Table of Contents

1. [Schema Change Overview](#schema-change-overview)
2. [New Column](#new-column)
3. [Phase 1: SQL Migration](#phase-1-sql-migration)
4. [Phase 2: ORM Changes](#phase-2-orm-changes)
5. [Phase 3: API Changes](#phase-3-api-changes)
6. [Phase 4: Schema Changes](#phase-4-schema-changes)
7. [Phase 5: Cleanup](#phase-5-cleanup)
8. [Tests Required](#tests-required)
9. [Files Requiring Changes](#files-requiring-changes)
10. [Risks and Mitigations](#risks-and-mitigations)

---

## Schema Change Overview

The work–edition relationship is currently stored in the `part`
table as an intermediary:

```
Work ← Part (work_id + edition_id, shortstory_id IS NULL) → Edition
```

A Part row with `shortstory_id IS NULL` represents the
work–edition bond. This same Part table also links short stories
to editions (when `shortstory_id IS NOT NULL`).

### Problems with the current model

- Queries for `Work.editions` and `Edition.work` must always join
  through Part and filter `shortstory_id IS NULL`.
- `Edition.work` is modelled as a list in SQLAlchemy and in
  schemas, even though there is exactly one work per edition.
  This forces callers to index with `[0]`.
- Multiple code paths re-derive the work from an edition by
  querying Part, rather than reading a single FK column.
- There are at least 10 distinct query sites across 7 files that
  express the Part-based Work↔Edition join.

### Proposed Model

Add `work_id` directly to `edition`:

```
Work.id ← Edition.work_id
```

Part rows with `shortstory_id IS NULL` become redundant for the
work–edition link and can be removed in the cleanup phase.
Part rows with `shortstory_id IS NOT NULL` (collection items)
are unaffected.

---

## New Column

```sql
ALTER TABLE edition
    ADD COLUMN work_id INTEGER NOT NULL
    REFERENCES work(id);

CREATE INDEX idx_edition_work_id ON edition(work_id);
```

Every edition has exactly one work; `NOT NULL` is enforced.

---

## Phase 1: SQL Migration

**File:** `migrations/004_edition_work_direct_link.sql`

```sql
SET search_path TO suomisf;

-- 1. Add nullable work_id column
ALTER TABLE edition
    ADD COLUMN work_id INTEGER REFERENCES work(id);

-- 2. Populate from the Part table
--    Each edition has exactly one Part row with shortstory_id IS NULL
--    and a non-null work_id; DISTINCT covers any duplicates.
UPDATE edition e
SET work_id = (
    SELECT DISTINCT p.work_id
    FROM part p
    WHERE p.edition_id = e.id
      AND p.work_id IS NOT NULL
      AND p.shortstory_id IS NULL
    LIMIT 1
);

-- 3. Verify no editions were missed before enforcing NOT NULL
--    (Run manually if needed):
-- SELECT count(*) FROM edition WHERE work_id IS NULL;

-- 4. Enforce NOT NULL
ALTER TABLE edition
    ALTER COLUMN work_id SET NOT NULL;

-- 5. Add index
CREATE INDEX IF NOT EXISTS idx_edition_work_id
    ON edition(work_id);

-- 6. Grant privileges (column inherits table grants; explicit for
--    clarity)
GRANT SELECT, INSERT, UPDATE, DELETE ON edition TO mep;

-- ---------------------------------------------------------------
-- Phase 5 cleanup (run after all tests pass):
-- Remove the redundant work_id column from Part where
-- shortstory_id IS NULL. Part rows for short stories are kept.
-- ---------------------------------------------------------------
-- DELETE FROM part
-- WHERE shortstory_id IS NULL;
--
-- ALTER TABLE part
--     DROP COLUMN IF EXISTS work_id;
```

**Apply order:**

```
python tests/scripts/setup_test_db.py
psql -d suomisf_test -f migrations/001_shortstory_migration.sql
psql -d suomisf_test -f migrations/002_edition_contributor_migration.sql
psql -d suomisf_test -f migrations/003_work_contributor_migration.sql
psql -d suomisf_test -f migrations/004_edition_work_direct_link.sql
```

---

## Phase 2: ORM Changes

**File:** `app/orm_decl.py`

### Edition class

Add the `work_id` column and replace the Part-based `work`
relationship with a direct FK relationship (singular, not a list):

```python
# New column (add with other FK columns)
work_id = Column(
    Integer, ForeignKey('work.id'),
    nullable=False, index=True)

# Replace:
# work = relationship('Work', secondary='part',
#                     uselist=True, viewonly=True)
# With:
work = relationship('Work', foreign_keys=[work_id],
                    uselist=False, viewonly=True)
```

### Work class

Replace the Part-based `editions` relationship with a direct FK:

```python
# Replace:
# editions = relationship(
#     'Edition',
#     primaryjoin='and_(Part.work_id == Work.id, '
#                 'Part.edition_id == Edition.id, '
#                 'Part.shortstory_id == None)',
#     secondary='part', uselist=True,
#     order_by='Edition.pubyear, Edition.version,
#               Edition.editionnum',
#     viewonly=True)
# With:
editions = relationship(
    'Edition',
    primaryjoin='Edition.work_id == Work.id',
    foreign_keys='Edition.work_id',
    order_by='Edition.pubyear, Edition.version, '
             'Edition.editionnum',
    uselist=True, viewonly=True)
```

---

## Phase 3: API Changes

### app/impl_editions.py

#### `create_first_edition()`

Set `work_id` on the new edition (currently not set):

```python
def create_first_edition(work: Work) -> Edition:
    retval = Edition()
    retval.title = work.title
    retval.subtitle = work.subtitle
    retval.pubyear = work.pubyear or 0
    retval.work_id = work.id    # NEW
    retval.editionnum = 1
    retval.version = 1
    retval.binding_id = 1
    retval.dustcover = 1
    retval.coverimage = 1
    retval.format_id = 1
    return retval
```

#### `create_edition()`

After the work lookup, set `edition.work_id` directly before the
first `session.add(edition)`:

```python
edition.work_id = work_id    # NEW — add before session.add(edition)
```

The Part row creation that follows (lines 402–413) can remain for
now (Phase 5 removes it). The contributor lookup on line 417 that
uses `part.work_id` should be changed to `edition.work_id`:

```python
# Old:
contributors = get_work_contributors(session, part.work_id)
# New:
contributors = get_work_contributors(session, edition.work_id)
```

#### `copy_edition()`

Add `work_id` to the `Edition(...)` constructor:

```python
new_edition = Edition(
    title=original_edition.title,
    subtitle=original_edition.subtitle,
    work_id=original_edition.work_id,   # NEW
    pubyear=original_edition.pubyear,
    # ... rest unchanged ...
)
```

#### `get_edition_work()`

The function currently accesses `edition.work[0].id` (a list
index). Replace with the direct column:

```python
# Old:
if not edition.work[0].id:
    ...
return ResponseType(edition.work[0].id, ...)

# New:
if not edition.work_id:
    ...
return ResponseType(edition.work_id, ...)
```

#### `edition_delete()`

Replace the Part-based work_id lookup (lines 795–808) with a
direct read and direct count:

```python
# Old:
work_ids = session.query(Part.work_id)\
    .filter(Part.edition_id == int_id)\
    .filter(Part.work_id.isnot(None))\
    .distinct().all()
work_ids = [w[0] for w in work_ids]

if work_ids:
    edition_count = session.query(Edition.id)\
        .join(Part, Part.edition_id == Edition.id)\
        .filter(Part.work_id.in_(work_ids))\
        .distinct().count()

# New:
edition = session.query(Edition).filter(Edition.id == int_id)\
    .first()
work_id = edition.work_id if edition else None

if work_id:
    edition_count = session.query(Edition.id)\
        .filter(Edition.work_id == work_id)\
        .count()
```

### app/impl_works.py

#### `work_delete()`

Replace the Part-joined edition query (lines 1190–1194):

```python
# Old:
editions = session.query(Edition)\
    .join(Part)\
    .filter(Part.work_id == work_id)\
    .filter(Part.edition_id == Edition.id)\
    .all()

# New:
editions = session.query(Edition)\
    .filter(Edition.work_id == work_id)\
    .all()
```

#### `get_work_shorts()`

Replace the Part join (lines 1248–1255):

```python
# Old:
first_edition = session.query(Edition)\
    .join(Part, Part.edition_id == Edition.id)\
    .filter(Part.work_id == work_id)\
    .filter(Part.shortstory_id.is_(None))\
    .filter(Edition.editionnum == 1)\
    .filter(or_(Edition.version == 1,
                Edition.version.is_(None)))\
    .first()

# New:
first_edition = session.query(Edition)\
    .filter(Edition.work_id == work_id)\
    .filter(Edition.editionnum == 1)\
    .filter(or_(Edition.version == 1,
                Edition.version.is_(None)))\
    .first()
```

#### `save_work_shorts()`

Replace the Part-based edition ID lookup (lines 1298–1306):

```python
# Old:
work_edition_ids = [
    row[0] for row in
    session.query(Part.edition_id)
    .filter(Part.work_id == work_id)
    .filter(Part.shortstory_id.is_(None))
    .filter(Part.edition_id.isnot(None))
    .distinct().all()
]

# New:
work_edition_ids = [
    row[0] for row in
    session.query(Edition.id)
    .filter(Edition.work_id == work_id)
    .all()
]
```

#### `search_works()`

Replace the Part join used to find editions for title filtering
(lines 342–348):

```python
# Old:
works = session.query(Work)\
    .filter(...)\
    .join(Part)\
    .filter(Part.work_id == Work.id)\
    .join(Edition)\
    .filter(Edition.id == Part.edition_id)\
    .filter(Edition.title.ilike(...) |
            Edition.subtitle.ilike(...))\
    .all()

# New:
works = session.query(Work)\
    .filter(...)\
    .join(Edition, Edition.work_id == Work.id)\
    .filter(Edition.title.ilike(...) |
            Edition.subtitle.ilike(...))\
    .all()
```

#### `search_books()`

Replace the first-editions subquery (lines 434–439) that currently
groups by `Part.work_id`:

```python
# Old:
first_editions = session.query(
    Part.work_id,
    func.min(Edition.id).label('first_edition_id')
).join(Edition, Part.edition_id == Edition.id)\
 .group_by(Part.work_id).subquery()

# New:
first_editions = session.query(
    Edition.work_id,
    func.min(Edition.id).label('first_edition_id')
).group_by(Edition.work_id).subquery()
```

### app/impl_changes.py

#### `get_work_changes()`

Replace the Part filter (lines 27–30):

```python
# Old:
editions = [x[0] for x in session.query(Edition.id)
            .filter(Part.work_id == workid,
                    Part.edition_id == Edition.id)
            .all()]

# New:
editions = [x[0] for x in
            session.query(Edition.id)
            .filter(Edition.work_id == workid)
            .all()]
```

### app/impl_stats.py

Three stats queries join Work↔Edition via Part with
`shortstory_id IS NULL`. Each can be simplified:

**`stats_publishercounts` genre breakdown (lines 474–479):**

```python
# Old:
.join(Part, Part.work_id == Work.id)\
.join(Edition, Edition.id == Part.edition_id)\
.filter(Edition.publisher_id == pub_data.id,
        Part.shortstory_id.is_(None))

# New:
.join(Edition, Edition.work_id == Work.id)\
.filter(Edition.publisher_id == pub_data.id)
```

**`stats_worksbyyear` (lines 552–555):**

```python
# Old:
.outerjoin(Part, and_(Part.edition_id == Edition.id,
                      Part.shortstory_id.is_(None)))\
.outerjoin(Work, Work.id == Part.work_id)\

# New:
.outerjoin(Work, Work.id == Edition.work_id)\
```

**`filter_works` by first edition year (lines 1197–1204):**

```python
# Old:
query = session.query(Work).join(
    Part, and_(Part.work_id == Work.id,
               Part.shortstory_id.is_(None))
).join(Edition, Edition.id == Part.edition_id)\
 .filter(...)

# New:
query = session.query(Work)\
    .join(Edition, Edition.work_id == Work.id)\
    .filter(...)
```

### app/impl_editions.py (raw SQL)

The raw SQL string around line 1058 joins Part to get the work
name for the user book list:

```python
# Old:
stmt += 'JOIN part on edition.id = part.edition_id '
stmt += 'AND part.shortstory_id IS NULL '
stmt += 'JOIN work on part.work_id = work.id '

# New:
stmt += 'JOIN work ON work.id = edition.work_id '
```

### app/impl_users.py (raw SQL)

The user genre stats query around line 284 joins Part to reach
the work:

```python
# Old:
stmt += 'INNER JOIN part ON part.work_id = work.id '
stmt += 'and part.shortstory_id is null '
stmt += 'INNER JOIN edition ON edition.id = part.edition_id '

# New:
stmt += 'INNER JOIN edition ON edition.work_id = work.id '
```

### app/route_helpers.py

`editions_for_work()` (line 371) already references
`Edition.work_id` in its filter — this is dead code that
anticipates the migration. Once the column is added, the function
becomes correct. No change needed.

---

## Phase 4: Schema Changes

**File:** `app/model.py`

`Edition.work` changes from a list (secondary via Part) to a
single object (direct FK). Update all edition schemas:

### EditionBriefestSchema

```python
# Old:
work = ma.List(fields.Nested(WorkBriefestSchema))
# New:
work = fields.Nested(WorkBriefestSchema)
```

### EditionBriefSchema

```python
# Old:
work = ma.List(fields.Nested(WorkBriefSchema))
# New:
work = fields.Nested(WorkBriefSchema)
```

### EditionSchema

```python
# Old:
work = ma.List(fields.Nested(WorkBriefSchema))
# New:
work = fields.Nested(WorkBriefSchema)
```

**API response impact:** `edition.work` changes from an array to
an object. Any frontend code that accesses `edition.work[0]` must
be updated to `edition.work`.

---

## Phase 5: Cleanup

After all tests pass:

1. Uncomment the cleanup block in the migration SQL:
   ```sql
   DELETE FROM part WHERE shortstory_id IS NULL;
   ALTER TABLE part DROP COLUMN IF EXISTS work_id;
   ```
2. Remove the Part creation block from `create_edition()` (the
   loop that creates Part rows with only `work_id` set).
3. Update `copy_edition()` to skip Part rows with
   `shortstory_id IS NULL` (work-level Part rows no longer needed).
4. Remove the Part deletion in `delete_edition()` — at that point
   all remaining Part rows will have `shortstory_id IS NOT NULL`.
5. Re-run the full test suite to confirm no regressions.

---

## Tests Required

New file: `tests/api/test_edition_work_link.py`

| Test | Description |
|------|-------------|
| `test_edition_has_work_id_column` | ORM Edition class exposes `work_id` as an integer column |
| `test_no_edition_has_null_work_id` | Every edition in test DB has a non-null `work_id` |
| `test_get_edition_work_is_object` | GET /api/editions/{id} returns `work` as an object, not a list |
| `test_get_edition_work_id_matches` | `edition.work.id` matches the work the edition belongs to |
| `test_create_edition_sets_work_id` | POST /api/editions creates edition with correct `work_id` |
| `test_copy_edition_preserves_work_id` | copy_edition produces edition with same `work_id` as original |
| `test_work_delete_removes_editions` | Deleting a work also deletes its editions (via `work_id`) |
| `test_get_work_includes_editions_list` | GET /api/works/{id} returns `editions` as a list |
| `test_work_editions_ordered` | Work editions returned ordered by `pubyear, version, editionnum` |
| `test_get_work_shorts_uses_work_id` | GET /api/works/{id}/shorts returns correct shorts via `work_id` |
| `test_get_edition_work_returns_work_id` | GET /api/editions/{id}/work returns the work ID as an integer |

---

## Files Requiring Changes

### Migration Layer

| File | Change |
|------|--------|
| `migrations/004_edition_work_direct_link.sql` | New: add column, populate, NOT NULL, index |

### ORM Layer

| File | Change |
|------|--------|
| `app/orm_decl.py` | Add `work_id` FK column to Edition; change `Edition.work` to direct FK; simplify `Work.editions` |

### Implementation Layer

| File | Functions Affected |
|------|-------------------|
| `app/impl_editions.py` | `create_first_edition()`, `create_edition()`, `copy_edition()`, `get_edition_work()`, `edition_delete()`, raw SQL (user book list, ~line 1058) |
| `app/impl_works.py` | `work_delete()`, `get_work_shorts()`, `save_work_shorts()`, `search_works()`, `search_books()` |
| `app/impl_changes.py` | `get_work_changes()` |
| `app/impl_stats.py` | `stats_publishercounts` genre breakdown, `stats_worksbyyear`, `filter_works` (3 query sites) |
| `app/impl_users.py` | `user_genres()` raw SQL, user book list raw SQL |

### Schema Layer

| File | Change |
|------|--------|
| `app/model.py` | `EditionBriefestSchema.work`, `EditionBriefSchema.work`, `EditionSchema.work`: List → Nested (singular) |

### Test Layer

| File | Change |
|------|--------|
| `tests/api/test_edition_work_link.py` | New file (11 tests) |
| `tests/conftest.py` | Apply migration 004 in `clone_test_database()` |
| `tests/TEST_DOCUMENTATION.md` | Document new tests |
| `tests/API_COVERAGE.md` | Update coverage matrix |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Edition without a Part row has NULL work_id | Check `SELECT count(*) FROM edition WHERE work_id IS NULL` before enforcing NOT NULL; investigate any orphans |
| API breaking change: `edition.work` array → object | Update all callers of `edition.work[0]`; update snapshots |
| Wide code surface (10+ query sites) | Migrate Phase 3 changes incrementally; run test suite after each file |
| Part rows still created until Phase 5 | Accepted; Part rows with `shortstory_id IS NULL` remain harmlessly until cleanup |
| Raw SQL in impl_editions.py / impl_users.py | Update join clause; unit test the affected endpoint |
| Stats queries may regress | Each stats query has a snapshot; snapshot test catches regressions |

---

## Success Criteria

1. All existing 623 tests pass (plus 2 skipped)
2. All 11 new edition–work link tests pass
3. `Edition.work_id` is NOT NULL for all editions in the test DB
4. API response for `edition.work` is a single object, not an
   array
5. No query in the application code joins through Part to
   express the Work↔Edition relationship
6. Snapshots regenerated after Phase 4 schema change
