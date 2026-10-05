"""
Saving works and editions the way the admin forms do: every field and
relation filled in, read back, changed, and deleted.

Covers the save paths the existing CRUD tests skip (series given as a new
name or an id, new and existing tags, links, genres, language, description
attribution, validation errors). Everything a test creates, including new
tags, series and languages, is removed afterwards.
"""
import pytest

from app.orm_decl import Bookseries, Language, Tag
from app.route_helpers import new_session

from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD

PERSON_ID = 1
NAME = 'B6 tallennustesti'
NEW_SERIES = 'B6 testisarja'
NEW_TAG = 'b6 uusi asiasana'
NEW_LANGUAGE = 'b6 testikieli'


@pytest.fixture
def admin_client(api_client):
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


def _delete_by_name(model, name):
    session = new_session()
    try:
        session.query(model).filter_by(name=name).delete()
        session.commit()
    finally:
        session.close()


def _existing(model, exclude_name=None):
    session = new_session()
    try:
        query = session.query(model).order_by(model.id)
        rows = query.limit(3).all()
        return [r for r in rows if r.name != exclude_name]
    finally:
        session.close()


def _work_payload(**overrides):
    data = {
        'title': NAME, 'subtitle': 'alaotsikko', 'orig_title': 'B6 Save Test',
        'pubyear': 2099, 'work_type': {'id': 1},
        'contributions': [{'person': {'id': PERSON_ID}, 'role': {'id': 1}}],
        'description': '<p>B6 kuvaus</p>', 'descr_attr': 'B6 lähde',
        'misc': 'B6 muuta', 'imported_string': 'B6 tuonti',
        'bookseries': NEW_SERIES, 'bookseriesnum': '3', 'bookseriesorder': 2,
        'language': NEW_LANGUAGE,
        'genres': [{'id': 1}],
        'links': [{'link': 'https://example.invalid/b6', 'description': 'B6'}],
    }
    data.update(overrides)
    return {'data': data}


@pytest.fixture
def cleanup_names(app):
    yield
    _delete_by_name(Tag, NEW_TAG)
    _delete_by_name(Bookseries, NEW_SERIES)
    _delete_by_name(Language, NEW_LANGUAGE)


# ---------------------------------------------------------------------------
# Works
# ---------------------------------------------------------------------------

def test_work_full_create_update_delete(admin_client, cleanup_names):
    existing_tag = _existing(Tag, exclude_name=NEW_TAG)[0]
    payload = _work_payload(tags=[{'id': existing_tag.id, 'name': existing_tag.name},
                                  {'id': 0, 'name': NEW_TAG}])
    response = admin_client.post('/api/works', data=payload)
    assert response.status_code == 201, response.json
    work_id = int(response.data)
    try:
        work = admin_client.get(f'/api/works/{work_id}').json
        assert work['subtitle'] == 'alaotsikko' and work['descr_attr'] == 'B6 lähde'
        assert work['bookseries']['name'] == NEW_SERIES
        assert work['bookseriesnum'] == '3' and work['bookseriesorder'] == 2
        assert work['language_name']['name'] == NEW_LANGUAGE
        assert {t['name'] for t in work['tags']} == {existing_tag.name, NEW_TAG}
        assert [g['id'] for g in work['genres']] == [1]
        assert [link['link'] for link in work['links']] == ['https://example.invalid/b6']

        # Change every relation: series cleared, tags/genres/links replaced,
        # language set to an existing one.
        other_tag = _existing(Tag, exclude_name=NEW_TAG)[1]
        english = _existing(Language)[0]
        update = dict(work, bookseries=None, bookseriesnum='', bookseriesorder=None,
                      tags=[{'id': other_tag.id, 'name': other_tag.name}],
                      genres=[{'id': 2}], links=[], language={'id': english.id},
                      descr_attr='B6 lähde 2', imported_string='B6 tuonti 2')
        response = admin_client.put('/api/works', data={'data': update})
        assert response.status_code == 200, response.json
        work = admin_client.get(f'/api/works/{work_id}').json
        assert work['bookseries'] is None
        assert [t['id'] for t in work['tags']] == [other_tag.id]
        assert [g['id'] for g in work['genres']] == [2]
        assert work['links'] == []
        assert work['language_name']['id'] == english.id
        assert work['descr_attr'] == 'B6 lähde 2'

        # Set the series by id this time.
        series = _existing(Bookseries)[0]
        update = dict(work, bookseries={'id': series.id})
        assert admin_client.put('/api/works', data={'data': update}).status_code == 200
        assert admin_client.get(f'/api/works/{work_id}').json['bookseries']['id'] == series.id
    finally:
        assert admin_client.delete(f'/api/works/{work_id}').status_code == 200
    assert admin_client.get(f'/api/works/{work_id}').status_code == 404


def test_work_save_errors(admin_client, cleanup_names):
    no_author = _work_payload(contributions=[])
    assert admin_client.post('/api/works', data=no_author).status_code == 400

    bad_link = _work_payload(bookseries=None, language=None,
                             links=[{'description': 'no address'}])
    assert admin_client.post('/api/works', data=bad_link).status_code == 400
    bad_genre = _work_payload(bookseries=None, language=None, genres=[{'name': 'x'}])
    assert admin_client.post('/api/works', data=bad_genre).status_code == 400
    # A refused work must not be left half-created (it used to be saved
    # with its first edition before the links were checked).
    session = new_session()
    try:
        from app.orm_decl import Work
        assert session.query(Work).filter_by(title=NAME).count() == 0
    finally:
        session.close()

    response = admin_client.post('/api/works', data=_work_payload(bookseries=None))
    assert response.status_code == 201, response.json
    work_id = int(response.data)
    try:
        work = admin_client.get(f'/api/works/{work_id}').json
        empty_title = dict(work, title='')
        assert admin_client.put('/api/works', data={'data': empty_title}).status_code == 400
        missing_series = dict(work, bookseries={'id': 999999999})
        assert admin_client.put('/api/works',
                                data={'data': missing_series}).status_code == 400
        missing_work = dict(work, id=999999999)
        assert admin_client.put('/api/works', data={'data': missing_work}).status_code == 404
    finally:
        admin_client.delete(f'/api/works/{work_id}')


# ---------------------------------------------------------------------------
# Editions
# ---------------------------------------------------------------------------

NEW_PUBSERIES = 'B6 kustantajan sarja'
VALID_ISBN = '9789510000014'


@pytest.fixture
def work_with_edition(admin_client, cleanup_names):
    """A fresh work (which brings its first edition); removed afterwards
    with all its editions and the publisher series a test creates."""
    response = admin_client.post('/api/works', data=_work_payload(
        bookseries=None, language=None, links=[], genres=[]))
    assert response.status_code == 201, response.json
    work_id = int(response.data)
    yield work_id
    for edition in admin_client.get(f'/api/works/{work_id}').json.get('editions', [])[1:]:
        admin_client.delete(f"/api/editions/{edition['id']}")
    admin_client.delete(f'/api/works/{work_id}')
    from app.orm_decl import Pubseries
    _delete_by_name(Pubseries, NEW_PUBSERIES)


def _ids(model):
    session = new_session()
    try:
        return [r.id for r in session.query(model).order_by(model.id).limit(3)]
    finally:
        session.close()


def test_edition_full_create_and_update(admin_client, work_with_edition):
    from app.orm_decl import BindingType, Format, Pubseries
    publisher_id = 387
    binding_ids, format_ids = _ids(BindingType), _ids(Format)
    response = admin_client.post('/api/editions', data={'data': {
        'work_id': work_with_edition, 'title': NAME, 'subtitle': 'B6 ala',
        'pubyear': 2099, 'editionnum': 2, 'version': 2,
        'publisher': {'id': publisher_id}, 'pubseries': NEW_PUBSERIES,
        'pubseriesnum': '7', 'isbn': VALID_ISBN, 'coll_info': 'B6 kokoelma',
        'pages': 321, 'binding': {'id': binding_ids[1]}, 'format': {'id': format_ids[0]},
        'size': 20, 'dustcover': 2, 'coverimage': 2, 'printedin': 'Porvoo',
        'misc': 'B6 muuta', 'imported_string': 'B6 tuonti', 'verified': True,
        'contributors': [{'person': {'id': PERSON_ID}, 'role': {'id': 2},
                          'description': None}],
    }})
    assert response.status_code in (200, 201), response.json
    edition_id = int(response.data)
    edition = admin_client.get(f'/api/editions/{edition_id}').json
    assert (edition['version'], edition['editionnum'], edition['isbn']) == (2, 2, VALID_ISBN)
    assert edition['pubseries']['name'] == NEW_PUBSERIES and edition['pubseriesnum'] == 7
    assert (edition['pages'], edition['size'], edition['printedin']) == (321, 20, 'Porvoo')
    assert edition['dustcover'] == 2 and edition['coverimage'] == 2 and edition['verified']
    assert 2 in [c['role']['id'] for c in edition['contributions']]

    existing_pubseries = _ids(Pubseries)[0]
    update = dict(edition, version=3, isbn='', pages=100, size=21, printedin='',
                  binding={'id': binding_ids[0]}, pubseries={'id': existing_pubseries},
                  pubseriesnum=None, dustcover=3, coverimage=3, misc='', verified=False,
                  imported_string='B6 tuonti 2')
    response = admin_client.put('/api/editions', data={'data': update})
    assert response.status_code == 200, response.json
    edition = admin_client.get(f'/api/editions/{edition_id}').json
    assert edition['version'] == 3 and edition['isbn'] is None
    assert edition['pubseries']['id'] == existing_pubseries
    assert (edition['pages'], edition['size'], edition['printedin']) == (100, 21, None)
    assert edition['binding']['id'] == binding_ids[0]
    assert (edition['dustcover'], edition['coverimage'], edition['verified']) == (3, 3, False)


@pytest.mark.parametrize('field,value', [
    ('title', ''), ('pubyear', ''), ('version', 'x'), ('isbn', '123'),
    ('pages', -5), ('size', 'iso'), ('pubseriesnum', 'x'), ('dustcover', 7),
    ('coverimage', 9), ('pubseries', {'id': 999999999}),
])
def test_edition_update_rejects_invalid_values(admin_client, work_with_edition, field, value):
    """Each invalid value is refused and nothing is saved. A missing
    publisher series used to answer 200 while discarding the whole save."""
    edition = admin_client.get(f'/api/works/{work_with_edition}').json['editions'][0]
    edition = admin_client.get(f"/api/editions/{edition['id']}").json
    update = dict(edition, misc='B6 ei tallennu', **{field: value})
    response = admin_client.put('/api/editions', data={'data': update})
    assert response.status_code == 400, response.json
    after = admin_client.get(f"/api/editions/{edition['id']}").json
    assert after['misc'] != 'B6 ei tallennu'


def test_edition_create_errors(admin_client, work_with_edition):
    base = {'work_id': work_with_edition, 'title': NAME, 'pubyear': 2099,
            'editionnum': 1, 'publisher': {'id': 387}}
    for change in ({'work_id': 'x'}, {'pubyear': 'x'}, {'isbn': '123'}):
        response = admin_client.post('/api/editions', data={'data': dict(base, **change)})
        assert response.status_code == 400, (change, response.json)
    no_year = {k: v for k, v in base.items() if k != 'pubyear'}
    assert admin_client.post('/api/editions', data={'data': no_year}).status_code == 400


# ---------------------------------------------------------------------------
# Awards given to a work, person or story (the awarded form)
# ---------------------------------------------------------------------------

NEW_AWARD = 'B6 testipalkinto'


def _work_category_and_award():
    from app.orm_decl import Award, AwardCategories, AwardCategory
    session = new_session()
    try:
        row = session.query(AwardCategories.award_id, AwardCategories.category_id)\
            .join(AwardCategory, AwardCategory.id == AwardCategories.category_id)\
            .filter(AwardCategory.type == 1).first()
        award = session.query(Award).get(row.award_id)
        return {'id': award.id, 'name': award.name}, {'id': row.category_id}
    finally:
        session.close()


def _awarded(client, work_id):
    response = client.get(f'/api/works/{work_id}/awarded')
    assert response.status_code == 200
    return response.json


def test_awarded_add_change_remove_for_work(admin_client, work_with_edition):
    award, category = _work_category_and_award()
    entry = {'id': 0, 'year': 2099, 'award': award, 'category': category,
             'work': {'id': work_with_edition}, 'person': {'id': 0}, 'story': {'id': 0}}
    try:
        body = {'id': work_with_edition, 'type': 1, 'awards': [entry]}
        assert admin_client.post('/api/awarded', data=body).status_code == 200
        saved = _awarded(admin_client, work_with_edition)
        assert [(a['year'], a['award']['id']) for a in saved] == [(2099, award['id'])]

        changed = dict(entry, id=saved[0]['id'], year=2098)
        body = {'id': work_with_edition, 'type': 1, 'awards': [changed]}
        assert admin_client.post('/api/awarded', data=body).status_code == 200
        assert [a['year'] for a in _awarded(admin_client, work_with_edition)] == [2098]

        # A new award typed by name is created with the work categories.
        by_name = dict(entry, award=NEW_AWARD)
        body = {'id': work_with_edition, 'type': 1, 'awards': [changed, by_name]}
        assert admin_client.post('/api/awarded', data=body).status_code == 200
        names = {a['award']['name'] for a in _awarded(admin_client, work_with_edition)}
        assert NEW_AWARD in names
        from app.orm_decl import Award, AwardCategories, AwardCategory
        session = new_session()
        try:
            new_award = session.query(Award).filter_by(name=NEW_AWARD).one()
            types = {c.type for c in session.query(AwardCategory)
                     .join(AwardCategories, AwardCategories.category_id == AwardCategory.id)
                     .filter(AwardCategories.award_id == new_award.id)}
        finally:
            session.close()
        assert types == {1}, 'new award should get the work (type 1) categories'

        body = {'id': work_with_edition, 'type': 1, 'awards': []}
        assert admin_client.post('/api/awarded', data=body).status_code == 200
        assert _awarded(admin_client, work_with_edition) == []
    finally:
        admin_client.post('/api/awarded', data={'id': work_with_edition, 'type': 1,
                                                'awards': []})
        from app.orm_decl import Award, AwardCategories
        session = new_session()
        try:
            for a in session.query(Award).filter_by(name=NEW_AWARD).all():
                session.query(AwardCategories).filter_by(award_id=a.id).delete()
                session.delete(a)
            session.commit()
        finally:
            session.close()


def test_awarded_rejects_bad_input(admin_client):
    body = {'id': 1, 'type': None, 'awards': []}
    assert admin_client.post('/api/awarded', data=body).status_code == 400
    missing_year = {'id': 0, 'award': {'id': 1}, 'category': {'id': 1}, 'work': {'id': 1}}
    body = {'id': 1, 'type': 1, 'awards': [missing_year]}
    assert admin_client.post('/api/awarded', data=body).status_code == 400


# ---------------------------------------------------------------------------
# Short stories
# ---------------------------------------------------------------------------

STORY_LANGUAGE = 'b6 jiddiš'   # contains "id": used to crash language handling


def _story_payload(**overrides):
    data = {'title': NAME, 'orig_title': 'B6 Story', 'pubyear': 2099,
            'type': {'id': 1}, 'genres': [], 'tags': [],
            'contributors': [{'person': {'id': PERSON_ID}, 'role': {'id': 1},
                              'description': None}]}
    data.update(overrides)
    return {'data': data}


def test_story_language_create_update_and_errors(admin_client):
    response = admin_client.post('/api/shorts', data=_story_payload(lang=STORY_LANGUAGE))
    assert response.status_code in (200, 201), response.json
    story_id = int(response.data)
    try:
        story = admin_client.get(f'/api/shorts/{story_id}').json
        assert story['lang']['name'] == STORY_LANGUAGE

        english = _existing(Language)[0]
        update = dict(story, lang={'id': english.id, 'name': english.name})
        assert admin_client.put('/api/shorts', data={'data': update}).status_code == 200
        assert admin_client.get(f'/api/shorts/{story_id}').json['lang']['id'] == english.id

        update = dict(story, lang='')
        assert admin_client.put('/api/shorts', data={'data': update}).status_code == 200
        assert admin_client.get(f'/api/shorts/{story_id}').json['lang'] is None

        for bad in ({'title': ''}, {'id': 'x'}):
            response = admin_client.put('/api/shorts', data={'data': dict(story, **bad)})
            assert response.status_code == 400, (bad, response.json)
        missing = dict(story, id=999999999)
        assert admin_client.put('/api/shorts', data={'data': missing}).status_code in (400, 404)
    finally:
        admin_client.delete(f'/api/shorts/{story_id}')
        _delete_by_name(Language, STORY_LANGUAGE)


def test_story_add_requires_title(admin_client):
    response = admin_client.post('/api/shorts', data=_story_payload(title=''))
    assert response.status_code == 400
