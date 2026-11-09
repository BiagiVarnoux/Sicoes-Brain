"""Pipeline integral offline: observaciones, DBC, vínculos y representaciones A/B."""
import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import sqlite3
import re
from .parser import norm
from . import pipeline
from .dbc import inventory
from .linking import link
from .technical import attributes,LEGACY
from .parser import identity,sha
from .review import source_fidelity

PACKAGE=Path(__file__).resolve().parent

def jsonl(path,items):pipeline.atomic(path,(''.join(pipeline.dumps(i)+'\n' for i in items)).encode())
def key(a):return (a['name'],pipeline.dumps(a['value']),a.get('unit_normalized',a['unit']),a['operator'],a['role'])

def representations(observations,specs,relations):
    byspec={b['spec_id']:b for b in specs};products=[]
    for o in observations:
        if o['stage']!='requerimiento':continue
        related=[r for r in relations if any(c['observation_id']==o['observation_id'] for c in r['candidates'])]
        confirmed=[r for r in related if r['status']=='CONFIRMADA' and r['observation_id']==o['observation_id']]
        baseline=attributes(o['description_visible'],{'document_id':o['document_id'],'table':o['table_position'],'row':o['row_position']})
        confirmed_specs=[byspec[r['spec_id']] for r in confirmed]
        additions=[dict(a,spec_id=b['spec_id'],origin='DBC') for b in confirmed_specs for a in b['attributes']]
        known={key(a) for a in baseline if a['value'] is not None}
        novel=[dict(a) for a in additions if a['value'] is not None and key(a) not in known]
        compact=lambda s:re.sub(r'[^a-z0-9]','',norm(str(s)))
        form_text=compact(o['description_visible'])
        for a in novel:
            values=a['value'] if isinstance(a['value'],list) else [a['value']]
            literal_present=all(compact(str(v)+(a.get('unit_normalized') or '')) in form_text for v in values)
            a['novelty_kind']='LITERAL_NO_ENCONTRADO_EN_FORM' if not literal_present else 'OPERADOR_DBC_ADICIONAL' if a['operator'] in ('GE','LE','RANGE','EQ','ONE_OF','PROHIBIDO') else 'DIFERENCIA_EXTRACCION_O_FORMATO'
            a['novelty_qualification']='Comparación textual/estructural; no prueba independiente de conocimiento nuevo ni precisión comercial'

        products.append({'observation_id':o['observation_id'],'cuce':o['cuce'],'stage':o['stage'],'form':o['form'],
                         'form_reference':{'path':o['source_path'],'sha256':o['source_sha256'],'table':o['table_position'],'row':o['row_position']},
                         'link_status':'CONFIRMADA' if confirmed else 'AMBIGUA' if any(r['status']=='AMBIGUA' for r in related) else 'SIN_CORRESPONDENCIA',
                         'candidate_spec_ids':sorted({r['spec_id'] for r in related}),
                         'A':{'description':o['description_visible'],'description_original':o['description_raw'],'attributes':baseline},
                         'B':{'description':o['description_visible'],'description_original':o['description_raw'],'specification_ids':[b['spec_id'] for b in confirmed_specs],
                              'specifications_original_text':[b['raw_text'] for b in confirmed_specs],
                              'technical_requirements_text':[[r['text'] for r in b['requirements']] for b in confirmed_specs],
                              'attributes':baseline+additions,'qualification':'Requisitos DBC, no especificaciones verificadas del producto adjudicado/recibido'},
                         'new_attribute_names':sorted({a['name'] for a in novel}),'new_constraints':novel})
    return products


def write_integrated_db(path,structured,inventory_rows,specs,relations,products,sections=None):
    temp=path.with_suffix('.sqlite.tmp')
    if temp.exists():temp.unlink()
    source=sqlite3.connect('file:'+str((structured/'observaciones.sqlite').resolve())+'?mode=ro',uri=True);db=sqlite3.connect(temp)
    try:
        source.backup(db)
        db.executescript('''CREATE TABLE dbc_inventory(cuce TEXT PRIMARY KEY,status TEXT NOT NULL,data_json TEXT NOT NULL);
        CREATE TABLE dbc_sections(dbc_id TEXT PRIMARY KEY,cuce TEXT NOT NULL,markdown_text TEXT,metadata_json TEXT NOT NULL);
        CREATE TABLE dbc_specs(spec_id TEXT PRIMARY KEY,cuce TEXT NOT NULL,dbc_id TEXT NOT NULL,title TEXT NOT NULL,original_text TEXT NOT NULL,data_json TEXT NOT NULL);
        CREATE TABLE technical_attributes(attribute_id TEXT PRIMARY KEY,spec_id TEXT NOT NULL REFERENCES dbc_specs,name TEXT NOT NULL,value_json TEXT NOT NULL,unit TEXT,operator TEXT NOT NULL,evidence TEXT NOT NULL,data_json TEXT NOT NULL);
        CREATE TABLE dbc_links(spec_id TEXT PRIMARY KEY REFERENCES dbc_specs,status TEXT NOT NULL,observation_id TEXT REFERENCES observaciones,data_json TEXT NOT NULL);
        CREATE TABLE canonicalization_inputs(observation_id TEXT PRIMARY KEY REFERENCES observaciones,link_status TEXT NOT NULL,A_json TEXT NOT NULL,B_json TEXT NOT NULL,comparison_json TEXT NOT NULL);''')
        db.execute('PRAGMA foreign_keys=ON')
        with db:
            for row in inventory_rows:db.execute('INSERT INTO dbc_inventory VALUES (?,?,?)',(row['cuce'],row['status'],pipeline.dumps(row)))
            for section in sections or []:
                db.execute('INSERT INTO dbc_sections VALUES (?,?,?,?)',(section['dbc_id'],section['cuce'],(section.get('markdown_section') or {}).get('text'),pipeline.dumps(section)))
            for b in specs:
                db.execute('INSERT INTO dbc_specs VALUES (?,?,?,?,?,?)',(b['spec_id'],b['cuce'],b['dbc_id'],b['title'],b['raw_text'],pipeline.dumps(b)))
                for i,a in enumerate(b['attributes']):db.execute('INSERT INTO technical_attributes VALUES (?,?,?,?,?,?,?,?)',(identity(b['spec_id'],i,a),b['spec_id'],a['name'],pipeline.dumps(a['value']),a['unit'],a['operator'],a['evidence'],pipeline.dumps(a)))
            for r in relations:db.execute('INSERT INTO dbc_links VALUES (?,?,?,?)',(r['spec_id'],r['status'],r['observation_id'],pipeline.dumps(r)))
            for p in products:db.execute('INSERT INTO canonicalization_inputs VALUES (?,?,?,?,?)',(p['observation_id'],p['link_status'],pipeline.dumps(p['A']),pipeline.dumps(p['B']),pipeline.dumps({'new_attribute_names':p['new_attribute_names'],'new_constraints':p['new_constraints']})))
        if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Referencias inválidas en enriquecimiento')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite enriquecida inválida')
        db.close();temp.replace(path)
    finally:source.close();db.close()


def report_markdown(report,inv,specs,relations,products,structured):
    lines=['# Conjunto histórico enriquecido — 0660-10 / 2024','',
           'Ejecución local sobre documentos existentes. No se usa LLM ni se cambia el scraper/canonicalización.','',
           '## Resultados verificables','', '| Medida | Resultado |','|---|---:|']
    for k,v in report.items():
        if isinstance(v,(int,str)):lines.append(f'| {k} | {v} |')
    lines+=['','## Inventario DBC','', '| CUCE | Modalidad | Estado | Ítems DBC |','|---|---|---|---:|']
    for r in inv:lines.append(f"| {r['cuce']} | {r['modality']} | {r['status']} | {sum(d.get('spec_blocks',0) for d in r['documents'])} |")
    lines+=['','## Relaciones documentales','', '| CUCE | Ítem DBC | Título | Estado | Motivo |','|---|---|---|---|---|']
    byspec={b['spec_id']:b for b in specs}
    for r in relations:
        b=byspec[r['spec_id']];reason=r['reason']
        if r['candidates']:
            e=r['candidates'][0]['evidence']
            if e['code_conflict']:reason+='; códigos declarados discrepantes'
            if e['quantity_conflict']:reason+='; cantidades discrepantes'
        lines.append(f"| {b['cuce']} | {b['number']} | {b['title'].replace('|','/')} | {r['status']} | {reason} |")
    lines+=['','## Ejemplos reales de información añadida','']
    examples=sorted([p for p in products if p['new_constraints']],key=lambda p:(not any(a['name']=='ram' for a in p['new_constraints']),-len(p['new_attribute_names'])))[:8]
    for p in examples:
        lines += [f"### {p['cuce']} — {p['A']['description'].strip()}",'',f"Relación documental: {p['link_status']}. Referencia FORM: `{p['form_reference']}`.",'']
        for a in p['new_constraints'][:10]:lines.append(f"- `{a['name']}` {a['operator']} `{a['value']}` {a['unit'] or ''}; evidencia literal: «{a['evidence']}»; tabla/fila/celda DOCX: `{a['reference']}`.")
        lines+=['']
    lines+=['## Errores, ambigüedades y límites','',
            '- Se corrigió una variante numérica real: `.90`, `,54`, `.80`, etc. Se conservó el original; no se corrigieron valores comerciales.',
            '- Todas las fuentes incluyen hashes. El Markdown completo y la sección técnica original se referencian; el DOCX aporta tablas/filas/celdas cuando el Markdown las aplana. No se inventan páginas DOCX.',
            '- Se excluyen ejemplos de evaluación y plantillas posteriores a la sección técnica requerida. Condiciones generales se conservan en la sección, sin asignarlas por defecto a cada producto.',
            '- Los atributos son requisitos publicados, no prueba de prestaciones del producto entregado. Valores mínimos, máximos, rangos, desconocidos y referencias alternativas permanecen distintos.',
            '- CONFIRMADA significa asociación documental bajo reglas conservadoras; no identidad comercial ni validación humana independiente. Se publican todos los candidatos/evidencias para auditar.',
            '- Solo se enriquece B con relaciones CONFIRMADA. Los casos AMBIGUA quedan sin inyección de atributos DBC. Los casos sin DBC conservan la misma base A/B.',
            '- Un operador DECLARADO_SIN_OPERADOR no se interpreta como valor exacto. Un atributo DESCONOCIDO nunca prueba igualdad. Compatibilidad se conserva aparte de identidad.',
            '- Los atributos no cubiertos por reglas permanecen en texto y en unstructured_requirements; no se promete extracción exhaustiva de cada cláusula.',
            '- La novedad separa literal no encontrado, operador adicional y diferencias de extracción/formato. Un atributo estructurado nuevo no prueba información nueva ni mejora de precisión.',
            '- Las reglas y la muestra se desarrollaron con estos datos: no hay medida independiente de precisión, recall de equivalencias o mejora del canonicalizador.',
            '- No se suman cantidades entre etapas, no se reconstruye demanda neta y FORM 100-E permanece excluido.','',
            'La auditoría completa de observaciones está en `observaciones/AUDITORIA.md`; datos de candidatos y procedencia en los JSONL/SQLite.']
    return '\n'.join(lines)+'\n'


def run(source=pipeline.DEFAULT_SOURCE,output=PACKAGE/'data/integral_0660-10_2024'):
    source=Path(source).resolve();output=Path(output).resolve()
    cuces=sorted(p.parent.name for p in source.glob('*/manifest.json'))
    if source.is_relative_to(output) or output.is_relative_to(source):raise ValueError('No solapar originales y salidas')
    structured=output/'observaciones';form_report=pipeline.run(source,structured,cuces,False)
    docs,form_checks,_=pipeline.load(source,cuces);observations=[o for d in docs for o in d['observations']]
    inv,specs,sections,dbc_checks=inventory(source,cuces);relations=link(specs,observations);products=representations(observations,specs,relations)
    fidelity=source_fidelity(docs,source)
    variants=[{'observation_id':o['observation_id'],'cuce':o['cuce'],'form':o['form'],'table':o['table_position'],'row':o['row_position'],'column':f['column'],'raw':f['raw'],'normalized':f['normalized']} for o in observations for f in o['fields'] if re.match(r'^-?[.,]\d',f['visible']) and f['normalized']['status']=='normalized']
    report={'source_cells_fidelity':fidelity['status'],'source_cells_checked':fidelity['cells_checked'],'leading_decimal_fields_normalized':len(variants),'processes':len(cuces),'form_documents_processed':sum(d['status']!='EXCLUIDO' for d in docs),'form_documents_excluded':sum(d['status']=='EXCLUIDO' for d in docs),
            'historical_observations':len(observations),'required_observations_A_B':len(products),'form_audit_status':form_report['status'],
            'form_rows_unextracted':sum(d['difference'] for d in form_report['documents']),
            'dbc_available':sum(bool(i['documents']) for i in inv),'dbc_missing_local':sum(not i['documents'] for i in inv),
            'dbc_unreadable':sum(i['status']=='DBC_ILEGIBLE' for i in inv),'dbc_without_identifiable_specs':sum(i['status']=='DBC_SIN_ESPECIFICACIONES_IDENTIFICABLES' for i in inv),
            'specification_blocks':len(specs),'technical_attributes':sum(len(b['attributes']) for b in specs),'known_attribute_values':sum(a['value'] is not None for b in specs for a in b['attributes']),'unknown_attribute_placeholders':sum(a['value'] is None for b in specs for a in b['attributes']),
            'requirements_without_structured_attribute':sum(len(b['unstructured_requirements']) for b in specs),
            'links_by_status':dict(Counter(r['status'] for r in relations)),'items_by_link_status':dict(Counter(p['link_status'] for p in products)),
            'items_with_new_attributes':sum(bool(p['new_constraints']) for p in products),'items_with_literal_additions':sum(any(a['novelty_kind']=='LITERAL_NO_ENCONTRADO_EN_FORM' for a in p['new_constraints']) for p in products),'novel_constraints_by_kind':dict(Counter(a['novelty_kind'] for p in products for a in p['new_constraints'])),'independent_accuracy_evaluation':'NO_DISPONIBLE'}
    checks={**form_checks,**dbc_checks};pipeline.assert_sources_unchanged(checks)
    pipeline.atomic(output/'cotejo_integral_celdas.json',(pipeline.dumps(fidelity)+'\n').encode())
    jsonl(output/'variantes_extraccion.jsonl',variants)
    jsonl(output/'inventario_dbc.jsonl',inv);jsonl(output/'especificaciones.jsonl',specs);jsonl(output/'secciones_originales.jsonl',sections)
    jsonl(output/'relaciones.jsonl',relations);jsonl(output/'productos_A_B.jsonl',products)
    jsonl(output/'A_descripcion_formulario.jsonl',[{'observation_id':p['observation_id'],'cuce':p['cuce'],**p['A']} for p in products])
    jsonl(output/'B_enriquecido_dbc.jsonl',[{'observation_id':p['observation_id'],'cuce':p['cuce'],'link_status':p['link_status'],**p['B']} for p in products])
    jsonl(output/'atributos_tecnicos.jsonl',[dict(a,spec_id=b['spec_id'],cuce=b['cuce'],dbc_id=b['dbc_id']) for b in specs for a in b['attributes']])
    pipeline.atomic(output/'resumen.json',(pipeline.dumps(report)+'\n').encode())
    pipeline.atomic(output/'INFORME.md',report_markdown(report,inv,specs,relations,products,structured).encode())
    sources={'inputs':checks,'rules_reference':{'path':str(LEGACY.relative_to(pipeline.ROOT)),'sha256':sha(LEGACY.read_bytes()),'reused':'_COD_FULL literal AST; sin imports/configuración ni equivalencias de alias'},
             'code_hashes':{p.name:sha(p.read_bytes()) for p in PACKAGE.glob('*') if p.suffix in ('.py','.sql','.json')}}
    pipeline.atomic(output/'procedencia.json',(pipeline.dumps(sources)+'\n').encode())
    write_integrated_db(output/'enriquecido.sqlite',structured,inv,specs,relations,products,sections)
    pipeline.assert_sources_unchanged(checks)
    print(pipeline.dumps(report));return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=pipeline.DEFAULT_SOURCE);p.add_argument('--output',type=Path,default=PACKAGE/'data/integral_0660-10_2024')
    args=p.parse_args();run(args.source,args.output)

if __name__=='__main__':main()
