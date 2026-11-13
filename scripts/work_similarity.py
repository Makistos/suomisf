"""
Similar works: for every eligible work, a ranked list of similar works
with the reasons, for GET /api/works/<id>/similar. See
docs/work-similarity-plan.md.

A run first hashes its inputs; if nothing changed since the last run it
stops. Otherwise it scores every pair of eligible works, re-ranks for
variety and rewrites the lists that changed, in one short transaction.

Usage:
    python scripts/work_similarity.py              # dev database
    python scripts/work_similarity.py --dry-run    # compute and report only
    python scripts/work_similarity.py --rebuild    # even if nothing changed
    python scripts/work_similarity.py --work 63    # one work's list only
    python scripts/work_similarity.py --no-description  # tags etc. only
    python scripts/work_similarity.py --reembed    # embed all descriptions
    python scripts/work_similarity.py --report FILE [--works 63,1731]
    python scripts/work_similarity.py --prod       # production database
    python scripts/work_similarity.py --db postgresql://...

The database is DATABASE_URL from .env; --prod uses
DATABASE_URL_TAG_SIMILARITY_PROD (the tag_similarity role, see migrations
044, 051 and 052). Needs the similarity group: pdm install -G similarity.
Descriptions are embedded with multilingual-e5-large (about 2 GB, shared
with the tag job); the first run embeds every eligible description (about
12 minutes on a workstation CPU), later runs only new and changed ones.
"""
import argparse
import hashlib
import html
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import (Any, Callable, Dict, FrozenSet, Iterable, List,
                    Optional, Set, Tuple)

import dotenv
import numpy as np
from sqlalchemy import create_engine, make_url, text

directory_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
dotenv.load_dotenv(os.path.join(directory_path, '.env'))

# Bump whenever the config or the scoring changes: the next run then
# rewrites every list.
ALGORITHM_VERSION = 7

# Tag types (tagtype.id).
AIHE, ALAGENRE, TYYLI, TOIMIJA, PAIKKA, AIKA, LISTA = 1, 2, 3, 4, 5, 6, 7
TAG_TYPE_NAMES = {AIHE: 'Aihe', ALAGENRE: 'Alagenre', TYYLI: 'Tyyli',
                  TOIMIJA: 'Toimija', PAIKKA: 'Paikka', AIKA: 'Aika'}

# Work types (worktype.id).
NONFICTION = 4
# Contributor roles.
AUTHOR_ROLE = 1

# Genres (genre.id). Children's and young-adult genres fold into their
# base genre; the age group is handled by its own rules.
CHILD_GENRES = frozenset({11, 12, 15, 17})   # Lasten SF, Satu, Lasten
#                                              kuvakirja, Lasten fantasia
YA_GENRES = frozenset({8, 9, 10})            # Nuorten fantasia, SF, kauhu
NON_CONTENT_GENRES = frozenset({13, 14, 16})  # Ei SpeFiä, rajatapaus,
#                                               Kokoelma
BASE_GENRE = {8: 1, 17: 1, 9: 5, 11: 5, 10: 2, 15: None}

SIMILARITY_CONFIG: Dict[str, Any] = {
    # S = weighted mean of the signals both works have.
    # Genre is nearly always shared (Fantasia, SF), so it weighs little:
    # at 0.20 it made up 37 % of the scores without telling works apart.
    # Year only settles near ties: at 0.05 a close year was enough to lift
    # a weak match ("Kongo" for "Avaruuden portti").
    'signals': {'T': 0.40, 'D': 0.35, 'G': 0.10, 'Y': 0.01},
    # T is rescaled like D (median pair 0, top percentile 1), so the
    # weights above compare like with like. Unscaled, a weighted Jaccard
    # of 0.3 was already a good tag match while D reached 0.9.
    'rescale_tags': True,
    # T = weighted mean over the tag types both works have. Lista tags
    # (lists and editions, not content) are not used.
    # Aihe tags are the most specific signal (2 300 tags), Alagenre the
    # broadest (39; "dystopia" on 300 works): the spec's 0.45 / 0.20 let a
    # differing subgenre outweigh five shared themes.
    'tag_types': {ALAGENRE: 0.30, TYYLI: 0.25, AIHE: 0.35,
                  AIKA: 0.05, TOIMIJA: 0.05, PAIKKA: 0.05},
    # Per-type similarity: 'cosine' (shared weight / sqrt(product of the
    # two works' weights), so a richly tagged work isn't penalised) or
    # 'jaccard' (shared / union, the spec's).
    'tag_measure': 'cosine',
    # Tags that only one eligible work has can't be shared; left out, they
    # don't dilute that work's similarity to every other.
    'ignore_unique_tags': True,
    # Types whose score is also multiplied by the rarity of the shared
    # tags (mean weight / the weight of a tag on two works). Works have
    # one subgenre as a rule, so its cosine is 1 whenever it is shared:
    # "dystopia" (292 works) counted as much as "biopunk" (4). Now a
    # shared "dystopia" counts 0.34, "kova scifi" (26) 0.69. Tyyli is the
    # same (median one per work): "seikkailu" (400 works) counted 1.0.
    'rarity_scaled_types': (ALAGENRE, TYYLI),
    # A tag type counts for a pair when 'both' works have it (the spec)
    # or when 'either' has it (missing on one side = no match).
    'tag_type_available': 'either',
    # None = no cap: a tag on 2 works weighs ~7.7, "seikkailu" (400) ~2.3.
    # The spec's cap of 4 was reached by every tag on fewer than ~120
    # works, so rarity hardly told shared tags apart.
    'rarity_cap': None,
    'year_half_life': 30,
    'same_series_multiplier': 0.25,
    'audience_mismatch_multiplier': 0.5,   # young adult vs adult
    # Minimum evidence: a shared Alagenre or Tyyli tag, or this much Aihe
    # overlap, or this similar a description.
    'min_shared_general_tags': 2,
    'min_general_similarity': 0.15,
    'min_description_similarity': 0.25,
    'max_from_source_series': 1,
    'max_per_other_series': 1,
    'max_per_author': 2,
    'stored_per_work': 40,
    # Eligibility, both ways.
    'min_description_words': 20,
    'min_tags': 3,
}

# Description similarity: cosine of multilingual embeddings (phase 2
# compared TF-IDF, mpnet and e5; e5 found the most thematic neighbours).
# Vectors are stored in work_embedding, so only new and changed
# descriptions are embedded.
EMBED_MODEL = 'intfloat/multilingual-e5-large'
EMBED_PREFIX = 'query: '   # e5's prefix for symmetric similarity
# e5 cosines bunch near 0.8; D rescales them so that the median pair is 0
# and this percentile of pairs is 1.
D_TOP_PERCENTILE = 99.9
D_SAMPLE_ROWS = 1000      # rows used to find the median and the top

# texts -> unit vectors, one row per text
Embed = Callable[[List[str]], np.ndarray]

# Rows scored at a time: bounds memory to a few (CHUNK x works) arrays.
CHUNK = 256

# Optional description similarity: (eligible works) -> function giving
# the D rows for source indices [i0, i1), or None when unavailable.
DescriptionModel = Callable[[List['Work']], Callable[[int, int], np.ndarray]]


@dataclass(frozen=True)
class Work:
    id: int
    type: Optional[int] = None
    year: Optional[int] = None
    words: int = 0
    # Tag type -> tag ids (Lista left out).
    tags: Dict[int, FrozenSet[int]] = field(default_factory=dict)
    genres: FrozenSet[int] = frozenset()
    series: Optional[int] = None          # top-level book series
    authors: FrozenSet[int] = frozenset()  # real persons
    omnibus: FrozenSet[int] = frozenset()  # omnibuses it is (in)

    def tag_count(self) -> int:
        return sum(len(t) for t in self.tags.values())


@dataclass
class Rec:
    target: int
    score: float
    signals: Dict[str, Any]
    reasons: List[Dict[str, Any]]


# --- Pure helpers ------------------------------------------------------

def word_count(description: Optional[str]) -> int:
    """Words in a description, HTML tags and entities removed."""
    plain = html.unescape(re.sub(r'<[^>]+>', ' ', description or ''))
    return len(plain.split())


def plain_text(description: Optional[str]) -> str:
    plain = html.unescape(re.sub(r'<[^>]+>', ' ', description or ''))
    return ' '.join(plain.split())


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def eligible(work: Work, config: Dict[str, Any]) -> bool:
    return (work.words >= config['min_description_words']
            and work.tag_count() >= config['min_tags'])


def rarity(df: int, n: int, cap: Optional[float]) -> float:
    """Weight of a tag used by df of the n works that have its type."""
    weight = 1 + math.log((n + 1) / (df + 1))
    return weight if cap is None else min(cap, weight)


def year_similarity(a: float, b: float, half_life: float) -> float:
    return 2 ** (-abs(a - b) / half_life)


def base_genres(genres: Iterable[int]) -> FrozenSet[int]:
    out = set()
    for g in genres:
        if g in NON_CONTENT_GENRES:
            continue
        base = BASE_GENRE.get(g, g)
        if base is not None:
            out.add(base)
    return frozenset(out)


def is_children(genres: FrozenSet[int]) -> bool:
    return bool(genres & CHILD_GENRES)


# Age groups as bits, for works that aren't children's books.
YA, ADULT = 1, 2


def audience(genres: FrozenSet[int]) -> int:
    """YA and/or ADULT; a work with neither kind of genre counts as
    adult."""
    bits = YA if genres & YA_GENRES else 0
    if any(g not in YA_GENRES | CHILD_GENRES | NON_CONTENT_GENRES
           for g in genres):
        bits |= ADULT
    return bits or ADULT


def series_root(series_id: Optional[int],
                parents: Dict[int, Optional[int]]) -> Optional[int]:
    """The top-level series of a (sub-)series."""
    seen = set()
    while series_id is not None and series_id not in seen:
        seen.add(series_id)
        parent = parents.get(series_id)
        if parent is None:
            return series_id
        series_id = parent
    return series_id


# --- Scoring -----------------------------------------------------------

class Scorer:
    """Pair scores of the eligible works, a block of rows at a time."""

    def __init__(self, works: List[Work], config: Dict[str, Any],
                 description: Optional[Callable[[int, int], np.ndarray]]
                 = None):
        self.works = works
        self.config = config
        self.description = description
        n = len(works)
        self.n = n
        cap = config['rarity_cap']

        # Per tag type: binary matrix, rarity-weighted matrix, row sums.
        self.types: Dict[int, Dict[str, Any]] = {}
        self.rarity: Dict[int, float] = {}
        for ttype in config['tag_types']:
            have = [i for i, w in enumerate(works) if w.tags.get(ttype)]
            if not have:
                continue
            df = Counter(t for w in works for t in w.tags.get(ttype, ()))
            if config.get('ignore_unique_tags'):
                df = Counter({t: c for t, c in df.items() if c > 1})
            if not df:
                continue
            tag_ids = sorted(df)
            col = {t: j for j, t in enumerate(tag_ids)}
            r = np.array([rarity(df[t], len(have), cap) for t in tag_ids],
                         dtype=np.float32)
            for t in tag_ids:
                self.rarity[t] = float(r[col[t]])
            b = np.zeros((n, len(tag_ids)), dtype=np.float32)
            for i, w in enumerate(works):
                for t in w.tags.get(ttype, ()):
                    if t in col:
                        b[i, col[t]] = 1
            weighted = b * r
            self.types[ttype] = {
                'b': b, 'w': weighted, 'sum': weighted.sum(axis=1),
                'norm': np.sqrt((weighted * weighted).sum(axis=1)),
                # The weight of the rarest tag that can be shared.
                'r_max': rarity(2, len(have), cap)}

        genres = [base_genres(w.genres) for w in works]
        g_ids = sorted({g for gs in genres for g in gs})
        gcol = {g: j for j, g in enumerate(g_ids)}
        self.g = np.zeros((n, max(1, len(g_ids))), dtype=np.float32)
        for i, gs in enumerate(genres):
            for g in gs:
                self.g[i, gcol[g]] = 1
        self.g_sum = self.g.sum(axis=1)

        self.year = np.array(
            [w.year if w.year and w.year >= 1000 else np.nan
             for w in works], dtype=np.float64)
        self.series = np.array(
            [w.series if w.series is not None else -1 for w in works])
        self.nonfiction = np.array([w.type == NONFICTION for w in works])
        self.children = np.array([is_children(w.genres) for w in works])
        self.audience = np.array([audience(w.genres) for w in works])
        self.ids = np.array([w.id for w in works])
        self.t_scale = self._calibrate_tags()

    def _tags(self, rows: Any, shape: Tuple[int, int]) -> Dict[str, Any]:
        """Tag similarity of the given rows (a slice or index array)
        against every work: T, per type, and the evidence flags."""
        cfg = self.config
        t_num = np.zeros(shape)
        t_den = np.zeros(shape)
        per_type: Dict[int, np.ndarray] = {}
        shared_strong = np.zeros(shape, dtype=bool)
        general_ok = np.zeros(shape, dtype=bool)
        for ttype, m in self.types.items():
            weight = cfg['tag_types'][ttype]
            has_a, has_b = m['sum'][rows, None] > 0, m['sum'][None, :] > 0
            avail = ((has_a | has_b)
                     if cfg['tag_type_available'] == 'either'
                     else (has_a & has_b))
            if cfg.get('tag_measure') == 'cosine':
                inter = m['w'][rows] @ m['w'].T
                denom = m['norm'][rows, None] * m['norm'][None, :]
            else:
                inter = m['w'][rows] @ m['b'].T
                denom = m['sum'][rows, None] + m['sum'][None, :] - inter
            tc = np.where(avail, inter / np.where(denom > 0, denom, 1), 0)
            if ttype in cfg.get('rarity_scaled_types', ()):
                # Mean weight of the shared tags, relative to the rarest.
                shared_n = m['b'][rows] @ m['b'].T
                shared_r = m['b'][rows] @ m['w'].T
                tc = tc * np.where(
                    shared_n > 0,
                    shared_r / np.where(shared_n > 0, shared_n, 1)
                    / m['r_max'], 0)
            per_type[ttype] = np.where(avail, tc, np.nan)
            t_num += weight * tc
            t_den += weight * avail
            if ttype in (ALAGENRE, TYYLI):
                shared_strong |= inter > 0
            if ttype == AIHE:
                count = m['b'][rows] @ m['b'].T
                enough = tc >= cfg['min_general_similarity']
                general_ok = ((count >= cfg['min_shared_general_tags'])
                              | (avail & enough & (inter > 0)))
        all_types = sum(cfg['tag_types'][t] for t in self.types) or 1
        t_avail = t_den > 0
        return {'T': np.where(t_avail, t_num / np.where(t_avail, t_den, 1),
                              0),
                'avail': t_avail, 'coverage': t_den / all_types,
                'types': per_type, 'strong': shared_strong,
                'general': general_ok}

    def _calibrate_tags(self) -> Optional[Tuple[float, float]]:
        """(median, span to the top percentile) of T over a sample of
        rows, or None if T can't be rescaled (too few works or no
        spread)."""
        if not self.config.get('rescale_tags') or self.n < 2:
            return None
        rng = np.random.default_rng(0)
        idx = rng.choice(self.n, size=min(D_SAMPLE_ROWS, self.n),
                         replace=False)
        tags = self._tags(idx, (len(idx), self.n))
        mask = tags['avail'].copy()
        mask[np.arange(len(idx)), idx] = False   # not a work with itself
        values = tags['T'][mask]
        if values.size == 0:
            return None
        lo = float(np.median(values))
        hi = float(np.percentile(values, D_TOP_PERCENTILE))
        return (lo, hi - lo) if hi > lo else None

    def _scale_t(self, t: np.ndarray) -> np.ndarray:
        if self.t_scale is None:
            return t
        lo, span = self.t_scale
        return np.clip((t - lo) / span, 0, 1)

    def block(self, i0: int, i1: int) -> Dict[str, Any]:
        """Scores of rows [i0, i1) against every work."""
        cfg = self.config
        sig = cfg['signals']
        rows = slice(i0, i1)
        shape = (i1 - i0, self.n)

        tags = self._tags(rows, shape)
        t_avail, tag_cov = tags['avail'], tags['coverage']
        t_raw = tags['T']
        t = self._scale_t(t_raw)
        per_type = tags['types']
        shared_strong, general_ok = tags['strong'], tags['general']

        g_inter = self.g[rows] @ self.g.T
        g_union = self.g_sum[rows, None] + self.g_sum[None, :] - g_inter
        g_avail = (self.g_sum[rows, None] > 0) & (self.g_sum[None, :] > 0)
        g = np.where(g_avail, g_inter / np.where(g_union > 0, g_union, 1), 0)

        ya, yb = self.year[rows, None], self.year[None, :]
        y_avail = ~np.isnan(ya) & ~np.isnan(yb)
        y = np.where(y_avail,
                     2 ** (-np.abs(np.nan_to_num(ya - yb))
                           / cfg['year_half_life']), 0)

        if self.description is not None:
            d = self.description(i0, i1)
            d_avail = ~np.isnan(d)
            d = np.nan_to_num(d)
        else:
            d = np.zeros(shape)
            d_avail = np.zeros(shape, dtype=bool)

        num = (sig['T'] * t * t_avail + sig['D'] * d * d_avail
               + sig['G'] * g * g_avail + sig['Y'] * y * y_avail)
        den = (sig['T'] * t_avail + sig['D'] * d_avail
               + sig['G'] * g_avail + sig['Y'] * y_avail)
        s = np.where(den > 0, num / np.where(den > 0, den, 1), 0)
        coverage = (sig['T'] * tag_cov * t_avail + sig['D'] * d_avail
                    + sig['G'] * g_avail + sig['Y'] * y_avail) \
            / sum(sig.values())

        evidence = (shared_strong | general_ok
                    | (d_avail & (d >= cfg['min_description_similarity'])))
        src = np.arange(i0, i1)
        allowed = (
            evidence
            & (self.ids[rows, None] != self.ids[None, :])
            & (self.nonfiction[rows, None] == self.nonfiction[None, :])
            & (self.children[rows, None] == self.children[None, :]))
        allowed[np.arange(i1 - i0), src] = False

        mult = np.ones(shape)
        same_series = ((self.series[rows, None] == self.series[None, :])
                       & (self.series[rows, None] >= 0))
        mult[same_series] *= cfg['same_series_multiplier']
        mismatch = (~self.children[rows, None]
                    & ((self.audience[rows, None] & self.audience[None, :])
                       == 0))
        mult[mismatch] *= cfg['audience_mismatch_multiplier']

        final = np.where(allowed, s * mult * (0.5 + 0.5 * coverage), -1.0)
        return {'final': final, 'S': s, 'T': np.where(t_avail, t, np.nan),
                'T_raw': np.where(t_avail, t_raw, np.nan),
                'D': np.where(d_avail, d, np.nan),
                'G': np.where(g_avail, g, np.nan),
                'Y': np.where(y_avail, y, np.nan),
                'coverage': coverage, 'types': per_type,
                'same_series': same_series, 'multiplier': mult}


def weighted_parts(signals: Dict[str, Any], per_type: Dict[int, float],
                   config: Dict[str, Any]) -> Dict[str, Any]:
    """How much each signal adds to S, and each tag type to the tags'
    share: {"parts": {T, D, G, Y}, "type_parts": {tag type id: ...}}.
    The parts add up to S, the type parts to parts["T"]."""
    weights = config['signals']
    available = {n: signals[n] for n in ('T', 'D', 'G', 'Y')
                 if signals.get(n) is not None}
    den = sum(weights[n] for n in available) or 1
    parts = {n: round(weights[n] * v / den, 4)
             for n, v in available.items()}
    typed = {t: config['tag_types'][t] * v for t, v in per_type.items()}
    total = sum(typed.values())
    t_part = weights['T'] * available.get('T', 0) / den
    type_parts = {str(t): round(t_part * v / total, 4) if total else 0.0
                  for t, v in typed.items()}
    return {'parts': parts, 'type_parts': type_parts}


def _ratio(scaled: Optional[float], raw: Optional[float]) -> float:
    """How much rescaling multiplied T, for the reasons' contributions."""
    return scaled / raw if scaled is not None and raw else 1.0


def reasons_for(a: Work, b: Work, per_type: Dict[int, float],
                config: Dict[str, Any], rarity_of: Dict[int, float],
                d: Optional[float] = None,
                t_factor: float = 1.0) -> List[Dict[str, Any]]:
    """Shared tags by type and a similar description, the biggest
    contribution to S first; tags within a type rarest first. The
    description is a reason when D passes the minimum-evidence level."""
    weights = config['tag_types']
    signal = config['signals']
    t_den = sum(weights[t] for t in per_type) or 1
    out: List[Dict[str, Any]] = []
    for ttype, weight in weights.items():
        shared = a.tags.get(ttype, frozenset()) & b.tags.get(ttype,
                                                              frozenset())
        if not shared:
            continue
        tags = sorted(shared, key=lambda t: (-rarity_of.get(t, 0), t))
        out.append({'type': ttype, 'tags': tags,
                    'contribution': signal['T'] * weight * t_factor
                    * (per_type.get(ttype) or 0) / t_den})
    if d is not None and d >= config['min_description_similarity']:
        out.append({'type': 'description', 'tags': [],
                    'contribution': signal['D'] * d})
    out.sort(key=lambda r: (-r['contribution'], str(r['type'])))
    for r in out:
        r['contribution'] = round(r['contribution'], 4)
    return out


def pick(source: Work, ranked: List[int], works: List[Work],
         config: Dict[str, Any]) -> List[int]:
    """Greedy selection for variety: series and author caps, no shared
    omnibus. ranked = candidate indices, best first."""
    chosen: List[int] = []
    per_series: Counter = Counter()
    per_author: Counter = Counter()
    for j in ranked:
        cand = works[j]
        if source.omnibus & cand.omnibus:
            continue
        if cand.series is not None:
            limit = (config['max_from_source_series']
                     if cand.series == source.series
                     else config['max_per_other_series'])
            if per_series[cand.series] >= limit:
                continue
        if any(per_author[a] >= config['max_per_author']
               for a in cand.authors):
            continue
        chosen.append(j)
        if cand.series is not None:
            per_series[cand.series] += 1
        for a in cand.authors:
            per_author[a] += 1
        if len(chosen) >= config['stored_per_work']:
            break
    return chosen


def compute_lists(all_works: List[Work],
                  config: Optional[Dict[str, Any]] = None,
                  description: Optional[DescriptionModel] = None,
                  only: Optional[Set[int]] = None
                  ) -> Tuple[List[Work], Dict[int, List[Rec]]]:
    """(eligible works, ranked list per eligible work id). only = compute
    these source ids only (scores still use every eligible work)."""
    config = config or SIMILARITY_CONFIG
    works = [w for w in all_works if eligible(w, config)]
    lists: Dict[int, List[Rec]] = {}
    if not works:
        return works, lists
    scorer = Scorer(works, config,
                    description(works) if description else None)
    sources = [i for i, w in enumerate(works)
               if only is None or w.id in only]
    for c0 in range(0, len(sources), CHUNK):
        chunk = sources[c0:c0 + CHUNK]
        i0, i1 = chunk[0], chunk[-1] + 1
        blk = scorer.block(i0, i1)
        for i in chunk:
            row = blk['final'][i - i0]
            cand = np.nonzero(row > 0)[0]
            # Best first; ties by work id, so runs are repeatable.
            order = cand[np.lexsort((scorer.ids[cand], -row[cand]))]
            chosen = pick(works[i], order.tolist(), works, config)
            recs = []
            for j in chosen:
                k = i - i0
                per_type = {t: float(v[k, j])
                            for t, v in blk['types'].items()
                            if not np.isnan(v[k, j])}
                signals: Dict[str, Any] = {
                    name: (None if np.isnan(blk[name][k, j])
                           else round(float(blk[name][k, j]), 4))
                    for name in ('S', 'T', 'T_raw', 'D', 'G', 'Y')}
                signals['coverage'] = round(float(blk['coverage'][k, j]), 4)
                signals['types'] = {str(t): round(v, 4)
                                    for t, v in per_type.items()}
                signals['same_series'] = bool(blk['same_series'][k, j])
                signals['multiplier'] = round(float(blk['multiplier'][k, j]),
                                              4)
                signals.update(weighted_parts(signals, per_type, config))
                recs.append(Rec(
                    target=works[j].id, score=round(float(row[j]), 6),
                    signals=signals,
                    reasons=reasons_for(works[i], works[j], per_type,
                                        config, scorer.rarity,
                                        signals['D'],
                                        _ratio(signals['T'],
                                               signals['T_raw']))))
            lists[works[i].id] = recs
    return works, lists


# --- Database ----------------------------------------------------------

def fastembed_embedder() -> Embed:
    """e5 embeddings from fastembed (ONNX), the model cached in
    ~/.cache/fastembed (shared with scripts/tag_similarity.py)."""
    from fastembed import TextEmbedding  # pylint: disable=C0415
    model = TextEmbedding(EMBED_MODEL,
                          cache_dir=os.path.expanduser('~/.cache/fastembed'))

    def embed(texts: List[str]) -> np.ndarray:
        vectors = np.array(list(model.embed(
            [EMBED_PREFIX + t for t in texts], batch_size=16)),
            dtype=np.float32)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return embed


def embed_missing(texts: Dict[int, str],
                  stored: Dict[int, Tuple[str, bytes]], embed: Embed,
                  rebuild: bool = False
                  ) -> Tuple[Dict[int, np.ndarray],
                             List[Tuple[int, str, bytes]]]:
    """(vector per work, new vectors to store as (work, hash, bytes)).
    Only texts with no stored vector or a changed hash are embedded."""
    vectors: Dict[int, np.ndarray] = {}
    todo = []
    for wid, txt in texts.items():
        old = stored.get(wid)
        if old and old[0] == text_hash(txt) and not rebuild:
            vectors[wid] = np.frombuffer(old[1], dtype='<f4')
        else:
            todo.append(wid)
    new: List[Tuple[int, str, bytes]] = []
    if todo:
        start = time.monotonic()
        for wid, vector in zip(todo, embed([texts[w] for w in todo]),
                               strict=True):
            vector = vector.astype('<f4')
            vectors[wid] = vector
            new.append((wid, text_hash(texts[wid]), vector.tobytes()))
        print(f'Embedded {len(todo)} descriptions in '
              f'{time.monotonic() - start:.0f} s.')
    return vectors, new


def description_model(vectors: Dict[int, np.ndarray]) -> DescriptionModel:
    """D from the vectors: cosine rescaled so the median pair is 0 and the
    top D_TOP_PERCENTILE is 1. Works without a vector have no D."""
    def factory(works: List[Work]) -> Callable[[int, int], np.ndarray]:
        dim = len(next(iter(vectors.values())))
        have = np.array([w.id in vectors for w in works])
        m = np.vstack([vectors.get(w.id, np.zeros(dim, dtype=np.float32))
                       for w in works]).astype(np.float32)
        rng = np.random.default_rng(0)
        rows = np.nonzero(have)[0]
        sample = rng.choice(rows, size=min(D_SAMPLE_ROWS, len(rows)),
                            replace=False)
        cos = m[sample] @ m[have].T
        off = cos[cos < 0.9999]   # leave out each row's own work
        lo = float(np.median(off))
        hi = float(np.percentile(off, D_TOP_PERCENTILE))
        span = hi - lo if hi > lo else 1.0

        def block(i0: int, i1: int) -> np.ndarray:
            d = np.clip((m[i0:i1] @ m.T - lo) / span, 0, 1)
            d[~have[i0:i1], :] = np.nan
            d[:, ~have] = np.nan
            return d
        return block
    return factory


def load_texts(conn: Any, ids: Iterable[int]) -> Dict[int, str]:
    """Plain-text descriptions of the given works."""
    return {r.id: plain_text(r.description) for r in conn.execute(text(
        'SELECT id, description FROM work WHERE id = ANY(:ids)'),
        {'ids': list(ids)})}


def stored_vectors(conn: Any) -> Dict[int, Tuple[str, bytes]]:
    return {r.work_id: (r.text_hash, bytes(r.vector)) for r in
            conn.execute(text(
                'SELECT work_id, text_hash, vector FROM work_embedding '
                'WHERE model = :m'), {'m': EMBED_MODEL})}


def store_vectors(conn: Any, new: List[Tuple[int, str, bytes]]) -> None:
    if not new:
        return
    # Works deleted since they were read are left out.
    conn.execute(text(
        'INSERT INTO work_embedding (work_id, model, text_hash, vector) '
        'SELECT :w, :m, :h, :v WHERE EXISTS (SELECT 1 FROM work '
        'WHERE id = :w) ON CONFLICT (work_id, model) DO UPDATE SET '
        'text_hash = EXCLUDED.text_hash, vector = EXCLUDED.vector, '
        'updated = now()'),
        [{'w': w, 'm': EMBED_MODEL, 'h': h, 'v': v} for w, h, v in new])


def load_works(conn: Any) -> Tuple[List[Work], str]:
    """Every work with the inputs the scores use, and a hash of them."""
    parents = {r.id: r.parent_id for r in conn.execute(text(
        'SELECT id, parent_id FROM bookseries'))}
    tags: Dict[int, Dict[int, Set[int]]] = defaultdict(
        lambda: defaultdict(set))
    for r in conn.execute(text(
            'SELECT wt.work_id, t.id, t.type_id FROM worktag wt '
            'JOIN tag t ON t.id = wt.tag_id '
            'WHERE t.type_id IS NOT NULL AND t.type_id <> :lista'),
            {'lista': LISTA}):
        tags[r.work_id][r.type_id].add(r.id)
    genres: Dict[int, Set[int]] = defaultdict(set)
    for r in conn.execute(text(
            'SELECT work_id, genre_id FROM workgenre')):
        genres[r.work_id].add(r.genre_id)
    authors: Dict[int, Set[int]] = defaultdict(set)
    for r in conn.execute(text(
            'SELECT work_id, COALESCE(real_person_id, person_id) AS p '
            'FROM workcontributor WHERE role_id = :role'),
            {'role': AUTHOR_ROLE}):
        authors[r.work_id].add(r.p)
    omnibus: Dict[int, Set[int]] = defaultdict(set)
    for r in conn.execute(text('SELECT omnibus_id, work_id FROM omnibus')):
        omnibus[r.work_id].add(r.omnibus_id)
        omnibus[r.omnibus_id].add(r.omnibus_id)

    digest = hashlib.sha256()
    digest.update(json.dumps([ALGORITHM_VERSION, SIMILARITY_CONFIG],
                             sort_keys=True, default=str).encode())
    works = []
    for r in conn.execute(text(
            'SELECT id, type, pubyear, description, bookseries_id '
            'FROM work ORDER BY id')):
        w = Work(
            id=r.id, type=r.type, year=r.pubyear,
            words=word_count(r.description),
            tags={t: frozenset(ids) for t, ids in tags[r.id].items()},
            genres=frozenset(genres[r.id]),
            series=series_root(r.bookseries_id, parents),
            authors=frozenset(authors[r.id]),
            omnibus=frozenset(omnibus[r.id]))
        works.append(w)
        digest.update(json.dumps([
            w.id, w.type, w.year, w.series,
            hashlib.sha256((r.description or '').encode()).hexdigest(),
            sorted((t, sorted(ids)) for t, ids in w.tags.items()),
            sorted(w.genres), sorted(w.authors), sorted(w.omnibus),
        ]).encode())
    return works, digest.hexdigest()


def last_run(conn: Any) -> Optional[Any]:
    return conn.execute(text(
        'SELECT algorithm_version, input_hash, eligible_works, computed_at '
        'FROM work_similarity_run WHERE id = 1')).first()


def stored_lists(conn: Any) -> Dict[int, List[Tuple[int, Any, int]]]:
    """source -> [(target, reasons, algorithm_version)] in rank order."""
    out: Dict[int, List[Tuple[int, Any, int]]] = defaultdict(list)
    for r in conn.execute(text(
            'SELECT source_work_id, target_work_id, reasons, '
            'algorithm_version FROM work_similarity '
            'ORDER BY source_work_id, rank')):
        out[r.source_work_id].append(
            (r.target_work_id, r.reasons, r.algorithm_version))
    return out


def _key(recs: List[Rec]) -> List[Tuple[int, Any, int]]:
    return [(r.target, json.loads(json.dumps(r.reasons)), ALGORITHM_VERSION)
            for r in recs]


@dataclass
class Changes:
    rewritten: List[int] = field(default_factory=list)
    removed: List[int] = field(default_factory=list)


def plan_changes(stored: Dict[int, List[Tuple[int, Any, int]]],
                 lists: Dict[int, List[Rec]],
                 only: Optional[Set[int]] = None) -> Changes:
    """Lists to rewrite (new or different targets, order, reasons or
    version) and to remove (works no longer eligible)."""
    changes = Changes()
    for source, recs in lists.items():
        if stored.get(source, []) != _key(recs):
            changes.rewritten.append(source)
    if only is None:
        changes.removed = [s for s in stored if s not in lists]
    else:
        changes.removed = [s for s in only if s in stored
                           and s not in lists]
    return changes


def apply(conn: Any, lists: Dict[int, List[Rec]], changes: Changes,
          input_hash: Optional[str], eligible_count: int) -> None:
    """Write the changed lists; input_hash None = don't record a full
    run (single-work update)."""
    touched = changes.rewritten + changes.removed
    if touched:
        conn.execute(text(
            'DELETE FROM work_similarity WHERE source_work_id = ANY(:ids)'),
            {'ids': touched})
    rows = [{'s': source, 't': rec.target, 'rank': rank, 'score': rec.score,
             'sig': json.dumps(rec.signals), 'rea': json.dumps(rec.reasons),
             'v': ALGORITHM_VERSION}
            for source in changes.rewritten
            for rank, rec in enumerate(lists[source], start=1)]
    if rows:
        # Works deleted since they were read are left out.
        conn.execute(text(
            'INSERT INTO work_similarity (source_work_id, target_work_id, '
            'rank, score, signal_scores, reasons, algorithm_version) '
            'SELECT :s, :t, :rank, :score, CAST(:sig AS jsonb), '
            'CAST(:rea AS jsonb), :v '
            'WHERE EXISTS (SELECT 1 FROM work WHERE id = :s) '
            'AND EXISTS (SELECT 1 FROM work WHERE id = :t)'), rows)
    if input_hash is not None:
        conn.execute(text(
            'INSERT INTO work_similarity_run (id, algorithm_version, '
            'input_hash, eligible_works, computed_at) '
            'VALUES (1, :v, :h, :n, now()) ON CONFLICT (id) DO UPDATE SET '
            'algorithm_version = :v, input_hash = :h, eligible_works = :n, '
            'computed_at = now()'),
            {'v': ALGORITHM_VERSION, 'h': input_hash, 'n': eligible_count})


# --- Report ------------------------------------------------------------

def statistics(works: List[Work], lists: Dict[int, List[Rec]],
               shown: int = 8) -> Dict[str, float]:
    by_id = {w.id: w for w in works}
    n = len(lists) or 1
    tops = {s: recs[:shown] for s, recs in lists.items()}
    with_series = [s for s in tops if by_id[s].series is not None]
    series_hits = sum(
        1 for s in with_series
        if any(by_id[r.target].series == by_id[s].series for r in tops[s]))
    diversity = [len({a for r in recs for a in by_id[r.target].authors})
                 / len(recs) for recs in tops.values() if recs]
    return {
        'eligible': len(works),
        'with_list': sum(1 for recs in lists.values() if recs),
        'fewer_than_3': sum(1 for recs in lists.values() if len(recs) < 3)
        / n,
        'empty': sum(1 for recs in lists.values() if not recs) / n,
        'mean_shown': sum(len(r) for r in tops.values()) / n,
        'source_series_share': (series_hits / len(with_series)
                                if with_series else 0.0),
        'author_diversity': (sum(diversity) / len(diversity)
                             if diversity else 0.0),
    }


def report(conn: Any, works: List[Work], lists: Dict[int, List[Rec]],
           sample: List[int], database: str, seconds: float) -> str:
    titles = {r.id: (r.title, r.author_str, r.pubyear) for r in
              conn.execute(text(
                  'SELECT id, title, author_str, pubyear FROM work'))}
    tag_names = {r.id: r.name for r in conn.execute(text(
        'SELECT id, name FROM tag'))}
    by_id = {w.id: w for w in works}
    st = statistics(works, lists)
    out = [f'# Similar works report ({database})', '',
           f'Algorithm version {ALGORITHM_VERSION}, computed in '
           f'{seconds:.1f} s.', '',
           '| | |', '|---|---|',
           f'| Eligible works | {st["eligible"]} |',
           f'| With at least one recommendation | {st["with_list"]} |',
           f'| Fewer than 3 recommendations | '
           f'{st["fewer_than_3"]:.1%} |',
           f'| No recommendations | {st["empty"]:.1%} |',
           f'| Mean shown (top 8) | {st["mean_shown"]:.1f} |',
           f'| Lists (of works in a series) showing a work of the same '
           f'series | {st["source_series_share"]:.1%} |',
           f'| Author diversity (distinct authors / items, top 8) | '
           f'{st["author_diversity"]:.2f} |', '']

    def label(wid: int) -> str:
        title, author, year = titles.get(wid, ('?', '', None))
        return f'{title} ({author or "?"}, {year or "?"}) #{wid}'

    def fmt(v: Optional[float]) -> str:
        return '–' if v is None else f'{v:.2f}'

    for wid in sample:
        out.append(f'## {label(wid)}')
        out.append('')
        if wid not in by_id:
            out.append('Not eligible (needs a description of 20+ words '
                       'and 3+ tags).')
            out.append('')
            continue
        recs = lists.get(wid, [])[:8]
        if not recs:
            out.append('No recommendations.')
            out.append('')
            continue
        out.append('| # | Work | Score | T | D | G | Y | Cov. | Reasons |')
        out.append('|---|---|---|---|---|---|---|---|---|')
        for rank, rec in enumerate(recs, start=1):
            s = rec.signals
            reasons = '; '.join(
                'Kuvaus' if r['type'] == 'description' else
                f'{TAG_TYPE_NAMES[r["type"]]}: '
                + ', '.join(tag_names.get(t, str(t)) for t in r['tags'][:4])
                for r in rec.reasons[:3])
            flag = ' (sama sarja)' if s['same_series'] else ''
            out.append(f'| {rank} | {label(rec.target)}{flag} | '
                       f'{rec.score:.3f} | {fmt(s["T"])} | {fmt(s["D"])} | '
                       f'{fmt(s["G"])} | '
                       f'{fmt(s["Y"])} | {s["coverage"]:.2f} | {reasons} |')
        out.append('')
    return '\n'.join(out)


def default_sample(works: List[Work], count: int = 12) -> List[int]:
    """Evenly spaced eligible works, for a repeatable report."""
    if not works:
        return []
    step = max(1, len(works) // count)
    return [w.id for w in works[::step][:count]]


# --- Main --------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description='Compute similar-works recommendations.')
    parser.add_argument('--dry-run', action='store_true',
                        help='compute and print, write nothing')
    parser.add_argument('--rebuild', action='store_true',
                        help='compute even if the inputs have not changed')
    parser.add_argument('--no-description', action='store_true',
                        help='leave out description similarity (no model)')
    parser.add_argument('--reembed', action='store_true',
                        help='embed every description again')
    parser.add_argument('--work', type=int, metavar='ID',
                        help="recompute this work's list only")
    parser.add_argument('--report', metavar='FILE',
                        help='write a Markdown report')
    parser.add_argument('--works', metavar='IDS',
                        help='comma-separated work ids for the report')
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

    start = time.monotonic()
    only = {args.work} if args.work else None
    use_d = not args.no_description
    with engine.connect() as conn:
        conn.execute(text('SET search_path = suomisf'))
        all_works, input_hash = load_works(conn)
        # Lists computed without D are not the same as ones with it.
        input_hash = text_hash(input_hash + ('+D' if use_d else '-D'))
        previous = last_run(conn)
        unchanged = (previous is not None
                     and previous.input_hash == input_hash
                     and previous.algorithm_version == ALGORITHM_VERSION)
        if unchanged and not (args.rebuild or args.work or args.report
                              or args.dry_run or args.reembed):
            assert previous is not None
            print(f'{database}: no changes since '
                  f'{previous.computed_at:%Y-%m-%d %H:%M}; nothing to do.')
            conn.rollback()
            engine.dispose()
            return 0
        eligible_ids = [w.id for w in all_works
                        if eligible(w, SIMILARITY_CONFIG)]
        texts = load_texts(conn, eligible_ids) if use_d else {}
        vectors_stored = stored_vectors(conn) if use_d else {}
        stored = stored_lists(conn)
        conn.rollback()

    # Embedding can take minutes; no connection is held meanwhile.
    vectors: Dict[int, np.ndarray] = {}
    new_vectors: List[Tuple[int, str, bytes]] = []
    if use_d:
        # The model (2 GB) is loaded only if something needs embedding.
        vectors, new_vectors = embed_missing(
            texts, vectors_stored,
            lambda batch: fastembed_embedder()(batch), args.reembed)
        if new_vectors and not args.dry_run:
            # Saved at once: embedding is the slow part, and a later
            # error shouldn't make the next run do it again.
            with engine.begin() as conn:
                conn.execute(text('SET search_path = suomisf'))
                store_vectors(conn, new_vectors)
            new_vectors = []
    works, lists = compute_lists(
        all_works, only=only,
        description=description_model(vectors) if vectors else None)
    seconds = time.monotonic() - start

    if args.report:
        sample = ([int(x) for x in args.works.split(',') if x.strip()]
                  if args.works else default_sample(works))
        with engine.connect() as conn:
            conn.execute(text('SET search_path = suomisf'))
            body = report(conn, works, lists, sample, database, seconds)
            conn.rollback()
        with open(args.report, 'w', encoding='utf-8') as f:
            f.write(body + '\n')
        print(f'Report: {args.report}')

    if args.work and args.work not in lists:
        print(f'Work {args.work} is not eligible (needs a description of '
              f'{SIMILARITY_CONFIG["min_description_words"]}+ words and '
              f'{SIMILARITY_CONFIG["min_tags"]}+ tags).')
    changes = plan_changes(stored, lists, only)
    if only:
        print(f'{database}: work {args.work}: '
              f'{len(lists.get(args.work, []))} recommendations, '
              f'computed in {seconds:.1f} s.')
    else:
        st = statistics(works, lists)
        print(f'{database}: {st["eligible"]} eligible works, '
              f'{st["fewer_than_3"]:.1%} with fewer than 3 '
              f'recommendations, computed in {seconds:.1f} s.')
    if args.dry_run:
        verb = 'Would rewrite'
    else:
        # One short transaction for the vectors and the lists.
        with engine.begin() as conn:
            conn.execute(text('SET search_path = suomisf'))
            store_vectors(conn, new_vectors)
            apply(conn, lists, changes, None if only else input_hash,
                  len(works))
        verb = 'Rewrote'
    print(f'{verb} {len(changes.rewritten)} lists, removed '
          f'{len(changes.removed)}.')
    engine.dispose()
    return 0


if __name__ == '__main__':
    sys.exit(main())
