import json
from pathlib import Path
import tempfile
import unittest
from sync_sleep_collection import prepare


class SyncTest(unittest.TestCase):
    def test_full_sync_and_failed_sync_preserves_last_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'public'
            private = root / 'private'
            private.mkdir()
            source = root / 'response.json'
            mon = {'pid': 1, 'num': 157, 'rank': 38, 'exp': 18929, 'nat': 10,
                   'msklv': 2, 'col': 0, 'favfl': 1, 'token': 'do-not-publish'}
            source.write_text(json.dumps({'UD': {'pokemon': {'all': {'1': mon}},
                                                'invent': {'all': {}}, 'main': {'all': {'coin': 5, 'uExp': 249}},
                                                'bestene': {'all': {'1': {'ene': 7171, 'snrnk': 3, 'vicnt': 1, 'sngm': 11000, 'private': 'do-not-publish'}}}}}))
            report = prepare(source, '2026-10-03', output, private)
            self.assertEqual(report['pokemon_count'], 1)
            inventory = json.loads((output / 'inventory.json').read_text())
            self.assertEqual(inventory['researcher_rank'], 3)
            self.assertEqual(inventory['island_bests'], [{'name': 'Greengrass Isle', 'strength': 7171,
                                                       'rank': 'Basic 3', 'area_bonus_percent': 10}])
            self.assertNotIn('do-not-publish', (output / 'inventory.json').read_text())
            before = {p.name: p.read_bytes() for p in output.glob('*.json')}
            self.assertNotIn('do-not-publish', (output / 'roster.json').read_text())
            self.assertTrue(json.loads((output / 'roster.json').read_text())['records'][0]['favorite'])
            source.write_text(json.dumps({'UD': {'pokemon': {'upd': {'1': mon}}}}))
            with self.assertRaises(ValueError):
                prepare(source, '2026-10-03', output, private)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.glob('*.json')})


if __name__ == '__main__':
    unittest.main()
