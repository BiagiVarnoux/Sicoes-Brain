"""Etapa 1 aislada: bien FORM 220 -> contexto del mismo documento; sin FORM 500."""
import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import re
from bs4 import BeautifulSoup
from . import parser, pipeline
from .review import SourceRows, source_fidelity

VERSION = 'form220-contexto-interno-1'
GOODS_HEADERS = ('Nro.', 'Código Catalogo', 'Partida', 'Descripción', 'Unidad de medida',
                 'Precio Unitario del Proveedor Preseleccionado', 'Proponente Contratado',
                 'Precio unitario Contratado', 'Cantidad Contratado', 'Total Contratado')
CONTRACT_HEADERS = ('Nro.', 'Nombre o razón social', 'Nro. Certificado RUPE', 'Tipo documento',
                    'Nro. Documento', 'Fecha Firma', 'Monto total', 'Responsable de firmar',
                    'Fecha estimada de recepción')


def is220(label):
    return bool(re.search(r'\bform(?:ulario)?\s*220\b', parser.norm(label)))


def erroneous(label, data):
    title = parser.norm(BeautifulSoup(data, 'lxml').get_text(' ', strip=True)[:200])
    return 'erroneo' in parser.norm(label) or bool(re.search(r'\bform\s*220\s+erroneo\b', title))


def schema(data):
    """Find header signatures and spans, independent of table offsets."""
    found = {'goods': [], 'contracts': []}
    for ti, table in enumerate(BeautifulSoup(data, 'lxml').find_all('table'), 1):
        if table.find('table'):
            continue
        for ri, tr in enumerate(parser.direct_rows(table), 1):
            cells = parser.cells(tr); headers = [parser.visible(c) for c in cells]
            for role, expected in (('goods', GOODS_HEADERS), ('contracts', CONTRACT_HEADERS)):
                if Counter(map(parser.norm, headers)) != Counter(map(parser.norm, expected)):
                    continue
                if any(c.get('colspan', '1') != '1' or c.get('rowspan', '1') not in ('1', '2') for c in cells):
                    continue
                found[role].append({'table': ti, 'header_row': ri, 'headers': headers})
    return {'status': 'B01_ADMITIDO' if all(len(v) == 1 for v in found.values()) else 'ESQUEMA_NO_ADMITIDO', **found}


def reference(document, table, row, column=None):
    result = {'document_id': document['document_id'], 'cuce': document['cuce'],
              'source_path': document['source_path'], 'source_root': document.get('source_root'),
              'source_sha256': document['source_sha256'], 'table': table, 'row': row}
    if column is not None:
        result['column'] = column
    return result


def context_field(context, header):
    fields = [f for f in context['fields'] if parser.norm(f['header_raw']) == parser.norm(header)]
    return fields[0] if len(fields) == 1 else None


def reference_kind(text):
    """Classify literal shape only: never split or expand a reference."""
    text = parser.norm(text or '')
    if re.fullmatch(r'\d+(?:\s*[-,;]\s*\d+)+', text):
        return 'COMPUESTA_NO_DESGLOSADA'
    if re.fullmatch(r'(?:(?:no|nro\.?|numero)\s*)?\d+(?:/\d{2,4})?', text):
        return 'LITERAL_SIMPLE'
    return 'NO_INTERPRETADA' if text else 'AUSENTE'


def associate(document, observation, detected_schema):
    """Pure derived result; leaves observations and document fields untouched."""
    o = observation
    base = {'schema_version': VERSION, 'link_id': parser.identity(VERSION, o['observation_id']),
            'observation_id': o['observation_id'], 'document_id': document['document_id'], 'cuce': document['cuce'],
            'item_reference': reference(document, o['table_position'], o['row_position']),
            'item_contract_number_original': None, 'context_status': 'SIN_CONTEXTO',
            'context_id': None, 'context_candidates': [], 'contextual_contract_reference': None,
            'individual_order_status': 'NO_DETERMINADA', 'individual_order_uncertain': True,
            'qualification': 'Solo relación interna FORM 220; no vincula recepción ni confirma identidad de producto'}
    if o['document_id'] != document['document_id'] or o['cuce'] != document['cuce']:
        return dict(base, context_status='NO_ELEGIBLE', reason='OBSERVACION_DE_OTRO_DOCUMENTO_O_CUCE')
    if o['form'] != '220' or o['stage'] != 'contratacion':
        return dict(base, context_status='NO_ELEGIBLE', reason='NO_ES_BIEN_CONTRATADO_FORM220')
    if detected_schema['status'] != 'B01_ADMITIDO':
        return dict(base, context_status='NO_ELEGIBLE', reason='ESQUEMA_NO_ADMITIDO')
    if o['table_position'] != detected_schema['goods'][0]['table']:
        return dict(base, context_status='NO_ELEGIBLE', reason='FUERA_TABLA_BIENES_ADMITIDA')
    # An unexpected original contract column must not be silently replaced with null.
    if any(f['name'] == 'nro_contrato_documentado' for f in o['fields']):
        raise ValueError('Esquema inconsistente: número contractual original inesperado')
    suppliers = [f for f in o['fields'] if f['name'] == 'proveedor_documentado']
    if len(suppliers) != 1 or not suppliers[0]['visible'].strip():
        return dict(base, context_status='AMBIGUA' if len(suppliers) > 1 else 'SIN_CONTEXTO',
                    reason='PROVEEDOR_ORIGINAL_NO_UNICO_O_AUSENTE')
    supplier = suppliers[0]
    candidates = []
    for c in document['contract_context']:
        if c['table_position'] != detected_schema['contracts'][0]['table']:
            continue
        name = context_field(c, 'Nombre o razón social')
        if name and parser.norm(name['raw']) == parser.norm(supplier['visible']):
            fields = [dict(f, reference=reference(document, c['table_position'], c['row_position'], f['column'])) for f in c['fields']]
            candidates.append({'context_id': parser.identity(document['document_id'], 'contract_context', c['table_position'], c['row_position']),
                               'reference': reference(document, c['table_position'], c['row_position']), 'fields': fields})
    base.update(context_candidates=candidates,
                supplier_evidence={'item_cell': dict(supplier, reference=reference(document, o['table_position'], o['row_position'], supplier['column'])),
                                   'comparison': 'IGUALDAD_DE_TEXTO_EXPLICITO_NORMALIZADO_EN_EL_MISMO_DOCUMENTO'})
    if len(candidates) != 1:
        return dict(base, context_status='AMBIGUA' if candidates else 'SIN_CONTEXTO',
                    reason='VARIAS_FILAS_CONTEXTUALES_DEL_PROVEEDOR' if candidates else 'PROVEEDOR_SIN_CONTEXTO_EN_ESTE_DOCUMENTO')
    context = candidates[0]
    number = next(f for f in context['fields'] if parser.norm(f['header_raw']) == 'nro. documento')
    kind = reference_kind(number['raw'])
    base.update(context_status='CONFIRMADA', context_id=context['context_id'], reason='PROVEEDOR_EXPLICITO_Y_CONTEXTO_UNICO_EN_EL_MISMO_DOCUMENTO',
                contextual_contract_reference={'origin': 'DERIVADA_DE_FILA_CONTEXTUAL', 'raw': number['raw'],
                                                'visible': ' '.join(number['raw'].split()), 'kind': kind,
                                                'reference': number['reference']},
                individual_order_status='REFERENCIA_SIMPLE_DOCUMENTADA' if kind == 'LITERAL_SIMPLE' else 'ORDEN_INDIVIDUAL_INDETERMINADA',
                individual_order_uncertain=kind != 'LITERAL_SIMPLE')
    return base


def process_document(data, cuce, source_path, document_key, label='FORM 220', source_root=None):
    if erroneous(label, data):
        return {'status': 'EXCLUIDO_PUBLICADO_ERRONEO', 'schema': None, 'document': None, 'links': []}
    title = BeautifulSoup(data, 'lxml').get_text(' ', strip=True)[:200]
    if not re.search(r'\bFORM\s*220\b', title, re.I):
        raise ValueError('El HTML no identifica FORM 220')
    detected = schema(data)
    document = parser.parse_document(data, cuce, '220', source_path, document_key)
    document['source_root'] = source_root
    for o in document['observations']:
        o['source_root'] = source_root
    links = [associate(document, o, detected) for o in document['observations'] if o['stage'] == 'contratacion']
    return {'status': 'PROCESADO' if detected['status'] == 'B01_ADMITIDO' else 'ESQUEMA_NO_ADMITIDO',
            'schema': detected, 'document': document, 'links': links}


def run(base, output):
    base = Path(base).resolve(); output = Path(output).resolve()
    if output.exists() or output.is_relative_to(base) or base.is_relative_to(output):
        raise ValueError('Salida nueva y sin solapamiento con originales requerida')
    checks = {}; inventory = []; processes = []; documents = []; links = []
    manifests = sorted(base.glob('historico_http_paginas_*/*/manifest.json'))
    if not manifests:
        raise ValueError('No hay manifiestos locales')
    for mp in manifests:
        raw = mp.read_bytes(); checks[str(mp)] = parser.sha(raw); m = json.loads(raw); cuce = m['cuce']
        if mp.parent.name != cuce:
            raise ValueError('CUCE del manifiesto no corresponde a carpeta')
        entries = [(k, d) for k, d in m['documents'].items() if d['kind'] == 'FORM' and is220(d['label'])]
        announced = any(is220(d['label']) and 'erroneo' not in parser.norm(d['label']) for d in m.get('announced', {}).get('forms', []))
        if not entries and not announced:
            continue
        process = {'cuce': cuce, 'entity': cuce[3:10], 'year': 2000+int(cuce[:2]),
                   'manifest_path': str(mp), 'regular_absent': not any('erroneo' not in parser.norm(d['label']) for _, d in entries),
                   'all_form220_absent': not entries, 'documents': []}
        processes.append(process)
        if announced and process['regular_absent']:
            inventory.append({'cuce': cuce, 'label': 'FORM 220 regular anunciado', 'status': 'AUSENTE_EN_MANIFIESTO', 'document_key': None})
        for key, d in entries:
            row = {'cuce': cuce, 'label': d['label'], 'document_key': key, 'status': 'SIN_VERSION_VALIDA'}
            inventory.append(row); process['documents'].append(row)
            v = next((v for v in reversed(d['versions']) if v.get('valid')), None)
            if v is None:
                continue
            path = (mp.parent/v['path']).resolve()
            if not path.is_relative_to(mp.parent.resolve()):
                raise ValueError('Ruta fuera del CUCE')
            if not path.is_file():
                row['status'] = 'ARCHIVO_AUSENTE'; continue
            data = path.read_bytes(); checks[str(path)] = parser.sha(data)
            if checks[str(path)] != v['sha256'] or len(data) != v['bytes']:
                raise ValueError('Integridad de original inválida: '+str(path))
            source = mp.parent.parent
            row.update(source_absolute=str(path), source_sha256=checks[str(path)])
            try:
                result = process_document(data, cuce, str(path.relative_to(source)), key, d['label'], str(source.relative_to(base.parents[2])))
            except ValueError as exc:
                row.update(status='ILEGIBLE_O_INCONSISTENTE', error=str(exc)); continue
            row['status'] = result['status']; row['schema'] = result['schema']
            if result['document']:
                document = result['document']; document['status'] = result['status']; document['source_absolute'] = str(path)
                documents.append(document); links.extend(result['links'])
    # The reused parser retains non-contracted rows, but they never enter links.
    observations = [o for d in documents for o in d['observations']]
    fidelity = source_fidelity([dict(d, source_path=d['source_absolute']) for d in documents], Path('/'))
    if fidelity['failures']:
        raise ValueError('Cotejo independiente de bienes falló')
    contexts_checked = 0; context_cells_checked = 0
    for d in documents:
        reader = SourceRows(); reader.feed(Path(d['source_absolute']).read_text())
        for c in d['contract_context']:
            cells = reader.rows[c['table_position']][c['row_position']]
            for f in c['fields']:
                if ' '.join(cells[f['column']-1].split()) != ' '.join(f['raw'].split()):
                    raise ValueError('Cotejo independiente de contexto falló')
                context_cells_checked += 1
            contexts_checked += 1
    by_year = []
    for entity, year in sorted({(p['entity'], p['year']) for p in processes}):
        cuces = {p['cuce'] for p in processes if (p['entity'], p['year']) == (entity, year)}
        ls = [l for l in links if l['cuce'] in cuces]; ds = [d for d in documents if d['cuce'] in cuces and d['status'] == 'PROCESADO']
        by_year.append({'entity': entity, 'year': year, 'regular_documents': len(ds), 'contracted_goods': len(ls),
                        'confirmed_contexts': sum(l['context_status'] == 'CONFIRMADA' for l in ls),
                        'compound_items': sum((l['contextual_contract_reference'] or {}).get('kind') == 'COMPUESTA_NO_DESGLOSADA' for l in ls),
                        'multi_supplier_documents': sum(len({parser.norm(context_field(c,'Nombre o razón social')['raw']) for c in d['contract_context']}) > 1 for d in ds)})
    report = {'version': VERSION, 'scope': 'ETAPA_1_SOLO_FORM220_INTERNO', 'form500_read_or_linked': False,
              'documents_by_status': dict(Counter(r['status'] for r in inventory)), 'processes': len(processes),
              'regular_absent_processes': sum(p['regular_absent'] for p in processes), 'all220_absent_processes': sum(p['all_form220_absent'] for p in processes),
              'observations_preserved': len(observations), 'observations_by_stage': dict(Counter(o['stage'] for o in observations)),
              'links': len(links), 'context_status': dict(Counter(l['context_status'] for l in links)),
              'contract_reference_kind': dict(Counter((l['contextual_contract_reference'] or {}).get('kind','SIN_REFERENCIA') for l in links)),
              'individual_order_uncertain_items': sum(l['individual_order_uncertain'] for l in links),
              'contract_context_rows': contexts_checked, 'context_cells_checked': context_cells_checked, 'source_fidelity': fidelity, 'by_entity_year': by_year}
    pipeline.assert_sources_unchanged(checks)
    output.mkdir(parents=True, exist_ok=False)
    for name, items in [('inventario', inventory), ('procesos', processes), ('documentos', documents),
                        ('observaciones', observations), ('asociaciones_internas', links)]:
        pipeline.atomic(output/(name+'.jsonl'), ''.join(pipeline.dumps(x)+'\n' for x in items).encode())
    pipeline.atomic(output/'resumen.json', (pipeline.dumps(report)+'\n').encode())
    provenance = {'version': VERSION, 'input_sha256': checks,
                  'code_sha256': {str(p): parser.sha(p.read_bytes()) for p in [Path(__file__), Path(parser.__file__), Path(pipeline.__file__), Path(__file__).with_name('review.py')]}}
    pipeline.atomic(output/'procedencia.json', (pipeline.dumps(provenance)+'\n').encode())
    stream = io.StringIO(newline=''); fields = ['observation_id','cuce','context_status','item_contract_number_original','individual_order_status','individual_order_uncertain','item_reference','contextual_contract_reference','context_candidates']
    writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
    for l in links:
        writer.writerow({k: pipeline.dumps(l[k]) if isinstance(l[k],(dict,list)) else l[k] for k in fields})
    pipeline.atomic(output/'asociaciones_internas.csv', stream.getvalue().encode('utf-8-sig'))
    pipeline.assert_sources_unchanged(checks)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=pipeline.ROOT/'scraper/historico_local/data')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); print(pipeline.dumps(run(args.base, args.output)))


if __name__ == '__main__': main()
