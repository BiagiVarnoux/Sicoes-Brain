#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FASE 3 — agrupación por FIRMA ESTRUCTURADA (tipo·marca·id·color), robusta al ruido.

Causa de fondo (confirmada en vivo): descripcion = "{etiqueta UNSPSC} {desc real}", y la
etiqueta la ponen mal las entidades (una misma Cinta Epson LQ-590 catalogada bajo 'Cinta' o
'Tóner'). El keyer viejo (familia=1ª palabra + sopa de tokens) se parte por eso + por ruido
('ORIGINAL', 'COLOR NEGRO', plural). Fase 3 arma una FIRMA estructurada por ítem escaneando
TODO el texto y agrupa por ella; el ruido y la etiqueta mal puesta dejan de importar.

Alcance: SOLO consumibles identificables (cinta, etiqueta, toner, tambor, tinta, cabezal,
fusor, mascara). Commodities sin identificador (papel bond, clips, bolsas) NO se tocan: caen
al pipeline viejo (clave_det + 2A + 2E). Conservador: si no hay id fuerte, no se agrupa por firma.

Guardas: nunca cruza TIPO (toner≠tambor), nunca cruza COLOR, nunca cruza MARCA. id por tipo:
  toner/tambor/tinta -> SKU de registro (si no, modelo de impresora pegado)
  cinta/cabezal/fusor/mascara -> modelo de impresora pegado (lq590)
  etiqueta -> DIMENSIÓN (62x30) [el código DK suele venir corrupto: 'DK 220:62']

  dry:  scraper/venv/bin/python scratchpad/fase3_firma.py
"""
import os, re, json, sys, unicodedata, urllib.request, urllib.parse
from collections import defaultdict, Counter
sys.path.insert(0, '/Users/fabriziocuellar/Sicoes-Brain/monitor')
from dotenv import load_dotenv
load_dotenv('/Users/fabriziocuellar/Sicoes-Brain/monitor/.env')
U = os.environ["SUPABASE_URL"].rstrip("/"); K = os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}
def _get(path):
    r = urllib.request.Request(f"{U}/rest/v1/{path}", headers=H)
    with urllib.request.urlopen(r, timeout=120) as x: return json.loads(x.read())

def strip_acc(s): return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
def norm(s):
    s = strip_acc((s or "").lower()); s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

BRANDS = ['epson','brother','lexmark','hp','hewlett','canon','xerox','samsung','kyocera','ricoh',
          'panasonic','oki','dell','pantum','sharp','toshiba','konica','minolta','zebra','dymo']
# TIPO por prioridad (gana el 1º): cinta>etiqueta>tambor>cabezal>mascara>fusor>toner>tinta
TIPO_RULES = [
    ('cinta',    ['cinta']),
    ('etiqueta', ['etiqueta','autoadhesiv','auto adhesiv','rotulo']),
    ('tambor',   ['tambor','drum','fotoconductor','unidad de imagen','cilindro']),
    ('cabezal',  ['cabezal']),
    ('mascara',  ['mascara']),
    ('fusor',    ['fusor','fusora']),
    ('toner',    ['toner']),
    ('tinta',    ['tinta']),
]
def tipo(n):
    for t, kws in TIPO_RULES:
        for kw in kws:
            if kw in n: return t
    return None
BRAND_CANON = {'hewlett':'hp','minolta':'konica'}   # konica minolta = una marca
def marca(n):
    for b in BRANDS:
        if re.search(r'\b'+b+r'\b', n): return BRAND_CANON.get(b, b)
    return ''
def color(n):
    if re.search(r'\b(cyan|cian)\b', n): return 'c'
    if 'magenta' in n: return 'm'
    if re.search(r'\b(amarillo|yellow)\b', n): return 'y'
    return 'k'

SKU_RX = [
    (re.compile(r'\btn[ ]?-?[ ]?(\d{2,4})\b'), lambda m: "tn"+m.group(1)),
    (re.compile(r'\bdr[ ]?-?[ ]?(\d{2,4})\b'), lambda m: "dr"+m.group(1)),
    (re.compile(r'\b(cf|ce|cb)[ ]?(\d{3})[ ]?([ax])\b'), lambda m: m.group(1)+m.group(2)+m.group(3)),
    (re.compile(r'\bq[ ]?(\d{4})[ ]?([ax])\b'), lambda m: "q"+m.group(1)+m.group(2)),
    (re.compile(r'\b(\d{2}[a-z]\d[a-z]?\d{2,3})\b'), lambda m: m.group(1)),       # lexmark 56f4000
    (re.compile(r'\bmlt[ ]?-?[ ]?(d\d{3}[a-z]?)\b'), lambda m: "mlt"+m.group(1)),
    (re.compile(r'\btk[ ]?-?[ ]?(\d{3,4})\b'), lambda m: "tk"+m.group(1)),
    (re.compile(r'\b(gpr|npg)[ ]?-?[ ]?(\d{1,3})\b'), lambda m: m.group(1)+m.group(2)),
    (re.compile(r'\bc[ ]?-?[ ]?exv[ ]?(\d{1,3})\b'), lambda m: "cexv"+m.group(1)),
]
def sku(n):
    for rx, fn in SKU_RX:
        m = rx.search(n)
        if m: return fn(m)
    return ''
# modelo de impresora pegado: prefijo de serie alfabético(1-4) + 3-4 dígitos (+sufijo corto)
SERIE = r'(lq|fx|lx|dfx|ms|mx|mb|cx|cs|hl|dcp|mfc|ml|scx|clx|clp|sl|m|p|cp|b|wf|l|ip|mg|mx|ts|tx|xp|gx|pro|phaser)'
MODEL_RX = re.compile(r'\b'+SERIE+r'[ ]?-?[ ]?(\d{3,4})([a-z]{0,3})\b')
UNIT = {'mm','cm','mt','mts','m','gr','grs','g','kg','ml','lt','l','w','v','hz'}
def modelo(n):
    best = ''
    for m in MODEL_RX.finditer(n):
        pre, num, suf = m.group(1), m.group(2), m.group(3)
        if pre in UNIT: continue
        cand = pre+num+suf
        if len(cand) > len(best): best = cand   # el más específico
    return best
# dimensión NxN (etiquetas): primer par alrededor de 'x'
DIM_RX = re.compile(r'\b(\d{1,3})(?:[.,]\d+)?[ ]?(?:mm|cm|m|mts)?[ ]?x[ ]?(\d{1,3})(?:[.,]\d+)?')
def dim(n):
    m = DIM_RX.search(n)
    if not m: return ''
    return f"{int(m.group(1))}x{int(m.group(2))}"

# inferir marca a partir del id (prefijo de código / modelo), cuando la palabra-marca falta
INFER = [('lq','epson'),('fx','epson'),('lx','epson'),('dfx','epson'),
         ('tn','brother'),('dr','brother'),('dk','brother'),
         ('cf','hp'),('ce','hp'),('cb','hp'),('q','hp'),
         ('mlt','samsung'),('tk','kyocera'),('gpr','canon'),('npg','canon'),('cexv','canon')]
def infer_marca(idv):
    for pre, mk in INFER:
        if idv.startswith(pre): return mk
    if re.fullmatch(r'\d{2}[a-z]\d[a-z]?\d{2,3}', idv): return 'lexmark'  # 56f4000
    return ''
# DK conocido -> su dimensión de fábrica (unifica 'DK 2205' sin medidas con los '62x30')
DK_DIM = {'2205': '62x30'}
DK_RX = re.compile(r'\bdk[ ]?-?[ ]?(\d{4})\b')
def dk_code(n):
    m = DK_RX.search(n)
    return m.group(1) if m else ''

def firma(desc):
    n = norm(desc)
    t = tipo(n)
    if not t: return None                      # no es consumible identificable -> fallback
    cl = color(n)
    if t in ('toner','tambor','tinta'):
        idv = sku(n) or modelo(n)
        mk = marca(n) or infer_marca(idv)
    elif t == 'etiqueta':
        dkc = dk_code(n)
        idv = dim(n) or DK_DIM.get(dkc, ('dk'+dkc) if dkc else '')
        mk = ''                                 # etiqueta: la dimensión identifica; marca omitida
    else:                                       # cinta, cabezal, fusor, mascara
        idv = modelo(n) or sku(n)
        mk = marca(n) or infer_marca(idv)
    if not idv: return None                     # sin identificador fuerte -> fallback (conservador)
    return f"{t}|{mk}|{idv}|{cl}"

# ====== MAIN (dry-run inspección; recablear_v4 reusa solo las funciones de arriba) ======
# ---------- cargar e inspeccionar ----------
items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,descripcion&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break

grupos = defaultdict(list)
sin_firma = 0
for it in items:
    f = firma(it["descripcion"])
    if f is None: sin_firma += 1; continue
    grupos[f].append(it)

clusters = {k: v for k, v in grupos.items() if len(v) >= 2}
en_cluster = sum(len(v) for v in clusters.values())
print(f"items: {len(items)} | con firma de consumible: {len(items)-sin_firma} | sin firma (fallback): {sin_firma}")
print(f"grupos por firma (>=2): {len(clusters)} | items en esos grupos: {en_cluster}")

# SEGURIDAD: ¿algún grupo mezcla MARCAS declaradas distintas? (señal de fusión errada)
def marcas_declaradas(its):
    s = set()
    for it in its:
        n = norm(it["descripcion"])
        for b in BRANDS:
            if re.search(r'\b'+b+r'\b', n): s.add(BRAND_CANON.get(b, b))
    return s
conflict = 0
for k, its in clusters.items():
    ms = marcas_declaradas(its)
    if len(ms) > 1:
        conflict += 1
        print(f"  !! CONFLICTO MARCA en {k}: {ms}  ({len(its)} items)")
print(f"SEGURIDAD grupos con marcas declaradas en conflicto: {conflict} (debe ser 0)")

print("\n==== TOP 20 grupos por firma (tamaño) ====")
for k in sorted(clusters, key=lambda k: -len(clusters[k]))[:20]:
    rep = Counter(i["descripcion"] for i in clusters[k]).most_common(1)[0][0]
    print(f"  [{len(clusters[k]):>3}] {k:28} | {rep[:72]}")

# CASOS DEL USUARIO
print("\n==== CASOS REPORTADOS ====")
def dump_firma(substr):
    seen = defaultdict(list)
    for it in items:
        if substr.lower() in it["descripcion"].lower():
            seen[firma(it["descripcion"])].append(it["descripcion"][:70])
    for f, ds in sorted(seen.items(), key=lambda x: -len(x[1])):
        print(f"  firma={f} | {len(ds)} items  e.g. {ds[0]}")
print("-- Cinta Epson LQ-590:")
dump_firma("LQ-590"); dump_firma("LQ 590")
print("-- Papel/Etiqueta autoadhesivo 62:")
dump_firma("AUTOADHESIVO")
print("-- DK 2205 / DK 220:")
dump_firma("DK 2205"); dump_firma("DK 220")
