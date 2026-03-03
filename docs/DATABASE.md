# SuomiSF Database Structure

PostgreSQL schema name: **`suomisf`**

See the accompanying ER diagram for a visual overview:
- [db_schema.png](db_schema.png) — full schema diagram (PNG)
- [db_schema.pdf](db_schema.pdf) — same diagram as PDF (scalable)
- [db_schema.dot](db_schema.dot) — Graphviz source
  (re-render: `dot -Tpng db_schema.dot -o db_schema.png`)

**Diagram conventions:**
- Single-arrow edges (`→`) are 1:N foreign keys.
- Double-arrow edges (`↔`) are M:N relationships. Pure junction
  tables (no payload beyond the two FKs) are collapsed into a
  single labelled M:N edge. The underlying junction table name is
  noted in the edge label or in the text sections below.
- Dotted edges are optional / secondary FKs (e.g. pseudonym
  real-person links).
- Node background colours indicate domain (see legend in diagram):
  green = core entities, tan = edition detail, light green =
  publishers/series, yellow = magazines/articles, pink = awards,
  blue = users, grey = lookup tables.

**Tables omitted from diagram** (documented in text below):
`userbookseries`, `userpubseries`, `log`, `problems`,
`editionprice`, `bookcondition`, `contributorrole`.

**Relationships omitted from diagram** (exist in DB, hidden to
reduce clutter):
- `persontag` — person ↔ tag M:N (tags on persons)
- `issuetag` — issue ↔ tag M:N (tags on issues)
- `magazinetag` — magazine ↔ tag M:N (tags on magazines)
- `workreview` — work ↔ article M:N (articles that review a work)
- `user.language_id` → `language` FK (UI language preference)

---

## Table of Contents

1. [Core entities](#1-core-entities)
2. [Contributor tables](#2-contributor-tables)
3. [Edition detail](#3-edition-detail)
4. [Publishers and series](#4-publishers-and-series)
5. [Magazines and articles](#5-magazines-and-articles)
6. [Awards](#6-awards)
7. [Users and personal library](#7-users-and-personal-library)
8. [Person detail](#8-person-detail)
9. [Tag and genre junctions](#9-tag-and-genre-junctions)
10. [Lookup / reference tables](#10-lookup--reference-tables)
11. [Admin and audit](#11-admin-and-audit)
12. [Views](#12-views)
13. [Migration history](#13-migration-history)

---

## 1. Core Entities

These four tables are the heart of the database.

### `work`

A literary work in its original, abstract sense — independent of any
specific edition or translation.

| Column | Type | Notes |
|---|---|---|
| `id` | bigint PK | |
| `title` | varchar | Finnish title (or original if not translated) |
| `orig_title` | varchar | Original title if different |
| `subtitle` | varchar | |
| `pubyear` | bigint | Year of first publication |
| `language` | bigint → `language` | Original language |
| `type` | bigint → `worktype` | e.g. novel, collection, non-fiction |
| `bookseries_id` | bigint → `bookseries` | |
| `bookseriesnum` | varchar | Position within the book series |
| `bookseriesorder` | bigint | Sort key within the book series |
| `description` | text | |
| `author_str` | varchar | Denormalised author string for display |
| `misc` | varchar | Free-form notes |
| `fts` | tsvector | Full-text search vector |

### `edition`

A concrete physical (or digital) publication of a work.

| Column | Type | Notes |
|---|---|---|
| `id` | bigint PK | |
| `work_id` | integer → `work` | Direct link to work (since migration 004) |
| `title` | varchar | Title as printed on the book |
| `subtitle` | varchar | |
| `pubyear` | bigint | Year this edition was published |
| `publisher_id` | bigint → `publisher` | |
| `pubseries_id` | bigint → `pubseries` | Publisher series |
| `pubseriesnum` | bigint | Number within publisher series |
| `isbn` | varchar | |
| `editionnum` | bigint | Edition number (1st, 2nd …) |
| `version` | bigint | Printing within an edition |
| `pages` | bigint | |
| `binding_id` | bigint → `bindingtype` | |
| `format_id` | bigint → `format` | |
| `verified` | boolean | Bibliographic data checked |
| `fts` | tsvector | |

### `shortstory`

A short story or novella. Short stories appear inside editions via
`editionshortstory` and are connected to works via the
`work_shortstory` VIEW (see [§12](#12-views)).

| Column | Type | Notes |
|---|---|---|
| `id` | bigint PK | |
| `title` | varchar | |
| `orig_title` | varchar | |
| `pubyear` | bigint | |
| `language` | bigint → `language` | |
| `story_type` | bigint → `storytype` | e.g. short story, novella |
| `fts` | tsvector | |

### `person`

An author, translator, editor, or any other contributor.

| Column | Type | Notes |
|---|---|---|
| `id` | bigint PK | |
| `name` | varchar | Display name (`Last, First`) |
| `alt_name` | varchar | Alternative form |
| `fullname` | varchar | Full (non-inverted) name |
| `other_names` | text | Additional pseudonyms, etc. |
| `first_name` | varchar | |
| `last_name` | varchar | |
| `nationality_id` | bigint → `country` | |
| `dob` / `dod` | bigint | Birth / death year |
| `bio` | text | |
| `image_src` | varchar | |
| `fts` | tsvector | |

---

## 2. Contributor Tables

Contributors record who participated in a work, edition, or short
story and in what role (author, translator, editor, illustrator …).
All four contributor tables share the same column structure and are
shown in the diagram as M:N edges between the entity and `person`,
annotated with the `contributorrole` lookup.

### Common columns

| Column | Type | Notes |
|---|---|---|
| `person_id` | integer → `person` | The contributor |
| `role_id` | integer → `contributorrole` | Role (see below) |
| `real_person_id` | integer → `person` | If contributor is a pseudonym, the real person |
| `description` | varchar | Free-form role note |

### `workcontributor`

Links a person to a **work**. PK: `(work_id, person_id, role_id)`.

### `editioncontributor`

Links a person to an **edition**. PK:
`(edition_id, person_id, role_id)`.

### `storycontributor`

Links a person to a **short story**. PK:
`(shortstory_id, person_id, role_id)`.

### `issuecontributor`

Links a person to a **magazine issue**. PK:
`(issue_id, person_id, role_id)`. Also covers editors (previously
`issueeditor` for role-less editor entries).

### `contributorrole`

Lookup table for contributor roles. Not shown in the diagram
(referenced implicitly by the contributor edge labels). Common
values:

| id | name |
|---|---|
| 1 | Kirjoittaja (Author) |
| 2 | Kääntäjä (Translator) |
| 3 | Toimittaja (Editor) |
| … | … |

---

## 3. Edition Detail

### `editionshortstory` (M:N junction)

Many-to-many between `edition` and `shortstory` with an ordering
column. This is the primary way short stories are assigned to a
collection or anthology. Shown in the diagram as the
"contains (M:N, ordered)" edge between `edition` and `shortstory`.

| Column | Notes |
|---|---|
| `edition_id` | |
| `shortstory_id` | |
| `order_num` | Story order within the edition |

### `editionimage`

Cover images attached to an edition. Shown as 1:N from `edition`.

### `editionlink`

External links (URLs) for an edition (not shown in diagram).

### `editionprice`

Historical price records for an edition (date, price, condition).
Not shown in diagram.

---

## 4. Publishers and Series

### `publisher`

A publishing house.

### `pubseries`

A publisher's named series (e.g. "Galaxy-pokkari"). Each pubseries
belongs to exactly one publisher.

### `bookseries`

A book series that may span multiple publishers (e.g. a numbered
fantasy sequence). `parent_id` allows a series-of-series hierarchy.

### `publisherlink` / `pubserieslink` / `bookserieslink`

External URL link tables (not shown in diagram — 1:N detail rows).

---

## 5. Magazines and Articles

### `magazine`

A periodical. Belongs to a publisher and has a type
(`magazinetype`: magazine, fanzine, etc.).

### `issue`

A single issue of a magazine, identified by number and year.

### `issuecontent` (M:N junction)

Contents of an issue: each row links an issue to either an
`article` or a `shortstory` (one of the two FKs will be NULL).
Shown as the "contents (M:N)" edges from `issue` in the diagram.

### `issueeditor` (M:N junction)

Editors of a specific issue (person→issue, no role column).
Merged with `issuecontributor` in the diagram.

### `article`

A non-fiction piece (review, essay, interview). The `person` column
is a free-text credit; structured authorship is in `articleauthor`.

### `articleauthor` / `articleperson` (M:N junctions)

Both link articles to persons. `articleauthor` records the authors;
`articleperson` records any person mentioned. Collapsed into the
"authors / mentioned (M:N)" edge in the diagram.

### `workreview` (M:N junction)

Links a `work` to an `article` that reviews it. Not shown in
diagram.

---

## 6. Awards

### `award`

An award (e.g. Atorox, Hugo).

### `awardcategory`

A category within an award (e.g. Best Novel, Best Short Story).

### `awardcategories` (M:N junction)

Many-to-many between `award` and `awardcategory`. Shown as the
"categories (M:N)" edge in the diagram.

### `awarded`

An award instance. One of `person_id`, `work_id`, or `story_id`
is populated depending on what was awarded; the others are NULL.

---

## 7. Users and Personal Library

### `user`

An application user with a hashed password and admin flag.

### `userbook`

A book (edition) in a user's personal library, with condition and
price paid.

### `userbookseries` / `userpubseries` (M:N junctions)

Book series and publisher series that a user is "collecting"
(following). Not shown in diagram.

---

## 8. Person Detail

### `alias` (M:N self-join)

Pen-name / pseudonym relationships. `alias` (person id) is a name
used by `realname` (person id). Both columns reference `person`.
Shown as the self-referential dashed "alias of (M:N)" edge on
`person` in the diagram.

A person's aggregate `roles` property in the Python ORM includes
contributions made under any of their aliases.

### `personlink`

External URLs for a person (Wikipedia, ISNI, etc.).
Not shown in diagram (1:N detail rows).

### `personlanguage` (M:N junction)

Languages a person writes in or translates from/to. Shown as
the "languages (M:N)" edge from `person` to `language`.

### `persontag` (M:N junction)

Tags applied to a person. Not shown in diagram (omitted to
reduce clutter; use `worktag`/`storytag` for primary tag
discovery).

### `personworks` (M:N junction)

A manually curated many-to-many between persons and works, used for
edge cases not covered by `workcontributor` (e.g. preface writers
listed separately). Shown as a dashed "personworks (M:N)" edge.

---

## 9. Many-to-Many: Tags and Genres

Tags and genres can be attached to most entity types via pure
junction tables. The high-frequency tag relationships are shown
in the diagram as M:N edges; low-traffic ones are omitted for
clarity.

| Junction table | Diagram |
|---|---|
| `worktag` | shown — work ↔ tag |
| `workgenre` | shown — work ↔ genre |
| `storytag` | shown — shortstory ↔ tag |
| `storygenre` | shown — shortstory ↔ genre |
| `articletag` | shown — article ↔ tag |
| `persontag` | **not shown** — person ↔ tag |
| `issuetag` | **not shown** — issue ↔ tag |
| `magazinetag` | **not shown** — magazine ↔ tag |
| `worklink` | not shown — URL detail rows |
| `articlelink` | not shown — URL detail rows |

### `tag`

| Column | Notes |
|---|---|
| `id` | |
| `name` | |
| `type_id` → `tagtype` | Category of tag |
| `description` | |

### `genre`

Simple lookup: `id`, `name`, `abbr`.

---

## 10. Lookup / Reference Tables

Small, mostly static tables used as foreign-key targets. All are
shown in the diagram except `bookcondition` (only used by the
omitted `editionprice` table).

| Table | Purpose | Diagram |
|---|---|---|
| `worktype` | Novel, collection, anthology, non-fiction, … | shown |
| `storytype` | Short story, novella, novelette, … | shown |
| `bindingtype` | Hardcover, paperback, e-book, … | shown |
| `format` | Physical format | shown |
| `publicationsize` | Page dimensions (mm) | shown |
| `country` | Countries (for person nationality) | shown |
| `language` | Languages | shown |
| `tagtype` | Tag categories | shown |
| `magazinetype` | Magazine type categories | shown |
| `bookcondition` | New, fine, good, fair, poor, … | **not shown** |

---

## 11. Admin and Audit

Neither table is shown in the diagram.

### `log`

Change log. Each row records one field change: who changed it,
what table and row, old value, and timestamp.

### `problems`

Manual issue tracker for bibliographic data problems. Links to any
table via `(table_name, table_id)`.

---

## 12. Views

### `work_shortstory`

Connects works to their short stories via the edition that
contains them:

```sql
SELECT e.work_id,
       ess.shortstory_id,
       MIN(ess.order_num) AS order_num
FROM editionshortstory ess
JOIN edition e ON e.id = ess.edition_id
WHERE e.work_id IS NOT NULL
GROUP BY e.work_id, ess.shortstory_id;
```

This view is used by the ORM (`Work.stories`, `ShortStory.works`)
via a separate SQLAlchemy `MetaData` instance to avoid conflicts
with `create_all()`.

**Permission note:** the view is owned by `postgres`. The
application user (`mep`) requires an explicit grant:
```sql
GRANT SELECT ON suomisf.work_shortstory TO mep;
```

---

## 13. Migration History

| Migration | File | What it does |
|---|---|---|
| 001 | `001_shortstory_migration.sql` | Creates `editionshortstory`, `storycontributor`, and `work_shortstory` VIEW |
| 002 | `002_edition_contributors.sql` | Creates `editioncontributor`; migrates edition-level contributions |
| 003 | `003_work_contributors.sql` | Creates `workcontributor`; migrates work-level contributions |
| 004 | `004_edition_work_direct_link.sql` | Adds `edition.work_id` direct FK to work (replaces old `part` join) |
| 005 | `005_drop_part.sql` | Rewrites `work_shortstory` VIEW, drops legacy `contributor` and `part` tables |

The `part` and `contributor` tables existed in the original schema
as a single polymorphic join between works, editions, and short
stories. Migrations 001–005 decomposed this into dedicated, typed
tables (`workcontributor`, `editioncontributor`, `storycontributor`,
`editionshortstory`) and a direct `edition.work_id` foreign key.
