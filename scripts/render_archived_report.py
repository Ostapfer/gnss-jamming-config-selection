"""Render a compact native-v2 report from shipped summaries; no model execution."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def render(output):
    paths=[ROOT/'results/summary.json',ROOT/'results/tables/raw_counts.csv',ROOT/'results/tables/realtime_metrics.csv']
    summary=json.loads(paths[0].read_text())
    with paths[1].open() as f:counts=list(csv.DictReader(f))
    with paths[2].open() as f:metrics=list(csv.DictReader(f))
    lines=['# Archived native-v2 development results','',
           'Rebuilt from shipped summary tables. No fitting, replay or new timing measurement.',
           'This report describes native v2 only; Docker and conditional external results are separate.','',
           f"Candidates: {summary['candidate_count']}; full configurations: {summary['detector_config_count']}; original-rate measured configurations: {summary['realtime_measured_config_count']}.",
           '', '## Raw counts', '', '| Session | Condition | Rows |','|---|---|---:|']
    for row in counts:lines.append(f"| {row['session_id']} | {row['state']} | {row['raw_count']} |")
    lines += ['', '## Eligible jamming execution delays', '', '| Configuration | Execution delay (s) | Information delay (s) |','|---|---:|---:|']
    seen=set()
    for row in metrics:
        if row['attack_type']!='jamming' or row['config_id'] in seen:continue
        seen.add(row['config_id'])
        lines.append(f"| {row['config_id']} | {row['confirmed_delay_s']} | {row['information_delay_s']} |")
    lines += ['', 'One development jamming session; thresholds selected using development evidence. ML fits/replays overlap. Annotated onset is not physical RF-on. All statistical evidence: INSUFFICIENT EVIDENCE.', '', '## Input provenance', '']
    for path in paths:lines.append(f"- `{path.relative_to(ROOT)}`: SHA256 `{hashlib.sha256(path.read_bytes()).hexdigest()}`")
    if output.exists():raise FileExistsError('Use a new report path; existing output will not be overwritten')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text('\n'.join(lines)+'\n');print(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    render(p.parse_args().output)
