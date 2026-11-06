#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pasada 2 — Asignación de productos canónicos (re-ejecutable, idempotente).
==========================================================================
Puebla `hist_productos_canonicos` y setea `hist_items.producto_canonico_id`
para los productos que tenemos CURADOS/confirmados. Es incremental: lo que no
matchea ningún canónico queda con producto_canonico_id = NULL y el dashboard lo
agrupa provisionalmente por UNSPSC (ver app/src/lib/historico.ts productoKey()).

Diseño:
  * Cada canónico es una ENTRADA del REGISTRO: nombre, categoría, unspsc de
    referencia, y un MATCHER declarativo sobre la descripción cruda.
  * El matcher usa condiciones AND de grupos OR de substrings (case-insensitive,
    sin tildes), con una lista de EXCLUSIONES. Esto resuelve el entity-resolution
    CROSS-CATEGORÍA: un mismo bien partido en varios UNSPSC colapsa a 1.
  * Re-ejecutable: en cada corrida (1) upsert del canónico por nombre, (2) toma
    TODAS las descripciones de hist_items que matchean, (3) setea su
    producto_canonico_id. Corre al final de cada scrapeo y absorbe filas nuevas.

Correr (desde monitor/):
  ../scraper/venv/bin/python asignar_canonicos.py            # aplica
  ../scraper/venv/bin/python asignar_canonicos.py --dry-run  # solo muestra qué haría
"""
import os
import re
import sys
import json
import argparse
import unicodedata
import urllib.request
import urllib.parse
from collections import Counter

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

U = os.environ["SUPABASE_URL"].rstrip("/")
K = os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}


# ─────────────────────────── REGISTRO DE CANÓNICOS ───────────────────────────
# matcher: {"all": [[op1,op2,...], ...], "any": [ <matcher>, ... ], "none": [exc1, ...]}
#   - "all": lista de GRUPOS; cada grupo es una lista de alternativas (OR).
#     El ítem matchea si en CADA grupo aparece al menos una alternativa.
#   - "any": lista de SUB-MATCHERS; matchea si CUALQUIERA de ellos matchea
#     (OR a nivel tope — p.ej. "código de modelo" O "atributos descriptivos").
#   - "none": si aparece cualquiera de estos, NO matchea.
# Todo se compara sobre la descripción normalizada (minúsculas, sin tildes).
REGISTRO = [
    {
        "nombre": "Etiqueta/rollo continuo autoadhesivo Brother DK-2205 62mm × 30.48m",
        "categoria": "Consumibles de impresión",
        "unspsc": "55121606",
        # DK-2205 es un SKU único (solo existe en 62mm × 30.48m): el código de
        # modelo por sí solo lo identifica. Si no está el modelo, se exige el
        # combo autoadhesiva + 62 + 30.48 para no arrastrar otras etiquetas.
        "matcher": {
            "any": [
                {"all": [["dk 2205", "dk2205", "dk-2205", "dk 220", "dk220"]]},
                {"all": [
                    ["autoadhes"],
                    ["62"],
                    ["30.4", "30,4", "30.48", "30,48"],
                ]},
            ],
        },
    },
]


# ─────────────────────────────── utilidades ─────────────────────────────────
def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", s).strip()


def matchea(desc_norm, m):
    if "any" in m:
        if not any(matchea(desc_norm, sub) for sub in m["any"]):
            return False
    for grupo in m.get("all", []):
        if not any(alt in desc_norm for alt in grupo):
            return False
    for exc in m.get("none", []):
        if exc in desc_norm:
            return False
    return True


def _get(path):
    r = urllib.request.Request(f"{U}/rest/v1/{path}", headers=H)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read()), resp.headers


def _req(method, path, body=None, extra=None):
    data = json.dumps(body).encode() if body is not None else None
    h = dict(H)
    if extra:
        h.update(extra)
    r = urllib.request.Request(f"{U}/rest/v1/{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read()
        return (json.loads(raw) if raw else None), resp.headers


def leer_items():
    """Todas las descripciones + id de hist_items (paginado)."""
    out, off = [], 0
    while True:
        rows, _ = _get(f"hist_items?select=id,descripcion,unspsc_codigo&limit=1000&offset={off}")
        if not rows:
            break
        out.extend(rows)
        off += 1000
        if len(rows) < 1000:
            break
    return out


def upsert_canonico(entry):
    """Devuelve el id del canónico (lo crea si no existe, por nombre)."""
    q = urllib.parse.quote(entry["nombre"])
    rows, _ = _get(f"hist_productos_canonicos?select=id&nombre_canonico=eq.{q}")
    if rows:
        return rows[0]["id"]
    body = {"nombre_canonico": entry["nombre"], "categoria": entry["categoria"],
            "unspsc_codigo": entry["unspsc"]}
    res, _ = _req("POST", "hist_productos_canonicos", body,
                  extra={"Prefer": "return=representation"})
    return res[0]["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    items = leer_items()
    print(f"→ {len(items)} filas hist_items leídas", flush=True)

    for entry in REGISTRO:
        matched = [it for it in items if matchea(norm(it["descripcion"]), entry["matcher"])]
        ids = [it["id"] for it in matched]
        unspsc = Counter(it["unspsc_codigo"] for it in matched if it["unspsc_codigo"])
        print(f"\n■ {entry['nombre']}")
        print(f"   matchea {len(ids)} ítems · UNSPSC presentes: {dict(unspsc)}")
        muestra = sorted({it['descripcion'].strip() for it in matched})[:6]
        for d in muestra:
            print(f"     · {d[:110]}")
        if args.dry_run or not ids:
            continue
        cid = upsert_canonico(entry)
        # asignar en bloques (PATCH con filtro id=in.())
        for i in range(0, len(ids), 200):
            chunk = ids[i:i + 200]
            flt = "id=in.(" + ",".join(str(x) for x in chunk) + ")"
            _req("PATCH", f"hist_items?{flt}", {"producto_canonico_id": cid},
                 extra={"Prefer": "return=minimal"})
        # recalcular n_items del canónico
        _req("PATCH", f"hist_productos_canonicos?id=eq.{cid}",
             {"n_items": len(ids)}, extra={"Prefer": "return=minimal"})
        print(f"   ✓ canónico id={cid} · {len(ids)} ítems asignados")

    print("\nListo." + ("  (dry-run, no se escribió nada)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
