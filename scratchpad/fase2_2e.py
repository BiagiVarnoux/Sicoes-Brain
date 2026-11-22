#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FASE 2E — consolidación CROSS-FAMILIA por CÓDIGO FUERTE de producto (SUPERSET de 2C).

El problema de fondo (medido en fase2_diag): un MISMO producto queda partido porque
(a) SICOES/las descripciones lo catalogan bajo sustantivos distintos -> familias distintas,
(b) la redacción varía. 2C ya fusiona por código REAL de consumible, pero SOLO dentro de la
misma familia. 2E hace lo mismo SIN la restricción de familia, usando exclusivamente un
REGISTRO EXPLÍCITO de part-numbers (nunca tokens genéricos ni modelos de impresora), de modo
que el diagnóstico demostró-garbage ("de100", "hojas100", "ms321") queda fuera por construcción.

Guardas (idénticas a 2C + cross-familia):
  · solo códigos del registro (SKU del consumible), jamás modelo de impresora ni "de<n>"
  · color en la llave de unión (TN-217 BK/C/M/Y no se mezclan)
  · drum/tambor separado de tóner (los códigos DR no unen tóner)
  · reporte de SEGURIDAD: para cada componente, los product-type words que abarca (ojo humano)

Emite scratchpad/fase2_2e_map.json = {clave: clave_canonica}. Dry-run por defecto.
  dry:  scraper/venv/bin/python scratchpad/fase2_2e.py
"""
import json, re
from collections import defaultdict, Counter
SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
src = open(SP + "/recablear_v3.py").read()
ns = {}
exec(src.split("# ================== CARGA")[0], ns)
_get = ns["_get"]; clave_det = ns["clave_det"]; firma = ns["firma"]; SKU_FAMS = ns["SKU_FAMS"]; nombre = ns["nombre"]

# ---- REGISTRO de códigos (2C) + extensión etiquetas/otros ----
CODE_RX = [
    (re.compile(r'\bTN[\s\-]?(\d{2,4})\b', re.I), lambda m: "tn" + m.group(1)),
    (re.compile(r'\bDR[\s\-]?(\d{2,4})\b', re.I), lambda m: "dr" + m.group(1)),
    (re.compile(r'\b(CF|CE|CB)\s?(\d{3})\s?([AX])\b', re.I), lambda m: (m.group(1)+m.group(2)+m.group(3)).lower()),
    (re.compile(r'\bQ\s?(\d{4})\s?([AX])\b', re.I), lambda m: "q"+m.group(1)+m.group(2).lower()),
    (re.compile(r'\b(\d{2}[A-Z]\d[A-Z]?\d{2,3})\b'), lambda m: m.group(1).lower()),   # Lexmark 56F4000
    (re.compile(r'\bMLT[\s\-]?(D\d{3}[A-Z]?)\b', re.I), lambda m: "mlt"+m.group(1).lower()),
    (re.compile(r'\bTK[\s\-]?(\d{3,4})\b', re.I), lambda m: "tk"+m.group(1)),
    (re.compile(r'\b(GPR|NPG)[\s\-]?(\d{1,3})\b', re.I), lambda m: (m.group(1)+m.group(2)).lower()),
    (re.compile(r'\bC[\s\-]?EXV\s?(\d{1,3})\b', re.I), lambda m: "cexv"+m.group(1)),
    # --- EXTENSIÓN 2E ---
    (re.compile(r'\bDK[\s\-]?(\d{4})\b', re.I), lambda m: "dk"+m.group(1)),           # Brother etiquetas DK-2205
    (re.compile(r'\bLC[\s\-]?(\d{2,4})\b', re.I), lambda m: "lc"+m.group(1)),         # Brother tinta LC-xxx
    (re.compile(r'\bGI[\s\-]?(\d{2,3})\b', re.I), lambda m: "gi"+m.group(1)),         # Canon tinta GI-xxx
    (re.compile(r'\bT[\s\-]?0?(\d{3})\b', re.I), lambda m: "t"+m.group(1)),           # Epson tinta Txxx (cuida: ver guard)
    (re.compile(r'\bS0?15[\s\-]?(\d{3})\b', re.I), lambda m: "s015"+m.group(1)),      # Epson cinta S015xxx
]
# nota: el patrón Epson Txxx es amplio; su guarda es el color + que SOLO une si cae en >=2 claves reales.
DRUM_RX = re.compile(r'\bDR[\s\-]?\d{2,4}\b', re.I)
def codigos(desc):
    out = set()
    for rx, fn in CODE_RX:
        for m in rx.finditer(desc or ""): out.add(fn(m))
    return out
def es_drum(desc):
    d = (desc or "").lower()
    return ('drum' in d or 'tambor' in d or 'cilindro' in d or 'unidad de imagen' in d) and 'toner' not in d and 'tóner' not in d
def color(desc):
    d = (desc or "").lower()
    if re.search(r'\b(cyan|cian)\b', d): return 'cyan'
    if 'magenta' in d: return 'magenta'
    if re.search(r'\b(amarillo|yellow)\b', d): return 'amarillo'
    return 'negro'

# ---- reconstruir claves finales (pre-keyer + 2A), igual que recablear_v3 ----
items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,descripcion&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break
for it in items: it["_c"] = clave_det(it["descripcion"]) or "sin_clave"
buckets = defaultdict(list)
for it in items: buckets[it["_c"]].append(it)
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
final = defaultdict(list)
for k, its in buckets.items():
    if k == "sin_clave": continue
    final[remap.get(k, k)].extend(its)

# ---- código/color/drum/familia por clave final ----
clave_codes={}; clave_fam={}; clave_n={}; clave_ej={}; clave_color={}; clave_drum={}
for clave, its in final.items():
    rep = Counter(i["descripcion"] for i in its).most_common(1)[0][0]
    cs = set()
    for it in its: cs |= codigos(it["descripcion"])
    clave_codes[clave]=cs; clave_fam[clave]=clave.split("|")[0]; clave_n[clave]=len(its)
    clave_ej[clave]=nombre(rep)[:90]; clave_color[clave]=color(rep); clave_drum[clave]=es_drum(rep)

# ---- union-find CROSS-FAMILIA por (drum, color, codigo) — SIN familia ----
parent={k:k for k in final}
def find(x):
    while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
    return x
def union(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: parent[rb]=ra
by_code=defaultdict(list)
for k,cs in clave_codes.items():
    for c in cs:
        if c.startswith("dr") and not clave_drum[k]: continue   # tóner no une por código de su drum
        by_code[(clave_drum[k], clave_color[k], c)].append(k)   # <-- sin clave_fam: cross-familia
for key,ks in by_code.items():
    if len(ks)>1:
        base=ks[0]
        for k in ks[1:]: union(base,k)

comp=defaultdict(list)
for k in final: comp[find(k)].append(k)
mapping={}; fusiones=[]
for r,ks in comp.items():
    if len(ks)==1: continue
    canon=max(ks, key=lambda k: clave_n[k])
    for k in ks: mapping[k]=canon
    fusiones.append((clave_fam[canon], sum(clave_n[k] for k in ks),
                     sorted(set(clave_fam[k] for k in ks)),
                     [(clave_n[k], clave_fam[k], clave_ej[k]) for k in sorted(ks,key=lambda k:-clave_n[k])]))

# ---- SEGURIDAD: product-type words y color por componente ----
def famword(s):
    s=(s or '').lower()
    for w in ['cinta','toner','tóner','tinta','papel','tambor','drum','etiqueta','memoria']:
        if w in s: return 'toner' if w=='tóner' else w
    return (re.sub(r'[^a-záéíóú ]',' ',s).split() or [''])[0]
mezcla_color=0; cross_fam=0
for r,ks in comp.items():
    if len(ks)<2: continue
    if len(set(clave_color[k] for k in ks))>1: mezcla_color+=1
    if len(set(clave_fam[k] for k in ks))>1: cross_fam+=1

nfus=len(fusiones); absorb=sum(len(v)-1 for v in comp.values() if len(v)>1)
print(f"claves finales (post 2A): {len(final)}")
print(f"componentes fusionados: {nfus} | claves absorbidas: {absorb}")
print(f"  de ellos CROSS-FAMILIA (lo nuevo de 2E vs 2C): {cross_fam}")
print(f"SEGURIDAD mezcla-color: {mezcla_color} (debe ser 0)")
print("\n==== CROSS-FAMILIA (lo que 2C NO podía unir y 2E sí) — todas ====")
for fam,n,fams,members in sorted((f for f in fusiones if len(f[2])>1), key=lambda x:-x[1]):
    print(f"\n  [{'+'.join(fams)}] {n} items, {len(members)} claves:")
    for cn,ff,ej in members[:6]:
        print(f"      n={cn:>3} [{ff}] {ej}")

json.dump(mapping, open(SP+"/fase2_2e_map.json","w"), ensure_ascii=False, indent=1)
print(f"\nmapping escrito: scratchpad/fase2_2e_map.json ({len(mapping)} claves -> canónica)")
