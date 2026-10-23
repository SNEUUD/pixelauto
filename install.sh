#!/usr/bin/env bash
# Installation (Debian / Ubuntu / Mint). Usage : bash install.sh [nom_de_voix]
# Voix FR Piper possibles : fr_FR-siwis-medium (défaut, féminine), fr_FR-tom-medium, fr_FR-upmc-medium
set -euo pipefail
cd "$(dirname "$0")"
VOICE="${1:-fr_FR-siwis-medium}"

sudo apt-get update
sudo apt-get install -y ffmpeg espeak-ng python3-venv curl

python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

mkdir -p assets voices
[ -f assets/PressStart2P-Regular.ttf ] || curl -L -o assets/PressStart2P-Regular.ttf \
  https://raw.githubusercontent.com/google/fonts/main/ofl/pressstart2p/PressStart2P-Regular.ttf

# fr_FR-siwis-medium -> fr/fr_FR/siwis/medium
IFS='-' read -r LANGCODE NAME QUALITY <<< "$VOICE"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/${LANGCODE%%_*}/${LANGCODE}/${NAME}/${QUALITY}"
for ext in onnx onnx.json; do
  [ -f "voices/${VOICE}.${ext}" ] || curl -L -o "voices/${VOICE}.${ext}" "${BASE}/${VOICE}.${ext}"
done

echo
echo "OK. Pour générer la vidéo :"
echo "  . .venv/bin/activate"
echo "  python3 make_video.py episodes/02_mazda_mx5_na.json --voice voices/${VOICE}.onnx --nvenc"
