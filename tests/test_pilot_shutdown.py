"""Lifecycle regression tests: observe exits before destructive cleanup."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pilot_shutdown_host',ROOT/'scripts/run_docker_pilot.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ShutdownTests(unittest.TestCase):
    def observe(self,before,after,timeout=False):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(m,'docker_json',side_effect=[[{'State':before}],[{'State':after}]]), \
                 patch.object(m,'execute',side_effect=subprocess.TimeoutExpired('docker wait',30) if timeout else None) as execute:
                result=m.await_detector_exit(root,root,'detector',30)
                self.assertTrue((root/'detector_shutdown.json').exists())
                self.assertTrue((root/'attempts.ndjson').exists())
                if before['Running']:execute.assert_called_once_with(['docker','wait','detector'],timeout=30)
                else:execute.assert_not_called()
                return result

    def test_delayed_exit_is_observed_without_stop(self):
        r=self.observe({'Running':True},{'Running':False,'ExitCode':0})
        self.assertFalse(r['timed_out']);self.assertEqual(r['before_cleanup']['ExitCode'],0)

    def test_stuck_shutdown_remains_timeout_before_cleanup(self):
        r=self.observe({'Running':True},{'Running':True},True)
        self.assertTrue(r['timed_out']);self.assertTrue(r['before_cleanup']['Running'])

    def test_midstream_failure_not_relabelled(self):
        state={'Running':False,'ExitCode':1,'OOMKilled':False}
        self.assertEqual(self.observe(state,state)['before_cleanup'],state)

    def test_oom_evidence_not_relabelled(self):
        state={'Running':False,'ExitCode':137,'OOMKilled':True}
        self.assertTrue(self.observe(state,state)['before_cleanup']['OOMKilled'])

if __name__=='__main__':unittest.main()
