import json, re, unicodedata, collections
SP="/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
d=json.load(open(SP+"/items_full.json"))

def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
def norm(s):
    s=strip_acc((s or "").lower())
    s=re.sub(r'[^a-z0-9 ]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

# Palabras-ruido que no distinguen producto (unidades, conectores)
STOP={'de','para','con','color','tipo','material','tamano','medida','numero','familia',
      'presentacion','envase','contenido','aproximado','marca','modelo','la','el','los','las',
      'un','una','y','o','por','aprox','caja','unidad','pieza','paquete'}

def tokens_sig(txt):
    # tokens significativos: palabras >=3 chars no-stop, y TODOS los números con su unidad
    out=[]
    for w in norm(txt).split():
        if re.fullmatch(r'\d+[a-z]*', w):      # 900ml, 500, 75gr
            out.append(w)
        elif len(w)>=3 and w not in STOP:
            out.append(w)
    return out

def clave_det(it):
    # clave determinística = familia(desc) + atributos ordenados(desc+specs)
    desc=norm(it["desc"])
    if not desc: return None,0.0
    fam=desc.split()[0] if desc.split() else ""
    if len(fam)<3: return None,0.0
    attrs=sorted(set(tokens_sig(it["desc"]+" "+it["specs"])))
    clave=fam+"|"+ "|".join(attrs) if attrs else fam
    # confianza: alta si hay familia + >=2 atributos (o un codigo/numero)
    hasnum=any(re.search(r'\d',a) for a in attrs)
    conf=1.0 if (len(attrs)>=2 or hasnum) else 0.4
    return clave, conf

for it in d:
    k,c=clave_det(it); it["kdet"]=k; it["conf"]=c

# BUCKETS
buckets=collections.defaultdict(list)
for i,it in enumerate(d):
    if it["kdet"]: buckets[it["kdet"]].append(i)

sin_clave=[it for it in d if not it["kdet"]]
multi=[k for k,v in buckets.items() if len(v)>=2]           # repetidos exactos -> GRATIS
items_en_multi=sum(len(buckets[k]) for k in multi)
singles=[k for k,v in buckets.items() if len(v)==1]
# singletons de baja confianza -> al LLM; de alta confianza -> probable pero sin par aun
single_hi=[k for k in singles if d[buckets[k][0]]["conf"]>=1.0]
single_lo=[k for k in singles if d[buckets[k][0]]["conf"]<1.0]

print("=== PRE-KEYER DETERMINÍSTICO sobre %d ítems ==="%len(d))
print("claves determinísticas distintas:", len(buckets))
print()
print("A) RESUELTOS GRATIS (clave repetida ≥2 veces, agrupan solos):")
print("   grupos:", len(multi), "| ítems:", items_en_multi, "(%.1f%%)"%(100*items_en_multi/len(d)))
print()
print("B) SINGLETONS alta confianza (familia+atributos claros, pero únicos por ahora):")
print("   ítems:", len(single_hi), "(%.1f%%)"%(100*len(single_hi)/len(d)))
print()
print("C) DUDOSOS -> necesitan LLM (desc pobre / sin atributos / sin clave):")
need=len(single_lo)+len(sin_clave)
print("   ítems:", need, "(%.1f%%)"%(100*need/len(d)))
print()
# Top grupos gratis
print("Top 12 grupos resueltos gratis:")
for k in sorted(multi,key=lambda k:-len(buckets[k]))[:12]:
    ej=d[buckets[k][0]]
    print("  %3d × %s"%(len(buckets[k]), ej["desc"][:45]))

# ===== COSTO EN TOKENS (para procesar TODO con Opus) =====
import statistics
def aprox_tok(s): return max(1,len(s)//4)   # ~4 chars/token
# input por item = desc + specs(400) + framing json (~25 tok)
in_tok=[aprox_tok(it["desc"])+aprox_tok(it["specs"][:400])+25 for it in d]
# output por item = ficha json {familia,marca,modelo,atributos,clave} ~ 55 tok
out_per=55
SYS=1800  # system prompt SYS1 en tokens, amortizado por batch de 15
B=15
n=len(d)
in_total=sum(in_tok)+ (n//B+1)*SYS
out_total=n*out_per
print()
print("=== COSTO EN TOKENS (procesar los %d con Opus, batch 15) ==="%n)
print("input  ~ %s tok (incl. system x %d batches)"%(f"{in_total:,}", n//B+1))
print("output ~ %s tok"%f"{out_total:,}")
print("TOTAL  ~ %s tok"%f"{in_total+out_total:,}")
# si solo proceso el RESTO que falta a Groq (3899) o solo los dudosos (C)
rem_groq=6785-2886
print()
print("si proceso solo lo que le falta a Groq (%d ítems): ~ %s tok"%(rem_groq, f"{int((in_total+out_total)*rem_groq/n):,}"))
print("si proceso solo los DUDOSOS del pre-keyer (%d ítems): ~ %s tok"%(need, f"{int((in_total+out_total)*need/n):,}"))
