"""Scènes génériques, réutilisables pour n'importe quelle voiture.

Chaque scène se règle dans le JSON de l'épisode (voir README, « Scènes ») :
  drive     la voiture roule dans un décor, avec un titre optionnel
  anecdote  un personnage raconte (bulle de dialogue)
  reveal    présentation au salon : projecteurs, réactions du public
  specs     fiche technique : jusqu'à 4 icônes qui apparaissent avec la voix
  counter   un chiffre qui défile (production, ventes, record…)
  date      une date clé en grand, la voiture arrive et s'arrête
"""
import math
import random

from . import sprites as S
from .scenes import (GROUND, SCENES, W, backdrop, car_at, car_sprite, clouds, draw_ctx, ease_out, ground, hills,
                     paste, pop, road, sky_cached, text, text_w, c)


# ------------------------------------------------------------ briques communes
def stage(img, t, dur, sc, speed=0.5, bands=(S.BLUE, S.BLUE, S.WHITE)):
    """Décor (banque ou ciel par défaut) + sol. Renvoie la ligne où poser la voiture."""
    if not backdrop(img, t, dur, sc, speed=speed):
        sky_cached(img, list(bands))
        clouds(img, t, speed=6, seed=hash(sc.get("type", "")) % 50)
        hills(img, t, S.GREEN, 150, 6, 10)
    kind = sc.get("ground", "road")
    moving = sc.get("car", "cruise") in ("cruise",)
    if kind == "road":
        road(img, t if moving else 0, speed=90)
        return GROUND + 22
    if kind == "field":
        ground(img, t if moving else 0, top=S.BROWN, dirt=S.BROWN, speed=60, furrows=True)
    elif kind == "sidewalk":
        d = draw_ctx(img)
        d.rectangle([(0, GROUND), (W, 320)], fill=c(S.DGREY))
        d.rectangle([(0, GROUND), (W, GROUND + 2)], fill=c(S.LGREY))
        for x in range(0, W, 16):
            d.line([(x, GROUND + 3), (x - 6, GROUND + 12)], fill=c(S.LGREY))
    elif kind == "floor":
        d = draw_ctx(img)
        d.rectangle([(0, GROUND), (W, 320)], fill=c(sc.get("floor_col", S.PLUM)))
    else:
        ground(img, t if moving else 0, speed=40)
    return GROUND + 6


def wrap_px(s, max_px, size):
    words, lines, cur = s.split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if text_w(cand, size) <= max_px:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def title_block(img, t, dur, sc, y=48):
    """Titre (16 px) + sous-titre (8 px) qui surgissent à `title_at` (fraction de la scène)."""
    title, sub = sc.get("title"), sc.get("subtitle")
    if not (title or sub):
        return
    start = dur * sc.get("title_at", 0.12)
    if t < start:
        return
    k = pop((t - start) / 0.35)
    dy = int((k - 1) * -6)
    for line in wrap_px(title or "", 160, 16):
        text(img, (W // 2, y + dy), line, col=sc.get("title_col", S.YELLOW), anchor="ma", size=16)
        y += 20
    for line in wrap_px(sub or "", 160, 8):
        text(img, (W // 2, y + 2 + dy), line, col=S.WHITE, anchor="ma")
        y += 11


def car_motion(img, t, dur, sc, ep, y):
    mode = sc.get("car", "cruise")
    lights = sc.get("lights_up", False)
    if mode == "none":
        return
    if mode == "cruise":
        car_at(img, t, W // 2 + 4 * math.sin(t * 1.1), y, ep, bounce=1, lights_up=lights)
    elif mode == "pass":
        x = -40 + (W + 80) * t / dur
        car_at(img, t, x, y, ep, bounce=1, lights_up=lights)
    elif mode == "enter":
        p = ease_out(t / (dur * 0.55))
        car_at(img, t, -40 + (W // 2 + 40) * p, y, ep, moving=p < 0.99, lights_up=lights)
    else:  # parked
        car_at(img, t, W // 2, y, ep, moving=False, lights_up=lights)


def cue_time(sc, dur, words, fallback):
    """Instant où un mot est prononcé / sous-titré (pour synchroniser une apparition)."""
    times = []
    words = [w.lower() for w in words if w]
    for a, _b, txt in sc.get("_subs", []):
        if any(w in txt for w in words):
            times.append(a)
            break
    voice = sc.get("voice", "").lower()
    for w in words:
        pos = voice.find(w)
        if pos >= 0:
            times.append(0.25 + pos / max(1, len(voice)) * (dur - 0.7))
            break
    return min(times) if times else fallback


# ------------------------------------------------------------ scènes
def scene_drive(img, t, dur, sc, ep):
    y = stage(img, t, dur, sc, speed=1 if sc.get("car", "cruise") == "cruise" else 0.3)
    car_motion(img, t, dur, sc, ep, y)
    title_block(img, t, dur, sc)


def scene_anecdote(img, t, dur, sc, ep):
    y = stage(img, t, dur, dict(sc, car="parked", ground=sc.get("ground", "grass")), speed=0.2)
    px = 34
    paste(img, S.person(sc.get("person", 0)), px, y)
    quote = sc.get("quote", "")
    start = dur * 0.15
    if quote and t > start:
        lines = wrap_px(quote.upper(), 108, 8)
        n = min(len(lines), int((t - start) / 0.18) + 1)   # la bulle s'écrit ligne par ligne
        bw = max(text_w(l) for l in lines) + 10
        bh = len(lines) * 11 + 6
        bx, by = 50, y - 34 - bh
        d = draw_ctx(img)
        d.rectangle([(bx, by), (bx + bw, by + bh)], fill=c(S.WHITE), outline=c(S.K))
        d.polygon([(bx + 4, by + bh), (bx + 14, by + bh), (px + 6, y - 22)], fill=c(S.WHITE))
        d.line([(bx + 4, by + bh), (px + 6, y - 22), (bx + 14, by + bh)], fill=c(S.K))
        for i, line in enumerate(lines[:n]):
            text(img, (bx + 5, by + 4 + i * 11), line, col=S.K, stroke=False)
    if sc.get("car") == "enter":
        p = ease_out((t - dur * 0.55) / (dur * 0.35))
        if p > 0:
            car_at(img, t, W + 40 - (W // 2 - 10) * p, y, ep, moving=p < 0.99, flip=True)
    title_block(img, t, dur, sc, y=44)


def scene_reveal(img, t, dur, sc, ep):
    d = draw_ctx(img)
    if not backdrop(img, t, dur, sc, speed=0.2):
        sky_cached(img, [S.K, S.PLUM])
    d.rectangle([(0, GROUND), (W, 320)], fill=c(S.PLUM))
    pxl = img.load()
    for (sx, ex) in ((30, 70), (150, 110)):          # projecteurs tramés
        for yy in range(36, GROUND):
            k = (yy - 36) / (GROUND - 36)
            x0 = sx + (ex - sx) * k - 6 - 18 * k
            x1 = sx + (ex - sx) * k + 6 + 18 * k
            for x in range(max(0, int(x0)), min(W, int(x1))):
                if (x + yy) % 2 == 0:
                    pxl[x, yy] = S.PAL[S.YELLOW] + (255,)
    for x0 in (0, W - 18):
        d.rectangle([(x0, 30), (x0 + 17, GROUND + 10)], fill=c(S.RED))
        for x in range(x0 + 3, x0 + 17, 5):
            d.line([(x, 30), (x, GROUND + 10)], fill=c(S.PLUM))
    if sc.get("title"):
        text(img, (W // 2, 40), sc["title"].upper(), col=S.YELLOW, anchor="ma")
    d.rectangle([(36, GROUND - 4), (144, GROUND + 6)], fill=c(S.LAVENDER))
    d.rectangle([(36, GROUND - 4), (144, GROUND - 3)], fill=c(S.WHITE))
    # phares escamotables qui clignent pour saluer le public (si la voiture en a)
    blink = sc.get("lights_up", False) or (dur * 0.4 < t < dur * 0.6 and int(t * 4) % 2 == 0)
    car_at(img, t, 90, GROUND - 3, ep, moving=False, lights_up=blink)
    for i, hx in enumerate((20, 42, 64, 88, 112, 136, 158)):
        col = (S.PEACH, S.BROWN, S.ORANGE)[i % 3]
        paste(img, S.person_head(col), hx, GROUND + 12 + (1 if (int(t * 4) + i) % 2 else 0))
    half = dur * sc.get("split", 0.5)
    bubbles = sc.get("bubbles", ["WOW", "?!", "OUAH"])
    spots = ((44, 126), (136, 112), (96, 90))
    if t < half:
        for i, s in enumerate(bubbles[:3]):
            if t > 0.4 + i * 0.6:
                bx, by = spots[i]
                w = text_w(s) + 6
                d.rectangle([(bx - w // 2, by), (bx + w // 2, by + 12)], fill=c(S.WHITE), outline=c(S.K))
                d.polygon([(bx - 2, by + 12), (bx + 2, by + 12), (bx, by + 16)], fill=c(S.WHITE))
                text(img, (bx, by + 3), s, col=S.K, anchor="ma", stroke=False)
    elif sc.get("hearts", True):
        rnd = random.Random(7)
        for i in range(10):
            hx = rnd.randint(14, 166)
            life = (t - half) * 30 - i * 6
            if life > 0:
                yy = GROUND + 10 - (life % 110)
                paste(img, S.heart(), hx + int(3 * math.sin(life / 6)), yy, anchor="mm")


def scene_specs(img, t, dur, sc, ep):
    sky_cached(img, [S.PEACH, S.ORANGE])
    d = draw_ctx(img)
    d.rectangle([(10, 36), (170, 204)], fill=c(S.WHITE), outline=c(S.K))
    for yy in range(64, 200, 10):
        d.line([(16, yy), (164, yy)], fill=c(S.LGREY))
    d.line([(26, 40), (26, 200)], fill=c(S.RED))
    for i, line in enumerate(wrap_px(sc.get("title", "FICHE TECHNIQUE").upper(), 140, 8)[:2]):
        text(img, (W // 2, 44 + i * 10), line, col=S.NAVY, anchor="ma", stroke=False)
    cells = [(48, 104), (134, 104), (48, 168), (134, 168)]
    for i, (item, (cx, cy)) in enumerate(zip(sc.get("items", [])[:4], cells)):
        start = cue_time(sc, dur, item.get("match", [item.get("label", "")]), dur * (0.12 + 0.2 * i))
        if t < start:
            continue
        k = pop((t - start) / 0.35)
        name = item.get("icon")
        if name == "farmers":
            paste(img, S.farmer(0), cx - 6, cy)
            paste(img, S.farmer(1), cx + 6, cy)
        elif name == "car":
            spr = car_sprite(ep, t, moving=False, lights_up=item.get("lights_up", False))
            paste(img, spr, cx, cy)
        else:
            spr = S.icon(name)
            if spr is not None:
                paste(img, spr, cx, cy)
        text(img, (cx, cy + 6 - int((k - 1) * 8)), item.get("label", "").upper(),
             col=S.NAVY, anchor="ma", stroke=False)


def scene_counter(img, t, dur, sc, ep):
    y = stage(img, t, dur, dict(sc, car="cruise", ground=sc.get("ground", "road")), speed=1)
    colors = sc.get("colors") or [{}]
    k = int(t / (dur / len(colors))) % len(colors)
    car_at(img, t, W // 2, y, ep, bounce=1, lights_up=sc.get("lights_up", False), **colors[k])
    target = sc.get("counter_to", 1000000)
    n = int(target * ease_out(t / (dur * 0.85)))
    s = f"{n:,}".replace(",", " ")
    text(img, (W // 2, 58), s, col=S.YELLOW, anchor="ma", size=16 if len(s) <= 9 else 8)
    for i, line in enumerate(wrap_px(sc.get("counter_label", "EXEMPLAIRES").upper(), 160, 8)):
        text(img, (W // 2, 80 + i * 11), line, anchor="ma")
    if n >= target and sc.get("counter_suffix"):
        text(img, (W // 2, 104), sc["counter_suffix"].upper(), col=S.WHITE, anchor="ma")


def scene_date(img, t, dur, sc, ep):
    y = stage(img, t, dur, dict(sc, car="enter"), speed=0.3)
    car_motion(img, t, dur, dict(sc, car=sc.get("car", "enter")), ep, y)
    if t > dur * sc.get("date_at", 0.45):
        text(img, (W // 2, 50), sc.get("date", ""), col=S.YELLOW, anchor="ma", size=16)
        for i, line in enumerate(wrap_px(sc.get("label", "").upper(), 160, 8)):
            text(img, (W // 2, 72 + i * 11), line, anchor="ma")


GENERIC = {
    "drive": scene_drive, "anecdote": scene_anecdote, "reveal": scene_reveal,
    "specs": scene_specs, "counter": scene_counter, "date": scene_date,
}


SCENES.update(GENERIC)
