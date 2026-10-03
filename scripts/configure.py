"""Set the public owner name and calendar timezone without touching collection data."""
import argparse
import html
import re
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True, help='Public display name')
    parser.add_argument('--timezone', default='UTC', help='IANA timezone for date met')
    args = parser.parse_args()
    ZoneInfo(args.timezone)
    name = html.escape(args.name, quote=True)
    page = ROOT / 'pokemon-sleep/index.html'
    text = page.read_text().replace('my field notes', name).replace('My Pokémon', name + '’s Pokémon')
    page.write_text(text)
    homepage = ROOT / 'index.html'
    homepage.write_text(homepage.read_text().replace('My Pokémon', name + '’s Pokémon'))
    exporter = ROOT / 'scripts/export-sleep-roster.py'
    # This token appears exactly once in the unconfigured template.
    text = re.sub(r'ZoneInfo\([^)]*\)', lambda _: 'ZoneInfo(' + repr(args.timezone) + ')', exporter.read_text())
    exporter.write_text(text)
    print('Configured public name and calendar timezone. Review changes before publishing.')

if __name__ == '__main__':
    main()
