"""
SuomiSF API - Work Contributor Tests (Migration 003)

Tests for WorkContributor table that stores work-specific
contributor roles directly on the work (without Part indirection).

Roles tested:
  1 = Kirjoittaja (Author)
  3 = Toimittaja (Editor)
  6 = Esiintyy (Appears in / Subject)

Note: Run tests/scripts/setup_test_db.py before running these tests,
then apply migrations 001, 002, and 003 to the test DB.
"""

import pytest

from app.orm_decl import (
    WorkContributor, Contributor, Part, Person
)
from app.route_helpers import new_session

from .base_test import BaseAPITest
from .test_works import (
    create_test_work, delete_test_work,
    TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD,
)


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

WORK_ROLES = {
    'author': 1,
    'editor': 3,
    'subject': 6,
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def set_work_contributors(client, work_id, contributors):
    """
    Update the contributors of a work via the API.

    Args:
        client: Authenticated admin API client.
        work_id: ID of the work to update.
        contributors: List of contributor dicts with 'person',
            'role', and optional 'description' keys.

    Returns:
        Response object from the PUT call.
    """
    get_resp = client.get(f'/api/works/{work_id}')
    get_resp.assert_success()
    current = get_resp.data

    work_data = {
        'data': {
            'id': work_id,
            'title': current.get('title', 'Test'),
            'orig_title': current.get('orig_title', ''),
            'pubyear': current.get('pubyear', 2025),
            'work_type': current.get('work_type') or {'id': 1},
            'contributions': contributors,
        }
    }
    return client.put('/api/works', data=work_data)


def get_work_contributions(client, work_id):
    """
    Retrieve the contributions list for a work.

    Args:
        client: Authenticated admin API client.
        work_id: ID of the work.

    Returns:
        List of contribution dicts from the API response.
    """
    resp = client.get(f'/api/works/{work_id}')
    resp.assert_success()
    return resp.data.get('contributions', [])


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def admin_client(api_client):
    """API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def existing_person_id(app):
    """An existing person ID to use as contributor."""
    with app.app_context():
        session = new_session()
        person = session.query(Person).first()
        pid = person.id if person else 1
        session.close()
        return pid


@pytest.fixture
def second_person_id(app, existing_person_id):
    """A second existing person ID, different from the first."""
    with app.app_context():
        session = new_session()
        person = (
            session.query(Person)
            .filter(Person.id != existing_person_id)
            .first()
        )
        pid = person.id if person else existing_person_id + 1
        session.close()
        return pid


@pytest.fixture
def test_work(admin_client, existing_person_id):
    """
    Create a work for contributor tests.

    Yields:
        work_id (int)

    Cleans up (deletes the work) after the test.
    """
    work_id = create_test_work(
        admin_client,
        existing_person_id,
        title='Work Contributor Test Work',
        pubyear=2025,
    )
    yield work_id
    delete_test_work(admin_client, work_id)


# -------------------------------------------------------------------
# Tests: individual work roles
# -------------------------------------------------------------------

class TestWorkContributorRoles(BaseAPITest):
    """
    Tests that each work-specific role can be stored and retrieved
    via the WorkContributor table.
    """

    def _assert_role_in_contributions(
            self, client, work_id, person_id, role_id, role_name):
        """
        Set a single contributor with role_id on work_id and assert
        it appears in the contributions list.

        Args:
            client: Authenticated admin API client.
            work_id: Work to update.
            person_id: Person to add.
            role_id: Role ID to assign.
            role_name: Role name for assertion messages.
        """
        contributors = [
            {
                'person': {'id': person_id},
                'role': {'id': role_id},
                'description': '',
            }
        ]
        resp = set_work_contributors(client, work_id, contributors)
        assert resp.status_code == 200, (
            f'Setting {role_name} failed: {resp.status_code} '
            f'{resp.json}'
        )

        contributions = get_work_contributions(client, work_id)
        role_ids = [c['role']['id'] for c in contributions]
        assert role_id in role_ids, (
            f'Role {role_name} (id={role_id}) not found in '
            f'contributions: {contributions}'
        )
        person_ids = [
            c['person']['id'] for c in contributions
            if c['role']['id'] == role_id
        ]
        assert person_id in person_ids, (
            f'Person {person_id} not found for role '
            f'{role_name}: {contributions}'
        )

    def test_work_contributor_author(
            self, admin_client, test_work, existing_person_id):
        """
        Author (role 1) is stored in WorkContributor and returned
        in contributions.

        Parameters: role_id=1, person=existing_person_id
        Assertions:
          - PUT /api/works returns 200
          - GET /api/works/{id} contributions includes role_id=1
          - Correct person_id is associated with the role
        """
        self._assert_role_in_contributions(
            admin_client, test_work, existing_person_id,
            WORK_ROLES['author'], 'author',
        )

    def test_work_contributor_editor(
            self, admin_client, test_work, existing_person_id):
        """
        Editor (role 3) is stored in WorkContributor and returned
        in contributions.

        Parameters: role_id=3, person=existing_person_id
        Assertions:
          - PUT /api/works returns 200
          - GET /api/works/{id} contributions includes role_id=3
          - Correct person_id is associated with the role
        """
        self._assert_role_in_contributions(
            admin_client, test_work, existing_person_id,
            WORK_ROLES['editor'], 'editor',
        )

    def test_work_contributor_subject(
            self, admin_client, test_work, existing_person_id):
        """
        Appears-in / subject (role 6) is stored in WorkContributor
        and returned in contributions.

        Parameters: role_id=6, person=existing_person_id
        Assertions:
          - PUT /api/works returns 200
          - GET /api/works/{id} contributions includes role_id=6
          - Correct person_id is associated with the role
        """
        self._assert_role_in_contributions(
            admin_client, test_work, existing_person_id,
            WORK_ROLES['subject'], 'subject',
        )

    def test_work_contributor_in_response(
            self, admin_client, test_work, existing_person_id):
        """
        GET /api/works/{id} returns contributions list with person,
        role, and description fields.

        Parameters: role_id=1, person=existing_person_id
        Assertions:
          - contributions is a list
          - Each item has 'person', 'role', 'description' keys
          - 'role' has 'id' and 'name' sub-keys
        """
        contributions = get_work_contributions(
            admin_client, test_work
        )
        assert isinstance(contributions, list), (
            f'contributions is not a list: {contributions}'
        )
        for contrib in contributions:
            assert 'person' in contrib, (
                f'Missing person key: {contrib}'
            )
            assert 'role' in contrib, (
                f'Missing role key: {contrib}'
            )
            assert 'id' in contrib['role'], (
                f'Missing role id: {contrib}'
            )
            assert 'name' in contrib['role'], (
                f'Missing role name: {contrib}'
            )


# -------------------------------------------------------------------
# Tests: update behaviour
# -------------------------------------------------------------------

class TestWorkContributorUpdate(BaseAPITest):
    """
    Tests that updating work contributors replaces existing rows.
    """

    def test_work_contributor_update_replaces(
            self, admin_client, test_work,
            existing_person_id, second_person_id):
        """
        PUT with a new contributor list replaces all existing
        WorkContributor rows for the work.

        Parameters:
          - First PUT: existing_person_id as author (role 1)
          - Second PUT: second_person_id as editor (role 3)
        Assertions:
          - After second PUT, author role is gone
          - After second PUT, editor is present with second person
        """
        resp = set_work_contributors(
            admin_client, test_work,
            [{'person': {'id': existing_person_id},
              'role': {'id': WORK_ROLES['author']},
              'description': ''}]
        )
        assert resp.status_code == 200

        resp = set_work_contributors(
            admin_client, test_work,
            [{'person': {'id': second_person_id},
              'role': {'id': WORK_ROLES['editor']},
              'description': ''}]
        )
        assert resp.status_code == 200

        contributions = get_work_contributions(
            admin_client, test_work
        )
        role_ids = [c['role']['id'] for c in contributions]
        person_ids = [c['person']['id'] for c in contributions]

        assert WORK_ROLES['editor'] in role_ids, (
            f'Editor role missing after update: {contributions}'
        )
        assert second_person_id in person_ids, (
            f'second_person_id missing after update: {contributions}'
        )
        assert WORK_ROLES['author'] not in role_ids, (
            f'Author role still present after replacement: '
            f'{contributions}'
        )

    def test_work_contributor_description_stored(
            self, admin_client, test_work, existing_person_id):
        """
        Description field is stored and returned for work
        contributors.

        Parameters:
          - role_id=6 (subject), description='biography chapter'
        Assertions:
          - description field equals 'biography chapter' in
            contributions
        """
        description = 'biography chapter'
        resp = set_work_contributors(
            admin_client, test_work,
            [{'person': {'id': existing_person_id},
              'role': {'id': WORK_ROLES['subject']},
              'description': description}]
        )
        assert resp.status_code == 200

        contributions = get_work_contributions(
            admin_client, test_work
        )
        matched = [
            c for c in contributions
            if c['role']['id'] == WORK_ROLES['subject']
            and c['person']['id'] == existing_person_id
        ]
        assert matched, (
            f'Subject contribution not found: {contributions}'
        )
        assert matched[0].get('description') == description, (
            'Description mismatch. '
            f"Got: {matched[0].get('description')}"
        )


# -------------------------------------------------------------------
# Tests: no duplicate contributors
# -------------------------------------------------------------------

class TestWorkContributorNoDuplicates(BaseAPITest):
    """
    Tests that WorkContributor rows contain no duplicates even for
    works that have multiple editions.
    """

    def test_work_no_duplicate_contributors(
            self, admin_client, test_work, existing_person_id):
        """
        A work with one author set via PUT has exactly one author row
        in contributions — no duplicates from multiple editions.

        Parameters: role_id=1, person=existing_person_id
        Assertions:
          - contributions contains exactly one entry for role_id=1
            and person_id=existing_person_id
        Fixtures: admin_client, test_work, existing_person_id
        """
        resp = set_work_contributors(
            admin_client, test_work,
            [{'person': {'id': existing_person_id},
              'role': {'id': WORK_ROLES['author']},
              'description': ''}]
        )
        assert resp.status_code == 200

        contributions = get_work_contributions(
            admin_client, test_work
        )
        author_entries = [
            c for c in contributions
            if c['role']['id'] == WORK_ROLES['author']
            and c['person']['id'] == existing_person_id
        ]
        assert len(author_entries) == 1, (
            f'Expected 1 author entry, got {len(author_entries)}: '
            f'{author_entries}'
        )


# -------------------------------------------------------------------
# Tests: authors stored in WorkContributor (not Contributor via Part)
# -------------------------------------------------------------------

class TestAuthorInWorkContributor(BaseAPITest):
    """
    Verifies that work authors (role 1) are stored in the
    WorkContributor table.
    """

    def test_author_in_workcontributor(
            self, app, admin_client, test_work, existing_person_id):
        """
        Author (role 1) set via PUT is stored in workcontributor
        table directly.

        Parameters: work from test_work, role_id=1
        Assertions:
          - suomisf.workcontributor has exactly one row with
            role_id=1 for this work
        Fixtures: app, admin_client, test_work, existing_person_id
        """
        resp = set_work_contributors(
            admin_client, test_work,
            [{'person': {'id': existing_person_id},
              'role': {'id': WORK_ROLES['author']},
              'description': ''}]
        )
        assert resp.status_code == 200

        with app.app_context():
            session = new_session()
            author_rows = (
                session.query(WorkContributor)
                .filter(WorkContributor.work_id == test_work)
                .filter(WorkContributor.role_id == 1)
                .count()
            )
            session.close()

        assert author_rows == 1, (
            f'Expected 1 author row in WorkContributor for work '
            f'{test_work}, got {author_rows}'
        )


# -------------------------------------------------------------------
# Tests: migration data integrity
# -------------------------------------------------------------------

class TestWorkMigrationIntegrity(BaseAPITest):
    """
    Verifies that the migration SQL correctly populated the
    WorkContributor table from the existing Contributor+Part data.
    """

    def test_migration_count_matches(self, app):
        """
        The number of rows in suomisf.workcontributor is at least as
        large as the number of distinct (work_id, person_id, role_id)
        tuples in contributor+part for work roles (1, 3, 6).

        Assertions:
          - workcontributor row count >= source distinct row count
        Fixtures: app
        """
        work_roles = (1, 3, 6)

        with app.app_context():
            session = new_session()

            wc_count = session.query(WorkContributor).count()

            source_count = (
                session.query(
                    Part.work_id,
                    Contributor.person_id,
                    Contributor.role_id,
                )
                .join(Part, Part.id == Contributor.part_id)
                .filter(Part.shortstory_id.is_(None))
                .filter(Part.work_id.isnot(None))
                .filter(Contributor.role_id.in_(work_roles))
                .distinct()
                .count()
            )
            session.close()

        assert wc_count >= source_count, (
            f'WorkContributor has {wc_count} rows but source has '
            f'{source_count} distinct (work,person,role) tuples. '
            f'Migration may be incomplete.'
        )
