"""Remove only the exact fictional starter snapshot; refuse any other collection."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1] / 'pokemon-sleep'
DEMO = '2000-01-01-5170989bb826'

def main():
    history = json.loads((ROOT / 'history.json').read_text())
    expected = {'snapshots': [{'id': DEMO, 'captured_at': '2000-01-01', 'file': f'snapshots/{DEMO}.json'}]}
    saved = json.loads((ROOT / 'snapshots' / f'{DEMO}.json').read_text())
    import hashlib
    content = json.dumps(saved, ensure_ascii=False, indent=2) + '\n'
    if (history != expected or hashlib.sha256(content.encode()).hexdigest()[:12] != DEMO.rsplit('-', 1)[1]
        or json.loads((ROOT / 'roster.json').read_text()) != saved['roster']
        or json.loads((ROOT / 'inventory.json').read_text()) != saved['inventory']
        or {x.name for x in (ROOT / 'snapshots').iterdir()} != {f'{DEMO}.json'}):
        raise SystemExit('Refusing to remove a real, modified, or additional collection.')
    for name in ['history.json', 'roster.json', 'inventory.json', f'snapshots/{DEMO}.json']:
        (ROOT / name).unlink()
    (ROOT / 'snapshots').rmdir()
    print('Removed the exact fictional demo. Import your own snapshot next.')

if __name__ == '__main__':
    main()
