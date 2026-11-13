# Similar works: the algorithm

How `scripts/work_similarity.py` ranks similar works, as of **algorithm
version 7** (2026-11-13). This describes the current state only; why each
choice was made, what was tried and how the results changed is in
`work-similarity-plan.md`. All weights and thresholds are in
`SIMILARITY_CONFIG` in the script; changing any of them means bumping
`ALGORITHM_VERSION`.

## 1. Which works take part

A work is **eligible** if

- its description, HTML removed, has at least **20 words**, and
- it has at least **3 tags**, not counting Lista tags.

Only eligible works get a list, and only eligible works are recommended.

## 2. Inputs per work

| Input | From |
|---|---|
| Tags by type | `worktag` + `tag.type_id`; Lista (7) left out |
| Description | `work.description`, HTML stripped |
| Genres | `workgenre` |
| Original year | `work.pubyear`; below 1000 counts as missing |
| Series | `work.bookseries_id`, followed up `bookseries.parent_id` to the top-level series |
| Authors | `workcontributor` role 1, as `real_person_id` when set (pseudonyms count as the person) |
| Omnibuses | `omnibus`: the omnibuses a work is in, plus its own id if it is one |
| Work type | `work.type`; 4 = Tietokirja |

## 3. The four signals

Each is between 0 and 1, or **unavailable** for a pair.

### T: tags

**Rarity weight** of a tag, within its type: among the eligible works, let
`N_c` be the number of works with at least one tag of type c, and `df_t`
the number of works with tag t. Then

```
r_t = 1 + ln((N_c + 1) / (df_t + 1))        (no cap)
```

A tag on 2 works weighs about 7.7; "seikkailu" (on about 400) about 2.3.
Tags that only one eligible work has are left out: they can never be
shared.

**Per type** (c), each work is a vector with `r_t` for each of its tags
of that type. The similarity is the cosine of the two vectors:

```
T_c = Σ r_t² (shared tags) / ( √Σ r_t² (A's tags) · √Σ r_t² (B's tags) )
```

A type counts for the pair if **either** work has tags of it. If only one
does, `T_c` = 0 (no match).

**Subgenre and style by rarity.** A work has one subgenre (Alagenre) and
one style (Tyyli) as a rule, so their cosine is 1 whenever the tag is
shared, whatever the tag. For these two types, `T_c` is therefore also
multiplied by the mean weight of the shared tags relative to the weight
of the rarest tag that can be shared (one on two works):

```
T_c ← T_c × mean(r_t, shared tags) / r(df = 2)
```

A shared "dystopia" (292 works) counts 0.34, "korkea fantasia" (64) 0.56,
"kova scifi" (26) 0.69, "biopunk" (4) 0.93; a shared "seikkailu" (Tyyli,
about 400 works) about 0.3. Other types use the cosine alone
(`rarity_scaled_types`).

**Combined**, as a weighted mean over the types that count:

```
T_raw = Σ w_c · T_c / Σ w_c
```

| Type (id) | w_c |
|---|---|
| Aihe (1) | 0.35 |
| Alagenre (2) | 0.30 |
| Tyyli (3) | 0.25 |
| Aika (6) | 0.05 |
| Toimija (4) | 0.05 |
| Paikka (5) | 0.05 |

**Rescaled.** Once per run, `T_raw` is computed for a sample of 1 000
source works against all works. With `lo` = the median pair and `hi` =
the 99.9th percentile:

```
T = clip((T_raw − lo) / (hi − lo), 0, 1)
```

So the median pair gets 0 and the top 0.1 % gets 1, on the same scale as
D. If there is no spread (tiny data sets), `T = T_raw`.

### D: description

Each eligible description (plain text, prefixed `query: `) is embedded
with **multilingual-e5-large** (fastembed, ONNX, on the workstation CPU).
Vectors are stored in `work_embedding` with a hash of the text, so only
new and changed descriptions are embedded again.

The cosine of two vectors is rescaled like T, from a sample of 1 000
works:

```
D = clip((cos − median pair) / (99.9th percentile − median pair), 0, 1)
```

e5 cosines bunch near 0.8, so the raw value says little until it is
rescaled.

### G: genre

Genres are first folded to base genres:

- Nuorten fantasia (8) and Lasten fantasia (17) → Fantasia (1)
- Nuorten SF (9) and Lasten SF (11) → SF (5)
- Nuorten kauhu (10) → Kauhu (2)
- Lasten kuvakirja (15) → none
- Kokoelma (16), rajatapaus (14) and Ei SpeFiä (13) are left out.

G is the Jaccard index of the two sets of base genres. It is unavailable if
either work has none.

### Y: original year

```
Y = 2^(−|yearA − yearB| / 30)
```

Y halves every 30 years. It is unavailable if either year is missing. Its
weight is small (0.01): it only settles near ties.

## 4. The score

**S** is the weighted mean of the available signals:

```
S = Σ w_s · signal_s / Σ w_s      over the available signals
w: T 0.40, D 0.35, G 0.10, Y 0.01
```

**Coverage** is the share of the full comparison that was available. The
tag part counts only the share of tag-type weight that counted:

```
coverage = (0.40 · Σw_c(counted)/Σw_c(all) + 0.35·[D] + 0.10·[G]
            + 0.01·[Y]) / 0.86
```

**Final score:**

```
score = S × multipliers × (0.5 + 0.5 · coverage)
```

| Multiplier | When |
|---|---|
| × 0.25 | same top-level book series |
| × 0.5 | age-group mismatch: one work young-adult only, the other adult only |

For the age group, a work is **young-adult** if it has Nuorten fantasia,
SF or kauhu (8, 9, 10). It is **adult** if it has any other content
genre, or no genre at all. It can be both.

## 5. Which pairs may be recommended

A pair is a **candidate** only if all of these hold:

- **Minimum evidence:** at least one of
  - a shared Alagenre or Tyyli tag,
  - 2 or more shared Aihe tags, or Aihe `T_c` ≥ 0.15 with at least one
    shared Aihe tag,
  - D ≥ 0.25.

  Year, genre, or Aika, Toimija or Paikka tags alone are never enough.
  These checks use the unscaled values.
- Not the work itself.
- **Non-fiction** only with non-fiction (work type 4).
- **Children's books** only with children's books. A work is a children's
  book if it has Lasten SF (11), Satu (12), Lasten kuvakirja (15) or Lasten
  fantasia (17).

Every pair is scored as numpy matrix products, in blocks of 256 source
works. There is no separate candidate search.

## 6. Picking the list

Candidates are sorted by score, best first (ties by work id). They are
taken greedily, skipping any that would break a rule:

- **No shared omnibus:** neither work is in an omnibus that contains the
  other, and they aren't in the same omnibus.
- At most **1** work from the source work's top-level series.
- At most **1** work from any other single series.
- At most **2** works by the same person. A work with several authors
  counts for each of them.

The first **40** are stored. The page shows 8. If fewer than 8 qualify,
the list is shorter; it is never padded.

## 7. Reasons

Each stored item has its reasons, in order of how much they contributed
to S:

- **A tag type with shared tags**, tags rarest first. Its contribution is
  `0.40 · w_c · T_c / Σw_c(counted)`, scaled by `T / T_raw`.
- **"description"**, when D ≥ 0.25. Its contribution is `0.35 · D`.

The API (`GET /api/works/<id>/similar`) adds tag names and leaves out
deleted tags. It keeps Aika, Toimija and Paikka reasons only when no
stronger reason exists. The admin dialog shows:

- the two strongest reasons,
- plus the shared Aihe tags when there are two or more,
- the score and its parts (`signals`).

## 8. Stored values

In `work_similarity`, per (source, target):

| Column | Contents |
|---|---|
| rank | 1 = best |
| score | the final score |
| signal_scores | S, T, T_raw, D, G, Y, coverage, types ({tag type id: T_c}), same_series, multiplier (series × age group), parts, type_parts (see below) |
| reasons | [{type, tags, contribution}], type is a tag type id or "description" |
| algorithm_version | 7 |

**Weighted parts**, for reading the values: `parts` is each signal's share
of S, `w_s · signal_s / Σ w_s (available)`, so the parts add up to S;
`type_parts` splits `parts.T` between the tag types in proportion to
`w_c · T_c`. The admin dialog shows each part with the signal's own value
in brackets ("Vuosi 0,01 (0,52)": the years are fairly close, but the year
hardly counts), the tag types' parts, and `score = S × (0.5 + 0.5 ·
coverage) × multiplier`.

## 9. When lists change

A run hashes all its inputs (every work's tags, genres, description hash,
year, series, authors, type and omnibuses) together with
`ALGORITHM_VERSION` and the config.

- **Same hash as the last run** (`work_similarity_run`): the run stops.
- **Otherwise:** everything is recomputed, because rarity and both
  rescalings depend on all works. Only the lists whose targets, order,
  reasons or version changed are rewritten, in one transaction.

`--work ID` recomputes one list and leaves the run record alone.
