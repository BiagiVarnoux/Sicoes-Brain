#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REGRESIÓN de las correcciones de cierre (E049, E014, E043, E034/E050) sobre las 4 muestras revisadas
(54+61+50+55, en ~/Downloads). SOLO LECTURA. Verifica ESTABILIDAD de salida y corre el test objetivo
producto-vs-componente + controles negativos nuevos. Reporta categoría/atributos/nivel por separado.
"""
import os, sys, json, csv, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, categoria, nrm, _cabeza

DL="/Users/fabriziocuellar/Downloads"
SAMPLES=[
 ("54 (muestra inicial)", f"{DL}/extractor_atributos_muestra_revisada.csv", "v1"),
 ("61 (v2)",              f"{DL}/validacion_extractor_v2_ciega_revisada.csv", "vN"),
 ("50 (v3)",              f"{DL}/validacion_extractor_v3_ciega_revisada.csv", "vN"),
 ("55 (v4)",              f"{DL}/validacion_extractor_v4_propuesta_chatgpt.csv", "vN"),
]
def salida(d):
    r=extraer(d)
    if r is None: return ("None","{}","—")
    return (r["categoria"], json.dumps(r["atributos"],ensure_ascii=False,sort_keys=True), r["nivel_identificable"])
def norm_json(s):
    try: return json.dumps(json.loads(s or "{}"),ensure_ascii=False,sort_keys=True)
    except Exception: return (s or "").strip()

print("="*90); print("REGRESIÓN — estabilidad de salida tras las correcciones de cierre"); print("="*90)
for nombre,path,schema in SAMPLES:
    if not os.path.exists(path): print(f"\n## {nombre}: FALTA {path}"); continue
    rows=list(csv.DictReader(open(path,encoding="utf-8-sig")))
    cat_ch=atr_ch=niv_ch=0; cambios=[]
    for i,row in enumerate(rows,1):
        d=row["descripcion"]
        if schema=="v1":
            old=(row["categoria"],norm_json(row["atributos"]),row["nivel_identificable"]); ok=row.get("EXTRACCION_OK(si/no)","").strip().lower(); rid=f"r{i:02d}"
        else:
            old=(row["categoria_extractor"],norm_json(row["atributos_extractor"]),row["nivel_extractor"])
            ok=(row.get("CATEGORIA_OK(si/no)","")+"/"+row.get("ATRIBUTOS_OK(si/no)","")+"/"+row.get("NIVEL_OK(si/no)","")).strip(); rid=row.get("id",f"r{i:02d}")
        nw=salida(d); dc,da,dn=old[0]!=nw[0],old[1]!=nw[1],old[2]!=nw[2]
        cat_ch+=dc; atr_ch+=da; niv_ch+=dn
        if dc or da or dn: cambios.append((rid,ok,d[:60],old,nw))
    print(f"\n## {nombre}  (n={len(rows)})  cambios → categoría:{cat_ch} atributos:{atr_ch} nivel:{niv_ch}")
    for rid,ok,d,o,nw in cambios:
        print(f"  [{rid}] marca={ok}  «{d}»")
        if o[0]!=nw[0]: print(f"       cat : {o[0]!r} → {nw[0]!r}")
        if o[1]!=nw[1]: print(f"       attr: {o[1]}  →  {nw[1]}")
        if o[2]!=nw[2]: print(f"       niv : {o[2]!r} → {nw[2]!r}")

PRINCIPAL_VS_COMPONENTE=[
 ("LAPTOP EMPRESARIAL i7, 16 GB RAM DDR4, SSD 512 GB", None),
 ("COMPUTADORA DE ESCRITORIO ALL IN ONE, 8 GB RAM, DISCO SSD 256 GB", None),
 ("IMPRESORA MULTIFUNCIONAL LASER, MEMORIA RAM 2 GB, 350 HOJAS", None),
 ("SERVIDOR RACK, 32 GB RAM, 2 DISCOS DUROS 2 TB", None),
 ("MINI PC INTEL, 16 GB RAM DDR4, SSD 1 TB", None),
 ("CAMARA IP DOMO 4MP CON RANURA MICRO SD 256GB", None),
 ("GRABADOR NVR 16 CANALES INCLUYE DISCO DURO 4TB", None),
 ("MEMORIA RAM DDR4 8 GB 3200 MHZ PARA PC", "ram"),
 ("DISCO DURO SSD 512 GB SATA 2.5", "almacenamiento"),
 ("MEMORIA RAM DDR3 4 GB", "ram"),
 ("DISCO SOLIDO INTERNO SSD 240 GB", "almacenamiento"),
]
print("\n"+"="*90); print("TEST OBJETIVO producto vs componente")
ok=sum(1 for d,e in PRINCIPAL_VS_COMPONENTE if categoria(nrm(d))==e)
for d,e in PRINCIPAL_VS_COMPONENTE:
    g=categoria(nrm(d)); print(f"  {'✓' if g==e else '✗'} esp={str(e):14} obt={str(g):14} ← {d[:48]}")
print(f"  → {ok}/{len(PRINCIPAL_VS_COMPONENTE)}")

print("\n"+"="*90); print("CONTROLES NEGATIVOS NUEVOS (las correcciones no deben romper otros casos)")
CTRL=[
 ("CASE EXTERNO PARA DISCO DURO 2.5 USB 3.0", "cat", None),
 ("RACK PARA 4 DISCOS DUROS", "cat", None),
 ("DISCO DURO 4 TB 3.5 PARA RACK DE DISCOS", "cat", "almacenamiento"),
 ("DISCO COMPACTO DE GRABACION 4.7 GB", "medio", None),
 ("DVD-R 4.7 GB 16X", "medio", "dvd"),
 ("CD-R 700 MB 52X", "medio", "cd"),
 ("PAPEL BOND CARTA 75-80 G/M2 BLANCO", "gram", "75-80"),
 ("PAPEL BOND CARTA 75 G/M2 BLANCO", "gram", 75),
 ("PAPEL CONTINUO 9 1/2 X 11 X 4 X 5.5 QUIMICO", "partes", 4),
 ("PAPEL CONTINUO AUTOCOPIATIVO 9 1/2 X 11 X 3", "partes", 3),
 ("PAPEL CONTINUO 9 1/2 X 11 X 2", "partes", 2),
]
okc=0
for d,kind,exp in CTRL:
    r=extraer(d)
    if kind=="cat": got=(r["categoria"] if r else None)
    elif kind=="medio": got=(r["atributos"].get("tipo_medio") if r else None)
    elif kind=="gram": got=(r["atributos"].get("gramaje_gm2") if r else None)
    elif kind=="partes": got=(r["atributos"].get("partes") if r else None)
    good=(got==exp); okc+=good
    print(f"  {'✓' if good else '✗'} [{kind:6}] esp={str(exp):10} obt={str(got):10} ← {d[:46]}")
print(f"  → {okc}/{len(CTRL)}")
