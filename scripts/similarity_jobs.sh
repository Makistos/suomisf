#!/usr/bin/env bash
# Runs the similarity jobs, scripts/work_similarity.py and
# scripts/tag_similarity.py, against production through an SSH tunnel.
# The systemd user timer in scripts/systemd/ runs this every hour while
# the workstation is on; see docs/similarity-timer.md.
#
# Settings, from the environment or ~/.config/suomisf/similarity.env:
#   SIMILARITY_SSH      ssh destination of the server, e.g. mep@host
#   SIMILARITY_SSH_KEY  key for the tunnel (default: ssh's own choice)
#   SIMILARITY_PORT     local end of the tunnel (default 5454; must match
#                       DATABASE_URL_TAG_SIMILARITY_PROD in .env)
#
# A tunnel already open on that port (one started by hand) is used as is.
# --dev runs both jobs against the dev database instead, without a tunnel.
# Exits non-zero if either job fails; both are tried.
set -euo pipefail
cd "$(dirname "$0")/.."

config=${SIMILARITY_CONFIG:-$HOME/.config/suomisf/similarity.env}
if [ -f "$config" ]; then
    # shellcheck source=/dev/null
    . "$config"
fi
port=${SIMILARITY_PORT:-5454}

# One run at a time: a first run can take longer than the timer's hour.
exec 9>"${XDG_RUNTIME_DIR:-/tmp}/suomisf-similarity.lock"
if ! flock -n 9; then
    echo "A run is already going; skipped."
    exit 0
fi

target=(--prod)
ready() { pg_isready -q -h localhost -p "$port"; }

if [ "${1:-}" = --dev ]; then
    target=()
elif ready; then
    echo "Using the tunnel already open on port $port."
else
    : "${SIMILARITY_SSH:?set SIMILARITY_SSH (ssh destination) in $config}"
    key=()
    if [ -n "${SIMILARITY_SSH_KEY:-}" ]; then
        key=(-i "$SIMILARITY_SSH_KEY" -o IdentitiesOnly=yes)
    fi
    tunnel=
    trap '[ -n "$tunnel" ] && kill "$tunnel" 2>/dev/null; true' EXIT
    # Right after the machine starts the network may not be up yet.
    for attempt in 1 2 3; do
        ssh -N -o BatchMode=yes -o ExitOnForwardFailure=yes \
            -o ConnectTimeout=15 -o ServerAliveInterval=30 "${key[@]}" \
            -L "$port:localhost:5432" "$SIMILARITY_SSH" &
        tunnel=$!
        for _ in $(seq 20); do
            ready && break
            kill -0 "$tunnel" 2>/dev/null || break
            sleep 1
        done
        ready && break
        kill "$tunnel" 2>/dev/null || true
        tunnel=
        echo "Tunnel attempt $attempt failed." >&2
        [ "$attempt" -lt 3 ] && sleep 30
    done
    if ! ready; then
        echo "No database through the tunnel on port $port." >&2
        exit 1
    fi
fi

status=0
nice -n 10 .venv/bin/python scripts/work_similarity.py "${target[@]}" \
    || status=$?
nice -n 10 .venv/bin/python scripts/tag_similarity.py "${target[@]}" \
    || status=$?
exit "$status"
