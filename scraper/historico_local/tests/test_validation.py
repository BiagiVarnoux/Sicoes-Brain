import unittest
from scraper.historico_local import parsing

CUCE="24-0660-10-1449810-1-1"

def html(cuce=CUCE,empty=False):
    row='<tr><td colspan="5">No Existen Registros</td></tr>' if empty else '<tr><td>1</td><td>14111504</td><td>Papel bond</td><td>0</td><td>1,000</td></tr>'
    return f'<html><h1>FORM110 {cuce}</h1><table><tr><td colspan="5">DETALLE DE BIENES REQUERIDOS</td></tr><tr><td>#</td><td>Código del Catálogo</td><td>Descripción del bien</td><td>Cantidad</td><td>Precio referencial unitario</td></tr>{row}</table></html>'.encode()

class ParsingTests(unittest.TestCase):
    def test_captcha_json_never_document(self):
            r=parsing.validate(b'{"ERROR":1,"DESCERROR":"captcha invalido"}','DBC',CUCE)
            self.assertFalse(r['valid']);self.assertEqual(r['detected_type'],'json');self.assertIn('captcha',r['errors'])

    def test_wrong_cuce_or_kind_rejected(self):
            self.assertFalse(parsing.validate(html('24-0660-10-9999999-1-1'),'FORM110',CUCE)['valid'])
            self.assertFalse(parsing.validate(html(),'FORM220',CUCE)['valid'])
            self.assertTrue(parsing.validate(html(),'FORM110',CUCE)['valid'])

    def test_zero_and_ambiguous_numbers_preserved(self):
            self.assertEqual(parsing.number('0')['value'],'0')
            self.assertEqual(parsing.number('3,090.00')['value'],'3090.00')
            self.assertEqual(parsing.number('1539,99')['value'],'1539.99')
            self.assertEqual(parsing.number('1,000')['status'],'ambiguous_separator')
            self.assertEqual(parsing.number('-5')['value'],'-5')

    def test_all_rows_and_raw_fields_retained(self):
            result,md=parsing.parse_html(html(),'FORM110',CUCE,'v1')
            self.assertEqual(result['raw_rows'],3)
            self.assertEqual(result['item_rows'],1)
            r=next(r for r in result['rows'] if r['is_item_record'])
            self.assertEqual(r['fields'][3]['raw'],'0');self.assertEqual(r['fields'][4]['raw'],'1,000')
            self.assertIn('Papel bond',md)
            other,_=parsing.parse_html(html(),'FORM110',CUCE,'v2')
            self.assertNotEqual(r['observation_id'],next(r for r in other['rows'] if r['is_item_record'])['observation_id'])

    def test_empty_and_unmapped_are_distinct(self):
            r,_=parsing.parse_html(html(empty=True),'FORM110',CUCE,'v')
            self.assertEqual(r['status'],'CAPTURED_NO_RECORDS')
            r,_=parsing.parse_html(f'<table><tr><td>{CUCE}</td></tr></table>'.encode(),'FORM110',CUCE,'v')
            self.assertEqual(r['status'],'PARSED_PARTIAL')

