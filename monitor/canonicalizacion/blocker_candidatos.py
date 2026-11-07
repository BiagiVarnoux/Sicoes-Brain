#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 2 — BLOCKER (generador de candidatos) por ATRIBUTOS. SOLO LECTURA, entorno aislado.
=============================================================================================
Función (B) del diseño v2, SEPARADA de extracción y verificación. GRUESO: NUNCA fusiona; solo
emite PARES CANDIDATOS para que el verificador (Etapa 3) asigne el veredicto por nivel.
NO escribe en la BD, NO migra, NO toca producción.

Principios del diseño aprobado:
  - BLOQUEO ≠ NIVEL. El bloque es la red de candidatos (grueso); el nivel {amplia/subfamilia/especifico}
    lo decide el verificador. Aquí NO se fusiona ni se asigna familia.
  - Red por FAMILIA AMPLIA = categoría (= tipo). Dos ítems del MISMO tipo son candidatos aunque difieran
    en toda otra característica (ej. SSD 256 vs SSD 1TB). Tipos distintos NUNCA son equivalentes
    (restricción dura de tipo) → no se cruzan (descarte auditable, no pérdida silenciosa).
    NOTA: que no haya pérdidas por construcción dentro del tipo modelado es una propiedad de DISEÑO,
    PENDIENTE de validación independiente; no se afirma como hecho probado.
  - Multi-señal: cada ítem lleva además su llave de SUBFAMILIA (categoría+valores de segmento EXACTOS)
    como ETIQUETA del par (comparten_subfamilia), no como filtro.
  - Ajuste #1: cobertura y descartes AGREGADOS y auditables (no par por par).
  - Ajuste #3: no se fusiona por transitividad — aquí ni siquiera se fusiona; solo pares.

Las cifras de cobertura son sobre DESCRIPCIONES ÚNICAS (≈5.067), NO sobre los registros hist_items (≈7.441).
Categorías de código (consumible_impresion) → delegadas al motor v2 por firmas; NO se re-bloquean aquí.
"""
import os, sys, json, csv, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, categoria, nrm, get, cuerpo, SEGMENTO
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes"); os.makedirs(OUT,exist_ok=True)

ATRIBUTO_CATS=set(SEGMENTO.keys())   # almacenamiento, optico, ram, papel_*, sobre_manila, llanta
DELEGADO={"consumible_impresion"}

def subfam_key(cat,attrs):
    seg=SEGMENTO.get(cat,[])
    if seg and all(a in attrs for a in seg):
        return cat+"|"+"|".join(f"{a}={json.dumps(attrs[a],ensure_ascii=False,sort_keys=True)}" for a in seg)
    return None   # sin segmento completo → solo familia amplia

def construir(uniq_rec):
    """uniq_rec: dict desc->registro extraer(). Devuelve bloques y pares candidatos."""
    amplia=collections.defaultdict(list); subfam=collections.defaultdict(set); solo_amplia=collections.Counter()
    estado=collections.Counter(); rec={}
    for d,r in uniq_rec.items():
        if r is None: estado["fuera_alcance (None)"]+=1; continue
        cat=r["categoria"]
        if cat in DELEGADO: estado["delegado_motor (consumible)"]+=1; continue
        if cat in ATRIBUTO_CATS:
            estado["en_alcance (atributos)"]+=1; amplia[cat].append(d); rec[d]=r
            sk=subfam_key(cat,r["atributos"])
            if sk: subfam[cat].add(sk)
            else: solo_amplia[cat]+=1
        else: estado["otra_categoria"]+=1
    return amplia,subfam,solo_amplia,estado,rec

def pares(amplia,rec):
    """Genera pares candidatos DENTRO de cada familia amplia. Devuelve lista [(cat,comp,a,b)]."""
    out=[]
    for cat,descs in amplia.items():
        for a,b in itertools.combinations(sorted(descs),2):
            ka=subfam_key(cat,rec[a]["atributos"]); kb=subfam_key(cat,rec[b]["atributos"])
            out.append((cat,(ka is not None and ka==kb),a,b))
    return out

if __name__=="__main__":
    items=get("hist_items?select=id,cuce,descripcion")
    por_desc=collections.defaultdict(list)
    for it in items:
        c=cuerpo(it["descripcion"])
        if c: por_desc[c].append(it)
    uniq=sorted(por_desc)
    uniq_rec={d:extraer(d) for d in uniq}
    amplia,subfam,solo_amplia,estado,rec=construir(uniq_rec)
    P=pares(amplia,rec)
    pares_por_cat=collections.Counter(c for c,_,_,_ in P)
    comparten_sub=collections.Counter(c for c,comp,_,_ in P if comp)

    tot_alcance=sum(len(v) for v in amplia.values())
    pares_intra=len(P); pares_total=tot_alcance*(tot_alcance-1)//2; pares_cross=pares_total-pares_intra

    # blocker-recall sobre la muestra v2 CONGELADA (validación, no ajuste)
    V2="/Users/fabriziocuellar/Downloads/validacion_v2_propuesta_chatgpt.csv"
    recall_txt=""
    if os.path.exists(V2):
        reales=capt=esp_r=esp_c=0; miss=[]
        for row in csv.DictReader(open(V2,encoding="utf-8-sig")):
            rel=(row.get("RELACION(MISMO_ESPECIFICO/MISMA_FAMILIA/DISTINTO/NO_SE)") or row.get("REVISION_CHATGPT") or "").upper()
            if "MISMO_ESPECIFICO" in rel or "MISMA_FAMILIA" in rel:
                reales+=1; esp="MISMO_ESPECIFICO" in rel; esp_r+=esp
                ca,cb=categoria(nrm(row["descripcion_A"])),categoria(nrm(row["descripcion_B"]))
                if ca is not None and ca==cb and ca in ATRIBUTO_CATS: capt+=1; esp_c+=esp
                else: miss.append((ca,cb,row["descripcion_A"][:40],row["descripcion_B"][:40]))
        recall_txt=(f"\n## (validación) Blocker-recall sobre la muestra v2 CONGELADA (no se ajustó nada con ella)\n"
                    f"- Relaciones reales (específico+familia): {reales}\n"
                    f"- Capturadas (misma familia amplia=tipo): **{capt}/{reales} ({100*capt//max(reales,1)}%)** "
                    f"— generador anterior por firmas: 36% (10/28).\n- MISMO_ESPECIFICO: {esp_c}/{esp_r}.\n")
        if miss:
            recall_txt+=f"- {len(miss)} no capturados (categorías aún no modeladas por la Etapa 1 → None):\n"
            for ca,cb,a,b in miss: recall_txt+=f"  - [{ca} vs {cb}] «{a}» ↔ «{b}»\n"

    L=["# Etapa 2 — Blocker de candidatos por atributos (cobertura y descartes, solo lectura)\n"]
    L.append(f"Universo: **{len(uniq)} descripciones ÚNICAS** (NO los ~7.441 registros hist_items).\n")
    L.append("## Estado de los ítems (cobertura global, sobre descripciones únicas)")
    for k,v in estado.most_common(): L.append(f"- {k}: {v}")
    L.append(f"\n**En alcance del blocker por atributos: {tot_alcance}** (categorías: {', '.join(sorted(amplia))})")
    L.append(f"\n> Suma de estados = {sum(estado.values())} descripciones únicas.")
    L.append("\n## Por familia amplia (= categoría = tipo)")
    L.append("| categoría | ítems | subfamilias distintas | solo familia_amplia | pares candidatos | comparten subfamilia |")
    L.append("|---|---|---|---|---|---|")
    for cat in sorted(amplia):
        L.append(f"| {cat} | {len(amplia[cat])} | {len(subfam[cat])} | {solo_amplia[cat]} | {pares_por_cat[cat]} | {comparten_sub[cat]} |")
    L.append(f"\n## Descartes AGREGADOS y auditables")
    L.append(f"- Pares cross-categoría NO generados (restricción dura de tipo): **{pares_cross:,}** de {pares_total:,} posibles entre ítems en alcance.")
    L.append(f"- Ítems delegados al motor v2 por código (consumible_impresion): {estado.get('delegado_motor (consumible)',0)}.")
    L.append(f"- Ítems fuera de alcance (equipos/accesorios/otros): {estado.get('fuera_alcance (None)',0)+estado.get('otra_categoria',0)}.")
    L.append(f"- Ítems en alcance SIN segmento completo (candidatos solo a familia_amplia): {sum(solo_amplia.values())} (no se pierden; el verificador decide).")
    L.append("\n## Nota de diseño")
    L.append("El blocker NO fusiona ni asigna familia: solo propone pares candidatos dentro del mismo tipo. "
             "`comparten_subfamilia` es una ETIQUETA del par, no un filtro. Los pares cross-tipo se descartan "
             "por regla dura de tipo (agregado). La ausencia de pérdidas dentro del tipo modelado es de DISEÑO, "
             "pendiente de validación independiente.")
    L.append(recall_txt)
    open(os.path.join(OUT,"blocker_cobertura.md"),"w").write("\n".join(L))

    with open(os.path.join(OUT,"blocker_candidatos_muestra.csv"),"w",newline="",encoding="utf-8") as fh:
        w=csv.writer(fh); w.writerow(["familia_amplia","comparten_subfamilia","desc_A","desc_B","attrs_A","attrs_B"])
        for cat,comp,a,b in P[:400]:
            w.writerow([cat,comp,a[:120],b[:120],
                        json.dumps(rec[a]["atributos"],ensure_ascii=False,sort_keys=True),
                        json.dumps(rec[b]["atributos"],ensure_ascii=False,sort_keys=True)])
    print("escrito reportes/blocker_cobertura.md + reportes/blocker_candidatos_muestra.csv")
    print("estado:",dict(estado)); print("pares por categoría:",dict(pares_por_cat)); print(recall_txt)
