#!/usr/bin/env python3
"""Client minimal de l'API (bibliothèque standard uniquement) : envoie, attend, télécharge.

    python3 client.py exemples/01_dns.json                     # -> ./01_dns.mp4
    python3 client.py exemples/*.json --out videos/            # plusieurs épisodes
    python3 client.py exemples/01_dns.json --url http://192.168.1.20:8000

La clé est lue dans INFOCLAIR_API_KEY, sinon dans le .env à côté de ce script.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def api_key():
    if os.environ.get("INFOCLAIR_API_KEY"):
        return os.environ["INFOCLAIR_API_KEY"]
    env = Path(__file__).resolve().parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("INFOCLAIR_API_KEY="):
                return line.split("=", 1)[1].split()[0]
    sys.exit("Clé introuvable : définis INFOCLAIR_API_KEY.")


def call(url, key, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"X-API-Key": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read(), r.headers.get_content_type()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        sys.exit(f"[erreur {e.code}] {detail}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodes", nargs="+")
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--out", default=".")
    ap.add_argument("--webhook")
    args = ap.parse_args()
    key, base = api_key(), args.url.rstrip("/")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for path in args.episodes:
        ep = json.loads(Path(path).read_text(encoding="utf-8"))
        body = {"episode": ep, "webhook": args.webhook} if args.webhook else ep
        st = json.loads(call(f"{base}/videos", key, "POST", body)[0])
        print(f"[envoyé] {ep['id']} -> {st['id']} (position {st.get('position')})")
        jobs.append((st["id"], ep["id"]))

    for jid, name in jobs:
        last = None
        while True:
            st = json.loads(call(f"{base}/videos/{jid}", key)[0])
            step = f" ({st['step']})" if st.get("step") else ""
            line = f"[{name}] {st['status']}{step} {st.get('progress', 0)} %"
            if line != last:
                print(line)
                last = line
            if st["status"] in ("done", "failed", "cancelled"):
                break
            time.sleep(3)
        if st["status"] == "done":
            data, _ = call(f"{base}/videos/{jid}/file", key)
            dest = out / f"{name}.mp4"
            dest.write_bytes(data)
            print(f"[ok] {dest}  ({st.get('duration')} s)")
        else:
            print(f"[échec] {name} : {st.get('error')}")


if __name__ == "__main__":
    main()
