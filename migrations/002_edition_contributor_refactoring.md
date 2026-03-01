# Migration 002: EditionContributor Refactoring

**Migration ID:** 002
**Created:** 2026-03-01
**Status:** Planning

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

Edition contributors (translator, editor, cover artist, illustrator,
chief editor) are currently stored in the generic `contributor`
table via the `part` table as intermediary:

```
Edition → Part (edition_id) → Contributor (part_id)
```

This is the same indirect path that short story contributors used
before Migration 001. The goal is a dedicated `editioncontributor`
table linking contributors directly to editions.

### Current Model

```
Edition.editors      → Part → Contributor (role_id=3)
Edition.translators  → Part → Contributor (role_id=2)
Edition.contributions→ Part → Contributor (role_id not in 1,3)
```

**Roles migrated:**

| ID | Finnish | English |
|----|---------|---------|
| 2 | Kääntäjä | Translator |
| 3 | Toimittaja | Editor |
| 4 | Kansikuva | Cover Artist |
| 5 | Kuvittaja | Illustrator |
| 7 | Päätoimittaja | Chief Editor |

**Roles staying in contributor table (work-level):**

| ID | Finnish | English |
|----|---------|---------|
| 1 | Kirjoittaja | Author |
| 6 | Esiintyy | Subject/Appears In |

### Proposed Model

```
Edition → EditionContributor (edition_id) [roles 2,3,4,5,7]
Edition.editors      → Person via EditionContributor (role_id=3)
Edition.translators  → Person via EditionContributor (role_id=2)
Edition.contributions→ EditionContributor (all edition roles)
```

This follows the same pattern as:
- `IssueContributor` (existing, no Part indirection)
- `StoryContributor` (created by Migration 001)

---

## New Table Structure

```sql
CREATE TABLE suomisf.editioncontributor (
    edition_id     INTEGER NOT NULL REFERENCES edition(id),
    person_id      INTEGER NOT NULL REFERENCES person(id),
    role_id        INTEGER NOT NULL REFERENCES contributorrole(id),
    real_person_id INTEGER REFERENCES person(id),
    description    VARCHAR(50),
    PRIMARY KEY (edition_id, person_id, role_id)
);
```

The primary key `(edition_id, person_id, role_id)` expresses that
a person holds at most one instance of a given role per edition.
`real_person_id` supports pseudonym tracking (same as StoryContributor).

---

## Phase 1: SQL Migration

Script: `migrations/002_edition_contributor_migration.sql`

Steps:
1. Create `suomisf.editioncontributor` table with indexes
2. Populate from existing `contributor` + `part` data
3. Grant SELECT/INSERT/UPDATE/DELETE to application user

The INSERT uses `DISTINCT` and `ON CONFLICT DO NOTHING` to handle
editions with multiple Parts safely (same person+role in different
Parts of the same edition collapses to one row).

**Apply order:**
```
python tests/scripts/setup_test_db.py
psql -d suomisf_test -f migrations/001_shortstory_migration.sql
psql -d suomisf_test -f migrations/002_edition_contributor_migration.sql
```

---

## Phase 2: ORM Changes

File: `app/orm_decl.py`

### New Class

Add `EditionContributor` after `StoryContributor` (before
`ContributorRole`):

```python
class EditionContributor(Base):
    """ Dedicated contributor table for editions. """
    __tablename__ = 'editioncontributor'
    __table_args__ = {'schema': 'suomisf'}
    edition_id = Column(
        Integer, ForeignKey('edition.id'),
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

### Updated Edition Relationships

Replace the Part-joined `editors`, `translators`, and `contributions`
relationships on the `Edition` class:

```python
# editors: returns Person objects (backward compatible)
editors = relationship(
    'Person',
    secondary='suomisf.editioncontributor',
    primaryjoin='and_(Edition.id == '
                'foreign(EditionContributor.edition_id),'
                ' EditionContributor.role_id == 3)',
    secondaryjoin='Person.id == EditionContributor.person_id',
    viewonly=True)

# translators: returns Person objects (backward compatible)
translators = relationship(
    'Person',
    secondary='suomisf.editioncontributor',
    primaryjoin='and_(Edition.id == '
                'foreign(EditionContributor.edition_id),'
                ' EditionContributor.role_id == 2)',
    secondaryjoin='Person.id == EditionContributor.person_id',
    viewonly=True)

# contributions: returns EditionContributor objects
contributions = relationship(
    'EditionContributor',
    primaryjoin='EditionContributor.edition_id == Edition.id',
    foreign_keys='EditionContributor.edition_id',
    viewonly=True)
```

---

## Phase 3: API Changes

### impl_contributors.py

**`update_edition_contributors()`** — rewrite to use `EditionContributor`
instead of `Contributor` via Part. New logic:

1. Filter input to edition roles only (2, 3, 4, 5, 7)
2. Delete existing `EditionContributor` rows for the edition
3. Insert new `EditionContributor` rows

**`_update_part_contributors()`** — remove the EDITION branch after
cleanup phase is complete.

### impl_editions.py

**`copy_edition()`** — after creating Parts, also copy
`EditionContributor` rows for the new edition. Do not copy
edition-role `Contributor` rows from the old Parts.

### model.py

Add `EditionContributorSchema`:

```python
class EditionContributorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EditionContributor
    person = fields.Nested(
        PersonBriefSchema(only=('id', 'name', 'alt_name')))
    role = fields.Nested(ContributorRoleSchema)
    description = fields.String()
    real_person = fields.Nested(
        lambda: PersonBriefSchema(only=('id', 'name')))
```

Update `EditionBriefSchema.contributions` and
`WorkEditionBriefSchema.contributions` to use
`EditionContributorSchema`.

---

## Phase 4: Cleanup

After all tests pass:

1. Run the cleanup SQL (uncomment Phase 4 block in migration SQL)
   to remove edition-role rows from `contributor` table
2. Remove EDITION branch from `_update_part_contributors()`
3. Update `get_contributors_string()` if called for editions
4. Re-run full test suite to confirm no regressions

---

## Tests Required

New test file: `tests/api/test_edition_contributors.py`

| Test | Description |
|------|-------------|
| `test_edition_contributor_translator` | Edition with translator (role 2) in editioncontributor |
| `test_edition_contributor_editor` | Edition with editor (role 3) |
| `test_edition_contributor_cover_artist` | Edition with cover artist (role 4) |
| `test_edition_contributor_illustrator` | Edition with illustrator (role 5) |
| `test_edition_contributor_chief_editor` | Edition with chief editor (role 7) |
| `test_edition_contributor_update` | PUT replaces existing edition contributors |
| `test_edition_contributor_in_response` | GET /api/editions/{id} includes contributions |
| `test_copy_edition_copies_contributors` | copy_edition copies EditionContributor rows |
| `test_edition_author_not_in_editioncontributor` | Authors (role 1) stay in Contributor |
| `test_migration_count_matches` | editioncontributor row count matches source data |

---

## Files Requiring Changes

### Migration Layer

| File | Change |
|------|--------|
| `migrations/002_edition_contributor_migration.sql` | New: create table, populate, grant |

### ORM Layer

| File | Change |
|------|--------|
| `app/orm_decl.py` | Add `EditionContributor` class; update `Edition` relationships |

### Implementation Layer

| File | Functions Affected |
|------|-------------------|
| `app/impl_contributors.py` | `update_edition_contributors()`, `_update_part_contributors()` |
| `app/impl_editions.py` | `copy_edition()` |

### Schema Layer

| File | Change |
|------|--------|
| `app/model.py` | Add `EditionContributorSchema`; update `EditionBriefSchema` |

### Test Layer

| File | Change |
|------|--------|
| `tests/api/test_edition_contributors.py` | New file |
| `tests/TEST_DOCUMENTATION.md` | Document new tests |
| `tests/API_COVERAGE.md` | Update coverage matrix |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | `ON CONFLICT DO NOTHING`; cleanup SQL is commented out until verified |
| API breaking changes | `editors`/`translators` keep returning `Person` objects |
| Multi-Part editions | `DISTINCT` in INSERT collapses same person+role from different Parts |
| Partial migration | Transaction wrapping in SQL; rollback by dropping the table |

---

## Success Criteria

1. All existing 598 tests pass (plus 4 stale snapshots, 2 skipped)
2. New edition contributor tests pass
3. API response format for editions unchanged
4. `editioncontributor` row count matches source contributor data
5. `copy_edition()` preserves contributors in the copied edition
6. Snapshots not updated until migration fully complete
