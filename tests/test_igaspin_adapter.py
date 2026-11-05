from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"validation/igaspin"))
import struct,unittest
from adapter import observations,nav,new_event_delays_ns,NS

def frame(c,m,p):
 body=bytes([c,m])+struct.pack('<H',len(p))+p;a=b=0
 for v in body:a=(a+v)&255;b=(b+a)&255
 return b'\xb5\x62'+body+bytes([a,b])
def pvt(sec,nano=0,valid=3):
 p=bytearray(92);struct.pack_into('<I',p,0,sec*1000);struct.pack_into('<H',p,4,2023);p[6:12]=bytes([12,7,12,6,sec,valid]);struct.pack_into('<I',p,12,22);struct.pack_into('<i',p,16,nano);struct.pack_into('<II',p,40,1200,2300);return frame(1,7,p)
def rf(a=12,b=34):
 p=bytearray(52);p[1]=2;struct.pack_into('<H',p,16,a);struct.pack_into('<H',p,40,b);return frame(10,56,p)
class Tests(unittest.TestCase):
 def test_leading_rf_both_unavailable_first(self):
  r=list(observations(rf()+pvt(1)+rf()+pvt(2)));self.assertFalse(r[0]['arms'][0]['available']);self.assertTrue(r[1]['arms'][0]['available'])
 def test_adjacent_and_duplicate_ids(self):
  r=list(observations(pvt(1)+rf()+pvt(2)))[1];self.assertEqual([x['noise_per_ms'] for x in r['arms']],[12,34]);self.assertEqual([x['literal_blockId'] for x in r['arms']],[0,0]);self.assertEqual(r['arms'][0]['rf_offset'],r['previous_nav_end_exclusive'])
 def test_no_rf_reuse(self):
  r=list(observations(pvt(1)+rf()+pvt(2)+pvt(3)));self.assertFalse(r[2]['arms'][0]['available'])
 def test_multiple_unavailable(self):
  r=list(observations(pvt(1)+rf()+rf()+pvt(2)));self.assertFalse(r[1]['arms'][0]['available'])
 def test_future_never_fills(self):
  r=list(observations(pvt(1)+pvt(2)+rf()));self.assertFalse(r[1]['arms'][0]['available'])
 def test_shape(self):
  r=list(observations(pvt(1)+frame(10,56,b'\0\2\0\0')+pvt(2)));self.assertEqual(r[1]['arms'][0]['unavailable_reason'],'unsupported_RF_shape')
 def test_invalid_time(self):
  with self.assertRaises(ValueError):list(observations(pvt(1,valid=0)))
 def test_negative_nano_and_units(self):
  r=list(observations(pvt(1,-400000)+rf()+pvt(2,-300000)));self.assertEqual(r[1]['utc_ns']-r[0]['utc_ns'],1000100000);self.assertEqual(r[0]['eph'],1.2);self.assertEqual(r[0]['epv'],2.3)
 def test_nonmonotone(self):
  with self.assertRaises(ValueError):list(observations(pvt(2)+rf()+pvt(1)))
 def test_exact_deadline(self):
  self.assertEqual(new_event_delays_ns([99,100,100+3*NS,101+3*NS],100,3),[0,3*NS])
 def test_integrity(self):
  with self.assertRaises(ValueError):list(observations(pvt(1)[:-1]+b'x'))
if __name__=='__main__':unittest.main()
