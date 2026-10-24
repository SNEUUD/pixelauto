"""Briques graphiques : thème, polices, texte, cartes, animations.

Tout est dessiné en 1080x1920 (taille finale, pas d'agrandissement).
Les formes sont tracées en sur-échantillonnage puis réduites : bords nets et lisses.
Les éléments fixes (cartes, textes, icônes) sont mis en cache : seule leur position
et leur opacité changent d'une image à l'autre.

Zones sûres TikTok : haut ~170 px (onglets), bas ~410 px (description, musique),
droite ~130 px (boutons). Le visuel se joue entre y=300 et y=1230,
les sous-titres vers y=1290-1480.
"""
import math
import re
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
CX = W // 2
STAGE_TOP, STAGE_BOT = 300, 1230
STAGE_CY = (STAGE_TOP + STAGE_BOT) // 2
CONTENT_W = 840                       # largeur utile du visuel
SS = 3                                # facteur de sur-échantillonnage des formes
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# ------------------------------------------------------------ thème
THEMES = {
    "light": {
        "bg": (244, 245, 248), "grid": (222, 226, 233), "card": (255, 255, 255),
        "text": (17, 24, 39), "muted": (99, 107, 122), "line": (224, 228, 235),
        "shadow": (15, 23, 42), "shadow_a": 30,
        "code_bg": (24, 28, 36), "code_bar": (34, 39, 49), "term_bg": (14, 16, 20),
    },
    "dark": {
        "bg": (12, 15, 21), "grid": (31, 37, 48), "card": (23, 28, 37),
        "text": (241, 244, 248), "muted": (148, 158, 174), "line": (45, 52, 64),
        "shadow": (0, 0, 0), "shadow_a": 90,
        "code_bg": (18, 21, 28), "code_bar": (28, 33, 42), "term_bg": (8, 10, 13),
    },
}
ACCENTS = {
    "bleu": (37, 99, 235), "indigo": (79, 70, 229), "violet": (124, 58, 237),
    "vert": (22, 163, 74), "cyan": (8, 145, 178), "orange": (234, 88, 12),
    "rose": (219, 39, 119), "rouge": (220, 38, 38),
}
# couleur secondaire (côté « monde réel » des analogies, côté droit des comparaisons)
SECOND = {"bleu": "orange", "indigo": "orange", "violet": "vert", "vert": "violet",
          "cyan": "rose", "orange": "bleu", "rose": "cyan", "rouge": "bleu"}


class Theme(dict):
    __getattr__ = dict.__getitem__


T = Theme()


def parse_color(v, default):
    if isinstance(v, str) and v.lower() in ACCENTS:
        return ACCENTS[v.lower()]
    if isinstance(v, str) and re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
        v = v.lstrip("#")
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return tuple(int(x) for x in v)
    return default


def set_theme(ep):
    """Thème de l'épisode : "theme": light | dark, "accent": nom ou #RRGGBB, "accent2"."""
    T.clear()
    T.update(THEMES.get(ep.get("theme", "light"), THEMES["light"]))
    name = ep.get("accent", "bleu")
    T["accent"] = parse_color(name, ACCENTS["bleu"])
    second = SECOND.get(str(name).lower(), "orange")
    T["accent2"] = parse_color(ep.get("accent2", second), ACCENTS[second])
    T["name"] = ep.get("theme", "light")
    T["on_accent"] = (255, 255, 255)
    _bg_cache.clear()
    _variants.clear()
    for f in (text_img, rich_block, shadow_img, card, pill, disc):   # sprites calculés avec l'ancien thème
        f.cache_clear()
    return T


def mix(a, b, k):
    """Mélange deux couleurs RGB (k=0 -> a, k=1 -> b)."""
    return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


def tint(col, k=0.12):
    """Couleur pâle dérivée de `col` sur le fond des cartes (pastilles d'icônes)."""
    return mix(T.card, col, k if T.name == "light" else k * 1.6)


# ------------------------------------------------------------ polices
_fonts = {}
_warned = []


def font(size, weight=400, mono=False):
    """Inter (texte) ou JetBrains Mono (code), polices variables : graisse 100-900."""
    key = (size, weight, mono)
    if key in _fonts:
        return _fonts[key]
    path = FONT_DIR / ("JetBrainsMono.ttf" if mono else "Inter.ttf")
    try:
        f = ImageFont.truetype(str(path), size)
        try:
            if mono:
                f.set_variation_by_axes([min(800, weight)])
            else:
                f.set_variation_by_axes([32 if size >= 40 else 14, weight])
        except (OSError, ValueError):
            pass
    except OSError:
        if not _warned:
            print(f"[polices] {path.name} introuvable dans assets/fonts : police de secours")
            _warned.append(1)
        fallback = "DejaVuSansMono.ttf" if mono else ("DejaVuSans-Bold.ttf" if weight >= 600 else "DejaVuSans.ttf")
        try:
            f = ImageFont.truetype(fallback, size)
        except OSError:
            f = ImageFont.load_default(size)
    _fonts[key] = f
    return f


def text_w(s, size, weight=400, mono=False):
    return font(size, weight, mono).getlength(s)


# ------------------------------------------------------------ texte
def parse_rich(s):
    """« un *mot* important » -> [("un", False), ("mot", True), ("important", False)]."""
    words = []
    for part in re.split(r"(\*[^*]+\*)", str(s)):
        hot = part.startswith("*") and part.endswith("*") and len(part) > 2
        toks = (part[1:-1] if hot else part).split()
        if toks and words and not hot and not part[0].isspace():   # « *IP*. » : le point reste collé
            words[-1] = (words[-1][0] + toks.pop(0), words[-1][1])
        words.extend((w, hot) for w in toks)
    return _glue(words)


def _glue(words):
    """Typographie française : « ? ! : ; » restent collés au mot précédent (espace insécable)."""
    out, glue_next = [], False
    for w, hot in words:
        if glue_next and out:
            out[-1] = (out[-1][0] + " " + w, out[-1][1] or hot)
            glue_next = False
        elif out and w in ("?", "!", ":", ";", "»", "%"):
            out[-1] = (out[-1][0] + " " + w, out[-1][1])
        elif w == "«":
            out.append((w, hot))
            glue_next = True
        else:
            out.append((w, hot))
    return out


def wrap_words(words, size, weight, max_w, mono=False):
    """Coupe une liste de (mot, accent) en lignes qui tiennent dans max_w pixels."""
    f = font(size, weight, mono)
    space = f.getlength(" ")
    lines, cur, cur_w = [], [], 0.0
    for w, hot in words:
        ww = f.getlength(w)
        if cur and cur_w + space + ww > max_w:
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur_w += (space if cur else 0) + ww
        cur.append((w, hot))
    if cur:
        lines.append(cur)
    return lines


def wrap(s, size, weight=400, max_w=CONTENT_W):
    return [" ".join(w for w, _ in line) for line in wrap_words(parse_rich(s), size, weight, max_w)]


@lru_cache(maxsize=2048)
def text_img(s, size, weight=400, color=None, mono=False):
    """Sprite d'une ligne de texte (hauteur fixe par taille : les lignes s'alignent)."""
    f = font(size, weight, mono)
    asc, desc = f.getmetrics()
    w = max(1, int(math.ceil(f.getlength(s))) + 4)
    img = Image.new("RGBA", (w, asc + desc + 4), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((2, 2), s, font=f, fill=color or T.text)
    return img


@lru_cache(maxsize=1024)
def rich_block(s, size, weight=700, max_w=CONTENT_W, color=None, hot=None, align="center",
               leading=1.18, max_lines=99):
    """Paragraphe : *mots* en couleur d'accent. Renvoie un sprite RGBA."""
    color, hot = color or T.text, hot or T.accent
    lines = wrap_words(parse_rich(s), size, weight, max_w)[:max_lines]
    f = font(size, weight)
    space = f.getlength(" ")
    lh = int(size * leading)
    asc, desc = f.getmetrics()
    widths = [sum(f.getlength(w) for w, _ in ln) + space * (len(ln) - 1) for ln in lines]
    bw = int(max(widths, default=1)) + 8
    img = Image.new("RGBA", (bw, lh * (len(lines) - 1) + asc + desc + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (ln, lw) in enumerate(zip(lines, widths)):
        x = {"center": (bw - lw) / 2, "left": 4, "right": bw - lw - 4}[align]
        for w, h in ln:
            d.text((x, 4 + i * lh), w, font=f, fill=hot if h else color)
            x += f.getlength(w) + space
    return img


# ------------------------------------------------------------ formes lisses
class Pen:
    """Dessin sur-échantillonné : coordonnées en pixels finaux, rendu réduit en LANCZOS."""

    def __init__(self, w, h, ss=SS):
        self.ss = ss
        self.img = Image.new("RGBA", (int(w * ss), int(h * ss)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def _xy(self, pts):
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def rrect(self, box, r, fill=None, outline=None, width=0):
        x0, y0, x1, y1 = (v * self.ss for v in box)
        self.d.rounded_rectangle([x0, y0, x1, y1], radius=r * self.ss, fill=fill, outline=outline,
                                 width=int(width * self.ss))

    def ellipse(self, box, fill=None, outline=None, width=0):
        self.d.ellipse([v * self.ss for v in box], fill=fill, outline=outline, width=int(width * self.ss))

    def circle(self, cx, cy, r, **kw):
        self.ellipse((cx - r, cy - r, cx + r, cy + r), **kw)

    def poly(self, pts, fill):
        self.d.polygon(self._xy(pts), fill=fill)

    def line(self, pts, fill, width, caps=True):
        w = width * self.ss
        self.d.line(self._xy(pts), fill=fill, width=int(w), joint="curve")
        if caps:
            for x, y in (pts[0], pts[-1]):
                self.d.ellipse([x * self.ss - w / 2, y * self.ss - w / 2, x * self.ss + w / 2, y * self.ss + w / 2],
                               fill=fill)

    def done(self):
        w, h = self.img.size
        return self.img.resize((w // self.ss, h // self.ss), Image.LANCZOS)


@lru_cache(maxsize=256)
def shadow_img(w, h, r, blur=26, alpha=None, dy=14):
    """Ombre douce d'une carte (w x h) : renvoie (sprite, marge)."""
    pad = blur * 2 + dy
    m = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    ImageDraw.Draw(m).rounded_rectangle([pad, pad + dy, pad + w, pad + h + dy], radius=r,
                                        fill=alpha if alpha is not None else T.shadow_a)
    m = m.filter(ImageFilter.GaussianBlur(blur))
    img = Image.new("RGBA", m.size, T.shadow + (0,))
    img.putalpha(m)
    return img, pad


@lru_cache(maxsize=256)
def card(w, h, r=40, fill=None, border=True, shadow=True):
    """Carte arrondie avec ombre portée. Renvoie (sprite, marge) : la carte commence à (marge, marge)."""
    fill = fill or T.card
    if shadow:
        sh, pad = shadow_img(w, h, r)
        img = sh.copy()
    else:
        pad = 0
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    p = Pen(w, h)
    p.rrect((0, 0, w, h), r, fill=fill + (255,))
    if border and T.name == "dark":
        p.rrect((0, 0, w, h), r, outline=T.line + (255,), width=2)
    img.alpha_composite(p.done(), (pad, pad))
    return img, pad


@lru_cache(maxsize=256)
def pill(label, size=30, weight=700, fg=None, bg=None, pad_x=22, pad_y=12):
    """Étiquette arrondie (« DÉFINITION », « 1983 »…)."""
    fg, bg = fg or T.on_accent, bg or T.accent
    t = text_img(label, size, weight, fg)
    f = font(size, weight)
    asc, desc = f.getmetrics()
    h = asc + desc + pad_y * 2 - 6
    w = t.width - 4 + pad_x * 2
    p = Pen(w, h)
    p.rrect((0, 0, w, h), h / 2, fill=bg + (255,))
    img = p.done()
    img.alpha_composite(t, (pad_x - 2, (h - t.height) // 2 + 1))
    return img


@lru_cache(maxsize=64)
def disc(d, fill, ring=None, ring_w=0):
    p = Pen(d, d)
    p.circle(d / 2, d / 2, d / 2 - 1, fill=fill + (255,))
    if ring:
        p.circle(d / 2, d / 2, d / 2 - 1 - ring_w / 2, outline=ring + (255,), width=ring_w)
    return p.done()


def arrow(L, x0, y0, x1, y1, col, width=8, head=26, alpha=1.0, progress=1.0):
    """Flèche lisse de (x0,y0) vers (x1,y1), dessinée sur `progress` de sa longueur."""
    if progress <= 0 or alpha <= 0:
        return
    xe, ye = x0 + (x1 - x0) * progress, y0 + (y1 - y0) * progress
    pad = head + width
    bx0, by0 = min(x0, xe) - pad, min(y0, ye) - pad
    p = Pen(abs(xe - x0) + pad * 2, abs(ye - y0) + pad * 2)
    a, b = (x0 - bx0, y0 - by0), (xe - bx0, ye - by0)
    ang = math.atan2(ye - y0, xe - x0)
    tip = b
    back = (b[0] - head * math.cos(ang), b[1] - head * math.sin(ang))
    c = col + (255,)
    p.line([a, back], c, width)
    left = (back[0] + head * 0.55 * math.sin(ang), back[1] - head * 0.55 * math.cos(ang))
    right = (back[0] - head * 0.55 * math.sin(ang), back[1] + head * 0.55 * math.cos(ang))
    p.poly([tip, left, right], c)
    blit(L, p.done(), bx0, by0, anchor="lt", alpha=alpha)


# ------------------------------------------------------------ collage avec opacité / échelle
_variants = OrderedDict()
CACHE_MAX_PX = 260_000        # au-delà, la variante est recalculée (sinon trop de mémoire)


def _variant(spr, alpha, scale, cache=True):
    qa = round(alpha * 24)
    key = (id(spr), qa, round(scale * 60))
    hit = _variants.get(key)
    if hit is not None and hit[0] is spr:
        _variants.move_to_end(key)
        return hit[1]
    out = spr
    if abs(scale - 1) > 1e-3:
        out = out.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.LANCZOS)
    if qa < 24:
        a = out.getchannel("A").point(lambda v, k=qa / 24: int(v * k))
        out = out.copy()
        out.putalpha(a)
    if cache and spr.width * spr.height <= CACHE_MAX_PX:
        _variants[key] = (spr, out)      # garde `spr` en vie : son id ne peut pas être réutilisé
        if len(_variants) > 300:
            _variants.popitem(last=False)
    return out


def blit(L, spr, x, y, anchor="mm", alpha=1.0, scale=1.0, cache=True):
    """Colle `spr` sur `L` (ancre : lt, mt, mm, mb, lm, rm), avec opacité et échelle.
    cache=False pour un sprite recréé à chaque image."""
    if alpha <= 0.01 or spr is None:
        return
    spr = _variant(spr, min(1.0, alpha), scale, cache)
    w, h = spr.size
    ax, ay = anchor[0], anchor[1]
    x = x - {"l": 0, "m": w / 2, "r": w}[ax]
    y = y - {"t": 0, "m": h / 2, "b": h}[ay]
    x, y = int(round(x)), int(round(y))
    sx, sy = max(0, -x), max(0, -y)
    if sx >= w or sy >= h or x >= L.width or y >= L.height:
        return
    if sx or sy:
        spr = spr.crop((sx, sy, w, h))
    L.alpha_composite(spr, (x + sx, y + sy))


# ------------------------------------------------------------ animation
def clamp(p):
    return max(0.0, min(1.0, p))


def ease_out(p):
    p = clamp(p)
    return 1 - (1 - p) ** 3


def ease_in_out(p):
    p = clamp(p)
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def back_out(p):
    """0 -> 1 avec un léger dépassement (apparition « pop »)."""
    p = clamp(p)
    c1 = 1.4
    return 1 + (c1 + 1) * (p - 1) ** 3 + c1 * (p - 1) ** 2


def appear(t, start, d=0.45):
    """Progression 0 -> 1 d'une apparition qui commence à `start` (secondes)."""
    return ease_out((t - start) / d)


def rise(L, spr, x, y, t, start, anchor="mm", d=0.45, dist=36):
    """Apparition standard : fondu + montée de `dist` px."""
    p = appear(t, start, d)
    if p > 0:
        blit(L, spr, x, y + (1 - p) * dist, anchor=anchor, alpha=p)
    return p


def pop(L, spr, x, y, t, start, anchor="mm", d=0.5):
    p = clamp((t - start) / d)
    if p > 0:
        blit(L, spr, x, y, anchor=anchor, alpha=min(1, p * 2.5), scale=0.6 + 0.4 * back_out(p))
    return p


# ------------------------------------------------------------ fond
_bg_cache = {}


def background():
    """Fond uni + grille de points discrète + halos de couleur d'accent (calculé une fois)."""
    if "bg" in _bg_cache:
        return _bg_cache["bg"]
    img = Image.new("RGBA", (W, H), T.bg + (255,))
    halo = Image.new("L", (W, H), 0)
    hd = ImageDraw.Draw(halo)
    hd.ellipse([W - 520, -380, W + 420, 520], fill=255)
    hd.ellipse([-480, H - 900, 420, H - 40], fill=200)
    halo = halo.filter(ImageFilter.GaussianBlur(160)).point(lambda v: int(v * (0.10 if T.name == "light" else 0.16)))
    col = Image.new("RGBA", (W, H), T.accent + (0,))
    col.putalpha(halo)
    img.alpha_composite(col)
    p = Pen(W, H, ss=2)
    step = 54
    for y in range(step // 2, H, step):
        for x in range(step // 2, W, step):
            p.circle(x, y, 2.2, fill=T.grid + (255,))
    img.alpha_composite(p.done())
    _bg_cache["bg"] = img
    return img
