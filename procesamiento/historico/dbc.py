"""Inventario DBC y segmentación de especificaciones, sin inferir páginas DOCX."""
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile
from .parser import norm,sha,identity
from .technical import attributes

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
HEADING='especificaciones tecnicas y condiciones tecnicas requeridas del bien'

def text(node):
    ps=list(node.iter(W+'p'))
    return '\n'.join(''.join(t.text or '' for t in p.iter(W+'t')) for p in ps) if ps else ''.join(t.text or '' for t in node.iter(W+'t'))

def section_bounds(markdown):
    lines=markdown.splitlines(keepends=True)
    start=next((i for i,l in enumerate(lines) if re.match(r'^\s*#{1,6}\s+',l) and HEADING in norm(l)),None)
    if start is None:return None
    stop=next((i for i in range(start+1,len(lines)) if 'criterios que se pueden anadir' in norm(lines[i]) or re.sub(r'[^a-z ]','',norm(lines[i])).strip()=='parte iii'),len(lines))
    return {'line_start':start+1,'line_end':stop,'text':''.join(lines[start:stop])}


def extract_blocks(original,markdown,cuce,dbc_id):
    with ZipFile(original) as archive:root=ET.fromstring(archive.read('word/document.xml'))
    body=list(root.find(W+'body'));all_tables=list(root.iter(W+'tbl'))
    start=next((i for i,e in enumerate(body) if e.tag==W+'p' and HEADING in norm(text(e)) and len(text(e))<150),None)
    if start is None:return [],{'error':'no_identifiable_original_spec_section'}
    stop=next((i for i in range(start+1,len(body)) if body[i].tag==W+'p' and ('criterios que se pueden anadir' in norm(text(body[i])) or norm(text(body[i]))=='parte iii')),len(body))
    md_section=section_bounds(markdown);blocks=[];tables_seen=[]
    for child in body[start+1:stop]:
        for table in child.iter(W+'tbl'):
            if table.findall('.//'+W+'tbl'):continue
            ti=all_tables.index(table)+1;rows=[]
            for ri,tr in enumerate(table.findall(W+'tr'),1):
                cells=[text(c) for c in tr.findall(W+'tc')]
                rows.append({'row':ri,'cells':cells})
            tables_seen.append({'table':ti,'rows':len(rows)})
            detailed=any(r['cells'] and re.fullmatch(r'\d+\.\d+',re.sub(r'\s+','',r['cells'][0])) for r in rows)
            current=None;last_title=''
            for r in rows:
                cs=r['cells'];first=re.sub(r'\s+','',cs[0]) if cs else ''
                if detailed:
                    if len(cs)==1 and cs[0].strip():
                        title=cs[0].strip()
                        if re.search(r'^(?:[A-Z]\.|III\.|IV\.|I V\.)',title):current=None
                        else:last_title=title
                    if len(cs)>=2 and first.isdigit() and 'caracteristicas tecnicas' in norm(cs[1]):
                        current={'number':first,'title':last_title,'requirements':[],'rows':[r],'table':ti,'row':r['row'],'quantity':None,'unit':None};blocks.append(current)
                    elif current and re.fullmatch(r'\d+\.\d+',first) and first.split('.')[0]==current['number']:
                        current['requirements'].append({'text':'\n'.join(cs[1:]),'table':ti,'row':r['row'],'cell':2});current['rows'].append(r)
                        m=re.search(r'cantidad\s*:\s*(\d+)\s*(\w+)', '\n'.join(cs[1:]),re.I)
                        if m:current.update(quantity=m[1],unit=m[2])
                elif len(cs)>=3 and re.fullmatch(r'(?:ITEM)?\d+',first,re.I):
                    title=cs[1].strip()
                    if not title:continue
                    # Dos diseños observados: [n,detalle,unidad,cantidad] y
                    # [n,detalle,condición común,cantidad,unidad]. No propagar celdas vacías.
                    last=cs[-1].strip();penultimate=cs[-2].strip()
                    quantity=last if re.fullmatch(r'\d+',last) else penultimate if re.fullmatch(r'\d+',penultimate) else None
                    unit=cs[-2] if quantity==last else cs[-1] if quantity else None
                    block={'number':re.sub(r'\D','',first),'title':title,'requirements':[{'text':cs[1],'table':ti,'row':r['row'],'cell':2}],
                           'rows':[r],'table':ti,'row':r['row'],'quantity':quantity,'unit':unit}
                    blocks.append(block)
    for block in blocks:
        block.update(cuce=cuce,dbc_id=dbc_id,spec_id=identity(dbc_id,block['table'],block['row'],block['number']),
                     source_section=HEADING,page=None,markdown_line_start=md_section['line_start'] if md_section else None,
                     markdown_line_end=md_section['line_end'] if md_section else None,
                     raw_text='\n'.join('\t'.join(r['cells']) for r in block['rows']))
        block['attributes']=[a for req in block['requirements'] for a in attributes(req['text'],{'table':req['table'],'row':req['row'],'cell':req['cell']})]
        block['unstructured_requirements']=[r for r in block['requirements'] if not attributes(r['text'])]
    return blocks,{'body_child_start':start+1,'body_child_end':stop,'markdown_section':md_section,'tables':tables_seen,
                   'note':'Se conserva sección completa; condiciones comunes no se asignan automáticamente a cada ítem. Página DOCX no estable: null.'}


def inventory(source,cuces):
    source=Path(source).resolve();result=[];all_blocks=[];checks={};sections=[]
    for cuce in cuces:
        folder=source/cuce;m=json.loads((folder/'manifest.json').read_text());docs=[(k,d) for k,d in m['documents'].items() if d['kind']=='DBC']
        entry={'cuce':cuce,'modality':m.get('metadata',{}).get('modalidad'),'status':'SIN_DBC_LOCAL','documents':[],
               'note':'Inventario de lo capturado localmente; no demuestra ausencia en SICOES.'}
        result.append(entry)
        for key,d in docs:
            record={'label':d['label'],'status':'DBC_ILEGIBLE','error':None};entry['documents'].append(record)
            v=next((v for v in reversed(d['versions']) if v.get('valid')),None)
            if not v:record['error']='sin_version_valida';continue
            original=(folder/v['path']).resolve()
            if not original.is_relative_to(folder.resolve()):raise ValueError('DBC fuera del CUCE')
            raw=original.read_bytes();checks[str(original)]=sha(raw)
            if sha(raw)!=v['sha256'] or len(raw)!=v['bytes']:raise ValueError('Integridad DBC incorrecta')
            record.update(original_path=str(original.relative_to(source)),original_sha256=sha(raw),format=v['format'])
            md=(folder/v.get('markdown','missing')).resolve()
            if not md.is_relative_to(folder.resolve()):raise ValueError('Markdown fuera del CUCE')
            if not md.is_file():record['error']='markdown_local_no_disponible';continue
            md_bytes=md.read_bytes();checks[str(md)]=sha(md_bytes);markdown=md_bytes.decode('utf-8-sig')
            record.update(markdown_path=str(md.relative_to(source)),markdown_sha256=sha(md_bytes),markdown_characters=len(markdown),
                          dbc_id=identity(cuce,key,sha(raw)))
            if not markdown.strip():record['error']='markdown_vacio';continue
            if v['format']!='docx':record['error']='segmentador_original_no_soporta_formato';continue
            try:blocks,section=extract_blocks(original,markdown,cuce,record['dbc_id'])
            except (ET.ParseError,ValueError,KeyError) as exc:record['error']=type(exc).__name__;continue
            for b in blocks:b.update(original_path=record['original_path'],original_sha256=record['original_sha256'],markdown_path=record['markdown_path'],markdown_sha256=record['markdown_sha256'])
            status='DBC_CON_ESPECIFICACIONES' if blocks else 'DBC_SIN_ESPECIFICACIONES_IDENTIFICABLES'
            record.update(status=status,spec_blocks=len(blocks),section_metadata={k:v for k,v in section.items() if k!='markdown_section'})
            entry['status']=status;all_blocks.extend(blocks)
            sections.append({'dbc_id':record['dbc_id'],'cuce':cuce,**section})
        if docs and entry['status']=='SIN_DBC_LOCAL':entry['status']='DBC_ILEGIBLE'
    return result,all_blocks,sections,checks
