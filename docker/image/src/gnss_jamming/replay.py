import argparse, hashlib, json, pickle, platform, multiprocessing as mp, time, uuid
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from .core import ROOT, config, sessions, read_json, write_json, relative, Calibration, Detector, score

class Runner:
    def __init__(self,candidate,cfg,decision_threshold=None,confirmation=None):
        self.c=candidate;self.cfg=cfg
        self.model=pickle.loads((ROOT/'experiments/models'/f'{candidate["candidate_id"]}.pkl').read_bytes())
        self.cal=Calibration(candidate['features'],cfg)
        thresholds=candidate['thresholds'] if decision_threshold is None else [decision_threshold]
        counts=cfg['confirmation_counts'] if confirmation is None else [confirmation]
        self.states={(th,n):Detector(n,cfg['recovery_negatives'],cfg['max_allowed_gap_s']) for th in thresholds for n in counts}
        self.timings=[];self.predictions=[]
    def state_label(self):
        if self.cal.failed:return 'UNAVAILABLE'
        if self.cal.baseline is None:return 'CALIBRATING'
        return '|'.join(sorted({d.state for d in self.states.values()}))
    def step(self,row,arrival=None,origin=None,scheduled=None):
        start=time.perf_counter();before=self.state_label();t=row['elapsed_s'];values=[row[f] for f in self.c['features']]
        valid=self.cal.update(t,values);s=None;infer_ms=0.;inference_executed=False;event_ready=None
        if self.cal.failed:
            for state in self.states.values():state.update(t,None)
        elif valid:
            if np.isfinite(values).all():
                x=relative([values],self.cal.baseline)
                t0=time.perf_counter();s=float(score(self.model,x)[0]);infer_ms=(time.perf_counter()-t0)*1000;inference_executed=True
                if not np.isfinite(s):s=None
            for (th,n),state in self.states.items():
                event=state.update(t,None if s is None else s>=th)
                if event is not None:
                    event_ready=time.perf_counter();event['ready_s']=event_ready-origin if origin is not None else t
        end=time.perf_counter()
        self.predictions.append({'elapsed_s':t,'score':s})
        self.timings.append(dict(elapsed_s=t,condition=row.get('condition',row.get('state','unknown')),state_before=before,state_after=self.state_label(),inference_executed=inference_executed,
            scheduled_due_time=scheduled,actual_arrival_time=arrival,processing_start_time=start,processing_end_time=end,event_ready_time=event_ready,
            producer_lateness_ms=None if scheduled is None or arrival is None else (arrival-scheduled)*1000,
            queue_ms=0. if arrival is None else max(0.,(start-arrival)*1000),processing_ms=(end-start)*1000,
            end_to_end_ms=(end-(start if arrival is None else arrival))*1000,
            scheduled_to_ready_ms=None if scheduled is None else (end-scheduled)*1000,model_only_ms=infer_ms))

def metrics(r,s,part,mode):
    cfg=r.cfg; rows=[];events=[]
    coverage=s.get('recording_end_us');end=float(part.elapsed_s.max()) if coverage is None else (coverage-int(part.timestamp.iloc[0]))/1e6;begin=cfg['calibration_s']; onset=None if s['onset_us'] is None else (s['onset_us']-int(part.timestamp.iloc[0]))/1e6
    for (th,n),state in r.states.items():
        cid=f'{r.c["candidate_id"]}_d{th:g}_c{n}'
        for i,e in enumerate(state.events):
            events.append(dict(config_id=cid,session_id=s['session_id'],event_index=i,**e,right_censored=e['end_s'] is None))
        # Cohort eligibility uses only recording metadata, never model behavior.
        eligible=onset is not None and s['attack_type']=='jamming' and end>=onset+10
        detection=[e for e in state.events if onset is not None and e['start_s']>=onset]
        first=min((e['ready_s']-onset for e in detection),default=None)
        readiness=r.cal.baseline is not None and not r.cal.failed
        intervals=[('benign',begin,end if onset is None else onset)]
        if s['attack_type']=='spoofing': intervals.append(('spoofing',onset,end))
        base=dict(config_id=cid,candidate_id=r.c['candidate_id'],session_id=s['session_id'],attack_type=s['attack_type'],mode=mode,workload='isolated_single_configuration' if mode=='realtime' else 'information_clock_only',recording_end_s=end,coverage_source='recording_end_us' if coverage is not None else 'last_gnss_sample',causal=r.c['causal'],decision_threshold=th,confirmation=n,readiness_success=readiness,eligible_episode=eligible,confirmed_delay_s=first if eligible else None,information_delay_s=min((e['start_s']-onset for e in detection),default=None) if eligible else None,active_before_onset=any(e['start_s']<onset and (e['end_s'] is None or e['end_s']>onset) for e in state.events) if onset is not None else False)
        for label,a,b in intervals:
            ee=[e for e in state.events if a<=e['start_s']<b]
            durations=[max(0.,min(b,e['end_s'] if e['end_s'] is not None else b)-e['start_s']) for e in ee]
            rows.append({**base,'condition':label,'exposure_s':max(0.,b-a),'false_events':len(ee),'false_active_s':interval_overlap_local(state.events,a,b),'false_event_duration_max_s':max(durations,default=0.),'false_event_duration_sum_s':sum(durations),'false_events_right_censored':sum(e['end_s'] is None or e['end_s']>b for e in ee)})
    return rows,events

def interval_overlap_local(events,a,b):
    return sum(max(0.,min(b,e['end_s'] if e['end_s'] is not None else b)-max(a,e['start_s'])) for e in events)

def _producer(send,ready,commands,records,coverage_s):
    """Spawned process independent of inference; shared OS monotonic clock."""
    ready.send(True);ready.close()
    origin=commands.recv();commands.close()
    try:
        for row in records:
            due=origin+row['elapsed_s'];time.sleep(max(0.,due-time.perf_counter()))
            arrival=time.perf_counter();send.send((row,arrival,due))
        time.sleep(max(0.,origin+coverage_s-time.perf_counter()))
        send.send(None)
    finally:send.close()

def isolated_replay(c,cfg,part,session,threshold,confirmation):
    r=Runner(c,cfg,decision_threshold=threshold,confirmation=confirmation)
    records=part.sort_values('elapsed_s').to_dict('records')
    coverage=session.get('recording_end_us')
    coverage_s=records[-1]['elapsed_s'] if coverage is None else (coverage-int(part.timestamp.iloc[0]))/1e6
    ctx=mp.get_context('spawn');receive,send=ctx.Pipe(duplex=False)
    ready_recv,ready_send=ctx.Pipe(duplex=False);cmd_recv,cmd_send=ctx.Pipe(duplex=False)
    process=ctx.Process(target=_producer,args=(send,ready_send,cmd_recv,records,coverage_s))
    process.start();send.close();ready_send.close();cmd_recv.close()
    try:
        if not ready_recv.poll(60):raise RuntimeError('Producer startup timed out')
        ready_recv.recv();origin=time.perf_counter()+.1;cmd_send.send(origin)
        while True:
            if not receive.poll(1):
                if not process.is_alive():raise RuntimeError(f'Producer exited before completion: {process.exitcode}')
                continue
            try:item=receive.recv()
            except EOFError as exc:raise RuntimeError('Producer closed without completion marker') from exc
            if item is None:break
            row,arrival,due=item;r.step(row,arrival=arrival,origin=origin,scheduled=due)
        process.join(timeout=10)
        if process.exitcode!=0:raise RuntimeError(f'Producer failed: {process.exitcode}')
        return r,time.perf_counter()-origin
    finally:
        if process.is_alive():process.terminate();process.join()
        receive.close();ready_recv.close();cmd_send.close()

def config_id(c,th,n):return f'{c["candidate_id"]}_d{th:g}_c{n}'

def append_csv(path,records,columns=None):
    if records:pd.DataFrame(records).to_csv(path,mode='a',header=not path.exists(),index=False)
    elif not path.exists() and columns:pd.DataFrame(columns=columns).to_csv(path,index=False)

def checkpoint(output,r,s,part,run_id,wall_s,fingerprint,hashes):
    rows,events=metrics(r,s,part,'realtime');th,n=next(iter(r.states));cid=config_id(r.c,th,n)
    common=dict(run_id=run_id,config_id=cid,candidate_id=r.c['candidate_id'],session_id=s['session_id'])
    for record in rows+events:record['run_id']=run_id
    append_csv(output/'realtime_metrics.csv',rows)
    append_csv(output/'realtime_events.csv',events,['config_id','session_id','event_index','start_s','ready_s','end_s','right_censored','run_id'])
    append_csv(output/'realtime_timings.csv',[{**common,**t} for t in r.timings])
    record={**common,'status':'complete','wall_s':wall_s,'fingerprint':fingerprint,'input_hashes':hashes,
            'seed':r.cfg['seed'],'trial':1,'messages':len(r.timings),'platform':platform.platform(),'python':platform.python_version(),
            'workload':'isolated_single_configuration','consumer':'fresh spawned process per configuration/session','producer':'independent spawned process, monotonic schedule; arrival before IPC send',
            'timing_boundary':'producer message available through pipe -> preprocessing/inference/state -> event ready; OS IPC/queue wait included; no physical transport',
            'physical_transport_included':False}
    # Completion record follows every artifact append; incomplete run_ids must be ignored.
    with (output/'realtime_runs.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')

def _run_pair_worker(c,cfg,part,session,threshold,confirmation,output,run_id,fingerprint,hashes):
    """Fresh detector process per configuration/session; producer is its child."""
    runner,wall_s=isolated_replay(c,cfg,part,session,threshold,confirmation)
    checkpoint(output,runner,session,part,run_id,wall_s,fingerprint,hashes)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--realtime',action='store_true')
    parser.add_argument('--config-id',action='append');parser.add_argument('--session-id',action='append')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/tables')
    parser.add_argument('--force',action='store_true',help='Repeat completed configuration/session pairs')
    args=parser.parse_args();cfg=config();cs=read_json(ROOT/'experiments/candidates.json');d=pd.read_csv(ROOT/'data/derived/development.csv')
    ss=[s for s in sessions() if args.session_id is None or s['session_id'] in args.session_id]
    if not ss or (args.session_id and set(args.session_id)-{s['session_id'] for s in ss}):parser.error('Unknown or empty session selection')
    output=args.output_dir;output.mkdir(parents=True,exist_ok=True)
    if args.realtime:
        ids=args.config_id or cfg.get('realtime_config_ids',[])
        if not ids:parser.error('Declare realtime_config_ids or pass --config-id')
        library={config_id(c,th,n):(c,th,n) for c in cs for th in c['thresholds'] for n in cfg['confirmation_counts']}
        if set(ids)-set(library):parser.error(f'Unknown config ids: {sorted(set(ids)-set(library))}')
        paths=[ROOT/'configs/experiment.json',ROOT/'configs/sessions.json',ROOT/'experiments/candidates.json',ROOT/'data/derived/development.csv',Path(__file__),ROOT/'src/gnss_jamming/core.py',ROOT/'requirements-lock.txt',ROOT/'experiments/environment.json']
        paths += [ROOT/'experiments/models'/f'{c["candidate_id"]}.pkl' for c in cs]
        hashes={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        fingerprint=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
        complete=set();journal=output/'realtime_runs.jsonl'
        if journal.exists() and not args.force:
            for line in journal.read_text().splitlines():
                rec=json.loads(line)
                if rec.get('status')=='complete' and rec.get('fingerprint')==fingerprint:complete.add((rec['config_id'],rec['session_id']))
        for cid in ids:
            c,th,n=library[cid]
            for s in ss:
                if (cid,s['session_id']) in complete:
                    print('Skip completed',cid,s['session_id'],flush=True);continue
                part=d[d.session_id==s['session_id']]
                print('Isolated realtime',cid,s['session_id'],flush=True)
                worker=mp.get_context('spawn').Process(target=_run_pair_worker,args=(c,cfg,part,s,th,n,output,uuid.uuid4().hex,fingerprint,hashes))
                worker.start();worker.join()
                if worker.exitcode!=0:raise RuntimeError(f'Detector worker failed for {cid}/{s["session_id"]}: {worker.exitcode}')
                print('Checkpoint complete',cid,s['session_id'],flush=True)
        return
    mode='information_clock_development';start=time.perf_counter();rows=[];events=[];timings=[]
    for s in ss:
        part=d[d.session_id==s['session_id']].sort_values('elapsed_s')
        for c in cs:
            r=Runner(c,cfg)
            for row in part.to_dict('records'):r.step(row)
            rr,ee=metrics(r,s,part,mode);rows+=rr;events+=ee
            timings += [dict(candidate_id=c['candidate_id'],session_id=s['session_id'],**t) for t in r.timings]
    pd.DataFrame(rows).to_csv(output/f'{mode}_metrics.csv',index=False)
    pd.DataFrame(events,columns=['config_id','session_id','event_index','start_s','ready_s','end_s','right_censored']).to_csv(output/f'{mode}_events.csv',index=False)
    pd.DataFrame(timings).to_csv(output/f'{mode}_timings.csv',index=False)
    write_json(ROOT/f'experiments/{mode}_run.json',{'mode':mode,'platform':platform.platform(),'python':platform.python_version(),'wall_s':time.perf_counter()-start,'config_sha256':hashlib.sha256((ROOT/'configs/experiment.json').read_bytes()).hexdigest(),'candidate_order':[c['candidate_id'] for c in cs],'workload':'all candidate threshold/confirmation states; information clock only; no execution-clock latency claim','physical_transport_included':False})
    print('Saved',mode,'metrics, events, timings',flush=True)
if __name__=='__main__':main()
