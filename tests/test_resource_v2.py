"""Resource workload/gate regression with a deterministic fake timed Runner."""
import json
import multiprocessing as mp
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import pandas as pd
from gnss_jamming import benchmark as b


class FakeRunner:
    def __init__(self, c, cfg, th, n):
        self.timings=[];self.states={(th,n):SimpleNamespace(events=[])}
    def step(self,row,**kwargs):
        calibration=row['elapsed_s']<=30
        self.timings.append(dict(processing_ms=99 if calibration else row['cost'],
            model_only_ms=0 if calibration else row['cost']/2,
            inference_executed=not calibration,state_before='CALIBRATING' if calibration else 'IDLE',
            state_after='CALIBRATING' if calibration else 'ACTIVE'))


class ResourceWorkloadTests(unittest.TestCase):
    def test_complete_configurations_are_individual(self):
        c={'candidate_id':'C','thresholds':[.5,.75]}
        result=list(b.complete_configs([c],{'confirmation_counts':[1,2,3]}))
        self.assertEqual(len(result),6)
        self.assertEqual(len({x[3] for x in result}),6)

    def test_producer_spawns_and_keeps_schedule_without_consumer_feedback(self):
        ctx=mp.get_context('spawn');out=ctx.Queue()
        ready_recv,ready_send=ctx.Pipe(duplex=False)
        cmd_recv,cmd_send=ctx.Pipe(duplex=False)
        proc=ctx.Process(target=b._producer,args=(out,ready_send,cmd_recv,[{'i':i} for i in range(3)],100))
        proc.start();ready_send.close();cmd_recv.close()
        try:
            self.assertTrue(ready_recv.poll(30));self.assertTrue(ready_recv.recv())
            start=time.perf_counter()+.02;cmd_send.send(start)
            # Read after entire schedule; consumer progress cannot throttle producer.
            time.sleep(.06)
            values=[out.get(timeout=5) for _ in range(3)]
            self.assertIsNone(out.get(timeout=5))
            self.assertEqual([x[3] for x in values],[0,1,2])
            self.assertAlmostEqual(values[-1][1]-values[0][1],.02,places=6)
            self.assertTrue(all(x[2]>=x[1] for x in values))
            proc.join(timeout=5);self.assertEqual(proc.exitcode,0)
        finally:
            if proc.is_alive():proc.terminate();proc.join()
            ready_recv.close();cmd_send.close();out.close();out.join_thread()

    def test_full_three_sessions_calibration_gate_and_condition_counts(self):
        cfg={'calibration_s':30,'primary_confirmation':2,'confirmation_counts':[2],
             'benchmark':{'warmup':2,'stress_hz':[100,1000]}}
        c={'candidate_id':'RULE','thresholds':[.5],'model_bytes':100}
        records=[]
        # Long benign prefix plus tail ensures the old first100-only bug fails.
        for sid in ['jamming','spoofing','benign']:
            for i in range(161):
                state=sid if sid!='benign' and i>=150 else 'benign'
                records.append(dict(session_id=sid,elapsed_s=float(i),state=state,
                    cost={'jamming':20,'spoofing':30,'benign':1}[state]))
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'results/tables').mkdir(parents=True);(root/'experiments').mkdir()
            (root/'data/derived').mkdir(parents=True)
            pd.DataFrame(records).to_csv(root/'data/derived/development.csv',index=False)
            (root/'experiments/candidates.json').write_text(json.dumps([c]))
            for name in ['configs/experiment.json','configs/sessions.json','src/gnss_jamming/core.py','src/gnss_jamming/replay.py','src/gnss_jamming/benchmark.py','requirements-lock.txt','experiments/environment.json','experiments/models/RULE.pkl']:
                fixture=root/name;fixture.parent.mkdir(parents=True,exist_ok=True);fixture.write_text('test fixture provenance')
            with patch.object(b,'ROOT',root),patch.object(b,'config',return_value=cfg),\
                 patch.object(b,'new_runner',side_effect=FakeRunner),\
                 patch('sys.argv',['benchmark','--skip-stress']):
                b.main()
            out=pd.read_csv(root/'results/tables/resources.csv').iloc[0]
            conditions=pd.read_csv(root/'results/tables/resources_by_condition.csv').set_index('condition')
            self.assertEqual(out.calibration_messages,31*3)
            self.assertEqual(out.measured_messages,130*3)
            self.assertEqual(conditions.loc['jamming','measured_messages'],11)
            self.assertEqual(conditions.loc['spoofing','measured_messages'],11)
            self.assertEqual(out.pipeline_p95_ms,99)  # Calibration included conservatively.
            self.assertEqual(conditions.loc['spoofing','pipeline_p95_ms'],30)
            meta=json.loads((root/'experiments/resource_run.json').read_text())
            self.assertEqual(meta['session_rows'],{'jamming':161,'spoofing':161,'benign':161})
            self.assertEqual(meta['full_passes'],1)

if __name__=='__main__':unittest.main()
