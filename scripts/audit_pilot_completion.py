"""Read-only workload/exit adjudication of a completed pilot; never rewrites trials."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def read(path):return json.loads(path.read_text())
def lines(path):return [json.loads(line) for line in path.read_text().splitlines()]


def audit(root, output):
    rows=[];hashes={}
    for trial in sorted((root/'trials').glob('pilot_*')):
        names=['attempt_result.json','spec.json','summary.json','trace.ndjson','source.ndjson',
               'driver_status.json','inspect.detector.json','inspect.driver.json','clock.json','identities.json']
        for name in names:
            path=trial/name;hashes[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
        a=read(trial/'attempt_result.json');s=read(trial/'summary.json');spec=read(trial/'spec.json')
        trace=lines(trial/'trace.ndjson');source=lines(trial/'source.ndjson');n=spec['expected_messages']
        results=[x for x in trace if x['kind']=='result'];complete=[x for x in trace if x['kind']=='complete']
        phases={x['phase'] for x in trace if x['kind']=='lifecycle'}
        checks={'exact_result_sequence':[x['sequence'] for x in results]==list(range(n)),
                'exact_source_sequence':[x['sequence'] for x in source]==list(range(n)),
                'source_all_accepted':all(x['accepted'] for x in source),
                'exactly_one_complete':len(complete)==1,
                'complete_after_results':bool(complete) and trace[-1]['kind']=='complete' and complete[0]['processed']==n,
                'all_lifecycle_markers':{'before_imports','after_imports','after_model_load','after_calibration','final'}<=phases,
                'summary_evidence_complete':s['evidence_complete'],
                'source_schedule_valid':s['source_schedule_valid'],
                'no_drops':s['dropped_messages']==0,
                'driver_clean':not read(trial/'driver_status.json')['errors'] and a['container_states']['driver']['ExitCode']==0}
        state=a['container_states']['detector']
        memory=[x.get('cgroup',{}).get('memory.events',{}) for x in trace if x['kind']=='lifecycle']
        no_oom=not state['OOMKilled'] and all(x.get('oom',0)==0 and x.get('oom_kill',0)==0 for x in memory)
        eligible=all(checks.values())
        rows.append({'trial':trial.name,'config_id':a['config_id'],'profile_id':a['profile_id'],
            'session_id':a['session_id'],'original_status':a['status'],'expected_messages':n,
            'processed_messages':len(results),'workload_integrity_pass':eligible,
            'detector_exit_code':state['ExitCode'],'no_oom_observed':no_oom,
            'adjudicated_workload_status':'WORKLOAD_COMPLETE' if eligible else 'INCOMPLETE_OR_INVALID',
            'adjudicated_termination_status':'EXIT_ZERO' if state['ExitCode']==0 else 'ABNORMAL_OR_CLEANUP_AFFECTED_EXIT',
            'measurement_use':'recording-window metrics with exit caveat' if eligible else 'exclude pending investigation',
            'checks':checks})
    output.mkdir(parents=True,exist_ok=False)
    doc={'scope':'Post-hoc workload integrity and lifecycle adjudication; original statuses unchanged',
         'attempts':len(rows),'workload_integrity_pass':sum(x['workload_integrity_pass'] for x in rows),
         'exit_zero':sum(x['detector_exit_code']==0 for x in rows),
         'exit_nonzero':sum(x['detector_exit_code']!=0 for x in rows),
         'no_oom_observed':all(x['no_oom_observed'] for x in rows),'trials':rows,
         'source_artifact_sha256':hashes,'independent_validation':False,
         'limitation':'Historical signal sender not recorded. No claim of clean shutdown for abnormal exits. CPU/RAM coverage ends with driver monitor; sampled max is not kernel peak.'}
    (output/'audit.json').write_text(json.dumps(doc,indent=2)+'\n')
    keys=[k for k in rows[0] if k!='checks']
    with (output/'trials.csv').open('w') as h:
        w=csv.DictWriter(h,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
    print(json.dumps({k:v for k,v in doc.items() if k not in ['trials','source_artifact_sha256']},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();audit(a.run_root,a.output)
