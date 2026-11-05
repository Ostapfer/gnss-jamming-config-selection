"""Meaningful bounded-transport and detector-semantic regression fixtures."""
import json
from pathlib import Path
import socket
import struct
import sys
import threading
import unittest
from collections import deque
import pickle
import tempfile
from unittest.mock import patch
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from gnss_jamming.pilot_runtime import (BoundedIngress,send_frame,receive_frame,
                                       runner_step,make_runner,own_cgroup_root)

POLICY=json.loads((ROOT/'docker/pilot/policy.json').read_text())


class PilotTransportTests(unittest.TestCase):
    def test_partial_frame_reads_and_size_limit(self):
        left,right=socket.socketpair()
        payload=json.dumps({'sequence':7,'value':'x'*200}).encode()
        wire=struct.pack('!I',len(payload))+payload
        def write():
            for byte in wire:left.sendall(bytes([byte]))
            left.close()
        writer=threading.Thread(target=write);writer.start()
        self.assertEqual(receive_frame(right,POLICY)['sequence'],7)
        self.assertIsNone(receive_frame(right,POLICY));right.close();writer.join()
        left,right=socket.socketpair()
        with self.assertRaises(ValueError):send_frame(left,{'value':'x'*POLICY['maximum_frame_bytes']},POLICY)
        left.close();right.close()

    def test_incomplete_frame_is_failure(self):
        left,right=socket.socketpair();left.sendall(struct.pack('!I',100)+b'bad');left.close()
        with self.assertRaises(EOFError):receive_frame(right,POLICY)
        right.close()

    def test_ingress_drop_new_and_atomic_timestamp(self):
        q=BoundedIngress(1);first={'sequence':1};second={'sequence':2}
        stamp=q.offer(first)
        self.assertIsNotNone(stamp);self.assertIsNone(q.offer(second))
        self.assertEqual(q.qsize(),1)
        self.assertEqual(q.get(.01)['accepted_ingress_available'],stamp)
        self.assertIsNotNone(q.offer(second))

    def test_host_namespace_uses_driver_membership_not_vm_root(self):
        with patch('gnss_jamming.pilot_runtime.file_text',return_value='0::/docker/driver-id'), \
             patch.object(Path,'is_dir',return_value=True):
            self.assertEqual(str(own_cgroup_root()),'/sys/fs/cgroup/docker/driver-id')

    def test_changed_provenance_cannot_relabel_cached_preflight(self):
        spec=importlib.util.spec_from_file_location('pilot_host',ROOT/'scripts/run_docker_pilot.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);p=root/'preflight.provenance.json';p.write_text('{"image_id":"old"}')
            with patch.object(module,'provenance',return_value={'image_id':'new'}):
                with self.assertRaisesRegex(ValueError,'fresh run-root'):
                    module.preflight(root,Path('/unused'))
            self.assertEqual(json.loads(p.read_text()),{'image_id':'old'})

    def test_missing_feature_matches_legacy_semantics_and_storage_stays_bounded(self):
        import numpy as np
        from gnss_jamming.core import Rule
        from gnss_jamming.replay import Runner
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'configs').mkdir();(root/'experiments/models').mkdir(parents=True)
            cfg={'calibration_s':1,'minimum_calibration_observations':2,'recovery_negatives':2,
                 'max_allowed_gap_s':1.5,'confirmation_counts':[2]}
            (root/'configs/experiment.json').write_text(json.dumps(cfg))
            candidate={'candidate_id':'RULE_test','features':['noise_per_ms'],'thresholds':[.5]}
            (root/'experiments/candidates.json').write_text(json.dumps([candidate]))
            (root/'experiments/models/RULE_test.pkl').write_bytes(pickle.dumps(Rule(.5)))
            legacy=Runner(candidate,cfg,decision_threshold=.5,confirmation=2,input_root=root)
            bounded=make_runner(root,'RULE_test_d0.5_c2',POLICY)
            values=[1,1,2,None,2,2,1,1]+[1]*500
            for i,value in enumerate(values):
                row={'elapsed_s':float(i),'noise_per_ms':value,'state':'benign'}
                a=runner_step(legacy,row);b=runner_step(bounded,row)
                for key in ['score','state','event_started','event_closed','current_event']:
                    self.assertEqual(a[key],b[key])
                self.assertLessEqual(len(bounded.timings),1)
                self.assertLessEqual(len(bounded.predictions),1)
                self.assertLessEqual(len(next(iter(bounded.states.values())).events),1)
            self.assertEqual(bounded.cal.rows,[])


if __name__=='__main__':unittest.main()
