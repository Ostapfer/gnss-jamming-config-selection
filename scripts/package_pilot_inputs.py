"""Copy a trusted, freshly prepared checkout into a NEW frozen pilot workspace.

Does not fit or unpickle models. Produces new-input provenance, never a claim
of byte-identical reconstruction of an older hardware measurement.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def package(source, destination):
    candidates = json.loads((source/'experiments/candidates.json').read_text())
    names = ['configs/experiment.json', 'configs/sessions.json', 'experiments/candidates.json',
             'data/derived/development.csv', 'src/gnss_jamming/core.py',
             'src/gnss_jamming/replay.py', 'src/gnss_jamming/benchmark.py',
             'requirements-lock.txt', 'experiments/environment.json']
    for candidate in candidates:
        name = candidate['candidate_id']
        if not name or Path(name).name != name or '/' in name or '\\' in name:
            raise ValueError('Invalid model identifier')
        names.append('experiments/models/'+name+'.pkl')
    if len(set(names)) != len(names):raise ValueError('Duplicate candidate/model path')
    missing = [n for n in names if not (source/n).is_file()]
    if missing:raise ValueError('Prepare and train in a separate checkout first; missing: '+', '.join(missing))
    if destination.exists():raise FileExistsError('Use a new destination; never overwrite frozen inputs')
    hashes = {n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in names}
    destination.mkdir(parents=True)
    workspace = destination/'workspace'
    for name in names:
        target=workspace/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source/name,target)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=hashes[name]:
            raise ValueError('Copy verification failed: '+name)
    manifest = {'purpose':'New trusted-input snapshot for a newly reproduced development pilot',
                'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'input_hashes':hashes,'model_count':len(candidates),
                'independent_validation':False,'historical_bytes_guaranteed':False,
                'limitations':['Models are development-fitted; no external validation',
                               'Input hashes detect later changes, not trustworthiness of arbitrary pickles']}
    (destination/'frozen_run_protocol.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Packaged {len(names)} verified files into {workspace}; original files unchanged')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,default=ROOT)
    p.add_argument('--destination',type=Path,required=True)
    a=p.parse_args();package(a.source_root.resolve(),a.destination.resolve())
