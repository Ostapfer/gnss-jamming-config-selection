#!/usr/bin/env python3
"""Build, verify, freeze and sequentially execute the user-selected Docker pilot.

Standard-library host controller. All model execution is in the frozen Linux
image. No training, legacy-output overwrite, remote publication or matrix up.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import threading
import signal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from gnss_jamming.pilot_runtime import dump, records, parse_config_id

PARENT_IMAGE = 'nulp-gnss:limits-v1'
EXPECTED_PARENT = 'sha256:9655423c10c1b9c522c89ba4e21e1736e25f63e7b901bab89c1db18e1e1ff3f3'
IMAGE = 'nulp-gnss:pilot-v1'
SCOPE = ROOT/'docs/review/PILOT_SCOPE.json'
POLICY = ROOT/'docker/pilot/policy.json'
COMPOSE = ROOT/'docker/pilot/compose.yaml'


def timestamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(command, env=None, timeout=120, check=True):
    result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f'Command failed {command[:4]}: {result.stderr[-3000:]} {result.stdout[-1000:]}')
    return result


def docker_json(*args):
    return json.loads(execute(['docker',*args]).stdout)


def resolve_input(explicit):
    if explicit:
        path = Path(explicit).expanduser().resolve()
    else:
        # Parse one literal local setting; never source/execute a shell file.
        settings = {}
        for line in (ROOT/'docker/.env.local').read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key,value = line.split('=',1); settings[key.strip()] = value.strip().strip('"\'')
        path = Path(settings['GNSS_INPUT_ROOT']).expanduser().resolve()
    if not (path/'data/derived/development.csv').is_file():
        raise ValueError('Input root lacks prepared chronological development.csv')
    return path


def input_hashes(input_root):
    source_manifest = input_root.parent/'frozen_run_protocol.json'
    if not source_manifest.is_file():
        raise ValueError('Trusted source frozen_run_protocol.json is required before unpickling')
    expected = json.loads(source_manifest.read_text())['input_hashes']
    failures = [name for name,digest in expected.items()
                if not (input_root/name).is_file() or sha(input_root/name) != digest]
    if failures:
        raise ValueError(f'Trusted input hash mismatch: {failures}')
    return expected


def code_hashes():
    paths = [Path(__file__), ROOT/'src/gnss_jamming/core.py', ROOT/'src/gnss_jamming/replay.py',
             ROOT/'src/gnss_jamming/pilot_runtime.py', ROOT/'docker/pilot/Dockerfile',
             ROOT/'docker/pilot/Dockerfile.dockerignore', COMPOSE, POLICY, SCOPE,
             ROOT/'docker/image/requirements-lock.txt']
    paths += list((ROOT/'src/gnss_jamming').glob('*.py'))
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}


def provenance(input_root):
    parent = docker_json('image','inspect',PARENT_IMAGE)[0]
    if parent['Id'] != EXPECTED_PARENT:
        raise ValueError('Pinned local dependency parent image ID differs')
    image = docker_json('image','inspect',IMAGE)[0]
    codes=code_hashes()
    digest=hashlib.sha256(json.dumps(codes,sort_keys=True).encode()).hexdigest()
    if image['Config'].get('Labels',{}).get('nulp.pilot.source-manifest-sha256')!=digest:
        raise ValueError('Image build-source label differs from current code/policy/scope; rebuild first')
    source_expected={name:hash_ for name,hash_ in codes.items() if name.startswith('src/')}
    script=('import hashlib,json; from pathlib import Path; '
            'names='+repr(list(source_expected))+'; '
            'print(json.dumps({n:hashlib.sha256((Path("/opt/research")/n).read_bytes()).hexdigest() for n in names}))')
    actual=json.loads(execute(['docker','run','--rm','--network','none','--read-only',
                        '--entrypoint','python',IMAGE,'-c',script],timeout=30).stdout)
    if actual!=source_expected:raise ValueError('Actual image source bytes differ from host frozen source')
    return {'code_hashes':codes,'input_hashes':input_hashes(input_root),
            'input_root':str(input_root),'parent_image_id':parent['Id'],
            'image_id':image['Id'],'image_architecture':image['Architecture'],
            'image_os':image['Os'],'image_rootfs_layers':image['RootFS']['Layers'],
            'image_source_bytes_verified':True,'image_source_label':digest}


def append_journal(root, record):
    root.mkdir(parents=True,exist_ok=True)
    with (root/'attempts.ndjson').open('a') as stream:
        stream.write(json.dumps({'at_utc':timestamp(),**record},allow_nan=False)+'\n')
        stream.flush(); os.fsync(stream.fileno())


def spec_for(input_root, item, scope, policy, workload='ORIGINAL_RATE_MEASURED'):
    session = next(s for s in json.loads((input_root/'configs/sessions.json').read_text())
                   if s['session_id']==item['session_id'])
    rows = records(input_root,item['session_id'])
    first = rows[0]['timestamp']
    coverage = ((session['recording_end_us']-first)/1e6 if session.get('recording_end_us') is not None
                else rows[-1]['elapsed_s'])
    cid,_,_ = parse_config_id(item['config_id'])
    profile = next(p for p in scope['profiles'] if p['id']==item['profile_id'])
    return {**item,'protocol':'docker-pilot-v1','workload':workload,'session':session,
            'profile':profile,'cpu_period_us':scope['cpu_period_us'],
            'model_sha256':sha(input_root/'experiments/models'/f'{cid}.pkl'),
            'model_bytes':(input_root/'experiments/models'/f'{cid}.pkl').stat().st_size,
            'coverage_s':coverage,'expected_messages':len(rows),
            'onset_s':None if session['onset_us'] is None else (session['onset_us']-first)/1e6,
            'calibration_s':json.loads((input_root/'configs/experiment.json').read_text())['calibration_s'],
            'policy':policy,'processing_delay_ms':0}


def await_detector_exit(run_root, trial, container_id, grace_s):
    """Observe natural shutdown before cleanup can alter the exit evidence."""
    before = docker_json('inspect', container_id)[0]['State']
    record = {'container_id': container_id, 'before_wait': before,
              'grace_s': grace_s, 'started_utc': timestamp(), 'timed_out': False}
    append_journal(run_root, {'event': 'DETECTOR_SHUTDOWN_WAIT', **record})
    started = time.monotonic()
    try:
        if before['Running']:
            execute(['docker', 'wait', container_id], timeout=grace_s)
    except subprocess.TimeoutExpired:
        record['timed_out'] = True
    record.update(elapsed_s=time.monotonic()-started, finished_utc=timestamp(),
                  before_cleanup=docker_json('inspect', container_id)[0]['State'])
    dump(trial/'detector_shutdown.json', record)
    append_journal(run_root, {'event': 'DETECTOR_SHUTDOWN_OBSERVED', **record})
    return record


def run_pair(run_root, input_root, spec, name):
    """Journal before create; preserve inspect/log/counters before own cleanup."""
    trial = run_root/'trials'/name
    if trial.exists():
        raise FileExistsError(f'Refusing to overwrite trial directory: {trial}')
    trial.mkdir(parents=True)
    transport = Path('/private/tmp')/('nulp-pilot-'+uuid.uuid4().hex[:14])
    transport.mkdir()
    dump(transport/'spec.json',spec); dump(trial/'spec.json',spec)
    project = 'nulp-pilot-'+uuid.uuid4().hex[:12]
    env = os.environ.copy()
    env.update(GNSS_INPUT_ROOT=str(input_root),PILOT_TRANSPORT_ROOT=str(transport),
               PILOT_OUTPUT_ROOT=str(trial),PILOT_IMAGE=IMAGE,
               PILOT_CPU_QUOTA=str(spec['profile']['cpu_quota_us'] if spec['profile']['cpu_quota_us'] is not None else -1),
               PILOT_MEMORY_MIB=str(spec['profile']['memory_mib']))
    compose = ['docker','compose','--project-name',project,'-f',str(COMPOSE)]
    item = {k:spec.get(k) for k in ['config_id','profile_id','session_id','planned_sequence','technical_trial','workload']}
    append_journal(run_root, {'event':'ATTEMPT_STARTED','trial_directory':str(trial),**item})
    containers = {}; error = None; timed_out = False; interrupted=False; shutdown = None
    started = time.monotonic()
    try:
        rendered = execute([*compose,'config'],env=env).stdout
        (trial/'compose.effective.yaml').write_text(rendered)
        execute([*compose,'create','--no-build','driver','detector'],env=env,timeout=60)
        for service in ['driver','detector']:
            containers[service] = execute([*compose,'ps','-a','-q',service],env=env).stdout.strip()
        if not all(containers.values()):
            raise RuntimeError('Compose did not create both scoped containers')
        for cid in containers.values():
            assert docker_json('inspect',cid)[0]['Image']==spec['image_id'], 'Created container image differs from frozen image'
        dump(transport/'detector_identity.json',{'container_id':containers['detector']})
        execute(['docker','start',containers['driver']],timeout=30)
        deadline = time.monotonic()+spec['policy']['startup_timeout_s']
        while not (trial/'driver_ready.json').exists():
            if time.monotonic()>deadline:
                raise TimeoutError('driver readiness timeout')
            if not docker_json('inspect',containers['driver'])[0]['State']['Running']:
                raise RuntimeError('driver exited before readiness')
            time.sleep(.2)
        execute(['docker','start',containers['detector']],timeout=30)
        duration = spec['coverage_s'] if spec['workload']=='ORIGINAL_RATE_MEASURED' else 0
        execute(['docker','wait',containers['driver']],timeout=duration+spec['policy']['host_timeout_extra_s'])
        shutdown = await_detector_exit(run_root, trial, containers['detector'],
                                       spec['policy'].get('shutdown_grace_s', spec['policy']['completion_grace_s']))
    except (subprocess.TimeoutExpired,TimeoutError) as exc:
        error = repr(exc); timed_out=True
    except KeyboardInterrupt:
        error='controller interrupted';interrupted=True
    except Exception as exc:
        error = repr(exc)
    finally:
        # Stop only this attempt's containers. An exit137 is not proof of OOM.
        for service,cid in containers.items():
            try:
                before_cleanup = docker_json('inspect',cid)[0]
                dump(trial/f'inspect.{service}.before_cleanup.json',before_cleanup)
                if before_cleanup['State']['Running']:
                    append_journal(run_root, {'event':'CLEANUP_STOP_REQUESTED', 'service':service,
                        'container_id':cid, 'reason':'bounded shutdown wait expired or controller abort',
                        'monotonic_s':time.monotonic(), 'state_before':before_cleanup['State'], **item})
                    stopped = execute(['docker','stop','--time','1',cid],timeout=15,check=False)
                    append_journal(run_root, {'event':'CLEANUP_STOP_RETURNED', 'service':service,
                        'container_id':cid, 'returncode':stopped.returncode, **item})
                info = docker_json('inspect',cid)[0]
                dump(trial/f'inspect.{service}.json',info)
                logs = execute(['docker','logs','--timestamps',cid],check=False)
                (trial/f'{service}.stdout.log').write_text(logs.stdout)
                (trial/f'{service}.stderr.log').write_text(logs.stderr)
            except Exception as exc:
                error = (error or '')+f';preservation:{service}:{exc!r}'
        result = {'event':'ATTEMPT_FINISHED',**item,'trial_directory':str(trial),
                  'host_wall_s':time.monotonic()-started,'host_error':error,'host_timed_out':timed_out,
                  'container_states':{}}
        for service in containers:
            path = trial/f'inspect.{service}.json'
            if path.exists():
                info=json.loads(path.read_text());result['container_states'][service]=info['State']
        summary_path=trial/'summary.json'
        summary=json.loads(summary_path.read_text()) if summary_path.exists() else {}
        state=result['container_states'].get('detector',{})
        driver_state=result['container_states'].get('driver',{})
        if interrupted:
            status='CONTROLLER_INTERRUPTED'
        elif state.get('OOMKilled'):
            status='DETECTOR_OOM'
        elif shutdown and shutdown['timed_out']:
            status='DETECTOR_SHUTDOWN_TIMEOUT'
        elif timed_out:
            status='TIMEOUT'
        elif not containers:
            status='INFRASTRUCTURE_START_FAILURE'
        elif state.get('ExitCode',0)!=0:
            status='DETECTOR_EXIT_FAILURE'
        elif error or driver_state.get('ExitCode',0)!=0:
            status='INCOMPLETE_EVIDENCE'
        else:
            status=summary.get('status','INCOMPLETE_EVIDENCE')
        result['status']=status
        result['workload_status']=summary.get('status','INCOMPLETE_EVIDENCE')
        result['detector_shutdown']=shutdown
        result['cleanup_intervened']=any((trial/f'inspect.{service}.before_cleanup.json').exists() and
            json.loads((trial/f'inspect.{service}.before_cleanup.json').read_text())['State']['Running']
            for service in containers)
        result['source_schedule_valid']=summary.get('source_schedule_valid')
        result['dropped_messages']=summary.get('dropped_messages')
        result['eligible_episode']=spec['session']['attack_type']=='jamming' and spec['onset_s'] is not None and spec['coverage_s']>=spec['onset_s']+10
        result['readiness_success']=summary.get('readiness_success')
        result['confirmed_delay_s']=summary.get('confirmed_delay_s')
        result['statistical_evidence']='INSUFFICIENT EVIDENCE'
        dump(trial/'attempt_result.json',result)
        append_journal(run_root,result)
        cleanup=execute([*compose,'down','--volumes','--remove-orphans'],env=env,timeout=60,check=False)
        (trial/'cleanup.log').write_text(cleanup.stdout+cleanup.stderr)
        if cleanup.returncode:
            append_journal(run_root,{'event':'CLEANUP_FAILURE','project':project,**item})
        shutil.rmtree(transport)
    if interrupted:raise KeyboardInterrupt
    return result


def build():
    actual=docker_json('image','inspect',PARENT_IMAGE)[0]['Id']
    if actual!=EXPECTED_PARENT:raise ValueError('Unexpected dependency parent; abort build')
    digest=hashlib.sha256(json.dumps(code_hashes(),sort_keys=True).encode()).hexdigest()
    result=execute(['docker','build','--network=none','--label','nulp.pilot.source-manifest-sha256='+digest,
                    '-t',IMAGE,'-f','docker/pilot/Dockerfile','.'],timeout=180)
    print(result.stdout);print(result.stderr)
    print(docker_json('image','inspect',IMAGE)[0]['Id'])


def preflight(run_root,input_root):
    run_root.mkdir(parents=True,exist_ok=True)
    start_provenance=provenance(input_root)
    provenance_path=run_root/'preflight.provenance.json'
    if provenance_path.exists():
        if json.loads(provenance_path.read_text())!=start_provenance:
            raise ValueError('Preflight artifacts belong to different provenance; use a fresh run-root')
    else:dump(provenance_path,start_provenance)
    binding=sha(provenance_path)
    dump(run_root/'docker_info.json',docker_json('info','--format','{{json .}}'))
    dump(run_root/'containers_before.json',
         [json.loads(line) for line in execute(['docker','ps','--format','{{json .}}']).stdout.splitlines()])
    scope=json.loads(SCOPE.read_text());policy=json.loads(POLICY.read_text())
    parity_path=run_root/'parity.json'
    if not parity_path.exists():
        result=execute(['docker','run','--rm','--network','none','--read-only',
                        '--tmpfs','/tmp:rw,nosuid,size=64m','--memory','1536m','--memory-swap','1536m',
                        '-v',str(input_root)+':/inputs:ro','-v',str(ROOT)+':/repo:ro',
                        '-v',str(run_root)+':/outputs',IMAGE,'parity','--input-root','/inputs',
                        '--scope','/repo/docs/review/PILOT_SCOPE.json','--policy','/repo/docker/pilot/policy.json',
                        '--output','/outputs/parity.json'],timeout=120)
        (run_root/'parity.stdout.log').write_text(result.stdout+result.stderr)
        dump(run_root/'parity.binding.json',{'provenance_sha256':binding,'parity_sha256':sha(parity_path)})
    parity_binding=json.loads((run_root/'parity.binding.json').read_text())
    assert parity_binding=={'provenance_sha256':binding,'parity_sha256':sha(parity_path)}, 'stale parity proof'
    assert json.loads(parity_path.read_text())['status']=='PASS'
    base={**scope['planned_order'][0],'profile_id':'cpu025_ram512'}
    checks=[]
    cases=[('normal',{},'COMPLETE'),
           ('normal_reference',{'profile_id':'guarded_reference'},'COMPLETE'),
           ('normal_cpu1',{'profile_id':'cpu1_ram512'},'COMPLETE'),
           ('normal_cpu05',{'profile_id':'cpu05_ram512'},'COMPLETE'),
           ('backlog_drop',{'processing_delay_ms':80,'synthetic_messages':160,
                            'policy_override':{'ingress_capacity_messages':2}},'IN_SCOPE_PIPELINE_FAILURE'),
           ('startup_failure',{'test_fail_start':True,'policy_override':{'startup_timeout_s':5,'completion_grace_s':3}},'DETECTOR_EXIT_FAILURE'),
           ('midstream_failure',{'test_fail_after':2,'policy_override':{'startup_timeout_s':20,'completion_grace_s':3}},'DETECTOR_EXIT_FAILURE')]
    for name,overrides,expected in cases:
        path=run_root/'trials'/('integration_'+name)/'attempt_result.json'
        if path.exists():
            record=json.loads(path.read_text())
            cached_spec=json.loads((path.parent/'spec.json').read_text())
            assert cached_spec.get('preflight_provenance_sha256')==binding,'stale integration proof'
        else:
            item={**base,'profile_id':overrides.get('profile_id',base['profile_id'])}
            spec=spec_for(input_root,item,scope,dict(policy),'SYNTHETIC_INFRASTRUCTURE_ONLY')
            spec['image_id']=start_provenance['image_id'];spec['preflight_provenance_sha256']=binding
            spec.update(overrides);spec['policy']={**policy,**overrides.get('policy_override',{})}
            record=run_pair(run_root,input_root,spec,'integration_'+name)
        assert record['status']==expected,(name,record)
        summary_path=run_root/'trials'/('integration_'+name)/'summary.json'
        summary=json.loads(summary_path.read_text())
        if name.startswith('normal'):
            assert summary['source_schedule_valid'] and summary['evidence_complete']
        if name=='backlog_drop':
            assert summary['dropped_messages']>0
            assert summary['queue_ms']['max']>=50
            assert summary['source_schedule_valid'], 'slow detector must not invalidate independent source'
        checks.append({'case':name,'expected':expected,'actual':record['status'],'passed':True})
    if provenance(input_root)!=start_provenance:raise ValueError('Provenance changed during preflight')
    dump(run_root/'preflight.json',{'status':'PASS','gate':'G2-G5','checks':checks,
         'provenance_sha256':sha(run_root/'preflight.provenance.json'),
         'parity_sha256':sha(parity_path),'scientific_pilot_started':False})
    print('Preflight PASS:',run_root)


def freeze(run_root,input_root):
    pre=json.loads((run_root/'preflight.json').read_text())
    assert pre['status']=='PASS'
    current=provenance(input_root)
    assert current==json.loads((run_root/'preflight.provenance.json').read_text())
    frozen={'protocol':'docker-pilot-v1','scope':json.loads(SCOPE.read_text()),'policy':json.loads(POLICY.read_text()),
            'provenance':current,'preflight_sha256':sha(run_root/'preflight.json'),
            'parity_sha256':sha(run_root/'parity.json'),'frozen_utc':timestamp(),
            'measurement_gate':'VERIFIED_BY_RECORDED_PREFLIGHT','development_only':True,
            'no_target_hardware_equivalence':True,'technical_trials_per_pair':1}
    path=run_root/'frozen_manifest.json'
    if path.exists():raise FileExistsError('Frozen manifest already exists; do not refreeze')
    dump(path,frozen);print('Frozen manifest:',path,sha(path))


def run(run_root,input_root):
    manifest_path=run_root/'frozen_manifest.json';manifest=json.loads(manifest_path.read_text())
    if manifest['provenance']!=provenance(input_root):raise ValueError('Resume prohibited: provenance differs')
    if manifest['preflight_sha256']!=sha(run_root/'preflight.json'):raise ValueError('Preflight changed after freeze')
    scope=manifest['scope'];policy=manifest['policy']
    manifest_digest=sha(manifest_path)
    status={'status':'RUNNING','manifest_sha256':manifest_digest,'started_utc':timestamp(),
            'host_pid':os.getpid(),'planned_attempts':60,'completed_attempts':0}
    lock=threading.Lock();stop=threading.Event()
    def update(**values):
        with lock:
            status.update(values);status['heartbeat_utc']=timestamp()
            dump(run_root/'run_status.json',status)
    def heartbeat():
        while not stop.wait(5):update()
    thread=threading.Thread(target=heartbeat,daemon=True);thread.start();update()
    try:
        for item in scope['planned_order']:
            if sha(manifest_path)!=manifest_digest:raise ValueError('Frozen manifest modified during run')
            if code_hashes()!=manifest['provenance']['code_hashes']:
                raise ValueError('Code/policy/scope changed during run; resume prohibited')
            for input_name,digest in manifest['provenance']['input_hashes'].items():
                if sha(input_root/input_name)!=digest:raise ValueError('Frozen input changed: '+input_name)
            name=f"pilot_{item['planned_sequence']:03d}"
            path=run_root/'trials'/name/'attempt_result.json'
            if path.exists():
                print('Recorded attempt, not repeated:',name,flush=True);continue
            if (run_root/'trials'/name).exists():
                append_journal(run_root,{'event':'INTERRUPTED_ATTEMPT_RETAINED','trial':name,**item})
                raise RuntimeError('Interrupted attempt requires explicit adjudication; no silent rerun')
            update(current_trial=name,current_selection=item)
            print('Starting',name,item['config_id'],item['profile_id'],item['session_id'],flush=True)
            spec=spec_for(input_root,item,scope,dict(policy));spec['image_id']=manifest['provenance']['image_id']
            result=run_pair(run_root,input_root,spec,name)
            print('Finished',name,result['status'],flush=True)
            completed=len(list((run_root/'trials').glob('pilot_*/attempt_result.json')))
            update(completed_attempts=completed,last_sequence=item['planned_sequence'],last_status=result['status'])
            if result['status']=='INFRASTRUCTURE_START_FAILURE':
                raise RuntimeError('Infrastructure start failure; stop rather than repeat60invalid attempts')
        summaries=[]
        for item in scope['planned_order']:
            trial=run_root/'trials'/f"pilot_{item['planned_sequence']:03d}"
            result=json.loads((trial/'attempt_result.json').read_text())
            if (trial/'summary.json').exists():result['metrics']=json.loads((trial/'summary.json').read_text())
            summaries.append(result)
        dump(run_root/'all_trial_results.json',summaries)
        update(status='COMPLETE',completed_attempts=60,finished_utc=timestamp(),current_trial=None,
               all_trials_successful=all(x['status']=='COMPLETE' and x.get('source_schedule_valid') for x in summaries),
               evidence='INSUFFICIENT EVIDENCE')
        print('Pilot attempts complete:',run_root,flush=True)
    except BaseException as exc:
        update(status='ABORTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR',
               error=repr(exc),finished_utc=timestamp())
        append_journal(run_root,{'event':'CONTROLLER_ABORTED','error':repr(exc),'host_pid':os.getpid()})
        raise
    finally:
        stop.set();thread.join(2)


def main():
    def terminate(signum,frame):raise KeyboardInterrupt(f'signal{signum}')
    signal.signal(signal.SIGTERM,terminate)
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['build','preflight','freeze','run'])
    parser.add_argument('--run-root',type=Path,default=ROOT/'docker/artifacts/pilot-v1/run_20261026')
    parser.add_argument('--input-root',type=Path)
    args=parser.parse_args();run_root=args.run_root.resolve()
    if args.action=='build':build();return
    input_root=resolve_input(args.input_root)
    {'preflight':preflight,'freeze':freeze,'run':run}[args.action](run_root,input_root)


if __name__=='__main__':main()
