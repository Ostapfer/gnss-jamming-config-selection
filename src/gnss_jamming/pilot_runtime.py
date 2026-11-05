"""Versioned Docker pilot runtime. Source/collector and detector are separate cgroups.

No training and no replacement of the historical replay. The detector executes
the original Runner.step with explicit model input paths and bounded histories.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import socket
import struct
import threading
import time
import traceback
import uuid
from collections import deque
from bisect import bisect_right


def now():
    return time.perf_counter()


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, 'tolist'):
        return clean(value.tolist())
    if hasattr(value, 'item'):
        return clean(value.item())
    return value


def dump(path, value):
    path=Path(path); temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(clean(value), ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    os.replace(temporary,path)


def emit(stream, value):
    stream.write(json.dumps(clean(value), allow_nan=False, separators=(',', ':'))+'\n')
    stream.flush()


def send_frame(conn, value, policy):
    payload = json.dumps(clean(value), allow_nan=False, separators=(',', ':')).encode()
    if len(payload)+4 > policy['maximum_frame_bytes']:
        raise ValueError(f'oversized frame: {len(payload)} bytes')
    conn.sendall(struct.pack('!I', len(payload))+payload)
    return len(payload)+4


def receive_exact(conn, size, allow_eof=False):
    result = bytearray()
    while len(result) < size:
        part = conn.recv(size-len(result))
        if not part:
            if allow_eof and not result:
                return None
            raise EOFError('partial frame / connection closed')
        result.extend(part)
    return bytes(result)


def receive_frame(conn, policy):
    header = receive_exact(conn, 4, allow_eof=True)
    if header is None:
        return None
    size, = struct.unpack('!I', header)
    if size+4 > policy['maximum_frame_bytes']:
        raise ValueError(f'oversized received frame: {size}')
    return json.loads(receive_exact(conn, size))


def configured_socket(policy):
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    for option in (socket.SO_SNDBUF, socket.SO_RCVBUF):
        conn.setsockopt(socket.SOL_SOCKET, option, policy['socket_buffer_bytes_requested'])
    conn.settimeout(policy['socket_timeout_s'])
    return conn


def socket_buffers(conn):
    return {'send_bytes': conn.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF),
            'receive_bytes': conn.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)}


def file_text(path):
    path = Path(path)
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None


class BoundedIngress:
    """Atomic acceptance timestamp; source never waits on detector/network IO."""
    def __init__(self, capacity):
        self.capacity = capacity
        self.items = deque()
        self.condition = threading.Condition()

    def offer(self, record):
        with self.condition:
            if len(self.items) >= self.capacity:
                return None
            self.items.append(record)
            record['accepted_ingress_available'] = now()
            self.condition.notify()
            return record['accepted_ingress_available']

    def get(self, timeout):
        with self.condition:
            if not self.condition.wait_for(lambda: bool(self.items), timeout):
                raise queue.Empty
            return self.items.popleft()

    def qsize(self):
        with self.condition:
            return len(self.items)


def kernel_identity():
    clock = time.get_clock_info('perf_counter')
    return {'boot_id': file_text('/proc/sys/kernel/random/boot_id'),
            'time_namespace': os.readlink('/proc/self/ns/time'),
            'cgroup_namespace': os.readlink('/proc/self/ns/cgroup'),
            'cgroup_membership': file_text('/proc/self/cgroup'),
            'cgroup_inode': own_cgroup_root().stat().st_ino,
            'own_cgroup_root':str(own_cgroup_root()),
            'perf_counter': {'implementation': clock.implementation,
                             'monotonic': clock.monotonic, 'adjustable': clock.adjustable,
                             'resolution_s': clock.resolution}}


def own_cgroup_root():
    membership = file_text('/proc/self/cgroup') or ''
    path = next((line.split('::',1)[1] for line in membership.splitlines() if line.startswith('0::')),None)
    if path is None:
        raise RuntimeError('cgroup v2 membership unavailable')
    root = Path('/sys/fs/cgroup')
    own = root/path.lstrip('/')
    if not own.is_dir():
        raise RuntimeError(f'own cgroup not visible: {path}')
    return own


def counters(root=None):
    root = own_cgroup_root() if root is None else Path(root)
    result = {}
    for name in ['cpu.max', 'cpu.stat', 'memory.max', 'memory.current', 'memory.peak',
                 'memory.swap.max', 'memory.events', 'pids.current']:
        text = file_text(root/name)
        if text is None:
            result[name] = None  # unsupported is not zero
        elif name in ['cpu.stat', 'memory.events']:
            result[name] = {k: int(v) for k, v in (line.split() for line in text.splitlines())}
        else:
            result[name] = int(text) if text.isdigit() else text
    return result


def records(input_root, session_id):
    output = []
    with (Path(input_root)/'data/derived/development.csv').open() as stream:
        for row in csv.DictReader(stream):
            if row['session_id'] != session_id:
                continue
            converted = {}
            for key, value in row.items():
                try:
                    converted[key] = float(value) if value else None
                except ValueError:
                    converted[key] = value
            output.append(converted)
    if not output:
        raise ValueError('session has no rows')
    return sorted(output, key=lambda row: row['elapsed_s'])


def parse_config_id(config_id):
    candidate_id, rest = config_id.rsplit('_d', 1)
    threshold, count = rest.rsplit('_c', 1)
    return candidate_id, float(threshold), int(count)


def make_runner(input_root, config_id, policy, bounded=True):
    from collections import deque
    import numpy as np
    from .core import Calibration
    from .replay import Runner
    root = Path(input_root)
    candidate_id, threshold, count = parse_config_id(config_id)
    cfg = json.loads((root/'configs/experiment.json').read_text())
    candidates = json.loads((root/'experiments/candidates.json').read_text())
    candidate = next(c for c in candidates if c['candidate_id'] == candidate_id)
    runner = Runner(candidate, cfg, decision_threshold=threshold, confirmation=count,
                    input_root=root)
    if bounded:
        class BoundedCalibration(Calibration):
            def update(self, timestamp, values):
                if self.failed:
                    return False
                x = np.asarray(values, dtype=float)
                within = self.start is None or timestamp-self.start <= self.cfg['calibration_s']
                if within and np.isfinite(x).all() and len(self.rows) >= policy['calibration_capacity_observations']:
                    self.failed = True
                    self.rows.clear()
                    return False
                ready = super().update(timestamp, values)
                if self.baseline is not None or self.failed:
                    self.rows.clear()
                return ready
        runner.cal = BoundedCalibration(candidate['features'], cfg)
        runner.timings = deque(maxlen=policy['detector_history_capacity'])
        runner.predictions = deque(maxlen=policy['detector_history_capacity'])
        for state in runner.states.values():
            state.events = deque(maxlen=policy['detector_history_capacity'])
    return runner


def runner_step(runner, row, origin=None, arrival=None, scheduled=None):
    import numpy as np
    pipeline_start = now()
    row = {k: np.nan if v is None else v for k, v in row.items()}
    state = next(iter(runner.states.values()))
    previous = state.current
    runner.step(row, arrival=arrival, origin=origin, scheduled=scheduled)
    timing = dict(runner.timings[-1])
    timing['inner_runner_processing_ms'] = timing['processing_ms']
    timing['processing_start_time'] = pipeline_start
    timing['processing_ms'] = (timing['processing_end_time']-pipeline_start)*1000
    timing['queue_ms'] = 0. if arrival is None else max(0.,(pipeline_start-arrival)*1000)
    return {'score': runner.predictions[-1]['score'], 'state': runner.state_label(),
            'positives': state.positives, 'negatives': state.negatives,
            'readiness_success': runner.cal.baseline is not None and not runner.cal.failed,
            'calibration_failed': runner.cal.failed,
            'baseline': runner.cal.baseline,
            'event_started': dict(state.current) if timing['event_ready_time'] is not None else None,
            'event_closed': dict(previous) if previous is not None and state.current is None else None,
            'current_event': dict(state.current) if state.current is not None else None,
            'timing': timing,
            'storage': {'timings': len(runner.timings), 'predictions': len(runner.predictions),
                        'events': len(state.events), 'calibration_rows': len(runner.cal.rows)}}


def parity(input_root, scope_path, policy_path, output):
    import numpy as np
    scope = json.loads(Path(scope_path).read_text()); policy = json.loads(Path(policy_path).read_text())
    results = []
    for config_id in scope['configs']:
        for sid in ['jamming', 'spoofing', 'benign']:
            old = make_runner(input_root, config_id, policy, bounded=False)
            new = make_runner(input_root, config_id, policy, bounded=True)
            rows = records(input_root, sid)
            for sequence, row in enumerate(rows):
                a, b = runner_step(old, row), runner_step(new, row)
                # Score tolerance never excuses a changed threshold crossing or state.
                for key in ['state', 'positives', 'negatives', 'readiness_success', 'calibration_failed',
                            'event_started', 'event_closed', 'current_event']:
                    assert clean(a[key]) == clean(b[key]), (config_id, sid, sequence, key)
                if a['score'] is None:
                    assert b['score'] is None
                else:
                    assert np.isclose(a['score'], b['score'], atol=policy['score_atol'], rtol=policy['score_rtol'])
                    _, threshold, _ = parse_config_id(config_id)
                    assert (a['score'] >= threshold) == (b['score'] >= threshold)
                if a['baseline'] is not None:
                    np.testing.assert_array_equal(a['baseline'], b['baseline'])
                assert b['storage']['timings'] <= 1 and b['storage']['predictions'] <= 1 and b['storage']['events'] <= 1
                assert b['storage']['calibration_rows'] <= policy['calibration_capacity_observations']
            results.append({'config_id': config_id, 'session_id': sid, 'rows': len(rows),
                            'full_trace_parity': True})
    dump(output, {'gate': 'G2', 'status': 'PASS', 'comparisons': results,
                  'rows_compared': sum(r['rows'] for r in results),
                  'original_runner_step_reused': True, 'input_root_explicit': True,
                  'threshold_crossings_states_events_exact': True,
                  'score_atol': policy['score_atol'], 'score_rtol': policy['score_rtol']})


def connect(path, policy):
    start = now()
    while True:
        conn = configured_socket(policy)
        try:
            conn.connect(str(path))
            return conn
        except (FileNotFoundError, ConnectionRefusedError):
            conn.close()
            if now()-start > policy['startup_timeout_s']:
                raise TimeoutError(f'connect timeout: {path}')
            time.sleep(.05)


def detector(spec, input_root):
    policy = spec['policy']; transport = Path('/ipc')
    result_conn = connect(transport/'result.sock', policy)
    def lifecycle(phase):
        send_frame(result_conn, {'kind': 'lifecycle', 'phase': phase, 'time': now(),
                                 'cgroup': counters()}, policy)
    lifecycle('before_imports')
    if spec.get('test_fail_start'):
        raise RuntimeError('controlled startup failure fixture')
    import numpy as np
    import psutil
    from threadpoolctl import threadpool_info
    from .replay import Runner  # import dependency footprint belongs to detector
    lifecycle('after_imports')
    model_id, _, _ = parse_config_id(spec['config_id'])
    model_path = Path(input_root)/'experiments/models'/f'{model_id}.pkl'
    assert hashlib.sha256(model_path.read_bytes()).hexdigest() == spec['model_sha256']
    runner = make_runner(input_root, spec['config_id'], policy)
    pools = threadpool_info()
    assert all(p.get('num_threads') == 1 for p in pools), pools
    lifecycle('after_model_load')
    conn = connect(transport/'data.sock', policy)
    send_frame(conn, {'kind': 'hello', 'identity': kernel_identity(), 'cgroup': counters(),
                      'threads': pools, 'socket_buffers': socket_buffers(conn),
                      'result_socket_buffers': socket_buffers(result_conn)}, policy)
    origin = None; seen = 0; calibrated_marker = False
    while True:
        message = receive_frame(conn, policy)
        received = now()
        if message is None:
            raise EOFError('missing source completion marker')
        if message['kind'] == 'ping':
            send_frame(conn, {'kind': 'pong', 'worker_time': now(), 'ping': message['ping']}, policy)
        elif message['kind'] == 'start':
            origin = message['origin']
        elif message['kind'] == 'row':
            if origin is None:
                raise RuntimeError('row before clock origin')
            delay = spec.get('processing_delay_ms', 0)
            if delay:
                time.sleep(delay/1000)
            result = runner_step(runner, message['row'], origin=origin,
                                 arrival=message['accepted_ingress_available'], scheduled=message['scheduled_due'])
            result.update(kind='result', sequence=message['sequence'], consumer_received=received,
                          accepted_ingress_available=message['accepted_ingress_available'],
                          source_attempt=message['source_attempt'], scheduled_due=message['scheduled_due'],
                          transport_send_attempt=message['transport_send_attempt'],
                          elapsed_s=message['row']['elapsed_s'], condition=message['row'].get('state'),
                          cpu_process_s=time.process_time(), process_rss_bytes=psutil.Process().memory_info().rss)
            send_frame(result_conn, result, policy)
            seen += 1
            if runner.cal.baseline is not None and not calibrated_marker:
                lifecycle('after_calibration'); calibrated_marker = True
            if spec.get('test_fail_after') == seen:
                raise RuntimeError('controlled midstream exit fixture')
        elif message['kind'] == 'end':
            lifecycle('final')
            send_frame(result_conn, {'kind': 'complete', 'processed': seen, 'time': now(),
                                     'readiness_success': runner.cal.baseline is not None and not runner.cal.failed,
                                     'calibration_failed': runner.cal.failed,
                                     'current_event': next(iter(runner.states.values())).current,
                                     'cpu_process_s':time.process_time(),
                                     'process_rss_bytes':psutil.Process().memory_info().rss}, policy)
            break
        else:
            raise ValueError('unknown protocol frame')
    conn.close(); result_conn.close()


def locate_cgroup(container_id, expected_inode=None):
    root = Path('/sys/fs/cgroup')
    for base, directories, _ in os.walk(root):
        path = Path(base)
        if container_id in path.name and (expected_inode is None or path.stat().st_ino == expected_inode):
            return path
    raise RuntimeError('external monitor cannot resolve detector cgroup; host cgroup namespace required')


def quantiles(values):
    if not values:
        return {'p50': None, 'p95': None, 'p99': None, 'max': None}
    ordered = sorted(values)
    def at(q):
        position = q*(len(ordered)-1); lo = math.floor(position); hi = math.ceil(position)
        return ordered[lo]+(ordered[hi]-ordered[lo])*(position-lo)
    return {'p50': at(.5), 'p95': at(.95), 'p99': at(.99), 'max': max(values)}


def summarize(spec, output):
    def load(name):
        path = output/name
        return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
    source = load('source.ndjson'); trace = load('trace.ndjson'); transport = load('transport.ndjson')
    samples = load('cgroups.ndjson'); events = []
    for row in trace:
        if row['kind'] != 'result':
            continue
        if row['event_started'] is not None:
            events.append(dict(row['event_started']))
        if row['event_closed'] is not None:
            match = next(e for e in reversed(events) if e['start_s'] == row['event_closed']['start_s'])
            match.update(row['event_closed'])
    results = [r for r in trace if r['kind'] == 'result']
    complete = next((r for r in reversed(trace) if r['kind'] == 'complete'), None)
    origin_record = json.loads((output/'clock.json').read_text()) if (output/'clock.json').exists() else {}
    origin = origin_record.get('origin')
    session = spec['session']; onset = spec.get('onset_s'); end = spec['coverage_s']
    cfg_cal = spec['calibration_s']
    measured = spec['workload']=='ORIGINAL_RATE_MEASURED'
    conditions = [('benign', cfg_cal, end if onset is None else onset)] if measured else []
    if measured and session['attack_type'] == 'spoofing':
        conditions.append(('spoofing', onset, end))
    condition_metrics = []
    for name, start, stop in conditions:
        starts = [e for e in events if start <= e['start_s'] < stop]
        durations = [max(0., min(stop, e['end_s'] if e['end_s'] is not None else stop)-e['start_s']) for e in starts]
        active = sum(max(0., min(stop,e['end_s'] if e['end_s'] is not None else stop)-max(start,e['start_s'])) for e in events)
        exposure = max(0., stop-start)
        condition_metrics.append({'condition': name, 'exposure_s': exposure, 'false_events': len(starts),
                                  'false_alarm_events_per_hour': len(starts)*3600/exposure if exposure else None,
                                  'false_active_s': active, 'false_event_duration_max_s': max(durations, default=0.),
                                  'false_events_right_censored': sum(e['end_s'] is None or e['end_s'] > stop for e in starts)})
    detections = [e for e in events if onset is not None and e['start_s'] >= onset]
    delay = min((e['ready_s']-onset for e in detections), default=None)
    source_lateness = [(s['source_attempt']-s['scheduled_due'])*1000 for s in source]
    source_q = quantiles(source_lateness)
    accepted = {s['sequence'] for s in source if s['accepted']}
    processed = {s['sequence'] for s in results}
    dropped = [s for s in source if not s['accepted']]
    pipeline = [r['timing']['end_to_end_ms'] for r in results]
    processing = [r['timing']['processing_ms'] for r in results]
    queue_ms = [r['timing']['queue_ms'] for r in results]
    accepted_times=[s['accepted_ingress_available'] for s in source if s['accepted']]
    waiting_counts=[max(0,bisect_right(accepted_times,r['timing']['processing_start_time'])-i-1)
                    for i,r in enumerate(results)]
    model = [r['timing']['model_only_ms'] for r in results if r['timing']['inference_executed']]
    latency_conditions = {}
    for r in results:
        label = r['condition'] if r['timing']['inference_executed'] else 'calibration_or_unavailable'
        latency_conditions.setdefault(label, []).append(r['timing']['processing_ms'])
    memory = [s['detector'].get('memory.current') for s in samples if isinstance(s['detector'].get('memory.current'), int)]
    driver_memory = [s['driver'].get('memory.current') for s in samples if isinstance(s['driver'].get('memory.current'), int)]
    source_valid = bool(source and source_q['p95'] <= spec['policy']['source_lateness_p95_limit_ms']
                        and source_q['max'] <= spec['policy']['source_lateness_max_limit_ms'])
    expected_messages = spec['expected_messages'] if measured else min(spec.get('synthetic_messages',12),spec['expected_messages'])
    source_sequences = [s['sequence'] for s in source]
    lifecycle = [s for s in trace if s['kind']=='lifecycle']
    phases = {s['phase'] for s in lifecycle}
    required_phases = {'before_imports','after_imports','after_model_load','final'}
    if complete and complete.get('readiness_success'):
        required_phases.add('after_calibration')
    external_samples_healthy = bool(samples and memory and driver_memory)
    identity_proof = (output/'identities.json').is_file() and (output/'clock.json').is_file()
    evidence_checks = {'completion_marker':complete is not None,
        'source_sequences_complete':source_sequences == list(range(expected_messages)),
        'accepted_processed_match':accepted==processed and len(results)==len(processed),
        'clock_identity_proof':identity_proof,'lifecycle_complete':required_phases <= phases,
        'external_monitor_samples':external_samples_healthy}
    evidence_complete = all(evidence_checks.values())
    status = 'COMPLETE' if evidence_complete and not dropped else 'IN_SCOPE_PIPELINE_FAILURE'
    if not evidence_complete:
        status = 'INCOMPLETE_EVIDENCE'
    result = {'protocol': 'docker-pilot-v1', 'workload': spec['workload'],
              'config_id': spec['config_id'], 'session_id': session['session_id'],
              'status': status, 'evidence_complete': evidence_complete,'evidence_checks':evidence_checks,
              'source_schedule_valid': source_valid,
              'source_invalid_does_not_erase_detector_drop_outcomes': True,
              'source_lateness_ms': source_q, 'offered_messages': len(source),
              'accepted_messages': len(accepted), 'processed_messages': len(processed),
              'dropped_messages': len(dropped), 'missing_accepted_sequences': sorted(accepted-processed),
              'readiness_success': complete.get('readiness_success') if complete else None,
              'eligible_episode': measured and session['attack_type'] == 'jamming' and onset is not None and end >= onset+10,
              'confirmed_delay_s': delay if session['attack_type'] == 'jamming' else None,
              'information_delay_s': min((e['start_s']-onset for e in detections),default=None) if session['attack_type']=='jamming' else None,
              'active_before_onset': any(e['start_s']<onset and (e['end_s'] is None or e['end_s']>onset) for e in events) if onset is not None else False,
              'conditions': condition_metrics, 'events': events,
              'processing_ms': quantiles(processing), 'ingress_to_processing_completion_ms': quantiles(pipeline),
              'queue_ms': quantiles(queue_ms), 'model_inference_ms': quantiles(model),
              'maximum_total_accepted_waiting_messages':max(waiting_counts,default=0),
              'backlog_scope':'all accepted ingress messages not yet started, including application and kernel transport buffers; excludes current processing message',
              'condition_processing_ms': {k:quantiles(v) for k,v in latency_conditions.items()},
              'detector_memory_current_sampled_peak_bytes': max(memory) if memory else None,
              'driver_memory_current_sampled_peak_bytes': max(driver_memory) if driver_memory else None,
              'detector_lifecycle':lifecycle,
              'detector_cgroup_stream_cpu_percent':None,
              'external_sample_interval_s': spec['policy']['external_monitor_interval_s'],
              'maximum_observed_frame_bytes': max((x.get('frame_bytes',0) for x in transport),default=0),
              'physical_transport_included': False, 'independent_validation': False,
              'statistical_evidence': 'INSUFFICIENT EVIDENCE', 'clock_origin': origin}
    usable=[s for s in samples if s['detector'].get('cpu.stat') is not None]
    if len(usable)>1 and usable[-1]['time']>usable[0]['time']:
        duration=usable[-1]['time']-usable[0]['time']
        cpu_delta=usable[-1]['detector']['cpu.stat']['usage_usec']-usable[0]['detector']['cpu.stat']['usage_usec']
        result['detector_cgroup_stream_cpu_percent']=100*cpu_delta/1e6/duration
        result['cpu_measurement_scope']='external samples from cgroup appearance through last available sample; includes startup/instrumentation'
        result['driver_cgroup_cpu_percent']=100*(usable[-1]['driver']['cpu.stat']['usage_usec']-usable[0]['driver']['cpu.stat']['usage_usec'])/1e6/duration
        result['driver_cpu_measurement_scope']='independent source/collector container, includes external monitor and file collection'
    result['model_bytes']=spec['model_bytes']
    dump(output/'summary.json', result)
    return result


def driver(spec, input_root, output):
    import psutil
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    policy = spec['policy']; transport_root = Path('/transport'); socket_root = Path('/ipc')
    ready_file = output/'driver_ready.json'
    servers = []
    for name in ['data.sock', 'result.sock']:
        path = socket_root/name
        if path.exists():
            path.unlink()
        server = configured_socket(policy); server.bind(str(path)); server.listen(1)
        server.settimeout(policy['startup_timeout_s']); servers.append(server)
    data_server, result_server = servers
    dump(ready_file, {'status':'LISTENING', 'identity':kernel_identity(), 'time':now()})
    state = {'errors': [], 'results_complete': False}; finished = threading.Event()
    result_connection = [None]
    def collector():
        try:
            conn,_ = result_server.accept(); result_connection[0] = conn
            conn.settimeout(policy['startup_timeout_s'])
            with (output/'trace.ndjson').open('w') as stream:
                while True:
                    record = receive_frame(conn, policy)
                    if record is None:
                        raise EOFError('detector result EOF without complete marker')
                    record['collector_received'] = now(); emit(stream, record)
                    if record['kind'] == 'complete':
                        state['results_complete'] = True; break
        except Exception as exc:
            state['errors'].append({'component':'collector','error':repr(exc)})
        finally:
            finished.set()
    collect_thread = threading.Thread(target=collector, daemon=True); collect_thread.start()
    monitor_stop = threading.Event(); monitor_thread = None; data_conn = None
    source_stream = None; transport_stream = None
    try:
        container_id = json.loads((transport_root/'detector_identity.json').read_text())['container_id']
        monitor_state = {'path':None}
        def monitor():
            try:
                with (output/'cgroups.ndjson').open('w') as stream:
                    while not monitor_stop.is_set():
                        if monitor_state['path'] is None:
                            try: monitor_state['path'] = locate_cgroup(container_id)
                            except (RuntimeError,FileNotFoundError): pass
                        emit(stream, {'time':now(),
                                      'detector':counters(monitor_state['path']) if monitor_state['path'] is not None else {},
                                      'driver':counters(), 'driver_process_cpu_s':time.process_time(),
                                      'driver_process_rss_bytes':psutil.Process().memory_info().rss})
                        monitor_stop.wait(policy['external_monitor_interval_s'])
            except Exception as exc:
                state['errors'].append({'component':'external_monitor','error':repr(exc)})
        monitor_thread = threading.Thread(target=monitor, daemon=True); monitor_thread.start()
        data_conn,_ = data_server.accept(); data_conn.settimeout(policy['socket_timeout_s'])
        hello = receive_frame(data_conn, policy)
        if hello is None or hello['kind'] != 'hello':
            raise RuntimeError('no detector hello')
        driver_identity = kernel_identity(); detector_identity = hello['identity']
        assert driver_identity['boot_id'] == detector_identity['boot_id']
        assert driver_identity['time_namespace'] == detector_identity['time_namespace']
        assert driver_identity['cgroup_inode'] != detector_identity['cgroup_inode']
        assert driver_identity['perf_counter']['monotonic'] and detector_identity['perf_counter']['monotonic']
        detector_cgroup = locate_cgroup(container_id, detector_identity['cgroup_inode'])
        actual = counters(detector_cgroup)
        quota = spec['profile']['cpu_quota_us']; expected = 'max' if quota is None else str(quota)
        assert actual['cpu.max'] == expected+' '+str(spec['cpu_period_us']), actual
        assert actual['memory.max'] == spec['profile']['memory_mib']*2**20
        assert actual['memory.swap.max'] == 0
        driver_limits=counters()
        assert driver_limits['cpu.max']=='max '+str(spec['cpu_period_us'])
        assert driver_limits['memory.max']==policy['driver_memory_mib']*2**20
        assert driver_limits['memory.swap.max']==0
        dump(output/'identities.json', {'driver':driver_identity,'detector':hello,
             'detector_host_cgroup_path':str(detector_cgroup),'actual_detector_limits':actual,
             'driver_limits':driver_limits, 'driver_socket_buffers':socket_buffers(data_conn)})
        pings = []
        for index in range(policy['clock_ping_count']):
            before = now(); send_frame(data_conn, {'kind':'ping','ping':index}, policy)
            pong = receive_frame(data_conn, policy); after = now()
            assert pong['kind']=='pong' and pong['ping']==index
            worker_time = pong['worker_time']
            assert before <= worker_time <= after
            pings.append({'driver_before':before,'worker_time':worker_time,'driver_after':after,
                          'rtt_ms':(after-before)*1000,
                          'offset_interval_s':[worker_time-after,worker_time-before]})
        assert min(p['rtt_ms'] for p in pings)<=policy['clock_ping_rtt_limit_ms'], 'clock precision insufficient; quota latency is not source invalidity'
        origin = now()+.5
        dump(output/'clock.json', {'origin':origin,'pings':pings,'same_time_namespace':True,
                                  'same_boot':True,'distinct_cgroups':True,
                                  'best_rtt_ms':min(p['rtt_ms'] for p in pings),
                                  'clock_offset_intersection_s':[max(p['offset_interval_s'][0] for p in pings),
                                                                 min(p['offset_interval_s'][1] for p in pings)]})
        send_frame(data_conn, {'kind':'start','origin':origin}, policy)
        data = records(input_root, spec['session']['session_id'])
        if spec['workload'] != 'ORIGINAL_RATE_MEASURED':
            data = data[:spec.get('synthetic_messages',12)]
        ingress = BoundedIngress(policy['ingress_capacity_messages'])
        producer_finished = threading.Event(); writer_error = threading.Event()
        source_stream = (output/'source.ndjson').open('w')
        transport_stream = (output/'transport.ndjson').open('w')
        def writer():
            try:
                while True:
                    try: record = ingress.get(timeout=.1)
                    except queue.Empty:
                        if producer_finished.is_set(): break
                        continue
                    attempted = now(); record['transport_send_attempt'] = attempted
                    size = send_frame(data_conn, record, policy); done = now()
                    emit(transport_stream, {'sequence':record['sequence'],'send_attempt':attempted,
                         'send_done':done,'send_block_ms':(done-attempted)*1000,'frame_bytes':size,
                         'socket_buffers':socket_buffers(data_conn)})
                send_frame(data_conn, {'kind':'end'}, policy)
            except Exception as exc:
                state['errors'].append({'component':'transport','error':repr(exc)})
                writer_error.set()
        writer_thread = threading.Thread(target=writer, daemon=True); writer_thread.start()
        for sequence,row in enumerate(data):
            due = origin+(row['elapsed_s'] if spec['workload']=='ORIGINAL_RATE_MEASURED' else sequence/spec.get('synthetic_hz',50))
            time.sleep(max(0., due-now()))
            attempted = now(); accepted_at = None
            record = {'kind':'row','sequence':sequence,'row':row,'scheduled_due':due,
                      'source_attempt':attempted,'accepted_ingress_available':None}
            # offer() timestamps atomic bounded acceptance, independently of IO.
            accepted = False; reason = 'ingress_full'
            if writer_error.is_set(): reason='transport_failed'
            else:
                accepted_at = ingress.offer(record); accepted = accepted_at is not None
            emit(source_stream, {'sequence':sequence,'scheduled_due':due,'source_attempt':attempted,
                 'accepted':accepted,'accepted_ingress_available':accepted_at if accepted else None,
                 'application_queue_depth_after_attempt':ingress.qsize(),
                 'drop_reason':None if accepted else reason})
        if spec['workload']=='ORIGINAL_RATE_MEASURED':
            time.sleep(max(0., origin+spec['coverage_s']-now()))
        producer_finished.set(); writer_thread.join(policy['completion_grace_s'])
        if writer_thread.is_alive():
            state['errors'].append({'component':'transport','error':'drain timeout'})
        if not finished.wait(policy['completion_grace_s']):
            state['errors'].append({'component':'collector','error':'completion timeout'})
    except Exception as exc:
        state['errors'].append({'component':'driver','error':repr(exc),'traceback':traceback.format_exc()})
    finally:
        monitor_stop.set()
        if monitor_thread is not None: monitor_thread.join(2)
        for stream in [source_stream,transport_stream]:
            if stream is not None: stream.close()
        for conn in [data_conn,result_connection[0],*servers]:
            if conn is not None:
                try: conn.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                conn.close()
        collect_thread.join(2)
        dump(output/'driver_status.json', {'complete_marker':state['results_complete'],
              'errors':state['errors'],'final_driver_counters':counters()})
        summary = summarize(spec, output)
        summary['driver_errors'] = state['errors']
        if state['errors']: summary['status']='INCOMPLETE_EVIDENCE'
        dump(output/'summary.json',summary)
    return 0 if state['results_complete'] and not state['errors'] else 2


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('mode',choices=['driver','detector','parity'])
    parser.add_argument('--spec',type=Path); parser.add_argument('--input-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('/outputs'))
    parser.add_argument('--scope',type=Path); parser.add_argument('--policy',type=Path)
    args=parser.parse_args()
    if args.mode=='parity':
        parity(args.input_root,args.scope,args.policy,args.output);return
    spec=json.loads(args.spec.read_text())
    if args.mode=='detector': detector(spec,args.input_root)
    else: raise SystemExit(driver(spec,args.input_root,args.output))


if __name__=='__main__':
    main()
