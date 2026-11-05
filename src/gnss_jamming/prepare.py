import csv, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from .core import ROOT, FEATURES, config, sessions, read_json, write_json

def main():
    cfg = config()
    local = read_json(ROOT/'configs/local_paths.json')
    source = Path(local['source_root'])
    manifest, parts = [], []
    for s in sessions():
        f = source/s['path']
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if digest != s['sha256']: raise ValueError(f'Raw hash mismatch: {f}')
        d = pd.read_csv(f).sort_values('timestamp',kind='stable').reset_index(drop=True)
        if d.timestamp.duplicated().any(): raise ValueError('Duplicate timestamps')
        for name in FEATURES:
            d[name] = pd.to_numeric(d[name],errors='coerce')
        if ((d.satellites_used.dropna()%1)!=0).any(): raise ValueError('Fractional satellites in raw input')
        d['elapsed_s'] = (d.timestamp-d.timestamp.iloc[0])/1e6
        d['session_id'] = s['session_id']
        d['state'] = 'benign'
        if s['onset_us'] is not None: d.loc[d.timestamp>=s['onset_us'],'state']=s['attack_type']
        if s['onset_us'] is not None and s['onset_us'] <= int(d.timestamp.iloc[0])+cfg['calibration_s']*1e6:
            raise ValueError(f"Outside operating conditions: attack during clean calibration in {s['session_id']}")
        d['target_jamming'] = (d.state=='jamming').astype(int)
        dt = d.timestamp.diff().dropna()/1e6
        cal = d.loc[d.elapsed_s<=cfg['calibration_s'], FEATURES]
        manifest.append({**s,'rows':len(d),'start_us':int(d.timestamp.iloc[0]),'last_us':int(d.timestamp.iloc[-1]),'duration_s':float(d.elapsed_s.iloc[-1]),'median_interval_s':float(dt.median()),'max_interval_s':float(dt.max()),'calibration_valid_rows':int(np.isfinite(cal.to_numpy()).all(axis=1).sum()),'clean_calibration_available':s['onset_us'] is None or s['onset_us']>d.timestamp.iloc[0]+cfg['calibration_s']*1e6,'attack_end_policy':'unknown; label until recording end; end right-censored'})
        parts.append(d[['timestamp','elapsed_s','session_id','state','target_jamming']+FEATURES])
    data = pd.concat(parts, ignore_index=True)
    (ROOT/'data/derived').mkdir(exist_ok=True)
    data.to_csv(ROOT/'data/derived/development.csv',index=False)
    pd.DataFrame(manifest).to_csv(ROOT/'data/manifest.csv',index=False)
    data.groupby(['session_id','state']).size().rename('raw_count').to_csv(ROOT/'results/tables/raw_counts.csv')
    write_json(ROOT/'experiments/data_check.json', {'input_hashes_verified':True,'interpolation':False,'rows':len(data),'onset_semantics':'annotated transition; physical jammer-on unknown'})
    print('Prepared',len(data),'raw rows; no rows interpolated or dropped')
if __name__=='__main__': main()
