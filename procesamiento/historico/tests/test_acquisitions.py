"""Contratos comerciales, abstención y regresión sobre originales locales."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from procesamiento.historico import acquisitions as a, pipeline, dbc, linking
from procesamiento.historico.parser import parse_document


class AcquisitionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block = patch('socket.socket.connect', side_effect=AssertionError('Sin red'))
        cls.block.start()
        cls.source = pipeline.ROOT/'scraper/historico_local/data/historico_http_paginas_0660-11_2023'
        cls.cuce = '23-0660-11-1314047-1-1'
        folder = cls.source/cls.cuce
        m = json.loads((folder/'manifest.json').read_text())
        cls.docs = []
        for key, d in m['documents'].items():
            form = d['label'].replace('FORM ', '')
            if form not in ('200','500'): continue
            v = next(v for v in reversed(d['versions']) if v.get('valid'))
            cls.docs.append(parse_document((folder/v['path']).read_bytes(), cls.cuce, form, str(folder/v['path']), key))
        cls.c = next(d['observations'][0] for d in cls.docs if d['form']=='200')
        cls.r = next(d['observations'][0] for d in cls.docs if d['form']=='500')
    @classmethod
    def tearDownClass(cls): cls.block.stop()
    def test_original_case(self):
        c,r=self.c,self.r
        self.assertEqual((c['table_position'],c['row_position']),(11,3))
        self.assertEqual((r['table_position'],r['row_position']),(5,3))
        for key,expected in [('cantidad','20'),('precio_unitario_contratado','3090'),('importe_total_contratado','61800')]:
            self.assertEqual(a.value(c,key),expected)
        self.assertEqual(a.value(r,'proveedor_documentado'),'TOLA MAMANI PEDRO')
        self.assertEqual(a.value(r,'cantidad_reportada_recepcion'),'20')
        self.assertEqual(r['derived'][0]['value'],'3090')
        self.assertEqual(a.resolve([a.match_receipt(r,c)])[0]['status'],'CONFIRMADA')
        self.assertIsNone(a.commercial(r)['unidad_medida'])
    def test_item_number_alone_is_not_link(self):
        c=copy.deepcopy(self.c)
        c['description_visible']='Impresora térmica'
        for f in c['fields']:
            if f['name']=='nro_contrato_documentado': f['normalized']['value']='OTRO'
        self.assertIsNone(a.match_receipt(self.r,c))
    def test_conflict_and_many_relations_abstain(self):
        c=copy.deepcopy(self.c)
        c['fields'].append({'name':'unidad_medida','column':99,'visible':'CAJA','raw':'CAJA','normalized':{'value':'CAJA'}})
        # Duplicate semantic unit is unknown, not evidence for confirmation without quantity.
        r=copy.deepcopy(self.r)
        r['fields'].append({'name':'unidad_medida','column':99,'visible':'CAJA','raw':'CAJA','normalized':{'value':'CAJA'}})
        self.assertFalse(a.match_receipt(r,self.c)['supported'])
        e=a.match_receipt(self.r,self.c); other=dict(e,right_id='another')
        self.assertTrue(all(x['status']=='AMBIGUA' for x in a.resolve([e,other])))
        e=a.match_receipt(self.r,self.c); other=dict(e,left_id='another')
        self.assertTrue(all(x['status']=='AMBIGUA' for x in a.resolve([e,other])))
    def test_unconfirmed_receipt_does_not_claim_received_quantity(self):
        r=copy.deepcopy(self.r)
        for f in r['fields']:
            if f['name']=='estado_recepcion': f['normalized']['value']='Pendiente'
        self.assertIsNone(a.commercial(r)['cantidad_recibida'])
        self.assertIsNotNone(a.commercial(r)['cantidad_reportada_recepcion'])
    def test_real_dbc_unsupported_layout_is_explicit(self):
        inv, specs, sections, _ = dbc.inventory(self.source,[self.cuce])
        self.assertEqual(specs,[])
        self.assertEqual(inv[0]['status'],'DBC_SIN_ESPECIFICACIONES_IDENTIFICABLES')
        self.assertTrue(sections)
        self.assertIn('roble',sections[0]['markdown_section']['text'].lower())
    def test_existing_2024_regression(self):
        cuces=sorted(p.parent.name for p in pipeline.DEFAULT_SOURCE.glob('*/manifest.json'))
        docs, checks, _ = pipeline.load(pipeline.DEFAULT_SOURCE,cuces)
        observations=[o for d in docs for o in d['observations']]
        self.assertEqual(len(observations),348)
        _, specs, _, more=dbc.inventory(pipeline.DEFAULT_SOURCE,cuces)
        self.assertEqual(len(specs),54)
        self.assertEqual(sum(len(s['attributes']) for s in specs),198)
        relations=linking.link(specs,observations)
        self.assertEqual(sum(r['status']=='CONFIRMADA' for r in relations),51)
        self.assertEqual(sum(r['status']=='AMBIGUA' for r in relations),3)
        pipeline.assert_sources_unchanged({**checks,**more})


class RealComplexCases(unittest.TestCase):
    def test_multiple_suppliers_remain_unassigned(self):
        source = pipeline.ROOT/'scraper/historico_local/data/historico_http_paginas_0660-11_2025'
        folder = source/'25-0660-11-1517374-1-1'
        m = json.loads((folder/'manifest.json').read_text())
        for key,d in m['documents'].items():
            if d['label'] != 'FORM 200': continue
            v=next(v for v in reversed(d['versions']) if v.get('valid'))
            doc=parse_document((folder/v['path']).read_bytes(),m['cuce'],'200',str(folder/v['path']),key)
            suppliers={f['raw'] for r in doc['contract_context'] for f in r['fields'] if f['header_raw']=='Nombre o razón social'}
            self.assertGreater(len(suppliers),1)
            self.assertGreater(len(doc['observations']),1)
            self.assertTrue(all(a.value(o,'proveedor_documentado') is None for o in doc['observations']))
    def test_real_dbc_quantity_conflict_abstains(self):
        source=pipeline.ROOT/'scraper/historico_local/data/historico_http_paginas_0660-10_2023'
        cuce='23-0660-10-1329122-1-1'
        docs,_,_=pipeline.load(source,[cuce]);_,specs,_,_=dbc.inventory(source,[cuce])
        candidates=[linking.candidate(s,o) for s in specs for d in docs for o in d['observations'] if o['form']=='200']
        conflicts=[c for c in candidates if c and c['evidence']['quantity_conflict']]
        self.assertTrue(conflicts)
        self.assertTrue(all(not c['confirmation_supported'] for c in conflicts))


class AssociationV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref=json.loads((Path(a.__file__).parent/'acquisiciones_referencia_v2.json').read_text())
        cls.source=pipeline.ROOT/'scraper/historico_local/data/historico_http_paginas_0660-11_2025'
        cls.docs,_,_=pipeline.load(cls.source,[cls.ref['cuce']])
        cls.contract_doc=next(d for d in cls.docs if d['form']=='200')
        cls.receipt_doc=next(d for d in cls.docs if d['form']=='500')
        cls.cs=cls.contract_doc['observations'];cls.rs=cls.receipt_doc['observations']
    def test_curated_pairs_against_independent_original_reader(self):
        from procesamiento.historico.review import SourceRows
        self.assertEqual(self.contract_doc['source_sha256'],self.ref['contract_sha256'])
        self.assertEqual(self.receipt_doc['source_sha256'],self.ref['receipt_sha256'])
        readers=[]
        for d in (self.contract_doc,self.receipt_doc):
            r=SourceRows();r.feed((self.source/d['source_path']).read_text());readers.append(r)
        for pair in self.ref['positive_pairs']:
            c=readers[0].rows[11][pair['contract_row']];r=readers[1].rows[5][pair['receipt_row']]
            compact=lambda t:' '.join(t.split())
            self.assertEqual(compact(c[3]),compact(r[4]))
            self.assertEqual(compact(c[4]),compact(r[1]))
            self.assertEqual(compact(c[8]),compact(r[6]))
            self.assertEqual(compact(c[9]),compact(r[11]))
    def test_nineteen_pairs_six_suppliers_no_cross_product_fusions(self):
        edges=a.resolve_receipts([e for r in self.rs for c in self.cs if (e:=a.match_receipt_v2(r,c,self.contract_doc))])
        actual={(next(r['row_position'] for r in self.rs if r['observation_id']==e['left_id']),next(c['row_position'] for c in self.cs if c['observation_id']==e['right_id'])) for e in edges if e['status']=='CONFIRMADA'}
        expected={(p['receipt_row'],p['contract_row']) for p in self.ref['positive_pairs']}
        self.assertEqual(actual,expected)
        self.assertEqual(len(edges),99)
        self.assertEqual(sum(e['status']=='DESCARTADA' for e in edges),80)
        self.assertEqual(sum(a.match_receipt_v2(r,c,self.contract_doc) is None for r in self.rs for c in self.cs),262)
        suppliers={e['evidence']['contract_supplier_context']['matches'][0]['supplier'] for e in edges if e['status']=='CONFIRMADA'}
        self.assertEqual(len(suppliers),6)
        self.assertTrue(any(p['receipt_row']!=p['contract_row'] for p in self.ref['positive_pairs']))
    def test_conflicting_supplier_date_and_duplicate_context_abstain(self):
        r=self.rs[0];c=next(c for c in self.cs if c['row_position']==15)
        for field_name in ('proveedor_documentado','fecha_firma_contrato'):
            changed=copy.deepcopy(r)
            for f in changed['fields']:
                if f['name']==field_name:f['normalized']['value']='CONTRADICCION'
            edge=a.resolve_receipts([a.match_receipt_v2(changed,c,self.contract_doc)])[0]
            self.assertEqual(edge['status'],'DESCARTADA')
        doc=copy.deepcopy(self.contract_doc);doc['contract_context']+=copy.deepcopy(doc['contract_context'])
        e=a.resolve_receipts([a.match_receipt_v2(r,c,doc)])[0]
        self.assertEqual(e['status'],'AMBIGUA')
    def test_repeated_eligible_receipts_remain_ambiguous(self):
        r=self.rs[0];c=next(c for c in self.cs if c['row_position']==15)
        other=copy.deepcopy(r);other['observation_id']='partial_receipt'
        edges=a.resolve_receipts([a.match_receipt_v2(x,c,self.contract_doc) for x in (r,other)])
        self.assertTrue(all(e['status']=='AMBIGUA' for e in edges))

    def test_real_shared_contract_number_does_not_assign_supplier(self):
        source=pipeline.DEFAULT_SOURCE
        docs,_,_=pipeline.load(source,['24-0660-10-1411332-1-1'])
        doc=next(d for d in docs if d['form']=='200')
        ambiguous=[o for o in doc['observations'] if a.supplier_context(o,doc)['status']=='AMBIGUO']
        self.assertTrue(ambiguous)
        rs=[o for d in docs if d['form']=='500' for o in d['observations']]
        edges=[e for r in rs for c in ambiguous if (e:=a.match_receipt_v2(r,c,doc))]
        self.assertTrue(edges)
        self.assertTrue(all(e['status']!='CONFIRMADA' for e in a.resolve_receipts(edges)))

if __name__=='__main__': unittest.main()
