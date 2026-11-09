"""Cotejo contra el DOM por un lector independiente y referencia manual de desarrollo."""
from html.parser import HTMLParser
from decimal import Decimal
import json
from pathlib import Path


class SourceRows(HTMLParser):
    """Índices físicos 1-based; no usa BeautifulSoup ni el mapeador del extractor."""
    def __init__(self):
        super().__init__(convert_charrefs=True);self.tables=[];self.active=[];self.cells=[];self.rows={}
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.tables.append({'id':len(self.rows)+1,'row':0});self.active.append(self.tables[-1]);self.rows[len(self.rows)+1]={}
        elif tag=='tr' and self.active:
            t=self.active[-1];t['row']+=1;self.rows[t['id']][t['row']]=[]
        elif tag in ('td','th') and self.active:
            t=self.active[-1];cell={'tag':tag,'text':'','table':t['id'],'row':t['row']};self.cells.append(cell)
    def handle_data(self,text):
        for cell in self.cells:cell['text']+=text
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cells:
            cell=self.cells.pop();self.rows[cell['table']][cell['row']].append(cell['text'])
        elif tag=='table' and self.active:self.active.pop()


def check(documents,source,reference_path):
    ref=json.loads(Path(reference_path).read_text());failures=[];checked=0;checked_cells=0;layout_differences=0;manual=0
    actual={(d['cuce'].split('-')[3],d['form']):d for d in documents}
    expected_keys={(d['process'],d['form']) for d in ref['documents']}
    processed_keys={k for k,d in actual.items() if d.get('status')!='EXCLUIDO'}
    if processed_keys!=expected_keys:failures.append({'reason':'document_set_mismatch'})
    for expected in ref['documents']:
        doc=actual.get((expected['process'],expected['form']))
        if doc is None:failures.append({'document':expected,'reason':'missing_document'});continue
        if doc['source_sha256']!=expected['sha256']:failures.append({'form':doc['form'],'reason':'source_changed_since_manual_review'})
        reader=SourceRows();reader.feed((Path(source)/doc['source_path']).read_text())
        expected_positions={(r['table'],r['row']) for r in expected['rows']}
        obs={(r['table_position'],r['row_position']):r for r in doc['observations']}
        if set(obs)!=expected_positions:failures.append({'cuce':doc['cuce'],'form':doc['form'],'reason':'row_positions_mismatch'})
        for position,o in obs.items():
            raw=reader.rows.get(position[0],{}).get(position[1],[]);checked+=1
            extracted=[f['raw'] for f in o['fields']]
            if [' '.join(v.split()) for v in raw]!=[' '.join(v.split()) for v in extracted]:failures.append({'observation':o['observation_id'],'reason':'cell_content_differs_from_independent_html_reader'})
            layout_differences+=sum(a!=b for a,b in zip(raw,extracted))
            checked_cells+=len(raw)
            for f in o['fields']:
                if f['name']=='descripcion' and f['raw']!=o['description_raw']:failures.append({'observation':o['observation_id'],'reason':'description_not_original'})
        for r in expected['rows']:
            o=obs.get((r['table'],r['row']))
            if not o:continue
            if o['stage']!=r['stage']:failures.append({'reason':'wrong_stage','observation':o['observation_id']})
            fields={f['name']:f for f in o['fields']}
            for key,value in r.get('values',{}).items():
                manual+=1;found=fields.get(key)
                # Referencia curada: valores numéricos comparados sin redondear.
                if not found or found['normalized']['value'] is None or Decimal(found['normalized']['value'])!=Decimal(value):failures.append({'reason':'manual_numeric_mismatch','attribute':key,'observation':o['observation_id']})
            if r.get('description_contains','').casefold() not in o['description_visible'].casefold():failures.append({'reason':'manual_description_mismatch','observation':o['observation_id']})
            for key in r.get('absent',[]):
                if key in fields:failures.append({'reason':'invented_field','attribute':key})
            if 'derived_price' in r:
                if len(o['derived'])!=1 or Decimal(o['derived'][0]['value'])!=Decimal(r['derived_price']):failures.append({'reason':'derived_price_mismatch','observation':o['observation_id']})
                if any(f['name']=='precio_unitario_recepcion_derivado' for f in o['fields']):failures.append({'reason':'derived_value_mixed_with_original'})
    return {'status':'COTEJO_PILOTO_OK' if not failures else 'REQUIERE_REVISION','observations_checked':checked,'cells_checked':checked_cells,'layout_whitespace_differences':layout_differences,'comparison_policy':'Contenido de celdas sin sangría/espaciado de maquetación; integridad de bytes verificada por SHA256 del HTML original.',
            'manual_numeric_assertions':manual,'failures':failures,
            'scope':'Referencia de desarrollo revisada sobre estos HTML; no validación independiente de precisión comercial ni canonicalización.'}


def source_fidelity(documents,source):
    """Cotejo de todas las celdas extraídas sin llamarlo evaluación de precisión."""
    failures=[];observations=0;cells=0;layout=0
    for doc in documents:
        if doc.get('status')=='EXCLUIDO':continue
        reader=SourceRows();reader.feed((Path(source)/doc['source_path']).read_text())
        for o in doc['observations']:
            actual=reader.rows.get(o['table_position'],{}).get(o['row_position'],[]);extracted=[f['raw'] for f in o['fields']]
            observations+=1;cells+=len(actual);layout+=sum(a!=b for a,b in zip(actual,extracted))
            if [' '.join(v.split()) for v in actual]!=[' '.join(v.split()) for v in extracted]:failures.append({'observation_id':o['observation_id'],'reason':'contenido_no_coincide_con_HTML'})
    return {'observations_checked':observations,'cells_checked':cells,'layout_whitespace_differences':layout,'failures':failures,
            'status':'COTEJO_TEXTO_OK' if not failures else 'REQUIERE_REVISION',
            'qualification':'Verifica fidelidad de las filas extraídas, no recall independiente de filas omitidas ni exactitud comercial.'}
