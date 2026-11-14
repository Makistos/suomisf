# Running the similarity jobs every hour

The similar works (`scripts/work_similarity.py`) and the similar tags
(`scripts/tag_similarity.py`) are computed on a workstation, because
their embedding models need more memory than the production server has
(2 GB in all). A systemd user timer runs both against production every
hour while the workstation is on, through an SSH tunnel it opens and
closes itself. A run missed while the machine was off happens soon after
it starts.

**How long a run takes.** Both jobs first check what changed:

| Changes since the last run | Time |
|---|---|
| none | about 5 s |
| tags or descriptions edited | about a minute; new descriptions and tags are embedded (well under a second each), new tags looked up in Finto and Wikidata |
| a new algorithm version | the similar works are all rewritten, still a minute or two; the first run of version 8 embeds about 3 600 descriptions (20 minutes) |

Pieces:

| File | What |
|---|---|
| `scripts/similarity_jobs.sh` | opens the tunnel, runs both jobs at low priority, closes the tunnel |
| `scripts/systemd/suomisf-similarity.service` | runs the script |
| `scripts/systemd/suomisf-similarity.timer` | every hour, catching up after the machine was off |
| `scripts/systemd/suomisf-similarity-failed.service` | a desktop notification when a run fails |

Both jobs take a PostgreSQL advisory lock, so a run by hand while the
timer's run is going (or a run from another machine) just prints
"another run is going; nothing done."

## 1. A key for the tunnel

The timer can't use your ssh agent, so the tunnel gets a key of its own
without a passphrase, which the server only accepts for a forward to the
database port. On the workstation:

```sh
ssh-keygen -t ed25519 -N '' -C suomisf-similarity-tunnel \
    -f ~/.ssh/suomisf_similarity
cat ~/.ssh/suomisf_similarity.pub
```

On the server, add the public key to `~/.ssh/authorized_keys` of the
user you log in as, on one line, with these restrictions in front:

```
restrict,port-forwarding,permitopen="localhost:5432",command="/bin/false" ssh-ed25519 AAAA… suomisf-similarity-tunnel
```

`restrict` turns off everything (shell, agent and X11 forwarding, a
terminal); `port-forwarding` with `permitopen` allows only the forward to
PostgreSQL. If the key leaks, it opens no shell, and the database still
needs the `tag_similarity` role's password.

Check it from the workstation (the second command should print
"accepting connections"):

```sh
ssh -i ~/.ssh/suomisf_similarity -o IdentitiesOnly=yes -N \
    -L 5455:localhost:5432 <user>@<server> &
pg_isready -h localhost -p 5455; kill %1
```

## 2. Settings

`~/.config/suomisf/similarity.env` (make it with an editor;
`chmod 600`):

```sh
SIMILARITY_SSH=<user>@<server>
SIMILARITY_SSH_KEY=$HOME/.ssh/suomisf_similarity
# SIMILARITY_PORT=5454   # the default; must match the port in
#                        # DATABASE_URL_TAG_SIMILARITY_PROD
```

The database URL and password come from the backend's `.env` as for a run
by hand (`DATABASE_URL_TAG_SIMILARITY_PROD`, see
`tag-similarity-running.md`). If a tunnel is already open on the port, for
example one you started by hand, the script uses it and leaves it open.

## 3. The timer

The units assume the backend is at `~/src/suomisf`; otherwise change
`ExecStart` in the service after copying.

```sh
mkdir -p ~/.config/systemd/user
cp scripts/systemd/suomisf-similarity* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now suomisf-similarity.timer
```

Try a run at once and follow it:

```sh
systemctl --user start suomisf-similarity.service &
journalctl --user -u suomisf-similarity -f
```

Afterwards:

```sh
systemctl --user list-timers suomisf-similarity.timer   # next and last run
journalctl --user -u suomisf-similarity --since today   # what runs did
systemctl --user disable --now suomisf-similarity.timer # stop the runs
```

A user timer runs while you are logged in. To have it run also when the
machine is on but nobody is logged in: `loginctl enable-linger`.

## Trying the script

`scripts/similarity_jobs.sh --dev` runs both jobs against the dev
database (`DATABASE_URL`), without a tunnel.
