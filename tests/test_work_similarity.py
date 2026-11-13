"""
Tests for scripts/work_similarity.py: the scoring and re-ranking rules on
small hand-made sets of works, and a run against the test database inside
a transaction that is rolled back.
"""
import importlib.util
import math
import os
from typing import Any, Dict

import numpy as np
import pytest
from sqlalchemy import create_engine, text

_PATH = os.path.join(os.path.dirname(__file__), '..', 'scripts',
                     'work_similarity.py')
_spec = importlib.util.spec_from_file_location('work_similarity', _PATH)
assert _spec and _spec.loader
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)

ALAGENRE, TYYLI, AIHE, AIKA, TOIMIJA = (ws.ALAGENRE, ws.TYYLI, ws.AIHE,
                                        ws.AIKA, ws.TOIMIJA)
SF, FANTASIA = 5, 1


def W(wid, tags=None, genres=(SF,), year=2000, words=30, **kw):
    """A work; tags as {type: [ids]}."""
    return ws.Work(id=wid, year=year, words=words,
                   tags={t: frozenset(ids) for t, ids in
                         (tags or {}).items()},
                   genres=frozenset(genres), **kw)


def config(**changes) -> Dict[str, Any]:
    cfg = dict(ws.SIMILARITY_CONFIG)
    cfg.update(changes)
    return cfg


def lists(works, **changes):
    return ws.compute_lists(works, config(**changes))[1]


def targets(result, source):
    return [r.target for r in result.get(source, [])]


def rec(result, source, target):
    return next(r for r in result[source] if r.target == target)


# --- Helpers -----------------------------------------------------------

def test_word_count_strips_html():
    assert ws.word_count('<p>yksi<br/>kaksi&nbsp;kolme</p>') == 3
    assert ws.word_count(None) == 0


def test_eligibility_needs_description_and_three_tags():
    cfg = ws.SIMILARITY_CONFIG
    assert ws.eligible(W(1, {AIHE: [1, 2, 3]}), cfg)
    assert not ws.eligible(W(1, {AIHE: [1, 2]}), cfg)
    assert not ws.eligible(W(1, {AIHE: [1, 2, 3]}, words=19), cfg)


def test_ineligible_works_are_neither_sources_nor_targets():
    result = lists([W(1, {ALAGENRE: [1, 2, 3]}),
                    W(2, {ALAGENRE: [1, 2, 3]}),
                    W(3, {ALAGENRE: [1, 2, 3]}, words=5)])
    assert targets(result, 1) == [2]
    assert 3 not in result


def test_rarity():
    assert ws.rarity(9, 9, 4.0) == pytest.approx(1.0)
    assert ws.rarity(0, 9, 4.0) == pytest.approx(1 + math.log(10))
    assert ws.rarity(0, 10_000, 4.0) == 4.0
    # No cap (the default): rare tags keep rising.
    assert ws.rarity(0, 10_000, None) == pytest.approx(1 + math.log(10_001))


def test_year_similarity_halves_every_30_years():
    assert ws.year_similarity(1990, 1990, 30) == 1.0
    assert ws.year_similarity(1960, 1990, 30) == pytest.approx(0.5)


def test_base_genres_fold_age_groups_and_drop_non_content():
    # Nuorten fantasia -> Fantasia, Lasten SF -> SF, Kokoelma dropped.
    assert ws.base_genres({8, 11, 16}) == {FANTASIA, SF}


def test_series_root_follows_parents():
    parents = {1: None, 2: 1, 3: 2}
    assert ws.series_root(3, parents) == 1
    assert ws.series_root(None, parents) is None


# --- Scores ------------------------------------------------------------

JACCARD = {'tag_measure': 'jaccard', 'ignore_unique_tags': False,
           'rarity_cap': 4.0}
WORKS_123 = [W(1, {ALAGENRE: [1, 2, 3]}), W(2, {ALAGENRE: [1, 2, 4]}),
             W(3, {ALAGENRE: [5, 6, 7]})]


def test_weighted_jaccard_uses_rarity():
    result = lists(WORKS_123, **JACCARD)
    r_shared = ws.rarity(2, 3, 4.0)   # tags 1 and 2: two works each
    r_own = ws.rarity(1, 3, 4.0)      # tags 3 and 4: one work each
    expected = 2 * r_shared / (2 * r_shared + 2 * r_own)
    assert rec(result, 1, 2).signals['types'][str(ALAGENRE)] == \
        pytest.approx(expected, abs=1e-4)


def test_cosine_uses_rarity_and_ignores_unique_tags():
    with_unique = lists(WORKS_123, ignore_unique_tags=False)
    r_shared = ws.rarity(2, 3, None)
    r_own = ws.rarity(1, 3, None)
    shared = 2 * r_shared ** 2
    expected = shared / (shared + r_own ** 2)   # same norm on both sides
    assert rec(with_unique, 1, 2).signals['types'][str(ALAGENRE)] == \
        pytest.approx(expected, abs=1e-4)
    # Tags 3 and 4 are on one work each: left out, 1 and 2 match fully.
    default = lists(WORKS_123)
    assert rec(default, 1, 2).signals['types'][str(ALAGENRE)] == \
        pytest.approx(1.0)


def test_cosine_does_not_penalise_a_richly_tagged_work():
    # Work 1 has many more themes than 2; both share the same three.
    common = [1, 2, 3]
    extra = list(range(10, 30))
    works = [W(1, {AIHE: common + extra}), W(2, {AIHE: common}),
             W(3, {AIHE: extra})]   # 3 makes the extra tags non-unique
    cosine = rec(lists(works), 1, 2).signals['types'][str(AIHE)]
    jaccard = rec(lists(works, **JACCARD), 1, 2).signals['types'][str(AIHE)]
    assert cosine > 2 * jaccard


def test_missing_tag_type_both_rule_vs_either_rule():
    a = W(1, {ALAGENRE: [1, 2, 3], TYYLI: [10]})
    b = W(2, {ALAGENRE: [1, 2, 3]})
    keep = {'ignore_unique_tags': False}   # Tyyli 10 is on a only
    both = lists([a, b], tag_type_available='both', **keep)
    either = lists([a, b], tag_type_available='either', **keep)
    # 'both': Tyyli is unavailable, so the Alagenre match is all of T.
    assert rec(both, 1, 2).signals['T'] == pytest.approx(1.0)
    # 'either': b has no Tyyli, which counts as no match.
    assert rec(either, 1, 2).signals['T'] == pytest.approx(
        0.30 / (0.30 + 0.25), abs=1e-4)


def test_weights_renormalise_over_available_signals():
    # No genres on b: G is unavailable, S is the mean of T and Y only.
    result = lists([W(1, {ALAGENRE: [1, 2, 3]}, year=1990),
                    W(2, {ALAGENRE: [1, 2, 3]}, genres=(), year=1960)])
    s = rec(result, 1, 2).signals
    assert s['G'] is None
    assert s['S'] == pytest.approx((0.40 * 1.0 + 0.05 * 0.5) / 0.45,
                                   abs=1e-4)


def test_tag_score_is_rescaled_like_the_description():
    # Works on a chain: neighbours share two of three tags, others fewer.
    works = [W(i, {ALAGENRE: [i, i + 1, i + 2]}) for i in range(1, 13)]
    scaled = lists(works)
    raw = lists(works, rescale_tags=False)
    signals = [r.signals for recs in scaled.values() for r in recs]
    # The best pairs reach the top of the scale; the raw value is kept.
    assert max(s['T'] for s in signals) == pytest.approx(1.0)
    assert max(s['T_raw'] for s in signals) < 1.0
    pair = rec(scaled, 5, 6).signals
    assert pair['T_raw'] == pytest.approx(rec(raw, 5, 6).signals['T'])
    assert pair['T'] > pair['T_raw']


# --- Minimum evidence --------------------------------------------------

def test_era_and_actor_tags_alone_are_not_enough():
    result = lists([W(1, {AIKA: [1], TOIMIJA: [2], AIHE: [3]}),
                    W(2, {AIKA: [1], TOIMIJA: [2], AIHE: [4]})])
    assert targets(result, 1) == []


def test_two_shared_general_tags_are_enough_one_is_not():
    # Unique tags kept, so one shared tag of nine stays below 0.15.
    keep = {'ignore_unique_tags': False}
    two = lists([W(1, {AIHE: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}),
                 W(2, {AIHE: [1, 2, 11, 12, 13, 14, 15, 16, 17, 18]})],
                **keep)
    one = lists([W(1, {AIHE: [1, 3, 4, 5, 6, 7, 8, 9, 10]}),
                 W(2, {AIHE: [1, 11, 12, 13, 14, 15, 16, 17, 18]})],
                **keep)
    assert targets(two, 1) == [2]
    assert targets(one, 1) == []


def test_a_shared_style_tag_is_enough():
    result = lists([W(1, {TYYLI: [1], AIHE: [2, 3]}),
                    W(2, {TYYLI: [1], AIHE: [4, 5]})])
    assert targets(result, 1) == [2]


# --- Exclusions and age groups -----------------------------------------

def test_works_sharing_an_omnibus_are_left_out():
    tags = {ALAGENRE: [1, 2, 3]}
    result = lists([W(1, tags, omnibus=frozenset({9})),
                    W(2, tags, omnibus=frozenset({9})),
                    W(9, tags, omnibus=frozenset({9})),
                    W(3, tags)])
    assert targets(result, 1) == [3]


def test_non_fiction_only_with_non_fiction():
    tags = {ALAGENRE: [1, 2, 3]}
    result = lists([W(1, tags, type=ws.NONFICTION), W(2, tags, type=1),
                    W(3, tags, type=ws.NONFICTION)])
    assert targets(result, 1) == [3]


def test_childrens_books_only_with_childrens_books():
    tags = {ALAGENRE: [1, 2, 3]}
    result = lists([W(1, tags, genres=(17,)), W(2, tags, genres=(FANTASIA,)),
                    W(3, tags, genres=(17,))])
    assert targets(result, 1) == [3]
    assert 1 not in targets(result, 2)


def test_young_adult_and_adult_get_half_the_score():
    tags = {ALAGENRE: [1, 2, 3]}
    result = lists([W(1, tags, genres=(FANTASIA,)), W(2, tags, genres=(8,)),
                    W(3, tags, genres=(FANTASIA,))])
    assert targets(result, 1) == [3, 2]
    assert rec(result, 1, 2).score == pytest.approx(
        rec(result, 1, 3).score * 0.5)


# --- Series and variety ------------------------------------------------

def test_same_series_is_penalised_and_capped():
    tags = {ALAGENRE: [1, 2, 3]}
    other = {ALAGENRE: [1, 2, 4]}   # a weaker match
    result = lists([W(1, tags, series=7), W(2, tags, series=7),
                    W(3, tags, series=7), W(4, other)])
    # The weaker match outranks the same-series one (x 0.25), and only one
    # work of the source's series is kept.
    assert targets(result, 1) == [4, 2]


def test_one_work_per_other_series_and_two_per_author():
    tags = {ALAGENRE: [1, 2, 3]}
    works = [W(1, tags),
             W(2, tags, series=5), W(3, tags, series=5),
             W(4, tags, authors=frozenset({50})),
             W(5, tags, authors=frozenset({50})),
             W(6, tags, authors=frozenset({50, 51}))]
    assert targets(lists(works), 1) == [2, 4, 5]


def test_reasons_strongest_type_first():
    result = lists([W(1, {AIHE: [1, 2], ALAGENRE: [3]}),
                    W(2, {AIHE: [1, 2], ALAGENRE: [3]})])
    reasons = rec(result, 1, 2).reasons
    # Both match fully; Aihe weighs 0.35, Alagenre 0.30.
    assert [r['type'] for r in reasons] == [AIHE, ALAGENRE]
    assert reasons[0]['tags'] == [1, 2]


# --- Description similarity --------------------------------------------

def unit(*values):
    v = np.array(values, dtype=np.float32)
    return v / np.linalg.norm(v)


def test_embed_missing_embeds_only_new_and_changed_texts():
    calls = []

    def embed(texts):
        calls.extend(texts)
        return np.array([unit(1, len(t)) for t in texts])

    texts = {1: 'sama', 2: 'muuttunut', 3: 'uusi'}
    old = unit(0, 1).astype('<f4').tobytes()
    stored = {1: (ws.text_hash('sama'), old),
              2: (ws.text_hash('vanha'), old)}
    vectors, new = ws.embed_missing(texts, stored, embed)
    assert calls == ['muuttunut', 'uusi']
    assert [w for w, _, _ in new] == [2, 3]
    assert np.allclose(vectors[1], unit(0, 1))
    _, again = ws.embed_missing(texts, stored, embed, rebuild=True)
    assert len(again) == 3


def test_description_scale_median_pair_is_zero():
    # Ten works on a circle: the median pair gets D 0, the closest 1.
    vectors = {i: unit(math.cos(i / 10), math.sin(i / 10))
               for i in range(10)}
    works = [W(i) for i in range(10)]
    d = ws.description_model(vectors)(works)(0, 10)
    off = d[~np.eye(10, dtype=bool)]
    assert off.min() == 0.0 and off.max() == pytest.approx(1.0, abs=0.02)
    assert np.median(off) == pytest.approx(0.0, abs=0.05)


def test_similar_description_alone_is_enough_and_is_a_reason():
    # No shared tags; works 1 and 2 have the same description vector.
    works = [W(1, {AIHE: [1, 2, 3]}), W(2, {AIHE: [4, 5, 6]}),
             W(3, {AIHE: [7, 8, 9]}), W(4, {AIHE: [10, 11, 12]})]
    vectors = {1: unit(1, 0, 0), 2: unit(1, 0, 0), 3: unit(0, 1, 0),
               4: unit(0, 0, 1)}
    _, result = ws.compute_lists(
        works, description=ws.description_model(vectors))
    assert targets(result, 1) == [2]
    r = rec(result, 1, 2)
    assert r.signals['D'] == pytest.approx(1.0)
    assert r.reasons == [{'type': 'description', 'tags': [],
                          'contribution': pytest.approx(0.35)}]


def test_without_vectors_d_is_unavailable():
    result = lists([W(1, {ALAGENRE: [1, 2, 3]}),
                    W(2, {ALAGENRE: [1, 2, 3]})])
    assert rec(result, 1, 2).signals['D'] is None


# --- Changes -----------------------------------------------------------

def test_plan_changes_rewrites_only_changed_lists():
    result = lists([W(1, {ALAGENRE: [1, 2, 3]}),
                    W(2, {ALAGENRE: [1, 2, 3]})])
    stored = {s: ws._key(recs) for s, recs in result.items()}
    stored[99] = [(1, [], ws.ALGORITHM_VERSION)]
    changes = ws.plan_changes(stored, result)
    assert changes.rewritten == []
    assert changes.removed == [99]
    stored[1] = [(2, [], ws.ALGORITHM_VERSION - 1)]
    assert ws.plan_changes(stored, result).rewritten == [1]


# --- Against the test database -----------------------------------------

@pytest.fixture
def conn(app):  # pylint: disable=unused-argument
    # The app fixture points DATABASE_URL at the test database.
    url = os.environ['DATABASE_URL']
    assert 'suomisf_test' in url
    engine = create_engine(url)
    with engine.connect() as c:
        trans = c.begin()
        try:
            c.execute(text('SET search_path = suomisf'))
            c.execute(text('DELETE FROM work_similarity'))
            c.execute(text('DELETE FROM work_similarity_run'))
            c.execute(text('DELETE FROM work_embedding'))
            yield c
        finally:
            trans.rollback()
    engine.dispose()


def test_run_stores_lists_and_a_rerun_changes_nothing(conn):
    works, input_hash = ws.load_works(conn)
    eligible, result = ws.compute_lists(works)
    assert eligible, 'the test database has eligible works'
    changes = ws.plan_changes(ws.stored_lists(conn), result)
    ws.apply(conn, result, changes, input_hash, len(eligible))

    source = next(s for s, recs in result.items() if recs)
    rows = conn.execute(text(
        'SELECT target_work_id, rank FROM work_similarity '
        'WHERE source_work_id = :s ORDER BY rank'), {'s': source}).all()
    assert [r.target_work_id for r in rows] == targets(result, source)
    assert rows[0].rank == 1
    assert ws.last_run(conn).input_hash == input_hash

    again, hash_again = ws.load_works(conn)
    assert hash_again == input_hash
    _, result_again = ws.compute_lists(again)
    assert ws.plan_changes(ws.stored_lists(conn), result_again).rewritten \
        == []


def test_lista_tags_are_not_loaded_and_pseudonyms_count_as_the_person(conn):
    work = conn.execute(text(
        'SELECT work_id FROM worktag GROUP BY work_id LIMIT 1')).scalar()
    lista = conn.execute(text(
        "INSERT INTO tag (name, type_id) VALUES ('qqlista', :t) "
        'RETURNING id'), {'t': ws.LISTA}).scalar()
    conn.execute(text('INSERT INTO worktag (work_id, tag_id) '
                      'VALUES (:w, :t)'), {'w': work, 't': lista})
    alias = conn.execute(text(
        'SELECT person_id, real_person_id FROM workcontributor '
        'WHERE real_person_id IS NOT NULL AND role_id = 1 LIMIT 1')).first()
    works = {w.id: w for w in ws.load_works(conn)[0]}
    assert all(lista not in ids for ids in works[work].tags.values())
    if alias:
        assert any(alias.real_person_id in w.authors
                   and alias.person_id not in w.authors
                   for w in works.values())


def test_vectors_are_stored_and_read_back(conn):
    work = conn.execute(text('SELECT id FROM work LIMIT 1')).scalar()
    conn.execute(text('DELETE FROM work_embedding'))
    vector = unit(3, 4)
    ws.store_vectors(conn, [(work, 'h1', vector.astype('<f4').tobytes()),
                            (-1, 'h2', vector.tobytes())])
    stored = ws.stored_vectors(conn)
    assert set(stored) == {work}   # a missing work is left out
    assert stored[work][0] == 'h1'
    assert np.allclose(np.frombuffer(stored[work][1], dtype='<f4'), vector)


def test_single_work_update_leaves_the_run_record(conn):
    works, _ = ws.load_works(conn)
    eligible, _ = ws.compute_lists(works)
    one = eligible[0].id
    _, result = ws.compute_lists(works, only={one})
    assert set(result) == {one}
    changes = ws.plan_changes(ws.stored_lists(conn), result, {one})
    ws.apply(conn, result, changes, None, len(eligible))
    assert ws.last_run(conn) is None
