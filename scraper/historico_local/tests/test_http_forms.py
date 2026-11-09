import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock,Mock,patch
from scraper.historico_local import http_forms as h

CUCE='24-0660-10-1430989-1-2'
HTML=f'<div><table><tr><td>FORM 500 {CUCE}</td></tr></table></div>'

class HTTPFormsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.net=patch('socket.socket.connect',side_effect=AssertionError('Sin red'));self.net.start()
    async def asyncTearDown(self):self.net.stop()
    def test_observed_contract(self):
        self.assertEqual(h.extract_html(json.dumps({'data':HTML})),HTML)
        with self.assertRaises(ValueError):h.extract_html('{"data":{"data":"x"}}')
    def test_comparison_preserves_changes_and_duplicates(self):
        self.assertTrue(h.compare(HTML,'<html>'+HTML+'</html>')['same_tables'])
        self.assertFalse(h.compare(HTML,HTML.replace('500','110'))['same_tables'])
        self.assertFalse(h.compare(HTML,HTML+HTML)['same_tables'])
    def test_endpoint_ignores_other_hosts(self):
        self.assertFalse(h.endpoint('https://other.example/verFormulario.php'))
        self.assertTrue(h.endpoint('https://www.sicoes.gob.bo/portal/contrataciones/verFormulario.php'))
    def setup_capture(self,status=200,body=None):
        response=Mock(status=status);response.body=AsyncMock(return_value=body if body is not None else json.dumps({'data':HTML}).encode())
        future=asyncio.get_running_loop().create_future();future.set_result(response)
        event=Mock();event.value=future
        manager=Mock();manager.__aenter__=AsyncMock(return_value=event);manager.__aexit__=AsyncMock(return_value=False)
        page=Mock();page.expect_response.return_value=manager
        return page,AsyncMock(return_value=HTML),AsyncMock()
    async def test_healthy_capture_no_keepalive_or_new_requests(self):
        page,opening,closing=self.setup_capture()
        result=await h.capture_once(page,opening,closing,CUCE,'FORM500')
        self.assertTrue(result['valid']);self.assertTrue(result['comparison']['same_tables'])
        opening.assert_awaited_once();closing.assert_awaited_once()
        page.request.post.assert_not_called();page.evaluate.assert_not_called()
    async def test_server_error_classified_not_retried(self):
        page,opening,closing=self.setup_capture(500,b'error')
        result=await h.capture_once(page,opening,closing,CUCE,'FORM500')
        self.assertEqual(result['recovery_reason'],'http_server_error');self.assertFalse(result['valid'])
        opening.assert_awaited_once();closing.assert_awaited_once()
    async def test_missing_or_invalid_document_not_session_failure(self):
        for body in (b'{"data":"No publicado"}',b'{"error":"not found"}'):
            page,opening,closing=self.setup_capture(body=body)
            result=await h.capture_once(page,opening,closing,CUCE,'FORM500')
            self.assertFalse(result['valid']);self.assertIsNone(result['recovery_reason'])
    async def test_close_on_exception(self):
        page,opening,closing=self.setup_capture();opening.side_effect=RuntimeError('simulado')
        result=await h.capture_once(page,opening,closing,CUCE,'FORM500')
        self.assertFalse(result['valid']);self.assertEqual(result['error'],'RuntimeError')
        self.assertIn('raw_body',result)
        closing.assert_awaited_once()
    def test_har_summary_does_not_expose_parameters(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'fixture.har'
            p.write_text(json.dumps({'log':{'entries':[{'request':{'url':'https://www.sicoes.gob.bo/portal/verFormulario.php?token=secret'},'response':{'status':200,'content':{'text':json.dumps({'data':HTML})}}}]}}))
            summary=h.analyze_har(p)
            self.assertEqual(summary['counts']['json_data_html'],1)
            self.assertNotIn('secret',json.dumps(summary));self.assertNotIn(CUCE,json.dumps(summary))
    async def test_close_failure_keeps_received_body(self):
        page,opening,closing=self.setup_capture();closing.side_effect=RuntimeError('modal abierto')
        result=await h.capture_once(page,opening,closing,CUCE,'FORM500')
        self.assertTrue(result['valid']);self.assertEqual(result['close_error'],'RuntimeError')
        self.assertIn('raw_body',result)
