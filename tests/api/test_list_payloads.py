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
