"""
Public read paths no test reached (coverage plan step B4): front-page
random picks, the change logs, country and language filters, the people
list's filters and sorting, and setting a work's language on save.
"""
import pytest

from app.orm_decl import Language
from app.route_helpers import new_session

from .test_works import (TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD,
                         delete_test_work)

PERSON_ID = 1
NEW_LANGUAGE = 'B4 testikieli'


@pytest.fixture
def admin_client(api_client):
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


def test_frontpage_random_picks(api_client):
    """One work per genre category, never the same work twice."""
    response = api_client.get('/api/frontpage/random')
    assert response.status_code == 200
    picks = response.json
    assert 0 < len(picks) <= 6
    work_ids = [pick['work']['id'] for pick in picks]
    assert len(set(work_ids)) == len(work_ids)
    assert all(pick['work']['description'] for pick in picks)


@pytest.mark.parametrize('query', ['', '?period=30', '?table=Teos', '?period=30&table=Teos'])
def test_changes(api_client, query):
    response = api_client.get(f'/api/changes{query}')
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_changes_invalid_period_is_400(api_client):
    assert api_client.get('/api/changes?period=abc').status_code == 400


def test_person_changes(api_client):
    response = api_client.get(f'/api/person/{PERSON_ID}/changes')
    assert response.status_code == 200
    assert isinstance(response.json, list)


@pytest.mark.parametrize('path,expected', [
    ('/api/filter/countries/suo', 'Suomi'),
    ('/api/filter/languages/suo', 'suomi'),
])
def test_country_and_language_filters(api_client, path, expected):
    response = api_client.get(path)
    assert response.status_code == 200
    assert expected in [row['name'] for row in response.json]


# ---------------------------------------------------------------------------
# People list: the query string PrimeReact's lazy DataTable sends
# ---------------------------------------------------------------------------

def _people(api_client, query):
    response = api_client.get(f'/api/people/?first=0&rows=20&{query}')
    assert response.status_code == 200, response.json
    return response.json


def test_people_name_starts_with(api_client):
    body = _people(api_client, 'sortField=name&sortOrder=1'
                               '&filters_name_value=Asi&filters_name_matchMode=startsWith')
    names = [p['name'] for p in body['people']]
    assert names and all(n.lower().startswith('asi') for n in names)
    assert names == sorted(names, key=str.lower) or names == sorted(names)
    assert body['totalRecords'] >= len(names)


def test_people_sorted_by_birth_year_descending(api_client):
    body = _people(api_client, 'sortField=dob&sortOrder=-1'
                               '&filters_dob_value=1920&filters_dob_matchMode=gte')
    years = [p['dob'] for p in body['people']]
    assert years and years == sorted(years, reverse=True)
    assert all(y >= 1920 for y in years)


@pytest.mark.parametrize('mode,check', [
    ('lt', lambda y: y < 1920), ('lte', lambda y: y <= 1920),
    ('gt', lambda y: y > 1920), ('gte', lambda y: y >= 1920),
])
def test_people_birth_year_comparisons(api_client, mode, check):
    """lte and gte used to crash the list (no SQLAlchemy method by those names)."""
    body = _people(api_client, f'filters_dob_value=1920&filters_dob_matchMode={mode}')
    years = [p['dob'] for p in body['people']]
    assert years and all(check(y) for y in years)


def test_people_unknown_match_mode_is_400(api_client):
    response = api_client.get('/api/people/?first=0&rows=5'
                              '&filters_dob_value=1920&filters_dob_matchMode=between')
    assert response.status_code == 400


def test_people_unknown_filter_field_is_400(api_client):
    response = api_client.get('/api/people/?first=0&rows=5'
                              '&filters_password_value=x&filters_password_matchMode=equals')
    assert response.status_code == 400


def test_people_constraint_filter_form_is_400(api_client):
    """The constraint form used to crash the list with a 500."""
    response = api_client.get('/api/people/?first=0&rows=5&filters_name_operator=and'
                              '&filters_name_constraints_0_value=Asi'
                              '&filters_name_constraints_0_matchMode=startsWith')
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Work language on save
# ---------------------------------------------------------------------------

def test_work_save_with_new_language_creates_it(admin_client):
    """A language typed in the form arrives as a plain string and is created."""
    work_id = None
    try:
        response = admin_client.post('/api/works', data={'data': {
            'title': 'B4 kielitesti', 'orig_title': 'B4 kielitesti', 'pubyear': 2099,
            'work_type': {'id': 1}, 'language': NEW_LANGUAGE,
            'contributions': [{'person': {'id': PERSON_ID}, 'role': {'id': 1}}]}})
        assert response.status_code == 201, response.json
        work_id = int(response.data)
        work = admin_client.get(f'/api/works/{work_id}').json
        assert work['language_name']['name'] == NEW_LANGUAGE
    finally:
        if work_id:
            delete_test_work(admin_client, work_id)
        session = new_session()
        try:
            session.query(Language).filter_by(name=NEW_LANGUAGE).delete()
            session.commit()
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Front page latest additions
# ---------------------------------------------------------------------------

def test_frontpage_latest_shape(api_client):
    response = api_client.get('/api/frontpage/latest')
    assert response.status_code == 200
    latest = response.json
    assert len(latest) == 6
    assert set(latest[0]) == {'id', 'title', 'pubyear', 'editionnum', 'version',
                              'images', 'work'}
    assert set(latest[0]['work']) == {'id', 'title', 'author_str'}
    work_ids = [e['work']['id'] for e in latest]
    assert len(set(work_ids)) == len(work_ids)


@pytest.mark.parametrize('count', ['0', '21', 'x'])
def test_frontpage_latest_bad_count_is_400(api_client, count):
    assert api_client.get(f'/api/frontpage/latest?count={count}').status_code == 400


def test_frontpage_latest_groups_editions_of_a_work(admin_client):
    """Three new editions of one work are one entry, placed first (the
    newest addition), shown with the oldest edition that has a cover."""
    from app.orm_decl import Edition, EditionImage
    from .test_works import create_test_work
    work_id = create_test_work(admin_client, PERSON_ID, title='B4 kansitesti')
    session = new_session()
    extra = []
    try:
        first = session.query(Edition).filter_by(work_id=work_id).one()
        for n in (2, 3):
            edition = Edition(title='B4 kansitesti', pubyear=2099, work_id=work_id,
                              editionnum=n, version=1)
            session.add(edition)
            session.flush()
            extra.append(edition.id)
        session.add(EditionImage(edition_id=extra[0], image_src='/static/b4-cover.jpg'))
        session.commit()

        latest = admin_client.get('/api/frontpage/latest').json
        assert latest[0]['work']['id'] == work_id
        assert latest[0]['id'] == extra[0], 'oldest edition with a cover'
        assert [e['work']['id'] for e in latest].count(work_id) == 1
        assert first.id not in [e['id'] for e in latest]
    finally:
        session.rollback()
        session.query(EditionImage).filter(EditionImage.edition_id.in_(extra)).delete(
            synchronize_session=False)
        session.query(Edition).filter(Edition.id.in_(extra)).delete(
            synchronize_session=False)
        session.commit()
        session.close()
        delete_test_work(admin_client, work_id)
