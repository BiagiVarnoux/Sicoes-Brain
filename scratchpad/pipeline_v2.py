import json, re, unicodedata, collections
SP="/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
d=json.load(open(SP+"/items_full.json"))

def strip_acc(s): return "".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
def norm(s):
    s=strip_acc((s or "").lower()); s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

STOP={'de','para','con','color','tipo','material','tamano','medida','numero','familia',
      'presentacion','envase','contenido','aproximado','marca','modelo','la','el','los','las',
      'un','una','y','o','por','aprox','caja','unidad','pieza','paquete','mts','cms','cm','mm'}

# --- mapa de sinónimos de FAMILIA (primera palabra -> familia canónica) ---
FAM_SYN={
 'toner':'toner','tonner':'toner','cartucho':'toner','cartuchos':'toner','refil':'toner','refill':'toner','kits':'toner','kit':'toner','drum':'toner','tambor':'toner',
 'papel':'papel','papeles':'papel','resma':'papel','resmas':'papel','hoja':'papel','hojas':'papel',
 'silla':'silla','sillas':'silla','sillon':'silla','butaca':'silla',
 'disco':'almacenamiento','discos':'almacenamiento','memoria':'memoria','memorias':'memoria','usb':'almacenamiento','flash':'almacenamiento',
 'boligrafo':'boligrafo','boligrafos':'boligrafo','lapicero':'boligrafo','lapiceros':'boligrafo',
 'lapiz':'lapiz','lapices':'lapiz',
 'marcador':'marcador','marcadores':'marcador','resaltador':'resaltador','resaltadores':'resaltador',
 'cinta':'cinta','cintas':'cinta',
 'folder':'folder','folders':'folder','carpeta':'folder','carpetas':'folder','archivador':'archivador','archivadores':'archivador',
 'tinta':'tinta','tintas':'tinta',
 'guante':'guantes','guantes':'guantes',
 'desinfectante':'desinfectante','limpiador':'limpiador','limpiavidrios':'limpiavidrios',
 'engrapadora':'engrapadora','grapadora':'engrapadora','corchetera':'engrapadora',
 'grapa':'grapa','grapas':'grapa','corchete':'grapa','corchetes':'grapa',
}
def familia(desc):
    w=norm(desc).split()
    if not w: return ""
    f=w[0]
    return FAM_SYN.get(f,f)

def tokens_sig(txt):
    out=[]
    for w in norm(txt).split():
        if re.fullmatch(r'\d+[a-z]*', w): out.append(w)
        elif len(w)>=3 and w not in STOP: out.append(w)
    return out

def clave_det(it):
    desc=norm(it["desc"])
    if not desc: return None
    fam=familia(it["desc"])
    if len(fam)<3: return None
    attrs=sorted(set(tokens_sig(it["desc"]+" "+it["specs"])))
    return fam+"|"+"|".join(attrs) if attrs else fam

# PASADA 1 (gratis)
for it in d:
    it["clave"]=clave_det(it) or "sin_clave"

buckets=collections.defaultdict(list)
for i,it in enumerate(d):
    buckets[it["clave"]].append(i)

# PASADA 2 input: por familia, las claves distintas con un ejemplo
fam_keys=collections.defaultdict(dict)
for k,idxs in buckets.items():
    if k=="sin_clave": continue
    f=k.split("|")[0]
    ej=d[idxs[0]]
    fam_keys[f][k]={"n":len(idxs),"desc":ej["desc"][:70],"specs":ej["specs"][:110]}

p2in={f:ks for f,ks in fam_keys.items() if len(ks)>1}  # solo familias con >1 clave
json.dump({"buckets":{k:v for k,v in buckets.items()},"p2in":p2in},
          open(SP+"/pipeline_v2_state.json","w"), ensure_ascii=False)

tot=len(d); multi=sum(len(v) for v in buckets.values() if len(v)>=2 and list(buckets).index)  # placeholder
items_multi=sum(len(v) for k,v in buckets.items() if k!="sin_clave" and len(v)>=2)
print("PASADA 1 (pre-keyer, gratis):")
print("  ítems:",tot,"| claves distintas:",len([k for k in buckets if k!='sin_clave']))
print("  en grupo ≥2:",items_multi,"(%.1f%%)"%(100*items_multi/tot))
print("  familias a consolidar en P2:",len(p2in),"| claves en ellas:",sum(len(v) for v in p2in.values()))
print("  sin_clave:",len(buckets.get('sin_clave',[])))
