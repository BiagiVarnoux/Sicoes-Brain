#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUDITORÍA FINAL DE CALIDAD (SOLO ANÁLISIS, NO MODIFICA REGLAS) — 2026-11-07
=============================================================================================
Pedida tras la fase de corrección controlada, ANTES de autorizar agrupación. No cambia el
verificador ni las muestras. Reutiliza verificar()/enriquecer() tal como quedaron congelados
en el commit de la fase de corrección. Responde los 6 puntos del pedido:
  1. Las 7 transiciones ESP INSUF→SI y las 2 ESP NO→INSUF de #1 (caso por caso, trazable).
  2. Distribución final de los 595 ESP=SI por categoría + ejemplos + casos dudosos.
  3. Auditoría de los conjuntos IDENT por categoría (obligatorio/discrimina/complementario).
  4. Los 2.699 ESP=INSUF por categoría y MOTIVO (ausencia real / fallo extractor / no modelado).
  5. Reglas potencialmente demasiado estrictas (sin relajarlas).
  6. Consistencia jerárquica de los 595 ESP=SI con SUBFAMILIA y FAMILIA_AMPLIA.
Salida: reportes/auditoria_final.md
"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verificador_niveles import (verificar, enriquecer, VERIF_SEG, SEG_CONTRA, IDENT, BASE_ESP, OUT)
from extractor_atributos import extraer
from blocker_candidatos import construir, pares, get, cuerpo

def short(s,n=68): return (s[:n]+"…") if len(s)>n else s

items=get("hist_items?select=id,cuce,descripcion")
por_desc=collections.defaultdict(list)
for it in items:
    c=cuerpo(it["descripcion"])
    if c: por_desc[c].append(it)
uniq=sorted(por_desc); uniq_rec={d:extraer(d) for d in uniq}
amplia,subfam,solo_amplia,estado,rec=construir(uniq_rec)
P=pares(amplia,rec)
enr={d:enriquecer(rec[d]["categoria"],rec[d]["atributos"],d) for d in rec}

# precompute veredictos etapa 2 (+#2, sin #1) y etapa 3 (+#1) para cada par
FL2=dict(fix1=False,fix2=True,fix3=True)   # etapa 2
FL3=dict(fix1=True,fix2=True,fix3=True)    # etapa 3 (actual)
V2={}; V3={}
for cat,comp,a,b in P:
    V2[(a,b)]=verificar(cat,enr[a],enr[b],**FL2)
    V3[(a,b)]=verificar(cat,enr[a],enr[b],**FL3)

L=["# Auditoría final de calidad — verificador tras fase de corrección (SOLO ANÁLISIS)\n",
   "No modifica reglas ni muestras. Reejecuta el verificador congelado. Los 22/22/22 previos son "
   "REGRESIÓN, no validación independiente de esta versión.\n",
   f"Universo: {len(uniq)} descripciones únicas, {len(P):,} pares candidatos. "
   "Recordatorio: son pares, no productos independientes; un error de extracción afecta muchos pares.\n"]

# ── 1. Transiciones de #1: ESP INSUF→SI (7) y ESP NO→INSUF (2) ──────────────────────────────
L.append("## 1. Transiciones no-conservadoras de la corrección #1 (etapa 2 → etapa 3)\n")
insuf_si=[]; no_insuf=[]
for cat,comp,a,b in P:
    e2=V2[(a,b)]["PRODUCTO_ESPECIFICO"]; e3=V3[(a,b)]["PRODUCTO_ESPECIFICO"]
    if e2=="INSUF" and e3=="SI": insuf_si.append((cat,a,b))
    if e2=="NO" and e3=="INSUF": no_insuf.append((cat,a,b))
L.append(f"**ESP INSUF→SI: {len(insuf_si)} pares.** ESP NO→INSUF: {len(no_insuf)} pares. "
         "(Toda nueva confirmación o descontradicción se examina individualmente.)\n")
L.append("### 1a. INSUF→SI (nuevas confirmaciones — ¿sustentadas?)")
for cat,a,b in insuf_si:
    r2=V2[(a,b)]["razon_especifico"]; r3=V3[(a,b)]["razon_especifico"]
    L.append(f"- **[{cat}]** A=`{short(a)}` | B=`{short(b)}`")
    L.append(f"    - etapa2(INSUF): {r2 or '(sin razón)'}  →  etapa3(SI): {r3 or '(sin razón)'}")
L.append("\n### 1b. NO→INSUF (contradicciones que dejaron de serlo — ¿válido?)")
for cat,a,b in no_insuf:
    r2=V2[(a,b)]["razon_especifico"]; r3=V3[(a,b)]["razon_especifico"]
    L.append(f"- **[{cat}]** A=`{short(a)}` | B=`{short(b)}`")
    L.append(f"    - etapa2(NO): {r2 or '(sin razón)'}  →  etapa3(INSUF): {r3 or '(sin razón)'}")

# ── 2 y 6. 595 ESP=SI: distribución por categoría + consistencia jerárquica ─────────────────
esp_si=[(cat,a,b) for cat,comp,a,b in P if V3[(a,b)]["PRODUCTO_ESPECIFICO"]=="SI"]
L.append(f"\n## 2. Distribución de los {len(esp_si)} pares ESP=SI por categoría\n")
cat_si=collections.Counter(cat for cat,a,b in esp_si)
L.append("| categoría | ESP=SI |"); L.append("|---|---|")
for c,n in cat_si.most_common(): L.append(f"| {c} | {n} |")
L.append("\n### Ejemplos representativos (hasta 2 por categoría)")
seen=set()
for cat,a,b in esp_si:
    if cat in seen: continue
    seen.add(cat)
    ej=[p for p in esp_si if p[0]==cat][:2]
    for _,x,y in ej:
        L.append(f"- **[{cat}]** `{short(x)}` ≡ `{short(y)}`")

# 6. consistencia jerárquica: ESP=SI debe tener SUB=SI y FAM=SI
L.append(f"\n## 6. Consistencia jerárquica de los {len(esp_si)} ESP=SI")
viol=[(cat,a,b,V3[(a,b)]["SUBFAMILIA"],V3[(a,b)]["FAMILIA_AMPLIA"])
      for cat,a,b in esp_si if V3[(a,b)]["SUBFAMILIA"]!="SI" or V3[(a,b)]["FAMILIA_AMPLIA"]!="SI"]
if not viol:
    L.append("- **OK: los %d ESP=SI tienen SUBFAMILIA=SI y FAMILIA_AMPLIA=SI.** Jerarquía respetada "
             "(ESP=SI ⟹ SUB=SI ⟹ FAM=SI)." % len(esp_si))
else:
    L.append(f"- **{len(viol)} violaciones jerárquicas:**")
    for cat,a,b,s,f in viol[:20]: L.append(f"    - [{cat}] SUB={s} FAM={f} — `{short(a)}` ≡ `{short(b)}`")

# ── 4. 2.699 ESP=INSUF por categoría y motivo ───────────────────────────────────────────────
esp_insuf=[(cat,a,b) for cat,comp,a,b in P if V3[(a,b)]["PRODUCTO_ESPECIFICO"]=="INSUF"]
L.append(f"\n## 4. Los {len(esp_insuf)} pares ESP=INSUF por categoría y motivo\n")
cat_in=collections.Counter(cat for cat,a,b in esp_insuf)
L.append("| categoría | ESP=INSUF |"); L.append("|---|---|")
for c,n in cat_in.most_common(): L.append(f"| {c} | {n} |")
# clasificar motivo por la razón emitida
def motivo(r):
    r=r or ""
    # prioridad: una CONTRADICCIÓN modelada aparte (no debería dar INSUF) → marca rara
    if "mecanismo_copia" in r: return "mecanismo de copia no confirmado (soft)"
    if "empaque" in r or "juego" in r: return "empaque (juegos vs hojas)"
    if "requisito" in r or "residuo" in r or "ISO" in r or "norma" in r or "alcalino" in r or "certific" in r:
        return "requisito/residuo no acreditado"
    if "falta en AB" in r: return "ausencia en AMBOS lados (candidato débil)"
    if "falta en" in r: return "ausencia en UN lado (atributo de identidad no declarado)"
    if "difiere" in r: return "atributo complementario difiere"
    return "otro / todos presentes e iguales (revisar)"
mot=collections.Counter(motivo(V3[(a,b)]["razon_especifico"]) for cat,a,b in esp_insuf)
L.append("\n### Motivo de insuficiencia (agregado)")
L.append("| motivo | pares |"); L.append("|---|---|")
for m,n in mot.most_common(): L.append(f"| {m} | {n} |")
L.append("\n### Motivo × categoría")
mc=collections.Counter((cat,motivo(V3[(a,b)]["razon_especifico"])) for cat,a,b in esp_insuf)
L.append("| categoría | motivo | pares |"); L.append("|---|---|---|")
for (c,m),n in mc.most_common(): L.append(f"| {c} | {m} | {n} |")

# ── 3. Auditoría de IDENT ────────────────────────────────────────────────────────────────────
L.append("\n## 3. Conjuntos IDENT por categoría (obligatorio para ESP=SI)\n")
L.append("Para cada categoría: SEGMENTO (discrimina subfamilia) ⊆ IDENT (identidad). Lo que está en "
         "IDENT y NO en SEGMENTO es un discriminante de PRODUCTO ESPECÍFICO (complementario a nivel "
         "de demanda, determinante a nivel de identidad).\n")
L.append("| categoría | SEGMENTO (subfamilia) | IDENT∖SEGMENTO (específico) |")
L.append("|---|---|---|")
for cat in sorted(set(list(VERIF_SEG)+list(IDENT))):
    seg=VERIF_SEG.get(cat,[]); idt=IDENT.get(cat,[])
    extra=[k for k in idt if k not in seg]
    L.append(f"| {cat} | {', '.join(seg) or '—'} | {', '.join(extra) or '—'} |")

L.append("\n## 5. (Análisis en prosa, ver más abajo en el reporte redactado a mano.)")

open(os.path.join(OUT,"auditoria_final.md"),"w").write("\n".join(L))
print("escrito reportes/auditoria_final.md")
print("INSUF->SI:",len(insuf_si)," NO->INSUF:",len(no_insuf)," ESP=SI:",len(esp_si)," ESP=INSUF:",len(esp_insuf))
print("viol jerarquia:",len(viol))
print("motivos:",dict(mot))
print("ESP=SI por cat:",dict(cat_si))
