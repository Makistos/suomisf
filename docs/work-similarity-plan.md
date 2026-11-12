# Similar works: plan

Show 6–8 similar works on a work's page, each with a short reason drawn from
the data ("Yhteinen alalaji: avaruusooppera · Yhteinen tyyli: humoristinen").
Scores are computed by a batch job and stored; the page only reads them.

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
S = 0.40·T + 0.35·D + 0.20·G + 0.05·Y
```

over the signals available for both works, weights renormalised over that
set. Every eligible work has tags and a description, so in practice only
G and Y can be missing.

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

Phase 2. TF-IDF + cosine over the HTML-stripped description:

- Voikko base forms (word unigrams and bigrams; Voikko is already used by
  the tag job and the search) together with character 3–5-grams, since
  Finnish compounds defeat plain word matching. Evaluation decides the mix.
- Boilerplate: 3 038 descriptions are back-cover texts ("Takakansi"), with
  marketing and author bios. Sentences that repeat across many works
  (document frequency over a threshold) are dropped before vectorising;
  the evaluation script shows what was dropped.
- Multilingual sentence embeddings (fastembed, the models the tag job
  already uses) are compared side by side in the evaluation script; they
  replace or join TF-IDF only if the results are better.

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
    ON suomisf.work_similarity, suomisf.work_similarity_run TO tag_similarity;
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
2. **Description similarity (D)**, TF-IDF with boilerplate removal;
   embeddings compared in the report. Review again.
3. **API** with tests and docs.
4. **Frontend (admin-only button)** with tests; wiki (Ylläpito while it is
   admin-only, Teossivu in the user guide once opened to everyone; the
   job in Ylläpito); changelog.
5. **Production**: grants, migration, first `--prod` run.

Each phase is its own commit (or a few), changelog entries separately.
