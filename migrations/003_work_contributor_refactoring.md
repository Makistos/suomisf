# Migration 003: WorkContributor Refactoring

**Migration ID:** 003
**Created:** 2026-03-01
**Status:** Phase 4 pending

---

## Table of Contents

1. [Schema Change Overview](#schema-change-overview)
2. [New Table Structure](#new-table-structure)
3. [Phase 1: SQL Migration](#phase-1-sql-migration)
4. [Phase 2: ORM Changes](#phase-2-orm-changes)
5. [Phase 3: API Changes](#phase-3-api-changes)
6. [Phase 4: Cleanup](#phase-4-cleanup)
7. [Tests Required](#tests-required)
8. [Files Requiring Changes](#files-requiring-changes)
9. [Risks and Mitigations](#risks-and-mitigations)

---

## Schema Change Overview

Work contributors (author, editor, appears-in) are currently stored
in the generic `contributor` table via the `part` table as
intermediary:

```
Work → Part (work_id) → Contributor (part_id)
```

This is the same indirect path that short story and edition
contributors used before Migrations 001 and 002. The goal is a
dedicated `workcontributor` table linking contributors directly to
works.

### Current Model

```
Work.authors       → Part → Contributor (role_id=1)
Work.contributions → Part → Contributor (role_id in 1,3,6)
```

The Part indirection causes a real problem: a work with multiple
editions produces duplicate rows in `Contributor`, requiring manual
deduplication in `get_work()`.

**Roles migrated:**

| ID | Finnish | English |
|----|---------|---------|
| 1 | Kirjoittaja | Author |
| 3 | Toimittaja | Editor |
| 6 | Esiintyy | Subject/Appears In |

**Roles staying in contributor table (edition-level):**

| ID | Finnish | English |
|----|---------|---------|
| 2 | Kääntäjä | Translator |
| 3 | Toimittaja | Editor (edition) |
| 4 | Kansikuva | Cover Artist |
| 5 | Kuvittaja | Illustrator |
| 7 | Päätoimittaja | Chief Editor |

### Proposed Model

```
Work → WorkContributor (work_id) [roles 1,3,6]
Work.authors       → Person via WorkContributor (role_id=1)
Work.contributions → WorkContributor (all work roles)
```

This follows the same pattern as:
- `IssueContributor` (existing, no Part indirection)
- `StoryContributor` (created by Migration 001)
- `EditionContributor` (created by Migration 002)

---

## New Table Structure

```sql
CREATE TABLE suomisf.workcontributor (
    work_id        INTEGER NOT NULL REFERENCES work(id),
    person_id      INTEGER NOT NULL REFERENCES person(id),
    role_id        INTEGER NOT NULL REFERENCES contributorrole(id),
    real_person_id INTEGER REFERENCES person(id),
    description    VARCHAR(50),
    PRIMARY KEY (work_id, person_id, role_id)
);
```

The primary key `(work_id, person_id, role_id)` expresses that a
person holds at most one instance of a given role per work.
`real_person_id` supports pseudonym tracking (same as
`StoryContributor` and `EditionContributor`).

---

## Phase 1: SQL Migration

Script: `migrations/003_work_contributor_migration.sql`

Steps:
1. Create `suomisf.workcontributor` table with indexes
2. Populate from existing `contributor` + `part` data (7,605 rows)
3. Grant SELECT/INSERT/UPDATE/DELETE to application user

The INSERT uses `DISTINCT` and `ON CONFLICT DO NOTHING` to handle
works with multiple editions safely (same person+role in different
Parts of the same work collapses to one row).

**Apply order:**
```
python tests/scripts/setup_test_db.py
psql -d suomisf_test -f migrations/001_shortstory_migration.sql
psql -d suomisf_test -f migrations/002_edition_contributor_migration.sql
psql -d suomisf_test -f migrations/003_work_contributor_migration.sql
```

---

## Phase 2: ORM Changes

File: `app/orm_decl.py`

### New Class

Add `WorkContributor` after `EditionContributor` (before
`ContributorRole`):

```python
class WorkContributor(Base):
    """ Dedicated contributor table for works. """
    __tablename__ = 'workcontributor'
    __table_args__ = {'schema': 'suomisf'}
    work_id = Column(
        Integer, ForeignKey('work.id'),
        nullable=False, primary_key=True)
    person_id = Column(
        Integer, ForeignKey('person.id'),
        nullable=False, primary_key=True)
    role_id = Column(
        Integer, ForeignKey('contributorrole.id'),
        nullable=False, primary_key=True)
    real_person_id = Column(Integer, ForeignKey('person.id'))
    description = Column(String(50))
    person = relationship('Person', foreign_keys=[person_id])
    role = relationship('ContributorRole', viewonly=True)
    real_person = relationship(
        'Person', foreign_keys=[real_person_id])
```

### Updated Work Relationships

Replace the Part-joined `authors` and `contributions` relationships
on the `Work` class:

```python
# authors: returns Person objects (backward compatible)
authors = relationship(
    'Person',
    secondary='suomisf.workcontributor',
    primaryjoin='and_(Work.id == WorkContributor.work_id,'
                ' WorkContributor.role_id == 1)',
    secondaryjoin='Person.id == WorkContributor.person_id',
    foreign_keys='[WorkContributor.work_id,'
                 ' WorkContributor.person_id,'
                 ' WorkContributor.role_id]',
    viewonly=True)

# contributions: returns WorkContributor objects
contributions = relationship(
    'WorkContributor',
    primaryjoin='WorkContributor.work_id == Work.id',
    foreign_keys='WorkContributor.work_id',
    viewonly=True, uselist=True)
```

### Updated Person Relationships

Replace Part-joined `works` and `work_contributions` on `Person`:

```python
works = relationship(
    'Work',
    secondary='suomisf.workcontributor',
    primaryjoin='Person.id == WorkContributor.person_id',
    secondaryjoin='Work.id == WorkContributor.work_id',
    foreign_keys='[WorkContributor.person_id,'
                 ' WorkContributor.work_id,'
                 ' WorkContributor.role_id]',
    order_by='Work.title',
    uselist=True, viewonly=True)
```

**Note:** When using a schema-qualified secondary table, the
`foreign_keys` parameter (listing all PK columns of the secondary)
is required to avoid SQLAlchemy "Could not locate FK columns for
secondary join" errors. The `foreign()` annotation alone is
insufficient.

---

## Phase 3: API Changes

### impl_contributors.py

**`_WORK_ROLES`** — constant for work-specific role IDs:

```python
_WORK_ROLES = frozenset({
    ContributorType.AUTHOR.value,    # 1
    ContributorType.EDITOR.value,    # 3
    ContributorType.SUBJECT.value,   # 6
})
```

**`update_work_contributors()`** — rewrite to use `WorkContributor`
instead of `Contributor` via Part. New logic:

1. Filter input to work roles only (1, 3, 6)
2. Delete existing `WorkContributor` rows for the work
3. Insert new `WorkContributor` rows

**`get_work_contributors()`** — rewrite to query `WorkContributor`
directly, eliminating the dedup loop.

**`_update_part_contributors()`** — remove the WORK branch after
cleanup phase is complete.

### impl_works.py

**`get_work()`** — remove the manual deduplication loop for
`work.contributions` (previously needed because
`Part → Contributor` produced duplicate rows for works with multiple
editions). Replace with a simple sort:

```python
work.contributions.sort(key=lambda x: x.role.id)
```

**`work_delete()`** — add `WorkContributor` cleanup before deleting
the work row to avoid FK violations:

```python
session.query(WorkContributor)\
    .filter(WorkContributor.work_id == work_id)\
    .delete()
```

### model.py

Update `WorkContributorSchema` to use `WorkContributor` ORM model:

```python
class WorkContributorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = WorkContributor
        exclude = ('work_id',)
    person = fields.Nested(
        PersonBriefSchema(only=('id', 'name', 'alt_name')))
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(
        lambda: PersonBriefSchema(only=('id', 'name')))
```

Update `WorkSchema.contributions` to use `WorkContributorSchema`
instead of `ContributorSchema`.

**Note:** `Meta.exclude = ('work_id',)` is required to prevent the
FK column from appearing in JSON output (same pattern as
`EditionContributorSchema`).

---

## Phase 4: Cleanup

After all tests pass:

1. Run the cleanup SQL (uncomment Phase 4 block in migration SQL)
   to remove work-role rows from `contributor` table:
   ```sql
   DELETE FROM contributor
   WHERE part_id IN (
       SELECT p.id FROM part p
       WHERE p.work_id IS NOT NULL
         AND p.shortstory_id IS NULL
   )
   AND role_id IN (1, 3, 6);
   ```
2. Remove WORK branch from `_update_part_contributors()`
3. Re-run full test suite to confirm no regressions

---

## Tests Required

New test file: `tests/api/test_work_contributors.py`

| Test | Description |
|------|-------------|
| `test_work_contributor_author` | Work with author (role 1) in workcontributor |
| `test_work_contributor_editor` | Work with editor (role 3) |
| `test_work_contributor_subject` | Work with appears-in (role 6) |
| `test_work_contributor_in_response` | GET /api/works/{id} includes contributions with correct fields |
| `test_work_contributor_update_replaces` | PUT replaces all existing work contributors |
| `test_work_contributor_description_stored` | Description field stored and returned |
| `test_work_no_duplicate_contributors` | No duplicate rows even for multi-edition works |
| `test_author_in_workcontributor` | Author (role 1) stored in workcontributor table directly |
| `test_migration_count_matches` | workcontributor row count >= source distinct (work,person,role) tuples |

---

## Files Requiring Changes

### Migration Layer

| File | Change |
|------|--------|
| `migrations/003_work_contributor_migration.sql` | New: create table, populate, grant |

### ORM Layer

| File | Change |
|------|--------|
| `app/orm_decl.py` | Add `WorkContributor` class; update `Work` and `Person` relationships |

### Implementation Layer

| File | Functions Affected |
|------|-------------------|
| `app/impl_contributors.py` | `update_work_contributors()`, `get_work_contributors()`, `_update_part_contributors()` |
| `app/impl_works.py` | `get_work()` (remove dedup), `work_delete()` (add WC cleanup) |

### Schema Layer

| File | Change |
|------|--------|
| `app/model.py` | Update `WorkContributorSchema`; update `WorkSchema.contributions` |

### Test Layer

| File | Change |
|------|--------|
| `tests/api/test_work_contributors.py` | New file (9 tests) |
| `tests/conftest.py` | Apply migration 003 in `clone_test_database()` |
| `tests/TEST_DOCUMENTATION.md` | Document new tests |
| `tests/API_COVERAGE.md` | Update coverage matrix |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | `ON CONFLICT DO NOTHING`; cleanup SQL commented out until verified |
| API breaking changes | `authors` keeps returning `Person` objects; `contributions` shape unchanged |
| Multi-edition duplicate rows | `DISTINCT` in INSERT collapses same person+role from different Parts |
| Partial migration | Transaction wrapping in SQL; rollback by dropping the table |
| SQLAlchemy secondary join errors | Use `foreign_keys` param (not `foreign()` annotation) for schema-qualified secondary tables |

---

## Success Criteria

1. All existing 614 tests pass (plus 2 skipped)
2. New work contributor tests pass (9 tests, 623 total)
3. API response format for works unchanged
4. `workcontributor` row count matches source contributor data
5. `get_work()` returns no duplicate contributions
6. Snapshots not updated until migration fully complete
