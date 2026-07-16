# Global search sorting

Reference for how the menu-bar quick search (`GET /api/search/<pattern>`)
ranks and orders its results. The implementation lives in
`search_with_fts()` in `app/api.py`.

## Overview

The search runs a single SQL statement that queries 11 entity types with
PostgreSQL full-text search (FTS) and merges them with `UNION ALL`. Each
type contributes rows in a common shape (`id`, `title`, `description`,
`type`, `rank`, `table_order`, `combined_score`, `author`). The merged set
is ordered, sliced to the first 50 rows in Python, and returned as JSON.

All FTS matching uses the `voikko` (Finnish) text-search configuration. The
query term is turned into a `tsquery` once, in a CTE, and reused by every
branch:

```sql
WITH query AS (
  SELECT plainto_tsquery('voikko', :search_term) AS q
)
```

Each entity table has a generated `fts` `tsvector` column (see
`migrations/009_finnish_collation.sql`). A row is a candidate only when its
`fts` matches the query (`table.fts @@ q.q`).

## The two sort keys

Results are ordered by two things, in this priority:

1. **People first.** Person rows (`table_order = 3`) are placed ahead of
   every other type, regardless of score. Within the people block, and
   within everything else, rows fall back to `combined_score`.
2. **`combined_score` descending**, then `title` as a final tie-breaker.

Because `ORDER BY` on a `UNION` may only reference output columns, the whole
union is wrapped in a subquery so the person-first `CASE` expression is
allowed:

```sql
SELECT * FROM ( ...all UNION ALL branches... ) AS combined
ORDER BY (CASE WHEN table_order = 3 THEN 0 ELSE 1 END),
         combined_score DESC, title;
```

## How `combined_score` is built

Every branch computes:

```
combined_score = ts_rank(fts, q) * 10.0     -- relevance of the FTS match
               + (12 - table_order)          -- fixed per-type priority
               + <type-specific bonuses>
```

`ts_rank` is usually small (roughly 0–1 before the ×10), so in practice the
**per-type priority** and the **bonuses** dominate the ordering. `table_order`
is a fixed rank per entity type; a lower number means higher priority, so the
`(12 - table_order)` term gives earlier types a bigger baseline.

### `table_order` values

| order | type | order | type |
|-------|------|-------|------|
| 1 | work | 7 | pubseries |
| 2 | edition | 8 | publisher |
| 3 | person | 9 | magazine |
| 4 | shortstory | 10 | issue |
| 5 | tag | 11 | award |
| 6 | bookseries | | |

Note that `table_order` only sets the *baseline* mixing between types; it is
not a hard grouping (except for people, which are forced first by the outer
`ORDER BY`). A highly relevant lower-priority row can still outrank a weak
higher-priority one.

### Work bonuses

The `work` branch adds bonuses so the most meaningful matches float up:

| bonus | condition |
|-------|-----------|
| +5  | the query matches the work **title** (`to_tsvector(title) @@ q`) |
| +10 | the query matches a **whole word** in the title (regex `\m<term>\M`) |
| +8  | the query matches the work's **author** (`to_tsvector(author_str) @@ q`) |

The author bonus ensures that when the term names an author, works **by**
that author rank above works that merely mention the term in their
description. Example: searching `herbert` puts books by *Herbert, Frank* and
*Herbert, James* (score ≈ 19–20) above books by other authors whose
descriptions happen to mention "Herbert" (score ≈ 11–12).

> **Caveat:** `author_str` is *not* part of the work `fts` vector, so the
> author bonus only reorders works that are already candidates (i.e. the
> term also appears in the title, subtitle, orig_title, misc, or
> description). A work by the searched author that never names them in those
> fields will not appear. Broadening the work branch's `WHERE` to also match
> `author_str` would be needed to surface those.

## Result shape and post-processing

Each returned row is a JSON object:

```json
{ "id": 5332, "img": "", "header": "Dyyni",
  "description": "…", "type": "work",
  "score": 32.83, "author": "Herbert, Frank" }
```

- `author` is populated only for works, aggregated from `workcontributor`
  joined to `person` where `role_id = 1` (author); empty for other types.
- **Edition de-duplication:** an `edition` row is dropped when a `work` in
  the same result set has an identical `title`, so a work and its
  same-named printing do not both appear. This is a `NOT EXISTS` filter in
  the edition branch, not part of the scoring.
- Only the top 50 rows (after ordering) are returned.
