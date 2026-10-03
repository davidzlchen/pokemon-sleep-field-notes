"""Copy only public website files, never the private working directory."""
import argparse
import shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    target = args.output.resolve()
    if target == ROOT or ROOT in target.parents:
        parser.error('Choose an output outside the repository.')
    if target.exists() and any(target.iterdir()):
        parser.error('Output directory must be empty; existing files will not be removed.')
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / 'index.html', target / 'index.html')
    shutil.copytree(ROOT / 'pokemon-sleep', target / 'pokemon-sleep')
    print('Staged public website. Serve this directory, not your private working files.')

if __name__ == '__main__':
    main()
