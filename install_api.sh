#!/usr/bin/env bash
# Installe l'API de rendu. À lancer après install.sh.
#   bash install_api.sh            -> dépendances + .env avec une clé d'API
#   bash install_api.sh --service  -> + démarrage automatique au login (service systemd utilisateur)
set -euo pipefail
cd "$(dirname "$0")"
. .venv/bin/activate
pip install -r requirements.txt

if [ ! -f .env ]; then
  KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  cat > .env <<EOF
# Réglages de l'API pixelauto
PIXELAUTO_API_KEY=$KEY
PIXELAUTO_HOST=127.0.0.1        # 0.0.0.0 pour l'ouvrir au réseau local
PIXELAUTO_PORT=8000
PIXELAUTO_PUBLIC_URL=http://127.0.0.1:8000   # adresse utilisée dans les liens envoyés aux webhooks
PIXELAUTO_VOICE=voices/fr_FR-siwis-medium.onnx
PIXELAUTO_TTS=piper
PIXELAUTO_NVENC=1
PIXELAUTO_KEEP_DAYS=14          # les vidéos plus vieilles sont supprimées au démarrage
EOF
  chmod 600 .env
  echo "Clé d'API créée dans .env"
fi

if [ "${1:-}" = "--service" ]; then
  mkdir -p ~/.config/systemd/user
  cat > ~/.config/systemd/user/pixelauto.service <<EOF
[Unit]
Description=pixelauto - API de rendu video

[Service]
ExecStart=$(pwd)/api.sh
Restart=on-failure

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now pixelauto.service
  echo "Service lancé : systemctl --user status pixelauto"
fi

KEY=$(grep '^PIXELAUTO_API_KEY=' .env | cut -d= -f2)
echo
echo "Lancer l'API :   ./api.sh        (documentation : http://127.0.0.1:8000/docs)"
echo "Ta clé :         $KEY"
echo "Exemple :        curl -H \"X-API-Key: $KEY\" -H 'Content-Type: application/json' \\"
echo "                   --data @episodes/04_fiat_500.json http://127.0.0.1:8000/videos"
