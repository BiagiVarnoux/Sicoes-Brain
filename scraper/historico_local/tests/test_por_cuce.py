import unittest
from unittest.mock import patch
from scraper.historico_local import por_cuce as pc


class ParseTests(unittest.TestCase):
    def test_num_only_defaults_variant(self):
        self.assertEqual(pc.parse_entry('1199042'), ('1199042', '1', '1'))

    def test_num_with_explicit_variant(self):
        self.assertEqual(pc.parse_entry('1199042-1-2'), ('1199042', '1', '2'))

    def test_variant_two_one(self):
        self.assertEqual(pc.parse_entry('1456215-2-1'), ('1456215', '2', '1'))

    def test_full_cuce_uses_tail_only(self):
        self.assertEqual(pc.parse_entry('22-0660-10-1199042-1-2'), ('1199042', '1', '2'))

    def test_full_cuce_default_variant(self):
        self.assertEqual(pc.parse_entry('23-0660-11-1333011-1-1'), ('1333011', '1', '1'))

    def test_junk_raises(self):
        for bad in ('abc', '1199042-1', '-1-2', ''):
            with self.assertRaises(ValueError):
                pc.parse_entry(bad)

    def test_parse_all_dedups_keeping_order(self):
        got = pc.parse_all(['1199042-1-2', '1199042-1-2', '1333011',
                            '22-0660-10-1199042-1-2'])
        self.assertEqual(got, [('1199042', '1', '2'), ('1333011', '1', '1')])


class ScopeTests(unittest.TestCase):
    def test_scope_of(self):
        self.assertEqual(pc.scope_of('23-0660-11-1333011-1-1'), ('0660-11', 2023))
        self.assertEqual(pc.scope_of('22-0660-10-1199042-1-2'), ('0660-10', 2022))


class DispatchTests(unittest.TestCase):
    def test_check_lists_without_connecting(self):
        argv = ['por_cuce', '1199042-1-2', '1333011', '--check']
        with patch('scraper.historico_local.historico_http_directo.dependencies',
                   return_value=object()) as dep, \
             patch('scraper.historico_local.historico_http_directo.prepare_brave') as brave, \
             patch('sys.argv', argv):
            pc.main()  # --check returns normally (no SystemExit)
        dep.assert_called_once()
        brave.assert_not_called()

    def test_capture_receives_parsed_entries(self):
        seen = {}

        async def fake_capture(entries, converter, startup, forms_map=None, forms_default=None):
            seen['entries'] = entries
            seen['forms_map'] = forms_map
            seen['forms_default'] = forms_default
            return 0

        argv = ['por_cuce', '1199042-1-2', '23-0660-11-1333011-1-1']
        with patch('scraper.historico_local.historico_http_directo.dependencies',
                   return_value=object()), \
             patch('scraper.historico_local.historico_http_directo.prepare_brave'), \
             patch('scraper.historico_local.por_cuce.capture', side_effect=fake_capture), \
             patch('sys.argv', argv):
            with self.assertRaises(SystemExit) as ctx:
                pc.main()
        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(seen['entries'],
                         [('1199042', '1', '2'), ('1333011', '1', '1')])
        # Sin flags de forms: comportamiento intacto (captura todo).
        self.assertIsNone(seen['forms_default'])
        self.assertEqual(seen['forms_map'], {})

    def _run_main(self, argv):
        seen = {}

        async def fake_capture(entries, converter, startup, forms_map=None, forms_default=None):
            seen.update(entries=entries, forms_map=forms_map, forms_default=forms_default)
            return 0

        with patch('scraper.historico_local.historico_http_directo.dependencies',
                   return_value=object()), \
             patch('scraper.historico_local.historico_http_directo.prepare_brave'), \
             patch('scraper.historico_local.por_cuce.capture', side_effect=fake_capture), \
             patch('sys.argv', argv):
            with self.assertRaises(SystemExit) as ctx:
                pc.main()
        self.assertEqual(ctx.exception.code, 0)
        return seen

    def test_solo_form500_sets_default(self):
        seen = self._run_main(['por_cuce', '1199042-1-2', '--solo-form500'])
        self.assertEqual(seen['forms_default'], {'500'})
        self.assertEqual(seen['forms_map'], {})

    def test_forms_flag_parses_csv(self):
        seen = self._run_main(['por_cuce', '1199042-1-2', '--forms', '100,200,500'])
        self.assertEqual(seen['forms_default'], {'100', '200', '500'})

    def test_forms_file_maps_per_cuce(self):
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix='.txt')
        try:
            os.write(fd, b'# comentario\n22-0660-10-1199042-1-2  500\n1333011-1-1 100,500\n')
            os.close(fd)
            seen = self._run_main(['por_cuce', '--forms-file', path])
        finally:
            os.unlink(path)
        self.assertEqual(seen['entries'],
                         [('1199042', '1', '2'), ('1333011', '1', '1')])
        self.assertEqual(seen['forms_map'], {'1199042': {'500'}, '1333011': {'100', '500'}})
        self.assertIsNone(seen['forms_default'])


if __name__ == '__main__':
    unittest.main()
