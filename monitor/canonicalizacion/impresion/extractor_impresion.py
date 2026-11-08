#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRENTE 2 — MOTOR DE CONSUMIBLES DE IMPRESIÓN por CÓDIGO. SOLO LECTURA, entorno aislado.
=============================================================================================
Es el "motor delegado" que el blocker (blocker_candidatos.py) ya reserva para la categoría
`consumible_impresion` (DELEGADO = {"consumible_impresion"}): el pipeline por atributos NO lo
modela, se resuelve aquí por el CÓDIGO del consumible.

IDENTIDAD (decisión de diseño, memoria canonicalizacion-diseno)
---------------------------------------------------------------
La identidad de un consumible de impresión es el MODELO DEL CONSUMIBLE (CE278A, TN-3609, GPR-35,
56F0Z00, Q2612A…), NO la impresora a la que sirve. Una descripción suele traer AMBOS (impresora
HP M201 + tóner CE278A); hay que quedarse con el código del consumible.

NIVELES (se conservan; una coincidencia de familia NO implica intercambiabilidad)
---------------------------------------------------------------------------------
  FAMILIA_AMPLIA      = "consumible_impresion" (todos).
  SUBFAMILIA          = tipo (toner / cartucho / tinta / cinta / drum / fusor / cabezal / ...).
  PRODUCTO_ESPECIFICO = (marca, modelo_normalizado, color). Solo se afirma cuando hay CÓDIGO.

CONFIANZA
---------
  alta  : hay un código de consumible explícito (serie/código completo).  → clave específica.
  media : solo alias corto HP (p.ej. "78A") sin el código largo.          → clave específica (alias).
  baja  : sin código; solo tipo+marca(+color).                            → NO específica; agrega a
                                                                             nivel subfamilia, provisional.

NUNCA fusiona por parecido de nombre: sin código igual → no se afirma intercambiabilidad. No escribe
en la BD, no migra, no toca producción.
"""
import os, re, sys, json, collections, unicodedata
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, ".."))
from extractor_atributos import categoria, cuerpo  # reutiliza la detección de categoría ya curada


def nrm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", s).strip()


# ── TIPO (subfamilia) ────────────────────────────────────────────────────────────────────────────
_TIPO = [
    ("drum", r"\b(drum|tambor|unidad de imagen|fotoconductor)\b"),
    ("fusor", r"\b(fusor|film fusor|unidad de fusion)\b"),
    ("cabezal", r"\b(cabezal)\b"),
    ("revelador", r"\b(revelador|developer)\b"),
    ("cinta", r"\b(cinta|ribbon)\b"),
    ("refil", r"\b(refil|recarga)\b"),
    ("tinta", r"\b(tinta|cartucho de tinta)\b"),
    ("toner", r"\b(toner|tonner)\b"),
    ("cartucho", r"\b(cartucho)\b"),
]
def tipo(n):
    for v, pat in _TIPO:
        if re.search(pat, n):
            return v
    return "consumible"   # consumible de impresión sin tipo claro


# ── MARCA ──────────────────────────────────────────────────────────────────────────────────────
_MARCAS = [("hp", r"\bhp\b|hewlett"), ("brother", r"\bbrother\b"), ("canon", r"\bcanon\b"),
           ("epson", r"\bepson\b"), ("lexmark", r"\blexmark\b"), ("samsung", r"\bsamsung\b"),
           ("kyocera", r"\bkyocera\b"), ("konica", r"\bkonica\b|minolta"), ("pantum", r"\bpantum\b"),
           ("xerox", r"\bxerox\b"), ("ricoh", r"\bricoh\b"), ("oki", r"\boki\b"),
           ("panasonic", r"\bpanasonic\b")]
def marca(n):
    for v, pat in _MARCAS:
        if re.search(pat, n):
            return v
    return None


# ── COLOR ────────────────────────────────────────────────────────────────────────────────────────
def color(n):
    if re.search(r"\b(cyan|cian)\b", n): return "cyan"
    if re.search(r"\bmagenta\b", n): return "magenta"
    if re.search(r"\b(amarillo|yellow)\b", n): return "amarillo"
    if re.search(r"\b(negro|negra|black|bk)\b", n): return "negro"
    if re.search(r"\bazul\b", n): return "azul"   # en pliegos a veces = cyan, se preserva aparte
    return None


# ── CÓDIGO DEL CONSUMIBLE ─────────────────────────────────────────────────────────────────────────
# Patrones de código COMPLETO (consumible), ordenados por especificidad. Devuelven el código tal cual
# aparece; luego se normaliza (sin espacios/guiones, mayúsculas).
# (patrón, solo_si_marca) — solo_si_marca=None aplica a cualquiera; separador [-\s]{0,3} tolera
# "TN - 3609", "CE 278 A", etc. Orden = especificidad (lo más inequívoco primero).
_COD_FULL = [
    (r"\bC[EFBC]\s?\d{3}\s?[A-Z]?\b", None),   # HP láser: CE278A, CF283A, CB435A, CC531A
    (r"\bQ\s?\d{4}\s?[A-Z]?\b", None),         # HP viejo: Q2612A, Q7553A
    (r"\bW\s?\d{4}\s?[A-Z]?\b", None),         # HP nuevo: W1450A, W2070A
    (r"\bTN[-\s]{0,3}\d{2,4}\s?[A-Z]{0,3}\b", None),  # Brother/Konica: TN-221, TN - 3609, TN323
    (r"\bDR[-\s]{0,3}\d{2,4}[A-Z]{0,3}\b", None),     # Brother drum: DR-2340, DR-221CL
    (r"\bGPR[-\s]{0,3}\d{1,3}\b", None),       # Canon: GPR-35, GPR-63
    (r"\bNPG[-\s]{0,3}\d{1,3}\b", None),       # Canon: NPG-xx
    (r"\bC[-\s]{0,2}EXV\s?\d{1,3}\b", None),   # Canon: C-EXV33
    (r"\b\d{2}F[0-9A-Z]{4}\b", None),         # Lexmark: 56F0Z00, 56F4H00, 56F4000
    (r"\bMLT[-\s]{0,3}D?\d{3}[A-Z]?\b", None), # Samsung: MLT-D111S
    (r"\bTK[-\s]{0,3}\d{3,4}[A-Z]?\b", None),  # Kyocera: TK-1175
    (r"\bTL[-\s]{0,3}\d{3,4}[A-Z]?\b", None),  # Pantum: TL-5120X
    (r"\bPA[-\s]{0,3}\d{3}[A-Z]?\b", None),    # Pantum: PA-210
    (r"\bBT\s?\d{3,4}[A-Z]?\b", None),         # Epson ecotank: BT5001
    (r"\bT\s?\d{3,4}\b", "epson"),             # Epson tinta: T544, T7741 (solo si marca epson)
]
# Alias corto HP: "78A", "83 A", "12A", "05X" (2-3 dígitos + A/X, opcional XL). MEDIA confianza.
_COD_ALIAS = r"(?<![a-z0-9])(\d{2,3})\s?([ax])(l)?(?![a-z0-9])"

# Equivalencias HP conocidas (alias corto → código completo). Inequívocas y públicas; permiten
# unir "TONER HP 78A" con "CE278A" (mismo producto). NO se inventan: solo pares documentados.
_HP_ALIAS = {
    "HP78A": "CE278A", "HP83A": "CF283A", "HP85A": "CE285A", "HP26A": "CF226A", "HP26X": "CF226X",
    "HP30A": "CF230A", "HP30X": "CF230X", "HP05A": "CE505A", "HP05X": "CE505X", "HP12A": "Q2612A",
    "HP35A": "CB435A", "HP36A": "CB436A", "HP53A": "Q7553A", "HP49A": "Q5949A", "HP80A": "CF280A",
    "HP80X": "CF280X", "HP17A": "CF217A", "HP48A": "CF248A", "HP79A": "CF279A", "HP58A": "CF258A",
    "HP59A": "CF259A", "HP94A": "CF294A", "HP07A": "CE307A", "HP10A": "W1010A", "HP11A": "Q6511A",
}

# ruido que NO es código de consumible: páginas, modelos de impresora típicos, capacidades
_STOP_CODE = re.compile(r"\b(paginas?|rendimiento|capacidad|original|impresora|fotocopiadora)\b")


def _norm_code(raw):
    return re.sub(r"[\s\-]", "", raw).upper()


def codigo(n, mk):
    """Devuelve (codigo_normalizado, confianza, evidencia) o (None, None, None).
    'serie <code>' tiene prioridad (el SICOES pone ahí el código del consumible)."""
    # 1) tras 'serie' el SICOES pone el código del consumible
    m = re.search(r"\bserie\s+([a-z]{0,3}\s?\d[\w\s\-]{1,8})", n)
    if m:
        for pat, solo in _COD_FULL:
            if solo and mk != solo:
                continue
            mm = re.search(pat, m.group(1), re.I)
            if mm:
                return _norm_code(mm.group(0)), "alta", f"serie {mm.group(0)}"
    # 2) código completo en cualquier parte (el primero por orden de especificidad)
    for pat, solo in _COD_FULL:
        if solo and mk != solo:          # p.ej. 'T\d{3,4}' solo vale para epson
            continue
        mm = re.search(pat, n, re.I)
        if mm:
            return _norm_code(mm.group(0)), "alta", mm.group(0)
    # 3) Epson refil/tinta por número desnudo (544, 664, 003): el modelo de IMPRESORA epson empieza
    #    por letra (L3110, WF, XP) → un número suelto tras refil/tinta/serie es el código de tinta.
    if mk == "epson":
        m = re.search(r"\b(?:refil|tinta|serie|bk)\s+(?:de\s+)?(?:recarga\s+)?(?:n[°º]\s*)?(\d{3})\b", n)
        if m:
            return f"T{m.group(1)}", "media", f"epson {m.group(1)}"
    # 4) alias corto HP (solo con marca hp o sin marca; nunca si hay otra marca con su sistema)
    if mk in (None, "hp"):
        for mm in re.finditer(_COD_ALIAS, n):
            ctx = n[max(0, mm.start()-12):mm.end()+4]
            if _STOP_CODE.search(ctx):     # descartar si está pegado a ruido (modelo de impresora, páginas)
                continue
            num, letra, xl = mm.group(1), mm.group(2), mm.group(3) or ""
            alias = f"HP{num}{letra.upper()}{xl.upper()}"
            full = _HP_ALIAS.get(alias)
            # si el alias es una equivalencia conocida, usar el código completo (une con el grupo CExxx);
            # confianza 'alta' porque la equivalencia es documentada, no un parecido de nombre.
            return (full, "alta", f"{mm.group(0).strip()}→{full}") if full else (alias, "media", mm.group(0).strip())
    return None, None, None


def extraer(desc):
    """desc cruda → registro del consumible, o None si no es consumible de impresión."""
    n = nrm(desc)
    if categoria(n) != "consumible_impresion":
        return None
    mk = marca(n)
    cod, conf, ev = codigo(n, mk)
    tp = tipo(n)
    col = color(n)
    if cod:
        nivel = "producto"            # identidad por código (color discrimina si está)
        clave = f"imp|{mk or '?'}|{cod}|{col or 'sincolor'}"
    else:
        nivel = "subfamilia"          # sin código no se afirma intercambiabilidad
        conf = "baja"
        clave = f"impsub|{tp}|{mk or '?'}|{col or 'sincolor'}"
    return {"categoria": "consumible_impresion", "tipo": tp, "marca": mk, "color": col,
            "codigo": cod, "confianza": conf, "evidencia_codigo": ev,
            "nivel_identificable": nivel, "clave_canonica": clave}


if __name__ == "__main__":
    # auto-prueba de cobertura sobre el corpus (solo lectura)
    import urllib.request
    from dotenv import load_dotenv
    load_dotenv("/Users/fabriziocuellar/Sicoes-Brain/monitor/.env")
    U = os.environ["SUPABASE_URL"].rstrip("/"); K = os.environ["SUPABASE_KEY"]
    H = {"apikey": K, "Authorization": f"Bearer {K}"}
    out, off = [], 0
    while True:
        r = urllib.request.Request(f"{U}/rest/v1/hist_items?select=descripcion&limit=1000&offset={off}", headers=H)
        rows = json.loads(urllib.request.urlopen(r, timeout=60).read()); out += rows; off += 1000
        if len(rows) < 1000: break
    uniq = sorted({cuerpo(x["descripcion"]) for x in out if x.get("descripcion")})
    recs = {d: extraer(d) for d in uniq}
    recs = {d: r for d, r in recs.items() if r}
    conf = collections.Counter(r["confianza"] for r in recs.values())
    con_cod = sum(1 for r in recs.values() if r["codigo"])
    print(f"consumible_impresion únicos: {len(recs)} · con código: {con_cod} "
          f"({100*con_cod//max(len(recs),1)}%) · confianza {dict(conf)}")
    grupos = collections.defaultdict(list)
    for d, r in recs.items(): grupos[r["clave_canonica"]].append(d)
    multi = {k: v for k, v in grupos.items() if len(v) > 1}
    print(f"claves canónicas: {len(grupos)} · con ≥2 descripciones (agrupan): {len(multi)}")
    print("\nTop grupos por nº de descripciones distintas agrupadas:")
    for k, v in sorted(multi.items(), key=lambda kv: -len(kv[1]))[:12]:
        print(f"  [{len(v)}] {k}")
        for d in sorted(v)[:3]:
            print(f"        · {d[:90]}")
