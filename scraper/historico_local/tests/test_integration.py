"""Regresiones de traslado; sin navegador, credenciales ni conexiones."""
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scraper.historico_local import brave_bootstrap as b, historico_http_directo as h, storage
from procesamiento.historico import pipeline, technical


class IntegrationTests(unittest.TestCase):
    def test_roots_profiles_and_preserved_helpers(self):
        self.assertEqual(storage.ROOT, pipeline.ROOT)
        self.assertEqual(technical.ROOT, pipeline.ROOT)
        self.assertEqual(h.PORT, 9226)
        self.assertEqual(b.PORT, 9226)
        self.assertEqual(b.profile_path(), h.PROFILE.resolve())
        self.assertTrue(technical.LEGACY.is_file())
        self.assertTrue(callable(storage.Store.start))

    def test_storage_schema_and_code_snapshot_without_pilot_launcher(self):
        (storage.PACKAGE/'data/tests').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=storage.PACKAGE/'data/tests') as tmp:
            store=storage.Store(tmp)
            try:
                store.start('test', {'network':False})
                self.assertEqual(store.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                code=store.code
                self.assertIn('Correr Sicoes Local.command',code['source_hashes'])
                self.assertIn('scraper/historico_local/schema.sql',code['source_hashes'])
                self.assertNotIn('Correr Prueba 2.command',code['source_hashes'])
            finally:
                store.close()

    def test_real_transport_reuses_only_9226_owned_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile=Path(tmp)/'profile'
            args=f'{h.BRAVE} --remote-debugging-port=9226 --user-data-dir={profile}'
            response=Mock()
            response.read.return_value=json.dumps({'webSocketDebuggerUrl':'ws://127.0.0.1:9226/devtools/browser/id'}).encode()
            opener=Mock()
            opener.open.return_value.__enter__=Mock(return_value=response)
            opener.open.return_value.__exit__=Mock(return_value=False)
            with patch.object(h,'safe_root',return_value=profile), patch.object(h.shutil,'which',return_value='/usr/sbin/lsof'), patch.object(h.subprocess,'run',return_value=Mock(returncode=0,stdout='123\n')), patch.object(h.subprocess,'check_output',return_value=args), patch.object(h.subprocess,'Popen',side_effect=AssertionError('No abrir navegador')), patch.object(h.urllib.request,'build_opener',return_value=opener):
                h.prepare_brave(timeout=1)
                opener.open.assert_called_once()
            with patch.object(h,'safe_root',return_value=profile), patch.object(h.shutil,'which',return_value='/usr/sbin/lsof'), patch.object(h.subprocess,'run',return_value=Mock(returncode=0,stdout='123\n')), patch.object(h.subprocess,'check_output',return_value=args.replace(str(profile),str(profile)+'-otro')), patch.object(h.urllib.request,'build_opener') as http:
                with self.assertRaises(RuntimeError):
                    h.prepare_brave(timeout=1)
                http.assert_not_called()

    def test_loaded_downloader_preserves_focus_protection_and_restoration(self):
        namespace=h.original_functions('primary')
        self.assertNotIn('_post',namespace)
        self.assertNotIn('supabase_post',namespace)
        # El wrapper conserva la función original en su closure, cargada por AST.
        wrapper=namespace['descargar_token']
        original=inspect.getclosurevars(wrapper).nonlocals['original_download']
        strings=[c for c in original.__code__.co_consts if isinstance(c,str)]
        self.assertTrue(any('HTMLFormElement.prototype.submit = function(){ cap(this); }' in c for c in strings))
        self.assertTrue(any('HTMLFormElement.prototype.submit = window.__dlOrig.s;' in c for c in strings))
        self.assertIn('post',original.__code__.co_names)
        self.assertIn('get',original.__code__.co_names)
        self.assertIn('remove_listener',original.__code__.co_names)


class FocusDownloaderTests(unittest.IsolatedAsyncioTestCase):
    async def download(self, fallback):
        from unittest.mock import AsyncMock
        namespace=h.original_functions('primary')
        original=inspect.getclosurevars(namespace['descargar_token']).nonlocals['original_download']
        page=Mock();context=page.context;context.pages=[page]
        page.url='https://www.sicoes.gob.bo/portal/index.php'
        page.wait_for_timeout=AsyncMock()
        api=Mock(ok=not fallback,headers={'content-type':'application/pdf'})
        api.body=AsyncMock(return_value=b'%PDF-fixture')
        context.request.post=AsyncMock(return_value=api)
        download=Mock(suggested_filename='fixture.pdf')
        callbacks={};evaluations=[];submissions=0
        def register(event,callback):callbacks[event]=callback
        page.on.side_effect=register
        async def evaluate(script):
            nonlocal submissions
            evaluations.append(script)
            if script.startswith('descargarArchivo('):
                submissions+=1
                if fallback and submissions==2:
                    callbacks['download'](download)
            if script=='() => window.__dl':
                return {'action':'/portal/download.php','method':'POST','data':{'fixture':'synthetic'}}
        page.evaluate=AsyncMock(side_effect=evaluate)
        async def save_as(path):Path(path).write_bytes(b'%PDF-fallback-fixture')
        download.save_as=AsyncMock(side_effect=save_as)
        with tempfile.TemporaryDirectory() as tmp:
            result=await original(page,'synthetic',tmp,'fixture')
            self.assertEqual(Path(result).read_bytes(),b'%PDF-fallback-fixture' if fallback else b'%PDF-fixture')
        context.request.post.assert_awaited_once()
        self.assertTrue(any('HTMLFormElement.prototype.submit = function(){ cap(this); };' in s for s in evaluations))
        self.assertIn('HTMLFormElement.prototype.submit = window.__dlOrig.s;',evaluations[-1])
        self.assertEqual(submissions,2 if fallback else 1)
        context.remove_listener.assert_called_once()
        page.remove_listener.assert_called_once()
        if not fallback:download.save_as.assert_not_awaited()

    async def test_session_http_download_without_native_window(self):
        await self.download(False)

    async def test_native_fallback_and_hook_restoration_preserved(self):
        await self.download(True)
