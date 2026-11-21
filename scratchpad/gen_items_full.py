import json, re, collections
STORE="/Users/fabriziocuellar/Sicoes-Brain/procesamiento/historico/data/adquisiciones_etapa2_full_20261114/especificaciones_llm.jsonl"
recs=[json.loads(l) for l in open(STORE) if l.strip()]
by={}
for r in recs: by[r.get("cuce")]=r  # latest-wins

def specs_txt(sp):
    if isinstance(sp,list): s=" | ".join(str(x) for x in sp)
    else: s=str(sp or "")
    return s[:500]

def es_basura(d):
    d=(d or "").strip()
    if not d: return True
    # precio/numero puro: "50,00" "1.200" "12"
    if re.fullmatch(r'[\d\.,\s]+', d): return True
    # unidad suelta
    if re.fullmatch(r'(pieza|piezas|unidad|unidades|pza|pzas|global|glb|juego|caja|cajas|resma|resmas|metro|metros)', d, re.I): return True
    return False

out=[]; drop=0
for cuce,r in by.items():
    met=r.get("metodo")
    for it in r.get("items",[]):
        desc=(it.get("descripcion") or "").strip().rstrip(":")
        if es_basura(desc): drop+=1; continue
        out.append({
            "cuce":cuce,
            "item":str(it.get("item") or ""),
            "desc":desc,
            "specs":specs_txt(it.get("especificaciones")),
            "cant":it.get("cantidad"),
            "unidad":it.get("unidad") or "",
            "cat":met,
        })
json.dump(out, open("/Users/fabriziocuellar/Sicoes-Brain/scratchpad/items_full.json","w"), ensure_ascii=False)
print("items validos:", len(out), "| descartados basura:", drop)
print("por metodo:", collections.Counter(x["cat"] for x in out))
