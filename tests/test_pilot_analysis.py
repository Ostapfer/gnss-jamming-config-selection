"""Regression fixtures for derived queue accounting and descriptive screening."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).resolve().parents[1]/'scripts/analyze_docker_pilot.py'
s=importlib.util.spec_from_file_location('pilot_analysis',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class PilotAnalysisTests(unittest.TestCase):
    def test_transient_wait_is_not_zero_post_dequeue_count(self):
        # Every post-dequeue observation is empty, but each message waited.
        q=m.queue_sweep([0.,1.],[.1,1.2])
        self.assertEqual(q['waiting_queue_max_over_time'],1)
        self.assertAlmostEqual(q['waiting_queue_integral_message_s'],.3)
        self.assertAlmostEqual(q['waiting_queue_nonempty_s'],.3)

    def test_backlog_integral_and_equal_timestamp_grouping(self):
        q=m.queue_sweep([0.,.2,.5],[.5,.7,.8])
        self.assertEqual(q['waiting_queue_max_over_time'],2)
        self.assertAlmostEqual(q['waiting_queue_integral_message_s'],1.3)
        self.assertAlmostEqual(q['waiting_queue_nonempty_s'],.8)
        self.assertEqual(m.queue_sweep([1.],[1.])['waiting_queue_max_over_time'],0)

    def test_missing_or_impossible_work_does_not_pass(self):
        with self.assertRaises(ValueError):m.queue_sweep([1.],[])
        with self.assertRaises(ValueError):m.queue_sweep([1.],[.9])

    def test_pareto_keeps_tradeoff_and_equal_points(self):
        a={'delay':1,'cost':3};b={'delay':2,'cost':2};c={'delay':3,'cost':4};same={'delay':1,'cost':3}
        points=[a,b,c,same]
        self.assertFalse(m.dominated(a,points,['delay','cost']))
        self.assertFalse(m.dominated(b,points,['delay','cost']))
        self.assertTrue(m.dominated(c,points,['delay','cost']))

if __name__=='__main__':unittest.main()
