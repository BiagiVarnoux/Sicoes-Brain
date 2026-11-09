"""Atributos con evidencia y operadores; no verifica identidad comercial."""
import ast
from functools import lru_cache
from pathlib import Path
import re
from .parser import norm,sha

ROOT=Path(__file__).resolve().parents[2]
LEGACY=ROOT/'monitor/canonicalizacion/impresion/extractor_impresion.py'

@lru_cache(maxsize=1)
def code_patterns():
    # Reutilización de patrones literales; no ejecutar imports, dotenv ni motor.
    tree=ast.parse(LEGACY.read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_COD_FULL' for t in node.targets):return ast.literal_eval(node.value)
    raise ValueError('Cambió el contrato de patrones de consumibles')


def codes(text):
    mapped=text.replace('ª','A').replace('º','O');found={}
    if not re.search(r't[oó]ner|tonner|cartucho|tinta|drum|tambor',text,re.I):return []
    for pat,brand in code_patterns():
        if brand and brand not in norm(text):continue
        for m in re.finditer(pat,mapped,re.I):
            value=re.sub(r'[\s-]','',norm(m.group())).upper()
            found[(m.start(),m.end())]={'value':value,'evidence':text[m.start():m.end()],'start':m.start(),'end':m.end()}
    pat=r'\bserie\s*[:;]?\s*((?:CE|CF|CB|CC|TN|GPR|BT|Q|W|TK|DR)\s*[-]?\s*\d{1,5}[A-Z]?|\d{2}F[A-Z0-9]{4}|\d{2,3}\s*[AX])\b'
    for m in re.finditer(pat,mapped,re.I):
        a,b=m.span(1);value=re.sub(r'[\s-]','',norm(mapped[a:b])).upper()
        found[(a,b)]={'value':value,'evidence':text[a:b],'start':a,'end':b}
    return list(found.values())


def operator(text):
    n=norm(text)
    if re.search(r'minim|al menos|no menor|o superior|como minimo|\b>=|≥',n):return 'GE'
    if re.search(r'maxim|hasta|no mayor|como maximo|\b<=|≤',n):return 'LE'
    if 'exactamente' in n or re.search(r'(?<![<>])=(?!=)',n):return 'EQ'
    return 'DECLARADO_SIN_OPERADOR'


def numeric(raw):
    s=raw.strip()
    if re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+',s):return s.replace('.','').replace(',','')
    return s.replace(',','.')


def attributes(text,reference=None):
    out=[]
    def add(name,value,evidence,start,end,op=None,unit=None,role='requisito_tecnico',**extra):
        if text[start:end]!=evidence:raise ValueError('Evidencia no literal')
        prefix=norm(text[max(0,start-45):start])
        if re.search(r'no\s+(?:se\s+)?(?:acepta(?:ra|ran)?|permit(?:e|en)|requiere)?\s*$',prefix):op='PROHIBIDO'
        out.append({'name':name,'value':value,'unit':unit,'unit_normalized':{'cms':'cm','grs':'g','gr':'g','mltr':'ml'}.get(norm(unit),norm(unit)) if unit else None,'operator':op or operator(text),'evidence':evidence,'span':[start,end],
                    'context':text,'reference':reference,'role':role,'required':not bool(re.search(r'\bopcional\b',norm(text))),**extra})
    for c in codes(text):add('codigo_consumible_declarado',c['value'],c['evidence'],c['start'],c['end'],'DECLARADO',role='identificador_declarado_no_verificado')
    # Compatibilidad separada; ningún modelo de impresora se convierte en código del tóner.
    if re.search(r't[oó]ner|cartucho|tinta|compatible',text,re.I):
        m=re.search(r'(?:modelo(?:\s+de\s+impresora)?|compatible\s+con)\s*[:;]?\s*(.+?)(?=;?\s*serie\b|[;.]\s*color\b|$)',text,re.I)
        if m:add('equipo_compatible_texto',m[1].strip(),m.group(),m.start(),m.end(),'COMPATIBILIDAD',role='compatibilidad_no_identidad')
    # Rangos numéricos: se conservan como dos extremos, no como igualdad.
    range_pat=r'(?<![A-Za-z0-9])(?:entre\s+)?(\d+(?:[.,]\d+)?)\s*(?:a|–|—|-|y)\s*(\d+(?:[.,]\d+)?)\s*(GB|MB|MHz|GHz|mm|cm|ml|g|grs?|ppm)\b'
    ranges=[]
    for m in re.finditer(r'(?<![A-Za-z0-9])(\d+(?:[.,]\d+)?)\s*(?:dpi|ppp|mm|cm)?\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(dpi|ppp|mm|cm)\b',text,re.I):
        name=('resolucion_optica' if 'optica' in norm(text) else 'resolucion_interpolada' if 'interpolada' in norm(text) else 'resolucion') if m[3].lower() in ('dpi','ppp') else 'dimensiones'
        add(name,[numeric(m[1]),numeric(m[2])],m.group(),m.start(),m.end(),unit=m[3]);ranges.append(m.span())
    for m in re.finditer(range_pat,text,re.I):
        if any(a<=m.start() and m.end()<=b for a,b in ranges):continue
        name='ram' if 'ram' in norm(text) and m[3].lower() in ('gb','mb') else 'rango_dimension' if m[3].lower() in ('mm','cm') else 'rango_tecnico'
        add(name,[numeric(m[1]),numeric(m[2])],m.group(),m.start(),m.end(),'RANGE',m[3]);ranges.append(m.span())
    for m in re.finditer(r'\b(\d+(?:[.,]\d+)?)\s*(GB|TB|MB|KB|GHz|MHz|dpi|ppp|ppm|ipm|CPS|mm|cms?|ml(?:tr)?|grs?|g|W|V|p[aá]ginas|hojas)\b',text,re.I):
        if any(a<=m.start() and m.end()<=b for a,b in ranges):continue
        unit=m[2];n=norm(text);prefix=norm(text[:m.start()]);u=norm(unit);op=operator(text)
        if u in ('gb','mb','tb','kb'):
            name='ram' if 'ram' in n else 'buffer' if 'buffer' in n else ('almacenamiento_ssd' if prefix.rfind('ssd')>prefix.rfind('hdd') else 'almacenamiento_hdd') if re.search('disco|ssd|hdd|almacenamiento',n) else 'cache_procesador' if 'cache' in n else 'capacidad_declarada'
        elif u in ('mhz','ghz'):name='frecuencia_memoria' if 'ddr' in n else 'frecuencia_procesador'
        elif u in ('dpi','ppp'):name='resolucion'
        elif u in ('ppm','ipm','cps'):name='velocidad_impresion_o_escaneo'
        elif u.startswith('pagina'):
            name='velocidad_impresion_o_escaneo' if re.search(r'(por|x) minuto',n) else 'rendimiento_paginas' if 'toner' in n or 'rendimiento' in n else 'ciclo_paginas'
            if name=='velocidad_impresion_o_escaneo':unit='paginas/min'
        elif u=='hojas':name='capacidad_hojas'
        elif u in ('mm','cm','cms'):
            prefix=norm(text[:m.start()])
            name='incremento_programable_lineas' if 'incrementos' in prefix else 'espaciado_lineas' if 'espacio entre' in n else 'dimension'
        elif u.startswith('ml'):name='volumen'
        elif u in ('g','gr','grs'):name='masa'
        elif u=='w':name='potencia'
        else:name='voltaje'
        if name=='velocidad_impresion_o_escaneo' and 'velocidad maxima' in n and not re.search('no mayor|hasta|como maximo',n):op='MAXIMO_DECLARADO'
        # "máximo ... 62 o superior" es una contradicción de operadores, no LE.
        if re.search('maxim',n) and re.search('o superior|minim',n):op='CONTRADICTORIO'
        add(name,numeric(m[1]),m.group(),m.start(),m.end(),op,unit)
    for name,pat in [('color',r'\b(?:color(?:\s+tinta)?\s*[:;]?\s*)?(negro|negra|azul|rojo|amarillo|blanco|transparente|surtido|varios)\b'),
                     ('material',r'\b(encobrado|metal|plastico|plástico|polipropileno|cartulina)\b'),
                     ('originalidad',r'\b(original(?:es)?)\b'),
                     ('tecnologia_impresion',r'\b(l[aá]ser\s+monocrom[aá]tic[oa]|t[eé]rmica\s+directa|matricial)\b'),
                     ('tipo_memoria',r'\bDDR[345]\b'),('duplex',r'\b(d[uú]plex|dos caras autom[aá]tico)\b'),('chip_electronico',r'\b(chip electr[oó]nico)\b')]:
        for m in re.finditer(pat,text,re.I):
            actual_name=name;role='requisito_tecnico'
            if name=='material' and re.search('documentos que admite|tipo de documentos',norm(text)):
                actual_name='material_documento_admitido';role='compatibilidad_no_identidad'
            if name=='color' and re.search(r'escan|blanco y negro|\bb/n\b',norm(text)):
                actual_name='modo_color_escaneo';role='modo_operacion_no_color_del_producto'
            add(actual_name,norm(m[1] if m.lastindex else m.group()),m.group(),m.start(),m.end(),'REQUIERE',role=role)
    for m in re.finditer(r'\b(HP|Brother|Canon|Lexmark|Epson)\b',text,re.I):add('marca_mencionada',m.group().lower(),m.group(),m.start(),m.end(),'MENCION',role='marca_sin_asignacion_de_identidad')
    for name,pat in [('presentacion',r'\b(?:presentaci[oó]n\s*)?(?:caja|paquete|taco)\s+(?:de\s*)?\d+\s*(?:unidades|unidad|hojas|colores)\b'),
                     ('procesador_referencia',r'\bIntel\s+Core\s+i\d[-\s]*\d{4,5}\b')]:
        for m in re.finditer(pat,text,re.I):add(name,m.group(),m.group(),m.start(),m.end(),'REFERENCIA_O_SUPERIOR' if operator(text)=='GE' else 'DECLARADO')
    for m in re.finditer(r'\b(marca|modelo)\s*:\s*\(?\s*especificar[^\n]*',text,re.I):
        add(m[1].lower(),None,m.group(),m.start(),m.end(),'DESCONOCIDO',required=True)
    for m in re.finditer(r'\((mm|cm)\)\s*:\s*(\d+(?:[.,]\d+)?)',text,re.I):
        op='CONTRADICTORIO' if re.search('maxim',norm(text)) and re.search('o superior|minim',norm(text)) else operator(text)
        add('dimension',numeric(m[2]),m.group(),m.start(),m.end(),op,m[1])
    # Alternativas: no convertir "azul o negro" en dos obligaciones simultáneas.
    clause=re.split(r'\(?\b(?:Manifestar|Especificar)\b',text,flags=re.I)[0]
    clause=re.sub(r'impresoras?\s+o\s+(?:fax|fotocopiadoras?)|bienes\s+o\s+servicios|\bo superior\b|y/o','',norm(clause))
    if re.search(r'\bo\b|\bu\b',clause):
        for a in out:
            if a['value'] is not None and a['operator'] not in ('CONTRADICTORIO','COMPATIBILIDAD'):
                a['operator_within_alternative']=a['operator'];a['operator']='ALTERNATIVA'
                a['alternative_context']=text
        groups={}
        for a in out:
            if a['operator']=='ALTERNATIVA':groups.setdefault(a['name'],[]).append(a)
        for name,group in groups.items():
            if len(group)>1:
                for a in group:a.update(operator='ONE_OF',alternatives=[g['value'] for g in group])
    return out
