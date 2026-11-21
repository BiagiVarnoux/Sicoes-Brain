#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FASE 1 — recableado canónico NATIVO sobre hist_items.

Arregla el bug del join por (cuce,nro_item): las claves se derivan ahora de
hist_items.descripcion (que ya trae desc+specs), así cada grupo queda ligado al
hist_items.id directamente. Contaminación cruzada imposible por construcción.

Pasos: pre-keyer determinístico + merge 2A por SKU (gratis, sin Groq).
Reconstrucción limpia: NULL de todas las asignaciones viejas, borra los canónicos
viejos (contaminados) y recrea por id. Grupos >=2 reciben canónico.

  dry-run:  scraper/venv/bin/python scratchpad/recablear_v3.py
  aplicar:  scraper/venv/bin/python scratchpad/recablear_v3.py --write
"""
import os, re, json, sys, argparse, unicodedata, urllib.request, urllib.parse, collections
from collections import Counter, defaultdict
sys.path.insert(0, '/Users/fabriziocuellar/Sicoes-Brain/monitor')
from dotenv import load_dotenv
load_dotenv('/Users/fabriziocuellar/Sicoes-Brain/monitor/.env')
U = os.environ["SUPABASE_URL"].rstrip("/"); K = os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}", "Content-Type": "application/json"}

def _get(path):
    r = urllib.request.Request(f"{U}/rest/v1/{path}", headers=H)
    with urllib.request.urlopen(r, timeout=120) as x: return json.loads(x.read())
def _req(method, path, body=None, extra=None):
    data = json.dumps(body).encode() if body is not None else None
    h = dict(H); h.update(extra or {})
    r = urllib.request.Request(f"{U}/rest/v1/{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=120) as x:
        raw = x.read(); return json.loads(raw) if raw else None

# ---------------- pre-keyer (idéntico a pipeline_v2) ----------------
def strip_acc(s): return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
def norm(s):
    s = strip_acc((s or "").lower()); s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()
STOP = {'de','para','con','color','tipo','material','tamano','medida','numero','familia',
        'presentacion','envase','contenido','aproximado','marca','modelo','la','el','los','las',
        'un','una','y','o','por','aprox','caja','unidad','pieza','paquete','mts','cms','cm','mm'}
FAM_SYN = {'toner':'toner','tonner':'toner','cartucho':'toner','cartuchos':'toner','refil':'toner','refill':'toner','kits':'toner','kit':'toner','drum':'toner','tambor':'toner',
 'papel':'papel','papeles':'papel','resma':'papel','resmas':'papel','hoja':'papel','hojas':'papel',
 'silla':'silla','sillas':'silla','sillon':'silla','butaca':'silla',
 'disco':'almacenamiento','discos':'almacenamiento','memoria':'memoria','memorias':'memoria','usb':'almacenamiento','flash':'almacenamiento',
 'boligrafo':'boligrafo','boligrafos':'boligrafo','lapicero':'boligrafo','lapiceros':'boligrafo',
 'lapiz':'lapiz','lapices':'lapiz',
 'marcador':'marcador','marcadores':'marcador','resaltador':'resaltador','resaltadores':'resaltador',
 'cinta':'cinta','cintas':'cinta',
 'folder':'folder','folders':'folder','carpeta':'folder','carpetas':'folder','archivador':'archivador','archivadores':'archivador',
 'tinta':'tinta','tintas':'tinta',
 'guante':'guantes','guantes':'guantes',
 'desinfectante':'desinfectante','limpiador':'limpiador','limpiavidrios':'limpiavidrios',
 'engrapadora':'engrapadora','grapadora':'engrapadora','corchetera':'engrapadora',
 'grapa':'grapa','grapas':'grapa','corchete':'grapa','corchetes':'grapa'}
# palabras "contenedor": no son el producto, el sustantivo real viene después
# (p.ej. "Cartuchos de tinta ...", "Kits de limpieza ...", "Kit de mantenimiento ...")
CONTAINER = {'kit','kits','cartucho','cartuchos','accesorio','accesorios','juego','juegos','set','sets'}
def familia(desc):
    toks = norm(desc).split()
    if not toks: return ""
    for t in toks:
        if t in CONTAINER:          # saltar contenedores, buscar el producto real
            continue
        f = FAM_SYN.get(t)
        if f: return f
        if len(t) >= 3 and t not in STOP:  # primer sustantivo significativo desconocido
            return t
    return toks[0]
def tokens_sig(txt):
    out = []
    for w in norm(txt).split():
        if re.fullmatch(r'\d+[a-z]*', w): out.append(w)
        elif len(w) >= 3 and w not in STOP: out.append(w)
    return out
def clave_det(desc):
    dn = norm(desc)
    if not dn: return None
    fam = familia(desc)
    if len(fam) < 3: return None
    attrs = sorted(set(tokens_sig(desc)))
    return fam + "|" + "|".join(attrs) if attrs else fam

# ---------------- 2A: merge determinístico por código SKU ----------------
BRANDS = {'hp','epson','brother','lexmark','canon','xerox','samsung','kyocera','ricoh','panasonic','oki','dell','pantum','sharp','toshiba','konica','minolta'}
COLORS = {'negro','negra','black','cyan','cian','magenta','amarillo','yellow','tricolor','bicolor','rojo','azul','verde','color'}
SKU_FAMS = {'toner','tinta','cinta','repuesto','memoria','almacenamiento','tambor','drum'}
def firma(clave):
    toks = clave.split("|")[1:]; mixed=set(); brands=set(); colors=set()
    for t in toks:
        if t in BRANDS: brands.add(t)
        elif t in COLORS: colors.add(t)
        elif re.fullmatch(r'[0-9x]+', t): pass
        elif re.fullmatch(r'\d+(mm|cm|mt|mts|m|kg|gr|grs|g|ml|lt|l|v|hz|khz|mhz|ghz|w|kw|btu|base|rpm|pulg|in|dpi|ppm|mp|pies|p)', t): pass
        elif re.search(r'[a-z]', t) and re.search(r'\d', t) and len(t) >= 3: mixed.add(t)
    return (frozenset(brands), frozenset(mixed), frozenset(colors))

# ---------------- nombre legible ----------------
def nombre(desc):
    s = re.sub(r'\s+', ' ', (desc or '').strip())
    s = s.replace(';', ' · ').replace(':', ' · ')
    s = re.sub(r'\s*·\s*', ' · ', s).strip(' ·-')
    return s[:160]

# ================== CARGA ==================
print("Leyendo hist_items…", flush=True)
items = []; off = 0
while True:
    r = _get(f"hist_items?select=id,cuce,nro_item,descripcion,unspsc_codigo&limit=1000&offset={off}")
    if not r: break
    items += r; off += 1000
    if len(r) < 1000: break
print(f"  hist_items: {len(items)}", flush=True)

# clave por item
for it in items:
    it["_clave"] = clave_det(it["descripcion"]) or "sin_clave"
buckets = defaultdict(list)
for it in items:
    buckets[it["_clave"]].append(it)

# 2A: por familia con >1 clave, fusionar por firma con código
p2 = defaultdict(list)
for k in buckets:
    if k != "sin_clave": p2[k.split("|")[0]].append(k)
remap = {}  # clave -> clave canónica
for fam, claves in p2.items():
    if fam not in SKU_FAMS or len(claves) < 2: continue
    byf = defaultdict(list)
    for k in claves:
        sig = firma(k)
        if len(sig[1]) > 0: byf[sig].append(k)
    for sig, grp in byf.items():
        if len(grp) > 1:
            canon = min(grp, key=len)
            for k in grp: remap[k] = canon

# grupos finales
grupos = defaultdict(list)   # clave_final -> [item]
for k, its in buckets.items():
    if k == "sin_clave": continue
    grupos[remap.get(k, k)].extend(its)
clusters = {c: v for c, v in grupos.items() if len(v) >= 2}

tot = len(items)
en_cluster = sum(len(v) for v in clusters.values())
print(f"Pre-keyer + 2A:  grupos>=2 = {len(clusters)} | ítems en cluster = {en_cluster} ({100*en_cluster/tot:.1f}%)", flush=True)

# nombre + categoria + unspsc por grupo
def info_grupo(its):
    rep = Counter(i["descripcion"] for i in its).most_common(1)[0][0]
    uns = Counter(i.get("unspsc_codigo") for i in its if i.get("unspsc_codigo")).most_common(1)
    return nombre(rep), uns[0][0] if uns else None

# auditoría previa: familia del item vs familia del grupo (debe ser 0 mismatch)
def famword(s):
    s = (s or '').lower()
    for w in ['cinta','toner','tóner','papel','tinta','disco','memoria','mouse','teclado','cartucho','cable','pila']:
        if w in s: return 'toner' if w == 'tóner' else w
    m = re.sub(r'[^a-záéíóú ]', ' ', s).split(); return m[0] if m else ''
bad = 0
for c, its in clusters.items():
    fc = c.split("|")[0]
    for it in its:
        if famword(it["descripcion"]) and fc and famword(it["descripcion"]) != fc and fc in ('toner','cinta','tinta','papel','memoria','almacenamiento'):
            bad += 1
print(f"Auditoría familia (item vs grupo) en claves de riesgo: {bad} mismatch", flush=True)

ap = argparse.ArgumentParser(); ap.add_argument("--write", action="store_true"); A = ap.parse_args()
if not A.write:
    print("\nDRY-RUN. 10 grupos más grandes:")
    for c in sorted(clusters, key=lambda c: -len(clusters[c]))[:10]:
        nm, _ = info_grupo(clusters[c])
        print(f"  [{len(clusters[c])}] {nm[:90]}")
    print("\n(usar --write para aplicar)")
    sys.exit(0)

# ================== ESCRITURA (reconstrucción limpia) ==================
print("\n--write: reconstruyendo canónicos desde cero…", flush=True)
# 1) NULL de todas las asignaciones viejas (contaminadas)
_req("PATCH", "hist_items?producto_canonico_id=not.is.null",
     {"producto_canonico_id": None}, extra={"Prefer": "return=minimal"})
print("  · hist_items.producto_canonico_id -> NULL (todas)", flush=True)
# 2) borrar canónicos viejos
_req("DELETE", "hist_productos_canonicos?id=gte.0", extra={"Prefer": "return=minimal"})
print("  · hist_productos_canonicos vaciada", flush=True)

# 3) insertar canónicos (batch) y mapear nombre->id
usados = {}
filas = []
meta = []  # (nombre, ids)
for c, its in clusters.items():
    nm, uns = info_grupo(its)
    base = nm; n = 2
    while nm in usados: nm = f"{base} ({n})"; n += 1
    usados[nm] = True
    ids = [it["id"] for it in its]
    filas.append({"nombre_canonico": nm, "categoria": c.split("|")[0], "unspsc_codigo": uns, "n_items": len(ids)})
    meta.append((nm, ids))

nombre2id = {}
for i in range(0, len(filas), 500):
    chunk = filas[i:i+500]
    res = _req("POST", "hist_productos_canonicos", chunk, extra={"Prefer": "return=representation"})
    for row in res: nombre2id[row["nombre_canonico"]] = row["id"]
print(f"  · {len(nombre2id)} canónicos creados", flush=True)

# 4) PATCH hist_items.producto_canonico_id por id
asignados = 0
for nm, ids in meta:
    cid = nombre2id[nm]
    for j in range(0, len(ids), 200):
        flt = "id=in.(" + ",".join(str(x) for x in ids[j:j+200]) + ")"
        _req("PATCH", f"hist_items?{flt}", {"producto_canonico_id": cid}, extra={"Prefer": "return=minimal"})
    asignados += len(ids)
print(f"\nLISTO FASE 1. canónicos: {len(nombre2id)} | hist_items asignados: {asignados}", flush=True)
