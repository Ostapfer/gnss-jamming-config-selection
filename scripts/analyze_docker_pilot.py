"""Analyze a frozen completed pilot without training, replay or trial mutation.

Recording-level quantiles stay separate. Any maximum-of-quantiles screening
summary is explicitly labelled; it is not a pooled percentile or confidence bound.
"""
import argparse
from collections import defaultdict
import csv
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics


def load(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def records(p):
    with p.open() as f:
        return [json.loads(line) for line in f if line.strip()]

def quantile(values, q):
    values=sorted(values)
    if not values:return None
    pos=(len(values)-1)*q; lo=math.floor(pos); hi=math.ceil(pos)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)

def queue_sweep(accepted, starts):
    """Exact waiting process: accepted but not started; simultaneous deltas grouped."""
    changes=defaultdict(int)
    for t in accepted:changes[t]+=1
    for t in starts:changes[t]-=1
    count=peak=0; integral=nonempty=0.; previous=None
    for t,delta in sorted(changes.items()):
        if previous is not None:
            integral+=count*(t-previous)
            if count:nonempty+=t-previous
        count+=delta
        if count<0:raise ValueError('Processing preceded corresponding acceptance')
        peak=max(peak,count);previous=t
    if count:raise ValueError('Accepted work remains unprocessed')
    return {'waiting_queue_max_over_time':peak,'waiting_queue_integral_message_s':integral,
            'waiting_queue_nonempty_s':nonempty}

def dominated(target, others, keys):
    return any(all(other[k]<=target[k] for k in keys) and any(other[k]<target[k] for k in keys)
               for other in others if other is not target)

def csv_write(path, rows):
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def analyze(run, output, figures=False):
    if output.exists():raise FileExistsError('Use a new analysis output; do not overwrite prior results')
    frozen=load(run/'frozen_manifest.json');status=load(run/'run_status.json')
    if status['status']!='COMPLETE':raise ValueError('The complete declared pilot is required')
    assert status['manifest_sha256']==digest(run/'frozen_manifest.json'), 'Run is not bound to this frozen manifest'
    scope=frozen['scope'];input_root=Path(frozen['provenance']['input_root'])
    for name,sha in frozen['provenance']['input_hashes'].items():
        if digest(input_root/name)!=sha:raise ValueError('Frozen input differs: '+name)
    experiment=load(input_root/'configs/experiment.json')
    candidates={c['candidate_id']:c for c in load(input_root/'experiments/candidates.json')}
    primary=[];conditions=[];events=[];triggers=[];latency_conditions=[];trace_check=[];sources={}
    signatures=defaultdict(set);trials={};workload_rows=0
    for item in scope['planned_order']:
        name=f"pilot_{item['planned_sequence']:03d}";folder=run/'trials'/name
        result=load(folder/'attempt_result.json');spec=load(folder/'spec.json');m=load(folder/'summary.json')
        trace=records(folder/'trace.ndjson');source=records(folder/'source.ndjson')
        samples=records(folder/'cgroups.ndjson');identity=load(folder/'identities.json');clock=load(folder/'clock.json')
        for file in ['spec.json','attempt_result.json','summary.json','trace.ndjson','source.ndjson','cgroups.ndjson','identities.json','clock.json']:
            sources[str((folder/file).relative_to(run))]=digest(folder/file)
        for k in ['config_id','profile_id','session_id','planned_sequence']:
            if spec[k]!=item[k] or result[k]!=item[k]:raise ValueError('Planned trial identity differs')
        if result['status']!='COMPLETE' or result.get('cleanup_intervened') or not m['evidence_complete'] or not m['source_schedule_valid']:
            raise ValueError('Invalid/incomplete attempt must be adjudicated before this completed-pilot analysis')
        rows=[r for r in trace if r['kind']=='result'];n=spec['expected_messages']
        if [r['sequence'] for r in rows]!=list(range(n)) or [r['sequence'] for r in source]!=list(range(n)):
            raise ValueError('Sequence mismatch')
        if not all(s['accepted'] for s in source):raise ValueError('Dropped input')
        complete=[r for r in trace if r['kind']=='complete']
        if len(complete)!=1 or complete[0]['processed']!=n:raise ValueError('Missing completion')
        driver=identity['driver'];detector=identity['detector']['identity']
        assert driver['boot_id']==detector['boot_id'] and driver['time_namespace']==detector['time_namespace']
        assert driver['cgroup_inode']!=detector['cgroup_inode']
        assert all(p['driver_before']<=p['worker_time']<=p['driver_after'] for p in clock['pings'])
        assert min(p['rtt_ms'] for p in clock['pings'])<=spec['policy']['clock_ping_rtt_limit_ms']
        limits=identity['actual_detector_limits'];quota=spec['profile']['cpu_quota_us'];ram=spec['profile']['memory_mib']
        expected_cpu=f"{quota if quota is not None else 'max'} {spec['cpu_period_us']}"
        assert limits['cpu.max']==expected_cpu and limits['memory.max']==ram*2**20 and limits['memory.swap.max']==0
        assert identity['driver_limits']['memory.max']==512*2**20 and identity['driver_limits']['memory.swap.max']==0
        life={r['phase']:r for r in trace if r['kind']=='lifecycle'}
        assert {'before_imports','after_imports','after_model_load','after_calibration','final'}<=life.keys()
        assert all(state['ExitCode']==0 and not state['OOMKilled'] for state in result['container_states'].values())
        candidate_id=spec['config_id'].rsplit('_d',1)[0];candidate=candidates[candidate_id]
        algorithm=candidate['algorithm'];base={'trial':name,'planned_sequence':item['planned_sequence'],
              'config_id':spec['config_id'],'algorithm':algorithm,'profile_id':spec['profile_id'],
              'session_id':spec['session']['session_id'],'features':'+'.join(candidate['features']),
              'development_fit_future_informed':not candidate['causal']}
        signatures[base['config_id'],base['session_id']].add(hashlib.sha256(json.dumps([
            [r['score'],r['state'],r['positives'],r['negatives'],r['readiness_success'],r['event_started']['start_s'] if r['event_started'] else None,
             r['event_closed']['end_s'] if r['event_closed'] else None] for r in rows],allow_nan=False).encode()).hexdigest())
        accepted=[s['accepted_ingress_available'] for s in source];starts=[r['timing']['processing_start_time'] for r in rows]
        queue=queue_sweep(accepted,starts)
        assert math.isclose(queue['waiting_queue_integral_message_s'],sum(t-a for a,t in zip(accepted,starts)),abs_tol=1e-7)
        assert all(r['timing']['processing_end_time']>=r['timing']['processing_start_time']>=s['accepted_ingress_available'] for r,s in zip(rows,source))
        rss_max=max(r['process_rss_bytes'] for r in rows)
        paired_memory=[s['detector']['memory.current']+s['driver']['memory.current'] for s in samples
                       if isinstance(s.get('detector',{}).get('memory.current'),int) and isinstance(s['driver'].get('memory.current'),int)]
        post_start=life['after_calibration'];end=life['final'];duration=end['time']-post_start['time']
        c0=post_start['cgroup']['cpu.stat'];c1=end['cgroup']['cpu.stat']
        before=life['before_imports'];loaded=life['after_model_load']
        row={**base,'cpu_quota_us':quota,'cpu_period_us':spec['cpu_period_us'],'detector_limit_mib':ram,
          'driver_limit_mib':512,'recording_coverage_s':spec['coverage_s'],'annotated_onset_s':spec['onset_s'],'messages':n,'readiness_success':m['readiness_success'],
          'eligible_episode':m['eligible_episode'],'confirmed_delay_s':m['confirmed_delay_s'],
          'information_delay_s':m['information_delay_s'],'active_before_onset':m['active_before_onset'],
          'model_bytes':m['model_bytes'],'detector_cgroup_sampled_max_mib':m['detector_memory_current_sampled_peak_bytes']/2**20,
          'driver_cgroup_sampled_max_mib':m['driver_memory_current_sampled_peak_bytes']/2**20,
          'combined_cgroup_paired_sample_max_mib':max(paired_memory)/2**20,
          'recorded_detector_process_rss_max_mib':rss_max/2**20,
          'kernel_memory_peak_available':any(s['detector'].get('memory.peak') is not None for s in samples),
          'startup_marker_wall_s':loaded['time']-before['time'],
          'startup_cpu_usage_s':(loaded['cgroup']['cpu.stat']['usage_usec']-before['cgroup']['cpu.stat']['usage_usec'])/1e6,
          'postcal_marker_wall_s':duration,'postcal_cpu_one_core_percent':100*(c1['usage_usec']-c0['usage_usec'])/1e6/duration,
          'postcal_throttled_s':(c1.get('throttled_usec',0)-c0.get('throttled_usec',0))/1e6,
          'postcal_throttled_periods':c1.get('nr_throttled',0)-c0.get('nr_throttled',0),
          'startup_inclusive_external_cpu_one_core_percent':m['detector_cgroup_stream_cpu_percent'],
          'driver_external_cpu_one_core_percent':m['driver_cgroup_cpu_percent'],
          'original_post_dequeue_waiting_count_max':m['maximum_total_accepted_waiting_messages'],**queue,
          'dropped_messages':m['dropped_messages'],'shutdown_wait_s':result['detector_shutdown']['elapsed_s'],
          'source_attempt_lateness_p95_ms':m['source_lateness_ms']['p95'],
          'source_attempt_lateness_max_ms':m['source_lateness_ms']['max']}
        for prefix,key in [('processing','processing_ms'),('queue','queue_ms'),('pipeline','ingress_to_processing_completion_ms'),('model_only','model_inference_ms')]:
            for q,value in m[key].items():row[f'{prefix}_{q}_ms']=value
        for prefix,key in [('processing','processing_ms'),('queue','queue_ms'),('pipeline','end_to_end_ms'),('model_only','model_only_ms')]:
            values=[r['timing'][key] for r in rows if prefix!='model_only' or r['timing']['inference_executed']]
            for label,q in [('p50',.5),('p95',.95),('p99',.99)]:
                assert math.isclose(row[prefix+'_'+label+'_ms'],quantile(values,q),abs_tol=1e-7), 'Raw quantile mismatch'
            assert math.isclose(row[prefix+'_max_ms'],max(values),abs_tol=1e-7)
        row['raw_latency_quantiles_verified']=True
        primary.append(row);workload_rows+=n
        for label,stats in m['condition_processing_ms'].items():
            count=sum((r['condition'] if r['timing']['inference_executed'] else 'calibration_or_unavailable')==label for r in rows)
            latency_conditions.append({**base,'condition':label,'messages':count,**{'processing_'+q+'_ms':value for q,value in stats.items()}})
        for c in m['conditions']:conditions.append({**base,**c,'duration_scope':'recording clock; observed/truncated duration; right-censoring retained'})
        if m['eligible_episode'] and m['confirmed_delay_s'] is not None:
            triggering=min((r for r in rows if r['event_started'] is not None and r['event_started']['start_s']>=spec['onset_s']),key=lambda r:r['event_started']['ready_s'])
            arrival=triggering['accepted_ingress_available'];start=triggering['timing']['processing_start_time']
            ready=triggering['timing']['event_ready_time'];scheduled=triggering['scheduled_due']
            components={'trigger_sample_delay_s':triggering['event_started']['start_s']-spec['onset_s'],
                'accepted_ingress_lateness_ms':1000*(arrival-scheduled),'queue_to_start_ms':1000*(start-arrival),
                'processing_to_event_ready_ms':1000*(ready-start),'sample_due_to_event_ready_ms':1000*(ready-scheduled)}
            assert math.isclose(components['accepted_ingress_lateness_ms']+components['queue_to_start_ms']+components['processing_to_event_ready_ms'],components['sample_due_to_event_ready_ms'],abs_tol=1e-5)
            triggers.append({**base,'trigger_sequence':triggering['sequence'],'confirmed_delay_s':m['confirmed_delay_s'],**components})
        for event_index,e in enumerate(m['events'],1):
            events.append({**base,'event_index':event_index,**e,'right_censored':e['end_s'] is None,
                           'observed_duration_s':(e['end_s'] if e['end_s'] is not None else spec['coverage_s'])-e['start_s']})
        trace_check.append({**base,'exact_sequences':True,'actual_clock_identity_verified':True,'actual_limits_verified':True,
                            'queue_integral_matches_sum_waits':True,'raw_latency_quantiles_verified':True,'all_lifecycle_markers':True})
        trials[name]=(m,rows)
    if any(len(v)!=1 for v in signatures.values()):raise ValueError('Detector decisions differ across profiles')
    if len(primary)!=60 or workload_rows!=12200:raise ValueError('Unexpected declared pilot coverage')
    summaries=[];grid=[];fronts=[]
    for config,profile in itertools.product(scope['configs'],[p['id'] for p in scope['profiles']]):
        group=[r for r in primary if r['config_id']==config and r['profile_id']==profile]
        assert len(group)==3
        condition_group=[c for c in conditions if c['config_id']==config and c['profile_id']==profile]
        jam=next(r for r in group if r['session_id']=='jamming')
        aggregate={name:{'exposure_s':sum(c['exposure_s'] for c in condition_group if c['condition']==name),
                         'false_events':sum(c['false_events'] for c in condition_group if c['condition']==name),
                         'false_active_s':sum(c['false_active_s'] for c in condition_group if c['condition']==name),
                         'right_censored_events':sum(c['false_events_right_censored'] for c in condition_group if c['condition']==name)}
                   for name in ['benign','spoofing']}
        selected_conditions=[c for c in latency_conditions if c['config_id']==config and c['profile_id']==profile]
        summary={'config_id':config,'algorithm':jam['algorithm'],'profile_id':profile,'features':jam['features'],
            'development_fit_future_informed':jam['development_fit_future_informed'],
            'eligible_episode_count':1,'ready_episode_count':int(jam['readiness_success']),
            'confirmed_delay_s':jam['confirmed_delay_s'],'information_delay_s':jam['information_delay_s'],
            'processing_phase_p95_max_ms':max(c['processing_p95_ms'] for c in selected_conditions),
            'recording_processing_p95_min_ms':min(r['processing_p95_ms'] for r in group),
            'recording_processing_p95_max_ms':max(r['processing_p95_ms'] for r in group),
            'recording_pipeline_p95_max_ms':max(r['pipeline_p95_ms'] for r in group),
            'processing_observation_max_ms':max(r['processing_max_ms'] for r in group),
            'queue_observation_max_ms':max(r['queue_max_ms'] for r in group),
            'detector_cgroup_sampled_recording_min_mib':min(r['detector_cgroup_sampled_max_mib'] for r in group),
            'detector_cgroup_sampled_max_mib':max(r['detector_cgroup_sampled_max_mib'] for r in group),
            'driver_cgroup_sampled_max_mib':max(r['driver_cgroup_sampled_max_mib'] for r in group),
            'combined_cgroup_paired_sample_max_mib':max(r['combined_cgroup_paired_sample_max_mib'] for r in group),
            'model_bytes':jam['model_bytes'],
            'startup_marker_wall_median_s':statistics.median(r['startup_marker_wall_s'] for r in group),
            'postcal_cpu_one_core_percent_min':min(r['postcal_cpu_one_core_percent'] for r in group),
            'postcal_cpu_one_core_percent_max':max(r['postcal_cpu_one_core_percent'] for r in group),
            'waiting_queue_max_over_time':max(r['waiting_queue_max_over_time'] for r in group),
            'dropped_messages':sum(r['dropped_messages'] for r in group)}
        for name,c in aggregate.items():
            for key,value in c.items():summary[f'{name}_{key}']=value
            summary[name+'_false_events_per_hour']=c['false_events']*3600/c['exposure_s']
        summaries.append(summary)
        for X,T,Y in itertools.product(experiment['detection_fraction_requirements'],experiment['detection_deadlines_s'],experiment['false_alarm_per_hour_requirements']):
            timely=int(jam['readiness_success'] and jam['confirmed_delay_s'] is not None and jam['confirmed_delay_s']<=T)
            passed=timely>=X and all(summary[c+'_false_events_per_hour']<=Y for c in ['benign','spoofing'])
            grid.append({'config_id':config,'algorithm':jam['algorithm'],'profile_id':profile,'X':X,'T_s':T,'Y_events_per_hour':Y,
                'timely_fraction':timely,'eligible_episodes':1,'empirical':'PASS' if passed else 'FAIL',
                'evidence':'INSUFFICIENT EVIDENCE','resource_scope':'actual enforced profile; no new software latency/model-size acceptance budget',
                'independent_episodes_added':0})
    objectives=['confirmed_delay_s','processing_phase_p95_max_ms','model_bytes']
    for profile in [p['id'] for p in scope['profiles']]:
        for X,T,Y in itertools.product(experiment['detection_fraction_requirements'],experiment['detection_deadlines_s'],experiment['false_alarm_per_hour_requirements']):
            feasible={r['config_id'] for r in grid if r['profile_id']==profile and r['X']==X and r['T_s']==T and r['Y_events_per_hour']==Y and r['empirical']=='PASS'}
            subset=[r for r in summaries if r['profile_id']==profile and r['config_id'] in feasible]
            for r in subset:
                fronts.append({'config_id':r['config_id'],'algorithm':r['algorithm'],'profile_id':profile,'X':X,'T_s':T,'Y_events_per_hour':Y,
                    **{k:r[k] for k in objectives},'nondominated':not dominated(r,subset,objectives),
                    'scope':'descriptive finite subset within one enforced profile; no inferential ranking',
                    'evidence':'INSUFFICIENT EVIDENCE'})
    output.mkdir(parents=True);tables=output/'tables';tables.mkdir()
    for name,rows in [('trials',primary),('conditions',conditions),('events',events),('latency_conditions',latency_conditions),
                      ('config_profiles',summaries),('triggering_messages',triggers),('functional_scenarios',grid),('pareto_descriptive',fronts),('trace_integrity',trace_check)]:csv_write(tables/(name+'.csv'),rows)
    totals={'status':'VERIFIED_COMPLETED_DEVELOPMENT_PILOT','attempts':60,'complete_attempts':60,'processed_messages_across_technical_trials':workload_rows,
        'configs':5,'profiles':4,'recordings':3,'unique_raw_rows':610,'unique_jamming_episodes':1,
        'same_decisions_across_profiles':True,'decision_signature_groups':len(signatures),'queue_max_over_time_min':min(r['waiting_queue_max_over_time'] for r in primary),
        'queue_max_over_time_max':max(r['waiting_queue_max_over_time'] for r in primary),'drops':0,
        'scenario_rows':len(grid),'empirical_pass_rows':sum(r['empirical']=='PASS' for r in grid),
        'evidence':'INSUFFICIENT EVIDENCE','independent_validation':False,'native_latency_budgets_transferred':False,
        'quantile_convention':'linear empirical percentile; per recording; phase-max screening objective is a maximum of quantiles, not a pooled percentile',
        'queue_correction':'Original zero is observed immediately after processing starts. Derived acceptance/start sweep finds transient waiting; original artifacts unchanged.',
        'memory_scope':'100ms sampled cgroup charges; separate driver budget; combined value is maximum paired-sample sum; kernel memory.peak unavailable',
        'cpu_scope':'postcal CPU uses after_calibration-to-final lifecycle snapshots; separate original startup-inclusive external CPU field',
        'pareto_objectives':objectives,'pareto_status':'descriptive post-processing of finite measured subset; no universal minimum or statistical winner',
        'run_started_utc':status['started_utc'],'run_finished_utc':status['finished_utc']}
    (output/'summary.json').write_text(json.dumps(totals,indent=2)+'\n')
    configuration_records=[]
    for config in scope['configs']:
        candidate_id, suffix=config.rsplit('_d',1);threshold,confirmation=suffix.rsplit('_c',1)
        configuration_records.append({'config_id':config,'decision_threshold':float(threshold),
                                      'confirmation_count':int(confirmation),**candidates[candidate_id]})
    manifest={'protocol':'docker-pilot-v1','source_run_label':run.name,'run_status':'COMPLETE',
        'configs':configuration_records,'profiles':scope['profiles'],'cpu_period_us':scope['cpu_period_us'],
        'seed':scope['seed'],'technical_attempts_per_pair':1,'planned_order':scope['planned_order'],
        'calibration':{'seconds':experiment['calibration_s'],'minimum_observations':experiment['minimum_calibration_observations'],
                       'baseline':'median of clean calibration observations','normalization':'(x-baseline)/baseline; no epsilon'},
        'recovery_negatives':experiment['recovery_negatives'],'maximum_observation_gap_s':experiment['max_allowed_gap_s'],
        'policy':frozen['policy'],'independent_validation':False,'source_inputs_shipped':False}
    (output/'experiment_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    provenance={'analysis_script_sha256':digest(Path(__file__)),'frozen_manifest_sha256':digest(run/'frozen_manifest.json'),
        'frozen_image_id':frozen['provenance']['image_id'],'frozen_parent_image_id':frozen['provenance']['parent_image_id'],
        'frozen_input_hashes':frozen['provenance']['input_hashes'],'trial_source_hashes':sources,
        'created_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_run_label':run.name,
        'no_retraining_or_replay':True,'original_trial_artifacts_modified':False}
    (output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    report(output,totals,summaries,fronts,primary)
    if figures:plot(output,primary,summaries,events)
    print(json.dumps(totals,indent=2))


def report(output,totals,rows,fronts,trials):
    order=['RULE','DT','KNN','SVM','RF'];profiles=['guarded_reference','cpu1_ram512','cpu05_ram512','cpu025_ram512']
    lines=['# Docker resource-sensitivity pilot: completed repeat','',
      f"{totals['configs']} frozen configurations, {totals['profiles']} enforced profiles, {totals['recordings']} development recordings and one technical attempt per configuration/profile/recording. All {totals['complete_attempts']} attempts completed with exit 0, no cleanup intervention, no drops and complete raw-trace checks. This analysis performs no new fitting or replay.",
      '', '## Detection and false alarms', '',
      '| Configuration | Confirmed execution delay range (s), four profiles | Benign false events per profile | Spoofing false events per profile |',
      '|---|---:|---:|---:|']
    for algorithm in order:
        group=[r for r in rows if r['algorithm']==algorithm];delays=[r['confirmed_delay_s'] for r in group if r['confirmed_delay_s'] is not None]
        value=f"{min(delays):.6f}–{max(delays):.6f}" if len(delays)==4 else f"Detected in {len(delays)}/4 profile runs"
        lines.append(f"| {group[0]['config_id']} | {value} | {group[0]['benign_false_events']} | {group[0]['spoofing_false_events']} |")
    first=rows[0]
    lines += ['', f"Each configuration/profile sees the same {first['benign_exposure_s']:.6f} s benign exposure and {first['spoofing_exposure_s']:.6f} s spoofing exposure. Do not add exposure across profiles, models or repeated executions as independent evidence. Zero observed false events does not establish a low real-world false-alarm rate.", '']
    for algorithm in order:
        group=[r for r in rows if r['algorithm']==algorithm];r=group[0]
        if r['spoofing_false_events']:
            lines.append(f"{algorithm} produced {r['spoofing_false_events']} false jamming event(s) during spoofing in each profile. Observed false-active time was {r['spoofing_false_active_s']:.6f} s ({100*r['spoofing_false_active_s']/r['spoofing_exposure_s']:.4f}% of that short interval), with {r['spoofing_right_censored_events']} right-censored event(s). The arithmetic {r['spoofing_false_events_per_hour']:.6f} events/hour is descriptive of this interval, not an established operational rate. Censored durations are not known full event durations.")
    lines += ['', f"Raw scores, states, confirmation counts and event sample boundaries were identical across profiles in all {totals['decision_signature_groups']} configuration/session groups. These are replays of {totals['unique_jamming_episodes']} unique development jamming episode, not independent attack trials. ML fitting includes the same episode and cannot establish external generalization. The rule is causal in replay time but was selected after development exploration. See triggering_messages.csv for the trigger-sample delay, accepted-ingress lateness, queue wait and processing-to-event-ready decomposition.", '',
      '## Processing and memory', '',
      'Values below are maxima over the three recording-level processing P95 values, in milliseconds. They include calibration in each recording. These are maxima of quantiles, not pooled P95s. Phase-specific quantiles are separate in latency_conditions.csv.', '',
      '| Algorithm | Reference, 1536 MiB | 1 CPU, 512 MiB | 0.5 CPU, 512 MiB | 0.25 CPU, 512 MiB | Sampled detector cgroup max range (MiB) | Model bytes |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for algorithm in order:
        group=[r for r in rows if r['algorithm']==algorithm];by={r['profile_id']:r for r in group}
        values=[f"{by[p]['recording_processing_p95_max_ms']:.3f}" for p in profiles]
        lines.append('| '+algorithm+' | '+' | '.join(values)+f" | {min(r['detector_cgroup_sampled_recording_min_mib'] for r in group):.2f}–{max(r['detector_cgroup_sampled_max_mib'] for r in group):.2f} | {group[0]['model_bytes']:,} |")
    rf={r['profile_id']:r for r in rows if r['algorithm']=='RF'}
    low=rf['cpu025_ram512'];full=rf['cpu1_ram512']
    lines += ['', f"RF recording-level processing P95 values were {low['recording_processing_p95_min_ms']:.2f}–{low['recording_processing_p95_max_ms']:.2f} ms at 0.25 CPU and {full['recording_processing_p95_min_ms']:.2f}–{full['recording_processing_p95_max_ms']:.2f} ms at 1 CPU, both with 512 MiB. This tail increase is consistent with observed throttling under a 100 ms quota period, even when average CPU usage is low at a roughly 1 Hz input rate. It is not target-hardware calibration or an isolated causal effect estimate. Other models show scheduling variation rather than uniform monotonic scaling.", '',
      'One technical attempt per pair and uncontrolled host/VM load do not support statistical speed rankings. The guarded reference additionally changes RAM; fixed-512-MiB comparisons provide the clearest quota contrasts.', '',
      f"Detector cgroup sampled maxima ranged from {min(r['detector_cgroup_sampled_max_mib'] for r in trials):.2f} to {max(r['detector_cgroup_sampled_max_mib'] for r in trials):.2f} MiB. The separate source/collector had its own 512 MiB budget and sampled maxima of {min(r['driver_cgroup_sampled_max_mib'] for r in trials):.2f}–{max(r['driver_cgroup_sampled_max_mib'] for r in trials):.2f} MiB. Paired-sample sums are available in trials.csv. Process RSS is a different accounting quantity; neither value is intrinsic model memory. Kernel memory.peak is unavailable; 100 ms sampled maxima are not true peak guarantees. No lower-memory profile was tested, so 512 MiB is not a measured minimum.", '',
      '## Startup, queue and CPU scope', '',
      'Startup below spans before_imports to after_model_load and excludes interpreter/container work before the first marker. Values are medians of three recording-startup measurements, not repeated estimates of the same session. The producer starts the replay clock after model readiness; these startup durations are separate from the annotated-onset detection delay.', '',
      '| Algorithm | 1 CPU startup (s) | 0.5 CPU startup (s) | 0.25 CPU startup (s) |', '|---|---:|---:|---:|']
    for algorithm in order:
        group={r['profile_id']:r for r in rows if r['algorithm']==algorithm}
        lines.append('| '+algorithm+' | '+' | '.join(f"{group[p]['startup_marker_wall_median_s']:.3f}" for p in profiles[1:])+' |')
    lines += ['', f"Post-calibration CPU measured between after_calibration and final lifecycle snapshots ranged from {min(r['postcal_cpu_one_core_percent'] for r in trials):.3f}% to {max(r['postcal_cpu_one_core_percent'] for r in trials):.3f}% of one core. The original external CPU field includes startup/instrumentation and is labelled separately in trials.csv.", '',
      f"The original summaries observed zero waiting messages immediately after processing starts. The derived continuous-time acceptance/start sweep finds a maximum of {totals['queue_max_over_time_min']}–{totals['queue_max_over_time_max']} waiting message(s) across trials. Every sweep stays nonnegative, ends at zero, and has an integral equal to the sum of individual waits. The longest queue wait was {max(r['queue_max_ms'] for r in trials):.3f} ms. Original summaries were preserved. This roughly 1 Hz workload does not establish stress capacity.", '',
      '## Functional screening and descriptive Pareto sets', '',
      f"The existing X={{0.8, 0.9, 1}}, T={{3, 5, 10}} s and Y={{0, 0.5, 1}} events/hour grid produces {totals['scenario_rows']} configuration/profile/scenario rows, of which {totals['empirical_pass_rows']} empirically pass. These are not independent experiments. All evidence remains INSUFFICIENT EVIDENCE. Readiness failures stay in the episode denominator; none occurred here. Benign and spoofing false alarms are screened separately. Native mac_experimental latency/model-size budgets are not transferred to Docker. The enforced profiles define tested CPU/RAM allocations; no new latency acceptance threshold is introduced.", '',
      'Pareto comparison is descriptive within each profile, after empirical functional screening, over execution delay, maximum condition/calibration processing P95 and serialized model bytes. It does not identify a statistical winner or globally minimal configuration. For X=1 and Y=0:', '',
      '| Profile | Deadline (s) | Nondominated selected configurations |', '|---|---:|---|']
    for profile in profiles:
        for deadline in [3,5,10]:
            selected=[r['algorithm'] for r in fronts if r['profile_id']==profile and r['X']==1 and r['Y_events_per_hour']==0 and r['T_s']==deadline and r['nondominated']]
            lines.append(f"| {profile} | {deadline} | {', '.join(selected)} |")
    lines += ['', '## Reproduce this analysis', '', '```sh',
      'python3 scripts/analyze_docker_pilot.py --run-root /path/to/retained/completed-run --output build/NEW_ANALYSIS',
      '# Add --figures in the pinned scientific environment to regenerate the plots.', '```', '',
      'The retained run bundle, trusted sibling input manifest/workspace and original trace files are required. Compact shipped summaries are not substitutes for those inputs. Analysis refuses to overwrite an output, verifies frozen input hashes, checks actual clock/cgroup limits, and reconstructs queue behavior. provenance.json records source hashes and frozen image identities.', '',
      '## Limitations for the manuscript', '',
      'One jamming episode/session, one spoofing session and one supplementary benign development recording. Future-informed ML fits and a development-selected rule threshold. One technical attempt per configuration/profile/session in this repeat; the earlier pilot is technical replication, not new independent data. Annotated onset is not physical jammer-on. No verified attack-end/recovery ground truth. A desktop Linux ARM64 VM is not a calibrated UAV processor. No validated external results or inferential 95% guarantees.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')


def plot(output,trials,rows,events):
    import os
    os.environ.setdefault('MPLCONFIGDIR',str(output/'matplotlib-cache'))
    cache=output/'matplotlib-cache';cache.mkdir(exist_ok=True)
    os.environ.setdefault('XDG_CACHE_HOME',str(cache))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'RULE':'#9467bd','DT':'#1f77b4','KNN':'#ff7f0e','SVM':'#d62728','RF':'#2ca02c'}
    order=['RULE','DT','KNN','SVM','RF'];profiles=['cpu025_ram512','cpu05_ram512','cpu1_ram512'];x=[.25,.5,1]
    figures=output/'figures';figures.mkdir()
    fig,ax=plt.subplots(1,2,figsize=(12,4.8))
    for algorithm in order:
        group={r['profile_id']:r for r in rows if r['algorithm']==algorithm}
        ax[0].plot(x,[group[p]['confirmed_delay_s'] for p in profiles],'o-',label=algorithm,color=colors[algorithm])
        ax[1].plot(x,[group[p]['processing_phase_p95_max_ms'] for p in profiles],'o-',label=algorithm,color=colors[algorithm])
    for deadline in [3,5,10]:ax[0].axhline(deadline,color='gray',linestyle='--',linewidth=.8);ax[0].text(1.01,deadline,f'{deadline}s',va='center')
    ax[0].set(ylabel='Confirmed execution delay (s)',title='One development jamming episode',ylim=(0,10.8))
    ax[1].set(ylabel='Maximum phase-specific processing P95 (ms)',title='Maximum across conditions and calibration',yscale='log')
    for a in ax:a.set_xlabel('CPU quota (512 MiB detector limit)');a.set_xticks(x);a.grid(alpha=.2)
    ax[1].legend();fig.suptitle('Docker resource sensitivity: fixed-memory quota contrasts\nOne attempt per configuration/profile/session; descriptive development results')
    fig.tight_layout();fig.savefig(figures/'quota_delay_and_processing.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(12,4.8))
    positions=range(len(order))
    for i,algorithm in enumerate(order):
        group=[r for r in rows if r['algorithm']==algorithm]
        lo=min(r['detector_cgroup_sampled_recording_min_mib'] for r in group);hi=max(r['detector_cgroup_sampled_max_mib'] for r in group)
        ax[0].plot([i,i],[lo,hi],color=colors[algorithm],linewidth=3);ax[0].scatter([i],[hi],color=colors[algorithm])
        ax[1].bar(i,group[0]['model_bytes'],color=colors[algorithm])
    ax[0].set(ylabel='Sampled detector cgroup maximum (MiB)',title='Range over profiles and recordings',ylim=(0,125))
    ax[1].set(ylabel='Serialized model size (bytes)',title='Model bytes are not runtime memory',yscale='log')
    for a in ax:a.set_xticks(list(positions),order);a.grid(axis='y',alpha=.2)
    fig.suptitle('Memory accounting: 100 ms sampled cgroup charge, kernel peak unavailable\nSeparate source/collector sampled charge approximately 15–17 MiB, outside detector budget')
    fig.tight_layout();fig.savefig(figures/'memory_and_model_size.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(12,4.8))
    for algorithm in order:
        group={r['profile_id']:r for r in rows if r['algorithm']==algorithm}
        ax[0].plot(x,[group[p]['startup_marker_wall_median_s'] for p in profiles],'o-',label=algorithm,color=colors[algorithm])
        a=[r for r in trials if r['algorithm']==algorithm]
        for i,profile in enumerate(profiles):
            g=[r for r in a if r['profile_id']==profile]
            ax[1].scatter([i]*len(g),[r['postcal_cpu_one_core_percent'] for r in g],color=colors[algorithm],alpha=.75)
    ax[0].set(xlabel='CPU quota (512 MiB)',ylabel='Marker-bounded startup wall time (s)',title='Median of three recording startup times');ax[0].set_xticks(x)
    ax[1].set(ylabel='Post-calibration CPU (% of one core)',title='After-calibration to final lifecycle markers');ax[1].set_xticks(range(3),['0.25CPU','0.5CPU','1CPU'])
    for a in ax:a.grid(alpha=.2)
    ax[0].legend();fig.tight_layout();fig.savefig(figures/'startup_and_postcal_cpu.png',dpi=160);plt.close(fig)

    fig,ax=plt.subplots(1,2,figsize=(12,4.8))
    for axis,session in zip(ax,['jamming','spoofing']):
        cohort=[r for r in trials if r['profile_id']=='cpu1_ram512' and r['session_id']==session]
        onset=cohort[0]['annotated_onset_s'];end=cohort[0]['recording_coverage_s']
        for index,algorithm in enumerate(order):
            subset=[e for e in events if e['profile_id']=='cpu1_ram512' and e['session_id']==session and e['algorithm']==algorithm]
            for event in subset:
                stop=event['end_s'] if event['end_s'] is not None else end
                axis.broken_barh([(event['start_s']-onset,stop-event['start_s'])],(index-.25,.5),facecolors=colors[algorithm])
        axis.axvline(0,color='gray',linestyle='--',linewidth=.8)
        axis.set_yticks(range(len(order)),order);axis.set_xlim(-10,end-onset)
        axis.set(xlabel='Recording seconds from annotated onset',title=session.capitalize()+' recording: ACTIVE intervals')
        axis.grid(axis='x',alpha=.2)
    fig.suptitle('Recording-clock state windows at 1 CPU / 512 MiB (last 10 s of clean prefix shown)\nML fitted on these development recordings; physical RF-on is not established')
    fig.tight_layout();fig.savefig(figures/'active_state_windows.png',dpi=160);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--figures',action='store_true')
    args=p.parse_args();analyze(args.run_root.resolve(),args.output.resolve(),args.figures)
