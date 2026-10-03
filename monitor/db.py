"""
Capa Supabase para el radar — tabla `convocatorias_radar`.
Reutiliza el patrón de reintentos de red del scraper (no crashear por un blip).
"""
import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

TABLA = "convocatorias_radar"


def _headers(extra: dict = {}) -> dict:
    base = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    base.update(extra)
    return base


def _urlopen_retry(req, timeout: int = 20, intentos: int = 4):
    ultimo = None
    for i in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError:
            raise
        except Exception as e:
            ultimo = e
            espera = 2 ** i
            print(f"      ⚠ Supabase red falló ({type(e).__name__}); reintento {i+1}/{intentos} en {espera}s...",
                  flush=True)
            time.sleep(espera)
    raise ultimo


def cuces_existentes(cuces: list[str]) -> set:
    """Devuelve el subconjunto de CUCE que ya está en la tabla (para no re-procesar)."""
    if not cuces:
        return set()
    vistos = set()
    # consultar en bloques por si la lista es larga (límite de URL)
    for base in range(0, len(cuces), 100):
        trozo = cuces[base:base + 100]
        lista = ",".join(f'"{c}"' for c in trozo)
        path = f"{TABLA}?cuce=in.({lista})&select=cuce"
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
        try:
            _s, body = _urlopen_retry(req, timeout=15)
            for row in json.loads(body):
                vistos.add(row["cuce"])
        except Exception as e:
            print(f"      ⚠ No se pudo consultar existentes: {e}", flush=True)
    return vistos


def upsert(rows: list[dict]) -> dict:
    """Inserta/actualiza por CUCE. Devuelve {ok, count} o {error}."""
    if not rows:
        return {"ok": True, "count": 0}
    url = f"{SUPABASE_URL}/rest/v1/{TABLA}?on_conflict=cuce"
    req = urllib.request.Request(
        url, data=json.dumps(rows).encode(), method="POST",
        headers=_headers({"Prefer": "resolution=merge-duplicates,return=minimal"}),
    )
    try:
        status, _body = _urlopen_retry(req)
        return {"ok": True, "count": len(rows), "status": status}
    except urllib.error.HTTPError as e:
        try:
            cuerpo = e.read().decode()
        except Exception:
            cuerpo = f"HTTP {e.code} (cuerpo ilegible)"
        return {"error": cuerpo}
    except Exception as e:
        return {"error": f"red: {e}"}


def marcar_dbc(cuce: str, dbc_path: str, dbc_archivos: list | None = None) -> None:
    """Actualiza la ruta local y los archivos subidos (URLs) del DBC para un CUCE."""
    payload = {"dbc_path": dbc_path, "dbc_descargado": True}
    if dbc_archivos is not None:
        payload["dbc_archivos"] = dbc_archivos
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{TABLA}?cuce=eq.{urllib.parse.quote(cuce)}",
        data=json.dumps(payload).encode(),
        method="PATCH", headers=_headers(),
    )
    try:
        _urlopen_retry(req)
    except Exception as e:
        print(f"      ⚠ No se pudo marcar DBC de {cuce}: {e}", flush=True)
