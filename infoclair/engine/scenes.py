"""Scènes de vulgarisation. Chaque scène se règle dans le JSON de l'épisode (voir README) :

  title     accroche : grand titre, sous-titre, icône
  concept   une notion et sa définition, sur une carte
  analogy   « c'est comme… » : la notion technique et son équivalent de la vie courante
  flow      un schéma en étapes reliées par des flèches, un paquet circule
  list      2 à 5 points qui apparaissent quand la voix les cite
  code      un extrait de code tapé à l'écran (éditeur ou terminal)
  stat      un chiffre clé qui défile
  versus    deux choses comparées côte à côte
  fact      « le saviez-vous ? » : une phrase forte en grand
  outro     titre de l'épisode + appel à commenter / s'abonner

Signature : scene(L, t, dur, sc, ep) dessine la scène sur le calque transparent L
au temps local t (secondes) d'une scène de durée dur.
"""
import math
import re
from functools import lru_cache

from PIL import Image, ImageDraw

from . import gfx
from . import icons as I
from .gfx import CX, STAGE_BOT, STAGE_CY, STAGE_TOP, T, appear, blit, pop, rich_block, rise, text_img

STAGE_H = STAGE_BOT - STAGE_TOP - 20


# ------------------------------------------------------------ outils
def cue_time(sc, dur, words, fallback):
    """Instant où l'un des `words` est prononcé (via les sous-titres), sinon `fallback`."""
    words = [str(w).lower() for w in words if w]
    if not words:
        return fallback
    for a, _b, txt in sc.get("_subs", []):
        if any(w in txt for w in words):
            return a
    voice = sc.get("voice", "").lower()
    for w in words:
        pos = voice.find(w)
        if pos >= 0:
            return 0.25 + pos / max(1, len(voice)) * (dur - 0.7)
    return fallback


def cues(sc, dur, items, start=0.3, span=0.7, gap=0.45):
    """Instants d'apparition d'éléments : quand la voix prononce un de leurs mots `match`,
    sinon répartis sur `span` de la scène ; toujours croissants, espacés d'au moins `gap`."""
    n = max(1, len(items))
    out = []
    for i, it in enumerate(items):
        fallback = max(start, dur * (0.08 + span * i / n))
        tt = cue_time(sc, dur, it.get("match") or [], fallback)
        out.append(max(tt, out[-1] + gap) if out else tt)
    return out


def stack(L, parts, t, cy=STAGE_CY, gap=32):
    """Empile verticalement des éléments centrés : parts = [(sprite, start, mode)].
    mode : "rise" (fondu + montée) ou "pop" (petit rebond)."""
    parts = [p for p in parts if p[0] is not None]
    total = sum(p[0].height for p in parts) + gap * (len(parts) - 1)
    y = cy - total / 2
    for spr, start, mode, *extra in parts:
        dy = extra[0] if extra else 0
        if mode == "pop":
            pop(L, spr, CX, y + spr.height / 2 + dy, t, start)
        else:
            rise(L, spr, CX, y + spr.height / 2 + dy, t, start)
        y += spr.height + gap


@lru_cache(maxsize=256)
def rich_lines(s, size, weight=800, max_w=gfx.CONTENT_W, leading=1.12):
    """Une image par ligne (pour faire apparaître un paragraphe ligne à ligne)."""
    lines = gfx.wrap_words(gfx.parse_rich(s), size, weight, max_w)
    out = []
    for ln in lines:
        txt = " ".join(("*" + w + "*") if h else w for w, h in ln)
        out.append(rich_block(txt, size, weight, max_w + 40, leading=leading))
    return out


def lines_block(L, lines, t, start, cy, step=0.12, size=80, leading=1.12):
    lh = int(size * leading)
    y0 = cy - lh * len(lines) / 2
    for i, spr in enumerate(lines):
        rise(L, spr, CX, y0 + i * lh + lh / 2, t, start + i * step)
    return lh * len(lines)


def place_card(L, w, h, x, y, t, start, fill=None):
    """Pose une carte (avec ombre) qui apparaît en fondu ; (x, y) = centre de la carte."""
    spr, _pad = gfx.card(int(w), int(h), fill=fill)
    return rise(L, spr, x, y, t, start)


def float_y(t, amp=8, speed=1.8):
    return amp * math.sin(t * speed)


# ------------------------------------------------------------ title (accroche)
def scene_title(L, t, dur, sc, ep):
    badge = I.badge(sc["icon"], 240) if sc.get("icon") else None
    kicker = gfx.pill(sc["kicker"].upper(), 30, 700) if sc.get("kicker") else None
    title = rich_lines(sc.get("title", ep.get("title", "")), 100, 800, 860, 1.06)
    sub = rich_block(sc["subtitle"], 44, 500, 820, color=T.muted, leading=1.3) if sc.get("subtitle") else None
    lh = int(100 * 1.06)
    parts_h = [(badge.height + 56) if badge else 0, (kicker.height + 30) if kicker else 0,
               lh * len(title), (sub.height + 30) if sub else 0]
    y = STAGE_CY - sum(parts_h) / 2
    if badge:
        pop(L, badge, CX, y + badge.height / 2 + float_y(t), t, 0.15)
        y += badge.height + 56
    if kicker:
        rise(L, kicker, CX, y + kicker.height / 2, t, 0.35)
        y += kicker.height + 30
    for i, spr in enumerate(title):
        rise(L, spr, CX, y + lh / 2, t, 0.5 + i * 0.12)
        y += lh
    if sub:
        rise(L, sub, CX, y + 30 + sub.height / 2, t, 0.6 + 0.12 * len(title))


# ------------------------------------------------------------ concept (définition)
def scene_concept(L, t, dur, sc, ep):
    cw, pad = 840, 64
    badge = I.badge(sc.get("icon", "info"), 170)
    tag = gfx.pill(sc.get("tag", "Définition").upper(), 28, 700, fg=T.accent, bg=gfx.tint(T.accent, 0.14))
    term = rich_block(sc.get("term", ""), 84, 800, cw - pad * 2, leading=1.08)
    defi = rich_block(sc.get("definition", ""), 46, 450, cw - pad * 2, color=T.muted, leading=1.38)
    gaps = (40, 22, 30)
    h = pad + badge.height + gaps[0] + tag.height + gaps[1] + term.height + gaps[2] + defi.height + pad
    top = STAGE_CY - h / 2
    place_card(L, cw, h, CX, STAGE_CY, t, 0.1)
    y = top + pad
    pop(L, badge, CX, y + badge.height / 2, t, 0.3)
    y += badge.height + gaps[0]
    rise(L, tag, CX, y + tag.height / 2, t, 0.45)
    y += tag.height + gaps[1]
    rise(L, term, CX, y + term.height / 2, t, 0.55)
    y += term.height + gaps[2]
    start = cue_time(sc, dur, sc.get("match", []), 0.85)
    rise(L, defi, CX, y + defi.height / 2, t, max(0.75, start))


# ------------------------------------------------------------ analogy (c'est comme…)
def _side_card(L, item, color, x, y, w, h, t, start):
    """Carte horizontale : pastille d'icône à gauche, libellé + précision à droite."""
    place_card(L, w, h, x, y, t, start)
    p = appear(t, start, 0.45)
    if p <= 0:
        return
    dy = (1 - p) * 36
    d = 160
    left = x - w / 2 + 50
    blit(L, I.badge(item.get("icon", "question"), d, color), left + d / 2, y + dy, alpha=p)
    tx = left + d + 40
    max_w = int(x + w / 2 - 44 - tx)
    lab = rich_block(item.get("label", ""), 56, 800, max_w, align="left", leading=1.1, hot=color)
    sub = rich_block(item["sub"], 36, 450, max_w, color=T.muted, align="left", leading=1.3) if item.get("sub") else None
    th = lab.height + (sub.height + 8 if sub else 0)
    ty = y - th / 2 + dy
    blit(L, lab, tx - 4, ty, anchor="lt", alpha=p)
    if sub:
        blit(L, sub, tx - 4, ty + lab.height + 8, anchor="lt", alpha=p)


def scene_analogy(L, t, dur, sc, ep):
    a, b = sc.get("left", {}), sc.get("right", {})
    cw, ch, gap = 840, 250, 120
    title = rich_block(sc["title"], 54, 800, 840) if sc.get("title") else None
    total = ch * 2 + gap + ((title.height + 60) if title else 0)
    y = STAGE_CY - total / 2
    if title:
        rise(L, title, CX, y + title.height / 2, t, 0.05)
        y += title.height + 60
    ya, yb = y + ch / 2, y + ch + gap + ch / 2
    tb = max(1.0, cue_time(sc, dur, b.get("match") or [b.get("label", "")], dur * 0.42))
    _side_card(L, a, T.accent, CX, ya, cw, ch, t, 0.15)
    _side_card(L, b, T.accent2, CX, yb, cw, ch, t, tb)
    sign = _equal_disc(sc.get("sign", "≈"))
    pop(L, sign, CX, (ya + yb) / 2, t, tb - 0.3)


@lru_cache(maxsize=8)
def _equal_disc(sign):
    img = gfx.disc(104, T.text).copy()
    txt = text_img(sign, 58, 800, T.bg)
    img.alpha_composite(txt, ((104 - txt.width) // 2, (104 - txt.height) // 2 - 2))
    return img


# ------------------------------------------------------------ flow (schéma en étapes)
def scene_flow(L, t, dur, sc, ep):
    nodes = sc.get("nodes", [])[:4]
    if not nodes:
        return
    times = cues(sc, dur, nodes, gap=0.6)
    times[0] = min(times[0], 0.3)
    title = rich_block(sc["title"], 54, 800, 840) if sc.get("title") else None
    row = sc.get("layout") == "row" and len(nodes) <= 3
    if row:
        _flow_row(L, t, dur, sc, nodes, times, title)
    else:
        _flow_column(L, t, dur, sc, nodes, times, title)


def _packet(L, t, segs, t_ready, back=False):
    """Petit point qui circule le long des flèches une fois le schéma complet."""
    if t < t_ready or not segs:
        return
    per = 0.7
    path = list(segs) + ([(b, a, True) for a, b, _ in reversed(segs)] if back else [])
    k = ((t - t_ready) / per)
    i = int(k) % len(path)
    f = gfx.ease_in_out(k - int(k))
    (x0, y0), (x1, y1), ret = path[i]
    x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
    col = T.accent2 if ret else T.accent
    blit(L, gfx.disc(34, col, ring=T.card, ring_w=6), x, y, alpha=min(1, (t - t_ready) / 0.3))


def _flow_column(L, t, dur, sc, nodes, times, title):
    n = len(nodes)
    cw, ch, gap, tgap = 780, 150, 92, 64
    total = n * ch + (n - 1) * gap + ((title.height + tgap) if title else 0)
    if total > STAGE_H:                  # 4 étapes + titre : on resserre les flèches
        tgap = 44
        gap = max(56, (STAGE_H - n * ch - ((title.height + tgap) if title else 0)) / (n - 1))
        total = n * ch + (n - 1) * gap + ((title.height + tgap) if title else 0)
    y = STAGE_CY - total / 2
    if title:
        rise(L, title, CX, y + title.height / 2, t, 0.05)
        y += title.height + tgap
    centers = [y + ch / 2 + i * (ch + gap) for i in range(n)]
    segs = []
    for i, (nd, cy, st) in enumerate(zip(nodes, centers, times)):
        if i:
            y0, y1 = centers[i - 1] + ch / 2 + 14, cy - ch / 2 - 14
            prog = gfx.ease_out((t - (st - 0.5)) / 0.45)
            gfx.arrow(L, CX, y0, CX, y1, T.accent, width=7, head=24, progress=prog)
            segs.append(((CX, y0), (CX, y1 - 18), False))
        color = T.accent2 if nd.get("alt") else T.accent
        place_card(L, cw, ch, CX, cy, t, st)
        p = appear(t, st, 0.45)
        if p <= 0:
            continue
        dy = (1 - p) * 36
        left = CX - cw / 2 + 32
        d = 104
        blit(L, I.badge(nd.get("icon", "question"), d, color), left + d / 2, cy + dy, alpha=p)
        tx = left + d + 34
        max_w = int(CX + cw / 2 - 40 - tx)
        lab = rich_block(nd.get("label", ""), 48, 750, max_w, align="left", leading=1.1)
        sub = rich_block(nd["sub"], 34, 450, max_w, color=T.muted, align="left") if nd.get("sub") else None
        th = lab.height + (sub.height + 2 if sub else 0)
        blit(L, lab, tx - 4, cy - th / 2 + dy, anchor="lt", alpha=p)
        if sub:
            blit(L, sub, tx - 4, cy - th / 2 + lab.height + 2 + dy, anchor="lt", alpha=p)
        step = nd.get("step")
        if step is not None:
            num = gfx.pill(str(step), 26, 700)
            blit(L, num, CX + cw / 2 - 30, cy - ch / 2 + 4 + dy, anchor="rm", alpha=p)
    _packet(L, t, segs, times[-1] + 0.6, back=sc.get("back", False))


def _flow_row(L, t, dur, sc, nodes, times, title):
    n = len(nodes)
    d = 190
    xs = [CX + (i - (n - 1) / 2) * (300 if n == 3 else 420) for i in range(n)]
    labels = [rich_block(nd.get("label", ""), 44, 750, 280, leading=1.1) for nd in nodes]
    subs = [rich_block(nd["sub"], 32, 450, 280, color=T.muted) if nd.get("sub") else None for nd in nodes]
    lab_h = max(lb.height + (sb.height + 4 if sb else 0) for lb, sb in zip(labels, subs))
    total = d + 30 + lab_h + ((title.height + 80) if title else 0)
    y = STAGE_CY - total / 2
    if title:
        rise(L, title, CX, y + title.height / 2, t, 0.05)
        y += title.height + 80
    by = y + d / 2
    segs = []
    for i, (nd, x, st) in enumerate(zip(nodes, xs, times)):
        if i:
            x0, x1 = xs[i - 1] + d / 2 + 18, x - d / 2 - 18
            prog = gfx.ease_out((t - (st - 0.5)) / 0.45)
            gfx.arrow(L, x0, by, x1, by, T.accent, width=7, head=22, progress=prog)
            segs.append(((x0, by), (x1 - 14, by), False))
        color = T.accent2 if nd.get("alt") else T.accent
        badge = I.badge(nd.get("icon", "question"), d, color, fill=T.card)
        sh, pad = gfx.shadow_img(d, d, d // 2, blur=20, dy=10)
        p = appear(t, st, 0.45)
        if p > 0:
            blit(L, sh, x, by + (1 - p) * 36 + 0, alpha=p)
            pop(L, badge, x, by, t, st)
            yy = by + d / 2 + 30 + (1 - p) * 36
            blit(L, labels[i], x, yy, anchor="mt", alpha=p)
            if subs[i]:
                blit(L, subs[i], x, yy + labels[i].height + 4, anchor="mt", alpha=p)
    _packet(L, t, segs, times[-1] + 0.6, back=sc.get("back", False))


# ------------------------------------------------------------ list (points clés)
@lru_cache(maxsize=64)
def _marker(style, i, icon_name, color):
    if style == "icon" and icon_name:
        return I.badge(icon_name, 92, color)
    if style in ("check", "cross"):
        col = (22, 163, 74) if style == "check" else (220, 38, 38)
        img = gfx.disc(76, gfx.tint(col, 0.16)).copy()
        ic = I.icon("check" if style == "check" else "cross", 44, col)
        img.alpha_composite(ic, (16, 16))
        return img
    img = gfx.disc(76, color).copy()
    num = text_img(str(i + 1), 38, 800, T.on_accent)
    img.alpha_composite(num, ((76 - num.width) // 2, (76 - num.height) // 2 - 1))
    return img


def scene_list(L, t, dur, sc, ep):
    items = sc.get("items", [])[:5]
    title = rich_block(sc["title"], 60, 800, 840) if sc.get("title") else None
    cw = 840
    default = sc.get("style") or ("icon" if any(it.get("icon") for it in items) else "number")
    for size, min_h, gap, pad in ((44, 132, 26, 56), (40, 116, 18, 44), (36, 104, 14, 36)):   # du plus aéré au plus serré
        texts = [rich_block(it.get("text", it.get("label", "")), size, 650, cw - 40 - 92 - 34 - 44, align="left",
                            leading=1.22) for it in items]
        heights = [max(min_h, tx.height + pad) for tx in texts]
        total = sum(heights) + gap * (len(items) - 1) + ((title.height + 56) if title else 0)
        if total <= STAGE_H:
            break
    y = STAGE_CY - total / 2
    if title:
        rise(L, title, CX, y + title.height / 2, t, 0.05)
        y += title.height + 56
    times = cues(sc, dur, items, gap=0.4)
    for i, (it, tx, h, st) in enumerate(zip(items, texts, heights, times)):
        cy = y + h / 2
        place_card(L, cw, h, CX, cy, t, st)
        p = appear(t, st, 0.45)
        if p > 0:
            dy = (1 - p) * 36
            style = it.get("style", default)
            mk = _marker(style, i, it.get("icon"), T.accent2 if it.get("alt") else T.accent)
            left = CX - cw / 2 + 40
            blit(L, mk, left + 46, cy + dy, alpha=p)
            blit(L, tx, left + 92 + 30, cy + dy, anchor="lm", alpha=p)
        y += h + gap


# ------------------------------------------------------------ code (éditeur / terminal)
KEYWORDS = set("""
def return if else elif for while in not and or import from as class try except finally with lambda yield pass break
continue global async await function const let var new this typeof instanceof switch case default do throw catch
public private protected static void int float double bool boolean char string str long struct enum interface
package func go defer fn mut impl use pub match echo then fi done select from where insert into values update set
delete create table drop join on group by order limit and or not null is true false True False None nil null
undefined print
""".split())
KEYWORDS_UPPER = {k.upper() for k in ("select", "from", "where", "insert", "into", "values", "update", "set", "delete",
                                      "create", "table", "join", "on", "group", "by", "order", "limit", "and", "or",
                                      "not", "null", "as")}
CODE_COLORS = {
    "text": (222, 226, 234), "kw": (199, 146, 255), "str": (152, 214, 135), "num": (247, 178, 103),
    "com": (112, 122, 140), "fn": (110, 182, 255), "punct": (160, 170, 186), "gutter": (82, 90, 106),
    "prompt": (90, 220, 130), "out": (170, 180, 196),
}
TOKEN = re.compile(r"(?P<com>#.*|//.*|--.*)|(?P<str>\"[^\"]*\"?|'[^']*'?|`[^`]*`?)|(?P<num>\b\d+(?:\.\d+)?\b)"
                   r"|(?P<word>[A-Za-z_][A-Za-z0-9_]*)|(?P<sp>\s+)|(?P<punct>.)")


def tokenize(line):
    out = []
    for m in TOKEN.finditer(line):
        kind = m.lastgroup
        s = m.group()
        if kind == "word":
            rest = line[m.end():]
            if s in KEYWORDS or s in KEYWORDS_UPPER:
                kind = "kw"
            elif rest.startswith("("):
                kind = "fn"
            else:
                kind = "text"
        elif kind == "sp":
            kind = "text"
        out.append((s, CODE_COLORS[kind]))
    return out


@lru_cache(maxsize=16)
def _window(w, h, title, terminal):
    bg = T.term_bg if terminal else T.code_bg
    spr, pad = gfx.card(w, h, r=30, fill=bg, border=False)
    spr = spr.copy()
    p = gfx.Pen(w, 72)
    p.rrect((0, 0, w, 72 + 30), 30, fill=T.code_bar + (255,))
    for i, col in enumerate(((255, 95, 87), (254, 188, 46), (40, 200, 64))):
        p.circle(40 + i * 34, 36, 10, fill=col + (255,))
    bar = p.done()
    spr.alpha_composite(bar.crop((0, 0, w, 72)), (pad, pad))
    if title:
        tt = text_img(title, 28, 500, (150, 160, 178), mono=True)
        spr.alpha_composite(tt, (pad + (w - tt.width) // 2, pad + (72 - tt.height) // 2))
    return spr, pad


def scene_code(L, t, dur, sc, ep):
    terminal = sc.get("style") == "terminal"
    code = sc.get("code", "")
    lines = code.split("\n") if isinstance(code, str) else list(code)
    lines = lines[:14]
    w = 860
    maxlen = max((len(l) for l in lines), default=10)
    gutter_chars = 0 if terminal else len(str(len(lines)))
    avail = w - 80 - (gutter_chars * 0.6 + 1.4) * 38 * (0 if terminal else 1)
    size = int(max(24, min(40, avail / (0.6 * max(maxlen, 1)))))
    f = gfx.font(size, 400, mono=True)
    cwid = f.getlength("M")
    lh = int(size * 1.6)
    gut = 0 if terminal else int((gutter_chars + 1.6) * cwid)
    h = 72 + 44 * 2 + lh * len(lines)
    title = rich_block(sc["title"], 52, 800, 840) if sc.get("title") else None
    total = h + ((title.height + 48) if title else 0)
    top = STAGE_CY - total / 2
    if title:
        rise(L, title, CX, top + title.height / 2, t, 0.05)
        top += title.height + 48
    win, pad = _window(w, h, sc.get("file", "Terminal" if terminal else ""), terminal)
    p = appear(t, 0.15, 0.45)
    if p <= 0:
        return
    dy = (1 - p) * 36
    layer = win.copy()
    d = ImageDraw.Draw(layer)
    ox, oy = pad + 40, pad + 72 + 44

    # frappe : caractères révélés progressivement (les sorties du terminal s'affichent d'un coup)
    typed = [not (terminal and not l.startswith("$")) for l in lines]
    n_chars = sum(len(l) for l, ty in zip(lines, typed) if ty)
    t0 = 0.6
    span = min(dur * 0.6, max(0.8, n_chars * 0.045)) if sc.get("typing", True) else 0.001
    budget = max(0.0, (t - t0) / span) * n_chars if span else n_chars
    cursor = None
    hl = set(sc.get("highlight", []))
    done = budget >= n_chars
    if done and hl:                    # lignes mises en avant une fois le code tapé
        k = appear(t, t0 + span + 0.2, 0.4)
        band = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(band)
        for i in hl:
            if 1 <= i <= len(lines):
                yy = oy + (i - 1) * lh
                bd.rectangle([pad + 4, yy - 6, pad + w - 4, yy + lh - 10], fill=T.accent + (int(70 * k),))
                bd.rectangle([pad + 4, yy - 6, pad + 10, yy + lh - 10], fill=T.accent + (int(255 * k),))
        layer.alpha_composite(band)
    for i, line in enumerate(lines):
        y = oy + i * lh
        if not terminal:
            d.text((ox + gut - cwid * 1.2, y), str(i + 1), font=f, fill=CODE_COLORS["gutter"], anchor="ra")
        if typed[i]:
            if budget <= 0:
                cursor = cursor or (ox + gut, y)
                break
            shown = int(min(len(line), budget))
            budget -= len(line)
        else:
            shown = len(line)
        x = ox + gut
        if terminal and line.startswith("$"):
            d.text((x, y), "$", font=f, fill=CODE_COLORS["prompt"])
            x += cwid * 2
            body, rest = line[1:].lstrip(), max(0, shown - (len(line) - len(line[1:].lstrip())))
            d.text((x, y), body[:rest], font=f, fill=CODE_COLORS["text"])
            x += f.getlength(body[:rest])
        elif terminal:
            d.text((x, y), line, font=f, fill=CODE_COLORS["out"])
            x += f.getlength(line)
        else:
            left = shown
            for tok, col in tokenize(line):
                if left <= 0:
                    break
                part = tok[:left]
                d.text((x, y), part, font=f, fill=col)
                x += f.getlength(part)
                left -= len(part)
        if typed[i] and shown < len(line):
            cursor = (x, y)
            break
        if typed[i]:
            cursor = (x, y)
    if cursor and int(t * 2.2) % 2 == 0:
        cx, cy = cursor
        d.rectangle([cx + 2, cy + 2, cx + 2 + cwid * 0.55, cy + size * 1.2], fill=T.accent + (255,))
    blit(L, layer, CX, top + h / 2 + dy, alpha=p, cache=False)


# ------------------------------------------------------------ stat (chiffre clé)
def fmt_number(v, decimals):
    s = f"{v:,.{decimals}f}"
    return s.replace(",", " ").replace(".", ",")


def scene_stat(L, t, dur, sc, ep):
    raw = sc.get("value", 0)
    target = float(raw)
    decimals = len(str(raw).split(".")[1]) if isinstance(raw, float) or "." in str(raw) else 0
    k = gfx.ease_out((t - 0.35) / max(0.8, dur * 0.55))
    val = target * k
    s = f"{sc.get('prefix', '')}{fmt_number(val, decimals)}{sc.get('suffix', '')}"
    final = f"{sc.get('prefix', '')}{fmt_number(target, decimals)}{sc.get('suffix', '')}"
    size = 190
    while gfx.text_w(final, size, 800) > 860 and size > 80:
        size -= 6
    badge = I.badge(sc["icon"], 150) if sc.get("icon") else None
    label = rich_block(sc.get("label", ""), 54, 750, 820, leading=1.15) if sc.get("label") else None
    note = rich_block(sc["note"], 40, 450, 780, color=T.muted, leading=1.3) if sc.get("note") else None
    num_h = int(size * 1.15)
    parts = [(badge.height + 40) if badge else 0, num_h, (label.height + 20) if label else 0,
             (note.height + 26) if note else 0]
    y = STAGE_CY - sum(parts) / 2
    if badge:
        pop(L, badge, CX, y + badge.height / 2 + float_y(t, 6), t, 0.1)
        y += badge.height + 40
    p = appear(t, 0.25, 0.4)
    if p > 0:
        num = text_img.__wrapped__(s, size, 800, T.accent)      # change à chaque image : pas de cache
        blit(L, num, CX, y + num_h / 2 + (1 - p) * 30, alpha=p, cache=False)
    y += num_h
    if label:
        rise(L, label, CX, y + 20 + label.height / 2, t, 0.5)
        y += label.height + 20
    if note:
        rise(L, note, CX, y + 26 + note.height / 2, t, max(0.9, cue_time(sc, dur, sc.get("match", []), dur * 0.5)))


# ------------------------------------------------------------ versus (comparaison)
def _vs_content(item, color, w):
    pad = 36
    badge = I.badge(item.get("icon", "question"), 116, color)
    label = rich_block(item.get("label", ""), 46, 800, w - pad * 2, leading=1.1, hot=color)
    points = [rich_block(pt, 34, 500, w - pad * 2 - 30, align="left", leading=1.25) for pt in item.get("points", [])[:4]]
    h = pad + badge.height + 22 + label.height + 26 + sum(pt.height + 18 for pt in points) + pad - 10
    return badge, label, points, h


def scene_versus(L, t, dur, sc, ep):
    a, b = sc.get("left", {}), sc.get("right", {})
    w, gap = 405, 30
    title = rich_block(sc["title"], 54, 800, 840) if sc.get("title") else None
    ca, cb = _vs_content(a, T.accent, w), _vs_content(b, T.accent2, w)
    h = max(ca[3], cb[3])
    total = h + ((title.height + 60) if title else 0)
    top = STAGE_CY - total / 2
    if title:
        rise(L, title, CX, top + title.height / 2, t, 0.05)
        top += title.height + 60
    tb = max(1.0, cue_time(sc, dur, b.get("match") or [b.get("label", "")], dur * 0.4))
    for (badge, label, points, _), x, st, color in ((ca, CX - (w + gap) / 2, 0.15, T.accent),
                                                     (cb, CX + (w + gap) / 2, tb, T.accent2)):
        place_card(L, w, h, x, top + h / 2, t, st)
        p = appear(t, st, 0.45)
        if p <= 0:
            continue
        dy = (1 - p) * 36
        y = top + 36
        blit(L, badge, x, y + badge.height / 2 + dy, alpha=p)
        y += badge.height + 22
        blit(L, label, x, y + dy, anchor="mt", alpha=p)
        y += label.height + 26
        for i, pt in enumerate(points):
            q = appear(t, st + 0.45 + i * 0.35, 0.4)
            if q > 0:
                blit(L, gfx.disc(14, color), x - w / 2 + 36 + 7, y + 28 + (1 - q) * 20, alpha=q)
                blit(L, pt, x - w / 2 + 36 + 26, y + (1 - q) * 20, anchor="lt", alpha=q)
            y += pt.height + 18
    pop(L, _vs_disc(), CX, top + 36 + 58, t, tb - 0.2)


@lru_cache(maxsize=4)
def _vs_disc():
    img = gfx.disc(92, T.text, ring=T.bg, ring_w=8).copy()
    txt = text_img("VS", 32, 800, T.bg)
    img.alpha_composite(txt, ((92 - txt.width) // 2, (92 - txt.height) // 2))
    return img


# ------------------------------------------------------------ fact (le saviez-vous ?)
def scene_fact(L, t, dur, sc, ep):
    badge = I.badge(sc["icon"], 160) if sc.get("icon") else None
    kicker = gfx.pill(sc.get("kicker", "Le saviez-vous ?").upper(), 30, 700)
    size = 72 if len(sc.get("text", "")) < 90 else 60
    lines = rich_lines(sc.get("text", ""), size, 800, 860, 1.14)
    detail = rich_block(sc["detail"], 40, 450, 800, color=T.muted, leading=1.32) if sc.get("detail") else None
    lh = int(size * 1.14)
    parts = [(badge.height + 44) if badge else 0, kicker.height + 40, lh * len(lines), (detail.height + 36) if detail else 0]
    y = STAGE_CY - sum(parts) / 2
    if badge:
        pop(L, badge, CX, y + badge.height / 2 + float_y(t, 6), t, 0.1)
        y += badge.height + 44
    rise(L, kicker, CX, y + kicker.height / 2, t, 0.2)
    y += kicker.height + 40
    for i, spr in enumerate(lines):
        rise(L, spr, CX, y + lh / 2, t, 0.4 + i * 0.12)
        y += lh
    if detail:
        rise(L, detail, CX, y + 36 + detail.height / 2, t, max(0.9, cue_time(sc, dur, sc.get("match", []), dur * 0.5)))


# ------------------------------------------------------------ outro
def scene_outro(L, t, dur, sc, ep):
    badge = I.badge(ep.get("icon", "lightbulb"), 200)
    title = rich_block(ep.get("title", ""), 80, 800, 840, leading=1.08)
    sub = rich_block(ep["subtitle"], 40, 500, 800, color=T.muted) if ep.get("subtitle") else None
    cta_txt = sc.get("cta", "Quel sujet pour le prochain épisode ? Dis-le en commentaire !")
    cw = 840
    msg = I.badge("message", 96, T.accent)
    cta = rich_block(cta_txt, 42, 700, cw - 48 - 96 - 32 - 48, align="left", leading=1.25)
    ch = max(150, cta.height + 60)
    follow = gfx.pill(sc.get("follow", "+ Abonne-toi"), 34, 700, pad_x=34, pad_y=18)
    parts = [badge.height + 44, title.height, (sub.height + 16) if sub else 0, ch + 60, follow.height + 44]
    y = STAGE_CY - sum(parts) / 2
    pop(L, badge, CX, y + badge.height / 2 + float_y(t), t, 0.1)
    y += badge.height + 44
    rise(L, title, CX, y + title.height / 2, t, 0.3)
    y += title.height
    if sub:
        rise(L, sub, CX, y + 16 + sub.height / 2, t, 0.45)
        y += sub.height + 16
    y += 60
    cy = y + ch / 2
    place_card(L, cw, ch, CX, cy, t, 0.6)
    p = appear(t, 0.6, 0.45)
    if p > 0:
        dy = (1 - p) * 36
        left = CX - cw / 2 + 48
        blit(L, msg, left + 48, cy + dy, alpha=p)
        blit(L, cta, left + 96 + 28, cy + dy, anchor="lm", alpha=p)
    y += ch + 44
    q = appear(t, 0.9, 0.4)
    if q > 0:
        beat = 1 + 0.04 * max(0.0, math.sin((t - 0.9) * 4)) ** 8 * 3
        blit(L, follow, CX, y + follow.height / 2, alpha=q, scale=beat)


SCENES = {
    "title": scene_title, "concept": scene_concept, "analogy": scene_analogy, "flow": scene_flow,
    "list": scene_list, "code": scene_code, "stat": scene_stat, "versus": scene_versus, "fact": scene_fact,
    "outro": scene_outro,
}


# ------------------------------------------------------------ habillage : en-tête, progression, sous-titres
@lru_cache(maxsize=4)
def _brand(series):
    logo_d = 56
    p = gfx.Pen(logo_d, logo_d)
    p.rrect((0, 0, logo_d, logo_d), 16, fill=T.accent + (255,))
    logo = p.done()
    ic = I.icon("code", 34, T.on_accent)
    logo.alpha_composite(ic, ((logo_d - 34) // 2, (logo_d - 34) // 2))
    txt = text_img(series, 34, 750, T.text)
    img = Image.new("RGBA", (logo_d + 18 + txt.width, logo_d), (0, 0, 0, 0))
    img.alpha_composite(logo, (0, 0))
    img.alpha_composite(txt, (logo_d + 18, (logo_d - txt.height) // 2))
    return img


def header(L, ep, gt, starts, durs):
    """Logo + nom de la série, numéro d'épisode, barre de progression par scène."""
    if ep.get("series"):
        blit(L, _brand(ep["series"]), 60, 204, anchor="lm")
    if ep.get("number"):
        blit(L, text_img(f"#{ep['number']}", 32, 700, T.muted), 1020, 204, anchor="rm")
    n = len(starts)
    x0, x1, y, gap = 60, 1020, 262, 10
    seg = (x1 - x0 - gap * (n - 1)) / n
    d = ImageDraw.Draw(L)
    for i, (st, du) in enumerate(zip(starts, durs)):
        a = x0 + i * (seg + gap)
        d.rounded_rectangle([a, y, a + seg, y + 6], radius=3, fill=T.line + (255,))
        k = gfx.clamp((gt - st) / du)
        if k > 0:
            d.rounded_rectangle([a, y, a + max(6, seg * k), y + 6], radius=3, fill=T.accent + (255,))


CAP_SIZE, CAP_W, CAP_X, CAP_Y = 58, 800, 520, 1392


def caption_chunks(caption, max_lines=2):
    """Découpe la phrase en blocs de 1-2 lignes (sous-titres façon TikTok)."""
    words = [w for w, _ in gfx.parse_rich(caption)]
    fits = lambda ws: len(gfx.wrap_words([(w, False) for w in ws], CAP_SIZE, 800, CAP_W)) <= max_lines  # noqa: E731
    chunks, cur = [], []
    for w in words:
        if cur and (not fits(cur + [w]) or (cur[-1][-1] in ".?!:…" and len(" ".join(cur)) > 10)):
            chunks.append(cur)
            cur = [w]
        else:
            cur = cur + [w]
    if cur:
        chunks.append(cur)
    merged = []
    for ch in chunks:            # pas de bloc orphelin d'un seul petit mot
        if merged and len(" ".join(ch)) < 12 and fits(merged[-1] + ch):
            merged[-1] = merged[-1] + ch
        else:
            merged.append(ch)
    return merged


@lru_cache(maxsize=512)
def caption_img(words, hot):
    """Bloc de sous-titre ; le mot `hot` (index) est surligné en couleur d'accent."""
    lines = gfx.wrap_words([(w, False) for w in words], CAP_SIZE, 800, CAP_W)
    f = gfx.font(CAP_SIZE, 800)
    space = f.getlength(" ") + 6         # un peu d'air pour la pastille du mot prononcé
    lh = int(CAP_SIZE * 1.3)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (CAP_W + 60, lh * len(lines) + 30), (0, 0, 0, 0))
    pen = gfx.Pen(img.width, img.height, ss=2)
    k = 0
    pos = []
    for i, ln in enumerate(lines):
        lw = sum(f.getlength(w) for w, _ in ln) + space * (len(ln) - 1)
        x = (img.width - lw) / 2
        for w, _ in ln:
            ww = f.getlength(w)
            pos.append((x, 15 + i * lh, ww, w, k))
            if k == hot:
                pen.rrect((x - 8, 15 + i * lh - 4, x + ww + 8, 15 + i * lh + asc + desc - 2), 14,
                          fill=T.accent + (255,))
            x += ww + space
            k += 1
    img.alpha_composite(pen.done())
    d = ImageDraw.Draw(img)
    for x, y, _ww, w, kk in pos:
        d.text((x, y), w.replace(" ", " "), font=f, fill=T.on_accent if kk == hot else T.text)
    return img


def subtitles(L, chunk, hot, p=1.0):
    img = caption_img(tuple(chunk), hot)
    blit(L, img, CAP_X, CAP_Y + (1 - p) * 14, alpha=p)
