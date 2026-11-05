"""Reconcile shipped aggregate tables and render the final article resource report.

Standard library only; does not download data, load models or rerun inference.
The archive reconciles published aggregates, not unavailable original traces.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def reconstruct(root, output):
    archive=root/'results/igaspin_resource_20261105'
    report=json.loads((archive/'report.json').read_text())
    with (archive/'trial_metrics.csv').open() as f:trials=list(csv.DictReader(f))
    valid=[x for x in trials if x['source_schedule_valid']=='True']
    assert len(trials)==report['completed_trials']==80
    assert len(valid)==report['source_schedule_valid_trials']==79
    assert sum(int(x['messages']) for x in trials)==report['offered_accepted_processed_messages_all80']==29600
    assert sum(int(x['messages']) for x in valid)==report['messages_source_valid79']==29238
    assert sum(int(x['drops']) for x in trials)==report['drops']==0
    assert not any(x['oom_killed']=='True' for x in trials)
    assert [x['trial'] for x in trials if x not in valid]==['igaspin_017']
    lines=['# Final article resource results','',
           'IGASPIN: 80 completed trials; 79 source-schedule-valid; 29,600 messages; 0 drops; 0 OOM.',
           'Trial 017 is retained but excluded from timing comparisons. This is repetition of two recordings, not 80 independent sessions.',
           '', '## Whole-stream processing P95 ranges','',
           '| Configuration | Profile | Valid streams | Minimum, ms | Maximum, ms |',
           '|---|---|---:|---:|---:|']
    with (archive/'processing_p95_ranges.csv').open() as f:
        for x in csv.DictReader(f):
            lines.append(f"| {x['config_id']} | {x['profile_id']} | {x['valid_runs']} | {float(x['whole_stream_processing_p95_min_ms']):.6f} | {float(x['whole_stream_processing_p95_max_ms']):.6f} |")
    lines.extend(['','Within-trial P95 includes calibration/unavailable messages. Ranges are neither pooled quantiles nor confidence intervals.',
                  '', '## Conditional events',''])
    for x in report['event_results_valid_jamming_only']:
        lines.append(f"- {x['config_id']}: {x['runs_with_new_post_reference_alarm']}/{x['valid_jamming_runs']} valid replays with a fresh post-reference alarm; carry-in runs: {x['carry_in_runs']}.")
    lines.extend(['','DT information delay: 10.999723103 s; execution-ready delay: 11.002824–11.014832 s. Other four variants have no fresh post-reference alarm.',
                  'Provider-reference timing is conditional. Physical-onset detection and operational FAR remain NOT EVALUABLE.',
                  'UBX decoding and RF/NAV association precede the measured prepared-message-to-event-ready path.',
                  '', '## Development repeat','',
                  'The separate development repeat completed 60 trials; 59 were source-valid. It does not add independent attack sessions.',
                  'See results/development_repeat_20261104 for the matched 59 records and 19 complete configuration/profile comparison.',
                  '', '## Provenance',''])
    for p in sorted(archive.glob('*')):
        if p.is_file():lines.append(f'- {p.name}: `{hashlib.sha256(p.read_bytes()).hexdigest()}`')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text('\n'.join(lines)+'\n')
    print('Final aggregate reconciliation PASS; report written to '+str(output))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/final-results.md')
    a=p.parse_args();reconstruct(ROOT,a.output.resolve())
