import json, sys, re, os, time, collections
from pathlib import Path
envf=Path('/Users/fabriziocuellar/Sicoes-Brain/monitor/.env')
for l in (envf.read_text().splitlines() if envf.exists() else []):
    if '=' in l and not l.strip().startswith('#'):
        k,v=l.split('=',1); os.environ.setdefault(k.strip(),v.strip())
sys.path.insert(0,'/Users/fabriziocuellar/Sicoes-Brain/monitor')
import clasificador_ia as G
_pri=("GROQ_API_KEY_CANON","GROQ_API_KEY_CANON_2","GROQ_API_KEY","GROQ_API_KEY_2",
      "GROQ_API_KEY_EXTRA_1","GROQ_API_KEY_EXTRA_2","GROQ_API_KEY_EXTRA_3")
_all=[os.environ[k] for k in _pri if os.environ.get(k)]
_seen=set(); _all=[x for x in _all if not (x in _seen or _seen.add(x))]
if _all: G.GROQ_API_KEYS=_all; G.GROQ_API_KEY=_all[0]
SP=Path("/Users/fabriziocuellar/Sicoes-Brain/scratchpad")

SYS=("Consolidas variantes de un producto de una misma familia de compras públicas. Fusiona las "
"claves que son EL MISMO producto intercambiable escrito distinto. NO fusiones si difieren en "
"modelo/serie, tamaño (oficio≠carta≠A4), capacidad/volumen (8gb≠16gb, 500ml≠900ml), gramaje, "
"color, o medida. Ante CUALQUIER duda, NO fusiones (deja la clave sola). Responde SOLO en JSON "
'{"grupos":[{"canonica":"<etiqueta corta>","ids":[<ids del mismo producto>]}]}. Cada id en un solo grupo.')

def call(payload):
    r=G._request(payload)
    if not r: return None
    c=r["choices"][0]["message"]["content"]
    try: return json.loads(c[c.find("{"):c.rfind("}")+1])
    except Exception: return {}
def norm(k): k=(k or '').lower(); k=re.sub(r'[^a-z0-9|]+','',k); return k or "x"
def stop_si_tpd():
    if len(G._tpd_agotadas)>=len(G.GROQ_API_KEYS):
        print("=== TPD AGOTADO EN LAS %d KEYS. Parcial guardado, reanuda tras reset. ==="%len(G.GROQ_API_KEYS),flush=True)
        sys.exit(2)

# cargar estado: buckets + ejemplos
st=json.load(open(SP/"pipeline_v2_state.json")); buckets=st["buckets"]
p2a=json.load(open(SP/"pass2a_map.json")); map2a=p2a["mapping2a"]
d=json.load(open(SP/"items_full.json"))
clave2={k:map2a.get(k,k) for k in buckets}
# ejemplo por clave final
ej={}
for k,idxs in buckets.items():
    c=clave2[k]
    if c not in ej: ej[c]={"desc":d[idxs[0]]["desc"][:60],"specs":d[idxs[0]]["specs"][:90]}
fam=collections.defaultdict(list)
for c in set(clave2.values()):
    if c=="sin_clave": continue
    fam[c.split("|")[0]].append(c)

HARD={'aire','aires','switch','equipo','computador','computadores','escritorio','silla','sillas',
 'servidor','laptop','monitor','camara','telefono','proyector','router','ups','estabilizador',
 'mueble','estante','estantes','archivador','credenza','mesa'}
# toner: ya bien consolidado por 2A (SKU) y de alto riesgo semántico -> NO 2B.
SKIP_2B={'toner'}
objetivo=[(f,ks) for f,ks in fam.items() if len(ks)>1 and f not in HARD and f not in SKIP_2B]
objetivo.sort(key=lambda x:-len(x[1]))

mapf=SP/"map_2b.json"
mapping=json.loads(mapf.read_text()) if mapf.exists() else {}
CH=25
print("familias atributo a consolidar:",len(objetivo),flush=True)
for n,(f,claves) in enumerate(objetivo):
    if all(c in mapping for c in claves): continue
    for s0 in range(0,len(claves),CH):
        chunk=claves[s0:s0+CH]
        if all(c in mapping for c in chunk): continue
        ent=[{"id":i,"clave":c,"ej":(ej[c]["desc"]+" || "+ej[c]["specs"])} for i,c in enumerate(chunk)]
        gr=None
        for intento in range(8):
            payload={"model":G.GROQ_MODEL,"temperature":0,"response_format":{"type":"json_object"},
              "messages":[{"role":"system","content":SYS},
                          {"role":"user","content":f"Familia: {f}\nClaves (JSON):\n"+json.dumps(ent,ensure_ascii=False)}]}
            obj=call(payload)
            if obj is not None and obj!={}: gr=obj.get("grupos",[]); break
            stop_si_tpd()
            if intento>=2: break
            time.sleep(20)
        if not gr:
            for c in chunk: mapping[c]=c
        else:
            asig=set()
            for g in gr:
                ids=[i for i in g.get("ids",[]) if isinstance(i,int) and 0<=i<len(chunk)]
                if not ids: continue
                canon=norm(g.get("canonica")) or chunk[ids[0]]
                for i in ids: mapping[chunk[i]]=canon; asig.add(i)
            for i,c in enumerate(chunk):
                if i not in asig: mapping[c]=c
        mapf.write_text(json.dumps(mapping,ensure_ascii=False))
    if n%15==0: print(f"  {n+1}/{len(objetivo)} familias (claves mapeadas {len(mapping)})",flush=True)

print("LISTO 2B. claves mapeadas:",len(mapping),flush=True)
