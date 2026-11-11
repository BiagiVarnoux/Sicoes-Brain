"""Etapa 1: corpus completo y controles adversos, sin nuevas relaciones con recepción."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bs4 import BeautifulSoup
from procesamiento.historico import form220_context as f, parser, pipeline

REPO = Path(os.environ.get('SICOES_FORM220_REPO_ROOT', str(pipeline.ROOT)))
BASE = REPO/'scraper/historico_local/data'
CUCE = '22-0660-10-1199746-1-1'


def original(cuce=CUCE, label='FORM 220'):
    root=BASE/f'historico_http_paginas_{cuce[3:10]}_20{cuce[:2]}'/cuce
    m=json.loads((root/'manifest.json').read_text())
    key,d=next((k,d) for k,d in m['documents'].items() if d['label']==label)
    v=next(v for v in reversed(d['versions']) if v.get('valid'))
    return (root/v['path']).read_bytes(),key,m,v


def process(data,cuce=CUCE,key='FORM:FORM 220:prueba'):
    return f.process_document(data,cuce,'prueba.html',key)


class IsolatedNegatives(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BASE.exists():raise unittest.SkipTest('Configurar SICOES_FORM220_REPO_ROOT')
        cls.block=patch('socket.socket.connect',side_effect=AssertionError('Prohibida la red'));cls.block.start()
        cls.data,_,_,_=original()
    @classmethod
    def tearDownClass(cls):cls.block.stop()
    def test_positions_can_shift(self):
        soup=BeautifulSoup(self.data,'lxml')
        soup.find('table').insert_before(BeautifulSoup('<table><tr><td>Nota de prueba</td></tr></table>','lxml').find('table'))
        before=process(self.data);after=process(str(soup).encode())
        self.assertNotEqual(before['schema']['contracts'][0]['table'],after['schema']['contracts'][0]['table'])
        self.assertEqual(after['links'][0]['context_status'],'CONFIRMADA')
        self.assertEqual(after['links'][0]['context_candidates'][0]['reference']['table'],after['schema']['contracts'][0]['table'])
    def test_supplier_column_can_move(self):
        soup=BeautifulSoup(self.data,'lxml');ti=f.schema(self.data)['goods'][0]['table'];table=soup.find_all('table')[ti-1]
        for tr in parser.direct_rows(table):
            cells=parser.cells(tr)
            if len(cells)==10:
                provider=cells[6].extract();cells[4].insert_before(provider)
        result=process(str(soup).encode());link=result['links'][0]
        self.assertEqual(link['context_status'],'CONFIRMADA')
        self.assertEqual(link['supplier_evidence']['item_cell']['reference']['column'],5)
    def test_contract_table_can_move(self):
        soup=BeautifulSoup(self.data,'lxml');ti=f.schema(self.data)['contracts'][0]['table']
        context=soup.find_all('table')[ti-1].extract();soup.find('table').insert_before(context)
        result=process(str(soup).encode())
        self.assertEqual(result['links'][0]['context_status'],'CONFIRMADA')
        self.assertEqual(result['schema']['contracts'][0]['table'],1)
    def test_duplicate_supplier_context_stays_ambiguous(self):
        soup=BeautifulSoup(self.data,'lxml');ti=f.schema(self.data)['contracts'][0]['table'];table=soup.find_all('table')[ti-1]
        data_row=parser.direct_rows(table)[1];other=copy.deepcopy(data_row)
        parser.cells(other)[0].string='2';parser.cells(other)[4].string='OTRA_ORDEN';table.append(other)
        result=process(str(soup).encode());link=result['links'][0]
        self.assertEqual(link['context_status'],'AMBIGUA');self.assertEqual(len(link['context_candidates']),2)
        self.assertIsNone(link['contextual_contract_reference']);self.assertIsNone(link['context_id'])
    def test_missing_mismatching_or_duplicate_supplier_does_not_fallback_to_total(self):
        for mode in ('missing','mismatch','duplicate_field'):
            result=process(self.data);d=result['document'];o=d['observations'][0]
            if mode=='missing':next(x for x in o['fields'] if x['name']=='proveedor_documentado')['visible']=''
            elif mode=='mismatch':next(x for x in o['fields'] if x['name']=='proveedor_documentado')['visible']='OTRO PROVEEDOR'
            else:o['fields'].append(copy.deepcopy(next(x for x in o['fields'] if x['name']=='proveedor_documentado')))
            with self.subTest(mode=mode):
                link=f.associate(d,o,result['schema'])
                self.assertNotEqual(link['context_status'],'CONFIRMADA');self.assertIsNone(link['contextual_contract_reference'])
    def test_other_document_and_other_cuce_are_rejected(self):
        r=process(self.data);o=r['document']['observations'][0]
        for changes in ({'document_id':'otro_documento'},{'cuce':'22-0660-11-9999999-1-1'},{'form':'500'},{'stage':'no_contratacion'}):
            with self.subTest(changes=changes):
                link=f.associate(r['document'],dict(o,**changes),r['schema'])
                self.assertEqual(link['context_status'],'NO_ELEGIBLE')
    def test_number_of_item_and_amount_never_choose_a_supplier(self):
        r=process(self.data);o=r['document']['observations'][0];supplier=next(x for x in o['fields'] if x['name']=='proveedor_documentado')
        o['fields'].remove(supplier)
        self.assertEqual(f.associate(r['document'],o,r['schema'])['context_status'],'SIN_CONTEXTO')
    def test_unknown_schema_abstains(self):
        soup=BeautifulSoup(self.data,'lxml');ti=f.schema(self.data)['contracts'][0]['table']
        parser.cells(parser.direct_rows(soup.find_all('table')[ti-1])[0])[4].string='Referencia no admitida'
        result=process(str(soup).encode());self.assertEqual(result['status'],'ESQUEMA_NO_ADMITIDO')
        self.assertTrue(all(l['context_status']=='NO_ELEGIBLE' for l in result['links']))
    def test_unknown_contract_literal_is_not_certified_simple(self):
        self.assertEqual(f.reference_kind('SIN DATO'),'NO_INTERPRETADA')
        for text in ('009-0010','57 - 61','19-29'):
            self.assertEqual(f.reference_kind(text),'COMPUESTA_NO_DESGLOSADA')
        self.assertEqual(f.reference_kind('Nº 55'),'LITERAL_SIMPLE')
    def test_erroneous_label_and_title_are_both_excluded(self):
        data,key,_,_=original('23-0660-11-1333011-1-1','Formulario 220 (Erroneo)')
        for label in ('FORM 220','Formulario 220 (Erroneo)'):
            with self.subTest(label=label):
                r=f.process_document(data,'23-0660-11-1333011-1-1','err.html',key,label)
                self.assertEqual(r['status'],'EXCLUIDO_PUBLICADO_ERRONEO');self.assertEqual(r['links'],[]);self.assertIsNone(r['document'])
    def test_document_and_observations_are_not_mutated(self):
        result=process(self.data);d=result['document'];before=copy.deepcopy(d)
        for o in d['observations']:f.associate(d,o,result['schema'])
        self.assertEqual(d,before)
        self.assertTrue(all(l['item_contract_number_original'] is None for l in result['links']))
        self.assertTrue(all(not any(x['name']=='nro_contrato_documentado' for x in o['fields']) for o in d['observations']))
    def test_non_contracted_goods_have_no_links(self):
        data,key,_,_=original('22-0660-10-1221191-1-1');r=process(data,'22-0660-10-1221191-1-1',key)
        excluded={o['observation_id'] for o in r['document']['observations'] if o['stage']=='no_contratacion'}
        self.assertEqual(len(excluded),1);self.assertTrue(excluded.isdisjoint(l['observation_id'] for l in r['links']))
    def test_absent_invalid_and_missing_file_are_distinct(self):
        for mode,status in [('manifest','AUSENTE_EN_MANIFIESTO'),('invalid','SIN_VERSION_VALIDA'),('file','ARCHIVO_AUSENTE')]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as td:
                base=Path(td)/'base';folder=base/'historico_http_paginas_0660-10_2022'/CUCE;folder.mkdir(parents=True)
                _,key,m,v=original();m=copy.deepcopy(m)
                m['documents']={} if mode=='manifest' else {key:{'kind':'FORM','label':'FORM 220','versions':[] if mode=='invalid' else [v]}}
                m['announced']={'forms':[{'label':'FORM 220'}]};(folder/'manifest.json').write_text(json.dumps(m))
                out=Path(td)/'out';report=f.run(base,out)
                self.assertEqual(report['documents_by_status'].get(status),1);self.assertEqual(report['links'],0)
    def test_integrity_failure_and_existing_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)/'base';folder=base/'historico_http_paginas_0660-10_2022'/CUCE;folder.mkdir(parents=True)
            data,key,m,v=original();m=copy.deepcopy(m);v=copy.deepcopy(v);v['sha256']='0'*64
            m['documents']={key:{'kind':'FORM','label':'FORM 220','versions':[v]}}
            path=folder/v['path'];path.parent.mkdir();path.write_bytes(data);(folder/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Integridad'):f.run(base,Path(td)/'out')
            with self.assertRaisesRegex(ValueError,'Salida nueva'):f.run(base,Path(td))


class FullCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BASE.exists():raise unittest.SkipTest('Configurar SICOES_FORM220_REPO_ROOT')
        cls.block=patch('socket.socket.connect',side_effect=AssertionError('Prohibida la red'));cls.block.start()
        cls.temp=tempfile.TemporaryDirectory();cls.out=Path(cls.temp.name)/'out'
        with patch.object(f.parser,'parse_document',wraps=f.parser.parse_document) as parse:
            cls.report=f.run(BASE,cls.out)
            assert all(c.args[2]=='220' for c in parse.call_args_list)
            cls.parse_count=parse.call_count
        read=lambda name:[json.loads(line) for line in (cls.out/name).open()]
        cls.obs=read('observaciones.jsonl');cls.links=read('asociaciones_internas.jsonl');cls.docs=read('documentos.jsonl')
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup();cls.block.stop()
    def test_all_386_goods_and_106_documents(self):
        self.assertEqual(self.report['links'],386);self.assertEqual(self.parse_count,106)
        self.assertEqual(self.report['context_status'],{'CONFIRMADA':386})
        self.assertEqual(self.report['contract_context_rows'],148)
        self.assertEqual(self.report['context_cells_checked'],1332)
        self.assertEqual(self.report['source_fidelity']['cells_checked'],3884)
    def test_20_multi_supplier_documents(self):
        self.assertEqual(sum(x['multi_supplier_documents'] for x in self.report['by_entity_year']),20)
    def test_all_23_compound_items_keep_the_exact_literal(self):
        compound=[l for l in self.links if l['contextual_contract_reference']['kind']=='COMPUESTA_NO_DESGLOSADA']
        self.assertEqual(len(compound),23)
        self.assertEqual(self.report['contract_reference_kind'],{'LITERAL_SIMPLE':363,'COMPUESTA_NO_DESGLOSADA':23})
        counts={s:sum(' '.join(l['contextual_contract_reference']['raw'].split())==s for l in compound) for s in ('009-0010','57 - 61','19-29')}
        self.assertEqual(counts,{'009-0010':2,'57 - 61':19,'19-29':2})
        self.assertTrue(all(l['context_status']=='CONFIRMADA' and l['individual_order_uncertain'] and l['individual_order_status']=='ORDEN_INDIVIDUAL_INDETERMINADA' for l in compound))
        self.assertTrue(all(l['item_contract_number_original'] is None for l in self.links))
    def test_exact_original_observations_v2_preserved(self):
        old=BASE.parents[2]/'procesamiento/historico/data/adquisiciones_v2_20261109_01/observaciones.jsonl'
        with old.open() as stream:before=[o for line in stream if (o:=json.loads(line))['form']=='220']
        self.assertEqual(self.obs,before)
    def test_3_non_contracted_1_erroneous_2_absent_regular(self):
        self.assertEqual(self.report['observations_by_stage'],{'contratacion':386,'no_contratacion':3})
        self.assertEqual(self.report['documents_by_status'],{'PROCESADO':106,'AUSENTE_EN_MANIFIESTO':2,'EXCLUIDO_PUBLICADO_ERRONEO':1})
        self.assertEqual(self.report['all220_absent_processes'],1)
        self.assertTrue(all(o['stage']=='contratacion' for o in self.obs if o['observation_id'] in {l['observation_id'] for l in self.links}))
    def test_references_point_to_original_cells_and_same_document(self):
        docs={d['document_id']:d for d in self.docs}
        for l in self.links:
            d=docs[l['document_id']];c=l['context_candidates'][0];ref=l['contextual_contract_reference']['reference']
            self.assertEqual(c['reference']['document_id'],l['item_reference']['document_id'])
            raw=next(r for r in d['raw_rows'] if r['table_position']==ref['table'] and r['row_position']==ref['row'])
            self.assertEqual(raw['cells'][ref['column']-1]['text'],l['contextual_contract_reference']['raw'])
    def test_no_form500_read_or_linked(self):
        pro=json.loads((self.out/'procedencia.json').read_text())
        self.assertFalse(self.report['form500_read_or_linked'])
        self.assertTrue(all('FORM_500' not in p and 'FORM_200' not in p and 'FORM_170' not in p for p in pro['input_sha256']))

if __name__=='__main__':unittest.main()
