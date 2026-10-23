"""Sprites 8 bits générés par code.

Chaque sprite est construit à petite échelle (1 px = 1 "gros pixel" final),
puis reçoit un contour noir automatique. Au premier lancement, chaque sprite
est aussi exporté en PNG dans assets/sprites/ : si tu redessines un PNG
(Aseprite, LibreSprite, Piskel…), c'est ta version qui sera utilisée.
"""
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw

# Palette PICO-8 (16 couleurs)
PAL = [
    (0, 0, 0), (29, 43, 83), (126, 37, 83), (0, 135, 81),
    (171, 82, 54), (95, 87, 79), (194, 195, 199), (255, 241, 232),
    (255, 0, 77), (255, 163, 0), (255, 236, 39), (0, 228, 54),
    (41, 173, 255), (131, 118, 156), (255, 119, 168), (255, 204, 170),
]
K, NAVY, PLUM, GREEN, BROWN, DGREY, LGREY, WHITE = range(8)
RED, ORANGE, YELLOW, LIME, BLUE, LAVENDER, PINK, PEACH = range(8, 16)

SPRITE_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites"


def c(i, a=255):
    r, g, b = PAL[i]
    return (r, g, b, a)


def new(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    return img, d


def outline(img, color=K):
    """Ajoute un contour 1 px autour des pixels opaques (style 8 bits)."""
    w, h = img.size
    out = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0))
    out.paste(img, (1, 1))
    src = out.load()
    res = out.copy()
    dst = res.load()
    for y in range(h + 2):
        for x in range(w + 2):
            if src[x, y][3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w + 2 and 0 <= ny < h + 2 and src[nx, ny][3] > 0:
                        dst[x, y] = c(color)
                        break
    return res


def _cached(name, builder):
    path = SPRITE_DIR / f"{name}.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    img = builder()
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img


# ---------------------------------------------------------------- roues
@lru_cache(maxsize=32)
def wheel(frame=0, size=13):
    img, d = new(size, size)
    m = size - 1
    k = size // 2
    d.ellipse([(0, 0), (m, m)], fill=c(K))
    d.ellipse([(1, 1), (m - 1, m - 1)], fill=c(DGREY))
    d.ellipse([(3, 3), (m - 3, m - 3)], fill=c(LGREY))
    d.ellipse([(k - 1, k - 1), (k + 1, k + 1)], fill=c(WHITE))
    # repère qui tourne
    spots = [(k, 2), (m - 2, k), (k, m - 2), (2, k)]
    d.point(spots[frame % 4], fill=c(K))
    return img


# ---------------------------------------------------------------- objets
def farmer(variant=0):
    def b():
        img, d = new(9, 18)
        hat = YELLOW if variant == 0 else BROWN
        d.rectangle([(0, 3), (8, 3)], fill=c(hat))
        d.rectangle([(2, 0), (6, 3)], fill=c(hat))
        d.rectangle([(2, 4), (6, 7)], fill=c(PEACH))
        d.point((3, 5), fill=c(K))
        d.point((5, 5), fill=c(K))
        shirt = BLUE if variant == 0 else RED
        d.rectangle([(1, 8), (7, 12)], fill=c(shirt))
        d.rectangle([(2, 13), (6, 15)], fill=c(NAVY))
        d.rectangle([(1, 16), (3, 17)], fill=c(BROWN))  # sabots
        d.rectangle([(5, 16), (7, 17)], fill=c(BROWN))
        return outline(img)
    return _cached(f"farmer_{variant}", b)


def sack():
    def b():
        img, d = new(16, 18)
        d.polygon([(4, 3), (11, 3), (15, 8), (15, 17), (0, 17), (0, 8)], fill=c(PEACH))
        d.rectangle([(5, 0), (10, 3)], fill=c(PEACH))
        d.line([(4, 3), (11, 3)], fill=c(BROWN))
        for (x, y) in ((4, 10), (9, 12), (11, 9), (6, 14)):
            d.ellipse([(x, y), (x + 3, y + 2)], fill=c(BROWN))
        return outline(img)
    return _cached("sack", b)


def speedo():
    def b():
        img, d = new(20, 12)
        d.pieslice([(0, 0), (19, 22)], 180, 360, fill=c(NAVY))
        d.pieslice([(2, 2), (17, 20)], 180, 360, fill=c(WHITE))
        for a in range(0, 6):
            x = 2 + a * 3
            d.point((x, 4 if a in (0, 5) else 2), fill=c(K))
        d.line([(10, 10), (15, 4)], fill=c(RED))
        return outline(img)
    return _cached("speedo", b)


def jerrycan():
    def b():
        img, d = new(13, 16)
        d.rectangle([(0, 3), (12, 15)], fill=c(RED))
        d.rectangle([(1, 0), (4, 3)], fill=c(DGREY))
        d.rectangle([(7, 1), (11, 2)], fill=c(RED))
        d.line([(1, 4), (11, 14)], fill=c(PLUM))
        d.line([(11, 4), (1, 14)], fill=c(PLUM))
        return outline(img)
    return _cached("jerrycan", b)


def heart():
    def b():
        img, d = new(7, 6)
        d.ellipse([(0, 0), (3, 3)], fill=c(PINK))
        d.ellipse([(3, 0), (6, 3)], fill=c(PINK))
        d.polygon([(0, 2), (6, 2), (3, 5)], fill=c(PINK))
        d.point((1, 1), fill=c(WHITE))
        return outline(img)
    return _cached("heart", b)


def person_head(color):
    img, d = new(10, 12)
    d.ellipse([(0, 0), (9, 9)], fill=c(color))
    d.rectangle([(1, 8), (8, 11)], fill=c(DGREY))
    return outline(img)


# ---------------------------------------------------------------- voiture décrite en JSON
_custom_cache = {}


def _col(spec, key, default):
    v = spec.get(key, default)
    return default if v is None else v


def build_custom_car(spec, lights_up=False):
    """Dessine une voiture à partir de sa description JSON (voir README, « Voiture »).

    spec : size [w,h], profile [[x,y]...], windows [[[x,y]...]...], wheels [x_ar, x_av],
           wheel_y, body/shade/light/glass (couleurs PICO-8), shapes [{type, pts, col}],
           popup {closed: [x0,y0,x1,y1], open: [x0,y0,x1,y1]}
    """
    import json as _json
    key = _json.dumps(spec, sort_keys=True) + str(lights_up)
    if key in _custom_cache:
        return _custom_cache[key]
    w, h = spec.get("size", [64, 22])
    img, d = new(w, h)
    body, shade = _col(spec, "body", RED), _col(spec, "shade", PLUM)
    light, glass = _col(spec, "light", PINK), _col(spec, "glass", BLUE)
    d.polygon([tuple(p) for p in spec["profile"]], fill=c(body))
    # ligne de bas de caisse + reflet haut
    bottom = max(p[1] for p in spec["profile"])
    d.line([(2, bottom - 1), (w - 3, bottom - 1)], fill=c(shade))
    for win in spec.get("windows", []):
        d.polygon([tuple(p) for p in win], fill=c(glass))
    r = spec.get("wheel_d", 13) // 2
    for wx in spec["wheels"]:      # passages de roue
        wy = spec.get("wheel_y", bottom)
        d.ellipse([(wx - r - 1, wy - r - 1), (wx + r + 1, wy + r + 1)], fill=(0, 0, 0, 0))
    for sh in spec.get("shapes", []):
        col = sh.get("col", "shade")
        col = {"body": body, "shade": shade, "light": light, "glass": glass}.get(col, col)
        pts = [tuple(p) for p in sh["pts"]]
        t = sh.get("type", "poly")
        if t == "poly":
            d.polygon(pts, fill=c(col))
        elif t == "rect":
            d.rectangle([pts[0], pts[1]], fill=c(col))
        elif t == "line":
            d.line(pts, fill=c(col))
        elif t == "point":
            for p in pts:
                d.point(p, fill=c(col))
    pop = spec.get("popup")
    if pop:
        box = pop["open"] if lights_up else pop["closed"]
        d.rectangle([tuple(box[:2]), tuple(box[2:])], fill=c(body))
        if lights_up:
            d.line([(box[2], box[1]), (box[2], box[3])], fill=c(YELLOW))
        else:
            d.line([(box[0], box[1]), (box[2], box[1])], fill=c(shade))
    img = outline(img)
    _custom_cache[key] = img
    return img


def custom_car_frame(t, spec, moving=True, lights_up=False, **colors):
    spec = dict(spec, **{k: v for k, v in colors.items() if v is not None})
    base = build_custom_car(spec, lights_up)
    w, h = base.size
    wy = spec.get("wheel_y", max(p[1] for p in spec["profile"])) + 1
    wd = spec.get("wheel_d", 13)
    img = Image.new("RGBA", (w, max(h, wy + wd // 2 + 1)), (0, 0, 0, 0))
    f = int(t * 12) % 4 if moving else 0
    for wx in spec["wheels"]:
        img.alpha_composite(wheel(f, wd), (wx + 1 - wd // 2, wy - wd // 2))
    img.alpha_composite(base, (0, 0))
    return img


# ---------------------------------------------------------------- icônes de fiche technique
def icon(name):
    builders = {
        "farmers": None, "sack": sack, "speed": speedo, "fuel": jerrycan,
        "weight": _icon_weight, "engine": _icon_engine, "rwd": _icon_rwd,
        "popup": _icon_popup, "trophy": _icon_trophy, "heart": heart,
        "calendar": _icon_calendar, "money": _icon_money,
        "fwd": _icon_fwd, "water": _icon_water, "people": _icon_people,
    }
    fn = builders.get(name)
    return fn() if fn else None


def _icon_weight():
    def b():
        img, d = new(18, 15)
        d.polygon([(4, 4), (13, 4), (17, 14), (0, 14)], fill=c(DGREY))
        d.ellipse([(6, 0), (11, 5)], outline=c(DGREY))
        d.line([(3, 12), (14, 12)], fill=c(LGREY))
        return outline(img)
    return _cached("icon_weight", b)


def _icon_engine():
    def b():
        img, d = new(20, 15)
        d.rectangle([(2, 5), (17, 14)], fill=c(DGREY))
        for x in (3, 7, 11, 15):
            d.rectangle([(x, 1), (x + 2, 5)], fill=c(LGREY))
        d.rectangle([(0, 8), (2, 11)], fill=c(DGREY))
        d.rectangle([(17, 8), (19, 11)], fill=c(DGREY))
        d.line([(4, 9), (15, 9)], fill=c(RED))
        return outline(img)
    return _cached("icon_engine", b)


def _icon_rwd():
    def b():
        img, d = new(22, 14)
        d.ellipse([(0, 1), (12, 13)], fill=c(K))
        d.ellipse([(3, 4), (9, 10)], fill=c(LGREY))
        d.line([(13, 7), (21, 7)], fill=c(RED))
        d.polygon([(16, 3), (21, 7), (16, 11)], fill=c(RED))
        return outline(img)
    return _cached("icon_rwd", b)


def _icon_popup():
    def b():
        img, d = new(18, 16)
        d.rectangle([(2, 6), (15, 12)], fill=c(RED))
        d.rectangle([(4, 7), (13, 11)], fill=c(YELLOW))
        d.polygon([(9, 0), (14, 4), (4, 4)], fill=c(NAVY))
        d.line([(0, 15), (17, 15)], fill=c(DGREY))
        return outline(img)
    return _cached("icon_popup", b)


def _icon_trophy():
    def b():
        img, d = new(16, 17)
        d.pieslice([(2, -6), (13, 10)], 0, 180, fill=c(YELLOW))
        d.arc([(0, 1), (5, 7)], 90, 270, fill=c(YELLOW))
        d.arc([(10, 1), (15, 7)], 270, 90, fill=c(YELLOW))
        d.rectangle([(6, 10), (9, 13)], fill=c(ORANGE))
        d.rectangle([(3, 13), (12, 16)], fill=c(BROWN))
        d.point((5, 3), fill=c(WHITE))
        return outline(img)
    return _cached("icon_trophy", b)


def _icon_calendar():
    def b():
        img, d = new(15, 15)
        d.rectangle([(0, 2), (14, 14)], fill=c(WHITE))
        d.rectangle([(0, 2), (14, 5)], fill=c(RED))
        for y in (8, 11):
            for x in (2, 6, 10):
                d.point((x, y), fill=c(DGREY))
        return outline(img)
    return _cached("icon_calendar", b)


def _icon_money():
    def b():
        img, d = new(16, 16)
        d.ellipse([(0, 0), (15, 15)], fill=c(YELLOW))
        d.ellipse([(2, 2), (13, 13)], outline=c(ORANGE))
        d.line([(8, 4), (8, 11)], fill=c(ORANGE))
        d.line([(6, 5), (10, 5)], fill=c(ORANGE))
        d.line([(6, 10), (10, 10)], fill=c(ORANGE))
        return outline(img)
    return _cached("icon_money", b)


def person(variant=0):
    """Silhouette générique (journaliste, ingénieur…), volontairement non ressemblante."""
    def b():
        img, d = new(11, 22)
        hat = [BROWN, DGREY, NAVY][variant % 3]
        d.rectangle([(1, 3), (9, 3)], fill=c(hat))
        d.rectangle([(3, 0), (7, 3)], fill=c(hat))
        d.rectangle([(3, 4), (7, 8)], fill=c(PEACH))
        d.point((4, 6), fill=c(K))
        d.point((6, 6), fill=c(K))
        coat = [BLUE, LGREY, ORANGE][variant % 3]
        d.rectangle([(1, 9), (9, 16)], fill=c(coat))
        d.rectangle([(8, 11), (10, 14)], fill=c(WHITE))     # carnet
        d.rectangle([(2, 17), (4, 21)], fill=c(NAVY))
        d.rectangle([(6, 17), (8, 21)], fill=c(NAVY))
        return outline(img)
    return _cached(f"person_{variant}", b)


def _icon_fwd():
    def b():
        img, d = new(22, 14)
        d.line([(0, 7), (8, 7)], fill=c(RED))
        d.polygon([(4, 3), (9, 7), (4, 11)], fill=c(RED))
        d.ellipse([(10, 1), (21, 12)], fill=c(K))
        d.ellipse([(13, 4), (18, 9)], fill=c(LGREY))
        return outline(img)
    return _cached("icon_fwd", b)


def _icon_water():
    def b():
        img, d = new(13, 17)
        d.polygon([(6, 0), (12, 10), (0, 10)], fill=c(BLUE))
        d.ellipse([(0, 5), (12, 16)], fill=c(BLUE))
        d.line([(3, 9), (3, 12)], fill=c(WHITE))
        return outline(img)
    return _cached("icon_water", b)


def _icon_people():
    def b():
        img = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
        img.alpha_composite(farmer(0), (0, 0))
        img.alpha_composite(farmer(1), (9, 0))
        return img
    return _cached("icon_people", b)
