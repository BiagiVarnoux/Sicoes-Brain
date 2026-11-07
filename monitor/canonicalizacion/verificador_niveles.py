#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 3 — VERIFICADOR POR NIVELES. SOLO LECTURA, entorno aislado. PIPELINE EXPERIMENTAL NO VALIDADO.
=============================================================================================
Toma los PARES CANDIDATOS del blocker (Etapa 2) y emite, POR SEPARADO, tres veredictos por par:
    FAMILIA_AMPLIA      ∈ {SI, NO, INSUF}   (equivalencia comercial amplia: mismo tipo)
    SUBFAMILIA          ∈ {SI, NO, INSUF}   (misma familia de demanda: mismo segmento)
    PRODUCTO_ESPECIFICO ∈ {SI, NO, INSUF}   (identidad exacta / intercambiable)

Jerarquía: mismo específico ⟹ misma subfamilia ⟹ misma familia amplia. Una diferencia discriminante
puede dejar misma familia sin el mismo específico. Atributo AUSENTE nunca = igual → si falta evidencia
(y no hay contradicción) = INSUF; contradicción confirmada manda = NO.

Mantiene SEPARADOS tres conceptos: equivalencia comercial (amplia) ≠ misma familia de demanda
(subfamilia) ≠ identidad exacta (específico). Para licitaciones, dos descripciones pueden ser demanda
comparable (misma subfamilia) sin exigir idéntica marca/presentación (eso es el nivel específico).

CAPA CORRECTIVA DEL VERIFICADOR (2026-11-07, extractor CONGELADO como línea base): resuelve defectos
semánticos detectados por revisión (ChatGPT). Causas raíz, NO ajuste a muestras:
  - óptico: distinguir +R/−R (polaridad) y presentación con/sin caja (específico).
  - papel impreso: la IDENTIDAD es el membrete/institución, no solo tamaño+gramaje → firma de membrete.
  - sobres: café y madera son el MISMO color comercial (kraft) → se normalizan (evita falso negativo).
  - almacenamiento: SATA 3.0 ES SATA → la versión no es incompatibilidad (se normaliza a familia base).
  - normalización: erratas evidentes de tamaño ("OFICIIO"→oficio), tolerancia estrecha.
NO fusiona, NO escribe en BD, NO migra, NO toca producción. La agrupación final y la agregación de
demanda (con prevención de fusión por transitividad) son etapas POSTERIORES, no se hacen aquí.
"""
import os, sys, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, categoria, nrm, tamano_papel
from blocker_candidatos import construir, pares, get, cuerpo
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes"); os.makedirs(OUT,exist_ok=True)

# ── llaves de comparación por nivel (prioridades del usuario) ─────────────────────────────────────
VERIF_SEG={
 "llanta":["medida"], "sobre_manila":["tamano"], "papel_bond":["tamano","gramaje_gm2"],
 "papel_continuo":["formato_continuo","partes"], "papel_impreso":["tamano"],
 "ram":["generacion","capacidad_gb"], "almacenamiento":["tecnologia","capacidad_gb"],
 "optico":["tipo_medio","capacidad_gb"],
}
# ESPECÍFICO base (línea anterior) y ESPECÍFICO con la capa correctiva (añade grabacion_pol/presentacion/membrete)
VERIF_ESP_BASE={
 "llanta":["tipo_constr","camara","pliegues","huella"], "sobre_manila":["gramaje_gm2","color"],
 "papel_bond":["color"], "papel_continuo":["gramaje_gm2","tipo"], "papel_impreso":["gramaje_gm2","color"],
 "ram":["frecuencia_mhz","formato"], "almacenamiento":["interfaz","formato"], "optico":["tipo_grabacion"],
}
VERIF_ESP={
 "llanta":["tipo_constr","camara","pliegues","huella"], "sobre_manila":["gramaje_gm2","color"],
 "papel_bond":["color"], "papel_continuo":["gramaje_gm2","tipo"],
 "papel_impreso":["gramaje_gm2","color","membrete"],
 "ram":["frecuencia_mhz","formato"], "almacenamiento":["interfaz","formato"],
 "optico":["tipo_grabacion","grabacion_pol","presentacion"],
}
# normalización de VALORES equivalentes (verifier-side; el extractor sigue congelado)
_COLOR_SINON={"madera":"cafe","anaranjado":"naranja"}   # café = madera (kraft); equivalentes comerciales
_IFACE_BASE ={"sata3":"sata"}                            # SATA 3.0 es SATA (familia base, no incompatibilidad)
def _nv(attr,v):
    if attr=="color": return _COLOR_SINON.get(v,v)
    if attr=="interfaz": return _IFACE_BASE.get(v,v)
    return v

_MISSING=object()
def _cmp(A,B,keys,norm=True):
    diff=missing=False; reasons=[]
    for k in keys:
        va=A.get(k,_MISSING); vb=B.get(k,_MISSING)
        if va is _MISSING or vb is _MISSING:
            missing=True; falta="A" if va is _MISSING else ""; falta+="B" if vb is _MISSING else ""
            reasons.append(f"{k}: falta en {falta}")
        else:
            na,nb=(_nv(k,va),_nv(k,vb)) if norm else (va,vb)
            if na!=nb: diff=True; reasons.append(f"{k}: {json.dumps(na,ensure_ascii=False)} ≠ {json.dumps(nb,ensure_ascii=False)}")
            else: reasons.append(f"{k}: = {json.dumps(na,ensure_ascii=False)}")
    if diff: return "NO",reasons
    if missing: return "INSUF",reasons
    return "SI",reasons

# ── capa correctiva: atributos re-derivados del texto crudo (extractor congelado) ─────────────────
_MEMB_STOP=set(("hoja hojas papel membretada membretado membrete tamano tamaño oficio carta memorandum "
 "a4 a3 impresion impresión full color anverso reverso paquete unidad por con del las los la el de en y "
 "cm mm grs gr trabajo x de").split())
def _membrete_firma(n):
    m=re.search(r"membretad[ao]|membrete",n)
    if not m: return None
    resto=n[m.end():]
    resto=re.sub(r"\(.*?\)"," ",resto); resto=re.sub(r"[^a-z\s]"," ",resto)
    toks=[t for t in resto.split() if len(t)>2 and t not in _MEMB_STOP]
    return " ".join(sorted(set(toks))) if toks else None
def _tamano_tolerante(n):
    n2=re.sub(r"ofici+o","oficio",n); n2=re.sub(r"oficc+io","oficio",n2)
    r=tamano_papel(n2); return r[0] if r else None
def enriquecer(cat,attrs,raw):
    n=nrm(raw); a=dict(attrs)
    if cat=="optico":
        if re.search(r"(dvd|cd)\s*\+\s*r|\+\s*r\b|\brx?\d*\b",n) and re.search(r"\+\s*r",n): a["grabacion_pol"]="+r"
        elif re.search(r"(dvd|cd)\s*-\s*r|\b-\s*r\b|dvd\s*-\s*r",n): a["grabacion_pol"]="-r"
        if re.search(r"sin\s+caja",n): a["presentacion"]="sin_caja"
        elif re.search(r"con\s+caja|caja plastica|caja plástica|con sobre",n): a["presentacion"]="con_caja"
    if cat in ("papel_bond","papel_impreso","sobre_manila") and "tamano" not in a:
        t=_tamano_tolerante(n)
        if t: a["tamano"]=t
    if cat=="papel_impreso":
        mb=_membrete_firma(n)
        if mb: a["membrete"]=mb
    return a

def verificar(cat,A,B,esp_cfg=VERIF_ESP,norm=True):
    seg=VERIF_SEG[cat]; esp=seg+esp_cfg[cat]
    v_sub,r_sub=_cmp(A,B,seg,norm)
    v_esp,r_esp=_cmp(A,B,esp,norm)
    if v_sub=="NO": v_esp="NO"
    return {"FAMILIA_AMPLIA":"SI","SUBFAMILIA":v_sub,"PRODUCTO_ESPECIFICO":v_esp,
            "razon_subfamilia":"; ".join(r_sub),"razon_especifico":"; ".join(r_esp)}

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
    enr={d:enriquecer(rec[d]["categoria"],rec[d]["atributos"],d) for d in rec}

    # ── doble pase: BASE (línea anterior) vs CORREGIDO (capa correctiva) para aislar impacto ──
    agg=collections.defaultdict(lambda:collections.Counter())
    ejemplos=collections.defaultdict(lambda:collections.defaultdict(list))
    cambios=collections.Counter(); cambios_ej=collections.defaultdict(list); todos=[]
    for cat,comp,a,b in P:
        v=verificar(cat,enr[a],enr[b],VERIF_ESP,norm=True)
        vb=verificar(cat,rec[a]["atributos"],rec[b]["atributos"],VERIF_ESP_BASE,norm=False)
        agg[cat][(v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"])]+=1
        if (vb["SUBFAMILIA"],vb["PRODUCTO_ESPECIFICO"])!=(v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"]):
            tag=f"{cat}: {vb['SUBFAMILIA']}/{vb['PRODUCTO_ESPECIFICO']} → {v['SUBFAMILIA']}/{v['PRODUCTO_ESPECIFICO']}"
            cambios[tag]+=1
            if len(cambios_ej[tag])<3: cambios_ej[tag].append((a,b,v["razon_especifico"]))
        key=(v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"])
        clase={("SI","SI"):"especifico_SI",("SI","INSUF"):"subfam_SI_esp_INSUF",("SI","NO"):"subfam_SI_esp_NO",
               ("NO","NO"):"subfam_NO",("INSUF","INSUF"):"subfam_INSUF",("INSUF","NO"):"subfam_INSUF"}.get(key,f"{key}")
        if len(ejemplos[cat][clase])<4:
            ejemplos[cat][clase].append((a,b, v["razon_subfamilia"] if clase=="subfam_NO" else v["razon_especifico"]))
        todos.append((cat,comp,a,b,v))

    L=["# Etapa 3 — Verificador por niveles (EXPERIMENTAL NO VALIDADO, solo lectura)\n"]
    L.append(f"Universo: **{len(uniq)} descripciones ÚNICAS** (NO los ~7.441 registros hist_items). "
             f"Pares candidatos verificados: **{len(P):,}**. Capa correctiva aplicada (extractor congelado).\n")
    L.append("Tres veredictos SEPARADOS: FAMILIA_AMPLIA (equivalencia comercial) · SUBFAMILIA (misma familia de "
             "demanda) · PRODUCTO_ESPECIFICO (identidad exacta). Atributo ausente ≠ igual → INSUF.\n")
    L.append("## Distribución de veredictos por categoría (SUBFAMILIA × PRODUCTO_ESPECIFICO)")
    L.append("| categoría | pares | sub=SI·esp=SI | sub=SI·esp=INSUF | sub=SI·esp=NO | sub=NO | sub=INSUF |")
    L.append("|---|---|---|---|---|---|---|")
    tot=collections.Counter()
    for cat in sorted(agg):
        c=agg[cat]; n=sum(c.values())
        si_si=c[("SI","SI")]; si_insuf=c[("SI","INSUF")]; si_no=c[("SI","NO")]
        no=sum(v for k,v in c.items() if k[0]=="NO"); insuf=sum(v for k,v in c.items() if k[0]=="INSUF")
        for a_,b_ in [("si_si",si_si),("si_insuf",si_insuf),("si_no",si_no),("no",no),("insuf",insuf),("n",n)]: tot[a_]+=b_
        L.append(f"| {cat} | {n} | {si_si} | {si_insuf} | {si_no} | {no} | {insuf} |")
    L.append(f"| **TOTAL** | **{tot['n']}** | **{tot['si_si']}** | **{tot['si_insuf']}** | **{tot['si_no']}** | **{tot['no']}** | **{tot['insuf']}** |")
    L.append("\n> Son resultados del algoritmo, NO una medición de precisión. Que N pares den 'mismo específico' "
             "NO prueba que sean intercambiables: eso requiere validación independiente a 3 niveles con datos nuevos.")

    # impacto de la capa correctiva (sistémico vs aislado)
    L.append("\n## Impacto de la capa correctiva (base → corregido; aísla sistémico vs aislado)")
    if cambios:
        L.append(f"Pares cuyo veredicto CAMBIÓ: **{sum(cambios.values())}** de {len(P):,}.")
        L.append("| cambio (SUB/ESP base → corregido) | pares |")
        L.append("|---|---|")
        for tag,nn in cambios.most_common(): L.append(f"| {tag} | {nn} |")
        L.append("\nEjemplos de cambios:")
        for tag,nn in cambios.most_common(6):
            for a,b,rz in cambios_ej[tag][:2]:
                L.append(f"- [{tag}] {rz}")
                L.append(f"    - A: «{a[:90]}»")
                L.append(f"    - B: «{b[:90]}»")
    else:
        L.append("Sin cambios de veredicto (ningún par afectado).")

    L.append("\n## Ejemplos trazables (coincidencias y contradicciones)")
    etiq={"especifico_SI":"✅ MISMO ESPECÍFICO","subfam_SI_esp_NO":"≈ MISMA FAMILIA, distinto específico",
          "subfam_SI_esp_INSUF":"≈ MISMA SUBFAMILIA, específico INSUF","subfam_NO":"✗ DISTINTA SUBFAMILIA",
          "subfam_INSUF":"? SUBFAMILIA INSUF (ambiguo)"}
    for cat in sorted(ejemplos):
        L.append(f"\n### {cat}")
        for clase in ["especifico_SI","subfam_SI_esp_NO","subfam_SI_esp_INSUF","subfam_NO","subfam_INSUF"]:
            for a,b,razon in ejemplos[cat].get(clase,[]):
                L.append(f"- {etiq[clase]}  ·  {razon}")
                L.append(f"    - A: «{a[:95]}»"); L.append(f"    - B: «{b[:95]}»")

    # cross-check v2 (ilustrativo, no ajuste)
    V2="/Users/fabriziocuellar/Downloads/validacion_v2_propuesta_chatgpt.csv"
    if os.path.exists(V2):
        import csv
        L.append("\n## Validación cruzada sobre la muestra v2 CONGELADA (ilustrativa, no ajuste)")
        filas=[]
        for row in csv.DictReader(open(V2,encoding="utf-8-sig")):
            rel=(row.get("RELACION(MISMO_ESPECIFICO/MISMA_FAMILIA/DISTINTO/NO_SE)") or "").upper().strip()
            da,db=row["descripcion_A"],row["descripcion_B"]; ca,cb=categoria(nrm(da)),categoria(nrm(db))
            if ca is None or ca!=cb or ca not in VERIF_SEG: continue
            A=enriquecer(ca,extraer(da)["atributos"],da); B=enriquecer(cb,extraer(db)["atributos"],db)
            v=verificar(ca,A,B); filas.append((row.get("par_id",""),ca,rel,v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"],v["razon_subfamilia"]))
        L.append(f"\nPares capturados: {len(filas)}. (MISMA_FAMILIA humano ↔ FAMILIA_AMPLIA=SI; SUBFAMILIA es corte más fino.)")
        L.append("| par | cat | humano (v2) | AMPLIA | SUBFAMILIA | ESPECÍFICO | razón subfamilia |")
        L.append("|---|---|---|---|---|---|---|")
        for pid,ca,rel,vs,ve,rz in filas: L.append(f"| {pid} | {ca} | {rel} | SI | {vs} | {ve} | {rz} |")

    L.append("\n## Pendientes documentados (no resueltos aquí)")
    L.append("- **RAM instalada en equipo** («? Memoria RAM 8GB instalado en un solo slot, expandible…»): "
             "1 sola descripción en el corpus (AISLADO) → no se toca el extractor congelado por un caso; "
             "una regla general podría descartar módulos reales. Pendiente de refinamiento del extractor.")
    L.append("- La firma de membrete es heurística (tokens institucionales); puede marcar NO entre fraseos "
             "distintos de la misma institución. Conservador (evita fusión falsa), a validar con humano.")
    L.append("- Precisión real del verificador: PENDIENTE de muestra NUEVA estratificada por categoría Y "
             "veredicto, etiquetada por separado a los 3 niveles, con falsos+/falsos−/INSUF separando error "
             "de extractor / blocker / verificador. NO implementar agrupación ni agregación hasta entonces.")

    open(os.path.join(OUT,"verificador_reporte.md"),"w").write("\n".join(L))
    import csv as _csv
    with open(os.path.join(OUT,"verificador_veredictos_muestra.csv"),"w",newline="",encoding="utf-8") as fh:
        w=_csv.writer(fh); w.writerow(["familia_amplia_cat","comparten_subfam_blocker","SUBFAMILIA","PRODUCTO_ESPECIFICO",
                                       "razon_subfamilia","razon_especifico","desc_A","desc_B"])
        for cat,comp,a,b,v in todos[:600]:
            w.writerow([cat,comp,v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"],v["razon_subfamilia"],v["razon_especifico"],a[:120],b[:120]])
    print("escrito reportes/verificador_reporte.md + reportes/verificador_veredictos_muestra.csv")
    print("total pares:",len(P)," totales:",dict(tot))
    print("cambios por capa correctiva:",dict(cambios))
