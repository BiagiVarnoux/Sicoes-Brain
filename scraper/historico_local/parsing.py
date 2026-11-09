"""Parseo conservador: preserva todos los TR, deriva campos sin fusionar fases."""
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from decimal import Decimal,InvalidOperation
from xml.etree import ElementTree
from bs4 import BeautifulSoup


def sha(data):return hashlib.sha256(data).hexdigest()
def norm(text):return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c)).lower().split())


def number(raw):
    s=raw.strip().replace('\xa0','').replace(' ','')
    if not re.fullmatch(r'-?\d+(?:[.,]\d+)*',s):return {'value':None,'status':'not_numeric'}
    if '.' in s and ',' in s:
        decimal=',' if s.rfind(',')>s.rfind('.') else '.';thousand='.' if decimal==',' else ','
        s=s.replace(thousand,'').replace(decimal,'.')
    elif re.fullmatch(r'-?\d{1,3}(?:[.,]\d{3})+',s):
        return {'value':None,'status':'ambiguous_separator','candidates':[s.replace(',','.'),s.replace(',','').replace('.','')]}
    else:s=s.replace(',','.')
    try:return {'value':str(Decimal(s)),'status':'normalized'}
    except InvalidOperation:return {'value':None,'status':'invalid_number'}


def validate(data,kind,cuce):
    lead=data.lstrip();result={'valid':False,'detected_type':'unknown','errors':[]}
    try:
        if lead.startswith((b'{',b'[')):
            obj=json.loads(data);text=json.dumps(obj).lower()
            result.update(detected_type='json',errors=['captcha' if 'captcha' in text else 'session' if ('sesion' in norm(text) or 'session' in text) else 'json_not_document']);return result
    except (ValueError,UnicodeDecodeError):pass
    if kind.startswith('FORM'):
        soup=BeautifulSoup(data,'lxml')
        for s in soup(['script','style']):s.decompose()
        text=soup.get_text(' ',strip=True)
        result['detected_type']='html'
        if not soup.find('table'):result['errors'].append('no_tables')
        if cuce not in re.sub(r'\s+','',text):result['errors'].append('cuce_not_in_visible_document')
        if 'captcha' in norm(text) and not soup.find('table'):result['errors'].append('captcha')
        # Si el formulario visible declara un número, exige que corresponda al solicitado.
        labels=set('FORM'+m for m in re.findall(r'\bFORM(?:ULARIO)?\s*[-:]?\s*(\d{3})\b',text,re.I))
        if labels and kind not in labels:result['errors'].append('wrong_form_kind')
        if 'sesion' in norm(text) and 'cuce_not_in_visible_document' in result['errors']:result['errors'].append('session')
        result['valid']=not result['errors'];return result
    if data.startswith(b'PK'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(i.file_size for i in z.infolist())>100_000_000:raise ValueError('archive_too_large')
                if 'word/document.xml' in z.namelist():
                    ElementTree.fromstring(z.read('word/document.xml'));typ='docx'
                else:
                    if z.testzip() is not None:raise ValueError('archive_crc_error')
                    typ='zip'
                result.update(valid=True,detected_type=typ);return result
        except (ValueError,zipfile.BadZipFile,ElementTree.ParseError):result['errors'].append('invalid_archive');return result
    if data.startswith(b'%PDF-'):
        result.update(valid=b'%%EOF' in data[-4096:],detected_type='pdf')
        if not result['valid']:result['errors'].append('pdf_missing_eof')
        return result
    if data.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        result.update(valid=True,detected_type='ole');result['warnings']=['container_only_not_document_semantics'];return result
    result['errors']=['html_or_session_response' if b'<html' in lead[:300].lower() else 'unsupported_or_invalid_type'];return result


ALIASES=[
 ('cantidad_recibida',r'recepcionada'),('cantidad_solicitada',r'cantidad solicitada'),
 ('precio_preseleccionado',r'precio.*preseleccion'),('precio_referencial_total',r'precio.*referencial.*total|precio total'),
 ('precio_referencial_unitario',r'precio.*referencial.*unitario|precio.*unitario.*referencial'),
 ('precio_adjudicado',r'precio.*(?:contratado|adjudicado)'),('monto_ejecutado',r'monto real ejecutado'),
 ('monto_total',r'monto total|total contratado'),('precio_unitario',r'precio unitario'),
 ('descripcion',r'descripci[oó]n'),('unspsc',r'codigo.*catalogo|codigo catalogo'),
 ('unidad',r'unidad.*medida'),('cantidad',r'^cantidad'),('proveedor',r'razon social|proponente contratado'),
 ('fecha_firma',r'fecha.*firma'),('fecha_definitiva',r'fecha.*recepcion definitiva'),
 ('fecha_provisional',r'fecha.*recepcion provisional'),('fecha_contrato',r'fecha.*recepcion segun contrato'),
 ('contrato',r'nro.*contrato|nro.*documento'),('estado',r'estado.*recepcion|estado.*item')]
NUMERIC={'cantidad_recibida','cantidad_solicitada','precio_preseleccionado','precio_referencial_total',
 'precio_referencial_unitario','precio_adjudicado','monto_ejecutado','monto_total','precio_unitario','cantidad'}


def field_name(text):
    h=norm(text)
    return next((key for key,pattern in ALIASES if re.search(pattern,h)),None)


def parse_html(data,kind,cuce,version_id):
    soup=BeautifulSoup(data,'lxml');rows=[];warnings=[];item_tables=set();empty_tables=set();md=[f'# {kind} — {cuce}','']
    # El texto íntegro queda además de las tablas; Markdown es derivado, HTML es autoridad.
    clean=BeautifulSoup(data,'lxml')
    for tag in clean(['script','style']):tag.decompose()
    md.extend([clean.get_text('\n',strip=True),'','## Tablas originales',''])
    for ti,table in enumerate(soup.find_all('table'),1):
        directrows=[tr for tr in table.find_all('tr') if tr.find_parent('table') is table]
        title=next((tr.get_text(' ',strip=True)[:250] for tr in directrows),f'table-{ti}')
        section=f'{ti}:{title}'
        headers=[];semantic=[]
        md.append(f'### Tabla {ti}: '+title)
        for ri,tr in enumerate(directrows,1):
            cells=tr.find_all(['td','th'],recursive=False)
            raw=[{'html':str(c),'text':c.get_text('',strip=False)} for c in cells]
            text=[c.get_text(' ',strip=True) for c in cells]
            names=[field_name(t) for t in text]
            container=bool(tr.find('table'))
            isheader=not container and len(cells)>=3 and len({n for n in names if n})>=2 and not (text and text[0].isdigit())
            if isheader:
                headers=text;semantic=names
                if 'descripcion' in names and ('unspsc' in names or kind=='FORM500'):item_tables.add(ti)
            if any('no existen registros' in norm(t) for t in text):empty_tables.add(ti)
            numericfirst=bool(text and text[0].isdigit())
            rowkind='container' if container else 'header' if isheader else 'data' if numericfirst else 'other'
            fields=[]
            if rowkind=='data':
                for ci,t in enumerate(text):
                    name=semantic[ci] if ci<len(semantic) else None
                    derived=number(t) if name in NUMERIC else {'value':t,'status':'whitespace_only'}
                    fields.append({'column':ci,'header_raw':headers[ci] if ci<len(headers) else None,
                        'name':name or f'column_{ci}','raw':raw[ci]['text'],'normalized':derived})
            item=bool(rowkind=='data' and any(f['name']=='descripcion' for f in fields) and
                (any(f['name']=='unspsc' for f in fields) or kind=='FORM500'))
            oid=sha(json.dumps([cuce,kind,version_id,ti,section,ri],ensure_ascii=False).encode())
            rows.append({'observation_id':oid,'section':section,'table_position':ti,'row_position':ri,
                'row_kind':rowkind,'raw_cells':raw,'raw_html':str(tr),'fields':fields,'is_item_record':item})
            if not container:
                md.append('| '+' | '.join(t.replace('|','\\|').replace('\n','<br>') for t in text)+' |')
        md.append('')
    items=sum(r['is_item_record'] for r in rows);generic=sum(r['row_kind']=='data' and not r['is_item_record'] for r in rows)
    if not rows:status='CAPTURED_NO_RECORDS'
    elif items:status='PARSED'
    elif item_tables & empty_tables:status='CAPTURED_NO_RECORDS'
    else:status='PARSED_PARTIAL';warnings.append('no_mapped_item_rows; all_raw_rows_preserved')
    return {'kind':kind,'cuce':cuce,'status':status,'raw_rows':len(rows),'item_rows':items,'generic_rows':generic,
            'warnings':warnings,'rows':rows},'\n'.join(md)


def convert_document(data,typ):
    if typ=='docx':
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            tree=ElementTree.fromstring(z.read('word/document.xml'))
        paragraphs=[]
        for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
            paragraphs.append(''.join(t.text or '' for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')))
        return '\n\n'.join(paragraphs)
    if typ=='pdf':
        from pypdf import PdfReader
        return '\n\n'.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(data)).pages)
    raise ValueError('local_conversion_not_supported:'+typ)
