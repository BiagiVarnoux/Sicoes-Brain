"""Acta de diagnóstico de casos revisados; no altera ni ejecuta reglas de asociación."""
import argparse
from collections import Counter, defaultdict
import csv
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import unicodedata
from procesamiento.historico.review import SourceRows

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT/'procesamiento/historico/data'
REVIEW = Path('/Users/fabriziocuellar/Downloads/muestra_auditoria_100_revisada.csv')
REPORT = Path('/Users/fabriziocuellar/Downloads/informe_auditoria_adquisiciones_v2.md')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(t): return ' '.join(''.join(c for c in unicodedata.normalize('NFKD',t.lower()) if not unicodedata.combining(c)).split())
def number(t):
    # Only the exact decimal literals encountered in these documented cases.
    return Decimal(''.join(t.split()).replace(',','.'))


def run(output):
    output = Path(output).resolve()
    if output.exists() or not output.is_relative_to(BASE.resolve()): raise ValueError('Salida nueva dentro de data requerida')
    frozen = [p for folder in BASE.iterdir() if folder.is_dir() and
              (folder.name.startswith(('adquisiciones_v1_', 'adquisiciones_v2_', 'auditoria_v2_100_')))
              for p in folder.rglob('*') if p.is_file()]
    hashes = {str(p):sha(p) for p in frozen+[REVIEW,REPORT]}
    provenance = json.loads((BASE/'adquisiciones_v2_20261109_01/procedencia.json').read_text())
    for path,digest in provenance['code_sha256'].items(): assert sha(ROOT/path)==digest
    hashes.update({str(ROOT/path):digest for path,digest in provenance['code_sha256'].items()})
    rows=list(csv.DictReader(REVIEW.open(encoding='utf-8-sig',newline='')))
    original={r['CASO_ID']:r for r in csv.DictReader((BASE/'auditoria_v2_100_20261109_01/muestra_auditoria_100.csv').open(encoding='utf-8-sig',newline=''))}
    human={'REVISION_HUMANA','ESTADO_CORRECTO','OBSERVACIONES_REVISION'}
    assert len(rows)==100 and len({r['CASO_ID'] for r in rows})==100
    for r in rows:
        assert {k:v for k,v in r.items() if k not in human}=={k:v for k,v in original[r['CASO_ID']].items() if k not in human}
    assert Counter(r['ESTADO_CORRECTO'] for r in rows)=={'RESPALDADA':50,'NO_RESPALDADA':12,'INDETERMINADA':38}
    selected=[r for r in rows if r['GRUPO_MUESTRA']!='NUEVA_CONFIRMADA']
    sources={};supplement={};manifests={}
    def source(path,expected=None):
        path=Path(path).resolve()
        if path not in sources:
            digest=sha(path)
            if expected: assert digest==expected
            reader=SourceRows();reader.feed(path.read_text())
            sources[path]={'path':str(path.relative_to(ROOT)),'sha256':digest,'reader':reader}
            hashes[str(path)]=digest
        if expected: assert sources[path]['sha256']==expected
        return sources[path]
    def ref(s,table,row):return {'document':s['path'],'sha256':s['sha256'],'table':table,'row':row,'cells':s['reader'].rows[table][row]}
    def goods(s,table):return [(ri,cs) for ri,cs in s['reader'].rows[table].items() if cs and cs[0].strip().isdigit() and len(cs)>=10]
    def contexts(s,table):return [ref(s,table,ri) for ri,cs in s['reader'].rows[table].items() if len(cs)==9 and cs[0].strip().isdigit()]
    def receipt(cs):
        new=len(cs)==13
        return {'contract':cs[1],'date':cs[2],'supplier':cs[3],'description':cs[5] if new else cs[4],
                'requested':cs[6],'received':cs[7],'amount':cs[9] if new else cs[11],
                'deadline':cs[4] if new else cs[8],'state':None if new else cs[5],
                'explicit_unit_price':cs[8] if new else None}
    def contract(cs,form):
        return {'description':cs[3],'quantity':cs[8],'amount':cs[9], 'unit_price':cs[7] if form=='220' else cs[6],
                'unit':cs[4] if form=='220' else cs[5],'supplier':cs[6] if form=='220' else None,
                'contract':None if form=='220' else cs[4]}
    def supplemental(cuce,label):
        key=(cuce,label)
        if key not in supplement:
            folder=ROOT/'scraper/historico_local/data'/f'historico_http_paginas_{cuce[3:10]}_20{cuce[:2]}'/cuce
            mp=folder/'manifest.json';hashes[str(mp)]=sha(mp);m=json.loads(mp.read_text());manifests[cuce]=m
            candidates=[(d,v) for d in m['documents'].values() if d['label']==label
                        for v in [next((v for v in reversed(d['versions']) if v.get('valid')),None)] if v]
            assert len(candidates)==1,(cuce,label)
            d,v=candidates[0];p=folder/v['path'];assert p.stat().st_size==v['bytes']
            supplement[key]=source(p,v['sha256'])
        return supplement[key]
    evidence=[];ledger=[];balances={}
    for r in selected:
        csrc=source(ROOT/r['CONTRATACION_DOCUMENTO'],r['CONTRATACION_SHA256'])
        rsrc=source(ROOT/r['RECEPCION_DOCUMENTO'],r['RECEPCION_SHA256'])
        ct,cr,rt,rr=map(int,[r['CONTRATACION_TABLA'],r['CONTRATACION_FILA'],r['RECEPCION_TABLA'],r['RECEPCION_FILA']])
        cref,rref=ref(csrc,ct,cr),ref(rsrc,rt,rr)
        c=contract(cref['cells'],r['CONTRATACION_FORM']);a=receipt(rref['cells'])
        assert norm(c['description'])==norm(r['CONTRATACION_DESCRIPCION_ORIGINAL'])
        assert norm(a['description'])==norm(r['RECEPCION_DESCRIPCION_ORIGINAL'])
        case={'case_id':r['CASO_ID'],'cuce':r['CUCE'],'original_group':r['GRUPO_MUESTRA'],
              'review_label_unchanged':r['ESTADO_CORRECTO'],'contract_item':cref,'receipt_item':rref,
              'contract_literal':c,'receipt_literal':a,'context_rows':contexts(csrc,ct-1)}
        matches_c=[(ri,cs) for ri,cs in goods(csrc,ct)
                   if norm(cs[3])==norm(a['description']) and number(cs[8])==number(a['requested']) and number(cs[9])==number(a['amount'])]
        matches_r=[(ri,cs) for ri,cs in goods(rsrc,rt)
                   if norm(receipt(cs)['description'])==norm(c['description']) and number(receipt(cs)['requested'])==number(c['quantity']) and number(receipt(cs)['amount'])==number(c['amount'])]
        case['matching_rows_in_full_tables']={'contract':[i for i,_ in matches_c],'receipt':[i for i,_ in matches_r]}
        if r['ESTADO_CORRECTO']=='NO_RESPALDADA':
            assert norm(c['description'])!=norm(a['description'])
            conclusion='MANTENER_DESCARTE';cause='DESCRIPCIONES_INCOMPATIBLES'
        else:
            assert matches_c==[(cr,cref['cells'])] and matches_r==[(rr,rref['cells'])]
            assert number(c['quantity'])==number(a['requested'])==number(a['received'])
            assert number(c['unit_price'])*number(c['quantity'])==number(c['amount'])==number(a['amount'])
            matching_context=[ctx for ctx in case['context_rows'] if norm(ctx['cells'][1])==norm(a['supplier'])]
            assert len(matching_context)==1,(r['CASO_ID'],matching_context)
            ctx=matching_context[0];case['provider_context_unique']=ctx
            if r['CONTRATACION_FORM']=='220':
                assert norm(c['supplier'])==norm(a['supplier'])
                assert norm(ctx['cells'][4])==norm(a['contract']) and ctx['cells'][5].strip()==a['date'].strip()
                assert ctx['cells'][8].strip()==a['deadline'].strip()
                headers=csrc['reader'].rows[ct][2]
                assert not any('contrato' in norm(h) or 'nro. documento' in norm(h) for h in headers)
                case['goods_header']=ref(csrc,ct,2)
                conclusion='VINCULABLE_POR_CONTEXTO_FORM220';cause='NUMERO_NO_PREVISTO_EN_TABLA_DE_BIENES'
            elif r['GRUPO_MUESTRA']=='AMBIGUA':
                assert norm(ctx['cells'][4])==norm(a['contract'])==norm(c['contract'])
                assert ctx['cells'][5].strip()==a['date'].strip() and ctx['cells'][8].strip()==a['deadline'].strip()
                s170=supplemental(r['CUCE'],'FORM 170')
                match170=[ref(s170,t,i) for t,rs in s170['reader'].rows.items() for i,cs in rs.items()
                          if len(cs)==10 and cs[0].strip().isdigit() and norm(cs[3])==norm(c['description'])
                          and number(cs[8])==number(c['quantity']) and number(cs[9])==number(c['amount'])]
                assert len(match170)==1,(r['CASO_ID'],match170)
                assert norm(match170[0]['cells'][6])==norm(a['supplier'])
                assert number(match170[0]['cells'][7])==number(c['unit_price'])
                case['adjudication_corroboration']=match170[0]
                conclusion='VINCULABLE_PROVEEDOR_CORROBORADO';cause='NUMERO_CONTRACTUAL_COMPARTIDO_ENTRE_PROVEEDORES'
            else:
                assert r['CUCE']=='26-0660-11-1658002-1-1'
                s250=supplemental(r['CUCE'],'FORM 250')
                case['contract_amendment']={k:ref(s250,*pos) for k,pos in {
                    'supplier':(5,4),'principal':(7,2),'scope':(9,2),'amendment':(10,2),'goods_no_records':(11,3),'consolidated':(12,1)}.items()}
                p250=case['contract_amendment']
                assert norm(p250['principal']['cells'][0])==norm(c['contract'])=='1210'
                assert norm(p250['amendment']['cells'][0])==norm(a['contract'])=='1353/2026'
                assert p250['principal']['cells'][2].strip()==ctx['cells'][5].strip()
                assert p250['amendment']['cells'][2].strip()==a['date'].strip()
                assert norm(p250['scope']['cells'][3])=='plazo'
                assert p250['amendment']['cells'][4].strip()==a['deadline'].strip()
                assert number(p250['amendment']['cells'][3])==0
                assert number(p250['consolidated']['cells'][2])==number(ctx['cells'][6])==39400
                assert norm(p250['supplier']['cells'][3])==norm(a['supplier'])
                conclusion='VINCULABLE_POR_MODIFICATORIO_FORM250';cause='REFERENCIA_A_ORDEN_MODIFICATORIA_DE_PLAZO'
        case.update(diagnostic_conclusion=conclusion,root_cause=cause)
        evidence.append(case)
        ledger.append({'CASO_ID':r['CASO_ID'],'CUCE':r['CUCE'],'GRUPO_MUESTRA':r['GRUPO_MUESTRA'],
                       'ETIQUETA_REVISION_ASISTIDA':r['ESTADO_CORRECTO'],'CONCLUSION_DIAGNOSTICO':conclusion,'CAUSA_RAIZ':cause,
                       'PROVEEDOR_RECEPCION':a['supplier'],'CONTRATO_FILA_CONTRATACION':c['contract'] or '',
                       'CONTRATO_RECEPCION':a['contract'],'CANTIDAD_CONTRATADA':c['quantity'],'CANTIDAD_RECIBIDA':a['received'],
                       'IMPORTE_CONTRATADO':c['amount'],'IMPORTE_RECIBIDO_HTML':a['amount'],
                       'REFERENCIA_CONTRATACION':f"{csrc['path']}#tabla={ct};fila={cr}",
                       'REFERENCIA_RECEPCION':f"{rsrc['path']}#tabla={rt};fila={rr}",
                       'EVIDENCIA_COMPLEMENTARIA':json.dumps(case.get('adjudication_corroboration') or case.get('contract_amendment') or case.get('provider_context_unique'),ensure_ascii=False)})
        if r['ESTADO_CORRECTO']=='INDETERMINADA' and r['CUCE'] not in balances:
            totals=defaultdict(Decimal)
            for _,cs in goods(rsrc,rt):
                rec=receipt(cs);totals[rec['supplier'].strip()]+=number(rec['amount'])
            ctxs=case['context_rows']
            comparisons=[{'supplier':ctx['cells'][1].strip(),'contract_context':ctx,
                          'contract_amount':str(number(ctx['cells'][6])),
                          'all_receipts_amount':str(totals.get(ctx['cells'][1].strip(),Decimal(0)))} for ctx in ctxs]
            assert all(number(x['contract_amount'])==number(x['all_receipts_amount']) for x in comparisons),(r['CUCE'],comparisons)
            balances[r['CUCE']]=comparisons
    for p,d in hashes.items(): assert sha(p)==d,p
    output.mkdir(parents=True,exist_ok=False)
    (output/'revision_asistida_recibida.csv').write_bytes(REVIEW.read_bytes())
    (output/'informe_asistido_recibido.md').write_bytes(REPORT.read_bytes())
    (output/'evidencia_por_caso.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (output/'conciliacion_por_proveedor.json').write_text(json.dumps(balances,ensure_ascii=False,indent=2)+'\n')
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(ledger[0]));w.writeheader();w.writerows(ledger)
    (output/'diagnostico_casos.csv').write_bytes(stream.getvalue().encode('utf-8-sig'))
    results={'cases':len(evidence),'review_indeterminate':38,'negative_controls':12,
             'diagnoses':dict(Counter(e['diagnostic_conclusion'] for e in evidence)),
             'cuces':len({e['cuce'] for e in evidence}),'cuces_indeterminate':len(balances),
             'original_html_files':len(sources),'sources_rules_outputs_inputs_unchanged':True,
             'code_and_inputs_sha256':hashes,'generator_sha256':sha(__file__)}
    (output/'verificacion_y_procedencia.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in results.items() if k!='code_and_inputs_sha256'},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    run(p.parse_args().output)
