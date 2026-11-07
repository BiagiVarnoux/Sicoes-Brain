#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETAPA 1 del diseño v2 — EXTRACTOR + NORMALIZADOR de atributos. SOLO LECTURA, entorno aislado.
=============================================================================================
Función (A) del diseño, SEPARADA de bloqueo y verificación. NO fusiona nada, NO escribe en la BD,
NO migra datos. Produce por ítem un registro estructurado + evidencia literal + nivel identificable.

Versión CERRADA provisionalmente (2026-11-06) tras 4 rondas de revisión humana + v4 (ChatGPT) y las
4 correcciones de correctitud (E049 case/rack líder, E014 tipo_medio óptico solo con token explícito,
E043 gramaje rango, E034/E050 vías papel continuo). Ver reportes/cierre_etapa1.md.

Ajustes acordados incorporados:
  #2 incertidumbre por nivel: `nivel_identificable` ∈ {producto, subfamilia, familia_amplia} según qué
     atributos estén presentes; se listan los `faltantes`. Un ítem con solo familia/subfamilia NO se
     fuerza a producto específico.
  #4 demanda: se extraen cantidad/unidad SOLO como dato descriptivo; se DEJA CONSTANCIA de que las
     cantidades/precios/adjudicaciones autoritativos vienen de los campos FORM de hist_items, no del
     texto, y que la agregación (anti doble-conteo) es una etapa posterior. Normalización de unidades.
  correcciones: separador de miles (1.000→1000); r16/rj45/3200/ddrN son ATRIBUTOS (medida/interfaz/
     frecuencia/generación), nunca "modelos".

Salidas (para revisión, sin tocar producción):
  - reportes/extractor_cobertura.md        (ítems por categoría, % por nivel, fill-rate por atributo)
  - reportes/extractor_cobertura_vista.csv (muestra interna; NO sobreescribe la muestra revisada)
"""
import os, re, sys, json, csv, collections, unicodedata, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv("/Users/fabriziocuellar/Sicoes-Brain/monitor/.env")
import urllib.request
U=os.environ["SUPABASE_URL"].rstrip("/"); K=os.environ["SUPABASE_KEY"]
HDR={"apikey":K,"Authorization":f"Bearer {K}"}
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reportes"); random.seed(7)
os.makedirs(OUT,exist_ok=True)

def get(p):
    out,off=[],0
    while True:
        r=urllib.request.Request(f"{U}/rest/v1/{p}&limit=1000&offset={off}",headers=HDR)
        rows=json.loads(urllib.request.urlopen(r,timeout=60).read()); out+=rows; off+=1000
        if len(rows)<1000: break
    return out
def cuerpo(d): return (d or "").split("—",1)[-1].strip()
def nrm(s):
    s=unicodedata.normalize("NFD",s or ""); return "".join(c for c in s if unicodedata.category(c)!="Mn").lower()

# ── helpers de evidencia: cada extractor devuelve (valor_normalizado, texto_evidencia) o None ──
def _num(s): return float(s.replace(",",".")) if s else None
def _int_miles(s):  # separador de miles: "1.000"→1000, "1,000"→1000, "500"→500
    return int(re.sub(r"[.,](?=\d{3}\b)","",s))

# ── CATEGORÍA (tipo comercial) ──────────────────────────────────────────────────────────────────
# orden importa: lo más específico primero (DVD/CD antes que "disco" genérico)
_EQUIPO=(r"computador|computadora|laptop|notebook|portatil|equipo(s)? portatil|equipo de escritorio|"
         r"equipo de computacion completo|all in one|mini ?pc|\bcpu\b|servidor|workstation|"
         r"estacion de trabajo|impresora|multifuncion|fotocopiadora|scanner|escaner|proyector|\bmonitor\b|"
         r"tablet|telefono|\bups\b|estabilizador|grabador|nvr|dvr|camara (ip|domo|bullet|ptz|de vigilancia|de seguridad)")
# cabezas que NO son el bien objetivo (accesorios físicos / artículos de escritorio) → fuera de alcance
_NO_PROD=(r"funda|estuche|porta ?cd|porta ?disco|base de acoplamiento|docking|\bdock\b|caddy|cooler|"
          r"ventilador|\bcable\b|adaptador|soporte|gabinete|carcasa")
# case/rack SOLO cuando es el producto LÍDER (al inicio de la cabeza); si aparece como mención
# ("disco ... para servidor en rack"), el producto es el disco, no el rack (precaución E049).
_NO_PROD_LIDER=r"^(case|rack)\b"
_ESCRIT=(r"borrador|goma de borrar|corrector|marcador|resaltador|boligrafo|lapiz|lapicero|tijera|regla|"
         r"pegamento|sacapunta|\bclip\b|grapa(s)?|engrapadora|perforadora|folder|archivador|cuaderno")
_CONSUM=(r"toner(es)?|tonn?er|cartucho(s)?|refil(es)?|ribbon(s)?|drum|tambor|fusor|cabezal|"
         r"unidad de imagen|revelador")
def _cabeza(n):
    parts=[p.strip() for p in re.split(r"[;,:()]",n) if p.strip()]
    return parts[0] if parts else n
def categoria(n):
    cab=_cabeza(n)
    # contexto accesorio/compatibilidad: "accesorio para X" / "repuesto para X" / "para X" / "compatible con"
    # → el equipo citado NO es el producto; el producto es el componente que sigue.
    es_accesorio_ctx = bool(re.match(r"^(accesorio|accesorios|repuesto|repuestos|para|compatible)\b",cab)) \
                       or bool(re.search(r"\bpara (computador|computadora|\bpc\b|equipo|impresora|laptop)\b",cab))
    # (0) accesorios físicos / escritorio como CABEZA → fuera de alcance (evita falsos: funda CD, borrador, docking)
    if re.search(r"\b("+_NO_PROD+r")\b",cab): return None
    if re.match(_NO_PROD_LIDER,cab): return None
    if re.search(r"\b("+_ESCRIT+r")\b",cab): return None
    # (1) consumible de impresión: el consumible debe ser el PRODUCTO (en la cabeza o claramente el bien),
    #     no una mención "uso tinta/lápiz". Repuestos de impresora (tambor/fusor) sí son consumibles.
    # consumibles FUERTES (inequívocos de impresión) en cualquier parte; el falso "borrador/uso tinta"
    # ya quedó excluido por la guarda de escritorio de arriba.
    if re.search(r"\b("+_CONSUM+r")\b",n): return "consumible_impresion"
    # cinta/tinta SOLO en contexto de impresión explícito (evita cinta adhesiva / "uso tinta")
    if re.search(r"\b(cinta|tinta)s? (para|de) (impresora|impresion|fotocopiadora|plotter|laser)\b",n):
        return "consumible_impresion"
    # (2) EQUIPO como CABEZA (y no en contexto accesorio/compatibilidad) → None (no es compra del componente)
    if re.search(r"\b("+_EQUIPO+r")",cab) and not es_accesorio_ctx: return None
    # (3) llanta (NO la cámara/neumático interno, que es otro producto)
    if re.search(r"\b(camara|tubo)\b",cab) and re.search(r"\b(llanta|motocicleta|moto|neumatico|vehiculo)\b",n): return None
    if re.search(r"\b(llanta(s)?|neumatico(s)?)\b",n): return "llanta"
    # (4) papel: impreso / continuo-químico / bond (demanda distinta)
    if re.search(r"\b(membret|hoja membretada|papel membretado)\b",n) or ("full color" in n and "papel" in n):
        return "papel_impreso"
    if ("papel" in n) and re.search(r"\b(papel continuo|formulario continuo|autocopiativ|autocopiante|con desglose|con calca|papel quimico)\b",n):
        return "papel_continuo"
    if re.search(r"\bpapel bond\b|\bpapel tamano\b|\bresma(s)? de papel\b",n): return "papel_bond"
    if re.search(r"\bsobre(s)? (manila|de manila)\b",n): return "sobre_manila"
    # (5) un LECTOR/grabadora/unidad/reproductor de CD/DVD es un PERIFÉRICO, no un disco óptico consumible
    if re.search(r"\b(lector|lectora|grabadora de (cd|dvd)|quemador|unidad de (cd|dvd)|reproductor de|drive)\b",n):
        return None
    # (6) óptico = MEDIO (disco cd/dvd) ANTES que almacenamiento (disco compacto ≠ disco duro)
    if re.search(r"\b(dvd|\bcd\b|discos? compactos?|blu[- ]?ray)\b",n): return "optico"
    # (7) COMPONENTE (ram/almacenamiento) solo si es el PRODUCTO: en la CABEZA, o en contexto accesorio.
    #     Un dispositivo cuya cabeza NO es el componente (reloj biométrico con RAM) → None.
    _ALM=r"discos? (duros?|solidos?)|\bssd\b|\bhdd\b|estado solido|nvme|unidad(es)? de estado"
    _RAM=r"memoria(s)? ram|\bram\b|ddr\d|\bpc[2-5]\b"
    if re.search(r"\b("+_ALM+r")\b",cab) or (es_accesorio_ctx and re.search(r"\b("+_ALM+r")\b",n)): return "almacenamiento"
    if ("flash" not in n) and (re.search(r"\b("+_RAM+r")\b",cab) or (es_accesorio_ctx and re.search(r"\b("+_RAM+r")\b",n))): return "ram"
    return None

# ── EXTRACTORES por atributo (valor normalizado + evidencia literal) ─────────────────────────────
def _caps(n):
    """Capacidades normalizadas a GB. EXCLUYE velocidades (gb/s, gbps) y caché (mb cuando ya hay gb/tb).
    Marca mínimos ('500 GB o superior'). Devuelve [(valor_gb, evidencia, es_minimo)]."""
    out=[]
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(tb|gb)\b(?!\s*/\s*s|ps\b)",n):   # excluye gb/s y gbps (velocidad), NO 'gb sata'
        v=_num(m.group(1)); v=v*1000 if m.group(2)=="tb" else v
        tail=n[m.end():m.end()+16]; prev=n[max(0,m.start()-10):m.start()]
        mn=bool(re.search(r"o\s+(superior|mas|mayor)|minimo|\bmin\b",tail)) or bool(re.search(r"(minimo|desde|mayor a)\s*$",prev))
        out.append((round(v,3),m.group(0),mn))
    if not out:   # MB solo si NO hay GB/TB (evita contar caché 64MB); nunca MB/s (velocidad)
        for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*mb\b(?!\s*/\s*s)",n):
            tail=n[m.end():m.end()+18]; prev=n[max(0,m.start()-10):m.start()]
            mn=bool(re.search(r"o\s+(superior|mas|mayor)|como minimo|minimo|\bmin\b",tail)) or bool(re.search(r"(minimo|desde|mayor a)\s*$",prev))
            out.append((round(_num(m.group(1))/1000,3),m.group(0),mn))
    return out
def cap_gb(n):
    ex=[c for c in _caps(n) if not c[2]]           # capacidades EXACTAS (sin "o superior")
    if not ex: return None
    if len({v for v,_,_ in ex})>1: return ("AMBIGUO",[e for _,e,_ in ex])
    return (ex[0][0],ex[0][1])
def cap_min_gb(n):
    mn=[c for c in _caps(n) if c[2]]               # requisito MÍNIMO (no exacto)
    return (mn[0][0],mn[0][1]) if mn else None
def interfaz(n):
    for pat,val in [(r"\bnvme\b","nvme"),(r"\bsata\s*3(?:\.0)?\b","sata3"),(r"\bsata\b","sata"),
                    (r"\bm\.?2\b","m.2"),(r"\busb\b","usb")]:
        m=re.search(pat,n)
        if m: return (val,m.group(0))
    return None
def formato_disco(n):   # factor de forma SOLO (2.5/3.5/M.2); 'interno/externo' NO es formato → va a instalacion
    m=re.search(r"\b(2\.5|3\.5|m\.?2)\b",n)
    return (m.group(1).replace("m2","m.2"),m.group(0)) if m else None
def instalacion(n):     # ubicación/instalación, atributo separado del formato
    if re.search(r"\binterno\b",n): return ("interno","interno")
    if re.search(r"\b(externo|portatil)\b",n): return ("externo","externo")
    return None
def tecnologia_alm(n):
    # NO asumir HDD por "disco duro" genérico: tecnología indeterminada salvo marcador explícito.
    if re.search(r"\b(ssd|estado solido|solido|nvme)\b",n): return ("ssd","ssd")
    if re.search(r"\bhdd\b",n): return ("hdd","hdd")
    if re.search(r"\b(7200|5400)\s*rpm\b",n): return ("hdd","rpm")
    return None
def generacion_ddr(n):
    m=re.search(r"\bddr(\d)\b",n)
    if m: return (f"ddr{m.group(1)}",m.group(0))
    m=re.search(r"\bpc(\d)\b",n)      # PC3=DDR3, PC4=DDR4… (designación de módulo con evidencia)
    if m and m.group(1) in "2345": return (f"ddr{m.group(1)}",m.group(0))
    return None
def frecuencia_mhz(n):
    m=re.search(r"(\d{3,4})\s*mhz\b",n) or re.search(r"\bfrec(?:uencia)?\.?\s*(\d{3,4})\b",n)
    return (int(m.group(1)),m.group(0)) if m else None
def formato_ram(n):
    m=re.search(r"\b(so-?dimm|u-?dimm|dimm)\b",n)
    return (m.group(1).replace("-",""),m.group(0)) if m else None
def tamano_papel(n):
    m=re.search(r"\b(medio oficio|1/2 oficio|doble oficio|medio carta|1/2 carta|doble carta|oficio|carta|a4|a3)\b",n)
    if not m: return None
    v=m.group(1).replace("1/2 oficio","medio oficio").replace("1/2 carta","medio carta")
    return (v,m.group(0))
def gramaje(n):
    # rango "75-80 g/m2" → conservar límites (NO colapsar a exacto); valor normalizado "min-max".
    mr=re.search(r"(\d{2,3})\s*[-a]\s*(\d{2,3})\s*(?:g\s*/?\s*m2|gsm|grs?\b|g\b)",n)
    if mr:
        a,b=sorted((int(mr.group(1)),int(mr.group(2))))
        return (f"{a}-{b}",mr.group(0))
    m=re.search(r"(\d{2,3})\s*(g\s*/?\s*m2|gsm|grs?\b|g\b)",n)
    return (int(m.group(1)),m.group(0)) if m else None
_CONCRETO=r"blanco|negro|azul|rojo|amarillo|anaranjado|verde|cafe|madera|celeste|naranja|gris|rosado|crema|beige|morado"
def color(n):
    # ≥2 colores concretos listados = SURTIDO real (ej. amarillo/anaranjado/verde); 1 concreto = ese color
    # (una aclaración entre paréntesis "color surtido (celeste)" = 1 concreto → celeste).
    _SINON={"madera":"cafe","anaranjado":"naranja"}   # tonos equivalentes: colapsan SOLO para contar surtido
    found=re.findall(r"\b("+_CONCRETO+r")\b",n)
    distintos=sorted({_SINON.get(c,c) for c in found})
    surt=re.search(r"\b(surtido(s)?|colores?|varios|multicolor|a eleccion)\b",n)
    if len(distintos)>=2: return ("surtido", "+".join(distintos))   # ≥2 colores reales = surtido
    if found: return (found[0],found[0])                            # 1 color → literal original (madera≠cafe)
    if surt: return ("surtido",surt.group(0))
    return None
def cantidad_hojas(n):
    m=re.search(r"(\d{1,3}(?:[.,]\d{3})*|\d+)\s*hojas\b",n)
    return (_int_miles(m.group(1)),m.group(0)) if m else None
def llanta_medida(n):
    m=re.search(r"(\d{2,3})\s*/\s*(\d{2,3})\s*r\s*(\d{2})",n)       # auto/moto 205/55 R16, 90/90 R18
    if m: return ({"ancho":int(m.group(1)),"perfil":int(m.group(2)),"rin":int(m.group(3))},m.group(0))
    m=re.search(r"\b(\d{2,3})\s*-\s*(\d{2,3})\s*-\s*(\d{2})\b",n)   # moto 90-90-18
    if m: return ({"ancho":int(m.group(1)),"perfil":int(m.group(2)),"rin":int(m.group(3))},m.group(0))
    return None
def pliegues(n):  # tolera "plieges" (errata frecuente)
    m=re.search(r"(\d{1,2})\s*plieg[a-z]*|plieg[a-z]*\.?\s*(\d{1,2})",n)
    if not m: return None
    return (int(m.group(1) or m.group(2)),m.group(0))
def huella(n):
    m=re.search(r"\b(semi ?pantanera|pantanera|autopista|a todo terreno|normal|lisa)\b",n)
    return (m.group(1),m.group(0)) if m else None
def tipo_constr(n):
    # construcción de la carcasa: radial domina si aparece (es la construcción); "tubular"/cámara se
    # guardan aparte en camara_llanta. NO se inventa ambigüedad radial/tubular.
    if "radial" in n: return ("radial","radial")
    if "tubular" in n: return ("tubular","tubular")
    return None
def camara_llanta(n):   # con/sin cámara (atributo separado de la construcción)
    if re.search(r"sin\s+camara",n): return ("sin_camara","sin camara")
    if re.search(r"con\s+camara|tubular",n): return ("con_camara","con camara/tubular")
    return None
def ponchillo(n):
    if re.search(r"sin\s+ponchillo",n): return ("sin_ponchillo","sin ponchillo")
    if re.search(r"con\s+ponchillo",n): return ("con_ponchillo","con ponchillo")
    return None
def huella_llanta(n):
    m=re.search(r"\b(semi ?pantanera|pantanera|autopista|a ?todo ?terreno|all ?terrain|h/?t|a/?t|normal|lisa)\b",n)
    if not m: return None
    v={"a/t":"todo terreno","at":"todo terreno","all terrain":"todo terreno","h/t":"autopista","ht":"autopista"}.get(m.group(1).replace(" ",""),m.group(1))
    return (v,m.group(0))
def tipo_grabacion(n):
    # "de grabación/grabable" NO prueba R vs RW → no fijar; solo marcar con evidencia explícita.
    if re.search(r"\b(rw|regrabable)\b",n): return ("rw","rw")
    if re.search(r"(dvd|cd)\s*[\+\-]\s*r\b|\b[\+\-]r\b",n): return ("r","r")
    return None
def tipo_medio_optico(n):
    # SOLO con token explícito del medio. "disco compacto"/"disco" NO prueban CD (uso laxo en pliegos);
    # NO derivar el medio por la capacidad. Si la capacidad contradice el token, dejar indeterminado.
    tok=("dvd","dvd") if re.search(r"\bdvd\b",n) else (("cd","cd") if re.search(r"\bcd\b",n) else None)
    if not tok: return None                      # "disco compacto" solo → indeterminado (va a faltantes)
    cap=cap_gb(n)
    if cap and cap[0]!="AMBIGUO":                 # contradicción medio↔capacidad → no asumir
        v=cap[0]
        if tok[0]=="cd" and v>=4.7: return None   # 4.7/8.5 GB no es CD
        if tok[0]=="dvd" and v<=0.9: return None
    return tok
def formato_continuo(n):   # dimensión de pliego "9 1/2 x 11" (admite x, *, ×)
    m=re.search(r"9\s*(?:1/2|½|\.5)?\s*[x*×]\s*11",n)
    return ("9.5x11",m.group(0)) if m else None
def partes_continuo(n):    # nº de vías/copias tras el ancho 11": "…x 11 x 3", "…x11x4x5.5" (vía=4, NO 5.5)
    # sin \b (fallaba en "11x4x..."); tras "11[x]" solo se toma 1 dígito → "5.5" nunca es alcanzable.
    m=re.search(r"11\s*[x*×]\s*(\d)",n)
    return (int(m.group(1)),m.group(0)) if m else None
def quimico_continuo(n):
    if re.search(r"\b(quimico|autocopiativ|autocopiante)\b",n): return ("quimico","quimico")
    if re.search(r"con desglose",n): return ("desglose","con desglose")
    return None
def empaque(n):   # presentación jerárquica adicional: "caja de 10 paquetes"
    m=re.search(r"caja de (\d+) paquete",n)
    return (f"caja_x{m.group(1)}paq",m.group(0)) if m else None

# ── CONFIG por categoría: atributos de SEGMENTO (subfamilia) y ESPECÍFICOS (intercambiabilidad) ──
EXTRACT={
 "almacenamiento":{"tecnologia":tecnologia_alm,"capacidad_gb":cap_gb,"capacidad_min_gb":cap_min_gb,
                   "interfaz":interfaz,"formato":formato_disco,"instalacion":instalacion},
 "optico":        {"capacidad_gb":cap_gb,"tipo_grabacion":tipo_grabacion,"tipo_medio":tipo_medio_optico},
 "ram":           {"generacion":generacion_ddr,"capacidad_gb":cap_gb,"capacidad_min_gb":cap_min_gb,
                   "frecuencia_mhz":frecuencia_mhz,"formato":formato_ram},
 "papel_bond":    {"tamano":tamano_papel,"gramaje_gm2":gramaje,"color":color,"hojas":cantidad_hojas,"empaque":empaque},
 "papel_continuo":{"formato_continuo":formato_continuo,"partes":partes_continuo,"gramaje_gm2":gramaje,
                   "hojas":cantidad_hojas,"tipo":quimico_continuo},
 "papel_impreso": {"tamano":tamano_papel,"gramaje_gm2":gramaje,"color":color,"hojas":cantidad_hojas},
 "sobre_manila":  {"tamano":tamano_papel,"gramaje_gm2":gramaje,"color":color},
 "llanta":        {"medida":llanta_medida,"pliegues":pliegues,"huella":huella_llanta,"tipo_constr":tipo_constr,
                   "camara":camara_llanta,"ponchillo":ponchillo},
}
# SEGMENTO = subfamilia de demanda; ESPECIFICO = discriminantes de intercambiabilidad (producto).
# Sobres: TAMAÑO es la subfamilia (decisión del usuario); gramaje/color → específico.
SEGMENTO={"almacenamiento":["tecnologia","capacidad_gb"],"optico":["tipo_medio","capacidad_gb"],
          "ram":["generacion","capacidad_gb"],"papel_bond":["tamano","gramaje_gm2"],
          "papel_continuo":["formato_continuo","partes"],"papel_impreso":["tamano"],
          "sobre_manila":["tamano"],"llanta":["medida"]}
ESPECIFICO={"almacenamiento":["interfaz","formato"],"optico":[],"ram":["frecuencia_mhz","formato"],
            "papel_bond":["color"],"papel_continuo":[],"papel_impreso":[],
            "sobre_manila":["gramaje_gm2","color"],"llanta":["pliegues","huella","tipo_constr"]}

def extraer(desc):
    n=nrm(desc); cat=categoria(n)
    if cat is None: return None
    if cat=="consumible_impresion":   # para regresión se usa el verificador existente; aquí no se re-extrae
        return {"categoria":cat,"atributos":{},"evidencia":{},"nivel_identificable":"(verificador_codigos)","faltantes":[],"ambiguos":{}}
    atn={}; ev={}; amb={}
    for a,fn in EXTRACT[cat].items():
        r=fn(n)
        if r is None: continue
        if r[0]=="AMBIGUO":                    # contradicción/incertidumbre: NO se asume (#4)
            amb[a]=r[1]; continue
        atn[a]=r[0]; ev[a]=r[1]
    seg=SEGMENTO[cat]; esp=ESPECIFICO[cat]
    seg_ok=bool(seg) and all(a in atn for a in seg)
    esp_ok=seg_ok and bool(esp) and all(a in atn for a in esp)
    nivel="producto" if esp_ok else ("subfamilia" if seg_ok else "familia_amplia")
    faltan=[a for a in (seg+esp) if a not in atn]
    return {"categoria":cat,"atributos":atn,"evidencia":ev,"nivel_identificable":nivel,"faltantes":faltan,"ambiguos":amb}

if __name__=="__main__":
    items=get("hist_items?select=id,cuce,nro_item,descripcion,unspsc_codigo")
    por_desc=collections.defaultdict(list)
    for it in items:
        c=cuerpo(it["descripcion"])
        if c: por_desc[c].append(it)
    uniq=sorted(por_desc)
    res={d:extraer(d) for d in uniq}
    res={d:r for d,r in res.items() if r}
    # ── reporte de cobertura ──
    porcat=collections.defaultdict(list)
    for d,r in res.items(): porcat[r["categoria"]].append((d,r))
    objetivo=["almacenamiento","ram","papel_bond","papel_continuo","papel_impreso","sobre_manila",
              "llanta","optico","consumible_impresion"]
    lines=["# Etapa 1 — Cobertura del extractor de atributos (solo lectura)\n"]
    lines.append(f"descripciones únicas totales: {len(uniq)} · con categoría objetivo: {len(res)}\n")
    lines.append("| categoría | ítems únicos | producto | subfamilia | familia_amplia |")
    lines.append("|---|---|---|---|---|")
    for cat in objetivo:
        rows=porcat.get(cat,[])
        if not rows: continue
        c=collections.Counter(r["nivel_identificable"] for _,r in rows)
        n=len(rows)
        def pc(k): return f"{c.get(k,0)} ({100*c.get(k,0)//n}%)"
        lines.append(f"| {cat} | {n} | {pc('producto')} | {pc('subfamilia')} | {pc('familia_amplia')} |")
    lines.append("\n## Fill-rate por atributo (de los ítems de cada categoría)")
    for cat in objetivo:
        rows=porcat.get(cat,[])
        if not rows or cat=="consumible_impresion": continue
        n=len(rows); fill=collections.Counter()
        for _,r in rows:
            for a in r["atributos"]: fill[a]+=1
        det=", ".join(f"{a} {100*fill[a]//n}%" for a in (SEGMENTO.get(cat,[])+ESPECIFICO.get(cat,[])))
        lines.append(f"- **{cat}** (n={n}): {det}")
    lines.append("\n## Nota (#4 demanda)")
    lines.append("Las cantidades/precios/adjudicaciones autoritativos vienen de los campos FORM de "
                 "`hist_items`, NO del texto. La cantidad/unidad extraída del texto es solo descriptiva; "
                 "la agregación (normalización de unidades y prevención de doble conteo entre etapas de un "
                 "mismo proceso) es una etapa POSTERIOR, no se calcula aquí.")
    open(os.path.join(OUT,"extractor_cobertura.md"),"w").write("\n".join(lines))

    # ── vista interna (NO sobreescribe la muestra ya revisada; la muestra NUEVA la hace otro script) ──
    with open(os.path.join(OUT,"extractor_cobertura_vista.csv"),"w",newline="",encoding="utf-8") as fh:
        w=csv.writer(fh)
        w.writerow(["categoria","nivel_identificable","descripcion","atributos","evidencia","faltantes","ambiguos"])
        for cat in objetivo:
            rows=porcat.get(cat,[])
            if not rows or cat=="consumible_impresion": continue
            random.shuffle(rows)
            for d,r in rows[:9]:
                w.writerow([cat,r["nivel_identificable"],d[:150],
                            json.dumps(r["atributos"],ensure_ascii=False),
                            json.dumps(r["evidencia"],ensure_ascii=False),
                            ",".join(r["faltantes"]),json.dumps(r.get("ambiguos",{}),ensure_ascii=False)])
    print("escrito reportes/extractor_cobertura.md + reportes/extractor_cobertura_vista.csv")
    print("por categoría:", {c:len(v) for c,v in porcat.items()})
