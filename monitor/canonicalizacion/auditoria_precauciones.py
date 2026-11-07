#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORÍA de precauciones (SOLO LECTURA, NO modifica el verificador). Responde:
 #3  Efecto AISLADO de la regla de atributos SECUNDARIOS sobre SUBFAMILIA (usar_sec True vs False,
     mismos atributos enriquecidos) → qué pares salieron de INSUF y riesgo de falso positivo.
 #4  Discriminación de FAMILIA_AMPLIA: el blocker NUNCA empareja cross-categoría, así que FAM=SI es
     una ASUNCIÓN, no una medición. Se construyen NEGATIVOS cross-categoría y se verifica que el
     pipeline (categoría) los separa; se muestra que el verificador asume FAM=SI (bug latente).
"""
import os, sys, json, csv, collections, random, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, categoria, nrm
from blocker_candidatos import construir, pares, get, cuerpo
from verificador_niveles import verificar, enriquecer, VERIF_SEG, SEG_SEC
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes"); os.makedirs(OUT,exist_ok=True)
random.seed(7)

items=get("hist_items?select=id,descripcion")
por_desc=collections.defaultdict(list)
for it in items:
    c=cuerpo(it["descripcion"])
    if c: por_desc[c].append(it)
uniq=sorted(por_desc); uniq_rec={d:extraer(d) for d in uniq}
amplia,subfam,solo_amplia,estado,rec=construir(uniq_rec)
P=pares(amplia,rec)
enr={d:enriquecer(rec[d]["categoria"],rec[d]["atributos"],d) for d in rec}

# ── #3 efecto aislado de la regla de SECUNDARIOS ─────────────────────────────────────────────────
trans=collections.Counter(); insuf_si=[]; insuf_no=[]
riesgo_una=riesgo_ambas=0
for cat,comp,a,b in P:
    if cat not in SEG_SEC: continue      # solo categorías con secundarios (papel_bond, papel_continuo, llanta)
    vs_true=verificar(cat,enr[a],enr[b],usar_sec=True)["SUBFAMILIA"]
    vs_false=verificar(cat,enr[a],enr[b],usar_sec=False)["SUBFAMILIA"]
    if vs_true!=vs_false:
        trans[(vs_false,vs_true)]+=1
        if vs_false=="INSUF" and vs_true=="SI":
            # riesgo FP: primario igual, secundario ausente en 1 o ambos lados
            sec=SEG_SEC[cat]
            pres_a=all(k in enr[a] for k in sec); pres_b=all(k in enr[b] for k in sec)
            if pres_a ^ pres_b: riesgo_una+=1           # un lado SÍ declara el secundario, el otro no (asumimos que coincide)
            else: riesgo_ambas+=1                        # ninguno lo declara
            if len(insuf_si)<8: insuf_si.append((cat,a,b,sec))
        if vs_false=="INSUF" and vs_true=="NO":
            if len(insuf_no)<5: insuf_no.append((cat,a,b))

# ── #4 negativos cross-categoría (familia amplia) ────────────────────────────────────────────────
cats=sorted(amplia)
reps={c:amplia[c][:30] for c in cats}
negs=[]; ok_sep=0; tot=0
for c1,c2 in itertools.combinations(cats,2):
    a=random.choice(reps[c1]); b=random.choice(reps[c2]); tot+=1
    sep = categoria(nrm(a))!=categoria(nrm(b))   # el pipeline los separa por categoría
    ok_sep+=sep
    if len(negs)<10: negs.append((c1,c2,a,b,sep))

L=["# Auditoría de precauciones (#3 secundarios, #4 familia amplia) — SOLO LECTURA\n"]
L.append("## #3 — Efecto AISLADO de la regla de atributos SECUNDARIOS sobre SUBFAMILIA")
L.append("Comparación usar_sec=True vs usar_sec=False con LOS MISMOS atributos enriquecidos (aísla la regla, "
         "no mezcla con la extracción tolerante). Solo categorías con secundarios: papel_bond, papel_continuo, llanta.\n")
L.append("| transición SUBFAMILIA (sin regla → con regla) | pares |"); L.append("|---|---|")
for k,v in trans.most_common(): L.append(f"| {k[0]} → {k[1]} | {v} |")
tot_insuf_si=sum(v for k,v in trans.items() if k==('INSUF','SI'))
L.append(f"\n**INSUF→SI por la regla: {tot_insuf_si}.** De ellos, riesgo de falso positivo:")
L.append(f"- **{riesgo_una}**: UN lado declara el secundario (gramaje/aplicación) y el otro NO → se asume que coincide (riesgo real).")
L.append(f"- **{riesgo_ambas}**: NINGÚN lado lo declara → no hay valor que contradecir (riesgo bajo).")
L.append(f"- INSUF→NO por la regla (secundario que CONTRADICE → detecta diferencia): "
         f"{sum(v for k,v in trans.items() if k==('INSUF','NO'))}.")
L.append("\nEjemplos INSUF→SI (revisar si el secundario ausente oculta una diferencia real):")
for cat,a,b,sec in insuf_si:
    L.append(f"- [{cat}] secundario={sec}  A={json.dumps({k:enr[a].get(k) for k in sec},ensure_ascii=False)} "
             f"B={json.dumps({k:enr[b].get(k) for k in sec},ensure_ascii=False)}")
    L.append(f"    - A: «{a[:85]}»"); L.append(f"    - B: «{b[:85]}»")
L.append("\nEjemplos INSUF→NO (la regla detectó una diferencia de secundario):")
for cat,a,b in insuf_no:
    L.append(f"- [{cat}] A: «{a[:70]}» · B: «{b[:70]}»")

L.append("\n## #4 — Discriminación de FAMILIA_AMPLIA (necesita negativos de distintas familias)")
L.append(f"Categorías (familias amplias) en alcance: {len(cats)} → {', '.join(cats)}.")
L.append(f"Pares cross-categoría probados: {tot}; el pipeline los separa por categoría en **{ok_sep}/{tot}**.")
L.append("**ADVERTENCIA:** el 53/53 de FAMILIA_AMPLIA NO mide discriminación: el blocker solo empareja "
         "dentro de la misma categoría, y el verificador DEVUELVE FAM=SI por construcción (hardcode). Nunca "
         "se le presentan pares de distinta familia, así que no hay oportunidad de equivocarse → 53/53 es tautológico.")
L.append("La separación de familias ocurre en el BLOCKER (regla dura de tipo), no en el verificador. "
         "Ejemplos de negativos cross-familia (deberían ser FAMILIA_AMPLIA=NO; el blocker nunca los genera):")
for c1,c2,a,b,sep in negs:
    L.append(f"- {c1} ≠ {c2} (separados por categoría: {sep})")
    L.append(f"    - A: «{a[:70]}» · B: «{b[:70]}»")
open(os.path.join(OUT,"auditoria_precauciones.md"),"w").write("\n".join(L))
print("escrito reportes/auditoria_precauciones.md")
print("#3 transiciones:",dict(trans)," riesgo_una:",riesgo_una," riesgo_ambas:",riesgo_ambas)
print("#4 cross-cat separados:",f"{ok_sep}/{tot}")
