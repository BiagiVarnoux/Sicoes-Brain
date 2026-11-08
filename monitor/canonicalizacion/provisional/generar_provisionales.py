#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FRENTE 2/4 — GENERADOR DE CANÓNICOS PROVISIONALES (versionado, FUERA de producción). SOLO LECTURA.
=============================================================================================
Produce un artefacto JSON versionado que mapea cada descripción a un PRODUCTO CANÓNICO PROVISIONAL,
combinando:
  · motor de impresión por código (impresion/extractor_impresion.py) — familia #1 por volumen,
  · pipeline por atributos (extractor_atributos.py) para las 8 categorías ya modeladas.

NO escribe en hist_productos_canonicos ni en hist_items. El dashboard lo lee como CAPA DE DEMO,
claramente diferenciada de las asignaciones CONFIRMADAS (producto_canonico_id en la BD). No afirma
intercambiabilidad donde no hay evidencia: cada grupo lleva `nivel` (producto/subfamilia/familia) y
`confianza`. Re-ejecutable.

Clave de join con el dashboard: `cuerpo(descripcion)` normalizado (misma normalización en demanda.ts).

Correr (desde monitor/):
  ../scraper/venv/bin/python canonicalizacion/provisional/generar_provisionales.py
Salida: ../../app/public/canonicos_provisionales.json  (+ copia en provisional/ para el repo)
"""
import os, re, sys, json, datetime, subprocess, collections, unicodedata, urllib.request
AQUI = os.path.dirname(os.path.abspath(__file__))
CANON = os.path.join(AQUI, "..")
sys.path.insert(0, CANON)
sys.path.insert(0, os.path.join(CANON, "impresion"))
from extractor_atributos import extraer as extraer_attr, cuerpo, SEGMENTO, ESPECIFICO
import extractor_impresion as imp
from dotenv import load_dotenv
load_dotenv("/Users/fabriziocuellar/Sicoes-Brain/monitor/.env")
U = os.environ["SUPABASE_URL"].rstrip("/"); K = os.environ["SUPABASE_KEY"]
H = {"apikey": K, "Authorization": f"Bearer {K}"}


def norm_join(s):
    """Normalización de join: igual que demanda.ts cuerpoNorm()."""
    s = cuerpo(s)
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"\s+", " ", s).strip()


def label_impresion(r):
    t = r["tipo"].capitalize()
    mk = (r["marca"] or "").upper()
    cod = r["codigo"] or ""
    col = f" {r['color']}" if r["color"] else ""
    return " ".join(x for x in [t, mk, cod] if x).strip() + col


def clave_attr(cat, rec):
    """Clave canónica provisional para las 8 categorías por atributos, según el nivel detectado."""
    at = rec["atributos"]
    seg = [a for a in SEGMENTO.get(cat, []) if a in at]
    esp = [a for a in ESPECIFICO.get(cat, []) if a in at]
    nivel = rec["nivel_identificable"]
    if nivel == "producto":
        campos = SEGMENTO.get(cat, []) + ESPECIFICO.get(cat, [])
    elif nivel == "subfamilia":
        campos = SEGMENTO.get(cat, [])
    else:
        campos = []
    partes = [f"{a}={json.dumps(at[a],ensure_ascii=False,sort_keys=True)}" for a in campos if a in at]
    return "attr|" + cat + ("|" + "|".join(partes) if partes else "")


def label_attr(cat, rec):
    at = rec["atributos"]
    campos = SEGMENTO.get(cat, []) + ESPECIFICO.get(cat, [])
    vals = [f"{a}={at[a]}" for a in campos if a in at]
    return (cat.replace("_", " ") + (" · " + ", ".join(vals) if vals else "")).strip()


def main():
    rows, off = [], 0
    while True:
        r = urllib.request.Request(f"{U}/rest/v1/hist_items?select=descripcion&limit=1000&offset={off}", headers=H)
        page = json.loads(urllib.request.urlopen(r, timeout=60).read()); rows += page; off += 1000
        if len(page) < 1000: break
    uniq = sorted({cuerpo(x["descripcion"]) for x in rows if x.get("descripcion")})

    asign = {}          # norm_join(desc) -> {clave, motor}
    grupos = {}         # clave -> metadata
    for d in uniq:
        n = imp.nrm(d)
        rimp = imp.extraer(d)
        if rimp:
            clave = rimp["clave_canonica"]
            asign[norm_join(d)] = {"clave": clave, "motor": "impresion"}
            g = grupos.setdefault(clave, {"label": label_impresion(rimp), "familia": "Consumibles de impresión",
                                          "subfamilia": rimp["tipo"], "nivel": rimp["nivel_identificable"],
                                          "confianza": rimp["confianza"], "n_desc": 0})
            g["n_desc"] += 1
            continue
        rattr = extraer_attr(d)
        if rattr and rattr["categoria"] != "consumible_impresion":
            cat = rattr["categoria"]
            clave = clave_attr(cat, rattr)
            asign[norm_join(d)] = {"clave": clave, "motor": "atributos"}
            g = grupos.setdefault(clave, {"label": label_attr(cat, rattr), "familia": cat,
                                          "subfamilia": cat, "nivel": rattr["nivel_identificable"],
                                          "confianza": {"producto": "alta", "subfamilia": "media"}.get(rattr["nivel_identificable"], "baja"),
                                          "n_desc": 0})
            g["n_desc"] += 1

    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=AQUI).decode().strip()
    except Exception:
        commit = "desconocido"

    # resumen por nivel/confianza
    porniv = collections.Counter(g["nivel"] for g in grupos.values())
    desc_cubiertas = len(asign)
    grupos_multi = sum(1 for g in grupos.values() if g["n_desc"] > 1)

    payload = {
        "version": f"prov-{datetime.date.today().isoformat()}",
        "generado_en": datetime.datetime.now().isoformat(timespec="seconds"),
        "commit": commit,
        "nota": ("PROVISIONAL y fuera de producción. NO confirmado por humano, NO escrito en "
                 "hist_productos_canonicos. nivel=producto afirma intercambiabilidad; subfamilia/familia NO."),
        "motores": ["impresion(codigo)", "atributos(8 categorias)"],
        "cobertura": {"descripciones_unicas_total": len(uniq), "descripciones_asignadas": desc_cubiertas,
                      "grupos": len(grupos), "grupos_con_2omas": grupos_multi, "por_nivel": dict(porniv)},
        "asignaciones": asign,
        "grupos": grupos,
    }
    # salida 1: src/data/ del dashboard (lo IMPORTA la vista demo; se versiona con el código)
    datadir = "/Users/fabriziocuellar/Sicoes-Brain/app/src/data"
    os.makedirs(datadir, exist_ok=True)
    pub = os.path.join(datadir, "canonicos_provisionales.json")
    with open(pub, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    # salida 2: copia versionada junto al generador (auditoría)
    with open(os.path.join(AQUI, "canonicos_provisionales.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"descripciones únicas: {len(uniq)} · asignadas a canónico provisional: {desc_cubiertas} "
          f"({100*desc_cubiertas//len(uniq)}%)")
    print(f"grupos: {len(grupos)} (con ≥2 descripciones: {grupos_multi}) · por nivel: {dict(porniv)}")
    print(f"→ {pub}")
    print(f"→ {os.path.join(AQUI, 'canonicos_provisionales.json')}")


if __name__ == "__main__":
    main()
