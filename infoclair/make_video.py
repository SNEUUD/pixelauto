#!/usr/bin/env python3
"""Génère une vidéo TikTok de vulgarisation (1080x1920, 30 i/s) à partir d'un épisode JSON.

    python3 make_video.py exemples/01_dns.json
    python3 make_video.py exemples/01_dns.json --voice voices/fr_FR-siwis-medium.onnx --nvenc
    python3 make_video.py exemples/01_dns.json --preview 8               # 8 images PNG, sans vidéo
    python3 make_video.py exemples/01_dns.json --preview 8 --tts silent  # idem, en 2 secondes
    python3 make_video.py exemples/01_dns.json --music ma_musique.mp3    # ta propre musique
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from engine import audio, gfx, scenes
from engine.gfx import H, W
from engine.validate import validate

FPS = 30
MIN_SCALE = 0.95  # on n'accélère presque pas la voix : au-delà, elle devient mécanique
LEAD_IN = 0.3     # silence avant la voix dans chaque scène
TAIL = 0.45       # respiration après la voix
EXIT = 0.22       # fondu de sortie de chaque scène
ROOT = Path(__file__).resolve().parent


def build_audio(ep, voice, tmp, target):
    """Synthétise chaque scène, ajuste le débit pour viser `target` secondes."""
    for attempt in range(3):
        clips = [voice.say(sc["voice"], tmp / f"v{i}.wav") for i, sc in enumerate(ep["scenes"])]
        durs = [len(cl) / audio.SR + LEAD_IN + TAIL for cl in clips]
        total = sum(durs)
        print(f"[voix] {voice.engine}, débit x{voice.length_scale:.2f} -> {total:.1f} s")
        if abs(total - target) <= 1.5 or attempt == 2 or voice.tts == "silent":
            break
        new = max(MIN_SCALE, min(1.15, voice.length_scale * (target - 0.5) / total))
        if abs(new - voice.length_scale) < 0.01:
            break
        voice.length_scale = new
    words = sum(len(sc["voice"].split()) for sc in ep["scenes"])
    wpm = words / max(0.1, sum(len(c) for c in clips) / audio.SR) * 60
    print(f"[voix] débit : {wpm:.0f} mots/min (confortable : 150-175)")
    if total > target + 2:
        print(f"[voix] ! {total:.0f} s au lieu de {target:.0f} : raccourcis le texte plutôt que d'accélérer la voix")
    return clips, durs


def plan_subtitles(ep, starts, clips):
    """Blocs de sous-titres et instant de chaque mot (proportionnel à sa longueur)."""
    subs = []
    for sc, st, cl in zip(ep["scenes"], starts, clips):
        chunks = scenes.caption_chunks(sc.get("caption", sc["voice"]))
        vdur = len(cl) / audio.SR
        weights = [sum(len(w) + 2 for w in ch) for ch in chunks]
        acc = st + LEAD_IN
        sc["_subs"] = []
        for ch, wt in zip(chunks, weights):
            d = vdur * wt / sum(weights)
            marks, a = [], acc
            for w in ch:
                marks.append(a)
                a += d * (len(w) + 2) / wt
            subs.append((acc, acc + d, ch, marks))
            sc["_subs"].append((acc - st, acc + d - st, " ".join(ch).lower()))
            acc += d
    return subs


def render(ep, args, tmp):
    gfx.set_theme(ep)
    target = float(args.target or ep.get("target_seconds", 60))
    voice = audio.Voice(args.voice, length_scale=args.speed, tts=args.tts, ref=args.ref,
                        exaggeration=args.exaggeration, cfg_weight=args.cfg)
    clips, durs = build_audio(ep, voice, tmp, target)
    total = sum(durs)
    starts = list(np.cumsum([0] + durs[:-1]))

    # --- pistes audio
    n = int((total + 1) * audio.SR)
    voice_track, sfx = np.zeros(n, dtype=np.float32), np.zeros(n, dtype=np.float32)
    for k, (cl, st) in enumerate(zip(clips, starts)):
        i = int((st + LEAD_IN) * audio.SR)
        voice_track[i:i + len(cl)] += cl
        if k:
            w = audio.whoosh(seed=k)
            j = max(0, int((st - 0.12) * audio.SR))
            sfx[j:j + len(w)] += w[: len(sfx) - j]
    if args.no_music:
        music = np.zeros(n, dtype=np.float32)
    elif args.music:
        music = audio.load_music(args.music, total + 1, tmp)
    else:
        music = audio.ambient(total + 1)
    wav = tmp / "mix.wav"
    cut = int(total * audio.SR)
    audio.mix(voice_track[:cut], music[:cut], sfx[:cut], wav)

    subs = plan_subtitles(ep, starts, clips)
    base = gfx.background()

    def frame_at(gt):
        k = max(i for i, s in enumerate(starts) if s <= gt + 1e-9)
        sc, st, d = ep["scenes"][k], starts[k], durs[k]
        lt = gt - st
        frame = base.copy()
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        scenes.SCENES[sc["type"]](layer, lt, d, sc, ep)
        fade = 1.0 if k == len(starts) - 1 else gfx.clamp((d - lt) / EXIT)
        if fade < 1:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * fade)))
        frame.alpha_composite(layer)
        scenes.header(frame, ep, gt, starts, durs)
        for a, b, words, marks in subs:
            if a <= gt < b + 0.1:
                hot = max(i for i, m in enumerate(marks) if m <= gt + 1e-9) if gt >= marks[0] else 0
                scenes.subtitles(frame, words, hot, gfx.ease_out((gt - a) / 0.12))
                break
        return frame.convert("RGB")

    out = Path(args.out or ROOT / "out" / f"{ep['id']}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.preview:
        pdir = out.parent / f"{ep['id']}_preview"
        pdir.mkdir(exist_ok=True)
        for i in range(args.preview):
            gt = total * (i + 0.5) / args.preview
            frame_at(gt).save(pdir / f"{i:02d}.png")
        print(f"[aperçu] {args.preview} images dans {pdir}")
        return

    use_nvenc = args.nvenc and nvenc_ok()
    if args.nvenc and not use_nvenc:
        print("[vidéo] NVENC indisponible -> encodage processeur (libx264)")
    venc = ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "20"] if use_nvenc else \
           ["-c:v", "libx264", "-preset", "medium", "-crf", "19"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), *venc, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(total * FPS)
    for f in range(nframes):
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
                    help="modèle Piper .onnx (sinon espeak-ng)")
    ap.add_argument("--tts", choices=["piper", "chatterbox", "silent"], default="piper",
                    help="moteur de voix (silent : sans voix, pour les aperçus rapides)")
    ap.add_argument("--ref", help="chatterbox : extrait .wav de 5-10 s d'une voix à imiter (la tienne)")
    ap.add_argument("--exaggeration", type=float, default=0.5, help="chatterbox : expressivité 0.3-0.8")
    ap.add_argument("--cfg", type=float, default=0.5, help="chatterbox : 0.3 = débit plus posé")
    ap.add_argument("--speed", type=float, default=1.0, help="length_scale Piper de départ (<1 = plus rapide)")
    ap.add_argument("--target", type=float, help="durée visée en secondes (défaut : celle de l'épisode)")
    ap.add_argument("--music", help="ta musique de fond (mp3, wav…) à la place de la musique générée")
    ap.add_argument("--no-music", action="store_true", help="voix seule")
    ap.add_argument("--nvenc", action="store_true", help="encodage GPU NVIDIA (si disponible)")
    ap.add_argument("--preview", type=int, default=0, help="n'exporte que N images PNG d'aperçu")
    args = ap.parse_args()
    ep = json.loads(Path(args.episode).read_text(encoding="utf-8"))
    errors = validate(ep)
    if errors:
        sys.exit("Épisode invalide :\n  - " + "\n  - ".join(errors))
    with tempfile.TemporaryDirectory(prefix="infoclair_") as tmp:   # supprimé même en cas d'erreur
        render(ep, args, Path(tmp))


if __name__ == "__main__":
    main()
