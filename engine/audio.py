"""Voix off (Piper TTS, repli espeak-ng) + musique chiptune générée + mixage."""
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100


# ------------------------------------------------------------ voix
def _read_wav(path):
    with wave.open(str(path), "rb") as wf:
        sr, n, ch = wf.getframerate(), wf.getnframes(), wf.getnchannels()
        data = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32) / 32768
    if ch > 1:
        data = data.reshape(-1, ch).mean(axis=1)
    if sr != SR:
        x_old = np.linspace(0, 1, len(data), endpoint=False)
        x_new = np.linspace(0, 1, int(len(data) * SR / sr), endpoint=False)
        data = np.interp(x_new, x_old, data).astype(np.float32)
    return data


def _write_wav(path, data, sr):
    pcm = (np.clip(data, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def _atempo(data, factor, tmpdir):
    """Accélère/ralentit sans changer la hauteur de la voix (ffmpeg atempo)."""
    if abs(factor - 1) < 0.01:
        return data
    src, dst = Path(tmpdir) / "_tempo_in.wav", Path(tmpdir) / "_tempo_out.wav"
    _write_wav(src, data, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-filter:a", f"atempo={factor:.3f}", str(dst)], check=True)
    return _read_wav(dst)


def _trim(data):
    idx = np.where(np.abs(data) > 0.01)[0]
    if len(idx):
        data = data[max(0, idx[0] - 400): idx[-1] + 1200]
    return data


class Voice:
    """Moteurs : piper (rapide, CPU), chatterbox (plus naturel, GPU), espeak-ng (secours)."""

    def __init__(self, model=None, length_scale=1.0, tts="piper", ref=None,
                 exaggeration=0.5, cfg_weight=0.5):
        self.model = Path(model) if model else None
        self.length_scale = length_scale
        self.tts = tts
        self.ref = str(ref) if ref else None
        self.exaggeration, self.cfg_weight = exaggeration, cfg_weight
        self._piper = self._cb = None
        self._cache = {}
        if tts == "chatterbox":
            import torch
            from chatterbox.mtl_tts import ChatterboxMultilingualTTS
            dev = "cuda" if torch.cuda.is_available() else "cpu"
            try:
                self._cb = ChatterboxMultilingualTTS.from_pretrained(device=dev, t3_model="v3")
            except TypeError:
                self._cb = ChatterboxMultilingualTTS.from_pretrained(device=dev)
            print(f"[voix] chatterbox sur {dev}")
            return
        if self.model and self.model.exists():
            try:
                from piper import PiperVoice
                self._piper = PiperVoice.load(str(self.model))
            except Exception as e:  # noqa: BLE001
                print(f"[voix] Piper indisponible ({e}), repli espeak-ng")
        if not self._piper and not shutil.which("espeak-ng"):
            raise SystemExit("Aucun moteur de voix : installe piper-tts (+ un modèle .onnx) ou espeak-ng.")

    @property
    def engine(self):
        if self._cb:
            return "chatterbox"
        return f"piper ({self.model.stem})" if self._piper else "espeak-ng"

    def say(self, text, out_wav):
        out_wav = Path(out_wav)
        if self._cb:
            # synthèse unique (lente) puis réglage du débit par time-stretch
            if text not in self._cache:
                kw = dict(language_id="fr", exaggeration=self.exaggeration, cfg_weight=self.cfg_weight)
                if self.ref:
                    kw["audio_prompt_path"] = self.ref
                wav = self._cb.generate(text, **kw)
                arr = wav.squeeze().detach().cpu().numpy().astype(np.float32)
                _write_wav(out_wav, arr, self._cb.sr)
                self._cache[text] = _trim(_read_wav(out_wav))
            return _atempo(self._cache[text], 1 / self.length_scale, out_wav.parent)
        if self._piper:
            from piper import SynthesisConfig
            cfg = SynthesisConfig(length_scale=self.length_scale, noise_scale=0.667, noise_w_scale=0.8)
            with wave.open(str(out_wav), "wb") as wf:
                self._piper.synthesize_wav(text, wf, syn_config=cfg)
        else:
            speed = int(150 / self.length_scale)
            subprocess.run(["espeak-ng", "-v", "fr", "-s", str(speed), "-w", str(out_wav), text], check=True)
        return _trim(_read_wav(out_wav))


# ------------------------------------------------------------ chiptune
def _note_freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _square(freq, dur, duty=0.25, vol=0.2):
    t = np.arange(int(dur * SR)) / SR
    wave_ = np.where((t * freq) % 1 < duty, 1.0, -1.0)
    env = np.minimum(1, np.linspace(1.3, 0, len(t)) * 1.0)
    return (wave_ * env * vol).astype(np.float32)


def _triangle(freq, dur, vol=0.25):
    t = np.arange(int(dur * SR)) / SR
    wave_ = 2 * np.abs(2 * ((t * freq) % 1) - 1) - 1
    env = np.minimum(1, np.linspace(4, 0, len(t)))
    return (wave_ * env * vol).astype(np.float32)


def _noise(dur, vol=0.08, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    env = np.exp(-np.linspace(0, 12, n))
    return (rng.uniform(-1, 1, n) * env * vol).astype(np.float32)


def _kick(dur=0.15, vol=0.35):
    t = np.arange(int(dur * SR)) / SR
    f = 120 * np.exp(-t * 25) + 40
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * vol).astype(np.float32)


def chiptune(total_s, bpm=124, seed=42):
    """Boucle 8 bits joyeuse : I-V-vi-IV en Do, lead carré, basse triangle."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    step = beat / 2  # croches
    prog = [(60, [0, 4, 7]), (67, [0, 4, 7]), (69, [0, 3, 7]), (65, [0, 4, 7])]  # C G Am F
    pent = [0, 2, 4, 7, 9]
    bar_steps = 8
    # motif mélodique de 2 mesures, répété avec variation
    motif = [int(rng.integers(0, 5)) for _ in range(16)]
    rests = {3, 7, 11, 15}
    out = np.zeros(int((total_s + 2) * SR), dtype=np.float32)

    def add(sig, at):
        i = int(at * SR)
        j = min(len(out), i + len(sig))
        if i < len(out):
            out[i:j] += sig[: j - i]

    t, s = 0.0, 0
    while t < total_s + 1:
        bar = (s // bar_steps) % len(prog)
        root, chord = prog[bar]
        k = s % bar_steps
        # basse
        if k % 2 == 0:
            add(_triangle(_note_freq(root - 24 + (12 if k == 4 else 0)), step * 1.8), t)
        # batterie
        if k in (0, 4):
            add(_kick(), t)
        if k % 2 == 1:
            add(_noise(0.05, seed=s), t)
        if k in (2, 6):
            add(_noise(0.12, vol=0.12, seed=s + 99), t)
        # lead
        m = s % 16
        if m not in rests:
            deg = pent[(motif[m] + (s // 32) % 2) % 5]
            add(_square(_note_freq(root + 12 + deg - (root - 60)), step * 0.9, duty=0.25, vol=0.07), t)
        # arpège discret
        add(_square(_note_freq(root + chord[k % 3]), step * 0.5, duty=0.125, vol=0.025), t)
        t += step
        s += 1
    return out[: int(total_s * SR)]


def blip(freq=880, dur=0.08, vol=0.25):
    a = _square(freq, dur / 2, duty=0.5, vol=vol)
    b = _square(freq * 1.5, dur / 2, duty=0.5, vol=vol)
    return np.concatenate([a, b])


# ------------------------------------------------------------ mixage
def mix(voice_track, music, sfx, out_wav, music_vol=0.35, duck=0.75):
    n = max(len(voice_track), len(music))
    v = np.pad(voice_track, (0, n - len(voice_track)))
    m = np.pad(music, (0, n - len(music))) * music_vol
    k = int(SR / 2500)          # passe-bas doux (~2,5 kHz) : la voix garde ses aigus
    m = np.convolve(m, np.ones(k) / k, mode="same")
    # ducking : la musique baisse quand la voix parle
    env = np.abs(v)
    win = int(0.15 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env = np.clip(env / (env.max() + 1e-6) * 4, 0, 1)
    m *= 1 - duck * env
    s = np.pad(sfx, (0, max(0, n - len(sfx))))[:n]
    mixd = v * 0.95 + m + s
    peak = np.abs(mixd).max()
    if peak > 0.98:
        mixd *= 0.98 / peak
    # fondu de fin
    fade = int(0.6 * SR)
    mixd[-fade:] *= np.linspace(1, 0, fade)
    pcm = (mixd * 32767).astype(np.int16)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())
