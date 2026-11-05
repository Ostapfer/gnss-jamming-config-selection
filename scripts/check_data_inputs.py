"""Read-only verification of separately obtained development recordings."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path)
    args = parser.parse_args()
    source = args.source_root
    if source is None:
        settings = ROOT / 'configs/local_paths.json'
        if not settings.is_file():
            parser.exit(2, 'Copy configs/local_paths.example.json to configs/local_paths.json and set source_root, or pass --source-root. No data are bundled.\n')
        source = Path(json.loads(settings.read_text())['source_root']).expanduser()
    source = source.resolve()
    failures = []
    for session in json.loads((ROOT / 'configs/sessions.json').read_text()):
        path = (source / session['path']).resolve()
        if not path.is_relative_to(source):
            raise ValueError('Session path escapes source root')
        if not path.is_file():
            failures.append(session['session_id'] + ': missing raw input')
        elif hashlib.sha256(path.read_bytes()).hexdigest() != session['sha256']:
            failures.append(session['session_id'] + ': SHA256 mismatch')
        else:
            print(session['session_id'] + ': SHA256 PASS')
    if failures:
        parser.exit(1, '\n'.join(failures) + '\nObtain the correct inputs separately; see data/README.md.\n')
    print('All development inputs verified; no files changed and no models executed.')

if __name__ == '__main__':
    main()
