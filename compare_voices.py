#!/usr/bin/env python3
"""Génère la même phrase avec chaque voix disponible, pour choisir à l'oreille.

    python3 compare_voices.py                      # toutes les voix Piper de voices/ (+ chatterbox si installé)
    python3 compare_voices.py --ref ma_voix.wav    # chatterbox imite ta voix (5-10 s, sans musique)

Sortie : samples/<voix>.wav — écoute-les et choisis.
"""
import argparse
import time
from pathlib import Path

from engine import audio

ROOT = Path(__file__).resolve().parent
TEXT = ("Le sept octobre mille neuf cent quarante-huit, elle est enfin dévoilée au Salon de Paris. "
        "On se moque. Le public, lui, l'adopte.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", default=TEXT)
    ap.add_argument("--ref", help="extrait .wav pour le clonage de voix chatterbox")
    args = ap.parse_args()
    out = ROOT / "samples"
    out.mkdir(exist_ok=True)

    jobs = [("piper", m) for m in sorted((ROOT / "voices").glob("*.onnx"))]
    try:
        import chatterbox  # noqa: F401
        jobs.append(("chatterbox", None))
    except ImportError:
        print("(chatterbox non installé : bash install_tts.sh pour l'ajouter)")

    for tts, model in jobs:
        name = model.stem if model else ("chatterbox_clone" if args.ref else "chatterbox")
        t0 = time.time()
        v = audio.Voice(model, tts=tts, ref=args.ref)
        data = v.say(args.text, out / f"_{name}.wav")
        audio._write_wav(out / f"{name}.wav", data, audio.SR)
        (out / f"_{name}.wav").unlink(missing_ok=True)
        dur = len(data) / audio.SR
        wpm = len(args.text.split()) / dur * 60
        print(f"{name:28s} {dur:4.1f} s  {wpm:3.0f} mots/min  (calcul {time.time() - t0:.0f} s)")
    print(f"\nÉcoute les fichiers dans {out}/")


if __name__ == "__main__":
    main()
