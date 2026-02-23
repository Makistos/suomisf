Always use line widths less or equal to 79 characters.

If changing or adding an API function always add tests and update documentation
both for API and tests and document the API.

Always recreate test database and add test user before running tests.
Never run tests against or modify the main database.

When doing database refactoring do not update the snapshots until finished.

## Testing Documentation

When adding or modifying API tests, always update the following files:

1. **tests/TEST_DOCUMENTATION.md** - Document each test with:
   - Test name and description
   - Parameter values used
   - Expected behaviors and assertions
   - Any fixtures or helper functions used

2. **tests/API_COVERAGE.md** - Update the API coverage matrix to reflect:
   - Which endpoints are tested
   - Test coverage status for each HTTP method
   - Any new endpoints or test scenarios added
