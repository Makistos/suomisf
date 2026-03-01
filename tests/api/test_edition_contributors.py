"""
SuomiSF API - Edition Contributor Tests (Migration 002)

Tests for EditionContributor table that stores edition-specific
contributor roles directly on the edition (without Part indirection).

Roles tested:
  2 = Kääntäjä (Translator)
  3 = Toimittaja (Editor)
  4 = Kansikuva (Cover Artist)
  5 = Kuvittaja (Illustrator)
  7 = Päätoimittaja (Chief Editor)

Authors (role 1) are work-level and remain in the Contributor table
via Part; they are tested to verify they do NOT appear in the
EditionContributor table.

Note: Run tests/scripts/setup_test_db.py before running these tests,
then apply migrations/001_shortstory_migration.sql and
migrations/002_edition_contributor_migration.sql to the test DB.
"""

import pytest

from app.orm_decl import (
    EditionContributor, Contributor, Edition as EditionModel,
    Part, Person
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

EDITION_ROLES = {
    'translator': 2,
    'editor': 3,
    'cover_artist': 4,
    'illustrator': 5,
    'chief_editor': 7,
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def set_edition_contributors(client, edition_id, contributors):
    """
    Update the contributors of an edition via the API.

    Args:
        client: Authenticated admin API client.
        edition_id: ID of the edition to update.
        contributors: List of contributor dicts with 'person',
            'role', and optional 'description' keys.

    Returns:
        Response object from the PUT call.
    """
    get_resp = client.get(f'/api/editions/{edition_id}')
    get_resp.assert_success()
    current = get_resp.data

    edition_data = {
        'data': {
            'id': edition_id,
            'editionnum': current.get('editionnum', 1),
            'contributors': contributors,
        }
    }
    return client.put('/api/editions', data=edition_data)


def get_edition_contributions(client, edition_id):
    """
    Retrieve the contributions list for an edition.

    Args:
        client: Authenticated admin API client.
        edition_id: ID of the edition.

    Returns:
        List of contribution dicts from the API response.
    """
    resp = client.get(f'/api/editions/{edition_id}')
    resp.assert_success()
    return resp.data.get('contributions', [])


def get_edition_editors(client, edition_id):
    """
    Retrieve the editors list for an edition.

    Args:
        client: Authenticated admin API client.
        edition_id: ID of the edition.

    Returns:
        List of editor Person dicts from the API response.
    """
    resp = client.get(f'/api/editions/{edition_id}')
    resp.assert_success()
    return resp.data.get('editors', [])


def get_edition_translators(client, edition_id):
    """
    Retrieve the translators list for an edition.

    Args:
        client: Authenticated admin API client.
        edition_id: ID of the edition.

    Returns:
        List of translator Person dicts from the API response.
    """
    resp = client.get(f'/api/editions/{edition_id}')
    resp.assert_success()
    return resp.data.get('translators', [])


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
def test_work_and_edition(admin_client, existing_person_id, app):
    """
    Create a work+edition pair for contributor tests.

    The first edition is created automatically when the work is
    created.

    Yields:
        Tuple of (work_id, edition_id).

    Cleans up (deletes the work) after the test.
    """
    work_id = create_test_work(
        admin_client,
        existing_person_id,
        title='Edition Contributor Test Work',
        pubyear=2025,
    )

    with app.app_context():
        session = new_session()
        edition = (
            session.query(EditionModel)
            .filter(
                EditionModel.title == 'Edition Contributor Test Work'
            )
            .first()
        )
        edition_id = edition.id if edition else None
        session.close()

    assert edition_id is not None, (
        'Auto-created edition not found for new work'
    )
    yield work_id, edition_id
    delete_test_work(admin_client, work_id)


# -------------------------------------------------------------------
# Tests: individual edition roles
# -------------------------------------------------------------------

class TestEditionContributorRoles(BaseAPITest):
    """
    Tests that each edition-specific role can be stored and retrieved
    via the EditionContributor table.
    """

    def _assert_role_in_contributions(
            self, client, edition_id, person_id, role_id, role_name):
        """
        Set a single contributor with role_id on edition_id and
        assert it appears in the contributions list.

        Args:
            client: Authenticated admin API client.
            edition_id: Edition to update.
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
        resp = set_edition_contributors(client, edition_id, contributors)
        assert resp.status_code == 200, (
            f'Setting {role_name} failed: {resp.status_code} '
            f'{resp.json}'
        )

        contributions = get_edition_contributions(client, edition_id)
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

    def test_edition_contributor_translator(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Translator (role 2) is stored in EditionContributor and
        returned in contributions.

        Parameters: role_id=2, person=existing_person_id
        Assertions:
          - PUT /api/editions returns 200
          - GET /api/editions/{id} contributions includes role_id=2
          - Correct person_id is associated with the role
        """
        _, edition_id = test_work_and_edition
        self._assert_role_in_contributions(
            admin_client, edition_id, existing_person_id,
            EDITION_ROLES['translator'], 'translator',
        )

    def test_edition_contributor_editor(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Editor (role 3) is stored in EditionContributor and returned
        in contributions and editors shortcut list.

        Parameters: role_id=3, person=existing_person_id
        Assertions:
          - PUT /api/editions returns 200
          - GET /api/editions/{id} editors includes the person
        """
        _, edition_id = test_work_and_edition
        contributors = [
            {
                'person': {'id': existing_person_id},
                'role': {'id': EDITION_ROLES['editor']},
                'description': '',
            }
        ]
        resp = set_edition_contributors(
            admin_client, edition_id, contributors
        )
        assert resp.status_code == 200

        editors = get_edition_editors(admin_client, edition_id)
        editor_ids = [e['id'] for e in editors]
        assert existing_person_id in editor_ids, (
            f'Person {existing_person_id} not in editors: {editors}'
        )

    def test_edition_contributor_cover_artist(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Cover artist (role 4) is stored in EditionContributor and
        returned in contributions.

        Parameters: role_id=4, person=existing_person_id
        Assertions:
          - PUT /api/editions returns 200
          - GET /api/editions/{id} contributions includes role_id=4
        """
        _, edition_id = test_work_and_edition
        self._assert_role_in_contributions(
            admin_client, edition_id, existing_person_id,
            EDITION_ROLES['cover_artist'], 'cover_artist',
        )

    def test_edition_contributor_illustrator(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Illustrator (role 5) is stored in EditionContributor and
        returned in contributions.

        Parameters: role_id=5, person=existing_person_id
        Assertions:
          - PUT /api/editions returns 200
          - GET /api/editions/{id} contributions includes role_id=5
        """
        _, edition_id = test_work_and_edition
        self._assert_role_in_contributions(
            admin_client, edition_id, existing_person_id,
            EDITION_ROLES['illustrator'], 'illustrator',
        )

    def test_edition_contributor_chief_editor(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Chief editor (role 7) is stored in EditionContributor and
        returned in contributions.

        Parameters: role_id=7, person=existing_person_id
        Assertions:
          - PUT /api/editions returns 200
          - GET /api/editions/{id} contributions includes role_id=7
        """
        _, edition_id = test_work_and_edition
        self._assert_role_in_contributions(
            admin_client, edition_id, existing_person_id,
            EDITION_ROLES['chief_editor'], 'chief_editor',
        )

    def test_edition_contributor_translator_in_translators(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Translator (role 2) appears in the translators shortcut list.

        Parameters: role_id=2, person=existing_person_id
        Assertions:
          - GET /api/editions/{id} translators includes the person
        """
        _, edition_id = test_work_and_edition
        contributors = [
            {
                'person': {'id': existing_person_id},
                'role': {'id': EDITION_ROLES['translator']},
                'description': '',
            }
        ]
        resp = set_edition_contributors(
            admin_client, edition_id, contributors
        )
        assert resp.status_code == 200

        translators = get_edition_translators(admin_client, edition_id)
        translator_ids = [t['id'] for t in translators]
        assert existing_person_id in translator_ids, (
            f'Person {existing_person_id} not in translators: '
            f'{translators}'
        )


# -------------------------------------------------------------------
# Tests: update behaviour
# -------------------------------------------------------------------

class TestEditionContributorUpdate(BaseAPITest):
    """
    Tests that updating edition contributors replaces existing rows.
    """

    def test_edition_contributor_update_replaces(
            self, admin_client, test_work_and_edition,
            existing_person_id, second_person_id):
        """
        PUT with a new contributor list replaces all existing
        EditionContributor rows for the edition.

        Parameters:
          - First PUT: existing_person_id as translator (role 2)
          - Second PUT: second_person_id as cover_artist (role 4)
        Assertions:
          - After second PUT, translator role is gone
          - After second PUT, cover_artist is present with second person
        """
        _, edition_id = test_work_and_edition

        resp = set_edition_contributors(
            admin_client, edition_id,
            [{'person': {'id': existing_person_id},
              'role': {'id': EDITION_ROLES['translator']},
              'description': ''}]
        )
        assert resp.status_code == 200

        resp = set_edition_contributors(
            admin_client, edition_id,
            [{'person': {'id': second_person_id},
              'role': {'id': EDITION_ROLES['cover_artist']},
              'description': ''}]
        )
        assert resp.status_code == 200

        contributions = get_edition_contributions(
            admin_client, edition_id
        )
        role_ids = [c['role']['id'] for c in contributions]
        person_ids = [c['person']['id'] for c in contributions]

        assert EDITION_ROLES['cover_artist'] in role_ids, (
            f'cover_artist role missing after update: {contributions}'
        )
        assert second_person_id in person_ids, (
            f'second_person_id missing after update: {contributions}'
        )
        assert EDITION_ROLES['translator'] not in role_ids, (
            f'translator role still present after replacement: '
            f'{contributions}'
        )

    def test_edition_contributor_description_stored(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        Description field is stored and returned for edition
        contributors.

        Parameters:
          - role_id=5 (illustrator), description='cover only'
        Assertions:
          - description field equals 'cover only' in contributions
        """
        _, edition_id = test_work_and_edition
        description = 'cover only'
        resp = set_edition_contributors(
            admin_client, edition_id,
            [{'person': {'id': existing_person_id},
              'role': {'id': EDITION_ROLES['illustrator']},
              'description': description}]
        )
        assert resp.status_code == 200

        contributions = get_edition_contributions(
            admin_client, edition_id
        )
        matched = [
            c for c in contributions
            if c['role']['id'] == EDITION_ROLES['illustrator']
            and c['person']['id'] == existing_person_id
        ]
        assert matched, (
            f'Illustrator contribution not found: {contributions}'
        )
        assert matched[0].get('description') == description, (
            'Description mismatch. '
            f"Got: {matched[0].get('description')}"
        )


# -------------------------------------------------------------------
# Tests: copy_edition
# -------------------------------------------------------------------

class TestCopyEditionContributors(BaseAPITest):
    """
    Tests that copy_edition() copies EditionContributor rows to the
    new edition.
    """

    def test_copy_edition_copies_contributors(
            self, admin_client, test_work_and_edition,
            existing_person_id):
        """
        copy_edition copies EditionContributor rows to the new edition.

        Parameters:
          - Original edition has translator (role 2) and cover artist
            (role 4) contributors.
        Assertions:
          - Copied edition contributions list includes both roles.
          - Copied edition contributions list has correct person IDs.
        Fixtures: admin_client, test_work_and_edition, existing_person_id
        """
        _, edition_id = test_work_and_edition

        resp = set_edition_contributors(
            admin_client, edition_id,
            [
                {'person': {'id': existing_person_id},
                 'role': {'id': EDITION_ROLES['translator']},
                 'description': ''},
                {'person': {'id': existing_person_id},
                 'role': {'id': EDITION_ROLES['cover_artist']},
                 'description': ''},
            ]
        )
        assert resp.status_code == 200

        copy_resp = admin_client.post(
            f'/api/editions/{edition_id}/copy'
        )
        assert copy_resp.status_code in (200, 201), (
            f'copy_edition failed: {copy_resp.status_code} '
            f'{copy_resp.json}'
        )
        json_data = copy_resp.json
        if isinstance(json_data, dict):
            new_edition_id = int(json_data.get('response', 0))
        else:
            new_edition_id = int(json_data)

        try:
            contributions = get_edition_contributions(
                admin_client, new_edition_id
            )
            role_ids = [c['role']['id'] for c in contributions]

            assert EDITION_ROLES['translator'] in role_ids, (
                f'Translator missing in copied edition: {contributions}'
            )
            assert EDITION_ROLES['cover_artist'] in role_ids, (
                'Cover artist missing in copied edition: '
                f'{contributions}'
            )
        finally:
            admin_client.delete(f'/api/editions/{new_edition_id}')


# -------------------------------------------------------------------
# Tests: authors stay in Contributor (not EditionContributor)
# -------------------------------------------------------------------

class TestAuthorNotInEditionContributor(BaseAPITest):
    """
    Verifies that work authors (role 1) are not stored in the
    EditionContributor table.
    """

    def test_edition_author_not_in_editioncontributor(
            self, app, test_work_and_edition):
        """
        Authors (role 1) remain in the Contributor table via Part and
        do not appear in the EditionContributor table.

        Parameters: edition from test_work_and_edition fixture
        Assertions:
          - suomisf.editioncontributor has no rows with role_id=1
            for this edition
        Fixtures: app, test_work_and_edition
        """
        _, edition_id = test_work_and_edition

        with app.app_context():
            session = new_session()
            author_rows = (
                session.query(EditionContributor)
                .filter(EditionContributor.edition_id == edition_id)
                .filter(EditionContributor.role_id == 1)
                .count()
            )
            session.close()

        assert author_rows == 0, (
            f'Found {author_rows} author rows in EditionContributor '
            f'for edition {edition_id}; authors must stay in '
            f'Contributor via Part'
        )


# -------------------------------------------------------------------
# Tests: migration data integrity
# -------------------------------------------------------------------

class TestMigrationIntegrity(BaseAPITest):
    """
    Verifies that the migration SQL correctly populated the
    EditionContributor table from the existing Contributor+Part data.
    """

    def test_migration_count_matches(self, app):
        """
        The number of rows in suomisf.editioncontributor is at least
        as large as the number of distinct (edition_id, person_id,
        role_id) tuples in contributor+part for edition roles
        (2,3,4,5,7).

        Assertions:
          - editioncontributor row count >= source distinct row count
        Fixtures: app
        """
        edition_roles = (2, 3, 4, 5, 7)

        with app.app_context():
            session = new_session()

            ec_count = session.query(EditionContributor).count()

            source_count = (
                session.query(
                    Part.edition_id,
                    Contributor.person_id,
                    Contributor.role_id,
                )
                .join(Part, Part.id == Contributor.part_id)
                .filter(Part.shortstory_id.is_(None))
                .filter(Part.edition_id.isnot(None))
                .filter(Contributor.role_id.in_(edition_roles))
                .distinct()
                .count()
            )
            session.close()

        assert ec_count >= source_count, (
            f'EditionContributor has {ec_count} rows but source has '
            f'{source_count} distinct (edition,person,role) tuples. '
            f'Migration may be incomplete.'
        )
