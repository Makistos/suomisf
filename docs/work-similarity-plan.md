# Similar works: plan

Show 6–8 similar works on a work's page, each with a short reason drawn from
the data ("Yhteinen alalaji: avaruusooppera · Yhteinen tyyli: humoristinen").
Scores are computed by a batch job and stored; the page only reads them.

The current algorithm, without the history, is described in
`work-similarity-algorithm.md`.

Based on the spec `Similar works – AI agent spec.md` (frontend repo root),
adapted to the actual data below. Decisions made with the maintainer on
2026-11-12 are marked **(decided)**.

## Data today (production copy, 2026-11-11)

| | Works |
|---|---|
| All works | 7 299 |
| Any tag | 3 570 |
| Description of 20+ words | 6 364 |
| Genre | 7 274 |
| Original year (`work.pubyear`) | 7 298 (one is 0 → missing) |
| In a book series | 3 268 |
| **Description of 20+ words and 3+ tags (Lista not counted)** | **2 509** |

Tagging is in progress, so the last number grows; nothing in the design
depends on it staying small, but it is measured on every run.

## Which works take part (decided)

A work is **eligible** if its description (HTML stripped) has at least 20
words and it has at least 3 tags of the types below (Lista not counted).
The limit applies both ways: only eligible works get recommendations and
only eligible works are recommended. Other works show no section. A work
becomes eligible on the next run after it gets its description or third
tag.

Further rules for candidates:

- **Never** the work itself, an omnibus that contains it, or a work in the
  same omnibus (`omnibus`, 149 rows; `omnibus_contents` is empty). Editions belong to exactly
  one work (`edition.work_id`), so other editions never appear.
- **Non-fiction only for non-fiction (decided)**: work type Tietokirja (4)
  is recommended only for Tietokirja and vice versa. Novels, collections,
  anthologies and booklets mix.
- **Children's books stay apart (decided)**: a work is a children's book if
  it has a genre Lasten SF (11), Lasten fantasia (17), Lasten kuvakirja (15)
  or Satu (12). Children's books are recommended only for children's books.
- **Young adult vs adult (decided)**: Nuorten fantasia (8), Nuorten SF (9)
  and Nuorten kauhu (10) mark young-adult works. A pair where one is
  young-adult and the other adult gets `score × 0.5`. A work with both an
  adult and a young-adult genre counts as both.

## Scoring

```
S = 0.40·T + 0.35·D + 0.10·G + 0.05·Y
```

over the signals available for both works, weights renormalised over that
set. Every eligible work has tags and a description, so in practice only
G and Y can be missing.

**Balance (algorithm version 3, 2026-11-13).** With the spec's weights
(G 0.20) and T unscaled, the actual shares of the top-8 scores were T 20 %,
D 36 %, G 37 %, Y 7 %: a weighted Jaccard of 0.3 is already a good tag
match while the rescaled D reached 0.9, and genre is shared by nearly
every candidate (Fantasia, SF), so it added the same to all. 20 % of the
shown works shared no tag, and the description was the first reason for
73 %. Now T is rescaled like D (median pair 0, top 0.1 % of pairs 1,
computed from a sample of 1 000 rows; `T_raw` in `signal_scores` keeps
the unscaled value, and the minimum-evidence rules use the unscaled
per-type values) and G weighs 0.10. Shares became T 36 %, D 38 %, G 19 %,
Y 8 %; works sharing no tag 13 %; the description first reason for 49 %.

**Shared themes (algorithm version 4, 2026-11-13).** Pairs sharing several
Aihe tags still rarely made the top 8: of 1 872 pairs (not in the same
series) sharing 3+ Aihe tags, 163. Two causes: Jaccard divides by all of
both works' tags, so "Kafka rannalla" (26 Aihe tags) and "Harjukaupungin
salakäytävät" sharing five scored 0.18 on Aihe; and Alagenre (0.45)
outweighed Aihe (0.20), so differing subgenres wiped out five shared
themes ("Egalian tyttäret" → "Herland": T 0.08). Also the rarity cap of 4
was reached by every tag on fewer than ~120 works (2 291 of 2 297 Aihe
tags), so rarity hardly told shared tags apart. Changes:

- per-type similarity is the **cosine** of the rarity-weighted tag
  vectors (shared weight² / √(product of the two works' weight² sums)),
  `tag_measure: 'cosine'`; Jaccard remains an option;
- type weights **Aihe 0.35, Alagenre 0.30**, Tyyli 0.25, others 0.05;
- **no rarity cap** (`rarity_cap: None`): a tag on 2 works weighs ~7.7,
  "seikkailu" (400 works) ~2.3;
- tags on only one eligible work are left out of the comparison
  (`ignore_unique_tags`): they can't be shared and, uncapped, would weigh
  the most.

Result: pairs sharing 3+ Aihe tags in the top 8 163 → 241, top-8 items
with 2+ shared Aihe tags 1 037 → 1 590, items sharing no tag 2 623 →
1 432. "Egalian tyttäret" now lists "Pimeän pesä, paratiisi" (matriarkaatti,
feminismi, sukupuoliroolit); "Herland" → "Egalian tyttäret" rose from 332nd
to 20th.

The API also returns each item's `score` and `signals`, and the admin
dialog shows them, with the shared themes whenever there are two or more.

**Subgenre by rarity (algorithm version 5, 2026-11-13).** The values in the
dialog showed that a shared subgenre always scored 1.0 (one tag each, so
the cosine can't see its rarity): "dystopia" carried nearly the whole
"Egalian tyttäret" list and "kova scifi" put "Yksin Marsissa" in the
"Synkkä metsä" list with a near-average description. The Alagenre score
is now multiplied by the shared subgenre's rarity weight relative to a
tag on two works ("dystopia" 0.34, "kova scifi" 0.69). Pairs sharing 3+
themes in the top 8 241 → 283, items with 2+ shared themes 1 590 →
1 826, items sharing no tag 1 432 → 1 286. "Egalian tyttäret" gained
"Naisten planeetta" and "Valmiissa maailmassa". "Synkkä metsä" barely
changed: nearly all its candidates share "kova scifi", so the discount
hits them equally.

**Year and style (algorithm version 6, 2026-11-13).** "Kongo" was 7th for
"Avaruuden portti": the only shared tag was "seikkailu" (Tyyli, on ~400
works, but one Tyyli tag per work as a rule, so it scored 1.0 like the
subgenre did), and a close year settled the near tie. Year now weighs
0.01 instead of 0.05, and Tyyli is discounted by rarity like Alagenre
(a shared "seikkailu" counts ~0.3). "Kongo" fell to 36th. Pairs sharing
3+ themes in the top 8 283 → 337, items with 2+ shared themes 1 826 →
2 287, items sharing no tag 1 286 → 1 022.

**Weighted parts (algorithm version 7, 2026-11-13).** The raw values in the
dialog misled ("Vuosi 0,51" though the year weighs 0.01). The job stores
each signal's share of S (`parts`, adding up to S), the tag types' shares
of the tags' part (`type_parts`) and the series/age-group `multiplier`;
the dialog shows each share with the raw value in brackets, the tag types
that share something, and how the score comes from S.

### T: tags by type

Weighted Jaccard per tag type, then combined:

```
T_c = Σ r_t (shared tags of type c) / Σ r_t (union, type c)
r_t = min(4, 1 + ln((N_c + 1) / (df_t + 1)))
T   = Σ w_c·T_c / Σ w_c      over types both works have
```

`N_c` = eligible works with a tag of type c, `df_t` = eligible works with
tag t.

**Missing types (changed from the spec, to be confirmed).** The spec makes a
type that either work lacks unavailable (neither 0 nor a match). In phase 1
that let a sparsely tagged work match perfectly on one shared common tag:
"Etelän tähti" got eight works sharing only "seikkailu", each with T = 1.0.
The job now counts a type when *either* work has it, so a type missing on
one side is no match (`tag_type_available: 'either'`; `'both'` is the
spec's rule). With the 3-tag eligibility a missing type is informative.

| Spec name | Tag type in the DB | Weight |
|---|---|---|
| subgenre | Alagenre (2), 40 tags | 0.45 |
| style | Tyyli (3), 95 tags | 0.25 |
| general | Aihe (1), 2 554 tags | 0.20 |
| era | Aika (6), 100 tags | 0.05 |
| actors | Toimija (4), 693 tags | 0.05 |
| — | Paikka (5), 551 tags | 0.05 **(decided)** |
| — | Lista (7), 15 tags | not used **(decided)**: klassikot, elokuva, selkokieli, gutenberg… describe lists and editions, not content |

### D: description

Phase 2 compared three ways on the eligible works (2026-11-12):

| Way | Found | Problem |
|---|---|---|
| TF-IDF over Voikko base forms (+ compound parts, bigrams) | same-series works (0.3–0.4) | otherwise 0.06–0.16, half noise; names in the text leak ("Playground" by Lars Kepler → the Kepler62 books, worse with character n-grams) |
| paraphrase-multilingual-mpnet | some good (Bulgakov → Gogol's "Nenä") | noisy; reads only the first 128 tokens |
| **multilingual-e5-large** | themes: "Tik-Tok" → Dick's "Rakennamme sinut", Bulgakov → "Saatanalliset säkeet", "Pimenevä maa" → other post-apocalyptic books | first run 12 minutes |

**D is the cosine of e5-large vectors** of the plain-text description
(prefix `query: `), rescaled per run so that the median pair is 0 and the
top 0.1 % of pairs is 1 (e5 cosines bunch near 0.8). The vectors are
stored (`work_embedding`, migration 052) with a hash of the text, so a run
embeds only new and changed descriptions; the first run on the dev DB
embedded 2 509 descriptions in 12.5 minutes, later runs take seconds. The
model is loaded only when something needs embedding. No boilerplate
removal: the repeated sentences found (38) were mostly duplicate works,
and e5 copes with back-cover phrasing. `--no-description` runs without D.

When D ≥ the minimum-evidence level it is also a reason
(`{"type": "description"}`, shown as "Samankaltainen kuvaus"), ordered by
its contribution among the tag reasons.

### G: genre

Jaccard over base genres, with age groups folded in (Nuorten/Lasten
fantasia → Fantasia, Nuorten/Lasten SF → SF, Nuorten kauhu → Kauhu; the age
group is handled by the rules above). Kokoelma (16), rajatapaus (14) and
Ei SpeFiä (13) describe form or classification, not content, and are left
out; a work with only those has no G.

### Y: original year

`Y = 2^(-|yearA - yearB| / 30)` from `work.pubyear` (the original
publication year; editions have their own). Years below 1000 count as
missing.

### Not used positively

Author, title, edition data.

### Thin evidence

Renormalisation lets a pair with one shared rare tag and little else score
high. The ranking score is `S × (0.5 + 0.5·coverage)`, coverage = the
weight share of available signals and tag types. Checked with the
evaluation script and adjusted if needed.

## Minimum evidence

A candidate is kept only if at least one holds:

- it shares an Alagenre or Tyyli tag,
- it shares 2+ Aihe tags or `T_Aihe ≥ 0.15`,
- `D ≥ 0.25`.

Year, genre, era, actor or place tags alone are never enough. If only 3
candidates qualify, 3 are stored; the list is not padded.

## Series and diversity (re-ranking)

- **Series by top-level series**: book series nest (`bookseries.parent_id`,
  57 sub-series), so each work's series is followed up to its root and
  compared by that. Publisher series (on editions) don't count.
- A candidate in the source work's series gets `score × 0.25`.
- Greedy pick from the ranked list: at most 1 from the source's series, at
  most 1 from any other series, at most 2 by the same author. Authors are
  role 1 in `workcontributor`, counted by real person (`real_person_id`
  when set) so pseudonyms don't get around the limit.

## Candidates and speed

No separate candidate generation: every pair is scored, a block of 256
source rows at a time, as numpy matrix products (per tag type: rarity-
weighted works × tags times works × tags transposed). Measured in phase 1
on 2 509 eligible works: **3 s and 640 MB** for the whole run (0.3 s for
`--work`), so there is nothing to optimise. Memory grows with the block
size × the number of works, not with the square, so the growing number of
tagged works is no concern. The spec's genre candidate set would add
nothing anyway: genre alone never passes the minimum evidence.

## Storage (migration 051)

```sql
CREATE TABLE suomisf.work_similarity (
    source_work_id  integer NOT NULL REFERENCES suomisf.work(id) ON DELETE CASCADE,
    target_work_id  integer NOT NULL REFERENCES suomisf.work(id) ON DELETE CASCADE,
    rank            smallint NOT NULL,
    score           real NOT NULL,
    signal_scores   jsonb NOT NULL,   -- T, D, G, Y, per tag type, coverage
    reasons         jsonb NOT NULL,   -- shared tag ids per type, ordered by contribution
    algorithm_version integer NOT NULL,
    computed_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_work_id, target_work_id)
);
CREATE INDEX ON suomisf.work_similarity (source_work_id, rank);

-- One row: what the last run was computed from.
CREATE TABLE suomisf.work_similarity_run (
    id integer PRIMARY KEY CHECK (id = 1),
    algorithm_version integer NOT NULL,
    input_hash text NOT NULL,
    eligible_works integer NOT NULL,
    computed_at timestamptz NOT NULL
);
```

The top 40 per work are stored (the page shows up to 8; the rest feed the
evaluation and leave room for later filtering).

## The job: `scripts/work_similarity.py`

Same shape as `scripts/tag_similarity.py`: `similarity` dependency group,
reads `DATABASE_URL`, `--prod` for production through the SSH tunnel
(`docs/tag-similarity-running.md`).

```sh
.venv/bin/python scripts/work_similarity.py              # run if anything changed
.venv/bin/python scripts/work_similarity.py --dry-run    # compute and report, no writes
.venv/bin/python scripts/work_similarity.py --work 63    # one work's list only
.venv/bin/python scripts/work_similarity.py --rebuild    # ignore the fingerprint
.venv/bin/python scripts/work_similarity.py --prod
```

**Run as needed (decided).** The job hashes every input it reads (eligible
works' tags, genres, descriptions, years, series, authors, types, omnibus
links) together with `algorithm_version`. If the hash equals the stored
one, it prints "no changes" and exits in a second or two. Otherwise it
recomputes everything (rarity and description weights depend on all works,
so a partial update would drift) and rewrites, in one transaction at the
end, only the lists that changed. It prints eligible works, lists changed,
works with fewer than 3 recommendations and the time taken.

All weights and thresholds are in one `SIMILARITY_CONFIG` dict in the
script; changing any of them means bumping `algorithm_version`, which also
forces the next run.

**Database role.** The existing `tag_similarity` role is reused; it gets
read access to what the job reads and write access to the two new tables:

```sql
GRANT SELECT ON suomisf.work, suomisf.workgenre, suomisf.workcontributor,
    suomisf.bookseries, suomisf.omnibus TO tag_similarity;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON suomisf.work_similarity, suomisf.work_similarity_run,
    suomisf.work_embedding TO tag_similarity;
```

(`tag` and `worktag` it can already read.)

## API

```
GET /api/works/<id>/similar?limit=8
```

Public, no login. Up to `limit` (max 40) items in rank order: work id,
title, author string, original year, the cover thumbnail of its first
edition when one exists, and `reasons` — a list of
`{type, tags: [{id, name}]}` ordered by contribution, era/actor/place only
when nothing stronger exists, plus a description reason ("Samankaltainen
kuvaus") when D is the main contributor. No score in the response
(the page never shows one). A work with no rows gives `[]`, not an error.
Documented in the docstring like the other routes.

## Frontend

**Admins only at first (decided):** a "Samankaltaisia teoksia" button on
the work page, shown only to admins (`isAdmin`), opens the list; the
results are test-driven before visitors see them. The API stays public
(it only exposes public catalogue data), so opening it to everyone later
is a frontend change.

The button is hidden when the work has no recommendations; loading and
errors are handled like the page's other admin dialogs. Each item: cover
thumbnail if any, title (link), author, year, and 1–2 reasons.
Placement is decided with a screenshot in that phase. Once it is opened to
visitors, it becomes a section on the page, hidden when the list is empty.

## Tests

- **Job (pytest, fake data, no DB)**: weighted Jaccard; unavailable vs
  zero tag types; renormalisation; the year function; base-genre folding
  and the age-group rules; the non-fiction rule; series root and the
  series penalty; the diversity caps with pseudonyms; minimum evidence;
  omnibus exclusion; eligibility; the fingerprint (unchanged input → no
  writes).
- **API**: one test with fixture rows, one for a work with none.
- **Frontend (Vitest)**: the section with mock data, and the empty state.
- Documented in `tests/TEST_DOCUMENTATION.md` / `tests/README.md`.

## Evaluation script

`scripts/work_similarity.py --report FILE --works 63,1731,...` writes, for
the given works, the top 8 with each signal and the reasons, and for the
whole run: how often the source's series appears, author diversity, the
share of eligible works with fewer than 3 recommendations, and (phase 2)
TF-IDF vs embedding results side by side. It comes in phase 1, since the
weights can't be judged without it.

## Phases

1. **Migration 051, the job with T + G + Y, all rules, storage,
   fingerprint, evaluation report, tests** — done 2026-11-12
   (`tests/test_work_similarity.py`, 24 tests). On the dev DB: 2 509
   eligible works, 99.3 % get recommendations, 2.4 % fewer than 3, 3.8 %
   of lists of series works show one of the same series, author diversity
   0.97. Weak spot: works whose own tags are rare lean on one common tag
   ("seikkailu") plus genre and year — what D is for.
2. **Description similarity (D)** — done 2026-11-12 with e5-large
   embeddings (see D above; 29 tests). Every eligible work now gets a list
   (0.2 % fewer than 3), same-series works show in 0.3 % of lists, author
   diversity 0.98. Lists for works with few shared tags (e.g. "Pimenevä
   maa", "Painajaisakatemia 3", "Tik-Tok", "Ubik") are clearly better.
   To watch: D often dominates; some lists now rest on the description
   alone (T 0).
3. **API** with tests and docs — done 2026-11-12
   (`app/impl_work_similarity.py`, `tests/api/test_work_similarity_api.py`,
   6 tests). Reasons come with tag names and a `type_name`; tags deleted
   since the last run are left out.
4. **Frontend (admin-only button)** with tests; wiki (Ylläpito while it is
   admin-only, Teossivu in the user guide once opened to everyone; the
   job in Ylläpito); changelog — done 2026-11-12 (frontend `e08e776`,
   `src/features/work/components/similar-works.tsx`, 4 Vitest tests; wiki
   Ylläpito "Samankaltaiset teokset"). The button sits in the work page's
   right column under the Kirjasampo import.
5. **Production**: grants, migration, first `--prod` run.

Each phase is its own commit (or a few), changelog entries separately.
