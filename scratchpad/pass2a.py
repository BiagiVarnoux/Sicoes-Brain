import json, re, collections
SP="/Users/fabriziocuellar/Sicoes-Brain/scratchpad"
st=json.load(open(SP+"/pipeline_v2_state.json"))
buckets=st["buckets"]; p2in=st["p2in"]

BRANDS={'hp','epson','brother','lexmark','canon','xerox','samsung','kyocera','ricoh','panasonic',
        'oki','dell','pantum','sharp','toshiba','konica','minolta'}
COLORS={'negro','negra','black','cyan','cian','magenta','amarillo','yellow','tricolor','bicolor',
        'rojo','azul','verde','color'}

def firma(clave):
    # SEGURA: fusiona solo por código ALFANUMÉRICO real + marca + color.
    # Los números puros NO fusionan (son atributo: gramaje, cantidad, o modelo ambiguo).
    toks=clave.split("|")[1:]
    mixed=set(); brands=set(); colors=set()
    for t in toks:
        if t in BRANDS: brands.add(t)
        elif t in COLORS: colors.add(t)
        elif re.fullmatch(r'[0-9x]+',t):   # dimensión (215x330, 11x4x5): NO es código
            pass
        elif re.fullmatch(r'\d+(mm|cm|mt|mts|m|kg|gr|grs|g|ml|lt|l|v|hz|khz|mhz|ghz|w|kw|btu|base|rpm|pulg|in|dpi|ppm|mp|pies|p)',t):
            pass                           # spec con unidad (220v, 50hz, 50mm, 1000base): NO es código
        elif re.search(r'[a-z]',t) and re.search(r'\d',t) and len(t)>=3:  # cf226a, ms321, m452dw
            mixed.add(t)
    return (frozenset(brands),frozenset(mixed),frozenset(colors))

def tiene_codigo(sig):
    return len(sig[1])>0  # requiere al menos un código alfanumérico para fusionar

# Lista blanca: solo familias con SKU alfanumérico real. El hardware (aire, switch,
# equipo, escritorio, silla) se excluye: ahí la capacidad vive en números sueltos y el
# merge determinístico sobre-fusiona -> va al LLM (2B).
SKU_FAMS={'toner','tinta','cinta','repuesto','memoria','almacenamiento','tambor','drum'}

mapping={}   # clave -> canonica
merges=0; grupos_merge=[]
for f,ks in p2in.items():
    if f not in SKU_FAMS: continue
    claves=list(ks.keys())
    # agrupar por firma (solo si tiene código)
    byfirma=collections.defaultdict(list)
    for k in claves:
        sig=firma(k)
        if tiene_codigo(sig):  # requiere código alfanumérico real
            byfirma[sig].append(k)
    for sig,group in byfirma.items():
        if len(group)>1:
            canon=min(group,key=len)  # la más corta como canónica
            for k in group: mapping[k]=canon
            merges+=len(group)-1
            grupos_merge.append((f,group))

# aplicar: clave2
clave2_de={}
for k in buckets:
    clave2_de[k]=mapping.get(k,k)

# recomputar grupos finales
final=collections.defaultdict(int)
for k,idxs in buckets.items():
    if k=="sin_clave": continue
    final[clave2_de[k]]+=len(idxs)

json.dump({"mapping2a":mapping,"clave2_de":clave2_de},open(SP+"/pass2a_map.json","w"),ensure_ascii=False)
tot=sum(len(v) for k,v in buckets.items() if k!="sin_clave")
en2=sum(n for n in final.values() if n>=2)
print("PASADA 2A (determinística por código de modelo):")
print("  claves fusionadas:",merges,"| grupos de fusión:",len(grupos_merge))
print("  grupos finales:",len(final),"| ítems en grupo ≥2:",en2,"(%.1f%%)"%(100*en2/tot))
print()
print("Ejemplos de fusiones 2A (claves que se unieron por mismo código):")
for f,group in sorted(grupos_merge,key=lambda x:-len(x[1]))[:8]:
    print("  [%s] %d claves -> 1:"%(f,len(group)))
    for k in group[:4]: print("       ",k[:75])
