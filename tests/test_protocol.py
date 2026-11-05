import unittest
import numpy as np
from gnss_jamming.core import Detector,Calibration,relative,config
class ProtocolTests(unittest.TestCase):
    def test_confirmation_and_gap(self):
        d=Detector(2,2,1.5);self.assertIsNone(d.update(0,True));self.assertIsNone(d.update(3,True));self.assertIsNotNone(d.update(4,True));self.assertEqual(len(d.events),1)
    def test_missing_cannot_confirm_or_recover(self):
        d=Detector(2,2,1.5);d.update(0,True);d.update(1,None);self.assertIsNone(d.update(2,True));d.update(3,True);d.update(4,False);d.update(5,None);d.update(6,False);self.assertIsNotNone(d.current);d.update(7,False);self.assertIsNone(d.current)
    def test_old_alarm_does_not_create_new_event(self):
        d=Detector(2,2,1.5);d.update(0,True);d.update(1,True);d.update(2,True);d.update(3,True);self.assertEqual(len(d.events),1)
    def test_zero_no_epsilon(self):
        with self.assertRaises(ValueError):relative([[1]],[0])
    def test_calibration_causal_boundary(self):
        c=Calibration(['noise'],config())
        for t in range(31):self.assertFalse(c.update(t,[10]))
        self.assertTrue(c.update(31,[1000]));self.assertEqual(c.baseline[0],10)
    def test_insufficient_calibration(self):
        c=Calibration(['noise'],config());c.update(0,[1]);self.assertFalse(c.update(31,[1]));self.assertTrue(c.failed)
if __name__=='__main__':unittest.main()
