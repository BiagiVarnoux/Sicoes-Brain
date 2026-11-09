"""HTTP primario: no renderizado, cierre, evidencia y tiempos; sin conexiones."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock,Mock,patch
from scraper.historico_local import http_forms as f,historico_http_directo as h
from scraper.historico_local.storage import PACKAGE

CUCE='24-0660-10-1430989-1-2'
HTML=f'<table><tr><td>FORM 500 {CUCE}</td></tr></table>'

class PrimaryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.net=patch('socket.socket.connect',side_effect=AssertionError('Red prohibida'));self.net.start()
        (PACKAGE/'data/tests').mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=PACKAGE/'data/tests');self.root=Path(self.tmp.name)
    async def asyncTearDown(self):self.net.stop();self.tmp.cleanup()
    def fixture(self,status=200,body=None):
        response=Mock(status=status);response.body=AsyncMock(return_value=body or json.dumps({'data':HTML}).encode())
        future=asyncio.get_running_loop().create_future();future.set_result(response)
        event=Mock();event.value=future
        manager=Mock();manager.__aenter__=AsyncMock(return_value=event);manager.__aexit__=AsyncMock(return_value=False)
        page=Mock();page.expect_response.return_value=manager
        return page,AsyncMock(),AsyncMock()
    async def test_primary_never_reads_dom_and_measures_close(self):
        page,trigger,close=self.fixture()
        result=await f.capture_primary(page,trigger,close,CUCE,'FORM500')
        self.assertTrue(result['valid']);self.assertEqual(result['http_html'],HTML)
        self.assertNotIn('dom_html',result);self.assertNotIn('comparison',result)
        self.assertFalse(result['comparison_performed']);trigger.assert_awaited_once();close.assert_awaited_once()
        page.wait_for_selector.assert_not_called();page.evaluate.assert_not_called()
        self.assertIn('close_seconds',result['timings']);self.assertIn('response_headers_seconds',result['timings'])
    async def test_http500_preserved_without_dom_wait(self):
        page,trigger,close=self.fixture(500,b'error')
        result=await f.capture_primary(page,trigger,close,CUCE,'FORM500')
        self.assertEqual(result['raw_body'],b'error');self.assertFalse(result['valid'])
        self.assertEqual(result['recovery_reason'],'http_server_error');close.assert_awaited_once()
    async def test_invalid_json_and_wrong_cuce_not_accepted(self):
        for body in (b'{"error":"not published"}',json.dumps({'data':HTML.replace(CUCE,'other')}).encode()):
            page,trigger,close=self.fixture(body=body)
            result=await f.capture_primary(page,trigger,close,CUCE,'FORM500')
            self.assertFalse(result['valid']);self.assertIsNone(result['recovery_reason'])
    async def test_close_failure_preserves_valid_response(self):
        page,trigger,close=self.fixture();close.side_effect=RuntimeError('simulado')
        result=await f.capture_primary(page,trigger,close,CUCE,'FORM500')
        self.assertTrue(result['valid']);self.assertIn('raw_body',result);self.assertEqual(result['close_error'],'RuntimeError')
    async def test_trigger_failure_still_closes(self):
        page,trigger,close=self.fixture();trigger.side_effect=RuntimeError('simulado')
        with self.assertRaises(RuntimeError):await f.capture_primary(page,trigger,close,CUCE,'FORM500')
        close.assert_awaited_once()
    async def test_runner_primary_uses_normal_portal_function_not_old_dom_capture(self):
        page,trigger,close=self.fixture();page.evaluate=AsyncMock();page.wait_for_timeout=AsyncMock();page.wait_for_function=AsyncMock()
        row={'cuce':CUCE,'forms':[{'label':'FORM 500','token':'synthetic'}]}
        nav=h.original_functions();nav.update(_active_row=row,_active_label='FORM 500',_http_folder=self.root)
        nav['extraer_filas']=AsyncMock(return_value=[row]);nav['_cerrar_modales']=AsyncMock()
        nav['_cerrar_modal_real']=close;nav['_abrir_form_intento']=AsyncMock(side_effect=AssertionError('No DOM'))
        nav['keepalive']=AsyncMock(side_effect=AssertionError('No preventivo'))
        html=await nav['abrir_formulario_html'](page,'old')
        self.assertEqual(html,HTML);page.evaluate.assert_awaited_once_with('token=>{verFormulario(token);}','synthetic')
        nav['_abrir_form_intento'].assert_not_awaited();nav['keepalive'].assert_not_awaited();close.assert_awaited_once()
        record=json.loads(next(self.root.glob('*.json')).read_text())
        self.assertEqual(record['mode'],'http_primary');self.assertIn('timings',record)
        self.assertEqual(len(list(self.root.glob('*.dom.html'))),0)
    async def test_comparison_mode_remains_available(self):
        row={'cuce':CUCE,'forms':[{'label':'FORM 500','token':'synthetic'}]}
        nav=h.original_functions('compare');nav.update(_active_row=row,_active_label='FORM 500',_http_folder=self.root)
        nav['extraer_filas']=AsyncMock(return_value=[row])
        result={'status':200,'raw_body':json.dumps({'data':HTML}).encode(),'http_html':HTML,'dom_html':HTML,'valid':True,'comparison':{'same_visible_text':True,'same_tables':True}}
        with patch.object(h,'capture_once',new=AsyncMock(return_value=result)) as comparison,patch.object(h,'capture_primary',new=AsyncMock()) as primary:
            self.assertEqual(await nav['abrir_formulario_html'](Mock(),'synthetic'),HTML)
        comparison.assert_awaited_once();primary.assert_not_awaited()
    async def test_metrics_checkpoint_survives_failure(self):
        nav={'_timing_root':self.root,'_timing_mode':'primary','_timing_started':h.time.monotonic()}
        with self.assertRaises(RuntimeError):
            with h.timed(nav,'discovery'):raise RuntimeError('simulado')
        report=json.loads(next((self.root/'tiempos').glob('*.json')).read_text())
        self.assertEqual(report['events'][0]['status'],'FAILED');self.assertIn('discovery',report['phase_seconds'])
    async def test_process_does_not_close_owned_capture_twice(self):
        row={'cuce':CUCE,'modalidad':'CM','forms':[{'label':'FORM 500','token':'synthetic'}],'archivos':[]}
        nav={'_capture_owns_close':True,'abrir_formulario_html':AsyncMock(return_value=HTML),'_cerrar_modal_real':AsyncMock(),'keepalive':AsyncMock()}
        converter=Mock();converter.convert.return_value=Mock(text_content='texto')
        await h.process(Mock(),row,self.root,nav,converter)
        nav['_cerrar_modal_real'].assert_not_awaited();nav['keepalive'].assert_not_awaited()
        self.assertEqual({e['phase'] for e in nav['_timings']},{'form_capture','conversion'})

    async def test_waits_only_for_close_button_then_closes(self):
        page,trigger,close=self.fixture();order=[]
        async def ready():order.append('ready')
        async def closing():order.append('close')
        result=await f.capture_primary(page,trigger,closing,CUCE,'FORM500',before_close=ready)
        self.assertEqual(order,['ready','close']);self.assertIn('modal_ready_seconds',result['timings'])
        page.wait_for_selector.assert_not_called()
    async def test_missing_close_button_keeps_evidence_and_attempts_close(self):
        page,trigger,close=self.fixture();ready=AsyncMock(side_effect=TimeoutError('simulado'))
        result=await f.capture_primary(page,trigger,close,CUCE,'FORM500',before_close=ready)
        self.assertTrue(result['valid']);self.assertEqual(result['close_error'],'TimeoutError')
        self.assertIn('raw_body',result);close.assert_awaited_once()


    async def test_pdf_without_text_is_ocr_pending_success_not_navigation_failure(self):
        row={'cuce':CUCE,'modalidad':'CM','forms':[],'archivos':[{'label':'Oferta','token':'synthetic'}]}
        async def download(page,token,folder,label):
            p=Path(folder)/'oferta.pdf';p.parent.mkdir(parents=True);p.write_bytes(b'%PDF-1.4\nfixture\n%%EOF');return str(p)
        nav={'descargar_token':AsyncMock(side_effect=download),'keepalive':AsyncMock()}
        converter=Mock();converter.convert.return_value=Mock(text_content='',markdown='')
        self.assertTrue(await h.process(Mock(),row,self.root,nav,converter))
        report=json.loads((self.root/CUCE/'manifest.json').read_text())
        self.assertEqual(report['status'],'FALTA_OCR');self.assertEqual(report['pending_ocr'],['Oferta'])
        self.assertFalse(report['needs_navigation_recovery']);nav['keepalive'].assert_not_awaited()
        self.assertEqual(h.summarize(self.root,[CUCE])['pending_ocr'],1)
        self.assertEqual(h.exit_status({CUCE:report['status']}),0)
        self.assertTrue(await h.process(Mock(),row,self.root,nav,converter))
        converter.convert.assert_called_once();nav['descargar_token'].assert_awaited_once()
    async def test_empty_html_and_conversion_exception_remain_errors(self):
        converter=Mock();converter.convert.return_value=Mock(text_content='',markdown='')
        entry=h.save_original(self.root,'FORM500',HTML.encode(),'FORM500',CUCE)
        self.assertEqual(h.convert(self.root,entry,converter)['conversion'],'FAILED_CONVERSION')
        entry=h.save_original(self.root,'Oferta',b'%PDF-1.4\nfixture\n%%EOF','ANNEX',CUCE)
        converter.convert.side_effect=RuntimeError('fallo real del convertidor')
        self.assertEqual(h.convert(self.root,entry,converter)['conversion'],'FAILED_CONVERSION')
    async def test_partial_error_takes_precedence_over_ocr(self):
        self.assertEqual(h.exit_status({'a':'FALTA_OCR','b':'PARCIAL'}),2)
        self.assertEqual(h.exit_status({'a':'FALTA_OCR','b':'COMPLETA'}),0)
        self.assertEqual(h.exit_status({}),2)


class PrimaryLauncherTests(unittest.TestCase):
    def test_operational_launcher_check_and_year_scope(self):
        import os,subprocess
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);fake=root/'python';trace=root/'calls'
            fake.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$PRIMARY_TEST_TRACE"\n');fake.chmod(0o700)
            env=dict(os.environ,SICOES_LOCAL_PYTHON=str(fake),PRIMARY_TEST_TRACE=str(trace))
            launcher=h.ROOT/'Correr Sicoes Local.command'
            result=subprocess.run([str(launcher),'--check'],env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0);self.assertEqual(trace.read_text().strip(),'-B -m scraper.historico_local --check')
            trace.write_text('')
            result=subprocess.run([str(launcher)],input='0660-10\n2024\n',env=env,text=True,capture_output=True)
            self.assertEqual(result.returncode,0);command=trace.read_text()
            self.assertNotIn('--cuce',command);self.assertIn('--entidad 0660-10',command)
            self.assertIn('--anio 2024',command)
