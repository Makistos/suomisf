"""
Size and query count of the big list pages (API plan, Phase 3).

These pages list thousands of editions or works. Loading each edition's
relationships lazily while serializing made WSOY's publisher page issue
11,274 SQL queries (10 s in production) for a 4.6 MB response. The tests
pin the number of queries to a small bound that doesn't grow with the
list, and pin the fields sent, since the frontend's list components read
exactly these (see the *_FIELDS tuples next to each schema).
"""
import time
from contextlib import contextmanager

import pytest

from sqlalchemy import event
from sqlalchemy.engine import Engine

WSOY = 387
MAX_QUERIES = 60


@contextmanager
def count_queries():
    counter = {'n': 0}

    def before(*args, **kwargs):
        counter['n'] += 1

    event.listen(Engine, 'before_cursor_execute', before)
    try:
        yield counter
    finally:
        event.remove(Engine, 'before_cursor_execute', before)


def test_publisher_page_query_count_does_not_grow_with_editions(client):
    with count_queries() as queries:
        started = time.perf_counter()
        response = client.get(f'/api/publishers/{WSOY}')
        elapsed = time.perf_counter() - started
    assert response.status_code == 200
    editions = response.get_json()['editions']
    assert len(editions) > 1000
    assert queries['n'] <= MAX_QUERIES, f"{queries['n']} queries for {len(editions)} editions"
    assert elapsed < 5, f'{elapsed:.1f} s'


def test_publisher_page_edition_fields(client):
    editions = client.get(f'/api/publishers/{WSOY}').get_json()['editions']
    assert set(editions[0]) == {
        'id', 'title', 'pubyear', 'editionnum', 'version', 'pages', 'size', 'isbn',
        'images', 'publisher', 'owners', 'wishlisted', 'work'}
    assert set(editions[0]['work']) == {
        'id', 'title', 'orig_title', 'pubyear', 'type', 'author_str', 'genres',
        'language_name', 'contributions'}
    with_authors = next(e for e in editions if e['work']['contributions'])
    contribution = with_authors['work']['contributions'][0]
    assert contribution['person']['name'] and contribution['role']['id']


STEPHEN_KING = 2286
TRANSLATOR = 455    # Ilkka Rekiaro, ~180 translated editions


@pytest.mark.parametrize('person_id', [STEPHEN_KING, TRANSLATOR])
def test_person_page_query_count(client, person_id):
    """3,175 queries for Stephen King before the relationships were loaded
    up front and tags stopped listing every work they're on."""
    with count_queries() as queries:
        response = client.get(f'/api/people/{person_id}')
    assert response.status_code == 200
    assert queries['n'] <= 150, f"{queries['n']} queries"


def test_person_page_nested_editions_are_slim(client):
    person = client.get(f'/api/people/{STEPHEN_KING}').get_json()
    work = next(w for w in person['works'] if w['editions'])
    assert set(work['editions'][0]) == {
        'id', 'title', 'pubyear', 'editionnum', 'version', 'publisher',
        'pubseries', 'images', 'owners', 'wishlisted'}
    story = next(s for s in person['stories'] if s['editions'])
    assert set(story['editions'][0]) == {'id', 'work'}
    assert set(story['editions'][0]['work']) == {'id', 'title', 'pubyear', 'author_str'}
    tagged = next(w for w in person['works'] if w['tags'])
    assert set(tagged['tags'][0]) == {'id', 'name', 'type'}


BIG_TAG = 521   # dystopia, ~360 works


def test_tag_page_query_count(client):
    """5,047 queries before the works' relationships were loaded up front."""
    with count_queries() as queries:
        response = client.get(f'/api/tags/{BIG_TAG}')
    assert response.status_code == 200
    assert len(response.get_json()['works']) > 100
    assert queries['n'] <= 80, f"{queries['n']} queries"


def test_tag_page_work_editions_are_slim(client):
    works = client.get(f'/api/tags/{BIG_TAG}').get_json()['works']
    work = next(w for w in works if w['editions'])
    assert 'imported_string' not in work and 'description' in work
    assert set(work['editions'][0]) == {
        'id', 'title', 'pubyear', 'editionnum', 'version', 'publisher',
        'contributions', 'images', 'size', 'owners', 'wishlisted'}


def test_works_by_type_query_count(client):
    """1,366 queries for non-fiction (type 4) before the editions'
    relationships were loaded up front."""
    with count_queries() as queries:
        response = client.get('/api/works/bytype/4')
    assert response.status_code == 200
    assert queries['n'] <= 200, f"{queries['n']} queries"


def test_story_drilldown_is_slim_and_batched(client):
    """All novellas took 105,117 queries and 72 MB before."""
    with count_queries() as queries:
        response = client.get('/api/stats/filterstories?storytype=1')
    assert response.status_code == 200
    stories = response.get_json()
    assert len(stories) > 1000
    assert queries['n'] <= 150, f"{queries['n']} queries"
    story = next(s for s in stories if s['editions'] and s['issues'])
    assert set(story['editions'][0]) == {'id', 'work'}
    assert set(story['editions'][0]['work']) == {'id', 'title', 'pubyear'}
    assert set(story['issues'][0]['magazine']) == {'id', 'name'}
