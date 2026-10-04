"""
Admin create -> read -> change -> delete round trips for entities whose
create/delete paths had no tests (coverage plan step B2).

Every test removes what it created, through the API where a route exists
and directly in the database otherwise, also when an assertion fails.

Uses the raw Flask test `client` with Bearer headers, as
test_pricing_auth.py does (see its docstring for why).
"""
import io
import os

import pytest

from app import app as flask_app
from app.orm_decl import (Bookseries, EditionImage, Issue, IssueImage,
                          IssueTag, PersonLink, PersonTag, Publisher)
from app.route_helpers import new_session

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'

MAGAZINE_ID = 12
PERSON_ID = 1
TAG_ID = 1
EDITION_ID = 86
EDITION_WITH_SHORTS_ID = 242
TEST_LINK = 'https://example.invalid/b2-roundtrip'
TEST_NAME = 'B2 roundtrip test'

# A 1x1 JPEG (uploads accept .jpg/.jpeg only).
JPEG = bytes.fromhex(
    'ffd8ffe000104a46494600010100000100010000ffdb004300100b0c0e0c0a100e0d0e121110'
    '1318281a181616183123251d283a333d3c3933383740485c4e404457453738506d51575f6267'
    '68673e4d71797064785c656763ffdb0043011112121815182f1a1a2f63423842636363636363'
    '6363636363636363636363636363636363636363636363636363636363636363636363636363'
    '636363636363ffc00011080001000103012200021101031101ffc4001f000001050101010101'
    '0100000000000000000102030405060708090a0bffc400b51000020103030204030505040400'
    '00017d01020300041105122131410613516107227114328191a1082342b1c11552d1f0243362'
    '7282090a161718191a25262728292a3435363738393a434445464748494a535455565758595a'
    '636465666768696a737475767778797a838485868788898a92939495969798999aa2a3a4a5a6'
    'a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7'
    'e8e9eaf1f2f3f4f5f6f7f8f9faffc4001f010003010101010101010101000000000000010203'
    '0405060708090a0bffc400b51100020102040403040705040400010277000102031104052131'
    '061241510761711322328108144291a1b1c109233352f0156272d10a162434e125f11718191a'
    '262728292a35363738393a434445464748494a535455565758595a636465666768696a737475'
    '767778797a82838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7'
    'b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae2e3e4e5e6e7e8e9eaf2f3f4f5f6f7f8f9'
    'faffda000c03010002110311003f00c7a28a2b84fa83ffd9')


def _login(client):
    resp = client.post('/api/login', json={'username': TEST_ADMIN_NAME,
                                           'password': TEST_ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.get_json()
    return {'Authorization': f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def admin(client):
    return _login(client)


def _id_from(resp):
    """Create endpoints answer with the new id, as a bare value or in a dict."""
    body = resp.get_json()
    if isinstance(body, dict):
        body = body.get('id', body.get('response'))
    return int(body)


def _delete_rows(model, **filters):
    session = new_session()
    try:
        session.query(model).filter_by(**filters).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def upload_dirs(app):
    """Uploads must go to the temporary folders conftest sets, never to the
    real app/static/images ones."""
    static = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static'))
    for key in ('BOOKCOVER_SAVELOC', 'MAGAZINECOVER_SAVELOC'):
        location = os.path.realpath(flask_app.config[key])
        assert not location.startswith(static), f'{key} is {location}'


# ---------------------------------------------------------------------------
# Publisher and book series
# ---------------------------------------------------------------------------

def test_publisher_create_read_delete(client, admin):
    try:
        resp = client.post('/api/publishers', headers=admin, json={'data': {
            'name': TEST_NAME, 'fullname': f'{TEST_NAME} Oy', 'description': None,
            'image_src': None, 'image_attr': None, 'links': []}})
        assert resp.status_code in (200, 201), resp.get_json()
        publisher_id = _id_from(resp)

        got = client.get(f'/api/publishers/{publisher_id}')
        assert got.status_code == 200
        assert got.get_json()['name'] == TEST_NAME

        assert client.delete(f'/api/publishers/{publisher_id}', headers=admin).status_code == 200
        assert client.get(f'/api/publishers/{publisher_id}').status_code == 404
    finally:
        _delete_rows(Publisher, name=TEST_NAME)


def test_publisher_create_requires_name(client, admin):
    resp = client.post('/api/publishers', headers=admin, json={'data': {
        'name': '', 'fullname': '', 'description': None,
        'image_src': None, 'image_attr': None, 'links': []}})
    assert resp.status_code == 400


def test_bookseries_create_read_delete(client, admin):
    try:
        resp = client.post('/api/bookseries', headers=admin, json={'data': {
            'name': TEST_NAME, 'orig_name': None, 'important': False,
            'description': None, 'partof': None}})
        assert resp.status_code in (200, 201), resp.get_json()
        series_id = _id_from(resp)

        got = client.get(f'/api/bookseries/{series_id}')
        assert got.status_code == 200
        assert got.get_json()['name'] == TEST_NAME

        assert client.delete(f'/api/bookseries/{series_id}', headers=admin).status_code == 200
        assert client.get(f'/api/bookseries/{series_id}').status_code == 404
    finally:
        _delete_rows(Bookseries, name=TEST_NAME)


# ---------------------------------------------------------------------------
# Magazine issue, with a tag and a cover image
# ---------------------------------------------------------------------------

def test_issue_create_tag_image_delete(client, admin, upload_dirs):
    issue_id = None
    try:
        resp = client.post('/api/issues', headers=admin, json={
            'magazine_id': MAGAZINE_ID, 'number': 9999, 'year': 2099,
            'title': TEST_NAME})
        assert resp.status_code in (200, 201), resp.get_json()
        issue_id = _id_from(resp)

        got = client.get(f'/api/issues/{issue_id}')
        assert got.status_code == 200
        assert got.get_json()['title'] == TEST_NAME

        tag_url = f'/api/issue/{issue_id}/tags/{TAG_ID}'
        tags_url = f'/api/issues/{issue_id}/tags'
        assert client.put(tag_url, headers=admin).status_code == 200
        assert TAG_ID in [t['id'] for t in client.get(tags_url).get_json()]
        assert client.delete(tag_url, headers=admin).status_code == 200
        assert TAG_ID not in [t['id'] for t in client.get(tags_url).get_json()]

        resp = client.post(f'/api/issues/{issue_id}/images', headers=admin,
                           data={'file': (io.BytesIO(JPEG), 'b2-issue-cover.jpg')},
                           content_type='multipart/form-data')
        assert resp.status_code in (200, 201), resp.get_json()
        images = client.get(f'/api/issues/{issue_id}').get_json()['images']
        assert len(images) == 1
        resp = client.delete(f"/api/issues/{issue_id}/images/{images[0]['id']}", headers=admin)
        assert resp.status_code == 200
        assert client.get(f'/api/issues/{issue_id}').get_json()['images'] == []

        assert client.delete(f'/api/issues/{issue_id}', headers=admin).status_code == 200
        assert client.get(f'/api/issues/{issue_id}').status_code == 404
        issue_id = None
    finally:
        if issue_id:
            _delete_rows(IssueTag, issue_id=issue_id)
            _delete_rows(IssueImage, issue_id=issue_id)
            _delete_rows(Issue, id=issue_id)


def test_issue_create_requires_magazine(client, admin):
    resp = client.post('/api/issues', headers=admin, json={'number': 1})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Person links and tags
# ---------------------------------------------------------------------------

def test_person_link_add_replaces_same_description(client, admin):
    """One link per description: a second link with the same description
    replaces the first."""
    url = f'/api/person/{PERSON_ID}/links'
    second = TEST_LINK + '-2'
    try:
        resp = client.post(url, headers=admin, json={'link': TEST_LINK,
                                                     'description': TEST_NAME})
        assert resp.status_code == 201, resp.get_json()
        links = client.get(f'/api/people/{PERSON_ID}').get_json()['links']
        assert TEST_LINK in [link['link'] for link in links]

        resp = client.post(url, headers=admin, json={'link': second,
                                                     'description': TEST_NAME})
        assert resp.status_code == 201
        links = client.get(f'/api/people/{PERSON_ID}').get_json()['links']
        mine = [link['link'] for link in links if link['description'] == TEST_NAME]
        assert mine == [second]

        assert client.post(url, headers=admin, json={'description': 'x'}).status_code == 400
        assert client.post('/api/person/999999999/links', headers=admin,
                           json={'link': TEST_LINK}).status_code == 404
    finally:
        _delete_rows(PersonLink, person_id=PERSON_ID, description=TEST_NAME)


def _person_has_tag():
    session = new_session()
    try:
        return session.query(PersonTag).filter_by(person_id=PERSON_ID,
                                                  tag_id=TAG_ID).count() > 0
    finally:
        session.close()


def test_person_tag_add_and_remove(client, admin):
    url = f'/api/person/{PERSON_ID}/tags/{TAG_ID}'
    assert not _person_has_tag(), 'test person already has the test tag'
    try:
        assert client.put(url, headers=admin).status_code == 200
        assert _person_has_tag()
        assert client.delete(url, headers=admin).status_code == 200
        assert not _person_has_tag()
        assert client.put(f'/api/person/{PERSON_ID}/tags/999999999',
                          headers=admin).status_code == 404
    finally:
        _delete_rows(PersonTag, person_id=PERSON_ID, tag_id=TAG_ID)


# ---------------------------------------------------------------------------
# Edition cover image and short story list
# ---------------------------------------------------------------------------

def test_edition_image_upload_and_delete(client, admin, upload_dirs):
    before = {i['id'] for i in client.get(f'/api/editions/{EDITION_ID}').get_json()['images']}
    try:
        resp = client.post(f'/api/editions/{EDITION_ID}/images', headers=admin,
                           data={'file': (io.BytesIO(JPEG), 'b2.edition-cover.jpg')},
                           content_type='multipart/form-data')
        assert resp.status_code in (200, 201), resp.get_json()
        images = client.get(f'/api/editions/{EDITION_ID}').get_json()['images']
        new = [i for i in images if i['id'] not in before]
        assert len(new) == 1
        resp = client.delete(f"/api/editions/{EDITION_ID}/images/{new[0]['id']}", headers=admin)
        assert resp.status_code == 200
        after = {i['id'] for i in client.get(f'/api/editions/{EDITION_ID}').get_json()['images']}
        assert after == before
    finally:
        session = new_session()
        try:
            session.query(EditionImage).filter(
                EditionImage.edition_id == EDITION_ID,
                EditionImage.image_src.like('%b2.edition-cover%')).delete(
                    synchronize_session=False)
            session.commit()
        finally:
            session.close()


@pytest.mark.parametrize('name', ['b2.txt', 'b2.png', 'b2.jpg.exe', 'b2'])
def test_edition_image_rejects_other_types(client, admin, upload_dirs, name):
    resp = client.post(f'/api/editions/{EDITION_ID}/images', headers=admin,
                       data={'file': (io.BytesIO(JPEG), name)},
                       content_type='multipart/form-data')
    assert resp.status_code == 400


def test_edition_shorts_save_same_list_is_noop(client, admin):
    """Saving an edition's current story list back leaves it unchanged."""
    url = f'/api/editions/{EDITION_WITH_SHORTS_ID}/shorts'
    before = client.get(url).get_json()
    ids = [s['id'] for s in before]
    assert ids, 'test edition should have short stories'
    resp = client.put(url, headers=admin, json=ids)
    assert resp.status_code == 200, resp.get_json()
    assert [s['id'] for s in client.get(url).get_json()] == ids


def test_edition_shorts_save_requires_admin_token(client):
    resp = client.put(f'/api/editions/{EDITION_WITH_SHORTS_ID}/shorts', json=[])
    assert resp.status_code == 401
