#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FASE 2C — merge por CÓDIGO EXPLÍCITO de consumible (seguro, sin inferir modelo).
Extrae de la descripción representativa los códigos reales (Brother TN/DR, HP CF/CE/CB/Q,
Lexmark 56F4000-like, Samsung MLT, Kyocera TK, Canon GPR/NPG/C-EXV) normalizados, y fusiona
claves de la MISMA familia que comparten >=1 código. union-find. Dry-run por defecto.
Emite scratchpad/fase2_2c_map.json = {clave: clave_canonica}.
  dry:   scraper/venv/bin/python scratchpad/fase2_2c.py
"""
import json, re
from collections import defaultdict, Counter
SP = "/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
src = open(SP + "/recablear_v3.py").read()
ns = {}
exec(src.split("# ================== CARGA")[0], ns)
_get = ns["_get"]; clave_det = ns["clave_det"]; firma = ns["firma"]; SKU_FAMS = ns["SKU_FAMS"]

# ---- extractor de códigos de consumible ----
CODE_RX = [
    (re.compile(r'\bTN[\s\-]?(\d{2,4})\b', re.I), lambda m: "tn" + m.group(1)),           # Brother toner
    (re.compile(r'\bDR[\s\-]?(\d{2,4})\b', re.I), lambda m: "dr" + m.group(1)),           # Brother drum
    (re.compile(r'\b(CF|CE|CB)\s?(\d{3})\s?([AX])\b', re.I), lambda m: (m.group(1)+m.group(2)+m.group(3)).lower()),  # HP CFxxxA
    (re.compile(r'\bQ\s?(\d{4})\s?([AX])\b', re.I), lambda m: "q"+m.group(1)+m.group(2).lower()),                    # HP Qxxxx
    (re.compile(r'\b(\d{2}[A-Z]\d[A-Z]?\d{2,3})\b'), lambda m: m.group(1).lower()),       # Lexmark 56F4000 / 58D4H00
    (re.compile(r'\bMLT[\s\-]?(D\d{3}[A-Z]?)\b', re.I), lambda m: "mlt"+m.group(1).lower()),  # Samsung
    (re.compile(r'\bTK[\s\-]?(\d{3,4})\b', re.I), lambda m: "tk"+m.group(1)),             # Kyocera
    (re.compile(r'\b(GPR|NPG)[\s\-]?(\d{1,3})\b', re.I), lambda m: (m.group(1)+m.group(2)).lower()),  # Canon
    (re.compile(r'\bC[\s\-]?EXV\s?(\d{1,3})\b', re.I), lambda m: "cexv"+m.group(1)),      # Canon C-EXV
]
DRUM_RX = re.compile(r'\bDR[\s\-]?\d{2,4}\b', re.I)
def codigos(desc):
    out = set()
    for rx, fn in CODE_RX:
        for m in rx.finditer(desc or ""):
            out.add(fn(m))
    return out
def es_drum(desc):
    d = (desc or "").lower()
    return ('drum' in d or 'tambor' in d or 'cilindro' in d) and 'toner' not in d and 'tóner' not in d
def color(desc):
    d = (desc or "").lower()
    if re.search(r'\b(cyan|cian)\b', d): return 'cyan'
    if 'magenta' in d: return 'magenta'
    if re.search(r'\b(amarillo|yellow)\b', d): return 'amarillo'
    return 'negro'   # negro/black/sin color -> base

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

# ---- código representativo por clave final ----
clave_codes = {}; clave_fam = {}; clave_n = {}; clave_ej = {}; clave_color = {}; clave_drum = {}
for clave, its in final.items():
    fam = clave.split("|")[0]
    rep = Counter(i["descripcion"] for i in its).most_common(1)[0][0]
    cs = set()
    for it in its: cs |= codigos(it["descripcion"])
    clave_codes[clave] = cs; clave_fam[clave] = fam; clave_n[clave] = len(its)
    clave_ej[clave] = rep[:85]
    clave_color[clave] = color(rep)
    clave_drum[clave] = es_drum(rep)

# ---- union-find: fusionar claves de misma familia que comparten código ----
parent = {k: k for k in final}
def find(x):
    while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb:
        # el canónico será el de más items (se resuelve al final)
        parent[rb] = ra

# indexar por (familia, drum?, color, codigo) -> claves. Guardas:
#  - color separa negro/cyan/magenta/amarillo (TN-217 BK vs Y son productos distintos)
#  - drum separa cilindros (DR) de tóner aunque compartan modelo
by_code = defaultdict(list)
for k, cs in clave_codes.items():
    for c in cs:
        if c.startswith("dr") and not clave_drum[k]:
            continue   # un tóner que menciona su drum compatible NO debe unir por el código DR
        by_code[(clave_fam[k], clave_drum[k], clave_color[k], c)].append(k)
for key, ks in by_code.items():
    if len(ks) > 1:
        base = ks[0]
        for k in ks[1:]: union(base, k)

# resolver: para cada componente, canónica = clave con más items
comp = defaultdict(list)
for k in final: comp[find(k)].append(k)
mapping = {}  # clave -> clave_canonica
fusiones = []
for r, ks in comp.items():
    if len(ks) == 1: continue
    canon = max(ks, key=lambda k: clave_n[k])
    for k in ks: mapping[k] = canon
    fusiones.append((clave_fam[canon], sum(clave_n[k] for k in ks), [(clave_n[k], clave_ej[k]) for k in sorted(ks, key=lambda k:-clave_n[k])]))

# ---- SEGURIDAD: ¿alguna fusión mezcla familias? (no debería; es within-family) ----
def famword(s):
    s = (s or '').lower()
    for w in ['cinta','toner','tóner','tinta','papel','tambor','drum','memoria']:
        if w in s: return 'toner' if w == 'tóner' else w
    return (re.sub(r'[^a-záéíóú ]', ' ', s).split() or [''])[0]
mezcla = 0; mezcla_color = 0
for r, ks in comp.items():
    if len(ks) < 2: continue
    fws = set(); cols = set()
    for k in ks:
        cols.add(clave_color[k])
        for it in final[k]: fws.add(famword(it["descripcion"]))
    if len(fws) > 1: mezcla += 1
    if len(cols) > 1: mezcla_color += 1

print(f"claves finales (post 2A): {len(final)}")
print(f"componentes fusionados (>=2 claves): {len(fusiones)} | claves absorbidas: {sum(len(v)-1 for v in comp.values() if len(v)>1)}")
print(f"SEGURIDAD mezcla-familia: {mezcla} | mezcla-color: {mezcla_color} (ambos deben ser 0)")
print("\nTop 18 fusiones (familia | items | claves unidas):")
for fam, n, members in sorted(fusiones, key=lambda x:-x[1])[:18]:
    print(f"\n  [{fam}] {n} items, {len(members)} claves:")
    for cn, ej in members[:5]:
        print(f"      n={cn:>3} | {ej}")

json.dump(mapping, open(SP + "/fase2_2c_map.json", "w"), ensure_ascii=False, indent=1)
print(f"\nmapping escrito: scratchpad/fase2_2c_map.json ({len(mapping)} claves -> canónica)")
