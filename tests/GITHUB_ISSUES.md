# GitHub Issues for Failing Tests

These issues document backend bugs discovered during API testing.
Create these issues at: https://github.com/Makistos/suomisf/issues/new

---

## Issue 1: Edition owners endpoint fails with User schema 'many' keyword error

**Labels:** bug

### Description

The `GET /api/editions/{id}/owners` endpoint fails with a TypeError because the User schema is being called with an invalid `many` keyword argument.

### Error

```
TypeError: 'many' is an invalid keyword argument for User
```

### Affected Endpoint

- `GET /api/editions/{editionid}/owners`

### Location

The issue is likely in `app/api_editions.py` or the related implementation file where the User schema is instantiated.

### Failing Tests

- `tests/api/test_editions_extra.py::TestEditionOwners::test_edition_owners_processes_request`
- `tests/api/test_editions_extra.py::TestEditionOwners::test_edition_owners_nonexistent`

### Suggested Fix

Remove or fix the `many=True` argument when instantiating the User schema. Marshmallow schemas don't accept `many` as a constructor keyword - instead use `schema.dump(data, many=True)` or `Schema(many=True)` at class level.

---

## ~~Issue 2: Short story GET endpoint crashes on non-existent ID~~ FIXED

**Status:** Fixed in commits fixing GitHub issue #65

Added null check after querying for the short story in `impl_shorts.py`. Now returns 404 with Finnish error message "Novellia ei löydy" when short story is not found.

---

## ~~Issue 3: Magazine and Issue update endpoints crash on missing 'id' field~~ FIXED

**Status:** Fixed in commits fixing GitHub issues #66

The validation has been added to `impl_magazines.py` and `impl_issues.py` to check for required fields before processing updates.

---

## Issue 4: Issue contributors GET endpoint returns list instead of Response

**Labels:** bug

### Description

The `GET /api/issues/{id}/contributors` endpoint returns a raw Python list instead of wrapping it in a ResponseType object, causing `make_api_response()` to crash.

### Error

```
AttributeError: 'list' object has no attribute 'status'
```

### Affected Endpoint

- `GET /api/issues/{issueid}/contributors`

### Location

`app/api_issues.py` - The `api_getissuecontributors` function.

### Failing Tests

- `tests/api/test_magazines_issues.py::TestIssueContributors::test_contributors_get_returns_200`
- `tests/api/test_magazines_issues.py::TestIssueContributors::test_contributors_get_returns_data`
- `tests/api/test_magazines_issues.py::TestIssueContributors::test_contributors_get_nonexistent`

### Suggested Fix

The `get_issue_contributors()` implementation should return a `ResponseType` object instead of a raw list:

```python
# Instead of:
return contributors_list

# Use:
return ResponseType(contributors_list, status=HttpResponseCode.OK.value)
```

---

## ~~Issue 5: Issue tags GET endpoint has parameter name mismatch~~ FIXED

**Status:** Fixed in commits fixing GitHub issue #68

The parameter name was changed from `issue_id` to `issueid` to match the route definition.

---

## Summary

| Issue | Endpoints | Tests Affected | Status |
|-------|-----------|----------------|--------|
| User schema 'many' keyword | GET /api/editions/{id}/owners | 2 | Open |
| ~~Short story crash on not found~~ | GET /api/shorts/{id} | 1 | **Fixed** |
| ~~Missing 'id' validation~~ | PUT /api/magazines, PUT /api/issues | 2 | **Fixed** |
| Contributors returns list | GET /api/issues/{id}/contributors | 3 | Open |
| ~~Parameter name mismatch~~ | GET /api/issues/{id}/tags | 3 | **Fixed** |
| **Total Open** | | **5** | |
