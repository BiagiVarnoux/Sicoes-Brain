#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Muestra NUEVA e INDEPENDIENTE para validar el verificador (Etapa 3) a 3 NIVELES. SOLO LECTURA.
Estratificada por CATEGORÍA y por VEREDICTO propuesto (para cubrir falsos+, falsos− e INSUF).
EXCLUYE descripciones ya usadas en las muestras previas (extractor 54/61/50/55 y pares v2) para
mantener independencia. El humano/ChatGPT etiqueta POR SEPARADO los 3 niveles; el scoring posterior
separará error de EXTRACTOR / BLOCKER / VERIFICADOR. NO se etiqueta aquí.
"""
import os, sys, csv, json, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, nrm
from blocker_candidatos import construir, pares, get, cuerpo
from verificador_niveles import verificar, enriquecer
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"muestras"); os.makedirs(OUT,exist_ok=True)
import sys as _sys
SEED=int(_sys.argv[1]) if len(_sys.argv)>1 else 20261107
OUTNAME=_sys.argv[2] if len(_sys.argv)>2 else "validacion_verificador_ciega.csv"
random.seed(SEED)
DL="/Users/fabriziocuellar/Downloads"

# descripciones ya usadas (independencia) — incluye la muestra 53 ya ETIQUETADA que informó las correcciones
usados=set()
for p in ["extractor_atributos_muestra_revisada.csv","validacion_extractor_v2_ciega_revisada.csv",
          "validacion_extractor_v3_ciega_revisada.csv","validacion_extractor_v4_propuesta_chatgpt.csv"]:
    fp=os.path.join(DL,p)
    if os.path.exists(fp):
        for r in csv.DictReader(open(fp,encoding="utf-8-sig")):
            d=r.get("descripcion") or ""
            if d: usados.add(d[:150])
for p in ["validacion_v2_propuesta_chatgpt.csv","validacion_verificador_etiquetada_chatgpt.csv"]:
    fp=os.path.join(DL,p)
    if os.path.exists(fp):
        for r in csv.DictReader(open(fp,encoding="utf-8-sig")):
            for k in ("descripcion_A","descripcion_B"):
                if r.get(k): usados.add(r[k][:150])

items=get("hist_items?select=id,cuce,descripcion")
por_desc=collections.defaultdict(list)
for it in items:
    c=cuerpo(it["descripcion"])
    if c: por_desc[c].append(it)
uniq=sorted(por_desc)
rec={d:extraer(d) for d in uniq}
amplia,subfam,solo_amplia,estado,recc=construir(rec)
P=pares(amplia,recc)
enr={d:enriquecer(recc[d]["categoria"],recc[d]["atributos"],d) for d in recc}

# clasificar cada par por veredicto; excluir pares que toquen descripciones ya usadas
porclase=collections.defaultdict(list)   # (cat,clase) -> [(a,b,v)]
for cat,comp,a,b in P:
    if a[:150] in usados or b[:150] in usados: continue
    v=verificar(cat,enr[a],enr[b])
    clase={("SI","SI"):"ESP_SI",("SI","INSUF"):"SUB_SI_ESP_INSUF",("SI","NO"):"SUB_SI_ESP_NO",
           ("NO","NO"):"SUB_NO"}.get((v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"]),"INSUF")
    porclase[(cat,clase)].append((a,b,v))

CUPO={"ESP_SI":3,"SUB_SI_ESP_NO":3,"SUB_SI_ESP_INSUF":2,"SUB_NO":3,"INSUF":2}
muestra=[]
for (cat,clase),lst in sorted(porclase.items()):
    random.shuffle(lst)
    for a,b,v in lst[:CUPO.get(clase,2)]:
        muestra.append((cat,clase,a,b,v))
random.shuffle(muestra)

path=os.path.join(OUT,OUTNAME)
with open(path,"w",newline="",encoding="utf-8") as fh:
    w=csv.writer(fh)
    w.writerow(["par_id","categoria","clase_propuesta","descripcion_A","descripcion_B","attrs_A","attrs_B",
                "propuesta_FAMILIA_AMPLIA","propuesta_SUBFAMILIA","propuesta_PRODUCTO_ESPECIFICO",
                "razon_subfamilia","razon_especifico",
                "HUMANO_FAMILIA_AMPLIA(SI/NO/INSUF)","HUMANO_SUBFAMILIA(SI/NO/INSUF)",
                "HUMANO_PRODUCTO_ESPECIFICO(SI/NO/INSUF)","ERROR_DE(extractor/blocker/verificador/ninguno)","NOTA"])
    for i,(cat,clase,a,b,v) in enumerate(muestra,1):
        w.writerow([f"V{i:03d}",cat,clase,a[:150],b[:150],
                    json.dumps(enr[a],ensure_ascii=False,sort_keys=True),
                    json.dumps(enr[b],ensure_ascii=False,sort_keys=True),
                    v["FAMILIA_AMPLIA"],v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"],
                    v["razon_subfamilia"],v["razon_especifico"],"","","","",""])
print(f"escrito muestras/{OUTNAME} ({len(muestra)} pares)")
print("por categoría×clase:",{f"{c}/{cl}":len(porclase[(c,cl)]) for c,cl in sorted(porclase)})
