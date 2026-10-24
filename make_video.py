#!/usr/bin/env python3
"""Génère une vidéo TikTok 8 bits (1080x1920, 30 i/s) à partir d'un épisode JSON.

    python3 make_video.py episodes/02_mazda_mx5_na.json
    python3 make_video.py episodes/02_mazda_mx5_na.json --voice voices/fr_FR-siwis-medium.onnx --nvenc
    python3 make_video.py episodes/02_mazda_mx5_na.json --preview 8   # 8 images-clés en PNG, sans vidéo
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from engine import audio, decors, generic, scenes  # noqa: F401 (generic enregistre ses scènes)
from engine.scenes import W, H

FPS = 30
SCALE = 6
MIN_SCALE = 0.95  # on n'accélère presque pas la voix : au-delà, elle devient mécanique
LEAD_IN = 0.25    # silence avant la voix dans chaque scène
TAIL = 0.45       # respiration après la voix
ROOT = Path(__file__).resolve().parent


def build_audio(ep, voice, tmp, target):
    """Synthétise chaque scène, ajuste le débit pour viser `target` secondes."""
    for attempt in range(3):
        clips = []
        for i, sc in enumerate(ep["scenes"]):
            clips.append(voice.say(sc["voice"], tmp / f"v{i}.wav"))
        durs = [len(cl) / audio.SR + LEAD_IN + TAIL for cl in clips]
        total = sum(durs)
        print(f"[voix] {voice.engine}, débit x{voice.length_scale:.2f} -> {total:.1f} s")
        if abs(total - target) <= 1.5 or attempt == 2:
            break
        new = max(MIN_SCALE, min(1.15, voice.length_scale * (target - 0.5) / total))
        if abs(new - voice.length_scale) < 0.01:
            break
        voice.length_scale = new
    words = sum(len(sc["voice"].split()) for sc in ep["scenes"])
    wpm = words / (sum(len(c) for c in clips) / audio.SR) * 60
    print(f"[voix] débit : {wpm:.0f} mots/min (confortable : 150-175)")
    if total > target + 2:
        print(f"[voix] ! {total:.0f} s au lieu de {target:.0f} : raccourcis le texte plutôt que d'accélérer la voix")
    return clips, durs


def load_backdrops(ep, enabled=True):
    """Décor d'une scène : "bg": "<id>" -> banque assets/bank/<id>.png (dessinée par
    engine/decors.py au premier usage, retouchable dans Aseprite)."""
    used = []
    for sc in ep["scenes"]:
        if enabled and sc.get("bg"):
            img = decors.get(sc["bg"])
            if img is None:
                print(f"[décors] « {sc['bg']} » inconnu -> décor par défaut de la scène")
                continue
            sc["_bg"] = img
            used.append(sc["bg"])
    print(f"[décors] {', '.join(used)}" if used else "[décors] décors par défaut des scènes")


def render(ep, args, tmp):
    load_backdrops(ep, not args.no_bank)
    target = float(args.target or ep.get("target_seconds", 60))
    voice = audio.Voice(args.voice, length_scale=args.speed, tts=args.tts, ref=args.ref,
                        exaggeration=args.exaggeration, cfg_weight=args.cfg)
    clips, durs = build_audio(ep, voice, tmp, target)
    total = sum(durs)

    # --- pistes audio
    voice_track = np.zeros(int((total + 1) * audio.SR), dtype=np.float32)
    sfx = np.zeros_like(voice_track)
    t0 = 0.0
    starts = []
    for cl, d in zip(clips, durs):
        starts.append(t0)
        i = int((t0 + LEAD_IN) * audio.SR)
        voice_track[i:i + len(cl)] += cl
        b = audio.blip(660 if t0 else 990)
        j = int(t0 * audio.SR)
        sfx[j:j + len(b)] += b
        t0 += d
    music = audio.chiptune(total + 1)
    wav = tmp / "mix.wav"
    audio.mix(voice_track[: int(total * audio.SR)], music[: int(total * audio.SR)],
              sfx[: int(total * audio.SR)], wav)

    # --- plan des sous-titres (temps proportionnel au nombre de caractères)
    subs = []
    for sc, st, cl in zip(ep["scenes"], starts, clips):
        chunks = scenes.caption_chunks(sc.get("caption", sc["voice"]), max_chars=17)
        vdur = len(cl) / audio.SR
        weights = [sum(len(l) for l in ch) + 4 for ch in chunks]
        acc = st + LEAD_IN
        sc["_subs"] = []
        for ch, w in zip(chunks, weights):
            d = vdur * w / sum(weights)
            subs.append((acc, acc + d, ch))
            sc["_subs"].append((acc - st, acc + d - st, " ".join(ch).lower()))
            acc += d

    def frame_at(gt):
        k = max(i for i, s in enumerate(starts) if s <= gt + 1e-9)
        sc, st, d = ep["scenes"][k], starts[k], durs[k]
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        lt = gt - st
        scenes.SCENES[sc["type"]](img, lt, d, sc, ep)
        if sc.get("year") and sc["type"] != "outro":
            scenes.badge(img, sc["year"], x=8, y=104)
        scenes.header(img, ep)
        for a, b, lines in subs:
            if a <= gt < b + 0.12:
                scenes.subtitles(img, lines)
                break
        scenes.transition(img, lt / 0.25)
        return img.convert("RGB")

    out = Path(args.out or ROOT / "out" / f"{ep['id']}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.preview:
        pdir = out.parent / f"{ep['id']}_preview"
        pdir.mkdir(exist_ok=True)
        for i in range(args.preview):
            gt = total * (i + 0.5) / args.preview
            frame_at(gt).resize((W * SCALE // 2, H * SCALE // 2), Image.NEAREST).save(pdir / f"{i:02d}.png")
        print(f"[aperçu] {args.preview} images dans {pdir}")
        return

    use_nvenc = args.nvenc and nvenc_ok()
    if args.nvenc and not use_nvenc:
        print("[vidéo] NVENC indisponible -> encodage processeur (libx264)")
    venc = ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "19"] if use_nvenc else \
           ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "animation"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav),
           "-vf", f"scale={W * SCALE}:{H * SCALE}:flags=neighbor",
           *venc, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(total * FPS)
    for f in range(n):
        proc.stdin.write(frame_at(f / FPS).tobytes())
        if f % (FPS * 5) == 0:
            print(f"\r[vidéo] {f / FPS:5.1f}/{total:.1f} s", end="", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("\n[erreur] ffmpeg a échoué")
    print(f"\n[ok] {out}  ({total:.1f} s, voix {voice.engine})")


def nvenc_ok():
    """Teste en 0,1 s si l'encodeur GPU NVIDIA est utilisable."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.1",
                        "-c:v", "h264_nvenc", "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", help="fichier JSON de l'épisode")
    ap.add_argument("-o", "--out", help="chemin du .mp4 de sortie")
    ap.add_argument("--voice", default=str(ROOT / "voices" / "fr_FR-siwis-medium.onnx"),
                    help="modèle Piper .onnx (sinon espeak-ng ; ignoré par kokoro et chatterbox)")
    ap.add_argument("--tts", choices=["piper", "kokoro", "chatterbox"], default="piper",
                    help="moteur de voix (kokoro : plus naturel, CPU ; chatterbox : le plus naturel, GPU)")
    ap.add_argument("--ref", help="chatterbox : extrait .wav de 5-10 s d'une voix à imiter (la tienne)")
    ap.add_argument("--exaggeration", type=float, default=0.5, help="chatterbox : expressivité 0.3-0.8")
    ap.add_argument("--cfg", type=float, default=0.5, help="chatterbox : 0.3 = débit plus posé")
    ap.add_argument("--speed", type=float, default=1.0, help="length_scale Piper/Kokoro de départ (<1 = plus rapide)")
    ap.add_argument("--target", type=float, help="durée visée en secondes (défaut : celle de l'épisode)")
    ap.add_argument("--nvenc", action="store_true", help="encodage GPU NVIDIA (si disponible)")
    ap.add_argument("--no-bank", "--no-ai", dest="no_bank", action="store_true",
                    help="ignore la banque de décors")
    ap.add_argument("--preview", type=int, default=0, help="n'exporte que N images PNG d'aperçu")
    args = ap.parse_args()
    ep = json.loads(Path(args.episode).read_text(encoding="utf-8"))
    for sc in ep["scenes"]:
        if sc["type"] not in scenes.SCENES:
            sys.exit(f"Type de scène inconnu : {sc['type']}")
    with tempfile.TemporaryDirectory(prefix="pixelauto_") as tmp:   # supprimé même en cas d'erreur
        render(ep, args, Path(tmp))


if __name__ == "__main__":
    main()
