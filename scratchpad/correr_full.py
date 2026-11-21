import json, sys, re, os, time, collections
from pathlib import Path
envf=Path('/Users/fabriziocuellar/Sicoes-Brain/monitor/.env')
for l in (envf.read_text().splitlines() if envf.exists() else []):
    if '=' in l and not l.strip().startswith('#'):
        k,v=l.split('=',1); os.environ.setdefault(k.strip(),v.strip())
sys.path.insert(0,'/Users/fabriziocuellar/Sicoes-Brain/monitor')
import clasificador_ia as G
# Usar TODAS las keys (7). CANON primero para priorizar su cupo, luego el resto.
_pri=("GROQ_API_KEY_CANON","GROQ_API_KEY_CANON_2","GROQ_API_KEY","GROQ_API_KEY_2",
      "GROQ_API_KEY_EXTRA_1","GROQ_API_KEY_EXTRA_2","GROQ_API_KEY_EXTRA_3")
_all=[os.environ[k] for k in _pri if os.environ.get(k)]
_seen=set(); _all=[x for x in _all if not (x in _seen or _seen.add(x))]
if _all: G.GROQ_API_KEYS=_all; G.GROQ_API_KEY=_all[0]
# Scratchpad PERSISTENTE del proyecto (no /tmp, no se borra al cambiar de dia).
SP=Path("/Users/fabriziocuellar/Sicoes-Brain/scratchpad")

SYS1=("Eres un normalizador de productos de compras públicas. Para CADA ítem das su identidad "
"canónica para agrupar ítems iguales entre procesos distintos. Usa la descripción Y las "
"especificaciones (ahí suele estar marca/modelo/serie real). Devuelve SOLO un objeto JSON "
'{"items":[ ... ]} con un objeto por ítem en el MISMO orden, forma exacta:\n'
'{"i":<indice>,"familia":"<tipo comercial amplio en minúsculas>","marca":"<marca o null>",'
'"modelo":"<modelo/serie distintiva o null>","atributos":["<atributos que distinguen>"],'
'"clave":"<llave minúsculas sin espacios: familia|marca|modelo, o familia|atributo1|atributo2>"}\n'
"Regla de oro: dos ítems que son el MISMO producto deben recibir la MISMA clave. No inventes datos.")
SYS2=("Consolidas variantes de un producto de una misma familia. Fusiona las claves que son EL MISMO "
"producto intercambiable escrito distinto. NO fusiones distinto modelo/serie, tamaño (oficio≠carta), "
"capacidad (8gb≠16gb), color o medida. Ante la duda, NO fusiones. Responde SOLO en JSON "
'{"grupos":[{"canonica":"<etiqueta>","ids":[<ids mismos>]}]}. Cada id en exactamente un grupo.')

def call(payload):
    r=G._request(payload)
    if not r: return None
    cont=r["choices"][0]["message"]["content"]
    try: return json.loads(cont[cont.find("{"):cont.rfind("}")+1])
    except Exception: return {}
def norm(k): k=(k or '').lower(); k=re.sub(r'[^a-z0-9|]+','',k); return k or "sin_clave"
def _stop_si_tpd():
    # Si las 7 keys agotaron su cupo DIARIO, parar limpio: el parcial ya está en disco
    # y mañana (reset 20:00 Bolivia) se reanuda desde ahí. NO reintentar indefinidamente.
    if len(G._tpd_agotadas) >= len(G.GROQ_API_KEYS):
        print("=== CUPO DIARIO (TPD) AGOTADO EN LAS "+str(len(G.GROQ_API_KEYS))+
              " KEYS. Parcial guardado. Reanuda mañana tras el reset (20:00 Bolivia). ===",flush=True)
        sys.exit(2)

def pasada1(sample):
    donef=SP/"full_p1_parcial.json"
    out=json.loads(donef.read_text()) if donef.exists() else {}
    out={int(k):v for k,v in out.items()}
    # N-1: al reanudar, reprocesa el último ítem hecho (por si se cortó a medias).
    if out:
        ult=max(out); del out[ult]
        donef.write_text(json.dumps(out,ensure_ascii=False))
        print(f"  N-1: reproceso ítem {ult}. Reanudando con {len(out)} hechos.",flush=True)
    B=15
    for s0 in range(0,len(sample),B):
        chunk=[it for it in sample[s0:s0+B] if it["_i"] not in out]
        if not chunk: continue
        for intento in range(8):
            payload={"model":G.GROQ_MODEL,"temperature":0,"response_format":{"type":"json_object"},
              "messages":[{"role":"system","content":SYS1},{"role":"user","content":"Ítems:\n"+json.dumps(
                [{"i":it["_i"],"descripcion":it["desc"],"especificaciones":it["specs"][:400],"unidad":it.get("unidad")} for it in chunk],ensure_ascii=False)}]}
            obj=call(payload)
            if obj:
                arr=next((v for v in obj.values() if isinstance(v,list)),[])
                for o in arr:
                    if isinstance(o,dict) and "i" in o: out[o["i"]]=o
                donef.write_text(json.dumps(out,ensure_ascii=False)); break
            _stop_si_tpd(); time.sleep(30)
        if s0//B % 10==0: print(f"  P1 {min(s0+B,len(sample))}/{len(sample)} (ok {len(out)})",flush=True)
    for it in sample:
        o=out.get(it["_i"],{})
        it["familia"]=o.get("familia");it["marca"]=o.get("marca");it["modelo"]=o.get("modelo")
        it["atributos"]=o.get("atributos");it["clave"]=norm(o.get("clave"))
    return sample

def pasada2(sample):
    def nf(f): return re.sub(r'[^a-z0-9]','',(f or '').lower())
    fam=collections.defaultdict(dict)
    for it in sample:
        if it["clave"]=="sin_clave": continue
        fam[nf(it.get("familia"))].setdefault(it["clave"],{"desc":it["desc"],"specs":it["specs"]})
    mapf=SP/"full_p2_map.json"
    mapping=json.loads(mapf.read_text()) if mapf.exists() else {}
    objetivo=[(f,ks) for f,ks in fam.items() if len(ks)>1 and not all(k in mapping for k in ks)]
    print(f"  P2 familias a consolidar: {len(objetivo)}",flush=True)
    for n,(f,ks) in enumerate(objetivo):
        claves=list(ks.keys())
        ent=[{"id":i,"clave":c,"ejemplo":(ks[c]["desc"][:60]+" || "+ks[c]["specs"][:90])} for i,c in enumerate(claves)]
        gr=None
        for intento in range(8):
            payload={"model":G.GROQ_MODEL,"temperature":0,"response_format":{"type":"json_object"},
              "messages":[{"role":"system","content":SYS2},{"role":"user","content":f"Familia: {f}\nClaves:\n"+json.dumps(ent,ensure_ascii=False)}]}
            obj=call(payload)
            if obj is not None and obj!={}: gr=obj.get("grupos",[]); break
            _stop_si_tpd()
            if intento>=2: break
            time.sleep(25)
        if not gr:
            for c in claves: mapping[c]=c
        else:
            asig=set()
            for g in gr:
                ids=[i for i in g.get("ids",[]) if isinstance(i,int) and 0<=i<len(claves)]
                if not ids: continue
                canonk=norm(g.get("canonica")) or claves[ids[0]]
                for i in ids: mapping[claves[i]]=canonk; asig.add(i)
            for i,c in enumerate(claves):
                if i not in asig: mapping[c]=c
        mapf.write_text(json.dumps(mapping,ensure_ascii=False))
        if n%10==0: print(f"  P2 {n+1}/{len(objetivo)}",flush=True)
    for it in sample: it["clave2"]=mapping.get(it["clave"],it["clave"])
    return sample

if __name__=="__main__":
    print(f"keys Groq activas: {len(G.GROQ_API_KEYS)}",flush=True)
    sample=json.loads((SP/"items_full.json").read_text())
    for i,it in enumerate(sample): it["_i"]=i
    print(f"=== PASADA 1: {len(sample)} ítems ===",flush=True)
    sample=pasada1(sample)
    conclave=sum(1 for it in sample if it["clave"]!="sin_clave")
    print(f"P1 lista: {conclave}/{len(sample)} con clave",flush=True)
    print("=== PASADA 2: consolidación ===",flush=True)
    sample=pasada2(sample)
    (SP/"agrupado_full_final.json").write_text(json.dumps(sample,ensure_ascii=False))
    g=collections.defaultdict(list)
    for it in sample:
        if it.get("clave2") and it["clave2"]!="sin_clave": g[it["clave2"]].append(it)
    enc=sum(len(v) for v in g.values() if len(v)>1)
    print(f"=== LISTO ===\nítems: {len(sample)} | grupos canónicos: {len(g)} | en cluster(≥2): {enc} | singletons: {sum(1 for v in g.values() if len(v)==1)}",flush=True)
