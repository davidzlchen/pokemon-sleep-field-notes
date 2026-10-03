"""Generate a fictional demo, never the original author's account data."""
import json
import tempfile
from pathlib import Path
from sync_sleep_collection import prepare
ROOT = Path(__file__).resolve().parents[1]

def main():
    output = ROOT / 'pokemon-sleep'
    if (output / 'history.json').exists():
        raise SystemExit('Demo refuses to replace an existing collection. Use a fresh clone.')
    # Fictional stats with valid game IDs, not copied from any real account.
    mon = {'pid': 1, 'num': 157, 'rank': 1, 'exp': 0, 'nat': 10,
           'msklv': 0, 'col': 0, 'favfl': 0, 'nam': 'Demo helper',
           'sbski': [7, 13, 9, 15, 14], 'pic': [{'item': '7', 'typ': 4, 'num': 2}]}
    reference = json.loads((output / 'inventory-reference.json').read_text())
    # Four fictional island records exercise the full layout without owner data.
    islands = {field: {'ene': reference['island_ranks'][field]['ranks'][2]['strength'],
                       'snrnk': reference['island_ranks'][field]['ranks'][2]['id'],
                       'vicnt': 1, 'sngm': 10000 + bonus * 100}
               for field, bonus in [('1', 10), ('2', 15), ('3', 20), ('4', 5)]}
    with tempfile.TemporaryDirectory() as directory:
        private = Path(directory)
        source = private / 'demo.json'
        source.write_text(json.dumps({'UD': {'pokemon': {'all': {'1': mon}},
                                             'invent': {'all': {}}, 'main': {'all': {'coin': 0, 'uExp': 249}},
                                             'bestene': {'all': islands}}}))
        print(json.dumps(prepare(source, '2000-01-01', output, private)))

if __name__ == '__main__':
    main()
