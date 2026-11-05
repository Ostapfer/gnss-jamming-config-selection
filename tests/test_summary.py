import unittest
import tempfile
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import gnss_jamming.summarize as summary_module
import numpy as np
import pandas as pd
from gnss_jamming.summarize import (ISOLATED_WORKLOAD, accepted_realtime, build_scenarios,
                                     configuration_library, configuration_metrics, pareto)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.cfg = dict(confirmation_counts=[2], detection_fraction_requirements=[1],
                        detection_deadlines_s=[5], false_alarm_per_hour_requirements=[0],
                        resource_budgets=[dict(name='fixture', pipeline_p95_ms=1, model_bytes=100)])
        self.library = configuration_library([
            dict(candidate_id='measured', algorithm='RULE', causal=True, thresholds=[0.5]),
            dict(candidate_id='unmeasured', algorithm='RULE', causal=True, thresholds=[0.5])], self.cfg)
        self.resources = pd.DataFrame([dict(config_id=cid, pipeline_p95_ms=.1, model_bytes=10)
                                       for cid in self.library.config_id])
        self.cid = 'measured_d0.5_c2'

    def metric(self, session, delay=2., ready=True, condition='benign'):
        return dict(config_id=self.cid, session_id=session, readiness_success=ready,
                    confirmed_delay_s=delay, condition=condition, exposure_s=30.,
                    false_events=0, false_active_s=0., false_event_duration_max_s=0.)

    def fixture(self, **kwargs):
        return pd.DataFrame([self.metric('jam_a'), self.metric('jam_b', **kwargs),
                             self.metric('spoof', condition='spoofing', delay=None)])

    def scenarios(self, frame, eligible=('jam_a', 'jam_b')):
        return build_scenarios(self.library, frame, self.resources, self.cfg, 'realtime', eligible)

    def test_aggregate_uses_worst_session_and_is_order_invariant(self):
        frame = self.fixture(delay=7.)
        result = self.scenarios(frame)
        reversed_result = self.scenarios(frame.iloc[::-1])
        pd.testing.assert_frame_equal(result, reversed_result)
        measured = result.iloc[0]
        self.assertEqual(measured.delay_s, 7.)
        self.assertEqual(measured.X_e2e, .5)
        self.assertEqual(measured.empirical, 'FAIL')

    def test_readiness_failure_remains_in_denominator_and_infinite_delay(self):
        result = self.scenarios(self.fixture(ready=False)).iloc[0]
        self.assertEqual(result.eligible_total, 2)
        self.assertEqual(result.tested_count, 2)
        self.assertEqual(result.X_e2e, .5)
        self.assertEqual(result.readiness_success_rate, .5)
        self.assertEqual(result.conditional_detection_rate, 1.)
        self.assertTrue(np.isinf(result.delay_s))
        self.assertEqual(result.empirical, 'FAIL')

    def test_missing_detection_is_failure_even_if_other_episode_succeeds(self):
        result = self.scenarios(self.fixture(delay=None)).iloc[0]
        self.assertEqual(result.empirical, 'FAIL')
        self.assertTrue(np.isinf(result.delay_s))
        self.assertEqual(result.X_e2e, .5)

    def test_absent_session_not_evaluable_and_cannot_disappear(self):
        frame = self.fixture()
        result = self.scenarios(frame[frame.session_id != 'jam_b']).iloc[0]
        self.assertEqual(result.eligible_total, 2)
        self.assertEqual(result.tested_count, 1)
        self.assertTrue(np.isinf(result.delay_s))
        self.assertEqual(result.X_e2e, .5)
        self.assertEqual(result.empirical, 'NOT EVALUABLE')

    def test_unmeasured_config_never_inherits_execution_claim(self):
        result = self.scenarios(self.fixture())
        measured, unmeasured = result.iloc[0], result.iloc[1]
        self.assertEqual(measured.empirical, 'PASS')
        self.assertEqual(unmeasured.empirical, 'NOT EVALUABLE')
        self.assertEqual(unmeasured.operational_status, 'NOT EVALUABLE')
        self.assertEqual(unmeasured.tested_count, 0)
        self.assertEqual(unmeasured.eligible_total, 2)
        self.assertTrue(np.isinf(unmeasured.delay_s))
        self.assertTrue((result.evidence == 'INSUFFICIENT EVIDENCE').all())

    def test_missing_nonjamming_session_not_hidden_by_another_benign_session(self):
        frame = self.fixture()
        result = build_scenarios(self.library, frame, self.resources, self.cfg, 'realtime',
                                 {'jam_a', 'jam_b'}, {('other_benign', 'benign')}).iloc[0]
        self.assertEqual(result.empirical, 'NOT EVALUABLE')

    def test_resources_are_per_configuration_not_candidate(self):
        resources = self.resources.copy()
        resources.loc[resources.config_id == self.cid, 'pipeline_p95_ms'] = 2.
        result = build_scenarios(self.library, self.fixture(), resources, self.cfg, 'realtime',
                                 {'jam_a', 'jam_b'}).iloc[0]
        self.assertTrue(result.functional_pass)
        self.assertFalse(result.resource_pass)
        self.assertEqual(result.empirical, 'FAIL')

    def test_legacy_shared_consumer_is_rejected(self):
        self.assertTrue(accepted_realtime(self.fixture(), {'workload': 'shared single consumer'}).empty)

    def test_completion_journal_excludes_partial_and_superseded_trials(self):
        rows = pd.DataFrame([dict(config_id='a', session_id='j', workload=ISOLATED_WORKLOAD, run_id=run)
                             for run in ['old', 'latest', 'partial']])
        journal = [dict(config_id='a', session_id='j', workload=ISOLATED_WORKLOAD, run_id=run, status='complete')
                   for run in ['old', 'latest']]
        result = accepted_realtime(rows, {}, journal)
        self.assertEqual(result.run_id.tolist(), ['latest'])
        self.assertTrue(accepted_realtime(rows, {}, []).empty)

    def test_checkpoint_invalidated_when_input_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / 'model.bin'
            model.write_bytes(b'original')
            record = dict(status='complete', input_hashes={'model.bin': hashlib.sha256(model.read_bytes()).hexdigest()})
            journal = root / 'runs.jsonl'
            journal.write_text(json.dumps(record) + '\n')
            with patch.object(summary_module, 'ROOT', root):
                self.assertEqual(summary_module.current_completed_runs(journal), [record])
                model.write_bytes(b'changed')
                self.assertEqual(summary_module.current_completed_runs(journal), [])

    def test_report_derives_delay_counts_exposure_and_resource_method(self):
        primary = self.scenarios(self.fixture(delay=4.)).iloc[:1].copy()
        summary = dict(information_clock_config_count=17, realtime_measured_config_count=1,
                       eligible_jamming_sessions=2, nonjamming_exposure_s={'spoofing': 123.})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'results').mkdir()
            with patch.object(summary_module, 'ROOT', root):
                summary_module.write_report(primary, summary, self.cfg,
                    {'quantile_method': 'fixture_quantile', 'workload': 'fixture_workload'},
                    {'workload': ISOLATED_WORKLOAD})
                text = (root / 'results/REPORT.md').read_text()
                self.assertIn('Information-clock configurations: 17', text)
                self.assertIn('maximum eligible-episode delay 4 s', text)
                self.assertIn('fixture_quantile', text)
                self.assertIn('123 s', text)
                self.assertNotIn('A single eligible episode', text)
                primary.loc[:, 'delay_s'] = 9.876543
                summary_module.write_report(primary, summary, self.cfg, {}, {})
                updated = (root / 'results/REPORT.md').read_text()
                self.assertIn('9.87654 s', updated)
                self.assertNotIn('maximum eligible-episode delay 4 s', updated)

    def test_pareto_never_keeps_infinite_delay(self):
        frame = pd.DataFrame(dict(pipeline_p95_ms=[1., .1], model_bytes=[10, 1], delay_s=[2., np.inf]))
        self.assertEqual(pareto(frame).index.tolist(), [0])


if __name__ == '__main__':
    unittest.main()
