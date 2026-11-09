"""CLI local repetible. Lee manifiestos/HTML, escribe únicamente salidas derivadas."""
import argparse
from collections import Counter
import csv
import io
import json
import os
from pathlib import Path
import sqlite3
import uuid
from .parser import PHASE,NUMERIC,VERSION,identity,parse_document,sha
from .review import check

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=Path(__file__).resolve().parent
DEFAULT_SOURCE=ROOT/'scraper/historico_local/data/historico_http_paginas_0660-10_2024'
PILOT=('24-0660-10-1499648-1-1','24-0660-10-1411332-1-1','24-0660-10-1412564-2-2')


def dumps(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)
def atomic(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:temp.write_bytes(data);os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()


def load(source,cuces):
    source=Path(source).resolve();documents=[];checks={};process_info=[]
    for cuce in sorted(cuces):
        folder=source/cuce
        manifest_path=folder/'manifest.json';manifest_bytes=manifest_path.read_bytes();checks[str(manifest_path)]=sha(manifest_bytes)
        manifest=json.loads(manifest_bytes)
        if manifest['cuce']!=cuce:raise ValueError('CUCE de manifiesto no corresponde a carpeta')
        forms=[]
        for key,doc in sorted(manifest['documents'].items()):
            if doc['kind']!='FORM':continue
            form=doc['label'].upper().replace('FORM','').replace(' ','');forms.append(form)
            version=next((v for v in reversed(doc['versions']) if v.get('valid')),None)
            if version is None:raise ValueError(f'{cuce} {form}: sin versión original válida')
            path=(folder/version['path']).resolve()
            if not path.is_relative_to(folder.resolve()):raise ValueError('Ruta de origen fuera del CUCE')
            data=path.read_bytes();digest=sha(data);checks[str(path)]=digest
            if digest!=version['sha256'] or len(data)!=version['bytes']:raise ValueError(f'{cuce} {form}: hash o tamaño incorrecto')
            rel=str(path.relative_to(source))
            if form not in PHASE:
                # Solo inventario. No se parsean tablas ni eventos de FORM 100-E.
                documents.append({'document_id':identity(cuce,form,rel,digest,key),'cuce':cuce,'form':form,'source_path':rel,'source_sha256':digest,'document_key':key,
                                  'status':'EXCLUIDO','exclusion_reason':'FORM 100-E excluido deliberadamente del alcance inicial' if form=='100-E' else 'Formulario fuera del alcance inicial',
                                  'tables':[],'raw_rows':[],'observations':[],'context':[],'contract_context':[],'warnings':[]})
            else:
                parsed=parse_document(data,cuce,form,rel,key);parsed['status']='PARSED';documents.append(parsed)
        modality=manifest.get('metadata',{}).get('modalidad')
        expected={'110','220','500'} if modality=='CM' else {'100','170','200','500'}
        process_info.append({'cuce':cuce,'modality':modality,'forms_in_manifest':forms,'missing_expected_forms':sorted(expected-set(forms)),
                             'note':'Ausencia en manifiesto no demuestra ausencia de publicación en SICOES.'})
    return documents,checks,process_info


def assert_sources_unchanged(checks):
    for path,digest in checks.items():
        if sha(Path(path).read_bytes())!=digest:raise ValueError('Cambió un archivo fuente durante el procesamiento: '+path)


def write_database(output,docs,metadata):
    path=output/'observaciones.sqlite';temp=output/('.observaciones.'+uuid.uuid4().hex+'.sqlite')
    db=sqlite3.connect(temp)
    try:
        db.executescript((PACKAGE/'schema.sql').read_text())
        with db:
            for d in docs:
                db.execute('INSERT INTO documentos VALUES (?,?,?,?,?,?,?,?,?,?)',(d['document_id'],d['cuce'],d['form'],d['source_path'],d['source_sha256'],d['document_key'],d['status'],d.get('exclusion_reason'),dumps(d['context']),dumps(d['warnings'])))
                for t in d['tables']:db.execute('INSERT INTO tablas VALUES (?,?,?,?,?)',(d['document_id'],t['table_position'],t['section'],t['classification'],dumps(t)))
                for r in d['raw_rows']:db.execute('INSERT INTO filas_originales VALUES (?,?,?,?,?,?)',(d['document_id'],r['table_position'],r['row_position'],r['classification'],dumps(r['cells']),r['raw_html']))
                for o in d['observations']:
                    db.execute('INSERT INTO observaciones VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(o['observation_id'],d['document_id'],o['cuce'],o['form'],o['stage'],o['event_status'],o['section'],o['section_id'],o['table_position'],o['row_position'],o['description_raw'],o['description_visible'],o['demand_role'],dumps(o['warnings'])))
                    for f in o['fields']:
                        db.execute('INSERT INTO atributos_originales VALUES (?,?,?,?,?,?,?,?,?)',(o['observation_id'],f['column'],f['header_raw'],f['name'],f['raw'],f['visible'],f['normalized'].get('value'),f['normalized']['status'],dumps(f['normalized'])))
                    for f in o['derived']:db.execute('INSERT INTO atributos_derivados VALUES (?,?,?,?,?)',(o['observation_id'],f['name'],f['value'],f['formula'],dumps(f)))
                for r in d.get('contract_context',[]):db.execute('INSERT INTO contextos_contrato VALUES (?,?,?,?)',(d['document_id'],r['table_position'],r['row_position'],dumps(r['fields'])))
            for key,value in metadata.items():db.execute('INSERT INTO metadatos VALUES (?,?)',(key,dumps(value)))
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Error de integridad en SQLite derivada')
        if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Referencias inconsistentes en SQLite derivada')
        db.close();os.replace(temp,path)
    finally:
        db.close()
        if temp.exists():temp.unlink()


def write_csv(output,docs):
    observations=[o for d in docs for o in d['observations']]
    keys=sorted({f['name'] for o in observations for f in o['fields']})
    columns=['observation_id','cuce','formulario','etapa','estado_evento','document_id','documento_origen','sha256_origen','seccion','tabla','fila','descripcion_original','descripcion_visible','rol_demanda']
    for key in keys:columns.extend([key+'_original',key+'_normalizado'])
    columns+=['precio_unitario_recepcion_derivado','campos_originales_json','atributos_derivados_json','contexto_documento_json','contratos_del_documento_sin_asociar_json','alertas_json']
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
    doc_by_id={d['document_id']:d for d in docs}
    for o in observations:
        doc=doc_by_id[o['document_id']]
        row=dict(zip(columns[:14],[o['observation_id'],o['cuce'],o['form'],o['stage'],o['event_status'],o['document_id'],o['source_path'],o['source_sha256'],o['section'],o['table_position'],o['row_position'],o['description_raw'],o['description_visible'],o['demand_role']]))
        grouped={}
        for f in o['fields']:grouped.setdefault(f['name'],[]).append(f)
        for key,fs in grouped.items():
            row[key+'_original']=fs[0]['raw'] if len(fs)==1 else dumps([f['raw'] for f in fs])
            row[key+'_normalizado']=fs[0]['normalized']['value'] if len(fs)==1 else dumps([f['normalized']['value'] for f in fs])
        row['precio_unitario_recepcion_derivado']=o['derived'][0]['value'] if o['derived'] else ''
        row.update(campos_originales_json=dumps(o['fields']),atributos_derivados_json=dumps(o['derived']),contexto_documento_json=dumps(doc['context']),contratos_del_documento_sin_asociar_json=dumps(doc.get('contract_context',[])),alertas_json=dumps(o['warnings']))
        writer.writerow(row)
    atomic(output/'observaciones.csv',stream.getvalue().encode('utf-8-sig'))


def audit(docs,process_info,review):
    report={'status':'COTEJADO_PILOTO' if review and review['status']=='COTEJO_PILOTO_OK' else 'REVISAR','processes':process_info,'documents':[],
            'observations':sum(len(d['observations']) for d in docs),'by_stage':dict(Counter(o['stage'] for d in docs for o in d['observations'])),
            'reference_review':review,'limitations':['Piloto de desarrollo: no evaluación independiente de precisión.',
              'Sin fusión entre fases ni reconstrucción de demanda neta. No sumar cantidades entre FORM.',
              'FORM 100-E existe y se excluye deliberadamente; no se interpreta ni descuenta.',
              'Número de ítem y número de contrato no son identidad entre formularios.',
              'Tablas ajenas a bienes se conservan como filas/contexto, sin convertirlas en productos.']}
    needs_review=False
    for d in docs:
        tables=d['tables'];obs=d['observations'];goods=[t for t in tables if t['classification']=='goods']
        entry={'cuce':d['cuce'],'form':d['form'],'source_path':d['source_path'],'sha256':d['source_sha256'],'status':d['status'],
               'exclusion_reason':d.get('exclusion_reason'),'raw_rows_detected':len(d['raw_rows']),
               'goods_rows_detected':sum(t['detected_goods_rows'] for t in tables),'observations_extracted':len(obs),
               'difference':sum(t['detected_goods_rows'] for t in tables)-len(obs),'goods_tables':goods,
               'uninterpreted_tables':[t for t in tables if t['classification'] in ('non_goods_uninterpreted','uninterpreted_goods_candidate')],
               'document_context':d['context'],'contract_context':d.get('contract_context',[]),'document_warnings':d['warnings'],
               'observation_warnings':[{'observation_id':o['observation_id'],'warnings':o['warnings']} for o in obs if o['warnings']]}
        report['documents'].append(entry)
        if d['status']!='EXCLUIDO' and (entry['difference'] or not goods or any(t['warnings'] for t in tables) or any(o['warnings'] for o in obs)):
            # Avisos de proveedor ausente no significan extracción incorrecta; se conservan para revisión.
            substantive=[w for o in obs for w in o['warnings'] if not w.startswith('proveedor_no_documentado')]
            needs_review|=bool(entry['difference'] or not goods or any(t['warnings'] for t in tables) or substantive)
    if any(p['missing_expected_forms'] for p in process_info):needs_review=True
    if needs_review or review and review['failures']:report['status']='REQUIERE_REVISION'
    if not review and not needs_review:report['status']='EXTRAIDO_SIN_COTEJO_MANUAL'
    return report


def markdown(report):
    lines=['# Auditoría del procesamiento local', '',f"Estado: **{report['status']}**. Observaciones: **{report['observations']}**.",'',
           '| CUCE | FORM | Filas de bienes detectadas | Extraídas | Diferencia | Estado |','|---|---|---:|---:|---:|---|']
    for d in report['documents']:lines.append(f"| {d['cuce']} | {d['form']} | {d['goods_rows_detected']} | {d['observations_extracted']} | {d['difference']} | {d['status']} |")
    lines+=['','## Interpretación y anomalías','',
            '- FORM 110 conserva precios de proveedor preseleccionado; no se renombran como referenciales.',
            '- FORM 170 distingue adjudicación de declaratoria desierta; ambas son observaciones, no cantidades para sumar.',
            '- Los FORM 200 del piloto no indican proveedor por fila. Los contratos compartidos entre proveedores se conservan aparte, sin asociarlos automáticamente.',
            '- FORM 500 conserva cantidad solicitada, cantidad reportada, estado e importe. Precio unitario calculado solo cuando hay recepción confirmada, cantidad positiva e importe válido.',
            '- FORM 100-E está excluido deliberadamente. No se ha reconstruido demanda neta ni descontado anulaciones.','']
    if report['reference_review']:
        r=report['reference_review'];lines+=[f"Cotejo: {r['status']}; {r['observations_checked']} filas y {r['cells_checked']} celdas cotejadas con un lector HTML independiente; {r['manual_numeric_assertions']} comprobaciones numéricas de la referencia curada. Se ignora únicamente sangría y espaciado de maquetación al cotejar texto; la integridad del original se verifica por SHA256.",'']
    for d in report['documents']:
        lines += [f"## {d['cuce']} — FORM {d['form']}",'',f"Origen: `{d['source_path']}`. SHA256: `{d['sha256']}`.",'']
        if d['status']=='EXCLUIDO':lines += [d['exclusion_reason'],''];continue
        lines += [f"Filas TR directas preservadas: {d['raw_rows_detected']} (incluyen estructura, encabezados y metadatos; no equivalen a bienes).",'']
        for t in d['goods_tables']:
            lines += [f"- Tabla {t['table_position']}: {t['section']}; {t['detected_goods_rows']} detectadas / {t['extracted_goods_rows']} extraídas. Exclusiones: `{dumps(t['excluded_rows'])}`."]
        lines+=['',f"Tablas ajenas a bienes sin interpretación comercial: {', '.join(str(t['table_position']) for t in d['uninterpreted_tables']) or 'ninguna'}. Filas originales conservadas en SQLite. No se presentan como bienes extraídos.",'']
        for w in d['document_warnings']:lines += ['- '+w]
        for o in d['observation_warnings']:lines += ['- '+o['observation_id']+': '+'; '.join(o['warnings'])]
    lines+=['','## Límites de la evidencia','']+['- '+s for s in report['limitations']]
    return '\n'.join(lines)+'\n'


def run(source,output,cuces=PILOT,manual_review=True):
    source=Path(source).resolve();output=Path(output).resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):raise ValueError('Salida y originales no pueden solaparse')
    docs,checks,processes=load(source,cuces)
    review=check(docs,source,PACKAGE/'piloto_referencia.json') if manual_review else None
    report=audit(docs,processes,review)
    code={p.name:sha(p.read_bytes()) for p in sorted(PACKAGE.glob('*')) if p.suffix in ('.py','.sql','.json')}
    metadata={'parser_version':VERSION,'source_root':str(source),'selected_cuces':list(cuces),'code_sha256':code,
              'input_sha256':checks,'run_id':identity(checks,code),'audit_status':report['status']}
    assert_sources_unchanged(checks);output.mkdir(parents=True,exist_ok=True)
    write_database(output,docs,metadata);write_csv(output,docs)
    atomic(output/'auditoria.json',(dumps(report)+'\n').encode());atomic(output/'AUDITORIA.md',markdown(report).encode())
    atomic(output/'ejecucion.json',(dumps(metadata)+'\n').encode())
    if review:atomic(output/'cotejo_piloto.json',(dumps(review)+'\n').encode())
    assert_sources_unchanged(checks)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=DEFAULT_SOURCE);p.add_argument('--output',type=Path,default=PACKAGE/'data/piloto_0660-10_2024')
    g=p.add_mutually_exclusive_group();g.add_argument('--cuce',action='append');g.add_argument('--all',action='store_true',help='Ampliación explícita; no se ejecuta por defecto')
    args=p.parse_args();cuces=sorted(p.parent.name for p in args.source.glob('*/manifest.json')) if args.all else args.cuce or list(PILOT)
    if not cuces:p.error('No se encontraron CUCE')
    for c in cuces:
        if not re_cuce(c):p.error('CUCE completo inválido: '+c)
    manual=set(cuces)==set(PILOT)
    report=run(args.source,args.output,cuces,manual)
    print(dumps({'status':report['status'],'processes':len(cuces),'observations':report['observations'],'by_stage':report['by_stage'],'output':str(args.output)}))
    raise SystemExit(2 if report['status']=='REQUIERE_REVISION' else 0)


def re_cuce(cuce):
    import re
    return bool(re.fullmatch(r'\d{2}-\d{4}-\d{2}-\d+-\d+-\d+',cuce))
