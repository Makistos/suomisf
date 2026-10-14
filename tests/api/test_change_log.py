"""
Every change to the catalogue leaves a row in the change log (suomisf.log)
saying who changed what and when.

Each test makes a change through the API and checks the log rows written
since it started: the table, the row id, the action, the field and that
the user and date are set. Everything a test creates is removed afterwards.
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.orm_decl import (Bookseries, Magazine, Person, PersonLink,
                          Publisher, Pubseries, ShortStory, Tag, User)
from app.route_helpers import new_session

from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD

NAME = 'Lokitesti'
PERSON_ID = 1
WORK_ID = 1
MAGAZINE_ID = 12
EDITION_ID = 86


@pytest.fixture
def admin_client(api_client):
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.fixture
def admin_id(app):  # pylint: disable=unused-argument
    session = new_session()
    try:
        return session.query(User.id)\
            .filter(User.name == TEST_ADMIN_NAME).scalar()
    finally:
        session.close()


class LogWatch:
    """The log rows written after the watch was started."""

    def __init__(self, user_id):
        self.user_id = user_id
        self.start = self._max_id()

    @staticmethod
    def _max_id():
        session = new_session()
        try:
            return session.execute(text(
                'SELECT coalesce(max(id), 0) FROM suomisf.log')).scalar()
        finally:
            session.close()

    def rows(self):
        session = new_session()
        try:
            return session.execute(text(
                'SELECT table_name, table_id, action, field_name, user_id,'
                ' date, old_value FROM suomisf.log WHERE id > :start'
                ' ORDER BY id'), {'start': self.start}).mappings().all()
        finally:
            session.close()

    def find(self, table, action, field=None, table_id=None):
        """The new row matching the arguments; checks who and when."""
        for row in self.rows():
            if (row['table_name'] == table and row['action'] == action
                    and (field is None or row['field_name'] == field)
                    and (table_id is None or row['table_id'] == table_id)):
                assert row['user_id'] == self.user_id
                age = datetime.now(timezone.utc) - row['date']
                assert timedelta(0) <= age < timedelta(minutes=5)
                return row
        raise AssertionError(
            f'No log row {table} {action} {field} {table_id}:'
            f' {[dict(r) for r in self.rows()]}')


@pytest.fixture
def watch(admin_id):
    return lambda: LogWatch(admin_id)


def _id(response):
    body = response.data
    if isinstance(body, dict):
        body = body.get('id', body.get('response'))
    return int(body)


def _delete_by(model, **filters):
    session = new_session()
    try:
        session.query(model).filter_by(**filters).delete()
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Publishers and series
# ---------------------------------------------------------------------------

def test_publisher_create_update_delete(admin_client, watch):
    try:
        log = watch()
        response = admin_client.post('/api/publishers', data={'data': {
            'name': NAME, 'fullname': NAME + ' Oy', 'links': []}})
        assert response.status_code == 201, response.data
        pub_id = _id(response)
        log.find('Kustantaja', 'Uusi', table_id=pub_id)

        log = watch()
        assert admin_client.put('/api/publishers', data={'data': {
            'id': pub_id, 'name': NAME,
            'fullname': NAME + ' Ab'}}).status_code == 200
        log.find('Kustantaja', 'Päivitys', 'Koko nimi', pub_id)

        log = watch()
        assert admin_client.delete(
            f'/api/publishers/{pub_id}').status_code == 200
        log.find('Kustantaja', 'Poisto', table_id=pub_id)
    finally:
        _delete_by(Publisher, name=NAME)


def test_bookseries_create_update(admin_client, watch):
    try:
        log = watch()
        response = admin_client.post('/api/bookseries', data={'data': {
            'name': NAME, 'orig_name': None, 'important': False,
            'description': None, 'partof': None}})
        assert response.status_code == 201, response.data
        series_id = _id(response)
        log.find('Kirjasarja', 'Uusi', table_id=series_id)

        log = watch()
        assert admin_client.put('/api/bookseries', data={'data': {
            'id': series_id, 'name': NAME, 'orig_name': 'Muutettu',
            'important': False, 'description': None,
            'partof': None}}).status_code == 200
        log.find('Kirjasarja', 'Päivitys', table_id=series_id)

        log = watch()
        assert admin_client.delete(
            f'/api/bookseries/{series_id}').status_code == 200
        log.find('Kirjasarja', 'Poisto', table_id=series_id)
    finally:
        _delete_by(Bookseries, name=NAME)


def test_pubseries_update_delete(admin_client, watch):
    # POST /api/pubseries can't create one (it never sets the required
    # publisher), so make it directly.
    session = new_session()
    try:
        series = Pubseries(name=NAME, publisher_id=1)
        session.add(series)
        session.commit()
        series_id = series.id
    finally:
        session.close()
    try:
        log = watch()
        assert admin_client.put('/api/pubseries', data={'data': {
            'id': series_id, 'name': NAME,
            'description': 'Muutettu'}}).status_code == 200
        log.find('Julkaisusarja', 'Päivitys', 'Kuvaus', series_id)

        log = watch()
        assert admin_client.delete(
            f'/api/pubseries/{series_id}').status_code == 200
        log.find('Julkaisusarja', 'Poisto', table_id=series_id)
    finally:
        _delete_by(Pubseries, name=NAME)


# ---------------------------------------------------------------------------
# Magazines
# ---------------------------------------------------------------------------

def test_magazine_create_update_delete(admin_client, watch):
    try:
        log = watch()
        response = admin_client.post('/api/magazines', data={'data': {
            'name': NAME, 'publisher': None, 'type': {'id': 1}}})
        assert response.status_code == 201, response.data
        magazine_id = _id(response)
        log.find('Lehti', 'Uusi', table_id=magazine_id)

        log = watch()
        assert admin_client.put('/api/magazines', data={'data': {
            'id': magazine_id, 'name': NAME, 'publisher': None,
            'issn': '1234-5678', 'type': {'id': 1}}}).status_code == 200
        log.find('Lehti', 'Päivitys', 'ISSN', magazine_id)

        log = watch()
        assert admin_client.delete(
            f'/api/magazines/{magazine_id}').status_code == 200
        log.find('Lehti', 'Poisto', table_id=magazine_id)
    finally:
        _delete_by(Magazine, name=NAME)


# ---------------------------------------------------------------------------
# People and stories
# ---------------------------------------------------------------------------

def test_person_create_delete(admin_client, watch):
    try:
        log = watch()
        response = admin_client.post('/api/people', data={'data': {
            'name': NAME, 'alt_name': NAME, 'fullname': NAME}})
        assert response.status_code == 201, response.data
        person_id = _id(response)
        log.find('Henkilö', 'Uusi', table_id=person_id)

        log = watch()
        assert admin_client.delete(
            f'/api/people/{person_id}').status_code == 200
        log.find('Henkilö', 'Poisto', table_id=person_id)
    finally:
        _delete_by(Person, name=NAME)


def _story_payload(contributor):
    return {'data': {
        'title': NAME, 'orig_title': NAME, 'pubyear': 2099,
        'type': {'id': 1}, 'genres': [], 'tags': [],
        'contributors': [{'person': contributor, 'role': {'id': 1},
                          'description': None}]}}


def test_story_create_with_new_person_delete(admin_client, watch):
    """A person typed by name into a contributor field is created, and
    that is logged too."""
    new_person = NAME + ' Kirjoittaja'
    try:
        log = watch()
        response = admin_client.post('/api/shorts',
                                     data=_story_payload(new_person))
        assert response.status_code == 201, response.data
        story_id = _id(response)
        log.find('Novelli', 'Uusi', table_id=story_id)
        log.find('Henkilö', 'Uusi')

        log = watch()
        assert admin_client.delete(
            f'/api/shorts/{story_id}').status_code == 200
        log.find('Novelli', 'Poisto', table_id=story_id)
    finally:
        _delete_by(ShortStory, title=NAME)
        _delete_by(Person, name=new_person)


def test_person_link_add(admin_client, watch):
    link = 'https://example.invalid/lokitesti'
    try:
        log = watch()
        response = admin_client.post(f'/api/person/{PERSON_ID}/links',
                                     data={'link': link,
                                           'description': NAME})
        assert response.status_code == 201, response.data
        row = log.find('Henkilö', 'Päivitys', 'Linkit', PERSON_ID)
        assert row['old_value'] == 'Lisätty: ' + link
    finally:
        _delete_by(PersonLink, person_id=PERSON_ID, link=link)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

@pytest.fixture
def new_tags(app):  # pylint: disable=unused-argument
    names = [NAME + ' a', NAME + ' b']
    yield names
    for name in names:
        _delete_by(Tag, name=name)


def _create_tag(client, name):
    response = client.post('/api/tags', data={'data': {'name': name}})
    assert response.status_code == 201, response.data
    return _id(response)


def test_tag_create_update_delete(admin_client, watch, new_tags):
    log = watch()
    tag_id = _create_tag(admin_client, new_tags[0])
    log.find('Asiasana', 'Uusi', table_id=tag_id)

    log = watch()
    assert admin_client.put('/api/tags', data={
        'id': tag_id, 'name': new_tags[1], 'type': {'id': 1},
        'description': None}).status_code == 200
    row = log.find('Asiasana', 'Päivitys', 'Nimi', tag_id)
    assert row['old_value'] == new_tags[0]

    log = watch()
    assert admin_client.delete(f'/api/tags/{tag_id}').status_code == 200
    log.find('Asiasana', 'Poisto', table_id=tag_id)


def test_tag_merge_keeps_links(admin_client, watch, new_tags):
    """Merging moves the removed tag's people and works to the kept tag
    (it used to change the person id instead of the tag id) and logs it."""
    keep = _create_tag(admin_client, new_tags[0])
    remove = _create_tag(admin_client, new_tags[1])
    try:
        assert admin_client.put(
            f'/api/person/{PERSON_ID}/tags/{remove}').status_code == 200
        assert admin_client.put(
            f'/api/work/{WORK_ID}/tags/{remove}').status_code == 200

        log = watch()
        assert admin_client.post(
            f'/api/tags/{keep}/merge/{remove}').status_code == 200
        log.find('Asiasana', 'Päivitys', 'Yhdistetty', keep)
        log.find('Asiasana', 'Poisto', table_id=remove)

        session = new_session()
        try:
            for table, column, item in (('persontag', 'person_id', PERSON_ID),
                                        ('worktag', 'work_id', WORK_ID)):
                tags = session.execute(text(
                    f'SELECT tag_id FROM suomisf.{table}'
                    f' WHERE {column} = :item'), {'item': item}).scalars()
                assert keep in list(tags), table
        finally:
            session.close()
    finally:
        admin_client.delete(f'/api/person/{PERSON_ID}/tags/{keep}')
        admin_client.delete(f'/api/work/{WORK_ID}/tags/{keep}')
        admin_client.delete(f'/api/person/{PERSON_ID}/tags/{remove}')
        admin_client.delete(f'/api/work/{WORK_ID}/tags/{remove}')


@pytest.fixture
def story_id(admin_client):
    response = admin_client.post('/api/shorts',
                                 data=_story_payload({'id': PERSON_ID}))
    assert response.status_code == 201, response.data
    story = _id(response)
    yield story
    admin_client.delete(f'/api/shorts/{story}')
    _delete_by(ShortStory, title=NAME)


def test_tag_add_and_remove(admin_client, watch, new_tags, story_id):
    tag_id = _create_tag(admin_client, new_tags[0])
    targets = [('work', WORK_ID, 'Teos'), ('person', PERSON_ID, 'Henkilö'),
               ('story', story_id, 'Novelli'),
               ('issue', 1, 'Irtonumero')]
    for kind, item_id, table in targets:
        url = f'/api/{kind}/{item_id}/tags/{tag_id}'
        log = watch()
        assert admin_client.put(url).status_code == 200, url
        row = log.find(table, 'Päivitys', 'Asiasanat', item_id)
        assert row['old_value'] == 'Lisätty: ' + new_tags[0]

        log = watch()
        assert admin_client.delete(url).status_code == 200, url
        row = log.find(table, 'Päivitys', 'Asiasanat', item_id)
        assert row['old_value'] == 'Poistettu: ' + new_tags[0]
    admin_client.delete(f'/api/tags/{tag_id}')


# ---------------------------------------------------------------------------
# Story lists
# ---------------------------------------------------------------------------

def test_edition_story_list(admin_client, watch, story_id):
    url = f'/api/editions/{EDITION_ID}/shorts'
    old = [s['id'] for s in admin_client.get(url).data]
    try:
        log = watch()
        assert admin_client.put(url, data=old + [story_id]).status_code == 200
        log.find('Painos', 'Päivitys', 'Novellit', EDITION_ID)

        log = watch()
        assert admin_client.put(url, data=old + [story_id]).status_code == 200
        assert log.rows() == [], 'an unchanged list is not logged'
    finally:
        admin_client.put(url, data=old)


def test_issue_story_list(admin_client, watch, story_id):
    issue_id = 1
    old = [s['id'] for s in
           admin_client.get(f'/api/issues/{issue_id}/shorts').data]
    try:
        log = watch()
        assert admin_client.put('/api/issues/shorts', data={
            'issue_id': issue_id,
            'shorts': old + [story_id]}).status_code == 200
        log.find('Irtonumero', 'Päivitys', 'Novellit', issue_id)
    finally:
        admin_client.put('/api/issues/shorts', data={
            'issue_id': issue_id, 'shorts': old})


# ---------------------------------------------------------------------------
# Works and awards
# ---------------------------------------------------------------------------

def test_work_create_logs_first_edition_and_awards(admin_client, watch):
    log = watch()
    response = admin_client.post('/api/works', data={'data': {
        'title': NAME, 'pubyear': 2099, 'work_type': {'id': 1},
        'contributions': [{'person': {'id': PERSON_ID}, 'role': {'id': 1}}],
        'genres': [], 'links': []}})
    assert response.status_code == 201, response.data
    work_id = _id(response)
    try:
        log.find('Teos', 'Uusi', table_id=work_id)
        edition_id = admin_client.get(
            f'/api/works/{work_id}').data['editions'][0]['id']
        log.find('Painos', 'Uusi', table_id=edition_id)

        session = new_session()
        try:
            award_id, category_id = session.execute(text(
                'SELECT ac.award_id, ac.category_id'
                ' FROM suomisf.awardcategories ac'
                ' JOIN suomisf.awardcategory c ON c.id = ac.category_id'
                ' WHERE c.type = 1 LIMIT 1')).one()
        finally:
            session.close()
        entry = {'id': 0, 'year': 2099, 'award': {'id': award_id},
                 'category': {'id': category_id}, 'work': {'id': work_id},
                 'person': {'id': 0}, 'story': {'id': 0}}
        log = watch()
        assert admin_client.post('/api/awarded', data={
            'id': work_id, 'type': 1, 'awards': [entry]}).status_code == 200
        row = log.find('Teos', 'Päivitys', 'Palkinnot', work_id)
        assert row['old_value'] == ''

        log = watch()
        assert admin_client.post('/api/awarded', data={
            'id': work_id, 'type': 1, 'awards': []}).status_code == 200
        row = log.find('Teos', 'Päivitys', 'Palkinnot', work_id)
        assert '2099' in row['old_value']
    finally:
        admin_client.post('/api/awarded', data={'id': work_id, 'type': 1,
                                                'awards': []})
        assert admin_client.delete(f'/api/works/{work_id}').status_code == 200
