"""
Work link source maintenance (admin): list, rename/combine and delete.

Each test adds its own links with made-up sources to one work and removes
them afterwards, also when an assertion fails.
"""
import pytest

from app.orm_decl import WorkLink
from app.route_helpers import new_session

TEST_ADMIN_NAME = 'Test Admin'
TEST_ADMIN_PASSWORD = 'testadminpass123'
WORK_ID = 1
SRC_A = 'Testilähde A'
SRC_TYPO = 'Testilähe A'
LINK = 'https://example.invalid/worklink-sources'


def _login(client):
    resp = client.post('/api/login', json={'username': TEST_ADMIN_NAME,
                                           'password': TEST_ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.get_json()
    return {'Authorization': f"Bearer {resp.get_json()['access_token']}"}


@pytest.fixture
def admin(client):
    return _login(client)


@pytest.fixture
def test_links():
    """Two links with the correct source and one with a typo."""
    session = new_session()
    for i, source in enumerate([SRC_A, SRC_A, SRC_TYPO]):
        session.add(WorkLink(work_id=WORK_ID, link=f'{LINK}/{i}',
                             description=source))
    session.commit()
    session.close()
    yield
    session = new_session()
    session.query(WorkLink).filter(WorkLink.link.like(f'{LINK}%')).delete(
        synchronize_session=False)
    session.commit()
    session.close()


def _sources(client, admin):
    resp = client.get('/api/worklinks/sources', headers=admin)
    assert resp.status_code == 200
    return {r['source']: r for r in resp.get_json()}


def test_sources_require_admin(client):
    assert client.get('/api/worklinks/sources').status_code == 401


def test_list_sources_and_links(client, admin, test_links):
    sources = _sources(client, admin)
    assert sources[SRC_A]['count'] == 2
    assert sources[SRC_A]['works'] == 1
    assert sources[SRC_TYPO]['count'] == 1

    resp = client.get('/api/worklinks/sources/links',
                      query_string={'source': SRC_TYPO}, headers=admin)
    assert resp.status_code == 200
    links = resp.get_json()
    assert [x['link'] for x in links] == [f'{LINK}/2']
    assert links[0]['work_id'] == WORK_ID


def test_merge_typo_into_source(client, admin, test_links):
    resp = client.post('/api/worklinks/sources/merge', headers=admin,
                       json={'sources': [SRC_A, SRC_TYPO],
                             'target': f'  {SRC_A} '})
    assert resp.status_code == 200
    # The links that already had the target are not counted.
    assert resp.get_json() == {'updated': 1}
    sources = _sources(client, admin)
    assert SRC_TYPO not in sources
    assert sources[SRC_A]['count'] == 3


def test_merge_requires_target(client, admin, test_links):
    resp = client.post('/api/worklinks/sources/merge', headers=admin,
                       json={'sources': [SRC_TYPO], 'target': '  '})
    assert resp.status_code == 400
    assert _sources(client, admin)[SRC_TYPO]['count'] == 1


def test_delete_source(client, admin, test_links):
    resp = client.post('/api/worklinks/sources/delete', headers=admin,
                       json={'source': SRC_TYPO})
    assert resp.status_code == 200
    assert resp.get_json() == {'deleted': 1}
    sources = _sources(client, admin)
    assert SRC_TYPO not in sources
    assert sources[SRC_A]['count'] == 2
