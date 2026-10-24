#!/usr/bin/env bash
# Voix supplémentaires : 2 voix Piper FR + Chatterbox (voix neuronale plus naturelle, licence MIT, GPU).
# À lancer après install.sh.
set -uo pipefail
cd "$(dirname "$0")"
. .venv/bin/activate

BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR"
for v in tom/medium/fr_FR-tom-medium upmc/medium/fr_FR-upmc-medium; do
  f="voices/$(basename "$v")"
  for ext in onnx onnx.json; do
    [ -f "$f.$ext" ] || curl -fL -o "$f.$ext" "$BASE/$v.$ext" || echo "! $v indisponible, ignorée"
  done
done

# Chatterbox peut imposer sa propre version de torch : on vérifie CUDA juste après.
# setuptools<81 : le filigrane audio de Chatterbox (resemble-perth) a besoin de pkg_resources
pip install chatterbox-tts "setuptools<81"
python3 - <<'EOF'
import torch
print("torch", torch.__version__, "- CUDA :", torch.cuda.is_available())
EOF

echo
echo "Compare les voix :  python3 compare_voices.py"
