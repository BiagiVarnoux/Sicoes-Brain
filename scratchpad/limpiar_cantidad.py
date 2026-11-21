import json, os, glob, sys, collections
sys.path.insert(0,'/Users/fabriziocuellar/Sicoes-Brain/scraper')
import sicoes_items_cdp as S   # trae parsear_requerido, parse_numero, etc.

STORE="/Users/fabriziocuellar/Sicoes-Brain/procesamiento/historico/data/adquisiciones_etapa2_full_20261114/especificaciones_llm.jsonl"
DATA="/Users/fabriziocuellar/Sicoes-Brain/scraper/historico_local/data"

# 1) cuce -> ruta de FORM_100/110 (crudos). El basename del dir <CUCE> está en la ruta.
cuce_html={}
for p in glob.glob(DATA+"/historico_http_paginas_*/*/crudos/FORM_1[01]0*.html"):
    cuce=p.split("/crudos/")[0].split("/")[-1]
    cuce_html.setdefault(cuce,[]).append(p)
# tambien FORM_100-E
for p in glob.glob(DATA+"/historico_http_paginas_*/*/crudos/FORM_100-E*.html"):
    cuce=p.split("/crudos/")[0].split("/")[-1]
    cuce_html.setdefault(cuce,[]).append(p)

recs=[json.loads(l) for l in open(STORE) if l.strip()]
store={r["cuce"]:r for r in recs}   # latest-wins
print("cuces store:",len(store),"| cuces con FORM_100/110 en disco:",len(cuce_html))

# 2) reparsear cantidad por (cuce, nro_item)
qmap={}   # (cuce,nro_item)->cantidad
sin_html=[]; parse_ok=0
for cuce in store:
    paths=cuce_html.get(cuce)
    if not paths: sin_html.append(cuce); continue
    items=[]
    for p in paths:
        try:
            html=open(p,encoding="utf-8",errors="ignore").read()
            fn="FORM110" if "FORM_110" in p else "FORM100"
            items+=S.parsear_requerido(html,cuce,fn)
        except Exception as e:
            pass
    if items:
        parse_ok+=1
        for it in items:
            q=it.get("cantidad")
            if q is not None:
                qmap[(cuce,int(it["nro_item"]))]=q
print("cuces reparseados OK:",parse_ok,"| sin html:",len(sin_html))
print("(cuce,item) con cantidad limpia:",len(qmap))

json.dump({f"{c}|{n}":v for (c,n),v in qmap.items()},
          open("/Users/fabriziocuellar/Sicoes-Brain/scratchpad/cantidad_limpia.json","w"))

# 3) comparar con lo que había en el store (cuántos arregla)
def nint(x):
    try: return int(str(x))
    except: return None
antes_basura=0; cubiertos=0; total_items=0
for cuce,r in store.items():
    for it in r.get("items",[]):
        total_items+=1
        ni=nint(it.get("item"))
        if ni is None: continue
        if (cuce,ni) in qmap: cubiertos+=1
print("ítems store:",total_items,"| con cantidad limpia disponible:",cubiertos,
      "(%.1f%%)"%(100*cubiertos/total_items))
