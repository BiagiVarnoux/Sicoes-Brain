#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cablea los grupos canónicos (pipeline híbrido) al dashboard: puebla
hist_productos_canonicos y setea hist_items.producto_canonico_id por (cuce,nro_item).
Idempotente: upsert del canónico por nombre_canonico. --dry-run por defecto."""
import os, re, json, sys, argparse, unicodedata, urllib.request, urllib.parse
from collections import Counter, defaultdict
sys.path.insert(0,'/Users/fabriziocuellar/Sicoes-Brain/monitor')
from dotenv import load_dotenv
load_dotenv('/Users/fabriziocuellar/Sicoes-Brain/monitor/.env')
U=os.environ["SUPABASE_URL"].rstrip("/"); K=os.environ["SUPABASE_KEY"]
H={"apikey":K,"Authorization":f"Bearer {K}","Content-Type":"application/json"}
SP="/Users/fabriziocuellar/Sicoes-Brain/scratchpad"

def _get(path):
    r=urllib.request.Request(f"{U}/rest/v1/{path}",headers=H)
    with urllib.request.urlopen(r,timeout=90) as x: return json.loads(x.read())
def _req(method,path,body=None,extra=None):
    data=json.dumps(body).encode() if body is not None else None
    h=dict(H);  h.update(extra or {})
    r=urllib.request.Request(f"{U}/rest/v1/{path}",data=data,method=method,headers=h)
    with urllib.request.urlopen(r,timeout=90) as x:
        raw=x.read(); return json.loads(raw) if raw else None

# ---- cargar nuestra agrupación ----
fk=json.load(open(SP+"/clave_final.json"))
buckets=json.load(open(SP+"/pipeline_v2_state.json"))["buckets"]
d=json.load(open(SP+"/items_full.json"))
grp=defaultdict(list)
for k,idxs in buckets.items():
    if k!="sin_clave": grp[fk[k]].extend(idxs)
clusters={c:v for c,v in grp.items() if len(v)>=2}   # solo grupos ≥2 reciben canónico

def _clean(s):
    s=re.sub(r'\s+',' ',(s or '').replace('|',' · ').strip(' ;:-·'))
    return s
def nombre(c,idxs):
    # descriptor legible: desc representativa + specs clave del ítem más común
    rep=_clean(Counter(d[i]['desc'][:50] for i in idxs).most_common(1)[0][0])
    # specs del ítem cuya desc es la representativa
    specs=Counter(d[i]['specs'][:90] for i in idxs).most_common(1)[0][0]
    sb=_clean(specs)
    nm=f"{rep} — {sb}" if sb and sb.lower() not in rep.lower() else rep
    return nm[:160]
def familia(c): return c.split('|')[0]

# (cuce,nro_item) -> clave, para los clusterizados
pair2clave={}
for c,idxs in clusters.items():
    for i in idxs:
        it=d[i]
        try: ni=int(str(it['item']))
        except: continue
        pair2clave[(it['cuce'],ni)]=c

# ---- leer hist_items (id,cuce,nro_item,unspsc) ----
def leer_hist():
    out,off=[],0
    while True:
        rows=_get(f"hist_items?select=id,cuce,nro_item,unspsc_codigo,producto_canonico_id&limit=1000&offset={off}")
        if not rows: break
        out.extend(rows); off+=1000
        if len(rows)<1000: break
    return out
hist=leer_hist()
hi_by_pair={}
for r in hist:
    try: ni=int(r["nro_item"]) if r["nro_item"] is not None else None
    except: ni=None
    if ni is not None: hi_by_pair[(r["cuce"],ni)]=r
print(f"hist_items en Supabase: {len(hist)} | con (cuce,nro_item): {len(hi_by_pair)}")

# ---- match: de nuestros clusterizados, cuántos existen en hist_items ----
clave_items=defaultdict(list)   # clave -> [hist_item_id]
clave_unspsc=defaultdict(Counter)
matched=miss=0
for (cuce,ni),clave in pair2clave.items():
    r=hi_by_pair.get((cuce,ni))
    if r: matched+=1; clave_items[clave].append(r["id"]); clave_unspsc[clave][r.get("unspsc_codigo")]+=1
    else: miss+=1
print(f"ítems clusterizados nuestros: {len(pair2clave)} | matchean hist_items: {matched} | sin match: {miss}")
print(f"grupos canónicos a crear (con ≥1 ítem en hist_items): {len([c for c in clave_items if clave_items[c]])}")

ap=argparse.ArgumentParser(); ap.add_argument("--write",action="store_true"); A=ap.parse_args()
if not A.write:
    print("\nDRY-RUN. Muestra de 8 canónicos que se crearían:")
    for c in sorted(clave_items,key=lambda c:-len(clave_items[c]))[:8]:
        print(f"  [{len(clave_items[c])} items] {nombre(c,clusters[c])}")
    print("\n(usar --write para aplicar)")
    sys.exit(0)

# ---- aplicar: upsert canónico + PATCH items ----
def upsert(nm,cat,unspsc):
    q=urllib.parse.quote(nm)
    rows=_get(f"hist_productos_canonicos?select=id&nombre_canonico=eq.{q}")
    if rows: return rows[0]["id"]
    res=_req("POST","hist_productos_canonicos",
             {"nombre_canonico":nm,"categoria":cat,"unspsc_codigo":unspsc},
             extra={"Prefer":"return=representation"})
    return res[0]["id"]

creados=asignados=0; usados=set()
for c,ids in clave_items.items():
    if not ids: continue
    nm=nombre(c,clusters[c]); base=nm; n=2
    while nm in usados: nm=f"{base} ({n})"; n+=1
    usados.add(nm)
    uns=clave_unspsc[c].most_common(1)[0][0] if clave_unspsc[c] else None
    cid=upsert(nm,familia(c),uns); creados+=1
    for i in range(0,len(ids),200):
        chunk=ids[i:i+200]
        flt="id=in.("+",".join(str(x) for x in chunk)+")"
        _req("PATCH",f"hist_items?{flt}",{"producto_canonico_id":cid},extra={"Prefer":"return=minimal"})
    _req("PATCH",f"hist_productos_canonicos?id=eq.{cid}",{"n_items":len(ids)},extra={"Prefer":"return=minimal"})
    asignados+=len(ids)
    if creados%100==0: print(f"  {creados} canónicos, {asignados} ítems…",flush=True)
print(f"\nLISTO. canónicos creados/upsert: {creados} | hist_items asignados: {asignados}")
