"""Voix off (Piper TTS, repli espeak-ng), musique d'ambiance générée ou fournie, mixage."""
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 44100


# ------------------------------------------------------------ fichiers wav
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


def _write_wav(path, data, sr=SR):
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
    _write_wav(src, data)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-filter:a", f"atempo={factor:.3f}", str(dst)], check=True)
    return _read_wav(dst)


def _trim(data):
    idx = np.where(np.abs(data) > 0.01)[0]
    if len(idx):
        data = data[max(0, idx[0] - 400): idx[-1] + 1200]
    return data


# ------------------------------------------------------------ voix
class Voice:
    """Moteurs : piper (rapide, CPU), chatterbox (plus naturel, GPU), espeak-ng (secours),
    silent (aucune voix, durée estimée : pour régler la mise en page très vite)."""

    def __init__(self, model=None, length_scale=1.0, tts="piper", ref=None,
                 exaggeration=0.5, cfg_weight=0.5):
        self.model = Path(model) if model else None
        self.length_scale = length_scale
        self.tts = tts
        self.ref = str(ref) if ref else None
        self.exaggeration, self.cfg_weight = exaggeration, cfg_weight
        self._piper = self._cb = None
        self._cache = {}
        if tts == "silent":
            return
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
        if self.tts == "silent":
            return "silencieuse"
        if self._cb:
            return "chatterbox"
        return f"piper ({self.model.stem})" if self._piper else "espeak-ng"

    def say(self, text, out_wav):
        out_wav = Path(out_wav)
        if self.tts == "silent":     # ~165 mots/min
            return np.zeros(int(len(text.split()) * 0.36 * self.length_scale * SR), dtype=np.float32)
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
            speed = int(165 / self.length_scale)
            subprocess.run(["espeak-ng", "-v", "fr", "-s", str(speed), "-w", str(out_wav), text], check=True)
        return _trim(_read_wav(out_wav))


# ------------------------------------------------------------ musique d'ambiance
def _freq(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _env(n, attack, release):
    e = np.ones(n, dtype=np.float32)
    a, r = min(n, int(attack * SR)), min(n, int(release * SR))
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def _pad(notes, dur, vol=0.05):
    """Nappe douce : sinus légèrement désaccordés + un peu d'harmonique 2."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, dtype=np.float32)
    for m in notes:
        f = _freq(m)
        for det in (0.997, 1.003):
            out += np.sin(2 * np.pi * f * det * t) + 0.18 * np.sin(4 * np.pi * f * det * t)
    return out * _env(n, dur * 0.35, dur * 0.45) * vol / len(notes)


def _pluck(midi, dur=0.9, vol=0.08):
    """Note « kalimba » : attaque nette, décroissance exponentielle."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = _freq(midi)
    sig = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 18)
    return (sig * np.exp(-t * 5.5) * _env(n, 0.004, 0.05) * vol).astype(np.float32)


def _kick(vol=0.22):
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    f = 95 * np.exp(-t * 30) + 45
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16) * vol).astype(np.float32)


def _hat(seed, vol=0.018):
    rng = np.random.default_rng(seed)
    n = int(0.05 * SR)
    x = rng.uniform(-1, 1, n)
    x = np.diff(x, prepend=0)              # passe-haut grossier : son plus fin
    return (x * np.exp(-np.linspace(0, 9, n)) * vol).astype(np.float32)


def ambient(total_s, bpm=92, seed=7):
    """Boucle calme et neutre (ambiance « tech ») : Am7 - Fmaj7 - C - G6,
    nappe, arpège kalimba, basse ronde et percussion légère."""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bar = beat * 4
    prog = [(57, [0, 3, 7, 10]), (53, [0, 4, 7, 11]), (48, [0, 4, 7, 12]), (55, [0, 4, 7, 9])]
    out = np.zeros(int((total_s + 4) * SR), dtype=np.float32)

    def add(sig, at):
        i = int(at * SR)
        j = min(len(out), i + len(sig))
        if 0 <= i < len(out):
            out[i:j] += sig[: j - i]

    pattern = [0, 2, 1, 3, 2, 1, 3, 2]          # ordre de l'arpège sur 8 croches
    t, k = 0.0, 0
    while t < total_s + 1:
        root, chord = prog[k % len(prog)]
        add(_pad([root + 12 + c for c in chord[:3]], bar * 1.25), t - bar * 0.1 if t else 0)
        add(_pluck(root - 12, 1.8, 0.10), t)                           # basse
        add(_pluck(root - 12, 1.2, 0.06), t + beat * 2.5)
        for s in range(8):
            if s in (3, 7) and rng.random() < 0.5:                     # respirations aléatoires
                continue
            note = root + 24 + chord[pattern[s] % len(chord)]
            add(_pluck(note, 0.9, 0.045 if s % 2 else 0.06), t + s * beat / 2)
        for b in range(4):
            if b in (0, 2) and k > 0:                                  # pas de batterie sur la 1re mesure
                add(_kick(), t + b * beat)
            if k > 0:
                add(_hat(k * 8 + b), t + b * beat + beat / 2)
        t += bar
        k += 1
    # adoucit le haut du spectre
    kern = int(SR / 5000)
    out = np.convolve(out, np.ones(kern) / kern, mode="same").astype(np.float32)
    out /= max(1e-6, np.abs(out).max())
    return out[: int(total_s * SR)] * 0.6


def load_music(path, total_s, tmpdir):
    """Ta musique (mp3, wav…) : convertie, bouclée si trop courte, coupée à la bonne durée."""
    dst = Path(tmpdir) / "_music.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), str(dst)],
                   check=True)
    data = _read_wav(dst)
    n = int(total_s * SR)
    if len(data) < n:
        data = np.tile(data, n // max(1, len(data)) + 1)
    data = data[:n]
    return data / max(1e-6, np.abs(data).max()) * 0.6


def whoosh(dur=0.32, vol=0.05, seed=0):
    """Souffle discret aux changements de scène."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.uniform(-1, 1, n)
    k = 24
    x = np.convolve(x, np.ones(k) / k, mode="same")
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return (x * env * vol * 4).astype(np.float32)


# ------------------------------------------------------------ mixage
def mix(voice_track, music, sfx, out_wav, music_vol=0.30, duck=0.7):
    n = max(len(voice_track), len(music))
    v = np.pad(voice_track, (0, n - len(voice_track)))
    m = np.pad(music, (0, n - len(music))) * music_vol
    # ducking : la musique baisse quand la voix parle
    env = np.abs(v)
    win = int(0.2 * SR)
    env = np.convolve(env, np.ones(win) / win, mode="same")
    env = np.clip(env / (env.max() + 1e-6) * 4, 0, 1)
    m *= 1 - duck * env
    s = np.pad(sfx, (0, max(0, n - len(sfx))))[:n]
    mixd = v * 0.95 + m + s
    peak = np.abs(mixd).max()
    if peak > 0.98:
        mixd *= 0.98 / peak
    fade = int(0.8 * SR)                   # fondu de fin
    mixd[-fade:] *= np.linspace(1, 0, fade)
    _write_wav(out_wav, mixd)
