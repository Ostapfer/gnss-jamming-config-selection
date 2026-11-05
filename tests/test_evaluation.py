import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from gnss_jamming.core import Detector,config
from gnss_jamming.replay import metrics

class EvaluationTests(unittest.TestCase):
    def runner(self, detector, ready=True):
        return SimpleNamespace(cfg=config(), c={'candidate_id':'synthetic','causal':True},states={(0.5,2):detector},cal=SimpleNamespace(baseline=[1.] if ready else None,failed=not ready))
    def data(self,end=70.):
        return pd.DataFrame({'timestamp':[0,int(end*1e6)],'elapsed_s':[0.,end]})
    def session(self):
        return {'session_id':'synthetic','onset_us':50_000_000,'attack_type':'jamming'}
    def test_preexisting_alarm_not_new_detection(self):
        d=Detector(2,2,1.5);d.update(48,True);d.update(49,True);d.update(50,True);d.update(51,True)
        rows,_=metrics(self.runner(d),self.session(),self.data(),'synthetic')
        self.assertTrue(rows[0]['active_before_onset']);self.assertIsNone(rows[0]['confirmed_delay_s'])
    def test_readiness_failure_keeps_eligible_episode(self):
        rows,_=metrics(self.runner(Detector(2,2,1.5),False),self.session(),self.data(),'synthetic')
        self.assertTrue(rows[0]['eligible_episode']);self.assertFalse(rows[0]['readiness_success']);self.assertIsNone(rows[0]['confirmed_delay_s'])
    def test_incomplete_common_cohort(self):
        rows,_=metrics(self.runner(Detector(2,2,1.5)),self.session(),self.data(59),'synthetic')
        self.assertFalse(rows[0]['eligible_episode'])
    def test_execution_delay_uses_ready_clock(self):
        d=Detector(2,2,1.5);d.update(54,True);d.update(55,True,ready_t=57)
        rows,_=metrics(self.runner(d),self.session(),self.data(),'synthetic')
        self.assertEqual(rows[0]['confirmed_delay_s'],7);self.assertEqual(rows[0]['information_delay_s'],5)
if __name__=='__main__':unittest.main()
