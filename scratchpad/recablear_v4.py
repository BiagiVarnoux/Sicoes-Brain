#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RECABLEADO v4 — FIRMA ESTRUCTURADA (consumibles) + pipeline viejo (resto).

Clave de cada item:
  · si firma() de fase3 devuelve algo (consumible con id fuerte) -> group_key = "firma:"+firma
  · si no -> fallback al pipeline v3 (clave_det + 2A + 2E), idéntico a hoy
Reconstrucción limpia idempotente (NULL + DELETE + recrear por id), igual que v3.

Arregla de raíz: la familia ya NO depende de la 1ª palabra (= etiqueta UNSPSC mal puesta por
las entidades); el ruido ('ORIGINAL','COLOR NEGRO', plural, orden) deja de partir productos.
Commodities sin id (papel bond, clips) quedan en el pipeline viejo (no se tocan).

  dry:     scraper/venv/bin/python scratchpad/recablear_v4.py
  aplicar: scraper/venv/bin/python scratchpad/recablear_v4.py --write
"""
import os, sys, json, argparse, re
from collections import defaultdict, Counter
SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"

# --- reusar funciones de v3 (fallback) ---
ns3 = {}
exec(open(SP + "/recablear_v3.py").read().split("# ================== CARGA")[0], ns3)
_get = ns3["_get"]; _req = ns3["_req"]; clave_det = ns3["clave_det"]
firma2a = ns3["firma"]; SKU_FAMS = ns3["SKU_FAMS"]; nombre = ns3["nombre"]

# --- reusar firma estructurada de fase3 ---
nsf = {}
exec(open(SP + "/fase3_firma.py").read().split("# ====== MAIN")[0], nsf)
firma_estruct = nsf["firma"]

# --- cargar items ---
print("Leyendo hist_items…", flush=True)
items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,descripcion,unspsc_codigo&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break
print(f"  hist_items: {len(items)}", flush=True)

# --- fallback: reconstruir remap(2A) + map2e sobre las claves de los items SIN firma ---
for it in items:
    it["_fe"] = firma_estruct(it["descripcion"])          # firma estructurada o None
    it["_cd"] = clave_det(it["descripcion"]) or "sin_clave"
buckets = defaultdict(list)
for it in items:
    if it["_fe"] is None: buckets[it["_cd"]].append(it)
p2 = defaultdict(list)
for k in buckets:
    if k != "sin_clave": p2[k.split("|")[0]].append(k)
remap = {}
for fam, cl in p2.items():
    if fam not in SKU_FAMS or len(cl) < 2: continue
    byf = defaultdict(list)
    for k in cl:
        s = firma2a(k)
        if len(s[1]) > 0: byf[s].append(k)
    for s, g in byf.items():
        if len(g) > 1:
            c = min(g, key=len)
            for k in g: remap[k] = c
map2e = {}
_f2e = SP + "/fase2_2e_map.json"
if os.path.exists(_f2e): map2e = json.load(open(_f2e))
def fallback_key(k):
    k2 = remap.get(k, k)
    return "fb:" + map2e.get(k2, k2)

# --- group_key por item ---
grupos = defaultdict(list)
for it in items:
    if it["_fe"] is not None:
        grupos["firma:" + it["_fe"]].extend([it])
    else:
        if it["_cd"] == "sin_clave": continue
        grupos[fallback_key(it["_cd"])].append(it)
clusters = {c: v for c, v in grupos.items() if len(v) >= 2}
en_cluster = sum(len(v) for v in clusters.values())
n_firma = sum(1 for c in clusters if c.startswith("firma:"))
print(f"grupos>=2: {len(clusters)} ({n_firma} por firma, {len(clusters)-n_firma} fallback) | "
      f"items en cluster: {en_cluster} ({100*en_cluster/len(items):.1f}%)", flush=True)

# --- info grupo ---
def info_grupo(its):
    rep = Counter(i["descripcion"] for i in its).most_common(1)[0][0]
    uns = Counter(i.get("unspsc_codigo") for i in its if i.get("unspsc_codigo")).most_common(1)
    return nombre(rep), uns[0][0] if uns else None
def categoria(c):
    if c.startswith("firma:"): return c.split(":",1)[1].split("|")[0]
    return c.split(":",1)[1].split("|")[0]

ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
if not A.write:
    print("\nDRY-RUN. 12 grupos más grandes:")
    for c in sorted(clusters, key=lambda c: -len(clusters[c]))[:12]:
        nm, _ = info_grupo(clusters[c])
        print(f"  [{len(clusters[c]):>3}] {c.split(':',1)[1][:34]:34} | {nm[:60]}")
    print("\n(usar --write para aplicar)")
    sys.exit(0)

# ================== ESCRITURA (reconstrucción limpia, idéntica a v3) ==================
print("\n--write: reconstruyendo canónicos desde cero…", flush=True)
_req("PATCH", "hist_items?producto_canonico_id=not.is.null", {"producto_canonico_id": None}, extra={"Prefer": "return=minimal"})
print("  · hist_items.producto_canonico_id -> NULL", flush=True)
_req("DELETE", "hist_productos_canonicos?id=gte.0", extra={"Prefer": "return=minimal"})
print("  · hist_productos_canonicos vaciada", flush=True)

usados = {}; filas = []; meta = []
for c, its in clusters.items():
    nm, uns = info_grupo(its)
    base = nm; n = 2
    while nm in usados: nm = f"{base} ({n})"; n += 1
    usados[nm] = True
    ids = [it["id"] for it in its]
    filas.append({"nombre_canonico": nm, "categoria": categoria(c), "unspsc_codigo": uns, "n_items": len(ids)})
    meta.append((nm, ids))
nombre2id = {}
for i in range(0, len(filas), 500):
    res = _req("POST", "hist_productos_canonicos", filas[i:i+500], extra={"Prefer": "return=representation"})
    for row in res: nombre2id[row["nombre_canonico"]] = row["id"]
print(f"  · {len(nombre2id)} canónicos creados", flush=True)
asignados = 0
for nm, ids in meta:
    cid = nombre2id[nm]
    for j in range(0, len(ids), 200):
        flt = "id=in.(" + ",".join(str(x) for x in ids[j:j+200]) + ")"
        _req("PATCH", f"hist_items?{flt}", {"producto_canonico_id": cid}, extra={"Prefer": "return=minimal"})
    asignados += len(ids)
print(f"\nLISTO v4. canónicos: {len(nombre2id)} | hist_items asignados: {asignados}", flush=True)
