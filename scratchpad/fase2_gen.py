#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FASE 2 — generador de candidatos de consolidación semántica.
Reusa el keying de recablear_v3 (pre-keyer + 2A) sobre hist_items EN VIVO y
agrupa las claves finales por familia. Emite scratchpad/fase2_candidatos.json:
  {familia: [{clave, n_items, ejemplo, ids_n}], ...}  (solo familias con >1 clave)
Esto es el sustrato que Opus revisa para fusionar claves del MISMO producto.
"""
import json, re
from collections import defaultdict, Counter
SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
# cargar funciones de keying del script de Fase 1 (sin ejecutar la parte de escritura)
src = open(SP + "/recablear_v3.py").read()
ns = {}
exec(src.split("# ================== CARGA")[0], ns)
_get = ns["_get"]; clave_det = ns["clave_det"]; firma = ns["firma"]; SKU_FAMS = ns["SKU_FAMS"]; nombre = ns["nombre"]

items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,descripcion&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break

for it in items:
    it["_c"] = clave_det(it["descripcion"]) or "sin_clave"
buckets = defaultdict(list)
for it in items:
    buckets[it["_c"]].append(it)
# 2A remap
p2 = defaultdict(list)
for k in buckets:
    if k != "sin_clave": p2[k.split("|")[0]].append(k)
remap = {}
for fam, cl in p2.items():
    if fam not in SKU_FAMS or len(cl) < 2: continue
    byf = defaultdict(list)
    for k in cl:
        s = firma(k)
        if len(s[1]) > 0: byf[s].append(k)
    for s, g in byf.items():
        if len(g) > 1:
            c = min(g, key=len)
            for k in g: remap[k] = c
# clave final por item
final = defaultdict(list)
for k, its in buckets.items():
    if k == "sin_clave": continue
    final[remap.get(k, k)].extend(its)

# por familia, claves distintas
porfam = defaultdict(list)
for clave, its in final.items():
    fam = clave.split("|")[0]
    rep = Counter(i["descripcion"] for i in its).most_common(1)[0][0]
    porfam[fam].append({"clave": clave, "n_items": len(its), "ejemplo": nombre(rep)[:120],
                         "ids": [i["id"] for i in its]})

cand = {f: sorted(v, key=lambda x: -x["n_items"]) for f, v in porfam.items() if len(v) > 1}
json.dump(cand, open(SP + "/fase2_candidatos.json", "w"), ensure_ascii=False, indent=1)

# resumen
fams = sorted(cand.items(), key=lambda kv: -sum(x["n_items"] for x in kv[1]))
tot_claves = sum(len(v) for v in cand.values())
tot_items = sum(sum(x["n_items"] for x in v) for v in cand.values())
print(f"familias con >1 clave: {len(cand)} | claves totales en ellas: {tot_claves} | items: {tot_items}")
print("\nTop 15 familias por volumen (familia | #claves | #items):")
for f, v in fams[:15]:
    print(f"  {f:16} | {len(v):3} claves | {sum(x['n_items'] for x in v):4} items")
