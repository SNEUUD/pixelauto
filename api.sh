#!/usr/bin/env bash
# Lance l'API de rendu (réglages dans .env, créé par install_api.sh).
#   ./api.sh            -> http://127.0.0.1:8000  (docs : /docs)
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo "Pas de .env : lance d'abord  bash install_api.sh"; exit 1; }
set -a; . ./.env; set +a
. .venv/bin/activate
exec uvicorn server:app --host "${PIXELAUTO_HOST:-127.0.0.1}" --port "${PIXELAUTO_PORT:-8000}" --no-access-log
