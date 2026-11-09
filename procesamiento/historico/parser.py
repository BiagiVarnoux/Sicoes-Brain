"""Observaciones por fila y fase. Sin importaciones del scraper ni clientes remotos."""
import hashlib
import json
import re
import unicodedata
from decimal import Decimal,InvalidOperation,localcontext
from fractions import Fraction
from bs4 import BeautifulSoup

VERSION='observaciones-1.1'
PHASE={'100':'requerimiento','110':'requerimiento','170':'adjudicacion','200':'contratacion','220':'contratacion','500':'recepcion'}
NUMERIC={'cantidad','cantidad_contratada','cantidad_adjudicada','cantidad_solicitada','cantidad_reportada_recepcion',
         'precio_unitario_documentado','precio_unitario_referencial','precio_total_referencial','precio_unitario_preseleccionado','importe_total_preseleccionado',
         'precio_unitario_adjudicado','importe_total_adjudicado','precio_unitario_contratado','importe_total_contratado','monto_real_ejecutado'}


def norm(text):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c)).lower().split())
def sha(data):return hashlib.sha256(data).hexdigest()
def identity(*parts):return sha(json.dumps(parts,ensure_ascii=False,separators=(',',':')).encode())


def parse_number(raw):
    s=raw.strip().replace('\xa0','').replace(' ','')
    if not s:return {'value':None,'status':'missing'}
    leading_decimal=bool(re.fullmatch(r'-?[.,]\d+',s))
    if leading_decimal:s=s.replace('-.','-0.').replace('-,','-0,') if s.startswith('-') else '0'+s
    if not re.fullmatch(r'-?\d+(?:[.,]\d+)*',s):return {'value':None,'status':'not_numeric'}
    if '.' in s and ',' in s:
        dec=',' if s.rfind(',')>s.rfind('.') else '.';thou='.' if dec==',' else ','
        if not re.fullmatch(r'-?\d{1,3}(?:'+re.escape(thou)+r'\d{3})+'+re.escape(dec)+r'\d+',s):
            return {'value':None,'status':'invalid_grouping'}
        s=s.replace(thou,'').replace(dec,'.')
    elif s.count('.')+s.count(',')==1:
        if not leading_decimal and len(re.split('[.,]',s)[1])==3:
            return {'value':None,'status':'ambiguous_separator','candidates':[s.replace(',','.'),s.replace(',','').replace('.','')]}
        s=s.replace(',','.')
    elif s.count('.')+s.count(',')>1:
        return {'value':None,'status':'ambiguous_grouping'}
    try:
        value=Decimal(s)
        return {'value':format(value,'f'),'status':'normalized'}
    except InvalidOperation:return {'value':None,'status':'invalid_number'}


def field_name(header,form):
    h=norm(header)
    if h in ('#','n°','nº','nro.','nro','no.'):return 'nro_item_documento'
    if h.startswith('descripcion') and ('bien' in h or h=='descripcion'):return 'descripcion'
    if 'catalog' in h:return 'codigo_catalogo'
    if 'objeto de gasto' in h or h.startswith('partida'):return 'partida_presupuestaria'
    if 'unidad de medida' in h:return 'unidad_medida'
    if 'la cantidad es' in h:return 'tipo_cantidad'
    if 'cantidad' in h:
        if 'solicitada' in h:return 'cantidad_solicitada'
        if 'recepcionada' in h:return 'cantidad_reportada_recepcion'
        if 'contratad' in h:return 'cantidad_contratada'
        if 'adjudicad' in h:return 'cantidad_adjudicada'
        return 'cantidad'
    if 'unitario' in h:
        if 'preseleccionado' in h:return 'precio_unitario_preseleccionado'
        if 'referencial' in h:return 'precio_unitario_referencial'
        if 'adjudicado' in h:return 'precio_unitario_adjudicado'
        if 'contratado' in h or form in ('200','220'):return 'precio_unitario_contratado'
        return 'precio_unitario_documentado'
    if 'total' in h or 'monto real ejecutado' in h:
        if 'ejecutado' in h:return 'monto_real_ejecutado'
        if 'preseleccionado' in h:return 'importe_total_preseleccionado'
        if 'referencial' in h:return 'precio_total_referencial'
        if 'adjudicado' in h:return 'importe_total_adjudicado'
        if 'contratado' in h or form in ('200','220'):return 'importe_total_contratado'
    if 'proponente contratado' in h or 'proponente adjudicado' in h or 'razon social' in h:return 'proveedor_documentado'
    if 'estado de la recepcion' in h:return 'estado_recepcion'
    if 'estado del item' in h:return 'estado_item'
    if 'causal de declaratoria' in h:return 'causal_desierta'
    if 'fecha' in h:
        if 'firma' in h:return 'fecha_firma_contrato'
        if 'definitiva' in h:return 'fecha_recepcion_definitiva'
        if 'provisional' in h:return 'fecha_recepcion_provisional'
        if 'segun contrato' in h:return 'fecha_recepcion_segun_contrato'
    if 'contrato' in h:return 'nro_contrato_documentado'
    if h=='origen':return 'origen'
    if h=='lote' or 'nro. lote' in h:return 'lote_documentado'
    if 'marca' in h:return 'marca_documentada'
    return None


def direct_rows(table):return [r for r in table.find_all('tr') if r.find_parent('table') is table]
def cells(tr):return tr.find_all(['td','th'],recursive=False)
def visible(cell):return cell.get_text(' ',strip=True)


def section(table):
    for row in direct_rows(table):
        cs=cells(row)
        if len(cs)==1 and not row.find('table') and re.match(r'^\d+[.)]\s*\D',visible(cs[0])):return visible(cs[0])
    prev=table.find_previous(lambda t:t.name in ('td','th','h1','h2','h3','h4','legend') and not t.find('table') and bool(re.match(r'^\d+[.)]\s*\D',t.get_text(' ',strip=True))))
    return prev.get_text(' ',strip=True) if prev else 'Sección sin título explícito'


def stage(form,title):
    h=norm(title)
    if 'no contratados' in h:return 'no_contratacion','no_contratado'
    if 'desiertos' in h:return 'declaratoria_desierta','desierto'
    return PHASE[form],{'requerimiento':'requerido','adjudicacion':'adjudicado','contratacion':'contratado','recepcion':'recepcion_reportada'}[PHASE[form]]


def unique_field(fields,key):
    found=[f for f in fields if f['name']==key]
    return found[0] if len(found)==1 else None


def derive_received(fields):
    q=unique_field(fields,'cantidad_reportada_recepcion');total=unique_field(fields,'monto_real_ejecutado');state=unique_field(fields,'estado_recepcion')
    if not state or norm(state['visible']) not in ('recibido','recibida','recepcionado','recepcionada'):
        return [],['precio_recepcion_no_derivado: estado no confirma cantidad recibida']
    if not q or not total or q['normalized'].get('value') is None or total['normalized'].get('value') is None:
        return [],['precio_recepcion_no_derivado: cantidad o importe no numérico inequívoco']
    quantity=Decimal(q['normalized']['value']);amount=Decimal(total['normalized']['value'])
    if quantity<=0 or amount<0:return [],['precio_recepcion_no_derivado: cantidad no positiva o importe negativo']
    ratio=Fraction(amount)/Fraction(quantity);den=ratio.denominator
    for prime in (2,5):
        while den%prime==0:den//=prime
    with localcontext() as ctx:
        ctx.prec=40;value=format(amount/quantity,'f')
    return [{'name':'precio_unitario_recepcion_derivado','value':value,'formula':'monto_real_ejecutado / cantidad_reportada_recepcion',
             'operands':{'amount':str(amount),'quantity':str(quantity)},'source_columns':[total['column'],q['column'],state['column']],
             'exact_fraction':f'{ratio.numerator}/{ratio.denominator}','precision':'exact' if den==1 else '40_significant_digits',
             'qualification':'Derivado de recepción; no es precio unitario explícito ni prueba de identidad comercial'}],[]


def arithmetic_warnings(fields):
    for q,u,t in [('cantidad','precio_unitario_referencial','precio_total_referencial'),('cantidad','precio_unitario_preseleccionado','importe_total_preseleccionado'),
                  ('cantidad_adjudicada','precio_unitario_adjudicado','importe_total_adjudicado'),('cantidad_contratada','precio_unitario_contratado','importe_total_contratado'),('cantidad','precio_unitario_contratado','importe_total_contratado')]:
        fs=[unique_field(fields,k) for k in (q,u,t)]
        if all(f and f['normalized'].get('value') is not None for f in fs):
            a,b,c=[Decimal(f['normalized']['value']) for f in fs]
            if abs(a*b-c)>Decimal('.01'):return ['desajuste_aritmetico: revisar impuestos, redondeo o fuente; valores no corregidos']
    return []


def parse_document(data,cuce,form,source_path,document_key):
    if form not in PHASE:raise ValueError('Formulario no soportado: '+form)
    soup=BeautifulSoup(data,'lxml')
    if cuce not in re.sub(r'\s+','',soup.get_text()):raise ValueError('CUCE ausente del documento')
    digest=sha(data);doc_id=identity(cuce,form,source_path,digest,document_key)
    result={'document_id':doc_id,'cuce':cuce,'form':form,'source_path':source_path,'source_sha256':digest,'document_key':document_key,
            'tables':[],'raw_rows':[],'observations':[],'context':[],'contract_context':[],'warnings':[]}
    for ti,table in enumerate(soup.find_all('table'),1):
        trs=direct_rows(table);title=section(table);container=bool(table.find('table'))
        audit={'table_position':ti,'section':title,'classification':'container' if container else 'non_goods_uninterpreted',
               'direct_rows':len(trs),'header_row':None,'detected_goods_rows':0,'extracted_goods_rows':0,'unextracted_rows':[],
               'excluded_rows':[],'unknown_headers':[],'warnings':[]}
        result['tables'].append(audit);headers=None;names=None;declared=[];contract_headers=None
        for ri,tr in enumerate(trs,1):
            cs=cells(tr);texts=[visible(c) for c in cs];raw=[c.get_text('',strip=False) for c in cs]
            nested=bool(tr.find('table'))
            row_record={'table_position':ti,'row_position':ri,'classification':'container' if nested else 'other',
                        'cells':[{'text':r,'visible':v,'html':str(c),'rowspan':c.get('rowspan','1'),'colspan':c.get('colspan','1')} for c,r,v in zip(cs,raw,texts)],
                        'raw_html':None if nested else str(tr)}
            result['raw_rows'].append(row_record)
            if nested:continue
            mapped=[field_name(t,form) for t in texts]
            is_header='descripcion' in mapped and ('codigo_catalogo' in mapped or form=='500' and 'cantidad_reportada_recepcion' in mapped)
            if is_header:
                headers=texts;names=mapped;audit.update(classification='goods',header_row=ri)
                audit['unknown_headers']=[{'column':i,'header':h} for i,(h,k) in enumerate(zip(headers,names),1) if k is None]
                row_record['classification']='goods_header';continue
            if headers is None:
                hs=[norm(t) for t in texts]
                if 'nombre o razon social' in hs and 'nro. documento' in hs:
                    contract_headers=texts
                elif contract_headers and len(texts)==len(contract_headers) and texts[0].isdigit():
                    result['contract_context'].append({'table_position':ti,'row_position':ri,'fields':[{'column':i,'header_raw':h,'raw':v} for i,(h,v) in enumerate(zip(contract_headers,raw),1)]})
                if not container:
                    pairs=[]
                    if len(texts)==2 and texts[0].strip().endswith(':'):pairs=[(0,1)]
                    elif len(texts)==3 and texts[1]==':':pairs=[(0,2)]
                    elif len(texts)==4 and norm(texts[0])=='moneda':pairs=[(0,1),(2,3)]
                    for label_col,value_col in pairs:
                        result['context'].append({'scope':'document','table_position':ti,'row_position':ri,
                                                  'label_column':label_col+1,'value_column':value_col+1,
                                                  'label':texts[label_col],'value':raw[value_col]})
                continue
            flat=norm(' '.join(texts))
            if not texts or not flat:
                audit['excluded_rows'].append({'row':ri,'reason':'empty_or_header_rowspan_continuation'});continue
            if flat.startswith('no existen registros'):
                audit['excluded_rows'].append({'row':ri,'reason':'explicit_no_records'});continue
            if flat.startswith('total:') or flat=='total':
                row_record['classification']='total';declared.append(raw[-1]);audit['excluded_rows'].append({'row':ri,'reason':'total_not_item'});continue
            # Conservador: toda fila restante de una tabla de bienes queda contabilizada.
            audit['detected_goods_rows']+=1;row_record['classification']='goods_candidate'
            reason=None
            if len(cs)!=len(headers):reason='column_count_mismatch'
            elif any(int(c.get('rowspan',1))!=1 or int(c.get('colspan',1))!=1 for c in cs):reason='unsupported_data_span'
            elif not texts[names.index('descripcion')]:reason='empty_description'
            if reason:
                audit['unextracted_rows'].append({'row':ri,'reason':reason});continue
            fields=[]
            for ci,(header,key,value,text) in enumerate(zip(headers,names,raw,texts),1):
                key=key or f'column_{ci}'
                normalized=parse_number(text) if key in NUMERIC else {'value':text,'status':'visible_whitespace_only'}
                fields.append({'column':ci,'header_raw':header,'name':key,'raw':value,'visible':text,'normalized':normalized})
            phase,status=stage(form,title);desc=unique_field(fields,'descripcion')
            warnings=[f"columna_{f['column']}: {f['normalized']['status']}" for f in fields if f['name'] in NUMERIC and f['normalized']['status'] not in ('normalized','missing')]
            warnings+=arithmetic_warnings(fields)
            if names.count('descripcion')!=1 or any(names.count(n)>1 for n in names if n):warnings.append('encabezados_semanticos_duplicados')
            derived=[]
            if form=='500':
                derived,extra=derive_received(fields);warnings+=extra
                explicit=unique_field(fields,'precio_unitario_documentado')
                if derived and explicit and explicit['normalized'].get('value') is not None and abs(Decimal(explicit['normalized']['value'])-Decimal(derived[0]['value']))>Decimal('.01'):
                    warnings.append('precio_unitario_documentado_difiere_del_derivado; no_se_corrige_el_original')
            if form=='200' and unique_field(fields,'proveedor_documentado') is None:warnings.append('proveedor_no_documentado_en_fila; contexto_contractual_conservado_sin_asociar')
            if not re.fullmatch(r'\d+',texts[0]):warnings.append('numero_item_no_convencional; identidad basada en posición')
            obs={'observation_id':identity(doc_id,ti,ri),'document_id':doc_id,'cuce':cuce,'form':form,'source_path':source_path,'source_sha256':digest,
                 'section':title,'section_id':f'table_{ti}','table_position':ti,'row_position':ri,'stage':phase,'event_status':status,
                 'description_raw':desc['raw'],'description_visible':desc['visible'],'fields':fields,'derived':derived,'warnings':warnings,
                 'demand_role':'requerimiento_original_no_neto' if form in ('100','110') else 'otra_etapa_no_sumar'}
            result['observations'].append(obs);audit['extracted_goods_rows']+=1;row_record['classification']='goods_observation'
        if declared:
            audit['declared_totals_raw']=declared
        if audit['unknown_headers']:audit['warnings'].append('columnas_no_mapeadas_conservadas')
        if audit['detected_goods_rows']!=audit['extracted_goods_rows']:audit['warnings'].append('filas_detectadas_no_extraidas')
        if not container and headers is None:
            # Posibles tablas de bienes sin contrato conocido: no declararlas cubiertas.
            text=norm(' '.join(visible(c) for tr in trs for c in cells(tr)))
            if 'descripcion del bien' in text or 'precio unitario' in text and 'cantidad' in text:
                audit['classification']='uninterpreted_goods_candidate';audit['warnings'].append('posible_tabla_bienes_sin_encabezado_soportado')
    contracts={}
    for row in result['contract_context']:
        fs={norm(f['header_raw']):f['raw'].strip() for f in row['fields']}
        contracts.setdefault(fs.get('nro. documento'),set()).add(fs.get('nombre o razon social'))
    if any(key and len(values)>1 for key,values in contracts.items()):result['warnings'].append('numero_contrato_compartido_por_varios_proveedores; no_asociar_solo_por_numero')
    if not result['observations']:result['warnings'].append('documento_sin_observaciones_de_bienes; revisar tablas y vacíos explícitos')
    return result
