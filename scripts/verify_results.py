"""Validate the current frozen development run and write its artifact manifest."""
from pathlib import Path
import sys, hashlib, json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
from gnss_jamming.core import ROOT,config,read_json,write_json,sessions
from gnss_jamming.summarize import configuration_library,current_completed_runs,accepted_realtime


def main():
    cfg=config(); library=configuration_library(read_json(ROOT/'experiments/candidates.json'),cfg)
    data=pd.read_csv(ROOT/'data/derived/development.csv')
    resource=read_json(ROOT/'experiments/resource_run.json')
    assert resource.get('protocol_version')==cfg['protocol_version'],'resource protocol mismatch'
    assert resource.get('input_hashes'),'missing resource provenance'
    assert all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest for path,digest in resource['input_hashes'].items()),'stale resource inputs/code'
    r=pd.read_csv(ROOT/'results/tables/resources.csv'); cond=pd.read_csv(ROOT/'results/tables/resources_by_condition.csv');cal=pd.read_csv(ROOT/'results/tables/resource_calibration.csv')
    assert set(r.config_id)==set(library.config_id) and not r.config_id.duplicated().any()
    ncal=int((data.elapsed_s<=cfg['calibration_s']).sum());npost=len(data)-ncal
    assert r.calibration_messages.eq(ncal).all() and r.measured_messages.eq(npost).all()
    assert all(set(g.condition)=={'benign','jamming','spoofing'} for _,g in cond.groupby('config_id'))
    gates=pd.concat([cond[['config_id','pipeline_p95_ms']],cal[['config_id','calibration_p95_ms']].rename(columns={'calibration_p95_ms':'pipeline_p95_ms'})]).groupby('config_id').pipeline_p95_ms.max()
    assert np.allclose(r.set_index('config_id').pipeline_p95_ms.sort_index(),gates.sort_index())
    records=current_completed_runs(ROOT/'results/tables/realtime_runs.jsonl')
    latest={}
    for record in records:
        if record.get('status')=='complete':latest[record['config_id'],record['session_id']]=record
    expected={(cid,s['session_id']) for cid in cfg['realtime_config_ids'] for s in sessions()}
    assert expected.issubset(latest),'not all declared isolated configuration/session pairs completed'
    assert all('fresh spawned process' in latest[key]['consumer'] for key in expected)
    m=accepted_realtime(pd.read_csv(ROOT/'results/tables/realtime_metrics.csv'),{},records)
    measured=set(m.config_id);assert set(cfg['realtime_config_ids']).issubset(measured)
    scenarios=pd.read_csv(ROOT/'results/tables/scenarios.csv')
    op=scenarios[scenarios['mode']=='realtime']
    assert op[~op.config_id.isin(measured)].empirical.eq('NOT EVALUABLE').all()
    assert scenarios.evidence.eq('INSUFFICIENT EVIDENCE').all()
    assert op[op.config_id.isin(cfg['realtime_config_ids'])].tested_count.eq(len(set(m.loc[m.eligible_episode,'session_id']))).all()
    front=pd.read_csv(ROOT/'results/tables/pareto.csv');assert front.empirical.eq('PASS').all() and np.isfinite(front.delay_s).all()
    t=pd.read_csv(ROOT/'results/tables/realtime_timings.csv');accepted_ids={r['run_id'] for r in latest.values()};t=t[t.run_id.isin(accepted_ids)]
    assert (t.processing_end_time>=t.processing_start_time).all()
    assert (t.end_to_end_ms+1e-6>=t.processing_ms).all() and t.queue_ms.ge(0).all()
    assert np.allclose(t.end_to_end_ms,t.queue_ms+t.processing_ms,atol=1e-5)
    stress=pd.read_csv(ROOT/'results/tables/stress.csv')
    assert stress.messages.eq(cfg['benchmark']['stress_messages']).all()
    assert stress.scheduled_to_ready_deadline_misses.ge(stress.actual_arrival_deadline_misses).all()
    maintained=((stress.actual_offered_hz/stress.requested_hz-1).abs()<=.05)&(stress.producer_lateness_p95_ms<=stress.deadline_ms)
    assert maintained.eq(stress.offered_rate_maintained).all()
    aggregate=[]
    for (cid,sid),part in t.groupby(['config_id','session_id']):
        row={'config_id':cid,'session_id':sid}
        for col in ['queue_ms','processing_ms','end_to_end_ms','model_only_ms','producer_lateness_ms']:
            for quantile in [.5,.95,.99]:row[f'{col}_p{int(quantile*100)}']=float(part[col].quantile(quantile))
        aggregate.append(row)
    pd.DataFrame(aggregate).to_csv(ROOT/'results/tables/realtime_latency_summary.csv',index=False)
    result={'protocol_version':cfg['protocol_version'],'run_id':cfg['run_id'],'resource_configurations':len(r),'raw_rows_per_configuration':len(data),'calibration_rows':ncal,'postcalibration_rows':npost,'execution_configurations':len(measured),'completed_required_pairs':len(expected),'unmeasured_operational_configurations':len(library)-len(measured),'all_evidence':'INSUFFICIENT EVIDENCE','resource_hashes_current':True,'replay_hashes_current':True,'full_required_replays_complete':True,'fresh_environment_install_tested':False,'stress_valid_offered_rate_trials':int(maintained.sum()),'stress_trials':len(stress)}
    write_json(ROOT/'experiments/verification.json',result)
    files=[]
    for folder in ['src','scripts','configs','results','tests','docs']:
        files += [f for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.name!='local_paths.json']
    files += [ROOT/'README.md',ROOT/'PROJECT_STATE.md',ROOT/'data/manifest.csv',ROOT/'requirements-lock.txt',ROOT/'experiments/verification.json',ROOT/'experiments/test_run.json',ROOT/'experiments/resource_run.json',ROOT/'experiments/information_clock_development_run.json']
    write_json(ROOT/'experiments/artifact_hashes.json',{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(files)})
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
