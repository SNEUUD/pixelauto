"""Rendu des scènes sur un canevas 180x320 (agrandi x6 -> 1080x1920).

Zones sûres TikTok (en pixels internes) : haut ~26 px (onglets),
bas ~68 px (description, musique), droite ~22 px (boutons).
L'action se joue entre y=40 et y=205, les sous-titres vers y=212-246.
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from . import sprites as S
from .sprites import PAL, c

W, H = 180, 320
GROUND = 196          # ligne de sol
FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "PressStart2P-Regular.ttf"
_fonts = {}


def font(size=8):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(str(FONT_PATH), size)
    return _fonts[size]


def draw_ctx(img):
    d = ImageDraw.Draw(img)
    d.fontmode = "1"   # pas d'anti-aliasing : vrais pixels
    return d


def text(img, xy, s, col=S.WHITE, size=8, anchor="la", shadow=S.K, stroke=True):
    d = draw_ctx(img)
    x, y = xy
    if stroke:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    d.text((x + dx, y + dy), s, font=font(size), fill=c(shadow), anchor=anchor)
    d.text((x, y), s, font=font(size), fill=c(col), anchor=anchor)


def text_w(s, size=8):
    return int(font(size).getlength(s))


# ------------------------------------------------------------ décors
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def sky(img, bands):
    """Ciel en bandes avec tramage Bayer entre deux couleurs (look 8 bits)."""
    px = img.load()
    n = len(bands) - 1
    for y in range(H):
        pos = y / H * n
        i = min(int(pos), n - 1)
        frac = pos - i
        for x in range(W):
            col = bands[i + 1] if frac * 16 > BAYER[y % 4][x % 4] else bands[i]
            px[x, y] = PAL[col] + (255,)


_sky_cache = {}


def sky_cached(img, bands):
    key = tuple(bands)
    if key not in _sky_cache:
        tmp = Image.new("RGBA", (W, H))
        sky(tmp, bands)
        _sky_cache[key] = tmp
    img.alpha_composite(_sky_cache[key])


def hills(img, t, col, y0, amp, speed, freq=0.05, phase=0):
    d = draw_ctx(img)
    off = t * speed
    for x in range(W):
        y = int(y0 + amp * math.sin((x + off) * freq + phase) + amp * 0.5 * math.sin((x + off) * freq * 2.3))
        d.line([(x, y), (x, H)], fill=c(col))


def ground(img, t, top=S.GREEN, dirt=S.BROWN, speed=40, furrows=False):
    d = draw_ctx(img)
    d.rectangle([(0, GROUND), (W, H)], fill=c(dirt))
    d.rectangle([(0, GROUND), (W, GROUND + 3)], fill=c(top))
    off = int(t * speed)
    for y in range(GROUND + 8, H, 7 if furrows else 11):
        for x in range(-16, W + 16, 16):
            xx = x - (off % 16) + (y * 3 % 16)
            d.line([(xx, y), (xx + (9 if furrows else 4), y)], fill=c(S.ORANGE if furrows else S.DGREY))


def road(img, t, speed=60):
    d = draw_ctx(img)
    d.rectangle([(0, GROUND), (W, H)], fill=c(S.DGREY))
    d.rectangle([(0, GROUND), (W, GROUND + 1)], fill=c(S.LGREY))
    off = int(t * speed) % 24
    for x in range(-24, W + 24, 24):
        d.rectangle([(x - off, GROUND + 14), (x - off + 12, GROUND + 15)], fill=c(S.WHITE))
    d.rectangle([(0, GROUND + 30), (W, H)], fill=c(S.GREEN))


def clouds(img, t, speed=6, col=S.WHITE, seed=1):
    rnd = random.Random(seed)
    d = draw_ctx(img)
    for _ in range(4):
        x0, y0, s = rnd.randint(0, 260), rnd.randint(44, 110), rnd.randint(8, 16)
        x = (x0 - t * speed * (s / 10)) % 260 - 40
        d.ellipse([(x, y0), (x + s * 2, y0 + s * 0.8)], fill=c(col))
        d.ellipse([(x + s * 0.6, y0 - s * 0.4), (x + s * 1.6, y0 + s * 0.5)], fill=c(col))


def stars(img, t, seed=3, n=40):
    rnd = random.Random(seed)
    px = img.load()
    for i in range(n):
        x, y = rnd.randint(0, W - 1), rnd.randint(30, 170)
        if (int(t * 3) + i) % 7:
            px[x, y] = PAL[S.WHITE if i % 3 else S.YELLOW] + (255,)


def paste(img, spr, x, y, anchor="mb"):
    """Colle un sprite ; anchor mb = milieu bas."""
    w, h = spr.size
    if anchor == "mb":
        x, y = x - w // 2, y - h
    elif anchor == "mm":
        x, y = x - w // 2, y - h // 2
    img.alpha_composite(spr, (int(x), int(y)))


def ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def pop(p):
    """0 -> 1 avec léger rebond (apparition d'icônes)."""
    p = max(0.0, min(1.0, p))
    return 1 + 0.25 * math.sin(p * math.pi) if p < 1 else 1


def car_sprite(ep, t, moving=True, lights_up=False, **kw):
    """Sprite de la voiture de l'épisode, décrite en JSON ("profile", voir README)."""
    return S.custom_car_frame(t, ep["car"], moving=moving, lights_up=lights_up, **kw)


def car_at(img, t, x, y, ep, moving=True, bounce=0.0, lights_up=False, flip=False, **kw):
    spr = car_sprite(ep, t, moving, lights_up, **kw)
    if flip:   # la voiture roule vers la gauche
        spr = spr.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    dy = int(round(bounce * abs(math.sin(t * 9)))) if moving else 0
    paste(img, spr, x, y - dy)
    return spr


def badge(img, label, x=8, y=40):
    w = text_w(label) + 8
    d = draw_ctx(img)
    d.rectangle([(x, y), (x + w, y + 13)], fill=c(S.K))
    d.rectangle([(x + 1, y + 1), (x + w - 1, y + 12)], fill=c(S.YELLOW))
    text(img, (x + 4, y + 3), label, col=S.K, stroke=False)


# ------------------------------------------------------------ décors de la banque
def backdrop(img, t, dur, sc, speed=0.0):
    """Colle le décor de la banque ("bg") s'il y en a un (panoramique lent).
    Renvoie True si un décor a été posé, sinon la scène dessine le sien."""
    bg = sc.get("_bg")
    if bg is None:
        return False
    extra = bg.width - W
    x = -int(extra * min(1.0, t / dur) * speed) if extra > 0 else 0
    img.alpha_composite(bg, (x, 0))
    return True


# ------------------------------------------------------------ scènes
def scene_outro(img, t, dur, sc, ep):
    sky_cached(img, [S.K, S.NAVY])
    stars(img, t, seed=11, n=60)
    ground(img, 0, top=S.LAVENDER, dirt=S.NAVY, speed=0)
    title = ep["title"].split(" ")
    y = 50
    for word in title:
        text(img, (W // 2, y), word, col=S.YELLOW, anchor="ma", size=16)
        y += 22
    text(img, (W // 2, y + 2), ep.get("subtitle", ""), anchor="ma")
    car_at(img, t, 90, GROUND + 6, ep, moving=False)
    d = draw_ctx(img)
    for i in range(3):          # pots d'échappement
        life = (t * 10 + i * 6) % 18
        d.rectangle([(48 - life, GROUND - 2 - life * 0.3), (50 - life, GROUND - life * 0.3)], fill=c(S.LGREY))
    if int(t * 2) % 2 == 0:
        text(img, (W // 2, 140), "PROCHAIN", col=S.WHITE, anchor="ma")
        text(img, (W // 2, 152), "ÉPISODE ?", col=S.WHITE, anchor="ma")


SCENES = {"outro": scene_outro}   # + les scènes de generic.py


# ------------------------------------------------------------ habillage
def header(img, ep):
    s = ep.get("series", "")
    if s:
        text(img, (W // 2, 28), s, col=S.WHITE, anchor="ma")


def wrap(words, max_chars=19):
    lines, cur = [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def caption_chunks(caption, max_chars=19, max_lines=2):
    """Découpe en blocs de 1-2 lignes façon sous-titres TikTok."""
    words, glue_next = [], False
    for w in caption.split():          # « ? », « ! », « : » restent collés au mot précédent
        if glue_next and words:
            words[-1] += "\u00a0" + w
            glue_next = False
        elif words and w in ("?", "!", ":", ";", "»"):
            words[-1] += "\u00a0" + w
        elif w == "«":                 # « reste collé au mot suivant
            words.append(w)
            glue_next = True
        else:
            words.append(w)
    chunks, cur = [], []
    for w in words:
        test = cur + [w]
        if len(wrap(test, max_chars)) > max_lines or (cur and cur[-1][-1] in ".?!:…" and len(" ".join(cur)) > 8):
            chunks.append(cur)
            cur = [w]
        else:
            cur = test
    if cur:
        chunks.append(cur)
    # évite les sous-titres orphelins d'un seul petit mot (« PARAPLUIE. »)
    merged = []
    for ch in chunks:
        if merged and len(" ".join(ch)) < 11:
            if len(wrap(merged[-1] + ch, max_chars)) <= max_lines:
                merged[-1] = merged[-1] + ch
                continue
            prev = list(merged[-1])
            ch = list(ch)
            while len(" ".join(ch)) < 11 and len(prev) > 1 and \
                    len(wrap([prev[-1]] + ch, max_chars)) <= max_lines:
                ch.insert(0, prev.pop())
            merged[-1] = prev
        merged.append(ch)
    return [wrap(ch, max_chars) for ch in merged]


def subtitles(img, lines):
    y0 = 214
    cx = 86
    for i, line in enumerate(lines):
        text(img, (cx, y0 + i * 12), line.upper().replace("\u00a0", " "), col=S.WHITE, anchor="ma")


def transition(img, p):
    """Volet pixel (stores) en début de scène, p de 0 à 1."""
    if p >= 1:
        return
    d = draw_ctx(img)
    h = int(8 * (1 - p))
    if h <= 0:
        return
    for y in range(0, H, 8):
        d.rectangle([(0, y), (W, y + h - 1)], fill=c(S.K))
