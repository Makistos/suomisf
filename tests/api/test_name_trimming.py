"""
Names and titles are saved without leading, trailing or doubled spaces,
and name lookups ignore them, so " runo " finds the tag "runo" instead
of creating a second one.
"""
import pytest

from app.names import clean_name
from app.orm_decl import (Bookseries, Edition, Magazine, Person, Publisher,
                          Pubseries, ShortStory, Tag, Work)
from app.route_helpers import new_session

from .test_works import TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD


@pytest.fixture
def admin_client(api_client):
    api_client.login(TEST_ADMIN_NAME, TEST_ADMIN_PASSWORD)
    return api_client


@pytest.mark.parametrize('value, expected', [
    ('  Luella Miller', 'Luella Miller'),
    ('Daniel Dark  -trilogia ', 'Daniel Dark -trilogia'),
    ('Ei muutosta', 'Ei muutosta'),
    ('   ', ''),
    (None, None),
])
def test_clean_name(value, expected):
    assert clean_name(value) == expected


@pytest.mark.parametrize('model, attr', [
    (Person, 'name'), (Work, 'title'), (Edition, 'title'),
    (ShortStory, 'title'), (Publisher, 'name'), (Pubseries, 'name'),
    (Bookseries, 'name'), (Tag, 'name'), (Magazine, 'name'),
])
def test_model_cleans_on_set(model, attr):
    """Setting the field cleans it, both in the constructor and later."""
    obj = model(**{attr: '  Uusi  nimi '})
    assert getattr(obj, attr) == 'Uusi nimi'
    setattr(obj, attr, ' Toinen ')
    assert getattr(obj, attr) == 'Toinen'


def test_tag_create_trims_and_finds_existing(admin_client):
    """A tag created with spaces is saved trimmed, and the same name with
    spaces again counts as the existing tag."""
    resp = admin_client.post('/api/tags',
                             data={'data': {'name': '  Trimmitesti  x '}})
    assert resp.status_code == 201, resp.json
    tag_id = resp.data['id']
    try:
        session = new_session()
        assert session.get(Tag, tag_id).name == 'Trimmitesti x'
        session.close()

        again = admin_client.post('/api/tags',
                                  data={'data': {'name': 'Trimmitesti x  '}})
        assert again.status_code != 201
    finally:
        admin_client.delete(f'/api/tags/{tag_id}')
