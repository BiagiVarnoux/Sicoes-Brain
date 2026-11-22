#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIAGNÓSTICO GLOBAL — ¿cuánto producto está PARTIDO en todos los datos?
Reusa el keying de recablear_v3 (pre-keyer + 2A + 2C) sobre hist_items EN VIVO,
calcula la clave_final de cada item y extrae CÓDIGOS FUERTES (part-numbers) de la
descripción. Luego mide dos patologías del problema de fondo:

  (1) SILO POR FAMILIA  — un mismo código fuerte aparece en >=2 familias distintas
                          (mismo producto catalogado bajo UNSPSC distintos -> nunca se une)
  (2) PARTICIÓN          — un mismo código fuerte cae en >=2 claves_final distintas
                          (mismo producto, varias claves por redacción/dimensión)

No escribe nada. Solo mide e imprime, para diseñar el fix (2E) con guardas.
  scraper/venv/bin/python scratchpad/fase2_diag.py
"""
import json, re
from collections import defaultdict, Counter
SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
src = open(SP + "/recablear_v3.py").read()
ns = {}
exec(src.split("# ================== CARGA")[0], ns)
_get = ns["_get"]; clave_det = ns["clave_det"]; firma = ns["firma"]; SKU_FAMS = ns["SKU_FAMS"]; nombre = ns["nombre"]
norm = ns["norm"]

# ---------- extractor de CÓDIGO FUERTE (part-number) genérico ----------
# un código fuerte = prefijo alfabético de serie + dígitos (+ sufijo), inequívoco.
# incluye el patrón Lexmark (dígito-primero) y el alfanumérico clásico.
STOP_ALPHA = {'para','con','por','ser','serie','mod','modelo','tipo','color','marca','num','nro',
              'cod','ref','med','medida','cm','mm','mt','mts','ml','kg','gr','ghz','mhz','hz','rpm',
              'dpi','ppm','ver','rev','max','min','art','item','lote','und','pza','paq','caja'}
GENERIC = re.compile(r'\b([a-z]{2,5})[\s\-]?(\d{2,5})([a-z]{0,2})\b', re.I)
LEX     = re.compile(r'\b(\d{2}[a-z]\d[a-z]?\d{2,3})\b', re.I)
ALNUM_HY= re.compile(r'\b([a-z]{1,4}\-\d{2,5}[a-z]?)\b', re.I)  # tn-3479, dk-2205, mlt-d101
def codigos_fuertes(desc):
    d = desc or ""
    out = set()
    for m in LEX.finditer(d):
        out.add(m.group(1).lower())
    for m in GENERIC.finditer(d):
        pre = m.group(1).lower()
        if pre in STOP_ALPHA: continue
        out.add(pre + m.group(2) + (m.group(3) or "").lower())
    return out

def color(desc):
    dd = (desc or "").lower()
    if re.search(r'\b(cyan|cian)\b', dd): return 'cyan'
    if 'magenta' in dd: return 'magenta'
    if re.search(r'\b(amarillo|yellow)\b', dd): return 'amarillo'
    return 'negro'

# ---------- reconstruir clave_final por item (igual que el pipeline) ----------
items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,descripcion,unspsc_codigo&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break
print(f"hist_items: {len(items)}")

# reconstruir remap (2A) + map2c (2C), igual que recablear_v3 en su sección CARGA
for it in items:
    it["_k"] = clave_det(it["descripcion"]) or "sin_clave"
buckets = defaultdict(list)
for it in items: buckets[it["_k"]].append(it)
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
import os as _os
map2c = {}
_f2c = SP + "/fase2_2c_map.json"
if _os.path.exists(_f2c): map2c = json.load(open(_f2c))
def clave_final(k):
    k2 = remap.get(k, k)
    return map2c.get(k2, k2)

for it in items:
    k = it["_k"]
    it["_cf"] = "sin_clave" if k == "sin_clave" else clave_final(k)
    it["_fam"] = it["_cf"].split("|")[0] if it["_cf"] != "sin_clave" else "sin_clave"

# ---------- índice: código fuerte -> {familias, claves, items, ejemplos, colores} ----------
code_fams  = defaultdict(set)
code_claves= defaultdict(set)
code_items = defaultdict(list)
code_ej    = {}
code_cols  = defaultdict(set)
for it in items:
    cs = codigos_fuertes(it["descripcion"])
    for c in cs:
        code_fams[c].add(it["_fam"])
        code_claves[c].add(it["_cf"])
        code_items[c].append(it["id"])
        code_cols[c].add(color(it["descripcion"]))
        if c not in code_ej: code_ej[c] = nombre(it["descripcion"])[:95]

# ---------- (1) SILO POR FAMILIA ----------
silo = {c: fams for c, fams in code_fams.items() if len(fams) >= 2}
silo_items = sum(len(code_items[c]) for c in silo)
# ---------- (2) PARTICIÓN (misma-code, varias claves) ----------
part = {c: cl for c, cl in code_claves.items() if len(cl) >= 2}
part_items = sum(len(code_items[c]) for c in part)
# color-safe: de los silos, cuántos son monocolor (fusión directa segura)
silo_mono = {c: f for c, f in silo.items() if len(code_cols[c]) == 1}

print("\n==== PROBLEMA DE FONDO (medido sobre códigos fuertes) ====")
print(f"códigos fuertes distintos: {len(code_fams)}")
print(f"(1) SILO por familia  : {len(silo)} códigos en >=2 familias  -> {silo_items} items afectados")
print(f"    de esos, MONOCOLOR : {len(silo_mono)} códigos (fusión cross-familia directa y segura)")
print(f"(2) PARTICIÓN          : {len(part)} códigos en >=2 claves    -> {part_items} items afectados")

print("\n==== TOP 25 códigos partidos en MÁS familias (los peores) ====")
for c in sorted(silo, key=lambda c: (-len(code_fams[c]), -len(code_items[c])))[:25]:
    fams = sorted(code_fams[c])
    print(f"\n  [{c}]  {len(code_fams[c])} familias, {len(code_items[c])} items, colores={sorted(code_cols[c])}")
    print(f"      fams: {fams}")
    print(f"      ej:   {code_ej[c]}")

# volcar para diseñar el fix
dump = {c: {"familias": sorted(code_fams[c]), "n_claves": len(code_claves[c]),
            "n_items": len(code_items[c]), "colores": sorted(code_cols[c]),
            "ejemplo": code_ej[c]} for c in silo}
json.dump(dump, open(SP + "/fase2_diag_silos.json", "w"), ensure_ascii=False, indent=1)
print(f"\nvolcado: scratchpad/fase2_diag_silos.json ({len(dump)} códigos en silo)")
