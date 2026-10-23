#!/usr/bin/env python3
"""API de rendu : on envoie un épisode JSON, on récupère la vidéo.

    POST   /videos                 épisode JSON (ou {"episode": {...}, "webhook": "https://..."})
    GET    /videos                 derniers rendus
    GET    /videos/{id}            état : queued | running | done | failed (+ progression)
    GET    /videos/{id}/file       télécharge le MP4
    DELETE /videos/{id}            annule (si en attente) ou supprime
    GET    /health                 sans clé
Documentation interactive : http://<hôte>:8000/docs

Toutes les routes (sauf /health) demandent l'en-tête  X-API-Key: <clé>  (fichier .env).
Les rendus passent un par un (file d'attente) et survivent à un redémarrage (dossier jobs/).
"""
import json
import os
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Optional

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
JOBS.mkdir(exist_ok=True)

API_KEY = os.environ.get("PIXELAUTO_API_KEY", "")
VOICE = os.environ.get("PIXELAUTO_VOICE", str(ROOT / "voices" / "fr_FR-siwis-medium.onnx"))
TTS = os.environ.get("PIXELAUTO_TTS", "piper")
NVENC = os.environ.get("PIXELAUTO_NVENC", "1") == "1"
KEEP_DAYS = float(os.environ.get("PIXELAUTO_KEEP_DAYS", "14"))   # nettoyage des vieux rendus
MAX_QUEUE = int(os.environ.get("PIXELAUTO_MAX_QUEUE", "20"))
PUBLIC_URL = os.environ.get("PIXELAUTO_PUBLIC_URL", "").rstrip("/")   # pour les liens des webhooks

if not API_KEY:
    sys.exit("PIXELAUTO_API_KEY manquante : lance install_api.sh ou ./api.sh (qui lit .env).")

sys.path.insert(0, str(ROOT))
from engine import decors, generic, scenes  # noqa: E402,F401  (generic enregistre ses scènes)

work = queue.Queue()
lock = threading.Lock()
current = {"id": None, "proc": None}


# ------------------------------------------------------------ jobs (sur disque)
def job_dir(jid):
    if not re.fullmatch(r"[a-f0-9]{12}", jid or ""):
        raise HTTPException(404, "vidéo inconnue")
    d = JOBS / jid
    if not d.exists():
        raise HTTPException(404, "vidéo inconnue")
    return d


def read_status(d):
    try:
        return json.loads((d / "status.json").read_text())
    except (OSError, ValueError):
        return {"id": d.name, "status": "failed", "error": "état illisible"}


def write_status(d, **kw):
    with lock:
        st = read_status(d) if (d / "status.json").exists() else {}
        st.update(kw)
        tmp = d / "status.json.tmp"
        tmp.write_text(json.dumps(st, ensure_ascii=False, indent=2))
        tmp.replace(d / "status.json")
        return st


def public(st, request: Optional[Request] = None):
    out = {k: v for k, v in st.items() if k != "webhook"}
    if st.get("status") == "done":
        path = f"/videos/{st['id']}/file"
        base = str(request.base_url).rstrip("/") if request else PUBLIC_URL
        out["url"] = base + path
    return out


# ------------------------------------------------------------ validation de l'épisode
def validate(ep: Any):
    errors = []
    if not isinstance(ep, dict):
        return ["le corps doit être un objet JSON (l'épisode)"]
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,64}", str(ep.get("id", ""))):
        errors.append("id : 1 à 64 caractères parmi lettres, chiffres, _ et -")
    if not ep.get("title"):
        errors.append("title manquant")
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
        if sc.get("type") not in scenes.SCENES:
            errors.append(f"scène {i} : type « {sc.get('type')} » inconnu "
                          f"(possibles : {', '.join(sorted(scenes.SCENES))})")
        if not str(sc.get("voice", "")).strip():
            errors.append(f"scène {i} : voice vide")
        elif len(sc["voice"]) > 600:
            errors.append(f"scène {i} : voice trop long (600 caractères max)")
        if sc.get("bg") and not decors.known(sc["bg"]):
            errors.append(f"scène {i} : décor « {sc['bg']} » inconnu "
                          f"(possibles : {', '.join(decors.DECORS)})")
    car = ep.get("car")
    if not isinstance(car, dict) or not isinstance(car.get("profile"), list):
        errors.append("car : objet attendu avec un profile (voir README, « Voiture »)")
    elif not isinstance(car.get("wheels"), list) or len(car["wheels"]) != 2:
        errors.append("car.wheels : [x_arrière, x_avant] attendu")
    return errors


# ------------------------------------------------------------ worker (un rendu à la fois)
PROGRESS = re.compile(r"\[vidéo\]\s+([\d.]+)/([\d.]+) s")


def render(jid):
    d = JOBS / jid
    st = read_status(d)
    if st.get("status") == "cancelled":
        return
    write_status(d, status="running", step="voix", started=time.time(), progress=0)
    cmd = [sys.executable, "-u", str(ROOT / "make_video.py"), str(d / "episode.json"),
           "-o", str(d / "video.mp4"), "--voice", VOICE, "--tts", TTS]
    if NVENC:
        cmd.append("--nvenc")
    log = open(d / "log.txt", "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    current.update(id=jid, proc=proc)
    buf, last = b"", 0.0
    while True:
        ch = proc.stdout.read(64)
        if not ch:
            break
        buf += ch
        parts = re.split(rb"[\r\n]", buf)
        buf = parts.pop()
        for p in parts:
            line = p.decode("utf-8", "replace")
            if "Missing phoneme" in line or not line.strip():
                continue
            log.write(line + "\n")
            m = PROGRESS.search(line)
            if m and time.time() - last > 1:
                last = time.time()
                write_status(d, step="vidéo", progress=round(100 * float(m[1]) / float(m[2])))
    code = proc.wait()
    log.close()
    current.update(id=None, proc=None)
    if read_status(d).get("status") == "cancelled":
        return
    if code == 0 and (d / "video.mp4").exists():
        dur = probe_duration(d / "video.mp4")
        st = write_status(d, status="done", step=None, progress=100, finished=time.time(),
                          duration=dur, size=(d / "video.mp4").stat().st_size)
    else:
        tail = (d / "log.txt").read_text(encoding="utf-8").strip().splitlines()[-5:]
        st = write_status(d, status="failed", finished=time.time(), error="\n".join(tail) or f"code {code}")
    notify(st)


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 1)
    except ValueError:
        return None


def notify(st):
    url = st.get("webhook")
    if not url:
        return
    body = json.dumps(public(st), ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:  # noqa: BLE001
        print(f"[webhook] {url} : {e}")


def worker():
    while True:
        jid = work.get()
        try:
            render(jid)
        except Exception as e:  # noqa: BLE001
            write_status(JOBS / jid, status="failed", error=str(e), finished=time.time())
        finally:
            work.task_done()


def cleanup():
    """Supprime les rendus terminés depuis plus de KEEP_DAYS jours."""
    limit = time.time() - KEEP_DAYS * 86400
    for d in JOBS.iterdir():
        st = read_status(d) if d.is_dir() else {}
        if st.get("status") in ("done", "failed", "cancelled") and st.get("finished", time.time()) < limit:
            shutil.rmtree(d, ignore_errors=True)


def startup():
    cleanup()
    # reprend les rendus interrompus par un arrêt
    pending = []
    for d in JOBS.iterdir():
        if d.is_dir():
            st = read_status(d)
            if st.get("status") in ("queued", "running"):
                write_status(d, status="queued", progress=0)
                pending.append((st.get("created", 0), d.name))
    for _, jid in sorted(pending):
        work.put(jid)
    threading.Thread(target=worker, daemon=True).start()


@asynccontextmanager
async def lifespan(_app):
    startup()
    yield


app = FastAPI(title="pixelauto", version="1.0", lifespan=lifespan,
              description="Rendu de vidéos TikTok 8 bits à partir d'un épisode JSON.")


# ------------------------------------------------------------ routes
def auth(x_api_key: str = Header(default="")):
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(401, "clé d'API invalide (en-tête X-API-Key)")


@app.get("/health")
def health():
    return {"ok": True, "queue": work.qsize(), "rendering": current["id"]}


@app.post("/videos", status_code=202, dependencies=[Depends(auth)])
async def create(request: Request):
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(400, "JSON invalide")
    webhook = None
    if isinstance(body, dict) and "episode" in body:
        webhook = body.get("webhook")
        body = body["episode"]
    errors = validate(body)
    if errors:
        raise HTTPException(422, {"errors": errors})
    if webhook and not re.match(r"https?://", str(webhook)):
        raise HTTPException(422, {"errors": ["webhook : URL http(s) attendue"]})
    if work.qsize() >= MAX_QUEUE:
        raise HTTPException(429, "file d'attente pleine, réessaie plus tard")
    jid = secrets.token_hex(6)
    d = JOBS / jid
    d.mkdir()
    (d / "episode.json").write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    st = write_status(d, id=jid, episode=body["id"], title=body["title"], status="queued",
                      progress=0, created=time.time(), webhook=webhook)
    work.put(jid)
    st["position"] = work.qsize()
    return public(st, request)


@app.get("/videos", dependencies=[Depends(auth)])
def list_jobs(request: Request, limit: int = 20):
    items = [read_status(d) for d in JOBS.iterdir() if d.is_dir()]
    items.sort(key=lambda s: s.get("created", 0), reverse=True)
    return [public(s, request) for s in items[: max(1, min(limit, 100))]]


@app.get("/videos/{jid}", dependencies=[Depends(auth)])
def get_job(jid: str, request: Request):
    return public(read_status(job_dir(jid)), request)


@app.get("/videos/{jid}/file", dependencies=[Depends(auth)])
def get_file(jid: str):
    d = job_dir(jid)
    st = read_status(d)
    if st.get("status") != "done":
        raise HTTPException(409, f"vidéo pas prête (état : {st.get('status')})")
    return FileResponse(d / "video.mp4", media_type="video/mp4", filename=f"{st['episode']}.mp4")


@app.get("/videos/{jid}/log", dependencies=[Depends(auth)])
def get_log(jid: str):
    p = job_dir(jid) / "log.txt"
    return {"log": p.read_text(encoding="utf-8") if p.exists() else ""}


@app.delete("/videos/{jid}", dependencies=[Depends(auth)])
def delete(jid: str):
    d = job_dir(jid)
    if current["id"] == jid and current["proc"]:
        write_status(d, status="cancelled", finished=time.time())
        current["proc"].terminate()
        return {"id": jid, "status": "cancelled"}
    if read_status(d).get("status") == "queued":
        write_status(d, status="cancelled", finished=time.time())
        return {"id": jid, "status": "cancelled"}
    shutil.rmtree(d, ignore_errors=True)
    return {"id": jid, "status": "deleted"}
