#!/bin/bash
# Start a local Label Studio for reviewing the plot boxes.
#
# Everything stays on this machine: the database and login live in ~/.labelstudio_plotbox
# (outside Dropbox, so the SQLite file is never synced mid-write). The login is created
# automatically on first run; its details are in ~/.labelstudio_plotbox/credentials.env.
# Images are served read-only from real_data/ via Label Studio's local-file storage.
#
# Usage:  bash start_label_studio.sh        then open http://localhost:8089
set -euo pipefail

REAL_DATA="$(cd "$(dirname "$0")/../.." && pwd)"
LS_HOME="$HOME/.labelstudio_plotbox"
VENV="$HOME/.venvs/plotbox"
mkdir -p "$LS_HOME"

if [ ! -f "$LS_HOME/credentials.env" ]; then
  {
    echo "LS_USERNAME=jnaiman@illinois.edu"
    echo "LS_PASSWORD=$(openssl rand -hex 8)"
    echo "LS_TOKEN=$(openssl rand -hex 20)"
    echo "LS_PORT=8089"
  } > "$LS_HOME/credentials.env"
  chmod 600 "$LS_HOME/credentials.env"
  echo "created local login -> $LS_HOME/credentials.env"
fi
# shellcheck disable=SC1091
source "$LS_HOME/credentials.env"

export LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
export LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT="$REAL_DATA"

echo "Label Studio -> http://localhost:$LS_PORT   (login: $LS_USERNAME / $LS_PASSWORD)"
exec "$VENV/bin/label-studio" start \
  --data-dir "$LS_HOME/data" --port "$LS_PORT" --no-browser \
  --username "$LS_USERNAME" --password "$LS_PASSWORD" \
  --user-token "$LS_TOKEN" --enable-legacy-api-token
