"""Preparación probada con SO, HTTP y procesos simulados: jamás abre Brave."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from scraper.historico_local import brave_bootstrap as b

class BootstrapTests(unittest.TestCase):
    def test_exact_command_profile_and_port(self):
        p=Path('/tmp/Perfil experimental')
        good=f'Brave --remote-debugging-port=9226 --user-data-dir={p}'
        self.assertTrue(b.command_matches(good,p))
        for bad in (good+'-otro',good.replace('9226','9222'),good+' --user-data-dir=/otro'):
            self.assertFalse(b.command_matches(bad,p))

    def test_foreign_executable_or_profile_rejected(self):
        p=Path('/tmp/profile')
        for paths,args in ((['/usr/bin/python'],'--remote-debugging-port=9226 --user-data-dir=/tmp/profile'),
                           ([str(b.BRAVE)],'--remote-debugging-port=9226 --user-data-dir=/tmp/otro')):
            with patch.object(b,'process_identity',return_value=(paths,args)):
                with self.assertRaises(b.PreparationError):b.authorize_listener([123],p)

    def test_verify_owner_before_http(self):
        with patch.object(b,'profile_path',return_value=Path('/tmp/profile')),patch.object(b,'listeners',return_value=[1]),patch.object(b,'authorize_listener',side_effect=b.PreparationError('ajeno')),patch.object(b,'fetch_version') as http:
            with self.assertRaises(b.PreparationError):b.verify_ready()
            http.assert_not_called()

    def prepare_mock(self,*,occupied=False,foreign=False,timeout=False,reuse=False,interrupt=False):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            with contextlib.ExitStack() as stack:
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                stack.enter_context(patch.object(b,'safe_root',return_value=folder))
                stack.enter_context(patch.object(b,'profile_path',return_value=folder/'profile'))
                stack.enter_context(patch.object(b,'listeners',side_effect=(lambda:[1] if foreign or reuse else []) if timeout or occupied or foreign or reuse else [[],[1]]))
                stack.enter_context(patch.object(b,'port_is_occupied',return_value=occupied))
                auth=stack.enter_context(patch.object(b,'authorize_listener',side_effect=b.PreparationError('ajeno') if foreign else None))
                http=stack.enter_context(patch.object(b,'fetch_version',return_value={'browser':'Chrome/1','protocol_version':'1.3'}))
                spawn=stack.enter_context(patch.object(b,'spawn',return_value=Mock(pid=321),side_effect=KeyboardInterrupt if interrupt else None))
                stack.enter_context(patch.object(b.time,'monotonic',side_effect=[0,2,3]))
                stack.enter_context(patch.object(b.time,'sleep'))
                if occupied or foreign or timeout or interrupt:
                    with self.assertRaises((b.PreparationError,KeyboardInterrupt)):b.prepare(timeout=1)
                else:b.prepare(timeout=1)
                record=json.loads(next(folder.glob('*.json')).read_text())
                self.assertFalse(record['capture_started'])
                if occupied or foreign:
                    spawn.assert_not_called();http.assert_not_called()
                if timeout:http.assert_not_called()
                if not (occupied or foreign or timeout or interrupt):
                    auth.assert_called();http.assert_called_once();spawn.assert_called_once()
                return record

    def test_new_browser_ready(self):self.assertEqual(self.prepare_mock()['status'],'ready')
    def test_reuse_authorized_browser(self):self.assertEqual(self.prepare_mock(reuse=True)['status'],'ready')
    def test_foreign_port_archives_failure(self):self.assertEqual(self.prepare_mock(foreign=True)['status'],'failed')
    def test_unidentifiable_occupied_port(self):self.assertEqual(self.prepare_mock(occupied=True)['status'],'failed')
    def test_timeout_archives_failure(self):self.assertEqual(self.prepare_mock(timeout=True)['status'],'failed')
    def test_interrupt_archives_state(self):self.assertEqual(self.prepare_mock(interrupt=True)['status'],'interrupted')

    def test_spawn_exact_flags_without_real_process(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);exe=root/'Brave';exe.touch()
            with patch.object(b,'BRAVE',exe),patch.object(b.subprocess,'Popen') as popen:
                b.spawn(root/'profile',root/'log',True)
                self.assertEqual(popen.call_args.args[0],[str(exe),'--remote-debugging-port=9226',f'--user-data-dir={root}/profile',b.PORTAL])

    def test_missing_brave_does_not_spawn(self):
        with patch.object(b,'BRAVE',Path('/nonexistent/prueba2/Brave')),patch.object(b.subprocess,'Popen') as spawn:
            with self.assertRaises(b.PreparationError):b.spawn(Path('/tmp/unused'),Path('/tmp/unused.log'),True)
            spawn.assert_not_called()

    def test_cdp_json_validation_without_http(self):
        for body,valid in (({'Browser':'Chrome/1','webSocketDebuggerUrl':'ws://127.0.0.1:9226/devtools/browser/id'},True),
                           ({'Browser':'Chrome/1','webSocketDebuggerUrl':'ws://127.0.0.1:9222/devtools/browser/id'},False),
                           ({'error':'captcha'},False),([],False)):
            response=Mock(status=200);response.read.return_value=json.dumps(body).encode()
            opener=Mock();opener.open.return_value.__enter__=Mock(return_value=response);opener.open.return_value.__exit__=Mock(return_value=False)
            with patch.object(b.urllib.request,'build_opener',return_value=opener):
                if valid:self.assertEqual(b.fetch_version()['browser'],'Chrome/1')
                else:
                    with self.assertRaises(b.PreparationError):b.fetch_version()

if __name__=='__main__':unittest.main()
