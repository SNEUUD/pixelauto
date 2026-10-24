#!/usr/bin/env bash
# Une commande, une vidéo.
#   ./video.sh episodes/02_mazda_mx5_na.json   -> out/02_mazda_mx5_na.mp4
#   ./video.sh --all                            -> rend les épisodes nouveaux ou modifiés
#   ./video.sh --all --force                    -> les refait tous
#   ./video.sh episodes/02_mazda_mx5_na.json --preview 9   (options de make_video.py)
# Réglages par défaut : modifie les 3 lignes ci-dessous (ou crée config.sh avec les mêmes variables).
set -euo pipefail
cd "$(dirname "$0")"
VOICE="voices/fr_FR-siwis-medium.onnx"   # voix Piper
TTS="piper"                              # piper | chatterbox
NVENC="1"                                # 1 = encodage GPU NVIDIA si disponible
[ -f config.sh ] && . ./config.sh

. .venv/bin/activate
opts=(--voice "$VOICE" --tts "$TTS")
[ "$NVENC" = "1" ] && opts+=(--nvenc)

render() { python3 make_video.py "$@" "${opts[@]}"; }

if [ "${1:-}" = "--all" ]; then
  force="${2:-}"
  n=0
  for ep in episodes/*.json; do
    id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["id"])' "$ep")
    out="out/${id}.mp4"
    if [ "$force" = "--force" ] || [ ! -f "$out" ] || [ "$ep" -nt "$out" ]; then
      echo "=== $ep"
      render "$ep" && n=$((n + 1))
    fi
  done
  echo "[ok] $n vidéo(s) rendue(s) dans out/"
elif [ -n "${1:-}" ]; then
  render "$@"
else
  sed -n '2,7p' "$0"
fi
