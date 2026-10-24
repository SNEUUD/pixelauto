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
# Réglages de l'API infoclair
INFOCLAIR_API_KEY=$KEY
INFOCLAIR_HOST=127.0.0.1        # 0.0.0.0 pour l'ouvrir au réseau local
INFOCLAIR_PORT=8000
INFOCLAIR_PUBLIC_URL=http://127.0.0.1:8000   # adresse utilisée dans les liens envoyés aux webhooks
INFOCLAIR_VOICE=voices/fr_FR-siwis-medium.onnx
INFOCLAIR_TTS=piper
INFOCLAIR_NVENC=1
INFOCLAIR_MUSIC=                # chemin d'une musique à toi (vide = musique générée)
INFOCLAIR_KEEP_DAYS=14          # les vidéos plus vieilles sont supprimées au démarrage
EOF
  chmod 600 .env
  echo "Clé d'API créée dans .env"
fi

if [ "${1:-}" = "--service" ]; then
  mkdir -p ~/.config/systemd/user
  cat > ~/.config/systemd/user/infoclair.service <<EOF
[Unit]
Description=infoclair - API de rendu video

[Service]
ExecStart=$(pwd)/api.sh
Restart=on-failure

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now infoclair.service
  echo "Service lancé : systemctl --user status infoclair"
fi

KEY=$(grep '^INFOCLAIR_API_KEY=' .env | cut -d= -f2)
echo
echo "Lancer l'API :   ./api.sh        (documentation : http://127.0.0.1:8000/docs)"
echo "Ta clé :         $KEY"
echo "Exemple :        curl -H \"X-API-Key: $KEY\" -H 'Content-Type: application/json' \\"
echo "                   --data @exemples/01_dns.json http://127.0.0.1:8000/videos"
