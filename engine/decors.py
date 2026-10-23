"""Banque de décors 8 bits dessinés par le code (225x200, palette PICO-8).

    python3 -m engine.decors          # (re)génère assets/bank/*.png + planche.png

Chaque décor fait 225 px de large (180 visibles + marge de panoramique) et
200 px de haut : le sol du jeu commence à y=196. Tu peux retoucher les PNG
dans Aseprite ; s'ils existent, ce sont eux qui sont utilisés.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

from .sprites import PAL, c, K, NAVY, PLUM, GREEN, BROWN, DGREY, LGREY, WHITE, \
    RED, ORANGE, YELLOW, LIME, BLUE, LAVENDER, PINK, PEACH

W, H = 225, 200
HORIZON = 196
BANK = Path(__file__).resolve().parent.parent / "assets" / "bank"
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def canvas():
    img = Image.new("RGBA", (W, H), c(K))
    return img, ImageDraw.Draw(img)


def gradient(img, bands, y0=0, y1=H):
    """Dégradé en bandes avec tramage ordonné (le grand classique 8 bits)."""
    px = img.load()
    n = len(bands) - 1
    for y in range(y0, y1):
        pos = (y - y0) / max(1, y1 - y0) * n
        i = min(int(pos), n - 1)
        frac = pos - i
        for x in range(W):
            col = bands[i + 1] if frac * 16 > BAYER[y % 4][x % 4] else bands[i]
            px[x, y] = PAL[col] + (255,)


def ridge(d, base, amp, col, freq=0.04, seed=0, octave=2.3, top=None):
    """Ligne de collines / montagnes remplie jusqu'en bas."""
    ph = seed * 1.7
    pts = []
    for x in range(W + 1):
        y = base + amp * math.sin(x * freq + ph) + amp * 0.45 * math.sin(x * freq * octave + ph * 2)
        pts.append((x, int(y)))
    d.polygon(pts + [(W, H), (0, H)], fill=c(col))
    if top is not None:
        for x, y in pts:
            d.point((x, y), fill=c(top))
    return pts


def cloud(d, x, y, s, col=WHITE, shade=LGREY):
    d.ellipse([(x, y), (x + s * 2, y + s * 0.7)], fill=c(col))
    d.ellipse([(x + s * 0.5, y - s * 0.45), (x + s * 1.4, y + s * 0.5)], fill=c(col))
    d.line([(x + 2, y + int(s * 0.7)), (x + s * 2 - 2, y + int(s * 0.7))], fill=c(shade))


def stars(img, rnd, n, y_max, cols=(WHITE, YELLOW, LGREY)):
    px = img.load()
    for i in range(n):
        x, y = rnd.randint(0, W - 1), rnd.randint(0, y_max)
        px[x, y] = PAL[cols[i % len(cols)]] + (255,)


def tree_round(d, x, base, h, col=GREEN, hi=LIME):
    d.rectangle([(x - 1, base - h // 2), (x + 1, base)], fill=c(BROWN))
    d.ellipse([(x - h // 2, base - h), (x + h // 2, base - h // 3)], fill=c(col))
    d.ellipse([(x - h // 4, base - h + 2), (x, base - h + h // 3)], fill=c(hi))


def poplar(d, x, base, h, col=GREEN):
    d.line([(x, base - 3), (x, base)], fill=c(BROWN))
    d.ellipse([(x - 3, base - h), (x + 3, base - 2)], fill=c(col))
    d.line([(x - 1, base - h + 3), (x - 1, base - h // 2)], fill=c(LIME))


def pine(d, x, base, h, col=GREEN):
    d.polygon([(x, base - h), (x - h // 3, base), (x + h // 3, base)], fill=c(col))


def house(d, x, base, w, h, wall=PEACH, roof=RED, windows=True):
    d.rectangle([(x, base - h), (x + w, base)], fill=c(wall))
    d.polygon([(x - 2, base - h), (x + w // 2, base - h - w // 2), (x + w + 2, base - h)], fill=c(roof))
    if windows:
        for wx in range(x + 2, x + w - 2, 5):
            d.rectangle([(wx, base - h + 3), (wx + 2, base - h + 5)], fill=c(NAVY))
        d.rectangle([(x + w // 2 - 1, base - 5), (x + w // 2 + 1, base)], fill=c(BROWN))


# ------------------------------------------------------------ décors
def campagne():
    img, d = canvas()
    gradient(img, [BLUE, BLUE, WHITE], 0, 170)
    rnd = random.Random(1)
    for _ in range(5):
        cloud(d, rnd.randint(-10, 210), rnd.randint(40, 110), rnd.randint(7, 13))
    ridge(d, 150, 6, LAVENDER, 0.03, seed=1)
    ridge(d, 162, 7, GREEN, 0.045, seed=2, top=LIME)
    for x in range(0, W, 9):                       # haies
        d.ellipse([(x, 160 + int(4 * math.sin(x * 0.045 + 3.4))), (x + 6, 165 + int(4 * math.sin(x * 0.045 + 3.4)))], fill=c(GREEN))
    d.rectangle([(0, 176), (W, H)], fill=c(BROWN))  # champ labouré
    for y in range(178, H, 4):
        d.line([(0, y), (W, y)], fill=c(ORANGE))
    tree_round(d, 30, 176, 16)
    tree_round(d, 190, 176, 13)
    return img


def village():
    img, d = canvas()
    gradient(img, [BLUE, PEACH, PEACH], 0, 170)
    rnd = random.Random(2)
    for _ in range(3):
        cloud(d, rnd.randint(0, 200), rnd.randint(45, 90), rnd.randint(7, 11), WHITE, PEACH)
    ridge(d, 148, 5, LAVENDER, 0.03, seed=4)
    ridge(d, 160, 4, GREEN, 0.05, seed=5, top=LIME)
    # église
    d.rectangle([(96, 120), (110, 176)], fill=c(LGREY))
    d.polygon([(94, 120), (103, 100), (112, 120)], fill=c(DGREY))
    d.rectangle([(101, 126), (105, 132)], fill=c(NAVY))
    d.rectangle([(110, 146), (140, 176)], fill=c(LGREY))
    d.polygon([(108, 146), (125, 134), (142, 146)], fill=c(RED))
    d.point((103, 98), fill=c(YELLOW))
    for (x, w, h, roof) in ((20, 22, 18, RED), (48, 18, 22, ORANGE), (146, 24, 16, RED), (176, 20, 20, ORANGE), (70, 16, 14, RED)):
        house(d, x, 176, w, h, PEACH if x % 2 else LGREY, roof)
    for x in (8, 44, 140, 205, 218):
        poplar(d, x, 177, 30)
    d.rectangle([(0, 176), (W, H)], fill=c(GREEN))
    d.line([(0, 176), (W, 176)], fill=c(LIME))
    return img


def route():
    img, d = canvas()
    gradient(img, [BLUE, BLUE, WHITE], 0, 165)
    rnd = random.Random(3)
    for _ in range(5):
        cloud(d, rnd.randint(-10, 210), rnd.randint(40, 105), rnd.randint(7, 12))
    ridge(d, 145, 7, LAVENDER, 0.035, seed=6)
    ridge(d, 157, 5, GREEN, 0.05, seed=7, top=LIME)
    d.rectangle([(0, 165), (W, 180)], fill=c(YELLOW))      # blé
    for x in range(0, W, 3):
        d.point((x, 165 + (x % 2)), fill=c(ORANGE))
    d.rectangle([(0, 180), (W, H)], fill=c(GREEN))          # vignes
    for y in range(182, H, 4):
        for x in range(0, W, 4):
            d.point((x + (y // 4) % 2 * 2, y), fill=c(LIME))
    for x in range(6, W, 22):                               # platanes
        tree_round(d, x, 182, 22, GREEN, LIME)
    return img


def ville():
    img, d = canvas()
    gradient(img, [BLUE, PEACH], 0, 120)
    x = 0
    rnd = random.Random(4)
    while x < W:
        w = rnd.randint(38, 52)
        top = rnd.randint(68, 92)
        facade = rnd.choice([PEACH, LGREY, WHITE])
        d.rectangle([(x, top), (x + w, HORIZON)], fill=c(facade))
        d.polygon([(x, top), (x + 4, top - 10), (x + w - 4, top - 10), (x + w, top)], fill=c(LAVENDER))
        for cx in range(x + 8, x + w - 6, 12):              # cheminées / chiens-assis
            d.rectangle([(cx, top - 8), (cx + 3, top - 4)], fill=c(WHITE))
        for wy in range(top + 6, 170, 14):
            d.line([(x + 2, wy + 8), (x + w - 2, wy + 8)], fill=c(K))   # balcons
            for wx in range(x + 4, x + w - 5, 8):
                d.rectangle([(wx, wy), (wx + 4, wy + 7)], fill=c(NAVY))
                d.point((wx + 1, wy + 1), fill=c(BLUE))
        d.rectangle([(x, 172), (x + w, HORIZON)], fill=c(DGREY))       # boutiques
        for sx in range(x + 1, x + w - 1, 4):
            d.rectangle([(sx, 172), (sx + 1, 176)], fill=c(RED if (sx // 4) % 2 else WHITE))
        d.rectangle([(x + 4, 179), (x + w - 4, 193)], fill=c(YELLOW))
        d.line([(x, top), (x, HORIZON)], fill=c(DGREY))
        x += w
    for lx in (30, 120, 200):                               # réverbères
        d.line([(lx, 150), (lx, HORIZON)], fill=c(K))
        d.rectangle([(lx - 2, 147), (lx + 2, 151)], fill=c(YELLOW))
    return img


def usine():
    img, d = canvas()
    gradient(img, [NAVY, PLUM, PINK, ORANGE], 0, 175)
    d.ellipse([(140, 112), (186, 158)], fill=c(YELLOW))
    for y in (128, 136, 144):
        d.line([(140, y), (186, y)], fill=c(ORANGE))
    ridge(d, 160, 4, PLUM, 0.03, seed=8)
    x = -5
    rnd = random.Random(5)
    while x < W:
        w = rnd.randint(30, 50)
        base_top = rnd.randint(150, 165)
        d.rectangle([(x, base_top), (x + w, HORIZON)], fill=c(NAVY))
        for sx in range(x, x + w, 10):
            d.polygon([(sx, base_top), (sx + 10, base_top - 7), (sx + 10, base_top)], fill=c(NAVY))
        for wx in range(x + 3, x + w - 3, 6):
            if rnd.random() < 0.6:
                d.rectangle([(wx, base_top + 8), (wx + 2, base_top + 11)], fill=c(ORANGE))
        if rnd.random() < 0.7:
            cx = x + rnd.randint(4, w - 6)
            ch = rnd.randint(25, 45)
            d.rectangle([(cx, base_top - ch), (cx + 3, base_top)], fill=c(K))
            for i in range(4):
                d.ellipse([(cx - 2 + i * 4, base_top - ch - 6 - i * 5), (cx + 4 + i * 5, base_top - ch - i * 5)], fill=c(LAVENDER))
        x += w + rnd.randint(2, 8)
    return img


def salon():
    img, d = canvas()
    gradient(img, [K, PLUM, PLUM], 0, H)
    # verrière en arc
    cx, cy, r = W // 2, 150, 150
    d.pieslice([(cx - r, cy - r), (cx + r, cy + r)], 180, 360, fill=c(NAVY))
    for i in range(0, 13):
        a = math.pi + i * math.pi / 12
        d.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))], fill=c(LAVENDER))
    for rr in range(40, r, 22):
        d.arc([(cx - rr, cy - rr), (cx + rr, cy + rr)], 180, 360, fill=c(LAVENDER))
    gradient_px = img.load()
    for y in range(0, 150, 3):                     # lumière du jour à travers le verre
        for x in range((y // 3) % 2, W, 6):
            if gradient_px[x, y][:3] == PAL[NAVY]:
                gradient_px[x, y] = PAL[BLUE] + (255,)
    # galeries et pilliers
    d.rectangle([(0, 150), (W, 156)], fill=c(DGREY))
    for x in range(4, W, 20):
        d.rectangle([(x, 150), (x + 3, HORIZON)], fill=c(DGREY))
        d.rectangle([(x, 150), (x + 1, HORIZON)], fill=c(LGREY))
    # guirlande de fanions
    pts = [(x, 160 + int(6 * math.sin(x / 225 * math.pi * 3))) for x in range(0, W + 1, 9)]
    d.line(pts, fill=c(WHITE))
    for i, (x, y) in enumerate(pts[:-1]):
        d.polygon([(x, y), (x + 7, y), (x + 3, y + 6)], fill=c([RED, BLUE, YELLOW, WHITE][i % 4]))
    for bx in (16, 170):                            # bannières
        d.rectangle([(bx, 100), (bx + 34, 112)], fill=c(RED))
        d.rectangle([(bx + 2, 102), (bx + 32, 110)], fill=c(YELLOW))
    return img


def circuit():
    img, d = canvas()
    gradient(img, [BLUE, BLUE, WHITE], 0, 140)
    rnd = random.Random(6)
    for _ in range(3):
        cloud(d, rnd.randint(0, 200), rnd.randint(40, 80), rnd.randint(8, 12))
    for x in range(-4, W, 12):
        tree_round(d, x, 130, 18, GREEN, LIME)
    # tribune
    d.polygon([(10, 104), (150, 104), (156, 112), (4, 112)], fill=c(RED))
    d.rectangle([(8, 112), (152, 168)], fill=c(LGREY))
    px = img.load()
    for y in range(116, 164, 4):
        for x in range(10, 150, 2):
            px[x, y] = PAL[rnd.choice([PEACH, BROWN, RED, BLUE, YELLOW, WHITE])] + (255,)
    for x in range(12, 152, 20):
        d.line([(x, 112), (x, 168)], fill=c(DGREY))
    # stands
    d.rectangle([(160, 140), (W, 176)], fill=c(WHITE))
    for x in range(164, W, 10):
        d.rectangle([(x, 152), (x + 6, 176)], fill=c(DGREY))
    d.rectangle([(160, 136), (W, 140)], fill=c(BLUE))
    for fx in (170, 200):
        d.line([(fx, 112), (fx, 136)], fill=c(K))
        for j in range(4):
            for k in range(3):
                d.point((fx + 1 + j, 112 + k), fill=c(K if (j + k) % 2 else WHITE))
    d.rectangle([(0, 168), (W, 190)], fill=c(GREEN))
    for x in range(0, W, 8):                        # vibreur
        d.rectangle([(x, 190), (x + 3, HORIZON)], fill=c(RED))
        d.rectangle([(x + 4, 190), (x + 7, HORIZON)], fill=c(WHITE))
    return img


def nuit():
    img, d = canvas()
    gradient(img, [K, NAVY, NAVY], 0, 170)
    rnd = random.Random(7)
    stars(img, rnd, 70, 140)
    d.ellipse([(160, 30), (182, 52)], fill=c(WHITE))
    d.ellipse([(167, 27), (187, 47)], fill=c(NAVY))
    ridge(d, 150, 8, NAVY, 0.03, seed=9, top=LAVENDER)
    ridge(d, 166, 5, K, 0.05, seed=10)
    for x in range(0, W, 7):
        pine(d, x + rnd.randint(-2, 2), 176 + rnd.randint(0, 4), rnd.randint(16, 28), K)
    d.rectangle([(0, 178), (W, H)], fill=c(K))
    return img


def garage():
    img, d = canvas()
    d.rectangle([(0, 0), (W, H)], fill=c(BROWN))
    for x in range(0, W, 12):                        # planches
        d.line([(x, 0), (x, H)], fill=c(PLUM))
    d.rectangle([(0, 0), (W, 30)], fill=c(PLUM))
    # panneau à outils
    d.rectangle([(20, 70), (110, 130)], fill=c(PEACH))
    for y in range(74, 128, 6):
        for x in range(24, 108, 6):
            d.point((x, y), fill=c(BROWN))
    d.line([(32, 80), (32, 110)], fill=c(DGREY))                       # clés
    d.ellipse([(29, 76), (35, 82)], outline=c(DGREY))
    d.line([(46, 82), (46, 118)], fill=c(RED))                         # tournevis
    d.rectangle([(45, 80), (47, 92)], fill=c(RED))
    d.polygon([(60, 80), (78, 80), (78, 86), (70, 86), (70, 116), (66, 116), (66, 86), (60, 86)], fill=c(DGREY))  # marteau
    d.ellipse([(86, 86), (104, 104)], outline=c(K))                    # roue
    # étagère + bidons
    d.rectangle([(130, 96), (210, 99)], fill=c(DGREY))
    for i, col in enumerate((RED, BLUE, YELLOW, GREEN, RED)):
        x = 134 + i * 15
        d.rectangle([(x, 82), (x + 9, 96)], fill=c(col))
        d.rectangle([(x + 3, 79), (x + 6, 82)], fill=c(DGREY))
    # établi
    d.rectangle([(0, 160), (W, 166)], fill=c(ORANGE))
    d.rectangle([(0, 166), (W, HORIZON)], fill=c(PLUM))
    for x in (6, 100, 210):
        d.rectangle([(x, 166), (x + 4, HORIZON)], fill=c(BROWN))
    # lampes suspendues + halo tramé
    px = img.load()
    for lx in (60, 170):
        d.line([(lx, 0), (lx, 34)], fill=c(K))
        d.polygon([(lx - 7, 42), (lx + 7, 42), (lx + 3, 34), (lx - 3, 34)], fill=c(DGREY))
        d.rectangle([(lx - 2, 42), (lx + 2, 44)], fill=c(YELLOW))
        for y in range(45, 160):
            half = 4 + (y - 45) * 0.35
            for x in range(int(lx - half), int(lx + half)):
                if 0 <= x < W and (x + y) % 3 == 0:
                    px[x, y] = PAL[ORANGE if px[x, y][:3] == PAL[BROWN] else YELLOW] + (255,) \
                        if px[x, y][:3] in (PAL[BROWN], PAL[PLUM]) else px[x, y]
    return img


def montagne():
    img, d = canvas()
    gradient(img, [BLUE, BLUE, WHITE], 0, 150)
    rnd = random.Random(8)
    for _ in range(3):
        cloud(d, rnd.randint(0, 200), rnd.randint(36, 70), rnd.randint(7, 11))
    peaks = [(10, 70), (55, 50), (100, 78), (150, 44), (205, 66), (240, 80)]
    for (px_, py) in peaks:
        d.polygon([(px_ - 50, 160), (px_, py), (px_ + 50, 160)], fill=c(LAVENDER))
        d.polygon([(px_ - 12, py + 18), (px_, py), (px_ + 12, py + 18), (px_ + 4, py + 15), (px_, py + 20), (px_ - 5, py + 15)], fill=c(WHITE))
        d.line([(px_, py), (px_ + 50, 160)], fill=c(DGREY))
    ridge(d, 150, 6, GREEN, 0.05, seed=11)
    for x in range(0, W, 6):
        pine(d, x + rnd.randint(-2, 2), 168 + rnd.randint(-4, 6), rnd.randint(12, 20), GREEN)
    d.rectangle([(0, 172), (W, H)], fill=c(GREEN))
    road = [(x, 182 + int(6 * math.sin(x * 0.05))) for x in range(0, W + 1, 3)]
    d.line(road, fill=c(DGREY), width=5)
    d.line(road, fill=c(LGREY), width=1)
    return img


DECORS = {
    "campagne": campagne, "village": village, "route": route, "ville": ville,
    "usine": usine, "salon": salon, "circuit": circuit, "nuit": nuit,
    "garage": garage, "montagne": montagne,
}


def known(name):
    """Décor utilisable : dessiné par le code, ou PNG ajouté dans la banque (pas la planche d'aperçu)."""
    return name in DECORS or (name != "planche" and (BANK / f"{name}.png").exists())


def get(name):
    """Décor de la banque : le PNG (retouchable) s'il existe, sinon dessiné puis enregistré."""
    if not known(name):
        return None
    path = BANK / f"{name}.png"
    if path.exists():
        return Image.open(path).convert("RGBA")
    img = DECORS[name]()
    BANK.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return img


def build_all(force=True):
    BANK.mkdir(parents=True, exist_ok=True)
    ims = []
    for name, fn in DECORS.items():
        img = fn() if force else get(name)
        img.save(BANK / f"{name}.png")
        ims.append((name, img))
    cols = 5
    sheet = Image.new("RGB", (cols * (W + 4), 2 * (H + 14)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(ims):
        x, y = (i % cols) * (W + 4), (i // cols) * (H + 14)
        d.text((x + 2, y + 1), name, fill="black")
        sheet.paste(im.convert("RGB"), (x, y + 13))
    sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
    sheet.save(BANK / "planche.png")
    return BANK / "planche.png"


if __name__ == "__main__":
    print(build_all())
