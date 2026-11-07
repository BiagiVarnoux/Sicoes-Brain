#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 3 — VERIFICADOR POR NIVELES. SOLO LECTURA. PIPELINE EXPERIMENTAL NO VALIDADO.
=============================================================================================
Por cada par candidato emite TRES veredictos SEPARADOS:
    FAMILIA_AMPLIA      ∈ {SI, NO, INSUF}   (equivalencia comercial amplia: mismo tipo)
    SUBFAMILIA          ∈ {SI, NO, INSUF}   (misma familia de demanda: mismo segmento)
    PRODUCTO_ESPECIFICO ∈ {SI, NO, INSUF}   (identidad confirmada / intercambiable)

Jerarquía: específico SI ⟹ subfamilia SI ⟹ amplia SI. Atributo AUSENTE nunca = igual.
El veredicto de equivalencia es SEPARADO de la AUTORIZACIÓN a fusionar (fusionar exige ESP=SI; nunca
sobre INSUF). NO fusiona, NO escribe en BD, NO migra, NO toca producción.

FASE DE CORRECCIÓN CONTROLADA (2026-11-07, autorizada). Tres correcciones, aislables por banderas
(línea base congelada en congelado/verificador_niveles_baseline_2ff01aa.py):
  fix3 — SUBFAMILIA: un atributo de segmento AUSENTE mantiene INSUF (no confirma subfamilia); una
         CONTRADICCIÓN baja a NO. (Antes: el "secundario" ausente no degradaba → subía a SI.) 'aplicacion'
         de llanta sigue siendo SOLO-CONTRADICCIÓN (ausencia no degrada) porque no siempre se declara.
  fix2 — PAPEL CONTINUO: se separan `mecanismo_copia` (quimico/autocopiativo vs carbonico) y `desglose`
         (presentación) como atributos INDEPENDIENTES; NO se tratan como sinónimos. químico≠carbónico se
         preserva como diferencia técnica (determinante para DBC); 'desglose' es presentación. Se deja de
         usar el `tipo` colapsado del extractor.
  fix1 — PRODUCTO_ESPECIFICO: criterios SUFICIENTES por categoría (IDENT): ESP=SI exige TODOS los
         atributos de identidad (técnicos + presentación relevante) presentes e iguales y sin requisito
         no acreditado; si falta evidencia → INSUF (candidato, no confirmado); si contradice → NO.
Las muestras previas (53, v2, extractor 220) son ahora PRUEBAS DE REGRESIÓN, no validación independiente.
"""
import os, sys, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extractor_atributos import extraer, categoria, nrm, tamano_papel, _CONCRETO
from blocker_candidatos import construir, pares, get, cuerpo
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes"); os.makedirs(OUT,exist_ok=True)

# ── SEGMENTO (subfamilia). 'aplicacion' de llanta va aparte: solo contradicción. ────────────────
VERIF_SEG={
 "llanta":["medida","aplicacion"], "sobre_manila":["tamano"], "papel_bond":["tamano","gramaje_gm2"],
 "papel_continuo":["formato_continuo","partes","gramaje_gm2"], "papel_impreso":["tamano"],
 "ram":["generacion","capacidad_gb"], "almacenamiento":["tecnologia","capacidad_gb"],
 "optico":["tipo_medio","capacidad_gb"],
}
SEG_CONTRA={"llanta":["aplicacion"]}                 # fix3: solo-contradicción (ausencia no degrada)
BASE_SEG_SEC={"papel_bond":["gramaje_gm2"],"papel_continuo":["gramaje_gm2"],"llanta":["aplicacion"]}  # baseline
# ── IDENT: atributos de IDENTIDAD por categoría para ESP=SI (fix1). ⊇ SEGMENTO (preserva jerarquía) ──
IDENT={
 "llanta":["medida","tipo_constr","camara"],
 "sobre_manila":["tamano","gramaje_gm2","color"],
 "papel_bond":["tamano","gramaje_gm2","color","hojas"],
 "papel_continuo":["formato_continuo","partes","gramaje_gm2"],   # mecanismo_copia se trata SOFT (abajo), no hard
 "papel_impreso":["tamano","membrete"],
 "ram":["generacion","capacidad_gb","frecuencia_mhz","formato"],
 "almacenamiento":["tecnologia","capacidad_gb","interfaz","formato"],
 "optico":["tipo_medio","capacidad_gb","grabacion_pol","presentacion"],
}
# ESPECÍFICO de la LÍNEA BASE (para reproducir 2ff01aa con fix1=False)
BASE_ESP={"llanta":["tipo_constr","camara","pliegues","huella"],"sobre_manila":["gramaje_gm2","color"],
 "papel_bond":["color"],"papel_continuo":["tipo"],"papel_impreso":["gramaje_gm2","color","membrete"],
 "ram":["frecuencia_mhz","formato"],"almacenamiento":["interfaz","formato"],
 "optico":["tipo_grabacion","grabacion_pol","presentacion"]}

# ── HUELLA de llanta (fix4): contradicción SOLO entre grupos técnicamente incompatibles CONFIRMADOS.
# Las denominaciones comerciales ambiguas (todo terreno/A-T, normal, lisa, pantanera↔semipantanera) NO
# se declaran contradicción → INSUF. Ausencia NO degrada. (Precaución de normalización de ChatGPT.)
_HUELLA_GRUPO={"pantanera":"barro","semi pantanera":"barro","semipantanera":"barro","autopista":"carretera"}
def _huella_incompat(a,b):
    ga,gb=_HUELLA_GRUPO.get(a),_HUELLA_GRUPO.get(b)
    return ga is not None and gb is not None and ga!=gb   # barro vs carretera = incompatible confirmado
_COLOR_SINON={"madera":"cafe","anaranjado":"naranja"}
_IFACE_BASE ={"sata3":"sata"}
_TIPO_CONT  ={"quimico":"autocopiativo","desglose":"autocopiativo","carbonico":"autocopiativo","autocopiativo":"autocopiativo"}  # solo baseline
def _nv(attr,v):
    if attr=="color": return _COLOR_SINON.get(v,v)
    if attr=="interfaz": return _IFACE_BASE.get(v,v)
    if attr=="tipo": return _TIPO_CONT.get(v,v)   # solo se usa en baseline (fix2=False)
    return v

_M=object()
def _cmp(A,B,keys,norm=True):
    diff=missing=False; reasons=[]
    for k in keys:
        va=A.get(k,_M); vb=B.get(k,_M)
        if va is _M or vb is _M:
            missing=True; f=("A" if va is _M else "")+("B" if vb is _M else ""); reasons.append(f"{k}: falta en {f}")
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
    resto=re.sub(r"\(.*?\)"," ",n[m.end():]); resto=re.sub(r"[^a-z\s]"," ",resto)
    toks=[t for t in resto.split() if len(t)>2 and t not in _MEMB_STOP]
    return " ".join(sorted(set(toks))) if toks else None
def _tamano_tolerante(n):
    n2=re.sub(r"ofici+o","oficio",n); n2=re.sub(r"oficc+io","oficio",n2)
    r=tamano_papel(n2); return r[0] if r else None
def _color_tolerante(n):
    found=re.findall(r"\b("+_CONCRETO+r")",n)
    distintos=sorted({_COLOR_SINON.get(c,c) for c in found})
    if re.search(r"\bsurtido|\bcolores\b|\bvarios\b|multicolor",n): return "surtido"
    if len(distintos)>=2: return "surtido"
    return found[0] if found else None
def _continuo_tolerante(n):
    f="9.5x11" if re.search(r"9\s*[.,]?\s*(?:1/2|½|\.5)?\s*[x*×]\s*11",n) else None
    m=re.search(r"11\s*[x*×]\s*(\d)",n); p=int(m.group(1)) if m else None
    return f,p
def _aplicacion(n):
    if re.search(r"\b(moto|motocicleta)\b",n): return "moto"
    if re.search(r"\b(automotor|automovil|camioneta|vehiculo|auto)\b",n): return "auto"
    return None
def _mecanismo_copia(n):   # químico/autocopiativo = NCR; carbónico = carbón (DISTINTO). NO equiparar.
    if re.search(r"\bcarbonico\b|papel carbon",n): return "carbonico"
    if re.search(r"\bquimico\b|autocopiativ|autocopiante|auto copiante",n): return "quimico"
    return None
def _desglose(n):          # presentación (separable), ortogonal al mecanismo
    return "si" if re.search(r"desglose|con calca|\bcalca\b",n) else None
def _empaque_unidad(n):    # unidad del empaque: juegos ≠ hojas (no equiparables)
    if re.search(r"\bjgs\b|juegos?\b",n): return "juegos"
    if re.search(r"\bhojas?\b",n): return "hojas"
    return None
_RES_PATS=[("iso",r"\biso\s*\d{3,5}"),("alcalino",r"alcalin|alkalin"),("certif",r"certificaci")]
def _residual(n):          # requisitos normativos/material exigidos en un lado (exime "o (su) equivalente")
    out=set()
    for name,pat in _RES_PATS:
        for m in re.finditer(pat,n):
            if re.search(r"\bo\s+(su\s+)?equivalente",n[m.end():m.end()+25]): continue
            out.add(name)
    return frozenset(out)

def enriquecer(cat,attrs,raw):
    n=nrm(raw); a=dict(attrs)
    if cat=="optico":
        if re.search(r"\+\s*r",n): a["grabacion_pol"]="+r"
        elif re.search(r"(dvd|cd)\s*-\s*r|\b-\s*r\b",n): a["grabacion_pol"]="-r"
        if re.search(r"sin\s+caja",n): a["presentacion"]="sin_caja"
        elif re.search(r"con\s+caja|caja plastica|caja plástica|con sobre|con tapa",n): a["presentacion"]="con_caja"
        if a.get("grabacion_pol") in ("+r","-r") and "tipo_grabacion" not in a: a["tipo_grabacion"]="r"
    if cat in ("papel_bond","papel_impreso","sobre_manila") and "tamano" not in a:
        t=_tamano_tolerante(n)
        if t: a["tamano"]=t
    if cat in ("papel_bond","papel_impreso","sobre_manila") and "color" not in a:
        c=_color_tolerante(n)
        if c: a["color"]=c
    if cat=="papel_continuo":
        if "formato_continuo" not in a:
            f,p=_continuo_tolerante(n)
            if f: a["formato_continuo"]=f
            if p and "partes" not in a: a["partes"]=p
        mec=_mecanismo_copia(n);  des=_desglose(n);  emp=_empaque_unidad(n)
        if mec: a["mecanismo_copia"]=mec
        if des: a["desglose"]=des
        if emp: a["empaque_unidad"]=emp
    if cat=="papel_impreso":
        mb=_membrete_firma(n)
        if mb: a["membrete"]=mb
    if cat=="llanta":
        ap=_aplicacion(n)
        if ap: a["aplicacion"]=ap
    if cat in ("papel_bond","papel_impreso","papel_continuo","sobre_manila"):
        a["_residual"]=_residual(n)
    return a

def _esp_fix1(cat,A,B):
    v,reasons=_cmp(A,B,IDENT[cat],norm=True)          # differ→NO, falta→INSUF, todo igual→SI
    if v=="NO": return "NO",reasons
    ua,ub=A.get("empaque_unidad"),B.get("empaque_unidad")   # juegos ≠ hojas: no equiparable
    if ua and ub and ua!=ub:
        reasons.append(f"empaque: {ua} ≠ {ub} (no equiparable)")
        if v=="SI": v="INSUF"
    ra,rb=A.get("_residual",frozenset()),B.get("_residual",frozenset())   # requisito no acreditado en un lado
    if ra!=rb:
        reasons.append(f"requisito no acreditado: {sorted(ra^rb)}")
        if v=="SI": v="INSUF"
    return v,reasons

def verificar(cat,A,B,fix1=True,fix2=True,fix3=True,fix4=True):
    seg=VERIF_SEG[cat]
    contra = SEG_CONTRA.get(cat,[]) if fix3 else BASE_SEG_SEC.get(cat,[])
    required=[k for k in seg if k not in contra]
    v_sub,r_sub=_cmp(A,B,required,norm=True)
    for k in contra:
        va=A.get(k,_M); vb=B.get(k,_M)
        if va is not _M and vb is not _M:
            na,nb=_nv(k,va),_nv(k,vb)
            if na!=nb: v_sub="NO"; r_sub.append(f"{k}: {json.dumps(na,ensure_ascii=False)} ≠ {json.dumps(nb,ensure_ascii=False)} (contradicción)")
            else: r_sub.append(f"{k}: = {json.dumps(na,ensure_ascii=False)}")
        else: r_sub.append(f"{k}: falta (solo-contradicción, no degrada)")
    if v_sub=="NO":
        v_esp,r_esp="NO",["subfamilia NO"]
    else:
        if fix1:
            v_esp,r_esp=_esp_fix1(cat,A,B)
        else:
            espkeys = seg + (BASE_ESP[cat] if not (fix2 and cat=="papel_continuo") else [])  # fix2: quita 'tipo' colapsado
            v_esp,r_esp=_cmp(A,B,espkeys,norm=True)
        # #2 mecanismo de copia SOFT (quimico/autocopiativo vs carbonico): diferencia o ausencia → INSUF,
        # NUNCA NO (terminología imprecisa en pliegos; preserva la diferencia como candidato, no la afirma).
        if (fix2 or fix1) and cat=="papel_continuo":
            ma=A.get("mecanismo_copia"); mb=B.get("mecanismo_copia")
            if ma and mb and ma!=mb:
                if v_esp=="SI": v_esp="INSUF"
                r_esp.append("mecanismo_copia difiere (quimico/carbonico) → no confirmado (revisar DBC)")
            elif (ma is None)!=(mb is None):
                if v_esp=="SI": v_esp="INSUF"
                r_esp.append("mecanismo_copia ausente en un lado → no confirmado")
        # #4 LLANTA: recuperar huella y pliegues como DISCRIMINANTES solo-contradicción (no en IDENT duro:
        # su ausencia NO degrada). Contradicción técnica CONFIRMADA → NO; diferencia AMBIGUA → INSUF.
        if fix4 and cat=="llanta" and v_esp!="NO":
            ha,hb=A.get("huella"),B.get("huella")
            if ha and hb and ha!=hb:
                if _huella_incompat(ha,hb):
                    v_esp="NO"; r_esp.append(f"huella: {ha} ≠ {hb} (incompatible barro/carretera → distinto)")
                else:
                    if v_esp=="SI": v_esp="INSUF"
                    r_esp.append(f"huella: {ha} ≠ {hb} (denominación ambigua → no confirmado)")
            pa,pb=A.get("pliegues"),B.get("pliegues")
            if pa and pb and pa!=pb and v_esp!="NO":
                v_esp="NO"; r_esp.append(f"pliegues: {pa} ≠ {pb} (lona/carga distinta → distinto)")
    return {"FAMILIA_AMPLIA":"SI","SUBFAMILIA":v_sub,"PRODUCTO_ESPECIFICO":v_esp,
            "razon_subfamilia":"; ".join(r_sub),"razon_especifico":"; ".join(r_esp)}

if __name__=="__main__":
    items=get("hist_items?select=id,cuce,descripcion")
    por_desc=collections.defaultdict(list)
    for it in items:
        c=cuerpo(it["descripcion"])
        if c: por_desc[c].append(it)
    uniq=sorted(por_desc); uniq_rec={d:extraer(d) for d in uniq}
    amplia,subfam,solo_amplia,estado,rec=construir(uniq_rec)
    P=pares(amplia,rec)
    enr={d:enriquecer(rec[d]["categoria"],rec[d]["atributos"],d) for d in rec}

    STAGES=[("0 baseline",dict(fix1=False,fix2=False,fix3=False)),
            ("1 +#3 secundarios",dict(fix1=False,fix2=False,fix3=True)),
            ("2 +#2 mecanismo",dict(fix1=False,fix2=True,fix3=True)),
            ("3 +#1 identidad",dict(fix1=True,fix2=True,fix3=True))]
    estados={nombre:[] for nombre,_ in STAGES}
    for cat,comp,a,b in P:
        for nombre,fl in STAGES:
            v=verificar(cat,enr[a],enr[b],**fl)
            estados[nombre].append((v["SUBFAMILIA"],v["PRODUCTO_ESPECIFICO"]))
    def dist(lst):
        c=collections.Counter(lst)
        return {"SUB_SI":sum(v for k,v in c.items() if k[0]=="SI"),"SUB_NO":sum(v for k,v in c.items() if k[0]=="NO"),
                "SUB_INSUF":sum(v for k,v in c.items() if k[0]=="INSUF"),
                "ESP_SI":sum(v for k,v in c.items() if k[1]=="SI"),"ESP_NO":sum(v for k,v in c.items() if k[1]=="NO"),
                "ESP_INSUF":sum(v for k,v in c.items() if k[1]=="INSUF")}
    L=["# Etapa 3 — Impacto de la fase de corrección controlada (#3→#2→#1) sobre 9.828 pares\n"]
    L.append(f"Universo: {len(uniq)} descripciones únicas; {len(P):,} pares candidatos. Línea base = commit "
             "2ff01aa (congelada). Cada etapa añade UNA corrección sobre la anterior (aislamiento acumulativo).\n")
    L.append("## Distribución por etapa")
    L.append("| etapa | SUB SI | SUB NO | SUB INSUF | ESP SI | ESP NO | ESP INSUF |"); L.append("|"+"---|"*7)
    for nombre,_ in STAGES:
        d=dist(estados[nombre])
        L.append(f"| {nombre} | {d['SUB_SI']} | {d['SUB_NO']} | {d['SUB_INSUF']} | {d['ESP_SI']} | {d['ESP_NO']} | {d['ESP_INSUF']} |")
    # transiciones entre etapas consecutivas (registra TODAS; marca entradas a NO)
    L.append("\n## Transiciones entre etapas consecutivas (estado = SUBFAMILIA/PRODUCTO_ESPECIFICO)")
    for i in range(1,len(STAGES)):
        pn,_=STAGES[i-1]; cn,_=STAGES[i]
        trans=collections.Counter()
        hacia_no=0
        for j in range(len(P)):
            s0=estados[pn][j]; s1=estados[cn][j]
            if s0!=s1:
                trans[(s0,s1)]+=1
                if (s1[0]=="NO" and s0[0]!="NO") or (s1[1]=="NO" and s0[1]!="NO"): hacia_no+=1
        L.append(f"\n### {pn} → {cn}: {sum(trans.values())} pares cambian · **hacia NO nuevo: {hacia_no}**")
        L.append("| de (SUB/ESP) | a (SUB/ESP) | pares |"); L.append("|---|---|---|")
        for (s0,s1),nn in trans.most_common():
            L.append(f"| {s0[0]}/{s0[1]} | {s1[0]}/{s1[1]} | {nn} |")
    open(os.path.join(OUT,"verificador_impacto_correcciones.md"),"w").write("\n".join(L))
    print("escrito reportes/verificador_impacto_correcciones.md")
    for nombre,_ in STAGES: print(nombre, dist(estados[nombre]))
