"""Muestra de auditoría: solo lee salidas congeladas y originales; no ejecuta reglas."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
import sqlite3
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'procesamiento/historico/data'
V1 = BASE/'adquisiciones_v1_20261109_04'
V2 = BASE/'adquisiciones_v2_20261109_01'
EXCLUDED = '25-0660-11-1517374-1-1'
SEED = 'SICOES-BRAIN-auditoria-v2-100-20261109-v1'
QUOTAS = {'NUEVA_CONFIRMADA': 50, 'AMBIGUA': 20, 'DESCARTADA': 20, 'SIN_VINCULO': 10}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    with Path(path).open() as f:
        return [json.loads(line) for line in f]


def norm(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c)).split())


def fvalue(o, *names, normalized=False):
    for name in names:
        fields = [f for f in o['fields'] if f['name'] == name]
        if len(fields) == 1:
            return fields[0]['normalized'].get('value') if normalized else fields[0]['raw']
    return None if normalized else ''


def product_type(o):
    # Labels for audit allocation only, not canonical categories or identities.
    text = norm(o['description_visible'])
    rules = [('CONSUMIBLES_IMPRESION', r'toner|tonner|cartucho|tinta'),
             ('COMPUTACION', r'computador|computacion|laptop|portatil|notebook|memoria|disco duro'),
             ('EQUIPOS_IMPRESION', r'impresora|escaner'),
             ('MOBILIARIO', r'escritorio|silla|estante|mueble|archivador metalico'),
             ('PAPEL_Y_SOPORTES', r'papel|resma|cuaderno|cartulina|hoja'),
             ('UTILES_OFICINA', r'lapiz|lapices|boligrafo|marcador|clip|grapa|folder|carpeta|archivador|pegamento|cinta')]
    return next((label for label, pattern in rules if re.search(pattern, text)), 'OTROS')


def tokens(o):
    stop = set('de del la el las los para por y o en a al un una con bien bienes servicio servicios'.split())
    return set(re.findall('[a-z0-9]+', norm(o['description_visible']))) - stop


def quotas(capacities, total):
    """Disproportionate fixed allocation; small strata first, no dependence on labels."""
    if sum(capacities.values()) < total:
        raise ValueError(f'Población insuficiente: {total} frente a {sum(capacities.values())}')
    order = sorted(capacities, key=lambda k: (capacities[k], k))
    assigned = Counter()
    while sum(assigned.values()) < total:
        for key in order:
            if assigned[key] < capacities[key]:
                assigned[key] += 1
                if sum(assigned.values()) == total:
                    break
    return assigned


def select(pool, count, strata, used, label):
    """Allocate entity/year, then cause, then product; seeded sampling within leaves."""
    available = [p for p in pool if p['key'] not in used]
    def recurse(items, n, depth):
        if depth == len(strata):
            ordered = sorted(items, key=lambda x: x['key'])
            leaf = '|'.join([label] + [str(ordered[0][s]) for s in strata])
            rng = random.Random(int(hashlib.sha256((SEED+'|'+leaf).encode()).hexdigest(), 16))
            return rng.sample(ordered, n)
        groups = defaultdict(list)
        for item in items:
            groups[item[strata[depth]]].append(item)
        alloc = quotas({k: len(v) for k, v in groups.items()}, n)
        return [item for key in sorted(alloc) for item in recurse(groups[key], alloc[key], depth+1)]
    result = recurse(available, count, 0)
    used.update(p['key'] for p in result)
    return result, available


def run(output):
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('La salida debe ser nueva')
    if not output.is_relative_to(BASE.resolve()):
        raise ValueError('Solo escribir dentro de procesamiento/historico/data')
    inputs = [V2/n for n in ('observaciones.jsonl', 'asociaciones.jsonl', 'cobertura_procesos.jsonl',
                              'fichas.sqlite', 'documentos.jsonl', 'validacion_v2.json', 'procedencia.json')]
    inputs += [V1/'asociaciones.jsonl']
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    obs = {o['observation_id']: o for o in read(V2/'observaciones.jsonl')}
    meta = {r['cuce']: r for r in read(V2/'cobertura_procesos.jsonl')}
    old = {(e['left_id'], e['right_id']) for e in read(V1/'asociaciones.jsonl')
           if e['kind'] == 'RECEPCION_CONTRATACION' and e['status'] == 'CONFIRMADA'}
    all_edges = [e for e in read(V2/'asociaciones.jsonl') if e['kind'] == 'RECEPCION_CONTRATACION']
    edges = { (e['left_id'], e['right_id']): e for e in all_edges }
    eligible_counts = Counter(e['left_id'] for e in all_edges if e['status'] != 'DESCARTADA')
    eligible_reverse = Counter(e['right_id'] for e in all_edges if e['status'] != 'DESCARTADA')
    pools = {k: [] for k in QUOTAS}

    def item(r, c, label, cause, edge=None, **extra):
        m = meta[r['cuce']]
        return {'key': (r['observation_id'], c['observation_id']), 'group': label,
                'entity_year': f"{m['entity']}/{m['year']}", 'cause': cause,
                'product': product_type(c), 'edge': edge, **extra}

    for e in all_edges:
        r, c = obs[e['left_id']], obs[e['right_id']]
        if r['cuce'] == EXCLUDED:
            continue
        if e['status'] == 'CONFIRMADA':
            if (e['left_id'], e['right_id']) in old:
                continue
            label = 'NUEVA_CONFIRMADA'; cause = 'EVIDENCIA_CONJUNTA_UNICA'
        elif e['status'] == 'AMBIGUA':
            label = 'AMBIGUA'; reasons = []
            if e['evidence']['contract_supplier_context']['status'] == 'AMBIGUO':
                reasons.append('CONTEXTO_CONTRACTUAL_NO_UNICO')
            if eligible_counts[e['left_id']] > 1: reasons.append('VARIAS_CONTRATACIONES_ELEGIBLES')
            if eligible_reverse[e['right_id']] > 1: reasons.append('VARIAS_RECEPCIONES_ELEGIBLES')
            if not e['supported']: reasons.append('RESPALDO_NO_SUFICIENTE')
            cause = '+'.join(reasons) or 'OTRA_AMBIGUEDAD'
        else:
            label = 'DESCARTADA'; cause = '+'.join(sorted(e['rejection_reasons']))
        pools[label].append(item(r, c, label, cause, e))

    with sqlite3.connect('file:'+str((V2/'fichas.sqlite').resolve())+'?mode=ro', uri=True) as db:
        unlinked = {oid for (raw,) in db.execute("SELECT data_json FROM fichas WHERE estado='SIN_VINCULAR'")
                    for oid in json.loads(raw)['observation_ids']}
    # The unit sampled is an unlinked receipt, with a fixed lexical companion for audit.
    # A companion is not an association; both observations must be unlinked.
    contracts = defaultdict(list)
    for o in obs.values():
        if o['observation_id'] in unlinked and o['stage'] == 'contratacion':
            contracts[o['cuce']].append(o)
    for r in obs.values():
        if r['observation_id'] not in unlinked or r['stage'] != 'recepcion' or r['cuce'] == EXCLUDED:
            continue
        options = []
        for c in contracts[r['cuce']]:
            a, b = tokens(r), tokens(c); common = len(a & b); score = common/max(1, len(a | b))
            if common >= 2 and score >= .25:
                options.append((score, c['observation_id'], common))
        if not options:
            continue
        score, cid, common = sorted(options, key=lambda x: (-x[0], x[1]))[0]
        c = obs[cid]; edge = edges.get((r['observation_id'], cid))
        cause = '+'.join(sorted(edge['rejection_reasons'])) if edge else 'SIN_ARISTA_GENERADA'
        pools['SIN_VINCULO'].append(item(r, c, 'SIN_VINCULO', cause, edge,
                                        comparison_score=score, shared_tokens=common,
                                        companion_count=len(options)))

    chosen = []; used = set(); frames = {}
    # Preserve all three edge audit populations; no duplicated pair in the CSV.
    for label, n in QUOTAS.items():
        picked, frame = select(pools[label], n, ('entity_year', 'cause', 'product'), used, label)
        chosen.extend(picked); frames[label] = frame
    assert len(chosen) == 100 and len(used) == 100

    docs = {}
    wanted = {obs[oid]['document_id'] for p in chosen for oid in p['key']}
    with (V2/'documentos.jsonl').open() as f:
        for line in f:
            d = json.loads(line)
            if d['document_id'] in wanted:
                docs[d['document_id']] = {k: d[k] for k in ('document_id', 'contract_context')}
    rows = []; checked = {}; source_hashes = {}; checked_rows = set()
    # Independent original HTML reader, no call to the acquisition match/resolution rules.
    from procesamiento.historico.review import SourceRows
    for index, p in enumerate(chosen, 1):
        r, c = (obs[oid] for oid in p['key']); e = p['edge']
        assert r['cuce'] == c['cuce'] != EXCLUDED
        row = {'CASO_ID': f'AUD-V2-{index:03d}', 'GRUPO_MUESTRA': p['group'],
               'ENTIDAD': meta[r['cuce']]['entity'], 'GESTION': meta[r['cuce']]['year'],
               'CUCE': r['cuce'], 'TIPO_PRODUCTO_MUESTREO': p['product'], 'CAUSA_ESTRATO': p['cause'],
               'ESTADO_ALGORITMO_PAREJA': e['status'] if e else 'SIN_ARISTA_GENERADA',
               'ESTADO_ANCLA': 'SIN_VINCULAR' if p['group'] == 'SIN_VINCULO' else e['status'],
               'NUEVA_RESPECTO_V1': 'SI' if p['group'] == 'NUEVA_CONFIRMADA' else '',
               'COMPARACION_SOLO_PARA_AUDITORIA': 'SI' if p['group'] == 'SIN_VINCULO' else 'NO',
               'SIMILITUD_LEXICA_AUDITORIA': p.get('comparison_score', ''),
               'COMPARABLES_DISPONIBLES_ANCLA': p.get('companion_count', ''),
               'MOTIVOS_DESCARTE_JSON': json.dumps(e.get('rejection_reasons', []), ensure_ascii=False) if e else '',
               'EVIDENCIA_ALGORITMO_JSON': json.dumps(e['evidence'], ensure_ascii=False, sort_keys=True) if e else ''}
        for prefix, o in (('RECEPCION', r), ('CONTRATACION', c)):
            source = ROOT/o['source_root']/o['source_path']
            source_rel = str(source.relative_to(ROOT))
            if source_rel not in checked:
                assert digest(source) == o['source_sha256']
                reader = SourceRows(); reader.feed(source.read_text())
                checked[source_rel] = reader; source_hashes[source_rel] = digest(source)
            raw = checked[source_rel].rows[o['table_position']][o['row_position']]
            assert [' '.join(v.split()) for v in raw] == [' '.join(f['raw'].split()) for f in o['fields']]
            checked_rows.add((source_rel, o['table_position'], o['row_position']))
            row.update({prefix+'_OBSERVATION_ID': o['observation_id'], prefix+'_FORM': o['form'],
                        prefix+'_DESCRIPCION_ORIGINAL': o['description_raw'],
                        prefix+'_DESCRIPCION_VISIBLE': o['description_visible'],
                        prefix+'_DOCUMENTO': source_rel, prefix+'_SHA256': o['source_sha256'],
                        prefix+'_DOCUMENT_ID': o['document_id'], prefix+'_TABLA': o['table_position'],
                        prefix+'_FILA': o['row_position'], prefix+'_SECCION': o['section'],
                        prefix+'_CAMPOS_ORIGINALES_JSON': json.dumps(o['fields'], ensure_ascii=False, sort_keys=True)})
            for label, names in [('ITEM', ('nro_item_documento',)), ('CONTRATO', ('nro_contrato_documentado',)),
                                 ('PROVEEDOR_EN_FILA', ('proveedor_documentado',)), ('UNIDAD_EN_FILA', ('unidad_medida',)),
                                 ('CANTIDAD_CONTRATADA', ('cantidad_contratada', 'cantidad') if prefix == 'CONTRATACION' else ('cantidad_contratada',)),
                                 ('CANTIDAD_SOLICITADA', ('cantidad_solicitada',)), ('CANTIDAD_REPORTADA_RECEPCION', ('cantidad_reportada_recepcion',)),
                                 ('PRECIO_UNITARIO_EXPLICITO', ('precio_unitario_contratado','precio_unitario_documentado')),
                                 ('IMPORTE_CONTRATADO', ('importe_total_contratado',)), ('MONTO_EJECUTADO_REPORTADO', ('monto_real_ejecutado',)),
                                 ('ESTADO_RECEPCION', ('estado_recepcion',)), ('FECHA_FIRMA', ('fecha_firma_contrato',)),
                                 ('FECHA_RECEPCION_DEFINITIVA', ('fecha_recepcion_definitiva',))]:
                row[prefix+'_'+label+'_ORIGINAL'] = fvalue(o, *names)
                row[prefix+'_'+label+'_NORMALIZADO'] = fvalue(o, *names, normalized=True)
            row[prefix+'_PRECIO_DERIVADO_JSON'] = json.dumps(o['derived'], ensure_ascii=False, sort_keys=True)
        context = docs[c['document_id']]['contract_context']
        row['CONTRATACION_CONTEXTO_CONTRACTUAL_SIN_ASIGNAR_JSON'] = json.dumps(context, ensure_ascii=False, sort_keys=True)
        for ctx in context:
            original = checked[row['CONTRATACION_DOCUMENTO']].rows[ctx['table_position']][ctx['row_position']]
            for field in ctx['fields']:
                assert ' '.join(original[field['column']-1].split()) == ' '.join(field['raw'].split())
        # Empty human judgments: no inferred answer or prefilled human label.
        row.update(REVISION_HUMANA='', ESTADO_CORRECTO='', OBSERVACIONES_REVISION='')
        rows.append(row)

    stratum_rows = []
    for label in QUOTAS:
        counts = Counter((p['entity_year'], p['cause'], p['product']) for p in pools[label])
        frame_counts = Counter((p['entity_year'], p['cause'], p['product']) for p in frames[label])
        sampled = Counter((p['entity_year'], p['cause'], p['product']) for p in chosen if p['group'] == label)
        for key in sorted(counts):
            stratum_rows.append(dict(GRUPO=label, ENTIDAD_GESTION=key[0], CAUSA=key[1], TIPO_PRODUCTO=key[2],
                                     POBLACION=counts[key], MARCO_SIN_DUPLICAR_PAREJAS=frame_counts[key],
                                     MUESTRA=sampled[key]))
    assert Counter(row['GRUPO_MUESTRA'] for row in rows) == QUOTAS
    assert all(row[k] == '' for row in rows for k in ('REVISION_HUMANA','ESTADO_CORRECTO','OBSERVACIONES_REVISION'))
    for p in chosen:
        if p['group'] == 'NUEVA_CONFIRMADA': assert p['key'] not in old and p['edge']['status'] == 'CONFIRMADA'
        if p['group'] == 'SIN_VINCULO': assert set(p['key']) <= unlinked
    for rel, old_hash in {**hashes, **source_hashes}.items(): assert digest(ROOT/rel) == old_hash
    output.mkdir(parents=True, exist_ok=False)
    def csv_write(name, records):
        stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)
        (output/name).write_bytes(stream.getvalue().encode('utf-8-sig'))
    csv_write('muestra_auditoria_100.csv', rows); csv_write('estratos_poblacion_muestra.csv', stratum_rows)
    validation = {'casos': len(rows), 'parejas_unicas': len(used), 'cuces': len({r['CUCE'] for r in rows}),
                  'distribucion': dict(Counter(r['GRUPO_MUESTRA'] for r in rows)),
                  'fuentes_originales_verificadas': len(source_hashes), 'filas_originales_distintas_cotejadas': len(checked_rows),
                  'juicios_humanos_vacios': True, 'cuce_desarrollo_excluido': True,
                  'csv_roundtrip_ok': list(csv.DictReader(io.StringIO((output/'muestra_auditoria_100.csv').read_text(encoding='utf-8-sig')))) == [{k: '' if v is None else str(v) for k,v in row.items()} for row in rows]}
    assert validation['csv_roundtrip_ok']
    metadata = {'seed': SEED, 'quota': QUOTAS, 'excluded_cuce': EXCLUDED,
                'population': {k: len(v) for k,v in pools.items()}, 'available_frame': {k: len(v) for k,v in frames.items()},
                'input_sha256': hashes, 'selected_original_sha256': source_hashes,
                'generator_sha256': digest(__file__), 'selected': [{k:v for k,v in p.items() if k != 'edge'} for p in chosen],
                'validation': validation}
    (output/'seleccion_y_procedencia.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
    lines = ['# Muestra de auditoría de adquisiciones v2: 100 casos', '',
             'Sin modificar reglas, datos originales o producción. No se ejecutó resolución de asociaciones ni extracción documental nueva: se leyeron las salidas congeladas y se cotejaron las celdas seleccionadas con un lector HTML independiente.', '',
             '| Grupo | Población elegible tras excluir desarrollo | Marco sin parejas repetidas | Muestra |', '|---|---:|---:|---:|']
    for label in QUOTAS: lines.append(f'| {label} | {len(pools[label])} | {len(frames[label])} | {QUOTAS[label]} |')
    lines += ['', '## Selección y poblaciones', '',
              'Confirmadas nuevas: diferencia de pares confirmados v2 frente a v1. Las 497 nuevas se reducen a 480 al excluir las 17 nuevas del CUCE de desarrollo; las otras dos asociaciones de ese CUCE ya estaban en v1. No se muestrean las 63 confirmadas previas.',
              'Ambiguas y descartadas: aristas de RECEPCION_CONTRATACION, no vínculos DBC ni fichas. Las ambiguas existentes están únicamente en 0660-10 y su contexto contractual es no único; no se inventan casos de 0660-11.',
              'Sin vínculo: población de recepciones con estado de ficha SIN_VINCULAR y al menos una contratación también sin vínculo en el mismo CUCE. Se exige al menos dos tokens compartidos y Jaccard >= 0,25, con términos vacíos eliminados. Para cada recepción se fija la contratación de mayor Jaccard, desempate por ID. Esto solo aporta contexto al auditor y no cambia el algoritmo. Se publican puntuación y número de comparables. No representa observaciones sin documento comparable ni todos los 840 registros sin vínculo.',
              'Los grupos se seleccionan en orden 50/20/20/10, excluyendo parejas ya elegidas en grupos anteriores. Un ancla SIN_VINCULAR puede tener una pareja DESCARTADA: ESTADO_ANCLA y ESTADO_ALGORITMO_PAREJA se conservan por separado. No se disfraza el descarte como ausencia de arista.',
              'Asignación desproporcionada, primero por entidad/gestión, luego por combinación exacta de causas y después por tipo de producto. Se reparten plazas en rondas iguales hasta completar la cuota, con estratos pequeños primero y límites de disponibilidad. Dentro de cada celda se realiza selección pseudoaleatoria uniforme con semilla fija y orden inicial por IDs. Etiquetas de producto son filtros léxicos de muestreo sobre la descripción de contratación, no una clasificación canónica.',
              f'Semilla: `{SEED}`. El CSV de estratos incluye todas las celdas de población, incluso las no seleccionadas, y sus tamaños antes/después de evitar parejas repetidas. La selección es reproducible con el generador y las mismas entradas; no se entrenó ni evaluó una regla con etiquetas humanas.',
              '', '## Distribución seleccionada por entidad y gestión', '', '| Entidad/gestión | Nuevas | Ambiguas | Descartadas | Sin vínculo |', '|---|---:|---:|---:|---:|']
    for key in sorted({p['entity_year'] for p in chosen}):
        counts = Counter(p['group'] for p in chosen if p['entity_year'] == key)
        lines.append('| '+key+' | '+' | '.join(str(counts[k]) for k in QUOTAS)+' |')
    lines += ['', '## Interpretación y revisión', '',
              'Completar únicamente REVISION_HUMANA, ESTADO_CORRECTO y OBSERVACIONES_REVISION. Mantener el CASO_ID y documentar la evidencia por documento/tabla/fila/columna. ESTADO_CORRECTO debe indicar si la pareja está respaldada, no está respaldada o sigue siendo indeterminada; no confundir asociación documental con equivalencia comercial del producto. La muestra no lleva respuestas humanas prellenadas.',
              'Los datos originales y sus versiones normalizadas van separados. Una unidad o proveedor ausente en la fila permanece vacío. El contexto contractual completo y las referencias del contexto empleado por v2 se conservan en columnas JSON, sin atribuir al bien un proveedor ambiguo. El precio derivado de recepción se identifica como derivado, con fórmula y operandos; no se presenta como precio explícito. Las cantidades reportadas no presuponen recepción confirmada: consultar ESTADO_RECEPCION.',
              'Los formularios de contratación son FORM 200 o FORM 220, indicados por fila. El CSV UTF-8 con BOM usa comas y comillas para preservar saltos de línea de descripciones originales. CAMPOS_ORIGINALES_JSON incluye encabezados, índices de columna, literales y normalización. El contexto contractual usa sus propias tablas/filas. Los paths se resuelven desde la raíz del repositorio.',
              'Es una auditoría diagnóstica estratificada, no 100 compras independientes ni muestra simple del mercado. Puede compartir CUCE u observaciones y sobrerrepresenta estratos pequeños/causas raras. No extrapolar porcentajes sin ponderación, control de dependencia y consideración de estratos no muestreados. La precisión de nuevas confirmadas se calcula sobre sus 50 casos revisados; los otros 50 exploran abstención, descartes y posibles omisiones. No estiman por sí solos recall global ni exactitud de las 497, pues se excluyeron los 17 casos de desarrollo. La exposición previa de otros procesos a regresiones no equivale a validación humana independiente.',
              f'Cotejo: {validation["fuentes_originales_verificadas"]} archivos originales; {validation["filas_originales_distintas_cotejadas"]} filas distintas de bienes con todas sus celdas y contextos cotejados. 100 parejas únicas, 50/20/20/10, CUCE excluido, campos humanos vacíos y lectura CSV verificada. No hay todavía resultados de precisión.',
              '', '## Reproducción', '',
              'Desde la raíz del repositorio, con una ruta de salida nueva:', '', '```bash',
              'scraper/venv/bin/python -m procesamiento.historico.auditorias.generar_muestra_v2_100 --output procesamiento/historico/data/auditoria_v2_100_NUEVA', '```',
              'El generador rechaza salidas existentes. `seleccion_y_procedencia.json` fija IDs, semilla, hashes, tamaños y comprobaciones.']
    (output/'RESUMEN.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'output': str(output), **validation, 'population': metadata['population']}, ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    run(p.parse_args().output)
