# Data checks

`scripts/check_data.py` looks for data oddities: impossible values,
probable duplicates, unused records and stray whitespace.
Every check is a read-only query, so the script never changes anything.
Run it after refreshing the dev database from production, and fix what it
finds in production.

## Running

The script reads `DATABASE_URL` from `.env`, as the app does.

```sh
.venv/bin/python scripts/check_data.py              # all checks, 10 rows each
.venv/bin/python scripts/check_data.py --list       # the checks and their keys
.venv/bin/python scripts/check_data.py --only edition_number --all
.venv/bin/python scripts/check_data.py --rows 30 > checks.txt
.venv/bin/python scripts/check_data.py --sql edition_number   # the query
```

- `--only KEY…` runs some checks; `--all` prints every row instead of the
  first 10 (`--rows N` sets another number).
- `--format markdown` writes Markdown tables instead of plain text.
  Ids in them link to the item's page on the site
  (`--site URL`, default https://www.sf-bibliografia.fi).
- `--sql KEY` prints a check's query, ready to paste into `psql` against
  production, for example to confirm a row is still wrong there.
- The script exits with 1 when any check found rows and 0 when all are
  clean.

## Results in git

The latest full results are kept in `docs/data-check-results.md`: a
summary table of every check, then a table of rows for each check that
found something, with each id linked to its page.
Regenerate them after each refresh and commit them; `git diff` then shows
what was fixed and what is new:

```sh
.venv/bin/python scripts/check_data.py --format markdown --all \
    > docs/data-check-results.md
git diff docs/data-check-results.md
```

## False positives

Some rows are correct even though a check flags them: a set of volumes
sold under one ISBN, two namesakes, a book series still waiting for its
books. Once a row is confirmed correct, add it to
`scripts/check_data_ignore.txt` so it is not reported again:

```
# KEY            ID          reason
edition_number   4918,8938   Kummituspalatsi: volumes 1 and 2, not one book
isbn_shared      951-1-15417-6   two-volume set sold under one ISBN
person_name      1234,5678   different people, born 1890 and 1952
```

- **KEY** is the check's key (`--list`).
- **ID** is how the script identifies the row: the first column it prints.
  Pair and kind checks use the first two columns joined with a comma
  (`edition_number`, `alias_loop`, `link_twice`,
  `spaces_other`), `story_order` three and `contributor_twice` four.
  Grouped checks (`person_name`, `story_title`, `tag_name`,
  `publisher_name`, `awarded_twice`, `issue_twice`) print the group's ids
  first, e.g. `165,377`. For `isbn_shared` the ID is the ISBN.
- **reason** says why the row is correct, so nobody has to check it again.

Ignored rows are left out of the counts and the listing; each check says
how many it ignored, and `--show-ignored` lists them with their reasons.
When an ignored row no longer turns up (it was changed or deleted, or the
ID is mistyped), the script lists the entry under "Ignore entries that
matched no row" so the file can be cleaned up. An unknown KEY is an error.

If a whole kind of row is always fine, change the check's query instead
(as `edition_number` does for paperback and hardback pairs) and explain
it below.

## Workflow

1. Refresh the dev database from production.
2. Regenerate `docs/data-check-results.md` (above) and look at the
   diff and the summary line at the end ("N of 34 checks found
   something").
3. For each check with rows, decide whether the rows are errors (see the
   notes below: some results are expected).
4. Add rows that are correct to the ignore list (below).
5. Fix the errors in production, through the UI or with SQL. Before
   deleting a row, confirm with `--sql KEY` that it is still unused there.
6. Refresh again and rerun; fixed checks drop to 0. Commit the results
   and the ignore list.

## The checks and how to read them

### Wrong values

| Key | Finds | Notes |
|---|---|---|
| `edition_year` | Edition year missing, before 1850 or in the future | A modern publisher with an old year usually means the original work's year was copied. |
| `edition_pages` | Under 10 or over 2000 pages | Values like 2008–2018 are years typed into the pages field. |
| `edition_before_work` | Edition older than its work's original year | Either year can be the wrong one. |
| `work_year` | Original year before −1000 or in the future | |
| `isbn_format` | ISBN without 10 or 13 digits | Typos and truncated ISBNs. |
| `person_dates` | Died before birth, lived over 110 years, born in the future | |
| `issue_year` | Magazine issue year missing or impossible | Year 0 means "unknown" was typed as 0. |
| `lookup_ids` | Binding, format or size id that does not exist | Should always be 0. |

### Probable duplicates

| Key | Finds | Notes |
|---|---|---|
| `edition_number` | Two editions of the same work and version (laitos) with the same edition number (painos) | **Allowed:** a paperback (nidottu) and a hardback (sidottu) published in the same year; those pairs are left out. Rows marked `same` have the same publisher, year, ISBN and binding and are almost certainly one book entered twice: merge them. The rest usually need a corrected edition number, version or binding (unknown binding counts as different). |
| `isbn_shared` | One ISBN on editions of different works | Usually a copy-paste error. A set of volumes sold under one ISBN is legitimate. |
| `person_name` | People with the same name | Real namesakes exist; compare dates and works. |
| `story_title` | Stories with the same title, original title, authors and translators; a missing original title counts as the title, so Finnish stories are compared too | Articles with no original title (mostly recurring magazine columns) are left out, as are retranslations by another translator. |
| `tag_name`, `publisher_name` | Same name ignoring case and spaces | Merge into one. |
| `link_twice` | The same URL twice on one person, work or edition | Delete one. |
| `contributor_twice`, `awarded_twice`, `issue_twice`, `story_order`, `alias_loop` | Repeated rows, two stories in one position, alias cycles | Should always be 0. |

### Unused records

| Key | Finds | Notes |
|---|---|---|
| `person_unused` | People with no role, award, article or alias | Often left over after a work was deleted or a person merged. Safe to delete once confirmed. |
| `publisher_unused` | Publishers with no editions, magazines or publisher series | Delete the publisher's `publisherlink` rows first. |
| `story_unused` | Stories in no edition, work or magazine issue | Often magazine articles that lost their issue: reattach rather than delete. |
| `work_unused` | Works with no editions | |
| `pubseries_unused`, `bookseries_unused`, `tag_unused` | Series and tags used by nothing | A series may be waiting for its books to be entered. |
| `magazine_empty`, `issue_empty` | Magazines with no issues, issues with no contents | Often contents not entered yet rather than errors. |

### Whitespace

`spaces_*` finds names and titles with leading, trailing or double spaces.
They break sorting and exact searches. One statement per table fixes them,
for example:

```sql
UPDATE suomisf.person
SET name = btrim(regexp_replace(name, '\s+', ' ', 'g'))
WHERE name <> btrim(regexp_replace(name, '\s+', ' ', 'g'));
```

Use `title` instead of `name` for `work`, `edition` and `shortstory`.

## Adding a check

Add a `Check(key, group, title, sql, id_cols)` to `CHECKS` in the
script. The query runs with `search_path = suomisf` and must only read. It
returns the row's id first, so the row can be found in the UI and put on
the ignore list; `id_cols` (default 1) says how many leading columns make
up that id. Grouping queries return `string_agg(id::text, ',' ORDER BY
id)` first, so a group keeps the same id between runs. Put allowed cases in the
query's `WHERE` (as `edition_number` does for paperback and hardback pairs)
and explain them in this file.
