# Tag similarity: plan

Find tags that probably mean the same thing (candidates for merging) or are
closely related, and let an admin review them. Two signals:

1. **Usage** — how tags are used on works, short stories and articles.
2. **Meaning of the name** — a multilingual embedding model.

No hierarchy. The job runs now and then (e.g. after a batch of Kirjasampo
imports), so each run only does new work: it embeds new or renamed tags,
rescores, and never re-suggests a pair an admin has already decided on.

## Data today

- 3 110 tags; 17 346 work, 6 194 short story and 3 582 article links
  (person and magazine tags are negligible).
- Only 28 tags have a description, so the name is nearly all the text there
  is.
- No pgvector on the server, which is fine: 3 110 vectors fit in memory
  and the comparison is a single matrix product.
- No GPU; 32 cores and 31 GB RAM locally is ample for a small model.

## Signal 1: usage (SQL + numpy)

An item is a work, a short story or an article; every link counts once.

- **Containment**: the items two tags share, divided by the uses of the
  rarer one. Only pairs where both tags have at least 10 uses and share at
  least 3 items count. This finds *related* tags, and abbreviations the
  name can't ("science fiction" – "scifi").

NPMI and shared neighbours (second-order co-occurrence) were tried in phase
0 and dropped; see "Phase 0 results".

The whole thing is recomputed on every run: a few seconds, so nothing needs
to be stored between runs.

## Signal 2: meaning of the name (embeddings)

- **Models**: `intfloat/multilingual-e5-large` (with the `query: ` prefix)
  and `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`, run
  through `fastembed` (ONNX, no PyTorch). Name similarity is the mean of
  the two cosines. Local means no API keys, no per-run cost and the same
  results every time.
- **Text embedded**: the tag name alone.
- **Base-form check** (cheap, deterministic): each word of the name is
  reduced to its base forms with `libvoikko`; two names match when they
  have the same number of words and each pair of words shares a base form,
  e.g. "sota" / "sodat", "jyväskylä kesä" / "jyväskylän kesä". Not the
  `voikko` text-search config, which splits compounds.
- **Incremental**: each tag's vectors are stored with the model name and a
  hash of the embedded text, one row per model. A run embeds only tags with no vector, a
  changed hash (renamed) or a different model; deleted tags drop out
  through `ON DELETE CASCADE`. A full rebuild happens only when the model
  changes.

## Phase 0 results

184 pairs labelled by hand (d = duplicate, r = related, n = neither) on the
dev DB, 2026-11-04. "Duplicate" was read strictly: the same word in another
form or spelling. Synonyms and derived words ("väkivalta" – "väkivaltaisuus",
"amerikkalaiset" – "yhdysvaltalaiset") count as related.

| Signal | Pairs | d | r | n |
|---|---|---|---|---|
| Same base form (libvoikko, whole words) | 41 | 32 | 9 | 0 |
| Name similarity, top 100 (mean of e5-large and mpnet) | 100 | 6 | 91 | 3 |
| Containment (both ≥ 10 uses, ≥ 3 shared) | 25 | 2 | 21 | 2 |
| Shared neighbours (both ≥ 15 uses) | 20 | 0 | 12 | 8 |

Findings:

- **Base form finds the duplicates.** 78 % precision; the misses are a
  field and its practitioners ("arkeologia" – "arkeologit"), which are at
  least related. The `voikko` text-search config is unusable for this: it
  splits compounds, so "supersankarit" matched "antisankarit". The job uses
  the Python `libvoikko` bindings instead, comparing whole-word base forms
  word by word.
- **Name embeddings find related tags, not duplicates.** 97 of the top 100
  are duplicates or related, but only 6 are duplicates, and those are
  spelling variants and typos ("tsekkoslovakia" – "tšekkoslovakia",
  "taitelijaromaani"). So the embedding is the main *related* signal, and
  spelling variants get a rule of their own (below). Short look-alike
  words are the false positives ("valaat" – "valat", "muumit" – "muumiot").
- **Models**: e5-large ranks spelling variants highest, mpnet synonyms; the
  mean of the two works best. MiniLM was clearly worse. Adding work titles
  to the embedded text made results worse (the titles dominate); adding the
  type didn't help. So the text is the name alone.
- **Containment** (shared items / uses of the rarer tag) finds related
  tags, mostly narrower/broader ("pelit" – "konsolipelit"), plus
  abbreviations the name signals can't see ("science fiction" – "scifi",
  "suomen tieteiskirjoittajat" – "stk").
- **Shared neighbours**: dropped. For rare tags the profiles are identical
  and meaningless; for common ones it finds things of the same kind
  ("worldcon" – "eurocon"), and 8 of 20 were judged unrelated.
- **NPMI** at low counts is dominated by the tags of a single book series;
  containment with minimum counts replaces it.
- **Types**: many duplicates differ in type ("elokuva" Lista – "elokuvat"
  Aihe, "rikos" Tyyli – "rikokset" Aihe), so the merge dialog must show
  both types.
- **Speed**: embedding all 3 110 tags takes about 40 s (e5-large) and 20 s
  (mpnet) on the workstation CPU; together the models are about 3 GB on
  disk.

## Combining into suggestions

Each pair gets one of two kinds:

| Kind | Meaning | Rule |
|---|---|---|
| `duplicate` | Probably the same tag; merge | same base form, **or** a spelling variant: the names folded (lower case, diacritics and non-alphanumerics removed) are equal, or have a similarity ratio ≥ 0.9 with at least 5 characters, name similarity ≥ T1 (0.9), and they don't differ only in digits ("finncon 2007" – "finncon 2008") |
| `related` | Means nearly the same, or used together | not a duplicate, and name similarity ≥ T2 (0.94), **or** containment ≥ T3 (0.9) with both tags ≥ 10 uses and ≥ 3 shared items |

In the dev DB this gives 41 base-form and 12 spelling pairs, 122 name
pairs and 27 containment pairs. The spelling rule is about half right
("san fransisco", "lönnroot", "galápagossaaret" vs look-alikes such as
"valaat" – "valat"); a typo far from the original in meaning space
("tietokenepelit", 0.84) is missed. T2 = 0.94 and T3 = 0.9 are the lowest
scores that were labelled; below them precision is unknown, so lowering
them waits for real use. Name
similarity is the mean cosine of the e5-large and mpnet vectors.

The stored scores (name similarity, containment, shared item count) let the
UI show *why* a pair was suggested. Pairs across tag types are allowed, but
the UI shows both types, since e.g. Paikka "Japani" and Aihe "japani" can be
deliberate.

Only the top N per tag (e.g. 5) are kept, so the list stays reviewable.

## Storage (migration 044)

```sql
CREATE TABLE suomisf.tag_embedding (
    tag_id     integer NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    model      text NOT NULL,
    text_hash  text NOT NULL,
    vector     real[] NOT NULL,
    updated    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tag_id, model)
);

CREATE TABLE suomisf.tag_similarity (
    tag_a        integer NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    tag_b        integer NOT NULL REFERENCES suomisf.tag(id) ON DELETE CASCADE,
    kind         text NOT NULL,           -- 'duplicate' | 'related'
    reason       text NOT NULL,           -- 'baseform' | 'spelling' | 'name' | 'usage'
    name_score   real,
    containment  real,
    shared       integer NOT NULL DEFAULT 0,
    status       text NOT NULL DEFAULT 'new',   -- 'new' | 'dismissed'
    decided_by   integer REFERENCES suomisf."user"(id),
    decided_at   timestamptz,
    updated      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tag_a, tag_b),
    CHECK (tag_a < tag_b)
);
```

- A run upserts scores and `kind` but never touches `status`, so a
  dismissed pair stays dismissed. A `new` pair that no longer passes the
  thresholds is deleted; a dismissed one is kept.
- Merging tags deletes the source tag, and the cascade removes its pairs;
  nothing else is needed.

## The job: `scripts/tag_similarity.py`

Same shape as `scripts/check_data.py`: reads `DATABASE_URL`, with `--prod`
/ `--db URL` for another database.

```sh
.venv/bin/python scripts/tag_similarity.py            # incremental run
.venv/bin/python scripts/tag_similarity.py --dry-run  # report only, no writes
.venv/bin/python scripts/tag_similarity.py --rebuild  # re-embed everything
.venv/bin/python scripts/tag_similarity.py --report docs/tag-similarity-report.md
```

- The model dependencies go in an optional dependency group (`similarity`),
  so the web app and the server don't need them.
- It prints what it did: tags embedded, pairs added, updated or removed,
  and dismissed pairs kept.

## Getting the results to production

The script runs on a workstation and connects to the **production**
database directly, through the SSH tunnel described in
`docs/data-checks.md`. Nothing is exported or copied.

- **Reads from production**: the tags and tag links come from production,
  so the tag ids are the current ones and new tags get suggestions on the
  next run. Computing on the dev DB would use a stale snapshot: tags added,
  renamed or merged since the last refresh would be missing or wrong.
- **One short write**: all reading and computing happens first, and the
  writes (vectors and pairs) are a single transaction at the end that takes
  seconds. If a tag is merged or deleted in production while the script
  runs, its rows fail the foreign key check; the script drops those pairs
  and commits the rest.
- **Its own database role**: `check_data.py` connects read-only, and this
  script needs to write, so it gets a role of its own rather than the
  app's. A bug in the script then can't change anything else:

  ```sql
  CREATE ROLE tag_similarity LOGIN PASSWORD '...';
  GRANT USAGE ON SCHEMA suomisf TO tag_similarity;
  GRANT SELECT ON suomisf.tag, suomisf.tagtype, suomisf.worktag,
      suomisf.storytag, suomisf.articletag TO tag_similarity;
  GRANT SELECT, INSERT, UPDATE, DELETE
      ON suomisf.tag_embedding, suomisf.tag_similarity TO tag_similarity;
  ```

  Its URL goes in `.env` as `DATABASE_URL_TAG_SIMILARITY_PROD`, used with
  `--prod`. The script never reads `users` or anything else; for
  `decided_by` it needs no access, since only the API writes that column.
  Running it locally against the dev DB uses the normal `DATABASE_URL`.
- **Later, automatically**: if the job should run on a schedule instead,
  install the `similarity` group on the server and run the same script from
  cron with a local connection. Nothing else changes.

## API (admin only)

- `GET /api/tags/similar?kind=duplicate|related&status=new|dismissed`
  lists pairs with both tags (id, name, type, usage count) and the scores.
- `POST /api/tags/similar/dismiss` with `{tag_a, tag_b}` marks a pair "not
  the same" and records the admin and time; `.../restore` undoes it.
- Merging uses the existing `POST /api/tags/<source>/merge/<target>`; the
  pair disappears by cascade.

## Admin UI

A new card on `/admin`, "Samankaltaiset asiasanat":

- A DataTable with Duplicate / Related tabs (or a filter), sorted by score.
  Each row shows both tags as links, coloured by type as elsewhere (see
  `tag-type-to-severity.ts`), their usage counts and the reason ("Sama
  perusmuoto", "Kirjoitusasu", "Samankaltainen nimi", "Käytetään yhdessä",
  with scores in a tooltip).
- Actions: **Yhdistä** opens a confirm dialog that picks the target,
  defaulting to the more-used tag, with a swap button, and calls the
  existing merge. **Eri asiasanat** dismisses the pair. A "Hylätyt" view
  allows restoring a dismissed pair.
- When the job last ran is shown at the top, from the newest `updated`
  value.

## Phases

0. **Prototype and evaluate** — done 2026-11-04; see "Phase 0 results".
1. **Migration 044, the `tag_similarity` role and the job**, with
   incremental embedding, status preservation and `--dry-run`/`--report`. Pytest tests use a small
   fixture DB and a fake embedding function. Cover: the base-form and
   spelling rules, containment maths, incremental re-embedding on rename, dismissed
   pairs surviving a rerun, and cascades on tag delete.
2. **API endpoints** and their pytest tests.
3. **Admin card**, unit tests for the table and actions, and an E2E test
   for merging and dismissing a seeded pair. Changelog in both repos.

Later, if useful: "Related tags" on the tag page from the `related` pairs.
A Kirjasampo import that suggests a similar existing tag for a "Uusi" row
would need the model in the web app, or a precomputed lookup, so it is out
of scope for now.

## Risks and open questions

- **Short look-alike names** ("valaat" – "valat") get high name scores
  from both models; they are dismissed once.
- **Model size**: about 3 GB of models, downloaded on the first run into
  the fastembed cache. Fine on the workstation; worth remembering before
  moving the job to the server.
- **Rare tags**: tags with only one or two uses have no usable usage signal,
  so only the name signals apply to them. Most new
  Kirjasampo tags start out this way.
- **Deliberate near-duplicates** (e.g. "robotit" vs "androidit"): handled by
  dismissing them once.
- **Tunnel needed for each run**: running against production needs the SSH
  tunnel open. If that gets tedious, move to cron on the server (see
  "Getting the results to production").
