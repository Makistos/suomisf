# Schema Migration Test Plan: ShortStory Refactoring

This document outlines the tests required for migrating ShortStory from the
current Part-based model to a direct Edition relationship with dedicated
StoryContributors table.

**Created:** 2026-02-15

---

## Table of Contents

1. [Schema Change Overview](#schema-change-overview)
2. [New Junction Table Tests](#new-junction-table-tests)
3. [StoryContributors Table Tests](#storycontributors-table-tests)
4. [Affected Endpoint Tests](#affected-endpoint-tests)
5. [Data Migration Tests](#data-migration-tests)
6. [Backward Compatibility Tests](#backward-compatibility-tests)
7. [Implementation Priority](#implementation-priority)
8. [Files Requiring Changes](#files-requiring-changes)

---

## Schema Change Overview

### Current Model

```
ShortStory -> Part (shortstory_id) -> Edition (edition_id)
ShortStory authors -> Part -> Contributor (part_id)
```

**Key relationships:**
- ShortStory.id = Part.shortstory_id
- Part.edition_id = Edition.id
- Contributor.part_id = Part.id (shared with Work contributors)

### Proposed Model

```
ShortStory <-> Edition (via new edition_shortstory junction table)
ShortStory -> StoryContributors (new dedicated table)
```

**New tables:**
- `edition_shortstory`: Junction table (edition_id, shortstory_id, order_num)
- `story_contributor`: Dedicated contributors (shortstory_id, person_id,
  role_id, real_person_id, description)

---

## New Junction Table Tests

### Table: `edition_shortstory`

| Test | Description | Endpoint |
|------|-------------|----------|
| `test_add_short_to_edition` | POST adds short story to edition | POST /api/editions/{id}/shorts |
| `test_remove_short_from_edition` | DELETE removes short from edition | DELETE /api/editions/{id}/shorts/{sid} |
| `test_edition_shorts_returns_all` | GET returns all linked shorts | GET /api/editions/{id}/shorts |
| `test_short_editions_returns_all` | GET short includes all editions | GET /api/shorts/{id} |
| `test_short_order_in_edition` | Verify order_num preserved | GET /api/editions/{id}/shorts |
| `test_cascade_delete_edition` | Deleting edition removes junction entries | DELETE /api/editions/{id} |
| `test_cascade_delete_short` | Deleting short removes junction entries | DELETE /api/shorts/{id} |
| `test_duplicate_link_prevented` | Same short+edition pair rejected | POST /api/editions/{id}/shorts |

### Test Implementation Notes

```python
def test_add_short_to_edition(admin_client, existing_edition_id,
                               existing_short_id):
    """Add a short story to an edition."""
    data = {
        'data': {
            'shortstory_id': existing_short_id,
            'order_num': 1
        }
    }
    response = admin_client.post(
        f'/api/editions/{existing_edition_id}/shorts',
        data=data
    )
    assert response.status_code == 201
```

---

## StoryContributors Table Tests

### Table: `story_contributor`

| Test | Description |
|------|-------------|
| `test_add_story_contributor` | Add contributor to short story |
| `test_remove_story_contributor` | Remove contributor from short |
| `test_update_story_contributors` | PUT replaces all contributors |
| `test_story_author_role` | Verify role_id=1 (Kirjoittaja) works |
| `test_story_translator_role` | Verify role_id=2 (Kääntäjä) works |
| `test_story_illustrator_role` | Verify role_id=6 (Kuvittaja) works |
| `test_contributor_with_real_person` | Test real_person_id (pseudonym) |
| `test_contributor_with_description` | Test description field |
| `test_story_contributors_isolated` | Verify separation from Part.Contributor |

### Role IDs Reference

| ID | Finnish Name | English |
|----|--------------|---------|
| 1 | Kirjoittaja | Author |
| 2 | Kääntäjä | Translator |
| 6 | Kuvittaja | Illustrator |

### Test Implementation Notes

```python
def test_add_story_contributor(admin_client, existing_short_id,
                                existing_person_id):
    """Add a contributor directly to a short story."""
    data = {
        'data': {
            'contributors': [
                {
                    'person': {'id': existing_person_id},
                    'role': {'id': 1}  # Author
                }
            ]
        }
    }
    response = admin_client.put(
        f'/api/shorts/{existing_short_id}',
        data=data
    )
    assert response.status_code == 200

    # Verify contributor saved to story_contributor table
    get_resp = admin_client.get(f'/api/shorts/{existing_short_id}')
    contributors = get_resp.data.get('contributors', [])
    assert any(c['person']['id'] == existing_person_id for c in contributors)
```

---

## Affected Endpoint Tests

### Shorts CRUD (`/api/shorts`)

| Test | Current Behavior | New Behavior to Test |
|------|------------------|---------------------|
| `test_get_short_has_authors` | Authors via Part->Contributor | Authors via StoryContributors |
| `test_get_short_has_contributors` | Contributors via Part->Contributor | Contributors via StoryContributors |
| `test_create_short_with_contributors` | Saves to Contributor | Saves to StoryContributors |
| `test_update_short_contributors` | Updates Contributor | Updates StoryContributors |
| `test_short_has_editions` | Via Part | Via edition_shortstory |

### Edition Shorts (`/api/editions/{id}/shorts`)

| Test | Current Path | New Path |
|------|--------------|----------|
| `test_edition_shorts_count` | Part.edition_id + Part.shortstory_id | edition_shortstory join |
| `test_edition_shorts_order` | Part.order_num | edition_shortstory.order_num |
| `test_edition_shorts_with_contributors` | Via Part->Contributor | Via StoryContributors |

**Current implementation (impl_editions.py:943-958):**
```python
shorts = session.query(ShortStory)\
    .join(Part)\
    .filter(Part.edition_id == edition_id)\
    .filter(Part.shortstory_id == ShortStory.id)\
    .order_by(Part.order_num)\
    .all()
```

**New implementation:**
```python
shorts = session.query(ShortStory)\
    .join(EditionShortStory)\
    .filter(EditionShortStory.edition_id == edition_id)\
    .order_by(EditionShortStory.order_num)\
    .all()
```

### Work Shorts (`/api/works/shorts/{id}`)

| Test | Impact |
|------|--------|
| `test_work_shorts_returns_all` | Still uses Part for work_id link |
| `test_work_shorts_contributors_match` | Contributors from StoryContributors |

**Note:** Work-to-ShortStory relationship still goes through Part because
Part.work_id is needed to associate shorts with works.

### People Shorts (`/api/people/{id}/shorts`)

| Test | Current Path | New Path |
|------|--------------|----------|
| `test_person_shorts_as_author` | Part->Contributor | StoryContributors |
| `test_person_shorts_as_translator` | Part->Contributor | StoryContributors |
| `test_person_shorts_count` | Part->Contributor | StoryContributors |

**Current implementation (impl_people.py:1052-1058):**
```python
shorts = session.query(ShortStory)\
    .join(Part, Part.shortstory_id == ShortStory.id)\
    .join(Contributor, Contributor.part_id == Part.id)\
    .filter(Contributor.person_id == person_id)\
    .distinct()\
    .all()
```

**New implementation:**
```python
shorts = session.query(ShortStory)\
    .join(StoryContributor)\
    .filter(StoryContributor.person_id == person_id)\
    .distinct()\
    .all()
```

### Stats Endpoints

| Endpoint | Affected Query | Change Required |
|----------|---------------|-----------------|
| `/api/stats/nationalitycounts` | Join to Person via Contributor | Join via StoryContributor |
| `/api/stats/storypersoncounts` | Join to Person via Contributor | Join via StoryContributor |
| `/api/stats/storiesbyyear` | Uses ShortStory directly | No change needed |

---

## Data Migration Tests

### Migration Verification

| Test | Description |
|------|-------------|
| `test_migrate_part_shorts_to_junction` | All Part rows with shortstory_id create junction entries |
| `test_migrate_contributors_to_story_contributors` | Contributor rows for shorts copied to StoryContributors |
| `test_migration_preserves_order` | Part.order_num -> edition_shortstory.order_num |
| `test_migration_preserves_editions` | All edition links preserved |
| `test_migration_preserves_contributors` | All author/translator/illustrator links preserved |
| `test_migration_count_matches` | Total shorts unchanged |
| `test_migration_rollback` | Can rollback if issues |

### Migration Script Test Approach

```python
def test_migration_preserves_editions(app, db_session):
    """Verify all edition-short links are preserved after migration."""
    # Count links before migration
    before_count = db_session.query(Part)\
        .filter(Part.shortstory_id.isnot(None))\
        .filter(Part.edition_id.isnot(None))\
        .count()

    # Run migration
    run_migration()

    # Count links after migration
    after_count = db_session.query(EditionShortStory).count()

    assert after_count == before_count, (
        f"Edition-short links changed: {before_count} -> {after_count}"
    )
```

---

## Backward Compatibility Tests

### API Response Format

| Test | Description |
|------|-------------|
| `test_api_response_format_unchanged` | JSON structure matches pre-migration |
| `test_short_schema_fields_unchanged` | All existing fields present |
| `test_edition_shorts_format_unchanged` | Response format matches |
| `test_work_shorts_format_unchanged` | Snapshot comparison passes |

### Snapshot Comparisons

Use existing snapshots to verify responses don't change:
- `short_1.json` - Single short story response
- `work_shorts_1378.json` - Work shorts response (22 shorts)
- `edition_1.json` - Edition response (verify stories field)

```python
def test_short_response_matches_snapshot(api_client, snapshot_manager):
    """Verify short response format unchanged after migration."""
    response = api_client.get('/api/shorts/1')
    response.assert_success()

    snapshot = snapshot_manager.load_snapshot('short_1')
    expected_fields = snapshot['response']['data'].keys()

    for field in expected_fields:
        assert field in response.data, f"Missing field: {field}"
```

---

## Implementation Priority

### Phase 1: New Tables + Tests (Week 1)

1. Create `edition_shortstory` junction table
2. Create `story_contributor` table
3. Write unit tests for new tables
4. Add ORM models to `orm_decl.py`

### Phase 2: Migration + Tests (Week 2)

1. Write data migration script
2. Migration verification tests
3. Rollback tests
4. Test on copy of production data

### Phase 3: API Updates + Tests (Week 3)

1. Update `impl_shorts.py` to use new tables
2. Update `impl_editions.py` edition_shorts function
3. Update `impl_contributors.py` update_short_contributors
4. Update `impl_people.py` person_shorts
5. Run full test suite

### Phase 4: Cleanup (Week 4)

1. Remove old Part.shortstory_id queries where possible
2. Keep Part for work-to-short relationship
3. Update schemas if needed
4. Final regression tests
5. Deploy

---

## Files Requiring Changes

### ORM Layer

| File | Changes |
|------|---------|
| `orm_decl.py` | Add EditionShortStory, StoryContributor classes; update ShortStory relationships |

### Implementation Layer

| File | Functions Affected |
|------|-------------------|
| `impl_shorts.py` | get_short, story_create_update, search_shorts, get_latest_shorts |
| `impl_editions.py` | edition_shorts |
| `impl_works.py` | get_work_shorts (partial - still needs Part for work_id) |
| `impl_people.py` | person_shorts |
| `impl_contributors.py` | update_short_contributors |
| `impl_stats.py` | nationality counts, person counts queries |
| `impl_issues.py` | issue_shorts_get (uses IssueContent, may be unaffected) |

### Schema Layer

| File | Changes |
|------|---------|
| `model.py` | ShortBriefSchema - update contributors source |
| `model_shortsearch.py` | Update if search joins change |
| `model_person.py` | PersonShortsSchema if needed |

### Test Layer

| File | New Tests Needed |
|------|------------------|
| `test_shorts.py` | New file for shorts CRUD tests |
| `test_editions.py` | Add edition_shorts tests |
| `test_work_shorts.py` | Update for new contributor path |
| `test_migration.py` | New file for migration tests |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Run on test DB first; keep Part data until verified |
| API breaking changes | Snapshot tests verify response format unchanged |
| Performance regression | Add indexes on new junction tables |
| Partial migration | Transaction wrapping; rollback capability |

---

## Success Criteria

1. All existing tests pass after migration
2. Snapshot comparisons match pre-migration responses
3. No API response format changes
4. Short story counts match before/after
5. All contributor relationships preserved
6. Performance within 10% of current
