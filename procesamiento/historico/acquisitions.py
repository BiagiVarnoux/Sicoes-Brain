"""Fichas auditables offline sobre FORM 500 + 200/220 + DBC; CLI independiente."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import re
import json
import sqlite3
from decimal import Decimal
from . import pipeline, dbc, linking, technical
from .parser import parse_document, unique_field, identity, sha, norm
from .review import source_fidelity
from .form220_context import context_field

VERSION = 'adquisiciones-1'
RECEIPT_STATUSES = ('CONFIRMADA', 'AMBIGUA', 'DESCARTADA')
RECEIPT_BASELINES = ('adquisiciones_v1_20261109_04', 'adquisiciones_v2_20261109_01')
CORPORA = [(e, y) for e, years in [('0660-10', range(2022, 2025)),
                                  ('0660-11', range(2023, 2027))] for y in years]


def field(o, name):
    f = unique_field(o['fields'], name)
    if not f:
        return None
    return dict(f, reference=reference(o), value=f['normalized'].get('value'))


def reference(o):
    return {k: o.get(k) for k in ('document_id', 'source_root', 'source_path', 'source_sha256',
                             'table_position', 'row_position', 'section')}


def value(o, name):
    f = field(o, name)
    return f['value'] if f else None


def match_receipt(r, c):
    if r['cuce'] != c['cuce']:
        return None
    description = norm(r['description_visible']) == norm(c['description_visible'])
    contract_r = value(r, 'nro_contrato_documentado')
    contract_c = value(c, 'nro_contrato_documentado')
    contract = bool(contract_r and contract_c and norm(contract_r) == norm(contract_c))
    if not description and not contract:
        return None
    ur, uc = value(r, 'unidad_medida'), value(c, 'unidad_medida')
    # Unknown units must agree literally when both exist; no speculative conversion.
    unit_conflict = bool(ur and uc and (linking.unit_key(ur) or norm(ur)) != (linking.unit_key(uc) or norm(uc)))
    pr, pc = value(r, 'proveedor_documentado'), value(c, 'proveedor_documentado')
    supplier_conflict = bool(pr and pc and norm(pr) != norm(pc))
    qr = value(r, 'cantidad_solicitada')
    qc = value(c, 'cantidad_contratada') or value(c, 'cantidad')
    quantity_equal = qr is not None and qc is not None and Decimal(qr) == Decimal(qc)
    quantity_conflict = qr is not None and qc is not None and not quantity_equal
    supported = description and contract and not (unit_conflict or supplier_conflict or quantity_conflict)
    supported = supported and (bool(ur and uc) or quantity_equal)
    return {'left_id': r['observation_id'], 'right_id': c['observation_id'],
            'kind': 'RECEPCION_CONTRATACION', 'supported': supported,
            'evidence': {'description_equal': description, 'contract_equal': contract,
                         'unit_conflict': unit_conflict, 'supplier_conflict': supplier_conflict,
                         'requested_quantity_equal': quantity_equal, 'quantity_conflict': quantity_conflict,
                         'receipt_unit_missing': not bool(ur)}}


def resolve(edges):
    """Never select a winner from ties or contradictory alternatives."""
    left = Counter(e['left_id'] for e in edges)
    right = Counter(e['right_id'] for e in edges)
    for e in edges:
        e['status'] = 'CONFIRMADA' if e['supported'] and left[e['left_id']] == right[e['right_id']] == 1 else 'AMBIGUA'
    return edges


def supplier_context(observation, document):
    """Context is derived evidence; never insert a supplier into original fields."""
    by_supplier = observation['form'] == '220'
    key = value(observation, 'proveedor_documentado' if by_supplier else 'nro_contrato_documentado')
    header = 'Nombre o razón social' if by_supplier else 'Nro. Documento'
    matches = []
    for row in document.get('contract_context', []):
        match = context_field(row, header)
        if not key or not match or norm(match['raw']) != norm(key):
            continue
        supplier = context_field(row, 'Nombre o razón social')
        contract = context_field(row, 'Nro. Documento')
        signature_date = context_field(row, 'Fecha Firma')
        matches.append({'table': row['table_position'], 'row': row['row_position'],
                        'fields': row['fields'], 'reference': dict(
                            reference(observation), table_position=row['table_position'],
                            row_position=row['row_position']),
                        'supplier': supplier['raw'] if supplier else None,
                        'contract': contract['raw'] if contract else None,
                        'signature_date': signature_date['raw'] if signature_date else None})
    return {'status': 'UNICO' if len(matches) == 1 else 'AMBIGUO' if matches else 'NO_DOCUMENTADO',
            'matched_on': header, 'matches': matches}


def item_number(o):
    item = value(o, 'nro_item_documento')
    return int(item) if item is not None and re.fullmatch(r'[0-9]+', str(item)) else None


def match_receipt_v2(r, c, document):
    if (r['cuce'] != c['cuce'] or (r['form'], r['stage']) != ('500', 'recepcion')
            or c['form'] not in ('200', '220') or c['stage'] != 'contratacion'):
        return None
    dr, dc = norm(r['description_visible']), norm(c['description_visible'])
    description_equal = bool(dr and dr == dc)
    cr, cc = (value(o, 'nro_contrato_documentado') for o in (r, c))
    literal_contract_equal = bool(cr and cc and norm(cr) == norm(cc))
    # Keep historical same-contract alternatives for review.
    if not (description_equal or literal_contract_equal):
        return None

    context = supplier_context(c, document)
    derived = context['matches'][0] if context['status'] == 'UNICO' else {}
    pr = value(r, 'proveedor_documentado')
    pc = value(c, 'proveedor_documentado') if c['form'] == '220' else derived.get('supplier')
    effective_contract = derived.get('contract') if c['form'] == '220' else cc
    date_r = value(r, 'fecha_firma_contrato')
    date_c = derived.get('signature_date')
    ir, ic = item_number(r), item_number(c)
    ur, uc = (value(o, 'unidad_medida') for o in (r, c))
    qr = value(r, 'cantidad_solicitada')
    qc = value(c, 'cantidad_contratada')
    if qc is None:
        qc = value(c, 'cantidad')
    quantity_equal = Decimal(qr) == Decimal(qc) if qr is not None and qc is not None else None
    evidence = {'cuce': r['cuce'], 'receipt_item': ir, 'contract_item': ic,
                'item_equal': ir is not None and ir == ic,
                'match_key': 'descripcion' if description_equal else None,
                'description_equal': description_equal,
                'contract_equal': bool(cr and effective_contract and norm(cr) == norm(effective_contract)),
                'receipt_contract': cr, 'contracting_contract_literal': cc,
                'contracting_contract_effective': effective_contract,
                'receipt_supplier': pr, 'contracting_supplier': pc,
                'supplier_conflict': bool(pr and pc and norm(pr) != norm(pc)),
                'signature_date_conflict': bool(date_r and date_c and norm(date_r) != norm(date_c)),
                'receipt_signature_date': date_r, 'contracting_signature_date': date_c,
                'unit_conflict': bool(ur and uc and (linking.unit_key(ur) or norm(ur)) != (linking.unit_key(uc) or norm(uc))),
                'receipt_unit_missing': not bool(ur), 'requested_quantity_equal': quantity_equal,
                'receipt_requested_quantity': qr, 'contracted_quantity': qc,
                'contract_supplier_context': context}
    reasons = [key for key in ('supplier_conflict', 'signature_date_conflict') if evidence[key]]
    if not description_equal:
        reasons.append('description_not_exact')
    return {'left_id': r['observation_id'], 'right_id': c['observation_id'],
            'kind': 'RECEPCION_CONTRATACION',
            'supported': not reasons and context['status'] != 'AMBIGUO',
            'evidence': evidence, 'rejection_reasons': reasons,
            'association_rules_version': 'v2'}


def resolve_receipts(edges):
    """Resolve eligible description matches and retain abstentions and rejections."""
    resolve([e for e in edges if e['supported']])
    for e in edges:
        reasons = e['rejection_reasons']
        if reasons:
            e['status'] = 'DESCARTADA'
        elif not e['supported']:
            e['status'] = 'AMBIGUA'
            e['dominant_ambiguity_reason'] = 'contract_context_ambiguo'
        elif e['status'] == 'AMBIGUA':
            e['dominant_ambiguity_reason'] = 'descripcion_no_uno_a_uno'
    return edges


def receipt_edges_v2(receipts, contracts, documents):
    contracts_by_cuce = defaultdict(list)
    for c in contracts:
        contracts_by_cuce[c['cuce']].append(c)
    return resolve_receipts([
        edge for r in receipts for c in contracts_by_cuce[r['cuce']]
        if (edge := match_receipt_v2(r, c, documents[c['document_id']]))
    ])


def commercial(o):
    names = ('proveedor_documentado', 'cantidad_contratada', 'cantidad', 'cantidad_solicitada',
             'cantidad_reportada_recepcion', 'unidad_medida', 'precio_unitario_contratado',
             'importe_total_contratado', 'monto_real_ejecutado', 'estado_recepcion',
             'nro_item_documento', 'nro_contrato_documentado', 'codigo_catalogo', 'marca_documentada')
    data = {n: field(o, n) for n in names}
    data.update({f['name']: field(o, f['name']) for f in o['fields'] if f['name'].startswith('fecha_')})
    received = norm(value(o, 'estado_recepcion') or '') in ('recibido', 'recibida', 'recepcionado', 'recepcionada')
    data['cantidad_recibida'] = field(o, 'cantidad_reportada_recepcion') if received else None
    data['importe_recibido'] = field(o, 'monto_real_ejecutado') if received else None
    data['precio_unitario_recepcion_derivado'] = [dict(d, reference=reference(o)) for d in o['derived']] if received else []
    return data


def make_cards(observations, specs, edges, docs, metadata, availability, sections):
    byid = {o['observation_id']: o for o in observations}
    groups = []; used = set()
    for e in edges:
        if e['kind'] == 'RECEPCION_CONTRATACION' and e['status'] == 'CONFIRMADA':
            groups.append([byid[e['left_id']], byid[e['right_id']]])
            used.update((e['left_id'], e['right_id']))
    groups.extend([o] for o in observations if o['observation_id'] not in used)
    cards = []
    for group in groups:
        ids = sorted(o['observation_id'] for o in group); cuce = group[0]['cuce']
        related = [e for e in edges if e['left_id'] in ids or e['right_id'] in ids]
        confirmed_ids = {e['right_id'] for e in related if e['kind'] == 'OBSERVACION_DBC' and e['status'] == 'CONFIRMADA'}
        requirements = [s for s in specs if s['spec_id'] in confirmed_ids]
        doc_by_id = {d['document_id']: d for d in docs}
        missing = []
        for name, present in availability[cuce].items():
            if not present: missing.append(name)
        cards.append({'schema_version': VERSION, 'ficha_id': identity(VERSION, ids),
                      'cuce': cuce, **metadata[cuce], 'observation_ids': ids,
                      'commercial_status': 'NO_CONTRATADO' if all(o['stage'] == 'no_contratacion' for o in group) else 'RECEPCION_REPORTADA' if any(o['stage'] == 'recepcion' for o in group) else 'CONTRATADO_SIN_RECEPCION_VINCULADA',
                      'observations': [{'observation_id': o['observation_id'], 'form': o['form'],
                          'stage': o['stage'], 'description_original': o['description_raw'],
                          'reference': reference(o), 'commercial': commercial(o),
                          'attributes_declared': [dict(a, role='mencion_documentada_no_verificada')
                              for a in technical.attributes(o['description_visible'], reference(o))],
                          'warnings': o['warnings'],
                          'document_context': doc_by_id[o['document_id']]['context'],
                          'contract_context_unassigned': doc_by_id[o['document_id']]['contract_context']}
                          for o in group],
                      'associations': related,
                      'association_status': 'CONFIRMADA' if len(group) == 2 else 'AMBIGUA' if any(e['kind'] == 'RECEPCION_CONTRATACION' and e['status'] == 'AMBIGUA' for e in related) else 'SIN_VINCULAR',
                      'technical_requirements': requirements,
                      'dbc_status': 'CONFIRMADA' if requirements else 'AMBIGUA' if any(e['kind'] == 'OBSERVACION_DBC' for e in related) else 'SIN_VINCULAR',
                      'dbc_sections_available': [s['dbc_id'] for s in sections if s['cuce'] == cuce],
                      'missing_local_sources': missing,
                      'missing_commercial_fields': {o['observation_id']: [n for n, f in commercial(o).items() if f is None] for o in group},
                      'qualification': 'Requisitos DBC no verificados en recepción; etapas no aditivas; sin demanda neta ni identidad canónica'})
    return sorted(cards, key=lambda c: c['ficha_id'])


def run(output, base=pipeline.ROOT/'scraper/historico_local/data', association_rules='v2'):
    if association_rules not in ('v1', 'v2'): raise ValueError('Reglas desconocidas')
    output = Path(output).resolve(); base = Path(base).resolve()
    if output.exists() or output.is_relative_to(base) or base.is_relative_to(output):
        raise ValueError('Salida debe ser nueva y no solapar originales')
    docs = []; checks = {}; inventories = []; specs = []; sections = []; metadata = {}; availability = {}; coverage = []
    for entity, year in CORPORA:
        source = base/f'historico_http_paginas_{entity}_{year}'
        manifests = sorted(source.glob('*/manifest.json'))
        if not manifests: raise ValueError(f'Corpus local ausente: {source}')
        for mp in manifests:
            raw = mp.read_bytes(); checks[str(mp.resolve())] = sha(raw); m = json.loads(raw); cuce = m['cuce']
            metadata[cuce] = {'entity': entity, 'year': year, 'entity_name': m.get('metadata', {}).get('entidad'),
                              'process_metadata': m.get('metadata', {}), 'manifest_path': str(mp.relative_to(pipeline.ROOT))}
            availability[cuce] = {'FORM_500': False, 'FORM_200_220': False, 'DBC': False}
            for key, d in sorted(m['documents'].items()):
                form = d['label'].upper().replace('FORM', '').replace(' ', '')
                if d['kind'] != 'DBC' and (d['kind'] != 'FORM' or form not in ('500', '200', '220')): continue
                tag = 'DBC' if d['kind'] == 'DBC' else form
                row = {'entity': entity, 'year': year, 'cuce': cuce, 'document_key': key, 'type': tag,
                       'status': 'SIN_VERSION_VALIDA', 'observations': 0, 'detected_rows': 0}
                inventories.append(row)
                v = next((v for v in reversed(d['versions']) if v.get('valid')), None)
                if v is None: continue
                path = (mp.parent/v['path']).resolve()
                if not path.is_relative_to(mp.parent.resolve()): raise ValueError('Ruta fuera de CUCE')
                if not path.is_file(): row['status'] = 'ARCHIVO_AUSENTE'; continue
                data = path.read_bytes(); checks[str(path)] = sha(data)
                if sha(data) != v['sha256'] or len(data) != v['bytes']: raise ValueError(f'Integridad inválida: {path}')
                row.update(status='INTEGRIDAD_OK', source_path=str(path.relative_to(pipeline.ROOT)), source_sha256=sha(data))
                availability[cuce]['DBC' if tag == 'DBC' else 'FORM_500' if tag == '500' else 'FORM_200_220'] = True
                if tag == 'DBC': continue
                doc = parse_document(data, cuce, form, str(path.relative_to(source)), key); doc['status'] = 'PARSED'
                doc['source_root'] = str(source.relative_to(pipeline.ROOT))
                for o in doc['observations']: o['source_root'] = doc['source_root']
                docs.append(doc)
                row.update(observations=len(doc['observations']), detected_rows=sum(t['detected_goods_rows'] for t in doc['tables']),
                           tables=doc['tables'], warnings=doc['warnings'])
            # Existing DBC inventory validates originals and retains uninterpreted sections.
            inv, bs, ss, cs = dbc.inventory(source, [cuce]); checks.update(cs)
            for b in bs:
                b['original_path'] = str((source/b['original_path']).relative_to(pipeline.ROOT))
                b['markdown_path'] = str((source/b['markdown_path']).relative_to(pipeline.ROOT))
            specs.extend(bs); sections.extend(ss)
            coverage.append({'cuce': cuce, 'entity': entity, 'year': year, **availability[cuce],
                             'dbc_inventory': inv[0], 'manifest_status': m.get('status')})
    observations = [o for d in docs for o in d['observations']]
    # Cotejo independiente de todas las celdas extraídas, fuente con rutas desde ROOT.
    fidelity_docs = [dict(d, source_path=str(Path(d['source_root'])/d['source_path'])) for d in docs]
    fidelity = source_fidelity(fidelity_docs, pipeline.ROOT)
    if fidelity['failures']: raise ValueError('Fallo de fidelidad contra HTML original')
    receipts = [o for o in observations if o['stage'] == 'recepcion']
    contracts = [o for o in observations if o['stage'] == 'contratacion']
    if association_rules == 'v1':
        edges = resolve([e for r in receipts for c in contracts if (e := match_receipt(r, c))])
    else:
        bydoc = {d['document_id']: d for d in docs}
        edges = receipt_edges_v2(receipts, contracts, bydoc)
    dbc_edges = []
    for o in observations:
        if o['stage'] not in ('contratacion', 'recepcion'): continue
        for s in specs:
            c = linking.candidate(s, o)
            if c is None or c['score'] < .25: continue
            # The existing candidate uses cantidad; receipts intentionally abstain without that evidence.
            uf = value(o, 'unidad_medida'); us = s.get('unit')
            unknown_unit_conflict = bool(uf and us and (linking.unit_key(uf) or norm(uf)) != (linking.unit_key(us) or norm(us)))
            c['confirmation_supported'] = c['confirmation_supported'] and not unknown_unit_conflict
            c['evidence']['strict_unit_conflict'] = unknown_unit_conflict
            dbc_edges.append({'left_id': o['observation_id'], 'right_id': s['spec_id'], 'kind': 'OBSERVACION_DBC',
                              'supported': c['confirmation_supported'], 'evidence': c})
    # Multiple stages may independently support one DBC block; uniqueness is per stage.
    for stage in ('contratacion', 'recepcion'):
        ids = {o['observation_id'] for o in observations if o['stage'] == stage}
        edges.extend(resolve([e for e in dbc_edges if e['left_id'] in ids]))
    cards = make_cards(observations, specs, edges, docs, metadata, availability, sections)
    summary = []
    for entity, year in CORPORA:
        cov = [r for r in coverage if (r['entity'], r['year']) == (entity, year)]
        cuces = {r['cuce'] for r in cov}; ds = [r for r in inventories if r['cuce'] in cuces]; fs = [f for f in cards if f['cuce'] in cuces]
        summary.append({'entity': entity, 'year': year, 'cuces': len(cov),
                        'documents': dict(Counter(r['type'] for r in ds)),
                        'valid_documents': dict(Counter(r['type'] for r in ds if r['status'] == 'INTEGRIDAD_OK')),
                        'observations_by_form': dict(Counter(o['form'] for o in observations if o['cuce'] in cuces)),
                        'unextracted_rows': sum(r['detected_rows']-r['observations'] for r in ds),
                        'missing_sources_cuces': {k: sum(not r[k] for r in cov) for k in ('FORM_500', 'FORM_200_220', 'DBC')},
                        'cards': len(fs), 'card_associations': dict(Counter(f['association_status'] for f in fs)),
                        'dbc_cards': dict(Counter(f['dbc_status'] for f in fs))})
    report = {'version': VERSION, 'association_rules_version': association_rules, 'coverage': summary, 'cards': len(cards), 'observations': len(observations),
              'edges': dict(Counter(e['kind']+'_'+e['status'] for e in edges)), 'source_fidelity': fidelity,
              'independent_commercial_accuracy': 'NO_MEDIDA', 'demand_additive': False}
    if association_rules == 'v2':
        receipt_edges = [e for e in edges if e['kind'] == 'RECEPCION_CONTRATACION']
        statuses = Counter(e['status'] for e in receipt_edges)
        report['recepcion_contratacion'] = {
            'por_status': {status: statuses[status] for status in RECEIPT_STATUSES},
            'causas_dominantes_ambiguas': dict(Counter(
                e['dominant_ambiguity_reason'] for e in receipt_edges if e['status'] == 'AMBIGUA')),
        }
        comparisons = {}
        for name in RECEIPT_BASELINES:
            baseline = Path(__file__).parent/'data'/name/'resumen.json'
            if baseline.is_file():
                previous = json.loads(baseline.read_text())['edges']
                comparisons[name] = {
                    status: {'antes': previous.get('RECEPCION_CONTRATACION_'+status, 0),
                             'despues': statuses[status]}
                    for status in RECEIPT_STATUSES
                }
        report['recepcion_contratacion']['comparacion_corridas'] = comparisons
    pipeline.assert_sources_unchanged(checks)
    output.mkdir(parents=True, exist_ok=False)
    for name, items in [('fichas', cards), ('observaciones', observations), ('documentos', docs), ('inventario_documental', inventories),
                        ('cobertura_procesos', coverage), ('especificaciones', specs), ('secciones_dbc', sections), ('asociaciones', edges)]:
        pipeline.atomic(output/(name+'.jsonl'), ''.join(pipeline.dumps(i)+'\n' for i in items).encode())
    pipeline.atomic(output/'resumen.json', (pipeline.dumps(report)+'\n').encode())
    provenance = {'version': VERSION, 'association_rules_version': association_rules, 'input_sha256': checks,
                  'code_sha256': {str(p.relative_to(pipeline.ROOT)): sha(p.read_bytes()) for p in sorted(Path(__file__).parent.iterdir()) if p.suffix == '.py' or p.name == 'acquisiciones_referencia_v2.json'}}
    pipeline.atomic(output/'procedencia.json', (pipeline.dumps(provenance)+'\n').encode())
    with sqlite3.connect(output/'fichas.sqlite') as db:
        db.executescript('CREATE TABLE observaciones(id TEXT PRIMARY KEY,cuce TEXT,data_json TEXT); CREATE TABLE fichas(id TEXT PRIMARY KEY,cuce TEXT,estado TEXT,data_json TEXT); CREATE TABLE ficha_observacion(ficha_id TEXT REFERENCES fichas(id),observacion_id TEXT UNIQUE REFERENCES observaciones(id),PRIMARY KEY(ficha_id,observacion_id));')
        db.execute('PRAGMA foreign_keys=ON')
        db.executemany('INSERT INTO observaciones VALUES (?,?,?)', [(o['observation_id'],o['cuce'],pipeline.dumps(o)) for o in observations])
        db.executemany('INSERT INTO fichas VALUES (?,?,?,?)', [(f['ficha_id'],f['cuce'],f['association_status'],pipeline.dumps(f)) for f in cards])
        db.executemany('INSERT INTO ficha_observacion VALUES (?,?)', [(f['ficha_id'],oid) for f in cards for oid in f['observation_ids']])
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('SQLite inválida')
    pipeline.assert_sources_unchanged(checks)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--association-rules', choices=('v1','v2'), default='v2')
    args = p.parse_args()
    report = run(args.output, association_rules=args.association_rules)
    print(pipeline.dumps(report))
    if args.association_rules == 'v2':
        for name, comparison in report['recepcion_contratacion']['comparacion_corridas'].items():
            print(f'RECEPCION_CONTRATACION {name} → {args.output.name}')
            for status, counts in comparison.items():
                print(f"{status} {counts['antes']} → {counts['despues']}")


if __name__ == '__main__': main()
