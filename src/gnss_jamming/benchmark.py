"""Isolated complete-configuration resource measurements and open-loop stress."""
import argparse
import hashlib
from collections import Counter, defaultdict
import multiprocessing as mp
import platform
import time
import numpy as np
import pandas as pd
import psutil
from .core import ROOT, config, read_json, write_json
from .replay import Runner


def complete_configs(candidates, cfg):
    for c in candidates:
        for th in c['thresholds']:
            for n in cfg['confirmation_counts']:
                yield c, th, n, f'{c["candidate_id"]}_d{th:g}_c{n}'


def percentiles(values, prefix):
    return {f'{prefix}_p{p}_ms': float(np.percentile(values, p)) if values else None
            for p in (50, 95, 99)}


def new_runner(c, cfg, th, n):
    return Runner(c, cfg, decision_threshold=th, confirmation=n)


def ready_runner(c, cfg, part, th=None, n=None):
    """Only chronological calibration observations, never attack warmup."""
    th = c['thresholds'][0] if th is None else th
    n = cfg['primary_confirmation'] if n is None else n
    r = new_runner(c, cfg, th, n)
    for row in part:
        if row['elapsed_s'] <= cfg['calibration_s']:
            r.step(row)
    return r


def _producer(out, ready, commands, rows, hz):
    """Independent spawn process; schedule never depends on consumer progress."""
    ready.send(True); ready.close()
    start = commands.recv(); commands.close()
    for i, row in enumerate(rows):
        due = start + i / hz
        remaining = due - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)
        enqueued = time.perf_counter()
        out.put((row, due, enqueued, i))
    out.put(None)


def stress_run(c, cfg, part, hz, count):
    r = ready_runner(c, cfg, part)
    post = [row for row in part if row['elapsed_s'] > cfg['calibration_s']]
    indices = np.linspace(0, len(post)-1, count).astype(int)
    rows = []
    for i, j in enumerate(indices):
        row = post[j].copy()
        row['elapsed_s'] = cfg['calibration_s'] + 1 + i/hz
        rows.append(row)
    ctx = mp.get_context('spawn'); out = ctx.Queue()
    ready_recv,ready_send=ctx.Pipe(duplex=False)
    cmd_recv,cmd_send=ctx.Pipe(duplex=False)
    producer = ctx.Process(target=_producer, args=(out,ready_send,cmd_recv,rows,hz))
    producer.start(); ready_send.close(); cmd_recv.close()
    if not ready_recv.poll(60):
        producer.terminate();producer.join();raise RuntimeError('Producer startup timeout')
    ready_recv.recv();ready_recv.close()
    start=time.perf_counter()+.1;cmd_send.send(start);cmd_send.close()
    samples=[];cpu0=None;busy_start=None;consumed=0
    try:
        while True:
            item = out.get(timeout=60)
            if item is None: break
            row, due, enqueued, sequence = item
            received = time.perf_counter()
            if busy_start is None: busy_start = received;cpu0=time.process_time()
            r.step(row, arrival=enqueued, origin=start, scheduled=due)
            ready = time.perf_counter()
            samples.append(dict(sequence=sequence,condition=row['state'],scheduled_due_time=due,
                actual_arrival_time=enqueued,consumer_received_time=received,
                processing_start_time=r.timings[-1].get('processing_start_time',received),
                event_ready_time=r.timings[-1].get('event_ready_time',ready),
                producer_lateness_ms=(enqueued-due)*1000,scheduled_to_ready_ms=(ready-due)*1000,
                actual_arrival_to_ready_ms=(ready-enqueued)*1000,
                ipc_and_queue_ms=(received-enqueued)*1000,processing_ms=r.timings[-1]['processing_ms']))
            consumed += 1
    finally:
        producer.join(timeout=10)
        if producer.is_alive(): producer.terminate(); producer.join()
        out.close(); out.join_thread()
    end=time.perf_counter()
    if producer.exitcode != 0 or consumed != count:
        raise RuntimeError(f'Producer failed/incomplete stress trace: {consumed}/{count}')
    arrival=[x['actual_arrival_time'] for x in samples]
    offered=(count-1)/(arrival[-1]-arrival[0]); lateness=[x['producer_lateness_ms'] for x in samples]
    deadline=1000/hz
    queued=[max(0,int(np.searchsorted(arrival,x['processing_start_time'],side='right'))-i-1) for i,x in enumerate(samples)]
    due_times=[x['scheduled_due_time'] for x in samples]
    scheduled_backlog=[max(0,int(np.searchsorted(due_times,x['processing_start_time'],side='right'))-i-1) for i,x in enumerate(samples)]
    maintained=abs(offered/hz-1)<=.05 and np.percentile(lateness,95)<=deadline
    result=dict(candidate_id=c['candidate_id'],
        config_id=f'{c["candidate_id"]}_d{c["thresholds"][0]:g}_c{cfg["primary_confirmation"]}',
        arrival_hz=hz,requested_hz=hz,messages=count,actual_offered_hz=offered,
        offered_rate_maintained=bool(maintained),
        workload_status='VALID_OFFERED_RATE' if maintained else 'INVALID_OFFERED_RATE',
        observed_completion_hz=count/(end-start),deadline_ms=deadline,max_backlog=max(queued),actual_arrival_backlog_max=max(queued),scheduled_backlog_max=max(scheduled_backlog),
        scheduled_to_ready_deadline_misses=sum(x['scheduled_to_ready_ms']>deadline for x in samples),
        actual_arrival_deadline_misses=sum(x['actual_arrival_to_ready_ms']>deadline for x in samples),
        deadline_misses=sum(x['scheduled_to_ready_ms']>deadline for x in samples),
        **percentiles(lateness,'producer_lateness'),
        **percentiles([x['scheduled_to_ready_ms'] for x in samples],'scheduled_to_ready'),
        **percentiles([x['actual_arrival_to_ready_ms'] for x in samples],'end_to_end'),
        **percentiles([x['ipc_and_queue_ms'] for x in samples],'queue'),
        cpu_one_core_percent=100*(time.process_time()-cpu0)/(end-busy_start),
        total_process_rss_bytes=psutil.Process().memory_info().rss,producer_process_included_in_cpu=False)
    return result,samples


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--full-passes',type=int,default=1)
    parser.add_argument('--stress-messages',type=int,default=300)
    parser.add_argument('--skip-stress',action='store_true')
    args=parser.parse_args()
    if args.full_passes<1 or args.stress_messages<2:
        parser.error('full-passes >= 1 and stress-messages >= 2 required')
    cfg=config(); cs=read_json(ROOT/'experiments/candidates.json')
    data=pd.read_csv(ROOT/'data/derived/development.csv')
    parts={sid:g.sort_values('elapsed_s').to_dict('records') for sid,g in data.groupby('session_id',sort=False)}
    proc=psutil.Process(); resources=[]; conditions=[]; calibrations=[]; transitions=[]
    warmup=cfg['benchmark']['warmup']
    for index,(c,th,n,cid) in enumerate(complete_configs(cs,cfg)):
        # Warm up inference using a separate causally calibrated Runner.
        warm=ready_runner(c,cfg,next(iter(parts.values())),th,n)
        for row in [x for x in next(iter(parts.values())) if x['elapsed_s']>cfg['calibration_s']][:warmup]:
            warm.step(row)
        del warm
        measured=defaultdict(list); caltimes=[]; counts=Counter(); events=0
        cpu0=time.process_time(); wall0=time.perf_counter(); maxrss=proc.memory_info().rss
        for repeat in range(args.full_passes):
            for sid,part in parts.items():
                r=new_runner(c,cfg,th,n)
                for row in part:
                    r.step(row); timing=r.timings[-1]; condition=row['state']
                    counts[(sid,condition,timing.get('state_before','UNKNOWN'),timing.get('state_after','UNKNOWN'))]+=1
                    if row['elapsed_s']<=cfg['calibration_s']: caltimes.append(timing['processing_ms'])
                    else: measured[condition].append(timing)
                events+=sum(len(state.events) for state in r.states.values())
                maxrss=max(maxrss,proc.memory_info().rss)
                del r
        wall=time.perf_counter()-wall0; cpu=time.process_time()-cpu0; p95s=[]
        for condition,ts in measured.items():
            p=percentiles([x['processing_ms'] for x in ts],'pipeline'); p95s.append(p['pipeline_p95_ms'])
            conditions.append(dict(config_id=cid,candidate_id=c['candidate_id'],condition=condition,
                measured_messages=len(ts),full_passes=args.full_passes,**p,
                **percentiles([x['model_only_ms'] for x in ts if x.get('inference_executed',True)],'model_only')))
        calp=percentiles(caltimes,'calibration')
        if caltimes: p95s.append(calp['calibration_p95_ms'])
        all_ts=[t for ts in measured.values() for t in ts]
        pooled=percentiles([x['processing_ms'] for x in all_ts],'pooled_pipeline')
        resources.append(dict(config_id=cid,candidate_id=c['candidate_id'],decision_threshold=th,confirmation=n,
            model_bytes=c['model_bytes'],full_passes=args.full_passes,measured_messages=len(all_ts),
            calibration_messages=len(caltimes),pipeline_p95_ms=max(p95s),**pooled,
            pipeline_p50_ms=pooled['pooled_pipeline_p50_ms'],pipeline_p99_ms=pooled['pooled_pipeline_p99_ms'],
            **percentiles([x['model_only_ms'] for x in all_ts if x.get('inference_executed',True)],'model_only'),
            observed_alarm_events=events,total_process_rss_bytes=maxrss,model_incremental_rss_bytes=None,
            cpu_one_core_percent=100*cpu/wall,elapsed_wall_s=wall))
        calibrations.append(dict(config_id=cid,messages=len(caltimes),**calp))
        transitions.extend(dict(config_id=cid,session_id=sid,condition=cond,state_before=a,state_after=b,
            observations=count,source='empirical chronological trace') for (sid,cond,a,b),count in counts.items())
        if (index+1)%30==0: print('Resource configurations',index+1,flush=True)
    target=ROOT/'results/tables'
    for name,records in [('resources',resources),('resources_by_condition',conditions),
                         ('resource_calibration',calibrations),('resource_transitions',transitions)]:
        pd.DataFrame(records).to_csv(target/f'{name}.csv',index=False)
    stress=[]; trace=[]
    if not args.skip_stress:
        chosen=[c for c in cs if c['candidate_id'] in ['DT_f3_p2','KNN_f3_p1','SVM_f3_p2','RF_f3_p3','RULE_noise_t2']]
        for c in chosen:
            for hz in cfg['benchmark']['stress_hz']:
                result,samples=stress_run(c,cfg,parts['jamming'],hz,args.stress_messages)
                stress.append(result); trace.extend(dict(candidate_id=c['candidate_id'],requested_hz=hz,**s) for s in samples)
        pd.DataFrame(stress).to_csv(target/'stress.csv',index=False)
        pd.DataFrame(trace).to_csv(target/'stress_timings.csv',index=False)
    write_json(ROOT/'experiments/resource_run.json',dict(
        platform=platform.platform(),machine=platform.machine(),processor=platform.processor(),python=platform.python_version(),
        cpu_logical=psutil.cpu_count(),ram_bytes=psutil.virtual_memory().total,configurations=len(resources),
        session_rows={sid:len(p) for sid,p in parts.items()},full_passes=args.full_passes,warmup_messages=warmup,
        stress_messages=args.stress_messages,benchmark=cfg['benchmark'],
        quantile_method='numpy percentile linear; descriptive, not confidence bounds',
        timing='one isolated complete configuration sequentially; every chronological raw-derived row in all 3 sessions; fresh causal calibration per session/pass; batch=1 Runner.step; per-message timing excludes model load/file I/O',
        resource_gate='pipeline_p95_ms = max of empirical condition P95s (benign, jamming, spoofing) and calibration P95; synthetic transitions excluded',
        total_rss_scope='whole benchmark process Python/libraries/current model/measurement objects and allocator caches; sampled process RSS maximum, not intrinsic model footprint',
        cpu_scope='benchmark process CPU/wall includes loop/model initialization/measurement bookkeeping; percent of one core; producer CPU excluded',
        incremental_model_rss='unavailable; not reliably isolated',
        recovery_scope='observed transitions only; attack end unknown, no verified jammer-off recovery ground truth; unobserved transitions (including UNAVAILABLE if absent) not covered; only 19 spoofing observations per full pass',
        stress='synthetic compressed full jamming trace, no detection claim; independent spawned producer/unbounded IPC queue; actual_arrival_time = producer queue enqueue, so IPC included; all due/enqueue/receipt/start/ready clocks retained',
        offered_rate_validity='VALID only if actual offered rate within 5% requested AND producer lateness P95 <= interarrival interval; otherwise INVALID_OFFERED_RATE, not evidence of requested-rate capacity',
        stress_skipped=args.skip_stress,physical_transport_included=False,
        run_id=cfg.get('run_id'),protocol_version=cfg.get('protocol_version'),
        input_hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in [
            ROOT/'configs/experiment.json',ROOT/'configs/sessions.json',ROOT/'experiments/candidates.json',
            ROOT/'data/derived/development.csv',ROOT/'src/gnss_jamming/core.py',ROOT/'src/gnss_jamming/replay.py',
            ROOT/'src/gnss_jamming/benchmark.py',ROOT/'requirements-lock.txt',ROOT/'experiments/environment.json',
            *[ROOT/'experiments/models'/f'{c["candidate_id"]}.pkl' for c in cs]]}))
    print('Resource benchmark complete',flush=True)

if __name__=='__main__': main()
