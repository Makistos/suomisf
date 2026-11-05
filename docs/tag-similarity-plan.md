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

## Signal 3: places (Wikidata)

Paikka tags that name a real place are matched to a Wikidata item, and
a place is related to the nearest tag it lies in.

- **Matching**: the tag name (qualifiers such as "(paikka)" dropped) is
  searched among Finnish labels and aliases; only exact matches count.
  A match must be an instance of a geographic feature, administrative
  area, country, continent or region (followed through "subclass of",
  P279), not fictional, and have a Finnish description, which leaves out
  obscure namesakes (a village called Mars). Of several matches, the one
  with the most Wikipedia articles wins, unless an astronomical object
  of the same name has more ("europa" is Jupiter's moon, not the island).
  Kinds of place ("kahvilat", "vankilat") and cosmic or mythical places
  don't match. Better-known namesakes of other kinds don't rule a place
  out: the languages "englanti", "kiina" and "persia" outrank the places.
- **Ancestors**: the items a place is in through "located in" (P131) and
  "country" (P17), current statements only, so Turku is not in Sweden.
  The continent (P30) is used only when these reach no tag. A region in
  several countries is in none of them.
- **Pairs**: tags matched to the same item are duplicates ("usa" –
  "yhdysvallat"); a place and its nearest tagged ancestors are related
  ("new york" – "usa", "turku" – "suomi", not "turku" – "eurooppa").
- **Incremental**: each tag's match and ancestors are stored, so a run
  looks up only new and renamed Paikka tags (`--rebuild` all of them,
  `--no-places` none). A row marked `manual` is never looked up again,
  so a wrong match can be fixed by hand.
- **Cost**: a full lookup of the 398 Paikka tags takes about 4 minutes
  (mostly the class hierarchy, fetched once per run); a rerun with no
  new tags makes no requests.

Probe on the dev DB, 2026-11-05: 188 of 398 Paikka tags matched a real
place, 3 of them wrongly ("europa" a French island, "saaret" a Greek
regional unit, "onnela" an inn; "europa" fixed since by the
astronomical-namesake check); "ahvenanmaa" and "orangen piirikunta"
were missed. Of 166 place pairs labelled, 164 were useful, including 70
of 71 country – continent pairs. It also found 4 duplicates the name
rules miss ("alankomaat" – "hollanti", "tasmania" – "van diemenin maa").

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
| `duplicate` | Probably the same tag; merge | same base form, **or** the same Wikidata place, **or** a spelling variant: the names folded (lower case, diacritics and non-alphanumerics removed) are equal, or have a similarity ratio ≥ 0.9 with at least 5 characters, name similarity ≥ T1 (0.9), and they don't differ only in digits ("finncon 2007" – "finncon 2008") |
| `related` | Means nearly the same, in the same place, or used together | not a duplicate, and one place lies in the other, **or** name similarity ≥ T2 (0.91), **or** containment ≥ T3 (0.9) with both tags ≥ 10 uses and ≥ 3 shared items |

In the dev DB this gives 42 base-form and 11 spelling pairs, 410 name
pairs and 26 containment pairs (489 in all, after the limit per tag). The spelling rule is about half right
("san fransisco", "lönnroot", "galápagossaaret" vs look-alikes such as
"valaat" – "valat"); a typo far from the original in meaning space
("tietokenepelit", 0.84) is missed. Name similarity is the mean cosine of
the e5-large and mpnet vectors.

A second sheet of 110 pairs sampled just below the first thresholds set
T2 and T3:

| Band | Pairs in the dev DB | Useful (d or r) of those labelled |
|---|---|---|
| name 0.92–0.94 | 159 | 39 / 40 |
| name 0.91–0.92 | ≈ 160 | 15 / 15 |
| name 0.90–0.91 | ≈ 190 | 17 / 24 |
| containment 0.8–0.9 | 17 | 8 / 11 |
| containment 0.7–0.8 | 36 | 11 / 19 |

So T2 = 0.91; below it short look-alikes take over ("karpaatit" –
"kärpät", "kallot" – "klovnit"). T3 stays at 0.9: below it containment
finds themes of a genre ("dystopia" – "jengit") and single-series
artefacts ("rooma" – "gutenberg").

The stored scores (name similarity, containment, shared item count) let the
UI show *why* a pair was suggested. Pairs across tag types are allowed, but
the UI shows both types, since e.g. Paikka "Japani" and Aihe "japani" can be
deliberate.

Only the top N per tag (e.g. 5) are kept, so the list stays reviewable.

## Storage (migration 044)

`migrations/044_tag_similarity.sql` adds two tables:

- `tag_embedding (tag_id, model)`: the vector of each tag per model as
  float32 bytes (`bytea`, a quarter the size of `real[]` over the tunnel;
  about 21 MB for both models), with a hash of the embedded text, so a
  renamed tag is re-embedded.
- `tag_similarity (tag_a < tag_b)`: `kind` (duplicate / related), `reason`
  (baseform / spelling / name / usage), `name_score`, `containment`,
  `shared`, `status` (new / dismissed), `decided_by`, `decided_at` and
  `updated`.

Migration 045 adds `tag_place (tag_id)`: a Paikka tag's Wikidata item
(NULL if it is not a real place), label, description, ancestors with
their depth (`jsonb`), the hash of the name looked up and a `manual`
flag, and allows the reason `place`.

All reference `tag` with `ON DELETE CASCADE`.

- A run upserts scores and `kind` but never touches `status`, so a
  dismissed pair stays dismissed. A `new` pair that no longer passes the
  thresholds is deleted; a dismissed one is kept.
- Merging tags deletes the source tag, and the cascade removes its pairs;
  nothing else is needed.

## The job: `scripts/tag_similarity.py`

How to set up and run it, including the production tunnel and role:
`tag-similarity-running.md`.

Same shape as `scripts/check_data.py`: reads `DATABASE_URL`, with `--prod`
/ `--db URL` for another database.

```sh
pdm install -G similarity                             # once
.venv/bin/python scripts/tag_similarity.py            # incremental run
.venv/bin/python scripts/tag_similarity.py --dry-run  # compute only, no writes
.venv/bin/python scripts/tag_similarity.py --rebuild  # re-embed everything
.venv/bin/python scripts/tag_similarity.py --report docs/tag-similarity-report.md
.venv/bin/python scripts/tag_similarity.py --prod     # production
```

- The model dependencies (`fastembed`, `libvoikko`, `numpy`) are in the
  `similarity` dependency group, so the web app and the server don't need
  them. `libvoikko` also needs the system Voikko library and Finnish
  dictionary (Debian: `libvoikko1`, `voikko-fi`).
- The models are cached in `~/.cache/fastembed`.
- It prints what it did: tags embedded per model, pairs added, updated or
  removed, and dismissed pairs kept. On the dev DB a first run takes about
  40 s; a rerun with no new tags embeds nothing and takes a few seconds.

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
  seconds. Pairs and vectors of tags merged or deleted in production while
  the script ran are left out.
- **Its own database role**: `check_data.py` connects read-only, and this
  script needs to write, so it gets a role of its own rather than the
  app's. A bug in the script then can't change anything else:

  ```sql
  CREATE ROLE tag_similarity LOGIN PASSWORD '...';
  GRANT USAGE ON SCHEMA suomisf TO tag_similarity;
  GRANT SELECT ON suomisf.tag, suomisf.worktag,
      suomisf.storytag, suomisf.articletag TO tag_similarity;
  GRANT SELECT, INSERT, UPDATE, DELETE
      ON suomisf.tag_embedding, suomisf.tag_similarity, suomisf.tag_place
      TO tag_similarity;
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
  (status defaults to `new`, kind to both) returns `{updated, pairs}`:
  `updated` is the newest job write, and each pair has `tag_a` and
  `tag_b` (`{id, name, type: {id, name}, uses}`), `kind`, `reason`,
  `name_score`, `containment`, `shared`, `status`, `decided_by` (user
  name) and `decided_at`. Sorted by kind, then score.
- `POST /api/tags/similar/dismiss` with `{tag_a, tag_b}` (either order)
  marks a pair "not the same" and records the admin and time;
  `.../restore` sets it back to `new`, also recording who and when. 404
  for an unknown pair.
- `GET /api/tags/<id>/similar` (public) lists the tags suggested for one
  tag, dismissed pairs left out: `[{id, name, type, kind, reason}]`,
  duplicates first, then by score. Shown on the tag page (frontend
  `b9b93c7`).
- In `app/api_tags.py` and `app/impl_tags.py`; tests in
  `tests/api/test_tag_similar.py`.
- Merging uses the existing `POST /api/tags/<source>/merge/<target>`; the
  pair disappears by cascade.

## Admin UI

A new card on `/admin`, "Samankaltaiset asiasanat":

- A DataTable with Kaksoiskappaleet / Liittyvät / Hylätyt views (a
  SelectButton), sorted by score, with a search box. On phones the two
  tags stack in one cell with the reason under them.
  Each row shows both tags as links, coloured by type as elsewhere (see
  `tag-type-to-severity.ts`), their usage counts and the reason ("Sama
  perusmuoto", "Kirjoitusasu", "Paikka", "Samankaltainen nimi", "Käytetään yhdessä",
  with scores in a tooltip).
- Actions: **Yhdistä** opens a confirm dialog that picks the target,
  defaulting to the more-used tag, with a swap button, and calls the
  existing merge. **Eri asiasanat** dismisses the pair. A "Hylätyt" view
  allows restoring a dismissed pair.
- When the job last ran is shown at the top, from the newest `updated`
  value.

## Phases

0. **Prototype and evaluate** — done 2026-11-04; see "Phase 0 results".
1. **Migration 044, the `tag_similarity` role and the job** — done
   2026-11-04 (`tests/test_tag_similarity.py`), except creating the role
   in production, with
   incremental embedding, status preservation and `--dry-run`/`--report`. Pytest tests use a small
   fixture DB and a fake embedding function. Cover: the base-form and
   spelling rules, containment maths, incremental re-embedding on rename, dismissed
   pairs surviving a rerun, and cascades on tag delete.
2. **API endpoints** and their pytest tests — done 2026-11-05.
3. **Admin card**, unit tests for the table and actions, and an E2E test
   for merging and dismissing a seeded pair. Changelog in both repos —
   done 2026-11-05 (frontend `98f6b14`,
   `src/features/admin/components/similar-tags.tsx`). The E2E test
   dismisses and restores a pair from the copied job results rather than
   merging one, since a merge would delete a tag other specs may read;
   merging is covered by the unit tests and `tests/api/test_tag_similar.py`.

The tag page lists a tag's suggested similar tags (done 2026-11-05).
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
