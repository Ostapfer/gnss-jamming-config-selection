"""Reproduce illustrative finite-library selection from supplied historical vectors.

Standard library only. No models, raw telemetry or measurement execution.
"""
import argparse
import csv
import json
from pathlib import Path

OBJECTIVES = ('confirmed_delay_s', 'processing_phase_p95_max_ms', 'model_bytes')

def pareto(rows):
    def dominates(a, b):
        return all(a[k] <= b[k] for k in OBJECTIVES) and any(a[k] < b[k] for k in OBJECTIVES)
    return [r['config_id'] for r in rows if not any(dominates(other, r) for other in rows)]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vectors', type=Path, default=Path(__file__).with_name('selection_vectors.csv'))
    parser.add_argument('--profile', default='cpu1_ram512')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2]/'build/selection_reproduced.json')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new --output path to preserve prior results.')
    rows = list(csv.DictReader(args.vectors.open(newline='')))
    keys = [(r['config_id'], r['profile_id']) for r in rows]
    if len(rows) != 20 or len(set(keys)) != 20:
        parser.error('Expected exactly twenty unique historical detector/profile vectors.')
    selected = []
    for row in rows:
        if row['profile_id'] != args.profile:
            continue
        r = dict(row)
        for name in OBJECTIVES + ('benign_false_events_per_hour', 'spoofing_false_events_per_hour', 'readiness_success_rate_jamming'):
            r[name] = float(r[name])
        selected.append(r)
    if len(selected) != 5:
        parser.error('Expected exactly five variants in the selected fixed profile.')
    scenarios = []
    for deadline in (3, 10):
        feasible = [r for r in selected if r['readiness_success_rate_jamming'] == 1 and
                    r['confirmed_delay_s'] <= deadline and
                    r['benign_false_events_per_hour'] <= 0 and
                    r['spoofing_false_events_per_hour'] <= 0]
        # These are deliberately post-hoc illustration limits, not historical requirements.
        budgeted = [r for r in feasible if r['processing_phase_p95_max_ms'] <= 50 and r['model_bytes'] <= 10240]
        scenarios.append({'T_s': deadline, 'functional_feasible_ids': [r['config_id'] for r in feasible],
                          'pareto_ids': pareto(feasible),
                          'posthoc_illustrative_budget': {'processing_phase_p95_max_ms_le': 50,
                              'model_bytes_le': 10240, 'feasible_ids': [r['config_id'] for r in budgeted],
                              'pareto_ids': pareto(budgeted)}})
    result = {'status': 'ARITHMETIC_RECONSTRUCTION_ONLY', 'profile_id': args.profile,
              'X': 1, 'Y_benign': 0, 'Y_spoofing': 0, 'objectives': OBJECTIVES,
              'new_measurements': False, 'independent_validation': False,
              'evidence_status': 'INSUFFICIENT_EVIDENCE', 'scenarios': scenarios}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(args.output)

if __name__ == '__main__':
    main()
