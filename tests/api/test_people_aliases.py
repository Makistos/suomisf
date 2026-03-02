"""
SuomiSF API People Alias Tests

Tests for alias linking between persons:
- Create a person, create an alias person
- Link alias to real person
- Add a work to the alias person
- Verify GET /api/people/{id} merges alias works into real person
- Verify GET /api/filter/alias/{id} returns alias persons
"""

import pytest

from .base_test import BaseAPITest
from tests.api.test_works import create_test_work, delete_test_work


TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def create_test_person(admin_client, name):
    """
    Create a minimal test person via POST /api/people.

    Returns:
        int: Created person ID.
    """
    response = admin_client.post(
        '/api/people',
        data={'data': {'name': name}}
    )
    assert response.status_code == 201, (
        f"Failed to create person '{name}'. "
        f"Status: {response.status_code}. Response: {response.json}"
    )
    person_id = int(response.data)
    assert person_id > 0
    return person_id


def delete_test_person(admin_client, person_id):
    """Delete a test person via DELETE /api/people/{id}."""
    response = admin_client.delete(f'/api/people/{person_id}')
    assert response.status_code == 200, (
        f"Failed to delete person {person_id}. "
        f"Status: {response.status_code}. Response: {response.json}"
    )


def link_alias(admin_client, real_id, real_name, alias_ids):
    """
    Update a person's aliases list via PUT /api/people.

    Args:
        real_id: ID of the real person.
        real_name: Name of the real person (required by person_update).
        alias_ids: List of person IDs to set as aliases.
    """
    response = admin_client.put(
        '/api/people',
        data={
            'data': {
                'id': real_id,
                'name': real_name,
                'aliases': [{'id': aid} for aid in alias_ids],
            }
        }
    )
    assert response.status_code == 200, (
        f"Failed to link aliases for person {real_id}. "
        f"Status: {response.status_code}. Response: {response.json}"
    )


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """Get an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------

class TestPeopleAliases(BaseAPITest):
    """Tests for the alias merge behaviour in GET /api/people/{id}."""

    def test_alias_works_appear_on_real_person(self, admin_client):
        """
        A work attributed to an alias person must appear in the real
        person's work list returned by GET /api/people/{id}.

        Steps:
          1. Create real person and alias person.
          2. Link alias → real via PUT /api/people.
          3. Create a work with alias person as author.
          4. GET real person; assert the work is present in 'works'.
          5. Clean up: delete work, unlink alias, delete both persons.
        """
        # Step 1: create persons
        real_name = 'Test Real Person (alias test)'
        alias_name = 'Test Alias Person (alias test)'
        real_id = create_test_person(admin_client, real_name)
        alias_id = create_test_person(admin_client, alias_name)

        work_id = None
        try:
            # Step 2: link alias to real person
            link_alias(admin_client, real_id, real_name, [alias_id])

            # Step 3: create a work attributed to the alias person
            work_id = create_test_work(
                admin_client,
                alias_id,
                title='Alias Work (alias test)',
            )

            # Step 4: GET real person and verify work is merged in
            resp = admin_client.get(f'/api/people/{real_id}')
            resp.assert_success()
            person_data = resp.data

            work_ids = [w['id'] for w in person_data.get('works', [])]
            assert work_id in work_ids, (
                f"Work {work_id} (attributed to alias {alias_id}) "
                f"not found in real person {real_id} works: {work_ids}"
            )

        finally:
            # Clean up in reverse order
            if work_id is not None:
                delete_test_work(admin_client, work_id)
            # Remove alias link so persons can be deleted
            link_alias(admin_client, real_id, real_name, [])
            delete_test_person(admin_client, alias_id)
            delete_test_person(admin_client, real_id)

    def test_aliases_field_lists_alias_person(self, admin_client):
        """
        GET /api/people/{id} must include the alias person in the
        'aliases' field of the response.
        """
        real_name = 'Test Real Person (aliases field test)'
        alias_name = 'Test Alias Person (aliases field test)'
        real_id = create_test_person(admin_client, real_name)
        alias_id = create_test_person(admin_client, alias_name)

        try:
            link_alias(admin_client, real_id, real_name, [alias_id])

            resp = admin_client.get(f'/api/people/{real_id}')
            resp.assert_success()
            person_data = resp.data

            alias_ids = [
                int(a['id'])
                for a in person_data.get('aliases', [])
            ]
            assert alias_id in alias_ids, (
                f"Alias {alias_id} not found in real person {real_id} "
                f"aliases field: {alias_ids}"
            )

        finally:
            link_alias(admin_client, real_id, real_name, [])
            delete_test_person(admin_client, alias_id)
            delete_test_person(admin_client, real_id)

    def test_filter_alias_endpoint_returns_alias(self, admin_client):
        """
        GET /api/filter/alias/{id} must return the alias person's
        data when an alias link exists.
        """
        real_name = 'Test Real Person (filter alias test)'
        alias_name = 'Test Alias Person (filter alias test)'
        real_id = create_test_person(admin_client, real_name)
        alias_id = create_test_person(admin_client, alias_name)

        try:
            link_alias(admin_client, real_id, real_name, [alias_id])

            resp = admin_client.get(f'/api/filter/alias/{real_id}')
            resp.assert_success()
            alias_list = resp.data

            assert isinstance(alias_list, list), (
                f"Expected list from filter/alias, got {type(alias_list)}"
            )
            returned_ids = [int(a['id']) for a in alias_list]
            assert alias_id in returned_ids, (
                f"Alias {alias_id} not returned by filter/alias "
                f"for real person {real_id}: {returned_ids}"
            )

        finally:
            link_alias(admin_client, real_id, real_name, [])
            delete_test_person(admin_client, alias_id)
            delete_test_person(admin_client, real_id)

    def test_unlink_alias_removes_from_aliases_field(
            self, admin_client):
        """
        After removing the alias link, GET /api/people/{id} must no
        longer list the former alias in the 'aliases' field.
        """
        real_name = 'Test Real Person (unlink test)'
        alias_name = 'Test Alias Person (unlink test)'
        real_id = create_test_person(admin_client, real_name)
        alias_id = create_test_person(admin_client, alias_name)

        try:
            link_alias(admin_client, real_id, real_name, [alias_id])
            link_alias(admin_client, real_id, real_name, [])

            resp = admin_client.get(f'/api/people/{real_id}')
            resp.assert_success()
            person_data = resp.data

            alias_ids = [
                int(a['id'])
                for a in person_data.get('aliases', [])
            ]
            assert alias_id not in alias_ids, (
                f"Alias {alias_id} still present after unlinking "
                f"from real person {real_id}: {alias_ids}"
            )

        finally:
            delete_test_person(admin_client, alias_id)
            delete_test_person(admin_client, real_id)
