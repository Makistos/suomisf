# Running the tag similarity job

`scripts/tag_similarity.py` finds probable duplicate and related tags and
stores them as suggestions, which admins review on `/admin`
("Samankaltaiset asiasanat") and which the tag pages list. It runs on a
workstation and writes straight into the database it is pointed at; for
production that goes through an SSH tunnel. Background and the rules are in
`tag-similarity-plan.md`.

## 1. Workstation setup (once)

```sh
sudo apt install libvoikko1 voikko-fi     # Finnish base forms (Debian)
pdm install -G similarity                 # fastembed, libvoikko, numpy
```

The embedding models (about 3.5 GB) are downloaded on the first run into
`~/.cache/fastembed`.

## 2. Production database setup (once)

Done on the server, or through the tunnel from step 3.

**Migrations.** Apply them as the user that owns the `suomisf` tables (the
one the web app uses), so the app can read the new tables:

```sh
psql "$DATABASE_URL_PROD" -f migrations/044_tag_similarity.sql
psql "$DATABASE_URL_PROD" -f migrations/045_tag_place.sql
psql "$DATABASE_URL_PROD" -f migrations/046_tag_similarity_manual.sql
```

(046 lets admins link tags by hand; the role below needs nothing more
for it.)

`DATABASE_URL_PROD` here is the plain `postgresql://user@localhost:5454/suomisf`
form from `.env` (psql doesn't accept the `postgresql+psycopg2://` form). If
they are applied as another user, grant the app's user
`SELECT, UPDATE` on `suomisf.tag_similarity` and `SELECT` on
`suomisf.tag_place`.

**The job's role.** The job gets a role of its own that can only read the
tags and write its three tables. Creating a role needs a superuser, so on
the server:

```sh
sudo -u postgres psql -d suomisf
```

```sql
CREATE ROLE tag_similarity LOGIN;
GRANT USAGE ON SCHEMA suomisf TO tag_similarity;
GRANT SELECT ON suomisf.tag, suomisf.worktag, suomisf.storytag,
    suomisf.articletag TO tag_similarity;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON suomisf.tag_embedding, suomisf.tag_similarity, suomisf.tag_place
    TO tag_similarity;
```

The GRANTs need the tables, so apply the migrations first. Then set the
password as a separate step, typing it on its own line:

```
\password tag_similarity
```

Don't paste it together with the SQL above: a psql backslash command takes
the rest of the input line as its arguments, so pasted statements after it
are silently ignored. `\password` asks for the password, so it stays out
of the shell and psql history. Make one without characters that need
escaping in a URL, e.g. `openssl rand -hex 24`.

Check the result with `\dp suomisf.tag_similarity`: it should list
`tag_similarity=arwd`.

**The connection URL.** Add it to the backend's `.env` with an editor
(not on the command line, where it would end up in the history):

```
DATABASE_URL_TAG_SIMILARITY_PROD=postgresql://tag_similarity:<password>@localhost:5454/suomisf
```

The port is the local end of the tunnel below.

## 3. The tunnel (each session)

Production PostgreSQL only listens on the server, so forward a local port
to it:

```sh
ssh -N -L 5454:localhost:5432 <server>
```

Leave it running in its own terminal (`-N`: no shell, just the tunnel).
Check it from another one:

```sh
pg_isready -h localhost -p 5454      # "accepting connections"
```

To skip typing it, add the forward to `~/.ssh/config`:

```
Host suomisf-db
    HostName <server>
    LocalForward 5454 localhost:5432
```

and run `ssh -N suomisf-db`.

If the role can't log in through the tunnel ("password authentication
failed" or "no pg_hba.conf entry"), the server's `pg_hba.conf` needs a
`host suomisf tag_similarity 127.0.0.1/32 scram-sha-256` line (and a
reload) — the tunnel arrives as a local TCP connection.

## 4. Running it

From the backend directory, with the tunnel up:

```sh
.venv/bin/python scripts/tag_similarity.py --prod --dry-run   # what it would do
.venv/bin/python scripts/tag_similarity.py --prod             # do it
```

`--dry-run` computes everything and prints the counts without writing
("Would add …"). A first real run looks like this (numbers from the dev
database):

```
Embedded 3110 tags with intfloat/multilingual-e5-large in 32 s.
Embedded 3110 tags with sentence-transformers/paraphrase-multilingual-mpnet-base-v2 in 9 s.
Looked up 398 places in Wikidata in 242 s.
suomisf (production): 3110 tags, 57 duplicate and 625 related pairs.
Added 682 pairs, updated 0, removed 0; 0 dismissed pairs kept.
```

**How long.** The first run embeds every tag and looks every Paikka tag up
in Wikidata: about 5 minutes. Later runs only embed new and renamed tags
and look up new and renamed places, then compare all tags (a second or
so), so they take seconds. All writes are one short transaction at the
end; reading and computing happen first, so the site isn't held up.

**What a run changes.** New pairs are added, changed scores updated and
suggestions that no longer match removed. A pair an admin dismissed,
or linked by hand on a tag's edit dialog, is never changed or removed,
and a merged or deleted tag takes its pairs with it.

**Other options:**

| Option | |
|---|---|
| `--rebuild` | Embed every tag and look every place up again. Run it now and then (e.g. monthly) to pick up Wikidata corrections and rule changes; about 5 minutes. Places marked `manual` in `tag_place` are kept. |
| `--no-places` | Skip the Wikidata lookups and use the stored places (e.g. when Wikidata is down; the job also falls back to them by itself if a lookup fails). |
| `--report FILE` | Also write the pairs as a Markdown report. |
| `--db URL` | Any other database. |
| (none) | The dev database (`DATABASE_URL`). |

## 5. Checking the result

Open `/admin` as an admin: "Samankaltaiset asiasanat" shows when the job
last wrote ("Päivitetty …") and the suggestions. A tag page lists its
similar tags under the description.

## How often

New tags get suggestions on the next run, so run it after adding tags, or
on a schedule — weekly is plenty, with `--rebuild` monthly. To run it from
cron on the server instead, install the `similarity` group there and point
the job at the local database with `--db`; nothing else changes.

## Fixing a wrong place

A Paikka tag matched to the wrong Wikidata item (e.g. "onnela" an inn)
gives wrong place pairs. Dismissing the pairs on `/admin` is enough. To fix
the match itself, edit its `tag_place` row and set `manual = true` so the
job never looks it up again; `qid = NULL` makes it "not a place".
