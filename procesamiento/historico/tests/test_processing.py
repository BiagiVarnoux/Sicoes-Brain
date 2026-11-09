import csv
import os
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from procesamiento.historico import parser as p,pipeline as run
from procesamiento.historico.review import check

TEST_SOURCE=Path(os.environ.get("SICOES_HISTORICO_TEST_SOURCE", str(run.DEFAULT_SOURCE)))

CUCE='24-0660-10-1499648-1-1'
HEAD=['#','Código del Catálogo','Objeto de Gasto','Descripción del bien o servicio','Unidad de Medida','Cantidad','Precio referencial unitario','Precio referencial total']
DATA=['1','14111507','32100','Papel bond 75 gr','Paquete','652','46.00','29,992.00']
def table(headers,rows):return '<table><tr>'+''.join('<th>'+v+'</th>' for v in headers)+'</tr>'+''.join('<tr>'+''.join('<td>'+v+'</td>' for v in r)+'</tr>' for r in rows)+'</table>'
def parse(html,form='100'):
    return p.parse_document(('<html>'+CUCE+html+'</html>').encode(),CUCE,form,'crudos/form.html','FORM:test')
def receive(quantity='2',amount='10',state='Recibido',extra=False):
    headers=['#','Descripción del bien, obra o servicio objeto del contrato','Estado de la recepción','Cantidad solicitada','Cantidad Recepcionada/No Recepcionada','Monto real ejecutado']
    values=['1','Papel',state,'2',quantity,amount]
    if extra:headers.append('Precio unitario');values.append('9')
    return parse(table(headers,[values]),'500')

class ParserTests(unittest.TestCase):
    def test_numbers_and_ambiguity(self):
        for raw,value in [('29,992.00','29992.00'),('29.992,00','29992.00'),('44,89','44.89'),('67500','67500')]:self.assertEqual(p.parse_number(raw)['value'],value)
        for raw in ('1,706','1.706','Bs. 34','mínimo 10','1.2.3'):
            self.assertIsNone(p.parse_number(raw)['value'])
        self.assertEqual(p.parse_number('1,23.00')['status'],'invalid_grouping')
    def test_nested_tables_not_duplicate_goods(self):
        doc=parse('<table><tr><td>'+table(HEAD,[DATA])+'</td></tr></table>')
        self.assertEqual(len(doc['observations']),1);self.assertEqual(doc['observations'][0]['table_position'],2)
    def test_metadata_numbered_rows_not_goods(self):
        doc=parse(table(['#','Actividad','Fecha'],[['1','Entrega','03/12/2024']]))
        self.assertEqual(doc['observations'],[]);self.assertEqual(len(doc['raw_rows']),2)
    def test_unknown_commercial_column_is_preserved(self):
        doc=parse(table(HEAD+['Presentación adicional'],[DATA+['Caja 10 paquetes']]))
        f=doc['observations'][0]['fields'][-1]
        self.assertEqual(f['raw'],'Caja 10 paquetes');self.assertEqual(f['name'],'column_9')
        self.assertTrue(doc['tables'][0]['unknown_headers'])
    def test_repeated_item_number_does_not_collapse(self):
        doc=parse(table(HEAD,[DATA,DATA]));obs=doc['observations']
        self.assertEqual(len(obs),2);self.assertNotEqual(obs[0]['observation_id'],obs[1]['observation_id'])
    def test_malformed_goods_row_is_counted_not_silently_dropped(self):
        doc=parse(table(HEAD,[DATA[:-1]]));t=doc['tables'][0]
        self.assertEqual(t['detected_goods_rows'],1);self.assertEqual(t['extracted_goods_rows'],0)
        self.assertEqual(t['unextracted_rows'][0]['reason'],'column_count_mismatch')
    def test_header_rowspan_continuation_and_total_are_not_items(self):
        html='<table><tr>'+''.join('<th rowspan="2">'+v+'</th>' for v in HEAD)+'</tr><tr></tr><tr>'+''.join('<td>'+v+'</td>' for v in DATA)+'</tr><tr><td colspan="7">TOTAL: ejemplo</td><td>29,992.00</td></tr></table>'
        doc=parse(html);self.assertEqual(len(doc['observations']),1)
        self.assertEqual(doc['tables'][0]['detected_goods_rows'],1)
    def test_reception_derived_separate_from_explicit(self):
        o=receive(extra=True)['observations'][0]
        self.assertEqual(o['derived'][0]['value'],'5')
        self.assertEqual(next(f['raw'] for f in o['fields'] if f['name']=='precio_unitario_documentado'),'9')
        self.assertIn('difiere_del_derivado',' '.join(o['warnings']))
    def test_reception_invalid_calculation_is_abstention(self):
        for args in [('0','10','Recibido'),('-1','10','Recibido'),('2','-10','Recibido'),('1,234','10','Recibido'),('2','10','No Recibido')]:
            o=receive(*args)['observations'][0];self.assertEqual(o['derived'],[]);self.assertTrue(o['warnings'])
    def test_repeating_decimal_has_fraction_and_precision(self):
        d=receive('3','10')['observations'][0]['derived'][0]
        self.assertEqual(d['exact_fraction'],'10/3');self.assertEqual(d['precision'],'40_significant_digits')
    def test_wrong_cuce_rejected(self):
        with self.assertRaises(ValueError):p.parse_document(table(HEAD,[DATA]).encode(),CUCE,'100','x','y')
    def test_100e_not_supported_by_parser(self):
        self.assertNotIn('100-E',p.PHASE)
        with self.assertRaises(ValueError):parse(table(HEAD,[DATA]),'100-E')

class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block=patch('socket.socket.connect',side_effect=AssertionError('Sin red'));cls.block.start()
        if not (TEST_SOURCE/run.PILOT[0]/'manifest.json').is_file():raise unittest.SkipTest('Corpus local ausente; configurar SICOES_HISTORICO_TEST_SOURCE')
        cls.docs,cls.checks,cls.processes=run.load(TEST_SOURCE,run.PILOT)
    @classmethod
    def tearDownClass(cls):cls.block.stop()
    def test_manual_pilot_and_independent_reader(self):
        result=check(self.docs,TEST_SOURCE,run.PACKAGE/'piloto_referencia.json')
        self.assertEqual(result['status'],'COTEJO_PILOTO_OK');self.assertEqual(result['observations_checked'],29)
        self.assertEqual(result['cells_checked'],287);self.assertEqual(result['failures'],[])
    def test_no_merge_between_phases_and_deserted_retained(self):
        observations=[o for d in self.docs for o in d['observations']]
        self.assertEqual(len({o['observation_id'] for o in observations}),29)
        deserted=[o for o in observations if o['stage']=='declaratoria_desierta']
        self.assertEqual(len(deserted),1);self.assertIn('matriciales',deserted[0]['description_visible'])
    def test_100e_inventory_only(self):
        d=next(d for d in self.docs if d['form']=='100-E')
        self.assertEqual(d['status'],'EXCLUIDO');self.assertEqual(d['observations'],[]);self.assertEqual(d['tables'],[])
    def test_form200_supplier_not_inferred_from_ambiguous_contract(self):
        for d in self.docs:
            if d['form']!='200':continue
            self.assertTrue(d['contract_context']);self.assertIn('numero_contrato_compartido',' '.join(d['warnings']))
            self.assertTrue(all(not any(f['name']=='proveedor_documentado' for f in o['fields']) for o in d['observations']))
    def test_reception_prices_match_manual_reference(self):
        prices=[o['derived'][0]['value'] for d in self.docs for o in d['observations'] if d['form']=='500']
        self.assertEqual(sorted(prices),sorted(['44.89','675','2390','3970','4880','1700']))
    def test_document_currency_has_own_cell_provenance_no_cross_form_inheritance(self):
        for d in self.docs:
            if d['form'] in ('100','110','200'):
                currency=[c for c in d['context'] if 'moneda' in p.norm(c['label'])]
                self.assertTrue(currency);self.assertIn('Bolivianos',currency[0]['value'])
                self.assertIn('value_column',currency[0]);self.assertEqual(currency[0]['scope'],'document')
            if d['form']=='500':self.assertFalse(any('moneda' in p.norm(c['label']) for c in d['context']))
    def test_mutated_value_fails_manual_and_source_content_review(self):
        import copy
        docs=copy.deepcopy(self.docs);doc=next(d for d in docs if d['form']=='110')
        f=next(f for f in doc['observations'][0]['fields'] if f['name']=='cantidad');f['raw']='999';f['normalized']['value']='999'
        result=check(docs,TEST_SOURCE,run.PACKAGE/'piloto_referencia.json')
        self.assertEqual(result['status'],'REQUIERE_REVISION');self.assertGreaterEqual(len(result['failures']),2)
    def test_repeat_is_idempotent_csv_and_observation_ids(self):
        (run.PACKAGE/'data/tests').mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=run.PACKAGE/'data/tests') as tmp:
            output=Path(tmp)
            a=run.run(TEST_SOURCE,output);csv_a=(output/'observaciones.csv').read_bytes()
            with sqlite3.connect(output/'observaciones.sqlite') as db:ids=db.execute('SELECT observation_id FROM observaciones ORDER BY observation_id').fetchall()
            b=run.run(TEST_SOURCE,output)
            self.assertEqual(a['status'],'COTEJADO_PILOTO');self.assertEqual(a['observations'],29);self.assertEqual(b['observations'],29)
            self.assertEqual(csv_a,(output/'observaciones.csv').read_bytes())
            with sqlite3.connect(output/'observaciones.sqlite') as db:
                self.assertEqual(ids,db.execute('SELECT observation_id FROM observaciones ORDER BY observation_id').fetchall())
                self.assertEqual(db.execute('SELECT count(*) FROM atributos_derivados').fetchone()[0],6)
                self.assertEqual(db.execute('SELECT count(*) FROM observaciones WHERE formulario=?',('100-E',)).fetchone()[0],0)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(len(list(csv.DictReader(io.StringIO(csv_a.decode('utf-8-sig'))))),29)
        run.assert_sources_unchanged(self.checks)
    def test_output_cannot_overlap_originals(self):
        with self.assertRaises(ValueError):run.run(TEST_SOURCE,TEST_SOURCE/'derivados')
