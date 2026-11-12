"""
SuomiSF API Similar Works Tests

Tests for GET /api/works/<id>/similar with list rows written by the test
itself (the job is tested in tests/test_work_similarity.py).
"""
import json

import pytest
from sqlalchemy import text

from app.route_helpers import new_session

from .base_test import BaseAPITest


@pytest.fixture
def similar_rows():
    """A list for a work: two targets, the better one with a cover.

    Yields (source, best, second, tag id, tag name); removes the rows."""
    session = new_session()
    covered = session.execute(text(
        'SELECT e.work_id FROM edition e '
        'JOIN editionimage i ON i.edition_id = e.id '
        'ORDER BY e.work_id LIMIT 1')).scalar()
    others = [r[0] for r in session.execute(text(
        'SELECT id FROM work WHERE id <> :c ORDER BY id LIMIT 2'),
        {'c': covered})]
    source, second = others
    tag = session.execute(text(
        'SELECT id, name FROM tag ORDER BY id LIMIT 1')).first()
    session.execute(text(
        'DELETE FROM work_similarity WHERE source_work_id = :s'),
        {'s': source})
    reasons_best = [
        {'type': 6, 'tags': [tag.id], 'contribution': 0.3},     # Aika
        {'type': 2, 'tags': [tag.id], 'contribution': 0.2},     # Alagenre
        {'type': 'description', 'tags': [], 'contribution': 0.1},
    ]
    reasons_second = [
        {'type': 6, 'tags': [tag.id], 'contribution': 0.1},     # Aika only
        {'type': 1, 'tags': [-1], 'contribution': 0.05},        # deleted tag
    ]
    for target, rank, reasons in ((covered, 1, reasons_best),
                                  (second, 2, reasons_second)):
        session.execute(text(
            'INSERT INTO work_similarity (source_work_id, target_work_id, '
            'rank, score, signal_scores, reasons, algorithm_version) '
            "VALUES (:s, :t, :r, 0.5, '{}', CAST(:reasons AS jsonb), 0)"),
            {'s': source, 't': target, 'r': rank,
             'reasons': json.dumps(reasons)})
    session.commit()
    try:
        yield source, covered, second, tag.id, tag.name
    finally:
        session.execute(text(
            'DELETE FROM work_similarity WHERE source_work_id = :s'),
            {'s': source})
        session.commit()
        session.close()


class TestWorkSimilar(BaseAPITest):
    """Tests for GET /api/works/{id}/similar."""

    def test_list_in_rank_order_with_reasons_and_cover(self, api_client,
                                                       similar_rows):
        """The works come best first with title, cover and named reasons.

        Also checks:
        - era/actor/place reasons are dropped when a stronger one exists,
          and kept when they are all there is;
        - a reason whose tags no longer exist is dropped;
        - the description reason has no tags.
        """
        source, best, second, tag_id, tag_name = similar_rows
        response = api_client.get(f'/api/works/{source}/similar')
        response.assert_success()
        data = response.data
        assert [w['id'] for w in data] == [best, second]
        first = data[0]
        assert first['title']
        assert first['image']['image_src']
        assert 'thumb_src' in first['image']
        assert [r['type'] for r in first['reasons']] == [2, 'description']
        assert first['reasons'][0] == {
            'type': 2, 'type_name': 'Alagenre',
            'tags': [{'id': tag_id, 'name': tag_name}]}
        assert first['reasons'][1]['tags'] == []
        assert [r['type_name'] for r in data[1]['reasons']] == ['Aika']

    def test_limit(self, api_client, similar_rows):
        """?limit=1 gives only the best work."""
        source, best, _, _, _ = similar_rows
        response = api_client.get(f'/api/works/{source}/similar?limit=1')
        response.assert_success()
        assert [w['id'] for w in response.data] == [best]

    def test_work_without_list_gives_empty_list(self, api_client):
        """A work with no computed list gives [], not an error."""
        response = api_client.get('/api/works/999999999/similar')
        response.assert_success()
        assert response.data == []

    @pytest.mark.parametrize('path', ['/api/works/abc/similar',
                                      '/api/works/1/similar?limit=0',
                                      '/api/works/1/similar?limit=x'])
    def test_invalid_id_or_limit(self, api_client, path):
        """A non-numeric id or a limit below 1 gives 400."""
        response = api_client.get(path)
        assert response.status_code == 400
