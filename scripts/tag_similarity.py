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
The models (about 3 GB) are downloaded on the first run.
"""
import argparse
import hashlib
import itertools
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
RELATED_NAME = 0.94       # T2
RELATED_CONTAINMENT = 0.9  # T3
CONTAINMENT_USES = 10     # both tags need this many uses ...
CONTAINMENT_SHARED = 3    # ... and this many shared items
RELATED_PER_TAG = 5       # related pairs kept per tag, best first

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
    reason: str      # 'baseform' | 'spelling' | 'name' | 'usage'
    name_score: Optional[float] = None
    containment: Optional[float] = None
    shared: int = 0

    @property
    def score(self) -> float:
        """What a related pair is ranked by."""
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
               similarity: np.ndarray, analyze: Analyze) -> List[Pair]:
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

    # Related: name, then usage.
    for i, j in close:
        if upper[i, j] >= RELATED_NAME:
            add(int(i), int(j), 'related', 'name')
    index = {tag.id: i for i, tag in enumerate(tags)}
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


def compute(conn: Any, embed: Embed, analyze: Analyze,
            rebuild: bool = False) -> Computed:
    """Read the tags, embed what is missing and find the pairs. Only
    reads."""
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
    pairs = find_pairs(tags, items, similarity, analyze)
    return Computed(tags, items, pairs, vectors, embedded)


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
                           args.rebuild)
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
