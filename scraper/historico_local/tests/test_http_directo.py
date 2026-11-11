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


if __name__ == '__main__':
    unittest.main()
