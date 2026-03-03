"""
SuomiSF API People Roles Tests

Tests for the Person.roles field, which aggregates distinct
ContributorRole objects from WorkContributor, EditionContributor,
and StoryContributor for a given person.

The roles field is exposed via PersonBriefSchema and appears in:
  - GET /api/filter/people/<pattern>
  - Nested person objects in edition translators/editors lists
"""

import pytest

from .base_test import BaseAPITest
from tests.api.test_works import create_test_work, delete_test_work
from tests.api.test_people_aliases import (
    create_test_person,
    delete_test_person,
)

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'


@pytest.fixture
def admin_client(api_client):
    """Get an API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


class TestPersonRolesField(BaseAPITest):
    """
    Tests for the roles field on PersonBriefSchema.

    Verifies that Person.roles correctly combines contributions from
    WorkContributor, EditionContributor, and StoryContributor.
    """

    def test_filter_people_includes_roles_field(self, api_client):
        """
        GET /api/filter/people/<pattern> must include a 'roles' field
        in each returned person object.
        """
        resp = api_client.get('/api/filter/people/Unsworth')
        resp.assert_success()

        people = resp.data
        assert isinstance(people, list) and len(people) > 0, \
            "Expected at least one person matching 'Unsworth'"

        person = people[0]
        assert 'roles' in person, \
            f"'roles' field missing from filter_people response: {person}"

    def test_author_has_kirjoittaja_role(self, api_client):
        """
        A person with a work-level author contribution (role_id=1)
        must have 'Kirjoittaja' in their roles list.

        Uses person 1 (Unsworth, Barry) who has a WorkContributor
        row with role_id=1.
        """
        resp = api_client.get('/api/filter/people/Unsworth')
        resp.assert_success()

        people = resp.data
        person = next(
            (p for p in people if int(p['id']) == 1), None
        )
        assert person is not None, "Person 1 (Unsworth) not found"
        assert 'Kirjoittaja' in person['roles'], (
            f"Expected 'Kirjoittaja' in roles, got: {person['roles']}"
        )

    def test_translator_has_kaantaja_role(self, api_client):
        """
        A person with an edition-level translator contribution
        (role_id=2) must have 'Kääntäjä' in their roles list.

        Uses person 2 (Buffa, Aira) who has an EditionContributor
        row with role_id=2.
        """
        resp = api_client.get('/api/filter/people/Buffa')
        resp.assert_success()

        people = resp.data
        person = next(
            (p for p in people if int(p['id']) == 2), None
        )
        assert person is not None, "Person 2 (Buffa, Aira) not found"
        assert 'Kääntäjä' in person['roles'], (
            f"Expected 'Kääntäjä' in roles, got: {person['roles']}"
        )

    def test_new_work_contribution_adds_role(self, admin_client):
        """
        After creating a work attributed to a new person, that person's
        roles list must contain 'Kirjoittaja' (role_id=1).

        Tests that Person.roles reflects WorkContributor rows.
        """
        person_id = create_test_person(
            admin_client, 'Test Roles Person (roles test)'
        )
        work_id = None
        try:
            work_id = create_test_work(
                admin_client,
                person_id,
                title='Test Roles Work (roles test)',
            )

            resp = admin_client.get(
                '/api/filter/people/Test Roles Person'
            )
            resp.assert_success()
            people = resp.data
            person = next(
                (p for p in people if int(p['id']) == person_id),
                None
            )
            assert person is not None, (
                f"Person {person_id} not found in filter response"
            )
            assert 'Kirjoittaja' in person['roles'], (
                f"Expected 'Kirjoittaja' after work creation, "
                f"got: {person['roles']}"
            )
        finally:
            if work_id is not None:
                delete_test_work(admin_client, work_id)
            delete_test_person(admin_client, person_id)

    def test_person_with_no_contributions_has_empty_roles(
            self, admin_client):
        """
        A newly created person with no contributions must have an
        empty roles list.
        """
        person_id = create_test_person(
            admin_client, 'Test No Roles Person (roles test)'
        )
        try:
            resp = admin_client.get(
                '/api/filter/people/Test No Roles Person'
            )
            resp.assert_success()
            people = resp.data
            person = next(
                (p for p in people if int(p['id']) == person_id),
                None
            )
            assert person is not None, (
                f"Person {person_id} not found in filter response"
            )
            assert person['roles'] == [], (
                f"Expected empty roles for new person, "
                f"got: {person['roles']}"
            )
        finally:
            delete_test_person(admin_client, person_id)

    def test_alias_roles_appear_on_real_person(self, api_client):
        """
        A real person whose alias has a work contribution must show
        the alias's role in their own roles list.

        Uses person 34 (Aalto, Kaarina) whose alias is person 35
        (Valoaalto, Kaarina), the author of work 42 (Mystikko).
        """
        resp = api_client.get('/api/filter/people/Aalto, Kaarina')
        resp.assert_success()

        people = resp.data
        person = next(
            (p for p in people if int(p['id']) == 34), None
        )
        assert person is not None, \
            "Person 34 (Aalto, Kaarina) not found"
        assert 'Kirjoittaja' in person['roles'], (
            f"Expected 'Kirjoittaja' via alias, got: {person['roles']}"
        )
