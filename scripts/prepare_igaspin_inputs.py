"""Verify separately obtained UBX files and project the four ordinal NAV streams.

Offline preparation only. No model loading, fitting or resource measurement.
Prepared telemetry is private and must stay under an ignored local directory.
"""
import argparse
import calendar
import csv
import datetime
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('igaspin_adapter', ROOT/'validation/igaspin/adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def project(rows, recording, arm):
    for index, row in enumerate(rows):
        rf = row['arms'][arm]
        valid = rf['available'] and row['tAcc_ns'] != 0xffffffff
        valid = valid and all(v is not None and math.isfinite(v) for v in [rf['noise_per_ms'], row['eph']])
        yield {'session_id':recording+'__rf_ordinal_'+str(arm), 'elapsed_s':row['elapsed_s'],
               'utc_ns_exact':'ns:'+str(row['utc_ns']), 'state':'conditional_IGASPIN',
               'noise_per_ms':rf['noise_per_ms'] if valid else '', 'eph':row['eph'] if valid else '',
               'nav_offset':row['nav_offset'], 'rf_offset':rf['rf_offset'], 'observation_index':index}


def prepare(raw_root, output):
    if output.exists():
        raise FileExistsError('Use a new output directory; frozen inputs are never overwritten')
    if not output.is_relative_to(ROOT/'build'):
        raise ValueError('Store prepared receiver rows under the ignored repository build/ directory')
    manifest = json.loads((ROOT/'validation/igaspin/data_manifest.json').read_text())
    sessions, prepared, checks = [], [], []
    for item in manifest['records']:
        raw = raw_root/item['filename']
        data = raw.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != item['sha256']:
            raise ValueError('Raw input hash mismatch: '+item['filename'])
        rows = list(adapter.observations(data))
        if len(rows) != item['nav_epochs']:
            raise ValueError('Navigation epoch count differs from the declared recording')
        reference = item['provider_reference_utc']
        reference_ns = calendar.timegm(datetime.datetime.fromisoformat(reference.replace('Z','+00:00')).utctimetuple())*1_000_000_000 if reference else None
        for arm in [0,1]:
            values = list(project(rows,item['recording'],arm))
            prepared.extend(values)
            sessions.append({'session_id':values[0]['session_id'], 'attack_type':'conditional_external_resource_only',
                             'onset_us':None, 'recording':item['recording'], 'ordinal_arm':'rf_ordinal_'+str(arm),
                             'coverage_s':rows[-1]['elapsed_s'], 'expected_messages':len(rows),
                             'origin_utc_ns':rows[0]['utc_ns'], 'provider_reference_utc':reference,
                             'provider_reference_s':(reference_ns-rows[0]['utc_ns'])/1e9 if reference_ns is not None else None})
        checks.append({'filename':item['filename'], 'sha256':digest, 'nav_epochs':len(rows)})
    output.mkdir(parents=True)
    (output/'configs').mkdir()
    (output/'data/derived').mkdir(parents=True)
    with (output/'data/derived/development.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(prepared[0]));writer.writeheader();writer.writerows(prepared)
    (output/'configs/sessions.json').write_text(json.dumps(sessions,indent=2)+'\n')
    report={'input_checks':checks,'streams':len(sessions),'projected_messages':len(prepared),
            'models_loaded':False,'adapter_cost_in_resource_measurement':False,
            'physical_onset_verified':False,'historical_measurement_repeated':False}
    (output/'preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.raw_root.resolve(),a.output.resolve())
