import unittest
from unittest.mock import patch
from scraper.historico_local import por_cuce as pc


class NormalizeTests(unittest.TestCase):
    def test_full_passthrough(self):
        self.assertEqual(pc.normalize('22-0660-10-1199042-1-2'), '22-0660-10-1199042-1-2')

    def test_short_num_defaults_to_1_1(self):
        self.assertEqual(pc.normalize('1199042', '0660-10', 2022), '22-0660-10-1199042-1-1')

    def test_short_with_explicit_suffix(self):
        self.assertEqual(pc.normalize('1199042-1-2', '0660-10', 2022), '22-0660-10-1199042-1-2')

    def test_short_without_scope_raises(self):
        with self.assertRaises(ValueError):
            pc.normalize('1199042')

    def test_short_bad_entidad_raises(self):
        with self.assertRaises(ValueError):
            pc.normalize('1199042', '066010', 2022)

    def test_short_bad_anio_raises(self):
        with self.assertRaises(ValueError):
            pc.normalize('1199042', '0660-10', 1800)

    def test_unrecognized_token_raises(self):
        with self.assertRaises(ValueError):
            pc.normalize('abc-xyz', '0660-10', 2022)


class ScopeAndGroupTests(unittest.TestCase):
    def test_derive_scope(self):
        self.assertEqual(pc.derive_scope('23-0660-11-1333011-1-1'), ('0660-11', 2023))

    def test_group_dedups_and_splits_by_scope(self):
        g = pc.group(['22-0660-10-1199042-1-2', '22-0660-10-1199042-1-2',
                      '23-0660-11-1333011-1-1'])
        self.assertEqual(g[('0660-10', 2022)], ['22-0660-10-1199042-1-2'])
        self.assertEqual(g[('0660-11', 2023)], ['23-0660-11-1333011-1-1'])

    def test_group_mixes_long_and_short(self):
        g = pc.group(['1199042', '24-0660-11-1456215-1-1'], entidad='0660-10', anio=2022)
        self.assertEqual(g[('0660-10', 2022)], ['22-0660-10-1199042-1-1'])
        self.assertEqual(g[('0660-11', 2024)], ['24-0660-11-1456215-1-1'])

    def test_group_sorts_within_scope(self):
        g = pc.group(['22-0660-10-1300000-1-1', '22-0660-10-1200000-1-1'])
        self.assertEqual(g[('0660-10', 2022)],
                         ['22-0660-10-1200000-1-1', '22-0660-10-1300000-1-1'])


class DispatchTests(unittest.TestCase):
    def test_check_lists_without_connecting(self):
        argv = ['por_cuce', '22-0660-10-1199042-1-2', '--check']
        with patch('scraper.historico_local.historico_http_directo.dependencies', return_value=object()) as dep, \
             patch('scraper.historico_local.historico_http_directo.prepare_brave') as brave, \
             patch('sys.argv', argv):
            pc.main()  # --check returns normally (no SystemExit)
        dep.assert_called_once()
        brave.assert_not_called()

    def test_capture_groups_delegate_to_run(self):
        calls = []

        async def fake_run(entidad, anio, converter, cuces, elapsed):
            calls.append((entidad, anio, tuple(cuces)))
            return 0

        argv = ['por_cuce', '22-0660-10-1199042-1-2', '23-0660-11-1333011-1-1']
        with patch('scraper.historico_local.historico_http_directo.dependencies', return_value=object()), \
             patch('scraper.historico_local.historico_http_directo.prepare_brave'), \
             patch('scraper.historico_local.historico_http_paginas.run', side_effect=fake_run), \
             patch('sys.argv', argv):
            with self.assertRaises(SystemExit) as ctx:
                pc.main()
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn(('0660-10', 2022, ('22-0660-10-1199042-1-2',)), calls)
        self.assertIn(('0660-11', 2023, ('23-0660-11-1333011-1-1',)), calls)


if __name__ == '__main__':
    unittest.main()
