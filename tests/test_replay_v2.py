import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import pandas as pd
from gnss_jamming.core import Rule, config, Detector
from gnss_jamming.replay import Runner, metrics

class ReplayV2Tests(unittest.TestCase):
    def runner(self):
        c={'candidate_id':'synthetic','features':['noise_per_ms'],'thresholds':[.5,.75],'causal':True}
        with patch('gnss_jamming.replay.pickle.loads',return_value=Rule(.5)),patch('pathlib.Path.read_bytes',return_value=b''):
            return Runner(c,config(),decision_threshold=.5,confirmation=2)
    def calibrated(self):
        r=self.runner()
        for t in range(31):r.step({'elapsed_s':t,'noise_per_ms':10.,'state':'benign'})
        return r
    def test_isolated_configuration_and_all_rows_timed(self):
        r=self.calibrated();self.assertEqual(list(r.states),[(.5,2)])
        self.assertEqual(len(r.timings),31);self.assertTrue(all(x['state_after']=='CALIBRATING' for x in r.timings))
        r.step({'elapsed_s':31,'noise_per_ms':np.nan,'state':'jamming'})
        self.assertEqual(r.timings[-1]['state_after'],'UNAVAILABLE')
        self.assertFalse(r.timings[-1]['inference_executed']);self.assertIsNone(r.timings[-1]['event_ready_time'])
    def test_event_clock_and_instrumented_pipeline(self):
        import time
        r=self.calibrated();origin=time.perf_counter()-32
        r.step({'elapsed_s':31,'noise_per_ms':20.,'state':'jamming'},arrival=time.perf_counter(),origin=origin,scheduled=time.perf_counter())
        r.step({'elapsed_s':32,'noise_per_ms':20.,'state':'jamming'},arrival=time.perf_counter(),origin=origin,scheduled=time.perf_counter())
        tt=r.timings[-1];event=r.states[(.5,2)].events[0]
        self.assertEqual(tt['state_after'],'ACTIVE');self.assertEqual(tt['condition'],'jamming')
        self.assertAlmostEqual(event['ready_s'],tt['event_ready_time']-origin)
        self.assertLessEqual(tt['processing_start_time'],tt['event_ready_time']);self.assertLessEqual(tt['event_ready_time'],tt['processing_end_time'])
    def test_recording_continues_after_telemetry_loss(self):
        r=self.calibrated()
        part=pd.DataFrame({'timestamp':[0,55_000_000],'elapsed_s':[0.,55.]})
        s={'session_id':'x','onset_us':50_000_000,'recording_end_us':70_000_000,'attack_type':'jamming'}
        rows,_=metrics(r,s,part,'realtime')
        self.assertTrue(rows[0]['eligible_episode']);self.assertIsNone(rows[0]['confirmed_delay_s'])
        self.assertEqual(rows[0]['workload'],'isolated_single_configuration')
        self.assertEqual(rows[0]['coverage_source'],'recording_end_us')
