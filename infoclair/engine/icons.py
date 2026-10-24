"""Icônes au trait (style « line icons »), dessinées par le code sur une grille 24x24.

    icon("cloud", 160, (37, 99, 235))      -> sprite RGBA 160x160
    icon("text:IP", 160, couleur)          -> sigle dans l'icône (2-3 caractères)

Une icône à toi remplace celle du code : dépose assets/icons/<nom>.png
(carré, fond transparent, de préférence monochrome ; elle est recolorée).
`python3 -m engine.icons` exporte la planche de toutes les icônes (assets/icons_planche.png).
"""
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

from . import gfx

ICON_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
SSI = 4          # sur-échantillonnage des icônes
SW = 2.0         # épaisseur du trait, en unités de la grille 24


class Pen:
    """Trace en blanc sur un masque : la couleur est appliquée à la fin."""

    def __init__(self, size):
        self.k = size * SSI / 24
        self.m = Image.new("L", (size * SSI, size * SSI), 0)
        self.d = ImageDraw.Draw(self.m)
        self.w = SW * self.k

    def p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def _caps(self, pts, v=255):
        r = self.w / 2
        for x, y in self.p([pts[0], pts[-1]]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=v)

    def line(self, *pts):
        self.d.line(self.p(pts), fill=255, width=round(self.w), joint="curve")
        self._caps(pts)

    def closed(self, *pts):
        self.line(*pts, pts[0])

    def box(self, x0, y0, x1, y1, stroke=True):
        """Boîte en pixels. Pillow trace les contours vers l'intérieur : on l'élargit d'un
        demi-trait pour que le trait soit centré sur le tracé (comme pour les lignes)."""
        h = self.w / 2 if stroke else 0
        return [x0 * self.k - h, y0 * self.k - h, x1 * self.k + h, y1 * self.k + h]

    def rect(self, x0, y0, x1, y1, r=0.0, fill=False):
        if fill:
            self.d.rounded_rectangle(self.box(x0, y0, x1, y1, False), radius=r * self.k, fill=255)
        else:
            self.d.rounded_rectangle(self.box(x0, y0, x1, y1), radius=r * self.k + self.w / 2, outline=255,
                                     width=round(self.w))

    def circle(self, cx, cy, r, fill=False, v=255):
        if fill:
            self.d.ellipse(self.box(cx - r, cy - r, cx + r, cy + r, False), fill=v)
        else:
            self.d.ellipse(self.box(cx - r, cy - r, cx + r, cy + r), outline=v, width=round(self.w))

    def ellipse(self, x0, y0, x1, y1):
        self.d.ellipse(self.box(x0, y0, x1, y1), outline=255, width=round(self.w))

    def earc(self, x0, y0, x1, y1, a0, a1):
        """Arc d'ellipse inscrite dans la boîte (x0, y0, x1, y1), sans bouts arrondis."""
        self.d.arc(self.box(x0, y0, x1, y1), a0, a1, fill=255, width=round(self.w))

    def arc(self, cx, cy, r, a0, a1):
        """Arc de cercle, angles en degrés (0 = à droite, sens horaire, 270 = en haut)."""
        self.d.arc(self.box(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=255, width=round(self.w))
        ends = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (a0, a1)]
        self._caps(ends)

    def dot(self, cx, cy, r=1.3):
        self.circle(cx, cy, r, fill=True)

    def fill(self, *pts, v=255):
        self.d.polygon(self.p(pts), fill=v)

    def erase_circle(self, cx, cy, r):
        self.circle(cx, cy, r, fill=True, v=0)

    def glyph(self, s, cx, cy, h, weight=800, mono=False):
        """Texte centré dans l'icône (sigles, symboles)."""
        size = int(h * self.k)
        f = gfx.font(size, weight, mono)
        while f.getlength(s) > 19 * self.k and size > 8:
            size = int(size * 0.9)
            f = gfx.font(size, weight, mono)
        self.d.text((cx * self.k, cy * self.k), s, font=f, fill=255, anchor="mm")


def _ring(pen, outer, inner):
    """Contour d'une forme pleine : on peint `outer`, puis on efface `inner` (rétréci du trait)."""
    for kind, args in outer:
        getattr(pen, kind)(*args, **({"fill": True} if kind in ("circle", "rect") else {}))
    for kind, args in inner:
        if kind == "circle":
            pen.circle(*args, fill=True, v=0)
        elif kind == "fill":
            pen.fill(*args, v=0)
        elif kind == "rect":
            x0, y0, x1, y1, r = args
            pen.d.rounded_rectangle([x0 * pen.k, y0 * pen.k, x1 * pen.k, y1 * pen.k], radius=r * pen.k, fill=0)


# ------------------------------------------------------------ dessins (grille 24)
def i_laptop(p):
    p.rect(4, 5, 20, 15.5, 1.5)
    p.line((2, 19), (22, 19))


def i_monitor(p):
    p.rect(2.5, 3.5, 21.5, 16, 2)
    p.line((12, 16), (12, 20))
    p.line((8, 20.5), (16, 20.5))


def i_phone(p):
    p.rect(6.5, 2, 17.5, 22, 2.5)
    p.line((11, 18.5), (13, 18.5))


def i_server(p):
    p.rect(3, 3, 21, 10.5, 1.8)
    p.rect(3, 13.5, 21, 21, 1.8)
    p.dot(7, 6.75)
    p.dot(7, 17.25)
    p.line((12, 6.75), (17, 6.75))
    p.line((12, 17.25), (17, 17.25))


def i_cloud(p):
    w = SW
    _ring(p, [("circle", (8, 14.5, 4.5)), ("circle", (13, 11, 5.6)), ("circle", (17.5, 14.8, 4.2)),
              ("rect", (8, 13, 17.5, 19, 0))],
          [("circle", (8, 14.5, 4.5 - w)), ("circle", (13, 11, 5.6 - w)), ("circle", (17.5, 14.8, 4.2 - w)),
           ("rect", (8, 13, 17.5, 19 - w, 0))])


def i_globe(p):
    p.circle(12, 12, 9.5)
    p.ellipse(8, 2.5, 16, 21.5)
    p.line((2.8, 12), (21.2, 12))


def i_wifi(p):
    for r in (4.6, 8.6, 12.6):
        p.arc(12, 19.5, r, 225, 315)
    p.dot(12, 19.5, 1.5)


def i_router(p):
    p.rect(2.5, 13, 21.5, 20.5, 2)
    p.dot(6.5, 16.75)
    p.dot(10, 16.75)
    p.line((17, 13), (17, 8))
    p.arc(17, 8, 2.8, 210, 330)
    p.arc(17, 8, 5.6, 210, 330)


def i_lock(p):
    p.rect(4.5, 10.5, 19.5, 21.5, 2.2)
    p.arc(12, 8, 4.2, 180, 360)
    p.line((7.8, 8), (7.8, 10.5))
    p.line((16.2, 8), (16.2, 10.5))
    p.dot(12, 15.2, 1.4)
    p.line((12, 15.2), (12, 17.6))


def i_unlock(p):
    p.rect(4.5, 10.5, 19.5, 21.5, 2.2)
    p.arc(12, 6.5, 4.2, 180, 330)
    p.line((7.8, 6.5), (7.8, 10.5))
    p.dot(12, 15.2, 1.4)
    p.line((12, 15.2), (12, 17.6))


def i_key(p):
    p.circle(7.5, 16.5, 4.3)
    p.line((10.6, 13.4), (20.5, 3.5))
    p.line((17.2, 6.8), (19.8, 9.4))
    p.line((14.6, 9.4), (16.6, 11.4))


def i_database(p):
    p.ellipse(4.5, 2.5, 19.5, 7.5)
    p.line((4.5, 5), (4.5, 19))
    p.line((19.5, 5), (19.5, 19))
    p.earc(4.5, 16.5, 19.5, 21.5, 0, 180)
    p.earc(4.5, 9.5, 19.5, 14.5, 0, 180)


def i_cpu(p):
    p.rect(5.5, 5.5, 18.5, 18.5, 2)
    p.rect(9.3, 9.3, 14.7, 14.7, 0.8)
    for v in (9.5, 14.5):
        p.line((v, 2.5), (v, 5.5))
        p.line((v, 18.5), (v, 21.5))
        p.line((2.5, v), (5.5, v))
        p.line((18.5, v), (21.5, v))


def i_ram(p):
    p.rect(2, 6.5, 22, 16.5, 1.5)
    for x in (5, 10.5, 16):
        p.rect(x, 9.2, x + 3, 13.8, 0.5)
    for x in (5, 8, 11, 14, 17, 20):
        p.line((x - 0.5, 16.5), (x - 0.5, 19.5))


def i_disk(p):
    p.rect(3, 3, 21, 21, 2.5)
    p.circle(12, 10.5, 4.8)
    p.dot(12, 10.5, 1.2)
    p.line((7, 17.5), (10, 17.5))
    p.dot(17, 17.5, 1.1)


def i_file(p):
    p.line((14, 2.5), (6.5, 2.5), (6.5, 21.5), (19, 21.5), (19, 7.5), (14, 2.5), (14, 7.5), (19, 7.5))
    p.line((9.5, 12.5), (16, 12.5))
    p.line((9.5, 16.5), (16, 16.5))


def i_folder(p):
    p.closed((3, 6), (9.5, 6), (11.5, 8.5), (21, 8.5), (21, 19), (3, 19))


def i_code(p):
    p.line((8, 6.5), (2.8, 12), (8, 17.5))
    p.line((16, 6.5), (21.2, 12), (16, 17.5))
    p.line((14, 4), (10, 20))


def i_terminal(p):
    p.rect(2, 4, 22, 20, 2.2)
    p.line((6, 9), (9.5, 12), (6, 15))
    p.line((12, 15.5), (17, 15.5))


def i_user(p):
    p.circle(12, 8, 4.3)
    p.arc(12, 22, 8, 180, 360)


def i_users(p):
    p.circle(9, 8.5, 3.8)
    p.arc(9, 21.5, 6.8, 180, 360)
    p.earc(12.2, 4.7, 19.8, 12.3, 280, 100)
    p.earc(10.2, 14.7, 23.8, 28.3, 270, 360)


def i_mail(p):
    p.rect(2, 5, 22, 19, 2.2)
    p.line((3, 6.5), (12, 13), (21, 6.5))


def i_shield(p):
    p.closed((12, 2.2), (20, 5.2), (20, 11.5), (18.6, 15.6), (15.6, 19.2), (12, 21.8), (8.4, 19.2), (5.4, 15.6),
             (4, 11.5), (4, 5.2))


def i_shield_check(p):
    i_shield(p)
    p.line((8.6, 12), (11, 14.4), (15.6, 9.6))


def i_bug(p):
    p.rect(7, 7.5, 17, 21, 5)
    p.line((12, 11), (12, 21))
    p.line((7, 13.5), (3, 12))
    p.line((7, 17), (3, 18.5))
    p.line((17, 13.5), (21, 12))
    p.line((17, 17), (21, 18.5))
    p.line((9.6, 7.8), (8, 3.5))
    p.line((14.4, 7.8), (16, 3.5))


def _tooth(a, r0, r1, hw):
    ca, sa = math.cos(a), math.sin(a)
    return ((12 + r0 * ca - hw * sa, 12 + r0 * sa + hw * ca), (12 + r1 * ca - hw * sa, 12 + r1 * sa + hw * ca),
            (12 + r1 * ca + hw * sa, 12 + r1 * sa - hw * ca), (12 + r0 * ca + hw * sa, 12 + r0 * sa - hw * ca))


def i_gear(p):
    w = SW
    outer = [("circle", (12, 12, 7.4))] + [("fill", _tooth(k * math.pi / 4, 5, 10.2, 2.1)) for k in range(8)]
    inner = [("circle", (12, 12, 7.4 - w))] + [("fill", _tooth(k * math.pi / 4, 5, 10.2 - w, 2.1 - w))
                                               for k in range(8)]
    _ring(p, outer, inner)
    p.circle(12, 12, 2.9)


def i_search(p):
    p.circle(10.5, 10.5, 6.8)
    p.line((15.5, 15.5), (21, 21))


def i_chart(p):
    p.line((3, 21), (21, 21))
    p.line((6.5, 17.5), (6.5, 13))
    p.line((12, 17.5), (12, 6.5))
    p.line((17.5, 17.5), (17.5, 10))


def i_clock(p):
    p.circle(12, 12, 9.5)
    p.line((12, 6.5), (12, 12), (15.5, 14))


def i_link(p):
    # deux maillons inclinés à 45°
    for cx, cy in ((8.6, 15.4), (15.4, 8.6)):
        c, s = math.cos(math.radians(-45)), math.sin(math.radians(-45))
        pts = []
        for k in range(0, 361, 15):
            a = math.radians(k)
            x, y = 4.6 * math.cos(a), 2.7 * math.sin(a)
            x += 1.6 * (1 if math.cos(a) > 0 else -1)
            pts.append((cx + x * c - y * s, cy + x * s + y * c))
        p.line(*pts)


def i_package(p):
    p.closed((12, 2.2), (20.8, 7), (20.8, 17), (12, 21.8), (3.2, 17), (3.2, 7))
    p.line((3.6, 7.2), (12, 12), (20.4, 7.2))
    p.line((12, 12), (12, 21.5))
    p.line((7.6, 4.6), (16.4, 9.6))


def i_robot(p):
    p.rect(4, 8, 20, 20, 3.2)
    p.dot(9, 13.5, 1.5)
    p.dot(15, 13.5, 1.5)
    p.line((10, 16.8), (14, 16.8))
    p.line((12, 8), (12, 4.8))
    p.dot(12, 3.6, 1.4)
    p.line((1.8, 12.5), (1.8, 15.5))
    p.line((22.2, 12.5), (22.2, 15.5))


def i_sparkles(p):
    star = lambda cx, cy, r: [(cx, cy - r), (cx + r * 0.22, cy - r * 0.22), (cx + r, cy), (cx + r * 0.22, cy + r * 0.22),  # noqa: E731
                              (cx, cy + r), (cx - r * 0.22, cy + r * 0.22), (cx - r, cy), (cx - r * 0.22, cy - r * 0.22)]
    p.closed(*star(10, 13, 8))
    p.closed(*star(18.5, 5.5, 3.2))


def i_message(p):
    p.closed((5, 3.5), (19, 3.5), (21.5, 6), (21.5, 14), (19, 16.5), (10, 16.5), (5.5, 20.5), (5.5, 16.5),
             (5, 16.5), (2.5, 14), (2.5, 6))
    p.line((7.5, 8.5), (16.5, 8.5))
    p.line((7.5, 12), (13.5, 12))


def i_check(p):
    p.line((4, 12.5), (9.5, 18), (20, 6.5))


def i_cross(p):
    p.line((6, 6), (18, 18))
    p.line((18, 6), (6, 18))


def i_warning(p):
    p.closed((12, 3), (21.8, 20), (2.2, 20))
    p.line((12, 9.5), (12, 14))
    p.dot(12, 17, 1.3)


def i_bolt(p):
    p.closed((13.5, 2), (4.5, 13.5), (12, 13.5), (10.5, 22), (19.5, 10.5), (12, 10.5))


def i_eye(p):
    top = [(x / 2, 12 - 7.5 * math.sin(math.pi * (x / 2 - 2) / 20)) for x in range(4, 45)]
    bot = [(x, 24 - y) for x, y in reversed(top)]
    p.line(*top, *bot[1:])
    p.circle(12, 12, 3.2)


def i_cookie(p):
    p.circle(12, 12, 9.5)
    for x, y in ((8.5, 9), (14.5, 8), (9.5, 15), (15, 14.5), (12, 11.8)):
        p.dot(x, y, 1.2)


def i_password(p):
    p.rect(2, 7, 22, 17, 3)
    for x in (7, 12, 17):
        p.dot(x, 12, 1.7)


def i_network(p):
    p.circle(12, 4.8, 2.6)
    p.circle(4.8, 18.8, 2.6)
    p.circle(19.2, 18.8, 2.6)
    p.line((10.8, 7.1), (6, 16.5))
    p.line((13.2, 7.1), (18, 16.5))
    p.line((7.4, 18.8), (16.6, 18.8))


def i_money(p):
    p.circle(12, 12, 9.5)
    p.glyph("€", 12, 12.4, 11, 700)


def i_calendar(p):
    p.rect(3, 5, 21, 21, 2.2)
    p.line((3.5, 10), (20.5, 10))
    p.line((8, 3), (8, 7))
    p.line((16, 3), (16, 7))
    p.dot(8, 14.5, 1.1)
    p.dot(12, 14.5, 1.1)
    p.dot(16, 14.5, 1.1)


def i_heart(p):
    pts = []
    for k in range(0, 360, 6):
        a = math.radians(k)
        x = 16 * math.sin(a) ** 3
        y = 13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)
        pts.append((12 + x * 0.56, 11.4 - y * 0.56))
    p.closed(*pts)


def i_video(p):
    p.rect(2, 4.5, 22, 19.5, 2.5)
    p.closed((10, 9), (15.5, 12), (10, 15))


def i_image(p):
    p.rect(3, 4, 21, 20, 2.2)
    p.circle(9, 9.5, 1.8)
    p.line((3.5, 18), (9, 12.8), (14, 17.2), (16.8, 14.5), (20.5, 18))


def i_download(p):
    p.line((12, 3), (12, 15))
    p.line((7, 10), (12, 15), (17, 10))
    p.line((4, 20.5), (20, 20.5))


def i_upload(p):
    p.line((12, 15), (12, 3))
    p.line((7, 8), (12, 3), (17, 8))
    p.line((4, 20.5), (20, 20.5))


def i_speed(p):
    p.arc(12, 15, 9.5, 180, 360)
    p.line((12, 15), (16.8, 9.5))
    p.dot(12, 15, 1.6)
    p.line((2.5, 19), (21.5, 19))


def i_home(p):
    p.line((3, 11), (12, 3), (21, 11))
    p.line((5.5, 9.5), (5.5, 21), (18.5, 21), (18.5, 9.5))
    p.line((10, 21), (10, 15), (14, 15), (14, 21))


def i_book(p):
    p.rect(4.5, 2.5, 19.5, 21.5, 1.8)
    p.line((8.5, 2.8), (8.5, 21.2))
    p.line((11.5, 8), (16.5, 8))


def i_pin(p):
    w = SW
    _ring(p, [("circle", (12, 9.5, 7.4)), ("fill", ((5.4, 12.6), (12, 22.2), (18.6, 12.6)))],
          [("circle", (12, 9.5, 7.4 - w)), ("fill", ((7.6, 12.6), (12, 19), (16.4, 12.6)))])
    p.circle(12, 9.5, 2.6)


def i_truck(p):
    p.rect(1.5, 5.5, 14, 16.5, 1)
    p.line((14, 9), (18.5, 9), (22, 13), (22, 16.5), (14, 16.5))
    p.circle(6, 18.2, 2.2, fill=True)
    p.circle(17.5, 18.2, 2.2, fill=True)


def i_keyboard(p):
    p.rect(2, 6, 22, 18, 2.2)
    for y in (9.8, 12.8):
        for x in (6, 9.3, 12.6, 15.9, 19.2):
            p.dot(x - 0.3, y, 0.9)
    p.line((8, 15.6), (16, 15.6))


def i_question(p):
    p.circle(12, 12, 9.5)
    p.glyph("?", 12, 12.4, 12, 800)


def i_info(p):
    p.circle(12, 12, 9.5)
    p.line((12, 11), (12, 16.5))
    p.dot(12, 7.6, 1.4)


def i_battery(p):
    p.rect(2, 7, 19, 17, 2)
    p.line((21.5, 10.5), (21.5, 13.5))
    p.rect(5, 10, 11, 14, 0.5, fill=True)


def i_lightbulb(p):
    p.arc(12, 9.5, 6.5, 140, 400)
    p.line((7, 13.7), (9, 17), (15, 17), (17, 13.7))
    p.line((9.5, 20.5), (14.5, 20.5))


def i_target(p):
    p.circle(12, 12, 9.5)
    p.circle(12, 12, 5.2)
    p.dot(12, 12, 1.6)


def i_layers(p):
    p.closed((12, 3), (21.5, 8), (12, 13), (2.5, 8))
    p.line((2.5, 12.5), (12, 17.5), (21.5, 12.5))
    p.line((2.5, 17), (12, 22), (21.5, 17))


def i_binary(p):
    p.glyph("01", 12, 12.5, 12, 700, mono=True)
    p.rect(2, 4, 22, 20, 2.5)


def i_hash(p):
    p.line((9.5, 3.5), (7.5, 20.5))
    p.line((16.5, 3.5), (14.5, 20.5))
    p.line((4, 9), (21, 9))
    p.line((3, 15), (20, 15))


def i_at(p):
    p.glyph("@", 12, 12.6, 19, 600)


def _head(p, x, y, dx, dy, ln=3.4):
    """Pointe de flèche pleine au point (x, y), orientée selon (dx, dy)."""
    n = math.hypot(dx, dy)
    dx, dy = dx / n, dy / n
    p.fill((x + dx * ln, y + dy * ln), (x - dy * ln * 0.8, y + dx * ln * 0.8), (x + dy * ln * 0.8, y - dx * ln * 0.8))


def i_refresh(p):
    for a0, a1 in ((195, 330), (15, 150)):
        p.arc(12, 12, 8.2, a0, a1)
        a = math.radians(a1)
        _head(p, 12 + 8.2 * math.cos(a), 12 + 8.2 * math.sin(a), -math.sin(a), math.cos(a))


def i_trophy(p):
    p.line((7, 8.5), (7, 3.5), (17, 3.5), (17, 8.5))
    p.arc(12, 8.5, 5, 0, 180)
    p.earc(2.8, 4.5, 8.2, 10.5, 90, 270)
    p.earc(15.8, 4.5, 21.2, 10.5, 270, 450)
    p.line((12, 13.5), (12, 18))
    p.line((8, 20.5), (16, 20.5))


ICONS = {name[2:].replace("_", "-"): fn for name, fn in globals().items() if name.startswith("i_")}
ALIASES = {"pc": "laptop", "ordinateur": "laptop", "ecran": "monitor", "smartphone": "phone",
           "serveur": "server", "nuage": "cloud", "internet": "globe", "web": "globe", "box": "router",
           "cadenas": "lock", "cle": "key", "base": "database", "processeur": "cpu", "memoire": "ram",
           "disque": "disk", "fichier": "file", "dossier": "folder", "utilisateur": "user", "email": "mail",
           "bouclier": "shield", "engrenage": "gear", "loupe": "search", "horloge": "clock", "lien": "link",
           "colis": "package", "ia": "sparkles", "ai": "sparkles", "attention": "warning", "eclair": "bolt",
           "oeil": "eye", "reseau": "network", "argent": "money", "maison": "home", "livre": "book",
           "camion": "truck", "clavier": "keyboard", "ampoule": "lightbulb", "cible": "target",
           "couches": "layers", "binaire": "binary", "coeur": "heart", "commentaire": "message",
           "bulle": "message"}


def known(name):
    name = str(name or "")
    return (name.startswith("text:") and 0 < len(name) - 5 <= 4) or _resolve(name) in ICONS \
        or (ICON_DIR / f"{name}.png").exists()


def _resolve(name):
    return ALIASES.get(name, name)


@lru_cache(maxsize=256)
def icon(name, size, color):
    """Icône `name` en `size` px, couleur RGB. Inconnue -> point d'interrogation."""
    name = str(name or "")
    custom = ICON_DIR / f"{name}.png"
    if custom.exists():
        src = Image.open(custom).convert("RGBA").resize((size, size), Image.LANCZOS)
        out = Image.new("RGBA", (size, size), color + (0,))
        out.putalpha(src.getchannel("A"))
        return out
    p = Pen(size)
    if name.startswith("text:"):
        p.glyph(name[5:], 12, 12.6, 13 if len(name) <= 7 else 10, 800)
    else:
        ICONS.get(_resolve(name), i_question)(p)
    mask = p.m.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), color + (0,))
    out.putalpha(mask)
    return out


@lru_cache(maxsize=128)
def badge(name, d, color=None, fill=None, ratio=0.5):
    """Pastille ronde teintée avec l'icône au centre (le visuel principal des scènes)."""
    color = color or gfx.T.accent
    img = gfx.disc(d, fill or gfx.tint(color)).copy()
    ic = icon(name, int(d * ratio), color)
    img.alpha_composite(ic, ((d - ic.width) // 2, (d - ic.height) // 2))
    return img


def sheet(out=None):
    """Planche de toutes les icônes avec leur nom."""
    names = sorted(ICONS)
    cols, cell = 6, 180
    rows = math.ceil(len(names) / cols)
    img = Image.new("RGBA", (cols * cell, rows * cell), (255, 255, 255, 255))
    for i, n in enumerate(names):
        x, y = (i % cols) * cell, (i // cols) * cell
        img.alpha_composite(icon(n, 96, (17, 24, 39)), (x + 42, y + 22))
        ImageDraw.Draw(img).text((x + cell // 2, y + 140), n, font=gfx.font(22, 500), fill=(99, 107, 122),
                                 anchor="mm")
    out = out or ICON_DIR.parent / "icons_planche.png"
    img.convert("RGB").save(out)
    return out, len(names)


if __name__ == "__main__":
    gfx.set_theme({})
    path, n = sheet()
    print(f"{n} icônes -> {path}")
