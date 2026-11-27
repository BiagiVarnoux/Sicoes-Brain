#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RECABLEADO v5 — FIRMA ESTRUCTURADA (SKU) + NORMALIZADOR GENERICO + singletons confiables.

Cambios sobre v4:
  1. El fallback (todo lo que no tiene firma SKU) agrupa con normalizador.clave (medidas,
     unidades y ruido normalizados) en vez de clave_det literal -> menos siloing.
  2. 'provisional' deja de significar "singleton": un item con CLAVE CONFIABLE recibe canonico
     aunque aparezca una sola vez. Solo queda provisional lo genuinamente vago (familia sola,
     sin atributos). El isProvisional del frontend lo refleja solo (key 'c:').

Confiable = firma SKU, o clave normalizada con familia + >=1 atributo fuerte
            (un atributo con digito -> medida/numero+unidad, o >=2 atributos de palabra).

Reconstruccion limpia idempotente (NULL + DELETE + recrear), igual que v4.
  dry:     scraper/venv/bin/python scratchpad/recablear_v5.py
  aplicar: scraper/venv/bin/python scratchpad/recablear_v5.py --write
"""
import os, sys, json, argparse
from collections import defaultdict, Counter
SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"

# reusar infra + nombre() de v3
ns3 = {}
exec(open(SP + "/recablear_v3.py").read().split("# ================== CARGA")[0], ns3)
_get = ns3["_get"]; _req = ns3["_req"]; nombre = ns3["nombre"]
# firma estructurada SKU de fase3
nsf = {}
exec(open(SP + "/fase3_firma.py").read().split("# ====== MAIN")[0], nsf)
firma_estruct = nsf["firma"]
# normalizador generico
nn = {}
exec(open(SP + "/normalizador.py").read().split("if __name__")[0], nn)
clave_norm = nn["clave"]

def key_conf(desc):
    """(group_key, confiable) o (None, False) si no hay ni familia."""
    fe = firma_estruct(desc)
    if fe:
        return "firma:" + fe, True
    fam, k = clave_norm(desc)
    if not k:
        return None, False
    attrs = k.split("|")[1:]
    fuerte = any(any(c.isdigit() for c in a) for a in attrs) or len(attrs) >= 2
    return "norm:" + k, fuerte

# --- cargar items ---
print("Leyendo hist_items…", flush=True)
items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,descripcion,unspsc_codigo&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break
print(f"  hist_items: {len(items)}", flush=True)

grupos = defaultdict(list); conf = {}
for it in items:
    k, c = key_conf(it["descripcion"])
    it["_k"] = k
    if k is None:
        continue
    grupos[k].append(it); conf[k] = c

# canonico si: grupo>=2 (cualquiera) o singleton confiable
clusters = {k: v for k, v in grupos.items() if len(v) >= 2 or conf.get(k)}
en_cluster = sum(len(v) for v in clusters.values())
prov = len(items) - en_cluster
n_firma = sum(1 for c in clusters if c.startswith("firma:"))
n_multi = sum(1 for c in clusters if len(clusters[c]) >= 2)
print(f"canonicos: {len(clusters)} ({n_multi} grupos>=2 + {len(clusters)-n_multi} singleton-confiable; "
      f"{n_firma} por firma SKU) | provisionales: {prov} ({100*prov//len(items)}%)", flush=True)

def info_grupo(its):
    rep = Counter(i["descripcion"] for i in its).most_common(1)[0][0]
    uns = Counter(i.get("unspsc_codigo") for i in its if i.get("unspsc_codigo")).most_common(1)
    return nombre(rep), (uns[0][0] if uns else None)
def categoria(c):
    return c.split(":", 1)[1].split("|")[0]

ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
if not A.write:
    print("\nDRY-RUN. 12 grupos (>=2) más grandes:")
    multi = [c for c in clusters if len(clusters[c]) >= 2]
    for c in sorted(multi, key=lambda c: -len(clusters[c]))[:12]:
        nm, _ = info_grupo(clusters[c])
        print(f"  [{len(clusters[c]):>3}] {c.split(':',1)[1][:34]:34} | {nm[:56]}")
    print("\n(usar --write para aplicar)")
    sys.exit(0)

# ================== ESCRITURA (reconstrucción limpia, idéntica a v4) ==================
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
print(f"\nLISTO v5. canónicos: {len(nombre2id)} | hist_items asignados: {asignados}", flush=True)
