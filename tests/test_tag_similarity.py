"""
Tests for scripts/tag_similarity.py: the name and usage rules, and runs
against the test database inside a transaction that is rolled back. A
fake embedder and analyser stand in for the models and libvoikko.
"""
import hashlib
import importlib.util
import os
from typing import Dict, List

import numpy as np
import pytest
from sqlalchemy import create_engine, text

_PATH = os.path.join(os.path.dirname(__file__), '..', 'scripts',
                     'tag_similarity.py')
_spec = importlib.util.spec_from_file_location('tag_similarity', _PATH)
assert _spec and _spec.loader
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)

# Base forms for the fake analyser; other words stand for themselves.
BASEFORMS = {'qqsodat': {'qqsota'}, 'qqkesän': {'qqkesä'}}


def analyze(word):
    return frozenset(BASEFORMS.get(word, {word}))


class FakeEmbedder:
    """A random unit vector per text, or a shared one for texts in the
    same meaning group. Records what it was asked to embed."""

    def __init__(self, groups: Dict[str, str]):
        self.groups = groups
        self.calls: Dict[str, List[str]] = {}

    def __call__(self, model, texts):
        self.calls[model] = self.calls.get(model, []) + list(texts)
        rows = []
        for t in texts:
            seed = hashlib.sha256(self.groups.get(t, t).encode()).digest()
            rng = np.random.default_rng(int.from_bytes(seed[:8], 'big'))
            rows.append(rng.standard_normal(64))
        return ts.normalise(np.array(rows, dtype=np.float32))


# --- Rules ---------------------------------------------------------------

def test_baseform_pairs():
    tags = [ts.Tag(1, 'qqsota'), ts.Tag(2, 'qqsodat'), ts.Tag(3, 'qqkesä'),
            ts.Tag(4, 'qqsodat qqkesän'), ts.Tag(5, 'qqsota qqkesä'),
            ts.Tag(6, 'qqsota -- qqkesä')]
    # Same base forms word by word; "--" is not a word.
    assert ts.baseform_pairs(tags, analyze) == {(0, 1), (3, 4), (3, 5),
                                                (4, 5)}


@pytest.mark.parametrize('a, b, score, expected', [
    ('tsekkoslovakia', 'Tšekkoslovakia', 0.0, True),   # folded equal
    ('rinnakkaismaailmat', 'rinnakkaiset maailmat', 0.99, True),
    ('san fransisco', 'san francisco', 0.95, True),
    ('san fransisco', 'san francisco', 0.85, False),  # meaning too far
    ('finncon 2007', 'finncon 2008', 0.99, False),    # only digits differ
    ('kuu', 'kuut', 0.99, False),                     # too short
    ('koulutus', 'kulutus', 0.62, False),
])
def test_spelling_match(a, b, score, expected):
    assert ts.spelling_match(a, b, score) is expected


def test_containment():
    assert ts.containment(3, 10, 4) == 0.75
    assert ts.containment(0, 0, 4) is None


def test_usage_pairs_needs_uses_and_shared_items():
    items = {1: {f'w{i}' for i in range(12)},
             2: {f'w{i}' for i in range(10)},
             3: {f'w{i}' for i in range(9)}}    # too few uses
    assert ts.usage_pairs(items) == {(1, 2): 10}


def test_limit_related_keeps_best_per_tag():
    pairs = [ts.Pair(1, b, 'related', 'name', name_score=1 - b / 100)
             for b in range(2, 10)]
    kept = ts.limit_related(pairs, 3)
    # Tag 1 keeps its best 3; the others have only this one pair each,
    # so every pair is among the best of its other tag.
    assert len(kept) == 8
    pairs.append(ts.Pair(2, 3, 'related', 'name', name_score=0.95))
    assert len(ts.limit_related(pairs, 1)) == 8


# --- Runs against the test database -------------------------------------

GROUPS = {'qqväkivalta': 'violence', 'qqväkivaltaisuus': 'violence',
          'qqcon 2007': 'con', 'qqcon 2008': 'con'}
NAMES = ['qqsota', 'qqsodat', 'qqtsekkoslovakia', 'qqtšekkoslovakia',
         'qqväkivalta', 'qqväkivaltaisuus', 'qqcon 2007', 'qqcon 2008',
         'qqpelit', 'qqkonsolipelit']


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
            # The clone may carry the dev DB's real vectors and pairs.
            c.execute(text('DELETE FROM tag_similarity'))
            c.execute(text('DELETE FROM tag_embedding'))
            c.execute(text('DELETE FROM tag_place'))
            yield c
        finally:
            trans.rollback()
    engine.dispose()


def _setup(conn):
    """Test tags by name; qqpelit and qqkonsolipelit share 10 works."""
    ids = {name: conn.execute(text(
        'INSERT INTO tag (name) VALUES (:n) RETURNING id'),
        {'n': name}).scalar() for name in NAMES}
    works = [r[0] for r in conn.execute(text(
        'SELECT id FROM work ORDER BY id LIMIT 12'))]
    for i, work in enumerate(works):
        conn.execute(text('INSERT INTO worktag (work_id, tag_id) '
                          'VALUES (:w, :t)'), {'w': work, 't': ids['qqpelit']})
        if i < 10:
            conn.execute(text('INSERT INTO worktag (work_id, tag_id) '
                              'VALUES (:w, :t)'),
                         {'w': work, 't': ids['qqkonsolipelit']})
    return ids


def _run(conn, embed, rebuild=False):
    computed = ts.compute(conn, embed, analyze, rebuild)
    return computed, ts.apply(conn, computed)


def _stored(conn, ids):
    """Stored pairs among the test tags, by names."""
    names = {v: k for k, v in ids.items()}
    rows = conn.execute(text(
        'SELECT tag_a, tag_b, kind, reason, status, containment, shared '
        'FROM tag_similarity WHERE tag_a = ANY(:ids) AND tag_b = ANY(:ids)'),
        {'ids': list(ids.values())})
    return {frozenset((names[r.tag_a], names[r.tag_b])): r for r in rows}


def _pair(*names):
    return frozenset(names)


def test_run_finds_and_stores_pairs(conn):
    ids = _setup(conn)
    embed = FakeEmbedder(GROUPS)
    _, changes = _run(conn, embed)
    stored = _stored(conn, ids)

    assert {k: (r.kind, r.reason) for k, r in stored.items()} == {
        _pair('qqsota', 'qqsodat'): ('duplicate', 'baseform'),
        _pair('qqtsekkoslovakia', 'qqtšekkoslovakia'):
            ('duplicate', 'spelling'),
        _pair('qqväkivalta', 'qqväkivaltaisuus'): ('related', 'name'),
        # Same meaning, but only the year differs: related, not spelling.
        _pair('qqcon 2007', 'qqcon 2008'): ('related', 'name'),
        _pair('qqpelit', 'qqkonsolipelit'): ('related', 'usage'),
    }
    usage = stored[_pair('qqpelit', 'qqkonsolipelit')]
    assert (usage.shared, usage.containment) == (10, 1.0)
    assert len(changes.added) >= len(stored)
    # Every tag got a vector from each model.
    tags = conn.execute(text('SELECT count(*) FROM tag')).scalar()
    for model in ts.MODELS:
        assert len(embed.calls[model]) == tags
    assert conn.execute(text(
        'SELECT count(*) FROM tag_embedding')).scalar() == tags * 2


def test_rerun_embeds_only_renamed_and_keeps_dismissed(conn):
    ids = _setup(conn)
    _run(conn, FakeEmbedder(GROUPS))
    conn.execute(text(
        "UPDATE tag_similarity SET status = 'dismissed' "
        'WHERE tag_a = least(:a, :b) AND tag_b = greatest(:a, :b)'),
        {'a': ids['qqcon 2007'], 'b': ids['qqcon 2008']})
    # Neither pair passes the rules after the renames.
    conn.execute(text("UPDATE tag SET name = 'qqmuu' WHERE id = :id"),
                 {'id': ids['qqcon 2008']})
    conn.execute(text("UPDATE tag SET name = 'qqrauha' WHERE id = :id"),
                 {'id': ids['qqväkivaltaisuus']})

    embed = FakeEmbedder(GROUPS)
    computed, changes = _run(conn, embed)
    for model in ts.MODELS:
        assert sorted(embed.calls[model]) == ['qqmuu', 'qqrauha']
        assert computed.embedded[model] == 2
    stored = _stored(conn, {**ids, 'qqmuu': ids['qqcon 2008'],
                            'qqrauha': ids['qqväkivaltaisuus']})
    assert _pair('qqväkivalta', 'qqrauha') not in stored
    assert stored[_pair('qqcon 2007', 'qqmuu')].status == 'dismissed'
    assert changes.dismissed_kept >= 1
    assert len(changes.removed) >= 1

    # A rerun with the pair found again leaves the status alone.
    conn.execute(text("UPDATE tag SET name = 'qqcon 2008' WHERE id = :id"),
                 {'id': ids['qqcon 2008']})
    _run(conn, FakeEmbedder(GROUPS))
    assert _stored(conn, ids)[_pair('qqcon 2007', 'qqcon 2008')].status \
        == 'dismissed'


def test_rebuild_embeds_everything(conn):
    _setup(conn)
    _run(conn, FakeEmbedder(GROUPS))
    embed = FakeEmbedder(GROUPS)
    computed, _ = _run(conn, embed, rebuild=True)
    tags = conn.execute(text('SELECT count(*) FROM tag')).scalar()
    assert computed.embedded == dict.fromkeys(ts.MODELS, tags)


def test_deleting_a_tag_removes_its_rows(conn):
    ids = _setup(conn)
    _run(conn, FakeEmbedder(GROUPS))
    conn.execute(text('DELETE FROM tag WHERE id = :id'),
                 {'id': ids['qqsodat']})
    for table, col in (('tag_similarity', 'tag_b'),
                       ('tag_similarity', 'tag_a'),
                       ('tag_embedding', 'tag_id')):
        assert conn.execute(text(
            f'SELECT count(*) FROM {table} WHERE {col} = :id'),
            {'id': ids['qqsodat']}).scalar() == 0


def test_tags_deleted_after_compute_are_left_out(conn):
    ids = _setup(conn)
    computed = ts.compute(conn, FakeEmbedder(GROUPS), analyze)
    conn.execute(text('DELETE FROM tag WHERE id = :id'),
                 {'id': ids['qqsodat']})
    ts.apply(conn, computed)
    assert _pair('qqsota', 'qqsodat') not in _stored(conn, ids)


# --- Places ----------------------------------------------------------------

def _ent(label, description='paikka', sitelinks=10, instance=(), **up):
    return ts.Entity(label, description, sitelinks, list(instance),
                     {p: list(up.get(p, []))
                      for p in ('P131', 'P17', 'P30', 'P279')})


class FakeWikidata:
    """Q1 New York in Q2 (state) in Q3 USA, on Q4 (continent); Q5 Turku
    in Q6 Finland, both on Q7 Europe."""

    def __init__(self):
        self.searches: List[str] = []
        self.ents = {
            'Q1': _ent('New York', P131=['Q2']),
            'Q2': _ent('New Yorkin osavaltio', P17=['Q3']),
            'Q3': _ent('Yhdysvallat', P30=['Q4']),
            'Q4': _ent('Pohjois-Amerikka'),
            'Q5': _ent('Turku', P17=['Q6'], P30=['Q7']),
            'Q6': _ent('Suomi', P30=['Q7']),
            'Q7': _ent('Eurooppa'),
            # Namesakes: no Finnish description, fictional, not a place.
            'Q8': _ent('Mars', description=''),
            'Q9': _ent('Turku', instance=['Q3895768'], sitelinks=99),
            'Q10': _ent('Mars', description='planeetta'),
            'Q11': _ent('Turku', description='kylä', sitelinks=1),
        }
        self.geo = {'Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9',
                    'Q11'}
        self.names = {
            'qqnew york': ['Q1'], 'qqusa': ['Q3'], 'qqyhdysvallat': ['Q3'],
            'qqpohjoisvaltio': ['Q2'], 'qqturku': ['Q11', 'Q9', 'Q5'],
            'qqsuomi': ['Q6'], 'qqeurooppa': ['Q7'], 'qqmars': ['Q8', 'Q10'],
        }

    def search(self, name):
        self.searches.append(name)
        return self.names.get(name, [])

    def entities(self, qids):
        return {q: self.ents.get(q) for q in qids}

    def geographic(self, qids):
        return {q for q in qids if q in self.geo}


def test_resolve_place_picks_the_best_known_real_place():
    wd = FakeWikidata()
    turku = ts.resolve_place(ts.Tag(1, 'qqturku (paikka)'), wd)
    # Q9 is fictional, Q11 less known than Q5.
    assert (turku.qid, turku.label) == ('Q5', 'Turku')
    assert turku.ancestors == {'Q6': 1}
    assert turku.continent_ancestors == {'Q6': 1, 'Q7': 1}
    # No Finnish description (Q8) or not geographic (Q10).
    assert ts.resolve_place(ts.Tag(2, 'qqmars'), wd).qid is None
    assert ts.resolve_place(ts.Tag(3, 'qqkahvilat'), wd).qid is None
    assert ts.resolve_place(ts.Tag(4, 'derry (kuvitteellinen)'), wd).qid \
        is None
    assert 'derry' not in wd.searches


def test_entity_keeps_current_statements():
    def claim(qid, rank='normal', ended=False):
        c = {'rank': rank,
             'mainsnak': {'datavalue': {'value': {'id': qid}}}}
        if ended:
            c['qualifiers'] = {'P582': []}
        return c
    e = ts._entity({'labels': {'fi': {'value': 'Turku'}}, 'claims': {
        'P17': [claim('Q34', ended=True), claim('Q33')],
        'P131': [claim('Q1', 'preferred'), claim('Q2')],
        'P30': [claim('Q46', 'deprecated')]}})
    assert e.up == {'P131': ['Q1'], 'P17': ['Q33'], 'P30': [], 'P279': []}
    # A region in several countries is in none of them.
    e = ts._entity({'claims': {'P17': [claim('Q33'), claim('Q34')]}})
    assert e.up['P17'] == []


def _place(tag_id, qid, ancestors=None, continent=None):
    return ts.Place(tag_id, '', qid, ancestors=ancestors or {},
                    continent_ancestors=continent or ancestors or {})


def test_place_pairs_nearest_tagged_ancestor():
    places = [
        _place(1, 'Q1', {'Q2': 1, 'Q3': 2}, {'Q2': 1, 'Q3': 2, 'Q4': 3}),
        _place(2, 'Q3', {}, {'Q4': 1}),        # usa
        _place(3, 'Q3', {}, {'Q4': 1}),        # yhdysvallat
        _place(4, 'Q5', {'Q6': 1}, {'Q6': 1, 'Q7': 1}),
        _place(5, 'Q6', {}, {'Q7': 1}),
        _place(6, 'Q7'),
        _place(7, None),
    ]
    assert ts.place_pairs(places) == [
        (1, 2, 'related'), (1, 3, 'related'),   # New York in both
        (2, 3, 'duplicate'),                    # same item
        (4, 5, 'related'),                      # Turku - Suomi, not Europe
        (5, 6, 'related'),                      # continent fallback
    ]


PLACES = ['qqnew york', 'qqusa', 'qqyhdysvallat', 'qqturku', 'qqsuomi',
          'qqeurooppa', 'qqkahvilat']


def _setup_places(conn):
    return {name: conn.execute(text(
        'INSERT INTO tag (name, type_id) VALUES (:n, :t) RETURNING id'),
        {'n': name, 't': ts.PLACE_TYPE}).scalar() for name in PLACES}


def _run_places(conn, wd, rebuild=False):
    computed = ts.compute(conn, FakeEmbedder({}), analyze, rebuild, wd)
    ts.apply(conn, computed)
    return computed


def test_run_stores_places_and_pairs(conn):
    ids = _setup_places(conn)
    _run_places(conn, FakeWikidata())
    stored = _stored(conn, ids)
    assert {k: (r.kind, r.reason) for k, r in stored.items()} == {
        _pair('qqusa', 'qqyhdysvallat'): ('duplicate', 'place'),
        _pair('qqnew york', 'qqusa'): ('related', 'place'),
        _pair('qqnew york', 'qqyhdysvallat'): ('related', 'place'),
        _pair('qqturku', 'qqsuomi'): ('related', 'place'),
        _pair('qqsuomi', 'qqeurooppa'): ('related', 'place'),
    }
    rows = dict(conn.execute(text(
        'SELECT tag_id, qid FROM tag_place WHERE tag_id = ANY(:ids)'),
        {'ids': list(ids.values())}).all())
    assert rows[ids['qqturku']] == 'Q5'
    assert rows[ids['qqkahvilat']] is None


def test_rerun_looks_up_only_new_and_renamed_places(conn):
    ids = _setup_places(conn)
    _run_places(conn, FakeWikidata())
    conn.execute(text("UPDATE tag SET name = 'qqpohjoisvaltio' "
                      'WHERE id = :id'), {'id': ids['qqkahvilat']})
    # Set by hand: never looked up again, even when renamed.
    conn.execute(text("UPDATE tag_place SET manual = true, qid = 'Q99' "
                      'WHERE tag_id = :id'), {'id': ids['qqturku']})
    conn.execute(text("UPDATE tag SET name = 'qqturku2' WHERE id = :id"),
                 {'id': ids['qqturku']})
    wd = FakeWikidata()
    _run_places(conn, wd)
    assert set(wd.searches) == {'qqpohjoisvaltio'}
    assert conn.execute(text(
        'SELECT qid FROM tag_place WHERE tag_id = :id'),
        {'id': ids['qqturku']}).scalar() == 'Q99'
    # New York is now nearest to the tagged state, not to the country.
    names = {**ids, 'qqpohjoisvaltio': ids['qqkahvilat']}
    stored = _stored(conn, names)
    assert _pair('qqnew york', 'qqpohjoisvaltio') in stored
    assert _pair('qqnew york', 'qqusa') not in stored
    # Rebuild looks up everything but the manual one.
    wd = FakeWikidata()
    _run_places(conn, wd, rebuild=True)
    assert 'qqturku2' not in wd.searches
    assert 'qqusa' in wd.searches


def test_without_wikidata_stored_places_still_count(conn):
    ids = _setup_places(conn)
    _run_places(conn, FakeWikidata())
    computed = _run_places(conn, None)
    assert computed.places == []
    assert _pair('qqusa', 'qqyhdysvallat') in _stored(conn, ids)


def test_geographic_follows_subclasses():
    """A city is geographic through city -> human settlement -> a
    GEO_CLASSES class; a language is not. Cache filled by hand, so no
    network."""
    wd = ts.Wikidata()
    geo = ts.GEO_CLASSES[0]
    wd._entities.update({
        'Q1': _ent('Turku', instance=['C1']),
        'Q2': _ent('suomi', instance=['C3']),
        'C1': _ent('kaupunki', P279=['C2']),
        'C2': _ent('asutus', P279=[geo]),
        'C3': _ent('kieli', P279=['C4']),
        'C4': _ent('viestintä', P279=['C3']),     # a cycle
        geo: _ent('maantieteellinen kohde'),
    })
    assert wd.geographic(['Q1', 'Q2']) == {'Q1'}
