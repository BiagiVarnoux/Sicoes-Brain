import unittest
from scraper.historico_local import historico_http_directo as base


class NthLinkTests(unittest.TestCase):
    def setUp(self):
        self.links = [
            {'label': 'FORM 170', 'token': 'A'},
            {'label': 'FORM 200', 'token': 'B'},
            {'label': 'FORM 170', 'token': 'C'},  # 2ª 170 (re-adjudicación)
            {'label': 'FORM 170', 'token': 'D'},  # 3ª 170
        ]

    def test_unique_label_unchanged(self):
        self.assertEqual(base.nth_link(self.links, 'FORM 200', 0), 'B')

    def test_duplicate_label_picks_by_order(self):
        self.assertEqual(base.nth_link(self.links, 'FORM 170', 0), 'A')
        self.assertEqual(base.nth_link(self.links, 'FORM 170', 1), 'C')
        self.assertEqual(base.nth_link(self.links, 'FORM 170', 2), 'D')

    def test_missing_occurrence_raises_recovery(self):
        with self.assertRaises(base.RecoveryRequired):
            base.nth_link(self.links, 'FORM 170', 3)

    def test_absent_label_raises_recovery(self):
        with self.assertRaises(base.RecoveryRequired):
            base.nth_link(self.links, 'FORM 999', 0)


class CollapseFormsTests(unittest.TestCase):
    def labels(self, forms):
        return [f['label'] for f in forms]

    def test_keeps_only_last_170_in_order(self):
        # Estructura real del portal: 100, 170 (anulado), 190, 170 (vigente), 200, 500.
        forms = [
            {'label': 'FORM 100', 'token': 'a'},
            {'label': 'FORM 170', 'token': 'anulado'},
            {'label': 'FORM 190', 'token': 'c'},
            {'label': 'FORM 170', 'token': 'vigente'},
            {'label': 'FORM 200', 'token': 'e'},
            {'label': 'FORM 500', 'token': 'f'},
        ]
        out = base.collapse_forms(forms)
        self.assertEqual(self.labels(out),
                         ['FORM 100', 'FORM 190', 'FORM 170', 'FORM 200', 'FORM 500'])
        kept = [f for f in out if f['label'] == 'FORM 170']
        self.assertEqual([f['token'] for f in kept], ['vigente'])

    def test_three_170_keeps_last(self):
        forms = [
            {'label': 'FORM 170', 'token': 'A'},
            {'label': 'FORM 170', 'token': 'C'},
            {'label': 'FORM 170', 'token': 'D'},
        ]
        self.assertEqual([f['token'] for f in base.collapse_forms(forms)], ['D'])

    def test_single_170_unchanged(self):
        forms = [{'label': 'FORM 100', 'token': 'a'}, {'label': 'FORM 170', 'token': 'b'}]
        self.assertEqual(base.collapse_forms(forms), forms)

    def test_no_170_unchanged(self):
        forms = [{'label': 'FORM 100', 'token': 'a'}, {'label': 'FORM 500', 'token': 'b'}]
        self.assertEqual(base.collapse_forms(forms), forms)


if __name__ == '__main__':
    unittest.main()
