#!/usr/bin/env bash
# Installation (Debian / Ubuntu / Mint). Usage : bash install.sh [nom_de_voix]
# Voix FR Piper possibles : fr_FR-siwis-medium (défaut, féminine), fr_FR-tom-medium, fr_FR-upmc-medium
# Les polices (Inter, JetBrains Mono, licence OFL) sont déjà dans assets/fonts.
set -euo pipefail
cd "$(dirname "$0")"
VOICE="${1:-fr_FR-siwis-medium}"

sudo apt-get update
sudo apt-get install -y ffmpeg espeak-ng python3-venv curl

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# fr_FR-siwis-medium -> fr/fr_FR/siwis/medium
mkdir -p voices
IFS='-' read -r LANGCODE NAME QUALITY <<< "$VOICE"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/${LANGCODE%%_*}/${LANGCODE}/${NAME}/${QUALITY}"
for ext in onnx onnx.json; do
  [ -f "voices/${VOICE}.${ext}" ] || curl -L -o "voices/${VOICE}.${ext}" "${BASE}/${VOICE}.${ext}"
done

echo
echo "OK. Pour générer la vidéo d'exemple :"
echo "  ./video.sh exemples/01_dns.json"
