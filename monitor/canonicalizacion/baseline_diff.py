#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aísla el impacto EXACTO de las correcciones de cierre (E049, E014, E043, E034/E050) sobre TODO el corpus.
Corre el extractor ACTUAL, luego revierte SOLO esas funciones a su estado pre-cierre, re-corre y diffea.
Todo cambio listado es atribuible a esas correcciones (no a rondas previas). SOLO LECTURA.
"""
import os, sys, json, re, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extractor_atributos as E
from extractor_atributos import get, cuerpo

items=get("hist_items?select=id,descripcion")
uniq=sorted({cuerpo(it["descripcion"]) for it in items if cuerpo(it["descripcion"])})
def snap():
    out={}
    for d in uniq:
        r=E.extraer(d)
        out[d]=("None","{}","—") if r is None else (r["categoria"],json.dumps(r["atributos"],ensure_ascii=False,sort_keys=True),r["nivel_identificable"])
    return out
nuevo=snap()

E._NO_PROD_LIDER=r"(?!x)x"                       # pre-cierre: case/rack NO excluidos
def old_gramaje(n):
    m=re.search(r"(\d{2,3})\s*(g\s*/?\s*m2|gsm|grs?\b|g\b)",n)
    return (int(m.group(1)),m.group(0)) if m else None
def old_partes(n):
    m=re.search(r"11\s*[x*×]\s*(\d)\b",n)
    return (int(m.group(1)),m.group(0)) if m else None
old_tipo_medio=lambda n:(("dvd","dvd") if "dvd" in n else ("cd","cd") if ("cd" in n or "disco compacto" in n) else None)
for c in ["papel_bond","papel_impreso","sobre_manila","papel_continuo"]: E.EXTRACT[c]["gramaje_gm2"]=old_gramaje
E.EXTRACT["papel_continuo"]["partes"]=old_partes
E.EXTRACT["optico"]["tipo_medio"]=old_tipo_medio
viejo=snap()

cambios=[(d,viejo[d],nuevo[d]) for d in uniq if viejo[d]!=nuevo[d]]
buckets=collections.Counter()
print(f"corpus único: {len(uniq)} · filas afectadas por las correcciones de cierre: {len(cambios)}\n")
for d,o,n in cambios:
    tag=[t for t,c in (("CAT",o[0]!=n[0]),("ATR",o[1]!=n[1]),("NIV",o[2]!=n[2])) if c]
    nd=E.nrm(d)
    if re.match(r"^(case|rack)\b",E._cabeza(nd)): b="E049 case/rack"
    elif "disco compacto" in nd or ("cd" in nd and "dvd" not in nd): b="E014 tipo_medio"
    elif re.search(r"\d{2,3}\s*[-a]\s*\d{2,3}\s*(?:g\s*/?\s*m2|gsm|grs?\b)",nd): b="E043 gramaje rango"
    elif re.search(r"11\s*[x*×]\s*\d",nd): b="E034 partes"
    else: b="otro"
    buckets[b]+=1
    print(f"  [{'+'.join(tag):11}] {b:18} «{d[:58]}»")
    if o[0]!=n[0]: print(f"        cat : {o[0]!r} → {n[0]!r}")
    if o[1]!=n[1]: print(f"        attr: {o[1]}  →  {n[1]}")
    if o[2]!=n[2]: print(f"        niv : {o[2]!r} → {n[2]!r}")
print("\npor corrección:",dict(buckets))
