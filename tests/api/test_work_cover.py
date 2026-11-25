"""
SuomiSF API: the work's main cover (Work.cover_image_id, migration 053)

An admin picks which of the work's edition covers the work page shows
(PUT /api/works/<id>/cover); GET /api/works/<id> returns the choice as
cover_image_id, null meaning the page chooses by itself.
"""

import pytest
from sqlalchemy import text

from app.route_helpers import new_session

from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD

TEST_USER_NAME = 'Test User'
TEST_USER_PASSWORD = 'testpassword123'


@pytest.fixture
def admin_client(api_client):
    """An API client logged in as admin."""
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def covers():
    """A work with at least two covers, and a cover of another work."""
    session = new_session()
    try:
        row = session.execute(text(
            'SELECT e.work_id, array_agg(i.id ORDER BY i.id) '
            'FROM suomisf.editionimage i '
            'JOIN suomisf.edition e ON e.id = i.edition_id '
            'GROUP BY e.work_id HAVING count(*) >= 2 '
            'ORDER BY e.work_id LIMIT 1')).first()
        assert row, 'test data has no work with two covers'
        work_id, image_ids = row[0], list(row[1])
        other = session.execute(text(
            'SELECT i.id FROM suomisf.editionimage i '
            'JOIN suomisf.edition e ON e.id = i.edition_id '
            'WHERE e.work_id <> :w ORDER BY i.id LIMIT 1'),
            {'w': work_id}).scalar()
    finally:
        session.close()
    yield {'work_id': work_id, 'image_ids': image_ids, 'other': other}
    # Leave the work as it was for the other tests.
    session = new_session()
    try:
        session.execute(text(
            'UPDATE suomisf.work SET cover_image_id = NULL WHERE id = :w'),
            {'w': work_id})
        session.commit()
    finally:
        session.close()


def _cover(client, work_id):
    response = client.get(f'/api/works/{work_id}')
    response.assert_status(200)
    return response.data['cover_image_id']


class TestWorkCover:
    """PUT /api/works/<id>/cover and cover_image_id on the work."""

    def test_default_is_null(self, api_client, covers):
        assert _cover(api_client, covers['work_id']) is None

    def test_admin_sets_and_clears_the_cover(self, admin_client, covers):
        work_id, second = covers['work_id'], covers['image_ids'][1]
        response = admin_client.put(
            f'/api/works/{work_id}/cover', data={'image_id': second})
        response.assert_status(200)
        assert _cover(admin_client, work_id) == second

        response = admin_client.put(
            f'/api/works/{work_id}/cover', data={'image_id': None})
        response.assert_status(200)
        assert _cover(admin_client, work_id) is None

    def test_change_is_logged(self, admin_client, covers):
        work_id, second = covers['work_id'], covers['image_ids'][1]
        admin_client.put(
            f'/api/works/{work_id}/cover', data={'image_id': second}
        ).assert_status(200)
        session = new_session()
        try:
            row = session.execute(text(
                "SELECT action, old_value FROM suomisf.log "
                "WHERE table_name = 'Teos' AND table_id = :w "
                "AND field_name = 'Pääkuva' ORDER BY id DESC LIMIT 1"),
                {'w': work_id}).first()
        finally:
            session.close()
        assert row is not None
        assert row[0] == 'Päivitys'
        assert row[1] == 'oletus'

    def test_cover_of_another_work_is_rejected(self, admin_client, covers):
        response = admin_client.put(
            f"/api/works/{covers['work_id']}/cover",
            data={'image_id': covers['other']})
        response.assert_status(400)
        assert _cover(admin_client, covers['work_id']) is None

    def test_unknown_image_and_work(self, admin_client, covers):
        admin_client.put(
            f"/api/works/{covers['work_id']}/cover",
            data={'image_id': 999999999}).assert_status(400)
        admin_client.put(
            '/api/works/999999999/cover',
            data={'image_id': None}).assert_status(404)

    def test_bad_input(self, admin_client, covers):
        path = f"/api/works/{covers['work_id']}/cover"
        admin_client.put(path, data={}).assert_status(400)
        admin_client.put(path, data={'image_id': 'x'}).assert_status(400)
        admin_client.put(path, data={'image_id': True}).assert_status(400)
        admin_client.put(
            '/api/works/abc/cover', data={'image_id': None}
        ).assert_status(400)

    def test_only_admins(self, api_client, covers):
        path = f"/api/works/{covers['work_id']}/cover"
        body = {'image_id': covers['image_ids'][1]}
        assert api_client.put(path, data=body).status_code == 401
        api_client.login(TEST_USER_NAME, TEST_USER_PASSWORD)
        assert api_client.put(path, data=body).status_code in (401, 403)
        assert _cover(api_client, covers['work_id']) is None
