"""Verify packaged reference files without data downloads or model execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT/'release/file_manifest.json').read_text())
    failures = []
    for relative, expected in manifest['files'].items():
        path = ROOT/relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            failures.append(relative)
    if failures:
        raise SystemExit('Reference snapshot differs: '+', '.join(failures))
    print(f"Release snapshot verified: {len(manifest['files'])} files; no downloads or new measurements")


if __name__ == '__main__':
    main()
