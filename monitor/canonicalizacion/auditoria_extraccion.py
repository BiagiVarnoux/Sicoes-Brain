#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUBAUDITORÍA DE EXTRACCIÓN (SOLO LECTURA) — 2026-11-07
=============================================================================================
Pedida tras la corrección de llantas. Objetivo: en los pares donde falta un atributo PRIMARIO
(formato_continuo en papel_continuo; medida en llanta), distinguir TRES escenarios:
  (a) AUSENCIA REAL  — el texto crudo no contiene el patrón → el extractor acierta al no inventarlo.
  (b) FALLO EXTRACTOR — el texto SÍ contiene el patrón pero no se extrajo → bug a corregir.
  (c) DUDOSO          — patrón parcial/ambiguo.
No modifica el extractor ni el verificador. Salida: reportes/auditoria_extraccion.md
"""
import os,sys,re,collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from verificador_niveles import enriquecer
from extractor_atributos import extraer, nrm
from blocker_candidatos import construir,pares,get,cuerpo

# patrón "fuerte": lo que el extractor DEBERÍA haber capturado si el atributo primario estuviera.
# MODELADO: forma canónica que el extractor SÍ captura. Si está en el texto pero no se extrajo → FALLO.
PAT_FORMATO=re.compile(r"9\s*[.,]?\s*(?:1\s*/\s*2|½|\.5)?\s*[x*×]\s*11")   # 9½x11 / 9.5x11
PAT_MEDIDA =re.compile(r"\d{3}\s*/\s*\d{2}\s*r?\s*\d{2}|\d{3}\s*r\s*\d{2}") # 205/70 R15 / 185R14
# SIZE-LIKE: cualquier medida/dimensión presente (aunque NO en la forma modelada) → NO_MODELADO si no es canónica.
SIZE_CONT=re.compile(r"\d\s*(?:1\s*/\s*2|½|\.\d)?\s*[x*×]\s*\d")             # cualquier AxB
SIZE_LLAN=re.compile(r"\d[.,]?\d*\s*[/-]\s*\d|\br\s*\d{2}\b|\d{3}\s*r")      # 2.75/18, 2.75-18, R18…

def clasifica(raw,pat,size):
    n=nrm(raw)
    if pat.search(n):  return "FALLO_EXTRACTOR"   # forma canónica presente pero no extraída → bug
    if size.search(n): return "NO_MODELADO"       # hay una medida, pero en formato no soportado
    return "AUSENCIA_REAL"                         # el texto realmente no trae medida

items=get("hist_items?select=id,cuce,descripcion")
pd=collections.defaultdict(list)
for it in items:
    c=cuerpo(it["descripcion"])
    if c: pd[c].append(it)
uniq=sorted(pd); ur={d:extraer(d) for d in uniq}
amplia,subfam,sa,est,rec=construir(ur)
P=pares(amplia,rec); enr={d:enriquecer(rec[d]["categoria"],rec[d]["atributos"],d) for d in rec}

# recolectar DESCRIPCIONES ÚNICAS (no pares) que carecen del primario, para no multiplicar por pares
faltan={"papel_continuo":[], "llanta":[]}
for d in uniq:
    r=rec.get(d)
    if not r: continue
    cat=r["categoria"]
    if cat=="papel_continuo" and "formato_continuo" not in enr[d]:
        faltan["papel_continuo"].append(d)
    if cat=="llanta" and "medida" not in enr[d]:
        faltan["llanta"].append(d)

L=["# Subauditoría de extracción — atributos primarios ausentes (SOLO LECTURA)\n",
   "No modifica extractor ni verificador. Cuenta DESCRIPCIONES ÚNICAS (no pares) sin el atributo primario, "
   "y revisa el texto crudo para separar ausencia real de fallo de extracción.\n"]

for cat,pat,size,attr in [("papel_continuo",PAT_FORMATO,SIZE_CONT,"formato_continuo"),("llanta",PAT_MEDIDA,SIZE_LLAN,"medida")]:
    ds=faltan[cat]
    clas=collections.Counter(clasifica(d,pat,size) for d in ds)
    L.append(f"## {cat} — falta `{attr}` en {len(ds)} descripciones únicas")
    L.append(f"- AUSENCIA_REAL (texto no trae el patrón): **{clas['AUSENCIA_REAL']}**")
    L.append(f"- FALLO_EXTRACTOR (forma canónica presente, no extraída): **{clas['FALLO_EXTRACTOR']}**  ← bug si >0")
    L.append(f"- NO_MODELADO (trae medida en formato no soportado): **{clas['NO_MODELADO']}**  ← brecha de cobertura")
    fallos=[d for d in ds if clasifica(d,pat,size)=="FALLO_EXTRACTOR"]
    if fallos:
        L.append("\n  Ejemplos de FALLO_EXTRACTOR (trazables, hasta 12):")
        for d in fallos[:12]: L.append(f"  - `{d[:90]}`")
    nomod=[d for d in ds if clasifica(d,pat,size)=="NO_MODELADO"]
    aus=[d for d in ds if clasifica(d,pat,size)=="AUSENCIA_REAL"]
    if nomod:
        L.append("\n  Ejemplos de NO_MODELADO (trazables, hasta 12):")
        for d in nomod[:12]: L.append(f"  - `{d[:90]}`")
    if aus:
        L.append("\n  Ejemplos de AUSENCIA_REAL (hasta 6):")
        for d in aus[:6]: L.append(f"  - `{d[:90]}`")
    L.append("")

open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes","auditoria_extraccion.md"),"w").write("\n".join(L))
print("escrito reportes/auditoria_extraccion.md")
for cat,pat,size,attr in [("papel_continuo",PAT_FORMATO,SIZE_CONT,"formato_continuo"),("llanta",PAT_MEDIDA,SIZE_LLAN,"medida")]:
    ds=faltan[cat]; clas=collections.Counter(clasifica(d,pat,size) for d in ds)
    print(cat,attr,"→ únicas sin primario:",len(ds),dict(clas))
