import copy
import os
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from procesamiento.historico import technical as t,dbc,linking,enrich,pipeline
from procesamiento.historico.parser import parse_number

TEST_SOURCE=Path(os.environ.get("SICOES_HISTORICO_TEST_SOURCE", str(pipeline.DEFAULT_SOURCE)))

class ConstraintTests(unittest.TestCase):
    def test_leading_decimals_new_forms(self):
        for raw,value in [('.90','0.90'),(',54','0.54'),('-.8','-0.8'),('.800','0.800')]:self.assertEqual(parse_number(raw)['value'],value)
    def test_minimum_not_equality(self):
        attrs=t.attributes('RAM 16 GB mínimo')
        a=next(a for a in attrs if a['name']=='ram');self.assertEqual(a['operator'],'GE');self.assertEqual(a['value'],'16')
        self.assertNotEqual(t.attributes('RAM 16 GB')[0]['operator'],'EQ')
    def test_range_and_generation_not_range(self):
        attrs=t.attributes('RAM entre 16 y 32 GB')
        self.assertTrue(any(a['operator']=='RANGE' and a['value']==['16','32'] for a in attrs))
        attrs=t.attributes('Memoria RAM: 16 GB, DDR4 - 3200 MHz (o superior)')
        self.assertFalse(any(a['operator']=='RANGE' for a in attrs));self.assertTrue(any(a['name']=='frecuencia_memoria' and a['value']=='3200' for a in attrs))
    def test_maximum_and_contradiction(self):
        a=t.attributes('Ancho máximo (mm): 62 o superior')[-1];self.assertEqual(a['operator'],'CONTRADICTORIO')
        self.assertEqual(next(a for a in t.attributes('Tamaño hasta 20 mm') if a['name']=='dimension')['operator'],'LE')
    def test_alternative_not_two_simultaneous_requirements(self):
        attrs=t.attributes('Color azul o negro')
        self.assertTrue(all(a['operator']=='ONE_OF' for a in attrs));self.assertTrue(all(a['alternatives']==['azul','negro'] for a in attrs))
        attrs=t.attributes('Tóner para impresoras o fax serie TN750 color negro original')
        self.assertFalse(any(a['operator'] in ('ONE_OF','ALTERNATIVA') for a in attrs))
    def test_compatibility_codes_and_multiple_consumables(self):
        text='Tóner compatible con HP M201; serie Q2612A / CE285A color negro'
        attrs=t.attributes(text);codes={a['value'] for a in attrs if a['name']=='codigo_consumible_declarado'}
        self.assertEqual(codes,{'Q2612A','CE285A'});self.assertNotIn('M201',codes)
        self.assertTrue(any(a['role']=='compatibilidad_no_identidad' for a in attrs))
    def test_missing_brand_unknown_not_value_especificar(self):
        attrs=t.attributes('Marca: (Especificar lo requerido)')
        self.assertEqual(attrs[0]['value'],None);self.assertEqual(attrs[0]['operator'],'DESCONOCIDO')
    def test_evidence_literal_and_negative_requirement(self):
        text='No se acepta plástico'
        attrs=t.attributes(text);self.assertEqual(attrs[0]['operator'],'PROHIBIDO')
        for a in attrs:self.assertEqual(text[slice(*a['span'])],a['evidence'])
    def test_vector_resolution_and_page_unit(self):
        a=t.attributes('Resolución óptica 600 ppp x 600 ppp')
        self.assertTrue(any(x['value']==['600','600'] and x['name']=='resolucion_optica' for x in a))
        a=t.attributes('Velocidad 50 páginas x minuto o superior')
        self.assertEqual(a[0]['name'],'velocidad_impresion_o_escaneo');self.assertNotEqual(a[0]['name'],'voltaje')
    def test_component_scope_is_not_main_product_identity(self):
        a=t.attributes('Tipo de documentos que admite: tarjeta de plástico')
        self.assertTrue(any(x['name']=='material_documento_admitido' and x['role']=='compatibilidad_no_identidad' for x in a))
        self.assertFalse(any(x['name']=='material' for x in a))
        a=t.attributes('Datos velocidad de escáner: 40 ppm Blanco y negro')
        self.assertFalse(any(x['name']=='color' for x in a))
        a=t.attributes('Disco Duro: HDD 1TB y SSD 256GB (o superior)')
        self.assertTrue(any(x['name']=='almacenamiento_hdd' for x in a));self.assertTrue(any(x['name']=='almacenamiento_ssd' for x in a))


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block=patch('socket.socket.connect',side_effect=AssertionError('Sin red'));cls.block.start()
        cls.source=TEST_SOURCE
        if not list(cls.source.glob('*/manifest.json')):raise unittest.SkipTest('Corpus local ausente; configurar SICOES_HISTORICO_TEST_SOURCE')
        cls.cuces=sorted(p.parent.name for p in cls.source.glob('*/manifest.json'))
        cls.docs,cls.checks,cls.processes=pipeline.load(cls.source,cls.cuces)
        cls.obs=[o for d in cls.docs for o in d['observations']]
        cls.inv,cls.specs,cls.sections,cls.dbc_checks=dbc.inventory(cls.source,cls.cuces)
        cls.links=linking.link(cls.specs,cls.obs);cls.products=enrich.representations(cls.obs,cls.specs,cls.links)
    @classmethod
    def tearDownClass(cls):
        pipeline.assert_sources_unchanged({**cls.checks,**cls.dbc_checks});cls.block.stop()
    def test_expansion_counts_no_unextracted_goods(self):
        a=pipeline.audit(self.docs,self.processes,None)
        self.assertEqual(len(self.cuces),19);self.assertEqual(len(self.obs),348)
        self.assertEqual(a['status'],'EXTRAIDO_SIN_COTEJO_MANUAL');self.assertEqual(sum(d['difference'] for d in a['documents']),0)
        self.assertEqual(sum(d['status']=='EXCLUIDO' for d in self.docs),1)
    def test_coverage_not_every_process_has_dbc(self):
        self.assertEqual(len(self.inv),19);self.assertEqual(sum(i['status']=='SIN_DBC_LOCAL' for i in self.inv),12)
        self.assertEqual(sum(i['status']=='DBC_CON_ESPECIFICACIONES' for i in self.inv),7);self.assertEqual(len(self.specs),54)
    def test_main_section_only_no_template_example_contamination(self):
        pc=next(b for b in self.specs if '1444037' in b['cuce'])
        ram=[a for a in pc['attributes'] if a['name']=='ram']
        self.assertEqual([(a['value'],a['operator']) for a in ram],[('16','GE')])
        self.assertNotIn('512',[a['value'] for a in ram])
        self.assertTrue(all('PARTE III' not in s['markdown_section']['text'] for s in self.sections))
    def test_every_attribute_evidence_exists_in_original_docx_cell(self):
        from xml.etree import ElementTree as E
        from zipfile import ZipFile
        cache={}
        for b in self.specs:
            if b['original_path'] not in cache:
                with ZipFile(self.source/b['original_path']) as z:cache[b['original_path']]=list(E.fromstring(z.read('word/document.xml')).iter(dbc.W+'tbl'))
            tables=cache[b['original_path']]
            for a in b['attributes']:
                ref=a['reference'];row=tables[ref['table']-1].findall(dbc.W+'tr')[ref['row']-1];cell=row.findall(dbc.W+'tc')[ref['cell']-1]
                self.assertIn(a['evidence'],dbc.text(cell));self.assertEqual(a['context'][slice(*a['span'])],a['evidence'])
    def test_item_number_alone_cannot_confirm_and_code_conflict_stays_ambiguous(self):
        laser=next(b for b in self.specs if '1412564' in b['cuce'] and b['number']=='1')
        rel=next(r for r in self.links if r['spec_id']==laser['spec_id'])
        self.assertEqual(rel['status'],'AMBIGUA')
        typo=next(b for b in self.specs if '1477921' in b['cuce'] and b['number']=='7')
        rel=next(r for r in self.links if r['spec_id']==typo['spec_id'])
        self.assertEqual(rel['status'],'AMBIGUA');self.assertTrue(rel['candidates'][0]['evidence']['code_conflict'])
    def test_confirmed_evidence_uses_more_than_item_number_and_same_cuce(self):
        for r in self.links:
            if r['status']=='CONFIRMADA':
                e=r['candidates'][0]['evidence'];self.assertTrue(e['cuce_equal']);self.assertFalse(e['code_conflict']);self.assertFalse(e['quantity_conflict'])
                self.assertTrue(e['codes_shared'] or len(e['description_tokens_shared'])>=2 or e['type_form'] in ('escaner','matricial','termica'))
    def test_A_B_same_items_ambiguity_not_injected(self):
        self.assertEqual(len(self.products),100)
        for p in self.products:
            self.assertEqual(p['A']['description'],p['B']['description'])
            self.assertEqual(p['A']['description_original'],p['B']['description_original'])
            if p['link_status']!='CONFIRMADA':self.assertEqual(p['B']['attributes'],p['A']['attributes']);self.assertEqual(p['B']['specification_ids'],[])
    def test_duplicate_spec_claims_are_not_forced(self):
        b=next(b for b in self.specs if '1444037' in b['cuce']);dup=copy.deepcopy(b);dup['spec_id']='duplicate'
        links=linking.link([b,dup],self.obs)
        self.assertTrue(all(r['status']=='AMBIGUA' for r in links))
    def test_unit_and_lot_conflicts_cannot_confirm(self):
        spec=copy.deepcopy(next(b for b in self.specs if '1444037' in b['cuce']))
        observation=copy.deepcopy(next(o for o in self.obs if o['cuce']==spec['cuce'] and o['stage']=='requerimiento'))
        next(f for f in observation['fields'] if f['name']=='unidad_medida')['visible']='Paquete'
        c=linking.candidate(spec,observation);self.assertTrue(c['evidence']['unit_conflict']);self.assertFalse(c['confirmation_supported'])
        next(f for f in observation['fields'] if f['name']=='unidad_medida')['visible']='Pieza'
        spec['lot']='1';observation['fields'].append({'name':'lote_documentado','visible':'2'})
        c=linking.candidate(spec,observation);self.assertTrue(c['evidence']['lot_conflict']);self.assertFalse(c['confirmation_supported'])
    def test_integrated_sqlite_round_trip(self):
        (pipeline.PACKAGE/'data/tests').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=pipeline.PACKAGE/'data/tests') as tmp:
            root=Path(tmp);structured=root/'base';structured.mkdir()
            pipeline.write_database(structured,self.docs,{'test':True})
            enrich.write_integrated_db(root/'enriched.sqlite',structured,self.inv,self.specs,self.links,self.products,self.sections)
            with sqlite3.connect('file:'+str(root/'enriched.sqlite')+'?mode=ro',uri=True) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM observaciones').fetchone()[0],348)
                self.assertEqual(c.execute('SELECT count(*) FROM canonicalization_inputs').fetchone()[0],100)
                self.assertEqual(c.execute('SELECT count(*) FROM dbc_specs').fetchone()[0],54)
                self.assertEqual(c.execute('SELECT count(*) FROM dbc_sections').fetchone()[0],7)
                self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
