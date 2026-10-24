#!/usr/bin/env bash
# Une commande, une vidéo.
#   ./video.sh episodes/03_https.json           -> out/03_https.mp4
#   ./video.sh --all                            -> rend les épisodes nouveaux ou modifiés de episodes/
#   ./video.sh --all --force                    -> les refait tous
#   ./video.sh episodes/03_https.json --preview 8 --tts silent   (options de make_video.py)
# Réglages par défaut : modifie les lignes ci-dessous (ou crée config.sh avec les mêmes variables).
set -euo pipefail
cd "$(dirname "$0")"
VOICE="voices/fr_FR-siwis-medium.onnx"   # voix Piper
TTS="piper"                              # piper | chatterbox
NVENC="1"                                # 1 = encodage GPU NVIDIA si disponible
MUSIC=""                                 # chemin d'une musique à toi (vide = musique générée)
[ -f config.sh ] && . ./config.sh

. .venv/bin/activate
opts=(--voice "$VOICE" --tts "$TTS")
[ "$NVENC" = "1" ] && opts+=(--nvenc)
[ -n "$MUSIC" ] && opts+=(--music "$MUSIC")

render() { python3 make_video.py "$@" "${opts[@]}"; }

if [ "${1:-}" = "--all" ]; then
  force="${2:-}"
  n=0
  for ep in episodes/*.json; do
    [ -e "$ep" ] || { echo "Aucun épisode dans episodes/"; exit 0; }
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
