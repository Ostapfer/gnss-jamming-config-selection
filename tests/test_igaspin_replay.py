import unittest,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'validation/igaspin'))
from gnss_jamming import core
from replay import replay
from adapter import NS,new_event_delays_ns
CFG=json.loads((R/'configs/experiment.json').read_text())
def rows(baseline=2,invalid_until=0):
 return [{'elapsed_s':float(i),'utc_ns':i*NS,'tAcc_ns':22,'eph':baseline if i<=30 else baseline*2,'epv':1,'nav_offset':i*100,'arms':[{'available':i>invalid_until,'noise_per_ms':baseline if i<=30 else baseline*2,'rf_offset':i*100-50}]*2} for i in range(35)]
class Tests(unittest.TestCase):
 def test_origin_not_first_valid(self):
  x=replay(core,rows(),0,['eph'],CFG,core.Rule(.5),.5,1)
  self.assertEqual(x['valid_calibration_observations'],30);self.assertEqual(x['event_ns'][0],31*NS)
 def test_zero_baseline_fails(self):
  x=replay(core,rows(0),0,['eph'],CFG,core.Rule(.5),.5,2);self.assertFalse(x['readiness_success']);self.assertTrue(x['calibration_failed']);self.assertEqual(x['event_ns'],[])
 def test_insufficient_not_dropped(self):
  x=replay(core,rows(invalid_until=10),0,['eph'],CFG,core.Rule(.5),.5,2);self.assertFalse(x['readiness_success']);self.assertEqual(x['valid_calibration_observations'],20);self.assertEqual(x['event_ns'],[])
 def test_carry_in_not_new(self):
  x=replay(core,rows(),0,['eph'],CFG,core.Rule(.5),.5,2);self.assertEqual(x['event_ns'],[32*NS]);self.assertEqual(new_event_delays_ns(x['event_ns'],33*NS,10),[]);self.assertEqual(x['events'][0]['end_ns'],None)
 def test_tacc_joint_gate(self):
  rr=rows()
  for x in rr:x['tAcc_ns']=0xffffffff
  x=replay(core,rr,0,['eph'],CFG,core.Rule(.5),.5,2);self.assertFalse(x['readiness_success']);self.assertEqual(x['unavailable_observations'],35)
 def test_gap_does_not_confirm(self):
  rr=rows();rr[32]['elapsed_s']=34;rr[33]['elapsed_s']=35;rr[34]['elapsed_s']=36
  for x in rr:x['utc_ns']=int(x['elapsed_s']*NS)
  x=replay(core,rr,0,['eph'],CFG,core.Rule(.5),.5,2);self.assertEqual(x['event_ns'][0],35*NS)
if __name__=='__main__':unittest.main()
