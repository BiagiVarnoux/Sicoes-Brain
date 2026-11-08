#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRENTE 1 — CONSOLIDACIÓN DETERMINISTA de la taxonomía LLM + ESTADO/COBERTURA. SOLO LECTURA, sin API.
=============================================================================================
Separa las tres fases que la memoria pedía NO mezclar: (1) etiquetado [ya en el checkpoint],
(2) consolidación de CATEGORÍAS, (3) consolidación de HOJAS. Este script hace (2) de forma
DETERMINISTA y SEGURA (mayúsculas, tildes, plurales inequívocos, variantes ortográficas y un mapa
curado de equivalencias conocidas) — SIN llamar al LLM. NO fusiona HOJAS por parecido de nombre
(conserva modelos/capacidades/medidas); solo normaliza el NOMBRE de la categoría de cabecera.

Entradas:
  - taxonomia_checkpoint.jsonl  (etiquetas con `desc` ligado al texto — fix 7-nov ya aplicado)
  - corpus vivo de hist_items    (para medir cobertura real y pendientes)

Salidas (versionadas, en este directorio):
  - taxonomia_consolidada.json   (categorías consolidadas → hojas, con conteos y mapa crudo→consolidado)
  - taxonomia_estado.md          (cobertura, pendientes, duplicados, categorías antes/después)
  - taxonomia_pendientes.json    (descripciones del corpus aún sin etiqueta LLM, para el incremental)

Correr (desde monitor/):
  ../scraper/venv/bin/python canonicalizacion/taxonomia/consolidar_determinista.py
"""
import os, re, sys, json, unicodedata, collections, urllib.request, datetime
AQUI = os.path.dirname(os.path.abspath(__file__))
MON = "/Users/fabriziocuellar/Sicoes-Brain/monitor"
sys.path.insert(0, os.path.join(MON, "canonicalizacion"))
from extractor_atributos import cuerpo
from dotenv import load_dotenv
load_dotenv(os.path.join(MON, ".env"))
U = os.environ["SUPABASE_URL"].rstrip("/"); K = os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}"}
CHECKPOINT = os.path.join(MON, "taxonomia_checkpoint.jsonl")
CHECKPOINT_INC = os.path.join(AQUI, "taxonomia_pendientes_checkpoint.jsonl")  # etiquetado incremental


def nrm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", s).strip()


# mapa curado de equivalencias de CATEGORÍA conocidas (seguro; no toca hojas)
_SINON_CAT = {
    "tonner": "toner", "toner": "toner", "tooner": "toner",
    "cartuchos de tinta": "cartucho", "cartucho de tinta": "cartucho", "cartuchos": "cartucho",
    "boligrafos": "boligrafo", "lapiceros": "lapicero", "marcadores": "marcador",
    "resmas de papel": "papel", "resma de papel": "papel", "hojas de papel": "papel",
    "memorias usb": "memoria usb", "memorias": "memoria", "discos duros": "disco duro",
    "llantas": "llanta", "neumaticos": "llanta", "neumatico": "llanta",
    "sobres": "sobre", "sobres manila": "sobre manila", "folders": "folder", "archivadores": "archivador",
}


def clave_categoria(nombre):
    """Clave de consolidación de una categoría: sin acentos/caso, plural trivial colapsado, sinónimos."""
    n = nrm(nombre)
    n = re.sub(r"[.;:,]+$", "", n).strip()
    if n in _SINON_CAT:
        return _SINON_CAT[n]
    # plural inequívoco: 'xxxes'→'xxx', 'xxxs'→'xxx' SOLO si deja ≥3 chars (evita 'gas'→'ga')
    if n.endswith("es") and len(n) > 4:
        base = n[:-2]
    elif n.endswith("s") and len(n) > 3:
        base = n[:-1]
    else:
        base = n
    return _SINON_CAT.get(base, base)


def nombre_display(variantes):
    """Nombre legible representativo de un grupo de variantes de categoría: el más frecuente,
    desempatando por el que lleva tildes/caso 'bonito' (más largo con mayúscula inicial)."""
    freq = collections.Counter(variantes)
    mejor = sorted(freq.items(), key=lambda kv: (-kv[1], -len(kv[0])))[0][0]
    return mejor.strip().capitalize() if mejor.islower() else mejor.strip()


def cargar_etiquetas():
    ets, sin_desc = [], 0
    for path in (CHECKPOINT, CHECKPOINT_INC):
        if not os.path.exists(path):
            continue
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if not ln:
                continue
            try:
                o = json.loads(ln)
            except json.JSONDecodeError:
                continue
            for e in o.get("etiquetas", []):
                if isinstance(e, dict) and isinstance(e.get("desc"), str):
                    ets.append(e)
                else:
                    sin_desc += 1
    return ets, sin_desc


def corpus_vivo():
    rows, off = [], 0
    while True:
        r = urllib.request.Request(f"{U}/rest/v1/hist_items?select=descripcion&limit=1000&offset={off}", headers=H)
        pg = json.loads(urllib.request.urlopen(r, timeout=60).read()); rows += pg; off += 1000
        if len(pg) < 1000:
            break
    return sorted({cuerpo(x["descripcion"]) for x in rows if x.get("descripcion")})


def main():
    ets, sin_desc = cargar_etiquetas()
    # dedup por desc-norm (conserva la PRIMERA etiqueta; registra cuántas duplicadas había)
    por_desc = collections.OrderedDict()
    dup = 0
    for e in ets:
        k = nrm(cuerpo(e["desc"]))
        if k in por_desc:
            dup += 1
            continue
        por_desc[k] = e
    etiquetas = list(por_desc.values())

    # consolidación de CATEGORÍAS
    variantes_por_clave = collections.defaultdict(list)
    for e in etiquetas:
        c = e.get("categoria") or "(sin categoría)"
        variantes_por_clave[clave_categoria(c)].append(c)
    cat_display = {k: nombre_display(v) for k, v in variantes_por_clave.items()}

    # árbol consolidado: categoria_consolidada → subcategoria → producto_canonico → conteo
    arbol = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    crudo_a_consol = {}
    for e in etiquetas:
        craw = e.get("categoria") or "(sin categoría)"
        ck = clave_categoria(craw)
        cat = cat_display[ck]
        crudo_a_consol[craw] = cat
        sub = (e.get("subcategoria") or "—").strip()
        prod = (e.get("producto_canonico") or "—").strip()
        arbol[cat][sub][prod] += 1

    cats_crudas = len({e.get("categoria") for e in etiquetas})
    cats_consol = len(arbol)

    # cobertura vs corpus vivo
    corpus = corpus_vivo()
    corpus_norm = {nrm(d): d for d in corpus}
    etiquetadas = sum(1 for k in corpus_norm if k in por_desc)
    pendientes = [d for k, d in corpus_norm.items() if k not in por_desc]
    huerfanas = sum(1 for k in por_desc if k not in corpus_norm)

    # ── salidas ──
    consolidada = {
        "generado_en": datetime.datetime.now().isoformat(timespec="seconds"),
        "fuente": "taxonomia_checkpoint.jsonl (etiquetas con desc ligado)",
        "metodo": "consolidación DETERMINISTA de nombres de categoría (sin LLM); hojas NO fusionadas",
        "categorias_crudas": cats_crudas,
        "categorias_consolidadas": cats_consol,
        "mapa_crudo_a_consolidado": crudo_a_consol,
        "arbol": {cat: {sub: dict(prods) for sub, prods in subs.items()} for cat, subs in arbol.items()},
    }
    json.dump(consolidada, open(os.path.join(AQUI, "taxonomia_consolidada.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"generado_en": consolidada["generado_en"], "total": len(pendientes),
               "nota": "descripciones del corpus vivo SIN etiqueta LLM; entrada del etiquetador incremental",
               "pendientes": pendientes},
              open(os.path.join(AQUI, "taxonomia_pendientes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # top categorías consolidadas por nº de hojas
    tops = sorted(arbol.items(), key=lambda kv: -sum(len(p) for p in kv[1].values()))[:25]
    L = ["# Frente 1 — Estado y consolidación de la taxonomía LLM\n",
         f"_Generado {consolidada['generado_en']}. Solo lectura, sin API._\n",
         "## Cobertura (corpus vivo vs checkpoint)",
         f"- Corpus: **{len(corpus)}** descripciones `cuerpo` distintas ({len(corpus_norm)} normalizadas).",
         f"- Etiquetas válidas (con `desc`): **{len(ets)}** · sin `desc`: {sin_desc} · duplicadas colapsadas: {dup}.",
         f"- Descripciones únicas etiquetadas: **{len(por_desc)}**.",
         f"- Cobertura del corpus: **{etiquetadas}/{len(corpus_norm)} ({100*etiquetadas//max(len(corpus_norm),1)}%)**.",
         f"- Pendientes (sin etiqueta): **{len(pendientes)}** → `taxonomia_pendientes.json`.",
         f"- Etiquetas huérfanas (ya no en el corpus): {huerfanas}.\n",
         "## Consolidación de categorías (determinista)",
         f"- Categorías crudas: **{cats_crudas}** → consolidadas: **{cats_consol}** "
         f"(reducción {100 - 100*cats_consol//max(cats_crudas,1)}%).",
         "- Método: normalización de mayúsculas/tildes + plurales inequívocos + mapa curado. **No** se "
         "fusionaron hojas (productos) por parecido de nombre.\n",
         "## Top 25 categorías consolidadas (por nº de hojas distintas)",
         "| categoría | subcategorías | hojas | descripciones |", "|---|---|---|---|"]
    for cat, subs in tops:
        nhojas = sum(len(p) for p in subs.values())
        ndesc = sum(sum(p.values()) for p in subs.values())
        L.append(f"| {cat} | {len(subs)} | {nhojas} | {ndesc} |")
    L.append("\n## Nota")
    L.append("Los pendientes son, en su mayoría, consumibles de impresión que YA están modelados por el "
             "motor por código (canonicalizacion/impresion). La taxonomía LLM es un MAPA DE PRIORIZACIÓN, "
             "no una fuente de fusiones confirmadas.")
    open(os.path.join(AQUI, "taxonomia_estado.md"), "w", encoding="utf-8").write("\n".join(L))

    print(f"etiquetas válidas: {len(ets)} | únicas: {len(por_desc)} | duplicadas colapsadas: {dup}")
    print(f"categorías: {cats_crudas} crudas → {cats_consol} consolidadas")
    print(f"cobertura corpus: {etiquetadas}/{len(corpus_norm)} ({100*etiquetadas//max(len(corpus_norm),1)}%) | pendientes: {len(pendientes)}")
    print(f"→ escrito taxonomia_consolidada.json, taxonomia_estado.md, taxonomia_pendientes.json en {AQUI}")


if __name__ == "__main__":
    main()
