"""
Suggest tags that are probably duplicates or closely related, for an
admin to review. See docs/tag-similarity-plan.md.

Each run embeds only new and renamed tags, recomputes every pair and
updates the suggestions; a pair an admin has dismissed stays dismissed.

Usage:
    python scripts/tag_similarity.py              # dev database
    python scripts/tag_similarity.py --dry-run    # compute only, no writes
    python scripts/tag_similarity.py --rebuild    # re-embed every tag
    python scripts/tag_similarity.py --report docs/tag-similarity-report.md
    python scripts/tag_similarity.py --prod       # production database
    python scripts/tag_similarity.py --db postgresql://…

The database is DATABASE_URL from .env; --prod uses
DATABASE_URL_TAG_SIMILARITY_PROD (the tag_similarity role, see migration
044). Needs the similarity dependency group: pdm install -G similarity.
The models (about 3 GB) are downloaded on the first run. Paikka tags
are looked up in Wikidata (new and renamed ones only); --no-places skips
that and uses the stored matches.
"""
import argparse
import hashlib
import itertools
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import (Any, Callable, Dict, FrozenSet, Iterable, List,
                    NamedTuple, Optional, Set, Tuple)

import dotenv
import numpy as np
from sqlalchemy import create_engine, make_url, text

directory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
dotenv.load_dotenv(os.path.join(directory_path, '.env'))
dotenv.load_dotenv(os.path.join(directory_path, '../.env'))

# Embedding models and the prefix each expects. Name similarity is the
# mean of their cosines: e5 ranks spelling variants high, mpnet synonyms.
MODELS = {
    'intfloat/multilingual-e5-large': 'query: ',
    'sentence-transformers/paraphrase-multilingual-mpnet-base-v2': '',
}

# Thresholds, from the phase 0 labelling (docs/tag-similarity-plan.md).
SPELLING_RATIO = 0.9      # character similarity of the folded names
SPELLING_MIN_LEN = 5      # shorter names are too often look-alikes
SPELLING_NAME = 0.9       # T1: name similarity a spelling variant needs
RELATED_NAME = 0.91       # T2
RELATED_CONTAINMENT = 0.9  # T3
CONTAINMENT_USES = 10     # both tags need this many uses ...
CONTAINMENT_SHARED = 3    # ... and this many shared items
RELATED_PER_TAG = 5       # related pairs kept per tag, best first

# Places: Paikka tags are matched to Wikidata items.
PLACE_TYPE = 5            # tagtype Paikka
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
USER_AGENT = 'SuomiSF-tag-similarity/1.0 (https://www.sf-bibliografia.fi)'
# A match must be an instance of one of these: geographic feature,
# administrative area, country, continent, geographic region, ...
GEO_CLASSES = ('Q618123', 'Q56061', 'Q6256', 'Q5107', 'Q82794',
               'Q15642541')
FICTIONAL_CLASSES = {'Q3895768', 'Q17198419', 'Q15796005', 'Q1964689',
                     'Q15632617'}
# Followed for ancestors: located in (P131) and country (P17); the
# continent (P30) only when those reach no tag.
WALK = ('P131', 'P17')
CONTINENT = 'P30'
MAX_DEPTH = 6
CLASS_DEPTH = 10          # "subclass of" levels searched for GEO_CLASSES

# word -> its base forms
Analyze = Callable[[str], FrozenSet[str]]
# (model, texts) -> unit vectors, one row per text
Embed = Callable[[str, List[str]], np.ndarray]


class Tag(NamedTuple):
    id: int
    name: str


@dataclass
class Pair:
    tag_a: int
    tag_b: int
    kind: str        # 'duplicate' | 'related'
    reason: str      # 'baseform' | 'spelling' | 'place' | 'name' | 'usage'
    name_score: Optional[float] = None
    containment: Optional[float] = None
    shared: int = 0

    @property
    def score(self) -> float:
        """What a related pair is ranked by; a place pair comes first."""
        if self.reason == 'place':
            return 1.0
        value = self.containment if self.reason == 'usage' \
            else self.name_score
        return value or 0.0


# --- Name rules --------------------------------------------------------

def words(name: str) -> List[str]:
    """Words of a tag name; punctuation-only tokens such as "--" are
    dropped."""
    return [w for w in re.findall(r'[\w-]+', name.lower())
            if any(c.isalnum() for c in w)]


def baseform_key(name: str, analyze: Analyze) -> Tuple[FrozenSet[str], ...]:
    """Base forms of each word: "jyväskylän kesä" -> ({jyväskylä},
    {kesä})."""
    return tuple(analyze(w) for w in words(name))


def baseform_pairs(tags: List[Tag], analyze: Analyze) -> Set[Tuple[int, int]]:
    """Index pairs of tags with as many words as each other, each pair
    of words sharing a base form ("sota" / "sodat")."""
    buckets: Dict[Tuple[str, ...], List[int]] = defaultdict(list)
    for i, tag in enumerate(tags):
        key = baseform_key(tag.name, analyze)
        if not key:
            continue
        for combo in itertools.product(*(sorted(forms) for forms in key)):
            buckets[combo].append(i)
    pairs = set()
    for members in buckets.values():
        for i, j in itertools.combinations(sorted(set(members)), 2):
            pairs.add((i, j))
    return pairs


def fold(name: str) -> str:
    """Lower case without diacritics, spaces or punctuation:
    "Tšekkoslovakia" -> "tsekkoslovakia"."""
    decomposed = unicodedata.normalize('NFKD', name.lower())
    return ''.join(c for c in decomposed
                   if c.isalnum() and not unicodedata.combining(c))


def spelling_match(a: str, b: str, name_score: float) -> bool:
    """True when two names are spellings of the same word: equal once
    folded, or nearly equal and close in meaning. Names that differ only
    in digits ("finncon 2007", "finncon 2008") never match."""
    fa, fb = fold(a), fold(b)
    if not fa or not fb:
        return False
    if fa == fb:
        return True
    if re.sub(r'\d', '', fa) == re.sub(r'\d', '', fb):
        return False
    return (min(len(fa), len(fb)) >= SPELLING_MIN_LEN
            and name_score >= SPELLING_NAME
            and SequenceMatcher(None, fa, fb).ratio() >= SPELLING_RATIO)


def voikko_analyzer() -> Analyze:
    """Base forms from libvoikko; an unknown word stands for itself."""
    import libvoikko  # pylint: disable=import-outside-toplevel
    voikko = libvoikko.Voikko('fi')

    @lru_cache(maxsize=None)
    def analyze(word: str) -> FrozenSet[str]:
        forms = {a['BASEFORM'].lower() for a in voikko.analyze(word)
                 if a.get('BASEFORM')}
        return frozenset(forms or {word})
    return analyze


def fastembed_embedder() -> Embed:
    """Embeddings from fastembed (ONNX), models cached in
    ~/.cache/fastembed."""
    from fastembed import TextEmbedding  # pylint: disable=import-outside-toplevel
    cache_dir = os.path.expanduser('~/.cache/fastembed')
    loaded: Dict[str, Any] = {}

    def embed(model: str, texts: List[str]) -> np.ndarray:
        if model not in loaded:
            loaded[model] = TextEmbedding(model, cache_dir=cache_dir)
        prefix = MODELS[model]
        vectors = np.array(list(loaded[model].embed(
            [prefix + t for t in texts], batch_size=128)), dtype=np.float32)
        return normalise(vectors)
    return embed


def normalise(vectors: np.ndarray) -> np.ndarray:
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


# --- Usage ---------------------------------------------------------------

def tag_items(links: Iterable[Tuple[str, int]]) -> Dict[int, Set[str]]:
    """Items (works, short stories, articles) of each tag."""
    items: Dict[int, Set[str]] = defaultdict(set)
    for item, tag_id in links:
        items[tag_id].add(item)
    return items


def containment(shared: int, uses_a: int, uses_b: int) -> Optional[float]:
    """Shared items divided by the uses of the rarer tag."""
    fewer = min(uses_a, uses_b)
    return shared / fewer if fewer else None


def usage_pairs(items: Dict[int, Set[str]]) -> Dict[Tuple[int, int], int]:
    """Shared item counts of tag pairs (by id, smaller first) where both
    tags have CONTAINMENT_USES uses and share CONTAINMENT_SHARED items."""
    common = {t for t, its in items.items() if len(its) >= CONTAINMENT_USES}
    by_item: Dict[str, List[int]] = defaultdict(list)
    for tag_id in common:
        for item in items[tag_id]:
            by_item[item].append(tag_id)
    shared: Counter = Counter()
    for tag_ids in by_item.values():
        for pair in itertools.combinations(sorted(tag_ids), 2):
            shared[pair] += 1
    return {p: n for p, n in shared.items() if n >= CONTAINMENT_SHARED}


# --- Places --------------------------------------------------------------

@dataclass
class Place:
    """The Wikidata match of a Paikka tag (a tag_place row)."""
    tag_id: int
    name_hash: str
    qid: Optional[str]           # None: not a real place
    label: str = ''
    description: str = ''
    ancestors: Optional[Dict[str, int]] = None
    continent_ancestors: Optional[Dict[str, int]] = None
    manual: bool = False


class Entity(NamedTuple):
    label: str
    description: str             # Finnish; '' if none
    sitelinks: int
    instance: List[str]
    up: Dict[str, List[str]]     # property -> current values


class Wikidata:
    """The few Wikidata calls the place rule needs, cached per run."""

    def __init__(self) -> None:
        import requests  # pylint: disable=import-outside-toplevel
        self.requests = requests
        self.session = requests.Session()
        self.session.headers['User-Agent'] = USER_AGENT
        self._entities: Dict[str, Optional[Entity]] = {}
        self._searches: Dict[str, List[str]] = {}
        self._geo_class: Dict[str, bool] = {}

    def _get(self, url: str, params: Dict[str, str],
             timeout: int = 30) -> Any:
        for attempt in range(4):
            r = self.session.get(url, params={**params, 'format': 'json'},
                                 timeout=timeout)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()
        raise RuntimeError(f'Wikidata: HTTP {r.status_code}')

    def search(self, name: str) -> List[str]:
        """Items whose Finnish label or alias is name, ignoring case."""
        if name not in self._searches:
            res = self._get(WIKIDATA_API, {
                'action': 'wbsearchentities', 'search': name,
                'language': 'fi', 'uselang': 'fi', 'type': 'item',
                'limit': '7'})
            self._searches[name] = [
                h['id'] for h in res.get('search', [])
                if h.get('match', {}).get('text', '').lower()
                == name.lower()]
        return self._searches[name]

    def entities(self, qids: Iterable[str]) -> Dict[str, Optional[Entity]]:
        todo = [q for q in dict.fromkeys(qids) if q not in self._entities]
        for i in range(0, len(todo), 50):
            res = self._get(WIKIDATA_API, {
                'action': 'wbgetentities', 'ids': '|'.join(todo[i:i + 50]),
                'props': 'labels|descriptions|claims|sitelinks',
                'languages': 'fi|en'})
            for qid in todo[i:i + 50]:
                e = res.get('entities', {}).get(qid)
                self._entities[qid] = _entity(e) if e and 'missing' not in e \
                    else None
        return {q: self._entities.get(q) for q in qids}

    def geographic(self, qids: List[str]) -> Set[str]:
        """The items that are instances of a GEO_CLASSES class, directly
        or through "subclass of" (P279)."""
        ents = self.entities(qids)
        classes = {c for e in ents.values() if e for c in e.instance}
        self._load_classes(classes)
        return {q for q, e in ents.items()
                if e and any(self._is_geo(c) for c in e.instance)}

    def _load_classes(self, classes: Set[str]) -> None:
        """Fetch the classes and their superclasses, level by level."""
        frontier = classes
        for _ in range(CLASS_DEPTH):
            todo = [c for c in frontier if c not in self._entities]
            if not todo:
                break
            nxt: Set[str] = set()
            for e in self.entities(todo).values():
                if e:
                    nxt.update(e.up.get('P279', []))
            frontier = nxt

    def _is_geo(self, cls: str) -> bool:
        if cls not in self._geo_class:
            seen, frontier = {cls}, [cls]
            found = cls in GEO_CLASSES
            while frontier and not found:
                nxt = []
                for c in frontier:
                    e = self._entities.get(c)
                    for parent in (e.up.get('P279', []) if e else []):
                        if parent in GEO_CLASSES:
                            found = True
                        if parent not in seen:
                            seen.add(parent)
                            nxt.append(parent)
                frontier = nxt
            self._geo_class[cls] = found
        return self._geo_class[cls]


def _entity(e: Dict[str, Any]) -> Entity:
    claims = e.get('claims', {})

    def current(prop: str) -> List[str]:
        """Values of the best-ranked statements without an end time."""
        cs = [c for c in claims.get(prop, []) if c.get('rank') != 'deprecated'
              and 'P582' not in c.get('qualifiers', {})]
        if any(c.get('rank') == 'preferred' for c in cs):
            cs = [c for c in cs if c.get('rank') == 'preferred']
        values = [c.get('mainsnak', {}).get('datavalue', {}).get('value')
                  for c in cs]
        return [v['id'] for v in values if isinstance(v, dict) and 'id' in v]

    labels = e.get('labels', {})
    up = {p: current(p) for p in (*WALK, CONTINENT, 'P279')}
    # A region spanning several countries is not in any one of them.
    if len(up['P17']) > 1:
        up['P17'] = []
    return Entity(
        label=(labels.get('fi') or labels.get('en') or {}).get('value', ''),
        description=(e.get('descriptions', {}).get('fi') or {}).get(
            'value', ''),
        sitelinks=len(e.get('sitelinks', {})),
        instance=current('P31'),
        up=up)


def place_name(name: str) -> Optional[str]:
    """The name to look up: qualifiers dropped ("maine (paikka)" ->
    "maine"); None for a fictional place."""
    if '(kuvitteellinen)' in name:
        return None
    return re.sub(r'\s*\([^)]*\)', '', name).strip() or None


def resolve_place(tag: Tag, wd: Any) -> Place:
    """Match a Paikka tag to the best-known real place of that name.
    Obscure namesakes (a village called Mars) seldom have a Finnish
    description, so a match needs one."""
    place = Place(tag.id, text_hash(tag.name), None)
    name = place_name(tag.name)
    hits = wd.search(name) if name else []
    if not hits:
        return place
    ents = wd.entities(hits)
    geo = wd.geographic(hits)
    candidates = [q for q in hits if q in geo and ents[q]
                  and ents[q].description
                  and not set(ents[q].instance) & FICTIONAL_CLASSES]
    if not candidates:
        return place
    qid = max(candidates, key=lambda q: ents[q].sitelinks)
    place.qid, place.label, place.description = \
        qid, ents[qid].label, ents[qid].description
    place.ancestors = walk_up(qid, wd, WALK)
    place.continent_ancestors = walk_up(qid, wd, (*WALK, CONTINENT))
    return place


def walk_up(qid: str, wd: Any, props: Tuple[str, ...]) -> Dict[str, int]:
    """Every item a place is in through props, with its depth."""
    seen, frontier, found = {qid}, [qid], {}
    for depth in range(1, MAX_DEPTH + 1):
        nxt = []
        for e in wd.entities(frontier).values():
            for prop in props:
                for parent in (e.up.get(prop, []) if e else []):
                    if parent not in seen:
                        seen.add(parent)
                        nxt.append(parent)
                        found[parent] = depth
        if not nxt:
            break
        frontier = nxt
    return found


def place_pairs(places: Iterable[Place]) -> List[Tuple[int, int, str]]:
    """(tag_a, tag_b, kind) pairs: tags of the same place are duplicates;
    a place and its nearest tagged ancestors are related. An ancestor
    of another found ancestor is left out ("turku" - "suomi", not
    "turku" - "eurooppa")."""
    real = [p for p in places if p.qid]
    by_qid: Dict[str, List[int]] = defaultdict(list)
    for p in real:
        by_qid[p.qid].append(p.tag_id)  # type: ignore[index]
    ups = {p.qid: p.ancestors or {} for p in real}
    pairs: Set[Tuple[int, int, str]] = set()
    for ids in by_qid.values():
        for a, b in itertools.combinations(sorted(ids), 2):
            pairs.add((a, b, 'duplicate'))
    for p in real:
        found = [q for q in (p.ancestors or {}) if q in by_qid]
        if not found:
            found = [q for q in (p.continent_ancestors or {}) if q in by_qid]
        nearest = [q for q in found
                   if not any(q in ups.get(o, {}) for o in found if o != q)]
        for q in nearest:
            for other in by_qid[q]:
                a, b = sorted((p.tag_id, other))
                if (a, b, 'duplicate') not in pairs:
                    pairs.add((a, b, 'related'))
    return sorted(pairs)


# --- Pairs ---------------------------------------------------------------

def limit_related(pairs: List[Pair], per_tag: int) -> List[Pair]:
    """Keep a related pair if it is among the best per_tag of either of
    its tags."""
    by_tag: Dict[int, List[Pair]] = defaultdict(list)
    for p in pairs:
        by_tag[p.tag_a].append(p)
        by_tag[p.tag_b].append(p)
    kept: Set[Tuple[int, int]] = set()
    for tag_pairs in by_tag.values():
        tag_pairs.sort(key=lambda p: -p.score)
        kept.update((p.tag_a, p.tag_b) for p in tag_pairs[:per_tag])
    return [p for p in pairs if (p.tag_a, p.tag_b) in kept]


def find_pairs(tags: List[Tag], items: Dict[int, Set[str]],
               similarity: np.ndarray, analyze: Analyze,
               places: Iterable[Place] = ()) -> List[Pair]:
    """Every suggested pair. similarity[i, j] is the name similarity of
    tags[i] and tags[j]."""
    found: Dict[Tuple[int, int], Pair] = {}

    def add(i: int, j: int, kind: str, reason: str) -> None:
        a, b = sorted((tags[i].id, tags[j].id))
        if (a, b) not in found:
            found[(a, b)] = Pair(a, b, kind, reason)

    # Duplicates: base form, then spelling.
    for i, j in baseform_pairs(tags, analyze):
        add(i, j, 'duplicate', 'baseform')
    folded: Dict[str, List[int]] = defaultdict(list)
    for i, tag in enumerate(tags):
        if fold(tag.name):
            folded[fold(tag.name)].append(i)
    candidates = {pair for members in folded.values()
                  for pair in itertools.combinations(members, 2)}
    upper = np.triu(similarity, 1)
    close = np.argwhere(upper >= min(SPELLING_NAME, RELATED_NAME))
    candidates.update((int(i), int(j)) for i, j in close)
    for i, j in sorted(candidates):
        if spelling_match(tags[i].name, tags[j].name,
                          float(similarity[i, j])):
            add(i, j, 'duplicate', 'spelling')
    index = {tag.id: i for i, tag in enumerate(tags)}
    place_list = place_pairs(places)
    for a, b, kind in place_list:
        if kind == 'duplicate' and a in index and b in index:
            add(index[a], index[b], 'duplicate', 'place')

    # Related: place, name, then usage.
    for a, b, kind in place_list:
        if kind == 'related' and a in index and b in index:
            add(index[a], index[b], 'related', 'place')
    for i, j in close:
        if upper[i, j] >= RELATED_NAME:
            add(int(i), int(j), 'related', 'name')
    for (a, b), shared in usage_pairs(items).items():
        if (containment(shared, len(items[a]), len(items[b])) or 0) \
                >= RELATED_CONTAINMENT:
            add(index[a], index[b], 'related', 'usage')

    for p in found.values():
        p.name_score = round(float(similarity[index[p.tag_a],
                                              index[p.tag_b]]), 4)
        p.shared = len(items.get(p.tag_a, set()) & items.get(p.tag_b, set()))
        c = containment(p.shared, len(items.get(p.tag_a, ())),
                        len(items.get(p.tag_b, ())))
        p.containment = round(c, 4) if c is not None else None
    duplicates = [p for p in found.values() if p.kind == 'duplicate']
    related = [p for p in found.values() if p.kind == 'related']
    return duplicates + limit_related(related, RELATED_PER_TAG)


# --- Database ------------------------------------------------------------

LINKS_SQL = """
    SELECT 'w' || work_id, tag_id FROM worktag
    UNION ALL SELECT 's' || shortstory_id, tag_id FROM storytag
    UNION ALL SELECT 'a' || article_id, tag_id FROM articletag
"""


def text_hash(name: str) -> str:
    return hashlib.sha256(name.encode()).hexdigest()[:16]


@dataclass
class Computed:
    tags: List[Tag]
    items: Dict[int, Set[str]]
    pairs: List[Pair]
    # (tag_id, model, text_hash, vector bytes) to store
    vectors: List[Tuple[int, str, str, bytes]]
    embedded: Dict[str, int]
    # Places looked up this run, to store.
    places: List[Place]


def load_places(conn: Any) -> Dict[int, Place]:
    return {r.tag_id: Place(r.tag_id, r.name_hash, r.qid, r.label or '',
                            r.description or '', r.ancestors,
                            r.continent_ancestors, r.manual)
            for r in conn.execute(text(
                'SELECT tag_id, name_hash, qid, label, description, '
                'ancestors, continent_ancestors, manual FROM tag_place'))}


def update_places(conn: Any, wd: Any, rebuild: bool
                  ) -> Tuple[List[Place], List[Place]]:
    """(places of the current Paikka tags, places looked up now).
    Looks up new and renamed tags, or every one not set by hand with
    rebuild. If Wikidata fails, the stored matches are used."""
    tags = [Tag(*row) for row in conn.execute(text(
        'SELECT id, name FROM tag WHERE type_id = :t ORDER BY id'),
        {'t': PLACE_TYPE})]
    stored = load_places(conn)
    todo = [t for t in tags if wd is not None and not (
        t.id in stored and (stored[t.id].manual or (
            stored[t.id].name_hash == text_hash(t.name) and not rebuild)))]
    looked_up: List[Place] = []
    start = time.time()
    try:
        # Batch the calls resolve_place() makes; it then hits the cache.
        names = [n for n in map(place_name, (t.name for t in todo)) if n]
        hits = [q for n in names for q in wd.search(n)]
        wd.entities(hits)
        wd.geographic(hits)
        for tag in todo:
            looked_up.append(resolve_place(tag, wd))
    except Exception as exp:  # pylint: disable=broad-except
        print(f'Wikidata lookup failed ({exp}); using the stored '
              'places for the rest.', file=sys.stderr)
    if todo:
        print(f'Looked up {len(looked_up)} places in Wikidata in '
              f'{time.time() - start:.0f} s.')
    current = {p.tag_id: p for p in stored.values()}
    current.update({p.tag_id: p for p in looked_up})
    ids = {t.id for t in tags}
    return [p for p in current.values() if p.tag_id in ids], looked_up


def compute(conn: Any, embed: Embed, analyze: Analyze,
            rebuild: bool = False, wikidata: Any = None) -> Computed:
    """Read the tags, embed what is missing, look up new places and find
    the pairs. Only reads. Without wikidata only stored places count."""
    tags = [Tag(*row) for row in conn.execute(text(
        'SELECT id, name FROM tag ORDER BY id'))]
    items = tag_items(conn.execute(text(LINKS_SQL)))
    stored: Dict[Tuple[int, str], Tuple[str, bytes]] = {
        (tag_id, model): (h, bytes(vector))
        for tag_id, model, h, vector in conn.execute(text(
            'SELECT tag_id, model, text_hash, vector FROM tag_embedding'))}

    vectors: List[Tuple[int, str, str, bytes]] = []
    embedded: Dict[str, int] = {}
    similarity = np.zeros((len(tags), len(tags)), dtype=np.float32)
    for model in MODELS:
        hashes = [text_hash(t.name) for t in tags]
        matrix: List[Optional[np.ndarray]] = [None] * len(tags)
        todo = []
        for i, tag in enumerate(tags):
            old = stored.get((tag.id, model))
            if old and old[0] == hashes[i] and not rebuild:
                matrix[i] = np.frombuffer(old[1], dtype='<f4')
            else:
                todo.append(i)
        if todo:
            start = time.time()
            new = embed(model, [tags[i].name for i in todo])
            print(f'Embedded {len(todo)} tags with {model} '
                  f'in {time.time() - start:.0f} s.')
            for i, vector in zip(todo, new, strict=True):
                vector = vector.astype('<f4')
                matrix[i] = vector
                vectors.append((tags[i].id, model, hashes[i],
                                vector.tobytes()))
        embedded[model] = len(todo)
        if tags:
            m = np.vstack(matrix)  # type: ignore[arg-type]
            similarity += m @ m.T
    similarity /= len(MODELS)
    places, looked_up = update_places(conn, wikidata, rebuild)
    pairs = find_pairs(tags, items, similarity, analyze, places)
    return Computed(tags, items, pairs, vectors, embedded, looked_up)


class Changes(NamedTuple):
    added: List[Pair]
    updated: List[Pair]
    # New pairs that no longer pass the rules.
    removed: List[Tuple[int, int]]
    # Dismissed pairs no longer found; kept so they stay dismissed.
    dismissed_kept: int


def plan_changes(existing: Dict[Tuple[int, int], str],
                 pairs: List[Pair]) -> Changes:
    """existing maps stored pairs to their status."""
    found = {(p.tag_a, p.tag_b) for p in pairs}
    gone = [k for k in existing if k not in found]
    return Changes(
        added=[p for p in pairs if (p.tag_a, p.tag_b) not in existing],
        updated=[p for p in pairs if (p.tag_a, p.tag_b) in existing],
        removed=[k for k in gone if existing[k] == 'new'],
        dismissed_kept=sum(existing[k] == 'dismissed' for k in gone))


def existing_pairs(conn: Any) -> Dict[Tuple[int, int], str]:
    return {(a, b): status for a, b, status in conn.execute(text(
        'SELECT tag_a, tag_b, status FROM tag_similarity'))}


def apply(conn: Any, computed: Computed) -> Changes:
    """Store the vectors and pairs, in the caller's transaction. Tags
    deleted since compute() are left out."""
    from psycopg2.extras import execute_values  # pylint: disable=import-outside-toplevel
    ids = [t.id for t in computed.tags]
    alive = {row[0] for row in conn.execute(
        text('SELECT id FROM tag WHERE id = ANY(:ids)'), {'ids': ids})}
    pairs = [p for p in computed.pairs
             if p.tag_a in alive and p.tag_b in alive]
    changes = plan_changes(existing_pairs(conn), pairs)

    cur = conn.connection.cursor()
    vectors = [v for v in computed.vectors if v[0] in alive]
    if vectors:
        execute_values(cur, """
            INSERT INTO tag_embedding (tag_id, model, text_hash, vector)
            VALUES %s
            ON CONFLICT (tag_id, model) DO UPDATE
            SET text_hash = EXCLUDED.text_hash, vector = EXCLUDED.vector,
                updated = now()""",
            [(t, m, h, v) for t, m, h, v in vectors])
    places = [p for p in computed.places if p.tag_id in alive]
    if places:
        execute_values(cur, """
            INSERT INTO tag_place (tag_id, name_hash, qid, label,
                                   description, ancestors,
                                   continent_ancestors)
            VALUES %s
            ON CONFLICT (tag_id) DO UPDATE
            SET name_hash = EXCLUDED.name_hash, qid = EXCLUDED.qid,
                label = EXCLUDED.label, description = EXCLUDED.description,
                ancestors = EXCLUDED.ancestors,
                continent_ancestors = EXCLUDED.continent_ancestors,
                checked = now()
            WHERE NOT tag_place.manual""",
            [(p.tag_id, p.name_hash, p.qid, p.label, p.description,
              json.dumps(p.ancestors or {}),
              json.dumps(p.continent_ancestors or {})) for p in places],
            template='(%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)')
    # Vectors of models no longer used.
    conn.execute(text('DELETE FROM tag_embedding WHERE model <> ALL(:m)'),
                 {'m': list(MODELS)})
    if pairs:
        execute_values(cur, """
            INSERT INTO tag_similarity (tag_a, tag_b, kind, reason,
                                        name_score, containment, shared)
            VALUES %s
            ON CONFLICT (tag_a, tag_b) DO UPDATE
            SET kind = EXCLUDED.kind, reason = EXCLUDED.reason,
                name_score = EXCLUDED.name_score,
                containment = EXCLUDED.containment,
                shared = EXCLUDED.shared, updated = now()""",
            [(p.tag_a, p.tag_b, p.kind, p.reason, p.name_score,
              p.containment, p.shared) for p in pairs])
    if changes.removed:
        execute_values(cur, """
            DELETE FROM tag_similarity s USING (VALUES %s) AS r(a, b)
            WHERE s.tag_a = r.a AND s.tag_b = r.b AND s.status = 'new'""",
            changes.removed)
    return changes


# --- Output --------------------------------------------------------------

REASONS = {
    'baseform': 'Sama perusmuoto', 'spelling': 'Kirjoitusasu',
    'place': 'Paikka',
    'name': 'Samankaltainen nimi', 'usage': 'Käytetään yhdessä',
}


def report(computed: Computed, database: str) -> str:
    """Markdown list of the pairs, duplicates first."""
    names = {t.id: t.name for t in computed.tags}

    def uses(tag_id: int) -> int:
        return len(computed.items.get(tag_id, ()))

    out = ['# Tag similarity suggestions', '',
           f'Database: {database}. {len(computed.pairs)} pairs.', '']
    for kind, title in (('duplicate', 'Probable duplicates'),
                        ('related', 'Related')):
        rows = sorted((p for p in computed.pairs if p.kind == kind),
                      key=lambda p: (p.reason, -p.score))
        out += [f'## {title} ({len(rows)})', '',
                '| Tag | Tag | Reason | Name | Containment | Shared |',
                '|---|---|---|---|---|---|']
        for p in rows:
            cont = '' if p.containment is None else f'{p.containment:.2f}'
            out.append(
                f'| {names[p.tag_a]} ({uses(p.tag_a)}) '
                f'| {names[p.tag_b]} ({uses(p.tag_b)}) '
                f'| {REASONS[p.reason]} | {p.name_score:.3f} | {cont} '
                f'| {p.shared} |')
        out.append('')
    return '\n'.join(out)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Suggest duplicate and related tags.')
    parser.add_argument('--dry-run', action='store_true',
                        help='compute and print, write nothing')
    parser.add_argument('--rebuild', action='store_true',
                        help='re-embed every tag')
    parser.add_argument('--report', metavar='FILE',
                        help='write the pairs as Markdown')
    parser.add_argument('--no-places', action='store_true',
                        help='no Wikidata lookups; use the stored places')
    where = parser.add_mutually_exclusive_group()
    where.add_argument('--prod', action='store_true',
                       help='production database '
                            '(DATABASE_URL_TAG_SIMILARITY_PROD in .env)')
    where.add_argument('--db', metavar='URL',
                       help='this database (default DATABASE_URL in .env)')
    args = parser.parse_args()

    var = 'DATABASE_URL_TAG_SIMILARITY_PROD' if args.prod \
        else 'DATABASE_URL'
    db_url = args.db or os.environ.get(var)
    if not db_url:
        print(f'{var} is not set (.env).', file=sys.stderr)
        return 2
    database = make_url(db_url).database or '?'
    if args.prod:
        database += ' (production)'
    engine = create_engine(db_url)

    # Read and compute first, then write in one short transaction.
    with engine.connect() as conn:
        conn.execute(text('SET search_path = suomisf'))
        computed = compute(conn, fastembed_embedder(), voikko_analyzer(),
                           args.rebuild,
                           None if args.no_places else Wikidata())
        existing = existing_pairs(conn)
        conn.rollback()
    kinds = Counter(p.kind for p in computed.pairs)
    print(f'{database}: {len(computed.tags)} tags, '
          f'{kinds["duplicate"]} duplicate and {kinds["related"]} '
          'related pairs.')
    if args.report:
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(report(computed, database) + '\n')
        print(f'Report: {args.report}')

    if args.dry_run:
        changes = plan_changes(existing, computed.pairs)
        verb = 'Would add'
    else:
        with engine.begin() as conn:
            conn.execute(text('SET search_path = suomisf'))
            changes = apply(conn, computed)
        verb = 'Added'
    print(f'{verb} {len(changes.added)} pairs, updated '
          f'{len(changes.updated)}, removed {len(changes.removed)}; '
          f'{changes.dismissed_kept} dismissed pairs kept.')
    engine.dispose()
    return 0


if __name__ == '__main__':
    sys.exit(main())
