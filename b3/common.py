"""
common.py — utilidades compartilhadas da frente B3 small caps.

Paths, conexão SQLite (b3/data/b3.db), GET HTTP com retry + cache em disco + pausa educada,
e o encoding base64 que os endpoints públicos da B3 (sistemaswebb3-listados) exigem.
"""

import base64
import json
import os
import sqlite3
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
DB_PATH = os.path.join(DATA, "b3.db")
REPORTS = os.path.join(HERE, "reports")
os.makedirs(RAW, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (research; read-only)"}
B3_LISTED = "https://sistemaswebb3-listados.b3.com.br"


def db():
    con = sqlite3.connect(DB_PATH, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def b3_b64(params: dict) -> str:
    return base64.b64encode(json.dumps(params).encode()).decode()


_last_call = {}


def http_get(url, *, pause=0.4, retries=4, timeout=60, stream=False, host_key=None):
    """GET com retry exponencial e pausa mínima por host (rate limit educado)."""
    key = host_key or url.split("/")[2]
    wait = pause - (time.time() - _last_call.get(key, 0))
    if wait > 0:
        time.sleep(wait)
    err = None
    for i in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout, stream=stream)
            _last_call[key] = time.time()
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return r
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = repr(e)
        time.sleep(2 ** i)
    raise RuntimeError(f"GET failed {url}: {err}")


def b3_json(path, params, cache_name=None, max_age_h=24 * 7, pause=0.4):
    """Chama endpoint B3 (base64) com cache em data/raw/b3api/<cache_name>.json."""
    cache = None
    if cache_name:
        cache = os.path.join(RAW, "b3api", cache_name + ".json")
        if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < max_age_h * 3600:
            with open(cache, encoding="utf-8") as f:
                return json.load(f)
    r = http_get(f"{B3_LISTED}/{path}/{b3_b64(params)}", pause=pause)
    r.encoding = "utf-8"
    data = r.json() if r.status_code == 200 and r.text.strip() else None
    if cache and data is not None:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    return data


def br_num(s):
    """'3.481.513,58' -> 3481513.58 ; '' -> None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    return float(s.replace(".", "").replace(",", "."))


def br_date(s):
    """'30/12/2025' -> '2025-12-30'."""
    if not s or len(s) < 10 or s.startswith("31/12/9999"):
        return None
    d, m, y = s[:10].split("/")
    return f"{y}-{m}-{d}"
