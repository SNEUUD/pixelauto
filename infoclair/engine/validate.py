"""Vérification d'un épisode JSON avant rendu (utilisée par make_video.py et l'API)."""
import re
from typing import Any

from . import icons
from .scenes import SCENES

# champs obligatoires par type de scène
REQUIRED = {
    "concept": ["term", "definition"], "analogy": ["left", "right"], "flow": ["nodes"], "list": ["items"],
    "code": ["code"], "stat": ["value"], "versus": ["left", "right"], "fact": ["text"],
}


def _icon_fields(sc):
    """Toutes les icônes citées par une scène (champ, nom)."""
    if sc.get("icon"):
        yield "icon", sc["icon"]
    for side in ("left", "right"):
        if isinstance(sc.get(side), dict) and sc[side].get("icon"):
            yield f"{side}.icon", sc[side]["icon"]
    for key in ("nodes", "items"):
        for i, it in enumerate(sc.get(key) or []):
            if isinstance(it, dict) and it.get("icon"):
                yield f"{key}[{i}].icon", it["icon"]


def validate(ep: Any):
    """Renvoie la liste des erreurs (vide si l'épisode est rendable)."""
    errors = []
    if not isinstance(ep, dict):
        return ["l'épisode doit être un objet JSON"]
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", str(ep.get("id", ""))):
        errors.append("id : 1 à 64 caractères parmi lettres, chiffres, _ et -")
    if not ep.get("title"):
        errors.append("title manquant")
    if ep.get("theme", "light") not in ("light", "dark"):
        errors.append("theme : light ou dark")
    if ep.get("icon") and not icons.known(ep["icon"]):
        errors.append(f"icon « {ep['icon']} » inconnue")
    sc_list = ep.get("scenes")
    if not isinstance(sc_list, list) or not sc_list:
        errors.append("scenes : liste non vide attendue")
        return errors
    if len(sc_list) > 20:
        errors.append("scenes : 20 au maximum")
    for i, sc in enumerate(sc_list):
        if not isinstance(sc, dict):
            errors.append(f"scène {i} : objet attendu")
            continue
        kind = sc.get("type")
        if kind not in SCENES:
            errors.append(f"scène {i} : type « {kind} » inconnu (possibles : {', '.join(SCENES)})")
            continue
        if not str(sc.get("voice", "")).strip():
            errors.append(f"scène {i} : voice vide")
        elif len(sc["voice"]) > 600:
            errors.append(f"scène {i} : voice trop long (600 caractères max)")
        for f in REQUIRED.get(kind, []):
            if sc.get(f) in (None, "", [], {}):
                errors.append(f"scène {i} ({kind}) : champ « {f} » manquant")
        if kind == "flow" and not 2 <= len(sc.get("nodes") or []) <= 4:
            errors.append(f"scène {i} (flow) : 2 à 4 nodes")
        if kind == "list" and not 1 <= len(sc.get("items") or []) <= 5:
            errors.append(f"scène {i} (list) : 1 à 5 items")
        if kind == "stat":
            try:
                float(sc.get("value"))
            except (TypeError, ValueError):
                errors.append(f"scène {i} (stat) : value doit être un nombre")
        for field, name in _icon_fields(sc):
            if not icons.known(name):
                errors.append(f"scène {i} : {field} « {name} » inconnue (voir la liste dans le README)")
    return errors
