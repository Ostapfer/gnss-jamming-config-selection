"""Check the tracked publication file set; never inspect ignored private data."""
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {'.pdf', '.docx', '.doc', '.eml', '.msg', '.ubx', '.ulg', '.bag', '.pcap', '.pcapng', '.xlsx', '.xls', '.zip', '.gz', '.tgz', '.7z', '.rar', '.parquet', '.arrow', '.npy', '.npz', '.h5', '.hdf5', '.pkl', '.joblib', '.onnx', '.pt', '.pth', '.ckpt', '.bin', '.iq', '.sigmf-data'}
PREFIXES = ('data/raw/', 'data/derived/', 'data/external/', 'data/private/', 'experiments/models/', 'docker/artifacts/', 'integrations/', '.agents/')

def main():
    proc = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True)
    names = [name for name in proc.stdout.decode().split('\0') if name]
    failures = []
    for name in names:
        p = ROOT / name
        if p.suffix.lower() in FORBIDDEN or name.startswith(PREFIXES) or '/incoming/' in name or p.name in {'.env', '.env.local', 'local_paths.json'}:
            failures.append(name + ': private/data/model file type or location')
        if p.suffix.lower() == '.csv' and not (name == 'data/manifest.csv' or name.startswith(('results/', 'validation/'))):
            failures.append(name + ': CSV outside metadata/aggregate allow-list')
        if not p.is_file():
            failures.append(name + ': tracked file missing')
            continue
        if p.suffix.lower() == '.csv':
            import csv
            with p.open(newline='') as stream:
                header = set(next(csv.reader(stream), []))
            if header & {'noise_per_ms', 'noisePerMS', 'eph', 'epv', 'hAcc', 'vAcc', 'lat', 'lon', 'latitude', 'longitude'}:
                failures.append(name + ': receiver observation columns are excluded')
        if p.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
            continue
        text = p.read_text(errors='replace')
        # Construct path markers to avoid matching this scanner's own source.
        if ('/' + 'Users/') in text or ('file' + '://') in text:
            failures.append(name + ': personal filesystem path')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            failures.append(name + ': private key marker')
        if re.search('[\u0400-\u04ff]', text):
            failures.append(name + ': non-English Cyrillic text')
    if failures:
        raise SystemExit('Publication check failed:\n' + '\n'.join(failures))
    print(f'Publication file-set check PASS: {len(names)} tracked files. No prohibited data/model paths or personal-path/private-key markers; English text check passed.')
    print('This is a deterministic file-set check, not a licence determination or exhaustive secret/content audit. Review newly added aggregate outputs before publication.')

if __name__ == '__main__':
    main()
