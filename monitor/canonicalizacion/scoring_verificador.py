#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCORING del verificador vs etiquetas humanas/asistidas (3 niveles). SOLO LECTURA.
Lee el CSV etiquetado, re-corre el verificador ACTUAL sobre cada par (re-extrae de las descripciones),
y produce: (1) matrices de confusión por NIVEL y por CATEGORÍA {SI/NO/INSUF}; (2) lista de TODAS las
discrepancias con propuesta vs humano + el ERROR_DE sugerido. NO ajusta nada; es diagnóstico.

Uso: scoring_verificador.py [ruta_csv_etiquetado]
"""
import os, sys, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, categoria, nrm
from verificador_niveles import verificar, enriquecer, VERIF_SEG
CSV=sys.argv[1] if len(sys.argv)>1 else "/Users/fabriziocuellar/Downloads/validacion_verificador_etiquetada_chatgpt.csv"
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes"); os.makedirs(OUT,exist_ok=True)
NIV=["FAMILIA_AMPLIA","SUBFAMILIA","PRODUCTO_ESPECIFICO"]
VAL=["SI","NO","INSUF"]

rows=list(csv.DictReader(open(CSV,encoding="utf-8-sig")))
conf={n:collections.Counter() for n in NIV}           # (humano,propuesta)->count
confcat=collections.defaultdict(lambda:collections.Counter())
disc=[]; acc={n:0 for n in NIV}; n=0
for r in rows:
    da,db=r["descripcion_A"],r["descripcion_B"]; cat=categoria(nrm(da))
    if cat is None or cat not in VERIF_SEG:
        continue
    A=enriquecer(cat,extraer(da)["atributos"],da); B=enriquecer(cat,extraer(db)["atributos"],db)
    v=verificar(cat,A,B)
    n+=1
    hum={ "FAMILIA_AMPLIA":r["HUMANO_FAMILIA_AMPLIA(SI/NO/INSUF)"].strip().upper(),
          "SUBFAMILIA":r["HUMANO_SUBFAMILIA(SI/NO/INSUF)"].strip().upper(),
          "PRODUCTO_ESPECIFICO":r["HUMANO_PRODUCTO_ESPECIFICO(SI/NO/INSUF)"].strip().upper()}
    difs=[]
    for niv in NIV:
        p=v[niv]; h=hum[niv]
        conf[niv][(h,p)]+=1; confcat[(r["categoria"],niv)][(h,p)]+=1
        if p==h: acc[niv]+=1
        else: difs.append(f"{niv}: propuesta={p} humano={h}")
    if difs:
        disc.append((r["par_id"],r["categoria"],r.get("ERROR_DE(extractor/blocker/verificador/ninguno)","").strip(),
                     da[:55],db[:55],"; ".join(difs),r.get("NOTA","")))

L=[f"# Scoring del verificador vs etiquetas asistidas (3 niveles) — {os.path.basename(CSV)}\n"]
L.append(f"Pares evaluables: {n}. **Concordancia (NO precisión demostrada):** "
         f"FAMILIA_AMPLIA {acc['FAMILIA_AMPLIA']}/{n} · SUBFAMILIA {acc['SUBFAMILIA']}/{n} · "
         f"PRODUCTO_ESPECIFICO {acc['PRODUCTO_ESPECIFICO']}/{n}.")
L.append("> Las etiquetas son asistidas (ChatGPT), NO verdad certificada; la muestra trae las propuestas "
         "del algoritmo (no es ciega del todo). Concordancia ≠ precisión real.")
L.append("> ⚠️ **ESTA muestra (53) INFORMÓ las correcciones de la capa correctiva v2** → su concordancia "
         "post-fix NO es validación independiente (ChatGPT lo advirtió). La validación real debe hacerse "
         "sobre `muestras/validacion_verificador2_ciega.csv` (nueva, no usada para ajustar), aún sin etiquetar.\n")
for niv in NIV:
    L.append(f"\n## Matriz de confusión — {niv}  (filas=humano, cols=propuesta)")
    L.append("| humano\\propuesta | "+" | ".join(VAL)+" |"); L.append("|"+"---|"*(len(VAL)+1))
    for h in VAL:
        L.append(f"| **{h}** | "+" | ".join(str(conf[niv][(h,p)]) for p in VAL)+" |")
L.append("\n## Discrepancias (todas)")
for pid,cat,err,da,db,dif,nota in disc:
    L.append(f"- **{pid}** [{cat}] (ChatGPT ERROR_DE={err or '—'}) — {dif}")
    L.append(f"    - A: «{da}»  · B: «{db}»")
    if nota: L.append(f"    - nota: {nota}")
open(os.path.join(OUT,"scoring_verificador.md"),"w").write("\n".join(L))
print(f"pares={n} concordancia: FAM {acc['FAMILIA_AMPLIA']} SUB {acc['SUBFAMILIA']} ESP {acc['PRODUCTO_ESPECIFICO']}")
print(f"discrepancias={len(disc)} → reportes/scoring_verificador.md")
for pid,cat,err,da,db,dif,nota in disc: print(f"  {pid} [{cat}] {err:11} | {dif}")
