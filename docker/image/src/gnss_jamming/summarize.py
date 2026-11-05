"""Separate diagnostic information clocks from measured execution clocks."""
import itertools
import hashlib
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
os.environ.setdefault('MPLCONFIGDIR', str(Path(__file__).resolve().parents[2] / 'experiments/matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .core import ROOT, config, read_json, sessions, write_json

ISOLATED_WORKLOAD = 'isolated_single_configuration'


def boolean(series):
    return series.map(lambda value: value is True or str(value).lower() == 'true')


def configuration_library(candidates, cfg):
    return pd.DataFrame([
        dict(config_id=f'{c["candidate_id"]}_d{threshold:g}_c{count}', candidate_id=c['candidate_id'],
             causal=c['causal'], algorithm=c['algorithm'], decision_threshold=threshold, confirmation=count)
        for c in candidates for threshold in c['thresholds'] for count in cfg['confirmation_counts']])


def pareto(frame):
    if frame.empty:
        return frame
    vals = frame[['pipeline_p95_ms', 'model_bytes', 'delay_s']].to_numpy(dtype=float)
    keep = [np.isfinite(a).all() and not np.any(np.all(vals <= a, axis=1) & np.any(vals < a, axis=1)) for a in vals]
    return frame.loc[keep]


def configuration_metrics(part, eligible_session_ids, expected_condition_keys=None):
    """Keep measured failures in the denominator; absent sessions are not evaluable."""
    eligible_session_ids = set(eligible_session_ids)
    jam = part[part.session_id.isin(eligible_session_ids)].drop_duplicates('session_id') if not part.empty else part
    eligible, tested = len(eligible_session_ids), len(jam)
    ready = boolean(jam.readiness_success) if tested else pd.Series(dtype=bool)
    delays = pd.to_numeric(jam.confirmed_delay_s, errors='coerce') if tested else pd.Series(dtype=float)
    successful = ready & delays.notna() & np.isfinite(delays)
    worst_delay = float(delays.max()) if eligible and tested == eligible and successful.all() else np.inf
    false_alarms = {}
    if not part.empty:
        for condition, group in part.groupby('condition'):
            exposure, events = float(group.exposure_s.sum()), int(group.false_events.sum())
            false_alarms[condition] = dict(exposure_s=exposure, events=events,
                rate=events * 3600 / exposure if exposure > 0 else np.nan,
                false_active_s=float(group.false_active_s.sum()),
                false_event_duration_max_s=float(group.false_event_duration_max_s.max()) if 'false_event_duration_max_s' in group else np.nan)
    actual_keys = set(zip(part.session_id, part.condition)) if not part.empty else set()
    conditions_complete = (set(expected_condition_keys or []).issubset(actual_keys)
                           and all(false_alarms.get(c, {}).get('exposure_s', 0) > 0 for c in ['benign', 'spoofing']))
    return dict(jam=jam, ready=ready, delays=delays, fa=false_alarms, eligible_total=eligible,
                tested_count=tested, ready_count=int(ready.sum()), delay_s=worst_delay,
                evaluable=eligible > 0 and tested == eligible and conditions_complete)


def build_scenarios(library, metrics, resources, cfg, mode, eligible_session_ids, expected_condition_keys=None):
    """Emit every declared configuration, including unmeasured operational rows."""
    if resources.config_id.duplicated().any():
        raise ValueError('Resource table must have one conservative row per config_id')
    resource_index = resources.set_index('config_id')
    rows = []
    for declared in library.to_dict('records'):
        cid = declared['config_id']
        part = metrics[metrics.config_id == cid] if not metrics.empty else metrics
        aggregate = configuration_metrics(part, eligible_session_ids, expected_condition_keys)
        resource = resource_index.loc[cid] if cid in resource_index.index else pd.Series(dtype=float)
        latency, model_bytes = resource.get('pipeline_p95_ms', np.nan), resource.get('model_bytes', np.nan)
        resource_measured = pd.notna(latency) and np.isfinite(latency) and pd.notna(model_bytes)
        fa = aggregate['fa']
        for X, T, Y, budget in itertools.product(cfg['detection_fraction_requirements'], cfg['detection_deadlines_s'],
                                               cfg['false_alarm_per_hour_requirements'], cfg['resource_budgets']):
            timely = int((aggregate['ready'] & (aggregate['delays'] <= T)).sum())
            total = aggregate['eligible_total']
            rate = timely / total if total else np.nan
            functional = aggregate['evaluable'] and rate >= X and all(fa[c]['rate'] <= Y for c in ['benign', 'spoofing'])
            resource_pass = bool(resource_measured and latency <= budget['pipeline_p95_ms'] and model_bytes <= budget['model_bytes'])
            evaluable = aggregate['evaluable'] and resource_measured
            empirical = 'NOT EVALUABLE' if not evaluable else ('PASS' if functional and resource_pass else 'FAIL')
            row = dict(**declared, mode=mode, requirement_X=X, deadline_T_s=T, false_alarm_Y_per_h=Y,
                       budget=budget['name'], empirical=empirical, evidence='INSUFFICIENT EVIDENCE',
                       functional_pass=bool(functional), resource_pass=resource_pass,
                       operational_status=empirical if mode == 'realtime' else 'NOT EVALUATED',
                       eligible_episodes=total, eligible_total=total, tested_count=aggregate['tested_count'], X_e2e=rate,
                       conditional_detection_rate=timely / aggregate['ready_count'] if aggregate['ready_count'] else np.nan,
                       readiness_success_rate=aggregate['ready_count'] / total if total else np.nan,
                       delay_s=aggregate['delay_s'], pipeline_p95_ms=latency, model_bytes=model_bytes)
            for condition in ['benign', 'spoofing']:
                values = fa.get(condition, {})
                row.update({f'{condition}_fa_per_h': values.get('rate', np.nan),
                            f'{condition}_exposure_s': values.get('exposure_s', np.nan),
                            f'{condition}_false_active_s': values.get('false_active_s', np.nan),
                            f'{condition}_false_event_duration_max_s': values.get('false_event_duration_max_s', np.nan)})
            rows.append(row)
    return pd.DataFrame(rows)


def accepted_realtime(metrics, metadata, completed_runs=None):
    """Accept completed isolated trials only, selecting latest config/session pair."""
    if metrics.empty:
        return metrics
    accepted = metrics.iloc[:0].copy()
    for column in ['replay_workload', 'workload']:
        if column in metrics:
            accepted = metrics[metrics[column] == ISOLATED_WORKLOAD].copy()
            break
    else:
        if metadata.get('workload') == ISOLATED_WORKLOAD:
            accepted = metrics.copy()
    if completed_runs is not None:
        latest = {}
        for record in completed_runs:
            if record.get('status') == 'complete' and record.get('workload') == ISOLATED_WORKLOAD:
                latest[(record['config_id'], record['session_id'])] = record['run_id']
        if 'run_id' not in accepted:
            return accepted.iloc[:0]
        accepted = accepted[accepted.run_id.isin(set(latest.values()))]
    return accepted


def current_completed_runs(path):
    """Invalidate completed checkpoints when any declared input/code hash changed."""
    records = []
    if not path.exists():
        return records
    for line in path.read_text().splitlines():
        record = json.loads(line)
        hashes = record.get('input_hashes', {})
        if hashes and all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                          for name, digest in hashes.items()):
            records.append(record)
    return records


def read_table(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def fmt(value, suffix=''):
    return f'{value:.6g}{suffix}' if pd.notna(value) and np.isfinite(value) else 'NOT DETECTED / UNAVAILABLE'


def write_report(primary, summary, cfg, resource_metadata, run_metadata, stress=None, event_timing=None):
    text = '# Development results\n\n' + '\n'.join(f'- {key}: {value}' for key, value in summary.items()) + '\n\n'
    text += ('ML uses post-calibration development attack/spoofing rows for fitting and replay. '
             'Its information-clock results are diagnostic, in-sample and future-informed; they do not support causal detection claims. '
             'Rule thresholds use no attack labels for fitting but were specified after inspecting legacy data. '
             'Their execution-clock replay remains development exploration.\n\n'
             'All scenario evidence is INSUFFICIENT EVIDENCE. No independent validation, sample-level confidence bound, '
             'simultaneous confidence guarantee or general onboard sufficiency is claimed.\n\n')
    text += '## Cohorts and sensitivity grid\n\n'
    text += (f"Information-clock configurations: {summary['information_clock_config_count']}; "
             f"isolated execution-clock configurations actually measured: {summary['realtime_measured_config_count']}. "
             'Unmeasured configurations remain NOT EVALUABLE for operational scenarios; resource measurements alone do not establish execution-clock detection.\n\n')
    text += (f"Fixed common-deadline jamming cohort: {summary['eligible_jamming_sessions']} sessions/episodes. "
             f"X requirements: {cfg['detection_fraction_requirements']}; deadlines: {cfg['detection_deadlines_s']} s; "
             f"Y requirements: {cfg['false_alarm_per_hour_requirements']} events/hour separately for benign and spoofing. "
             'These grids illustrate selection mechanics; they do not add independent evidence.\n\n')
    if summary['eligible_jamming_sessions'] == 1:
        text += ('A single eligible episode permits only zero or one observed timely fraction, so the declared positive X grid values are nondiscriminating.\n\n')
    for condition, exposure in summary['nonjamming_exposure_s'].items():
        rate = 3600 / exposure if exposure > 0 else np.nan
        text += (f'{condition}: recorded exposure {fmt(exposure, " s")}; one observed false event corresponds to {fmt(rate, " events/hour")}. ')
        if np.isfinite(rate) and rate > max(cfg['false_alarm_per_hour_requirements']):
            text += 'This exceeds every declared Y, so zero versus at least one event gives the same decision throughout this Y grid.'
        text += '\n\n'
    text += '## Measured primary configurations\n\n'
    if primary.empty:
        text += 'No accepted isolated execution-clock primary configuration was measured.\n\n'
    else:
        first = primary.iloc[0]
        budget = next(b for b in cfg['resource_budgets'] if b['name'] == first.budget)
        text += (f"Scenario X={first.requirement_X:g}, T={first.deadline_T_s:g} s, Y={first.false_alarm_Y_per_h:g}/hour; "
                 f"budget {first.budget}: pipeline P95 ≤ {budget['pipeline_p95_ms']} ms, model ≤ {budget['model_bytes']} bytes.\n\n")
        for r in primary.itertuples():
            text += (f'- {r.config_id}: maximum eligible-episode delay {fmt(r.delay_s, " s")}; '
                     f'tested/eligible {r.tested_count}/{r.eligible_total}; '
                     f'benign FA/h {fmt(r.benign_fa_per_h)}, exposure {fmt(r.benign_exposure_s, " s")}; '
                     f'spoofing FA/h {fmt(r.spoofing_fa_per_h)}, exposure {fmt(r.spoofing_exposure_s, " s")}; '
                     f'empirical {r.empirical}; INSUFFICIENT EVIDENCE.\n')
    text += ('\nWorst-episode delay is infinite if any eligible episode has no detection, fails readiness, or was not measured. '
             'Readiness failures remain in the end-to-end denominator. Entirely missing replay sessions make a scenario NOT EVALUABLE.\n\n'
             'The historical 5.982160 s value is documented in docs/legacy_recovery.json; its ML fit used later samples '
             'of the same attack. It is a historical development-contaminated diagnostic, not a new measured result.\n\n')
    text += '## Resource and timing boundary\n\n'
    text += (f"Resource workload: {resource_metadata.get('workload', resource_metadata.get('timing', 'see resource run manifest'))}. "
             f"Percentile method: {resource_metadata.get('quantile_method', resource_metadata.get('percentile_method', 'see resource run manifest'))}. "
             'resources.csv is keyed by full detector configuration; pipeline_p95_ms is the maximum of condition-specific and calibration P95 values, '
             'not a pooled percentile. The resource plot collapses configurations to each candidate’s largest measured P95.\n\n'
             f"Execution workload: {run_metadata.get('workload', 'NOT EVALUATED')}. "
             'Execution delay uses event-ready time relative to mapped annotated onset. False-active durations and exposure use recording time. '
             'Physical receiver/transport latency is outside the measured boundary. Pareto fronts are conditional empirical development '
             'fronts per requirement, budget, clock mode and causal status on this platform.\n')
    if event_timing is not None and not event_timing.empty:
        text += '\n## Triggering-message scheduling diagnostics\n\n'
        text += ('Execution-clock delay includes replay-producer schedule lateness and IPC/processing. '
                 'Differences between separate trials cannot be interpreted as intrinsic algorithm cost. '
                 'Components below describe the triggering message; processing completion can be slightly later than the event-ready instant.\n\n')
        for row in event_timing.itertuples():
            text += (f'- {row.config_id}, {row.session_id}: information delay {fmt(row.information_delay_s, " s")}; '
                     f'execution delay {fmt(row.confirmed_delay_s, " s")}; '
                     f'producer lateness {fmt(row.producer_lateness_ms, " ms")}; '
                     f'IPC/queue {fmt(row.queue_ms, " ms")}; processing {fmt(row.processing_ms, " ms")}.\n')
    if stress is not None and not stress.empty:
        text += '\n## Short synthetic stress windows\n\n'
        valid = int((stress.workload_status == 'VALID_OFFERED_RATE').sum())
        text += (f'Offered-rate validity: {valid}/{len(stress)} trials met the frozen scheduling criteria. '
                 f'Messages per trial: {sorted(stress.messages.unique().tolist())}. '
                 'These finite bursts are not a sustained operational capacity guarantee; stress is not attack validation. '
                 'Scheduled misses include source lateness; arrival-based misses begin at actual IPC availability.\n\n')
        for row in stress.itertuples():
            text += (f'- {row.config_id}: requested {row.requested_hz:g}/s, actual offered {fmt(row.actual_offered_hz, "/s")}; '
                     f'{row.workload_status}; scheduled misses {row.scheduled_to_ready_deadline_misses}/{row.messages}; '
                     f'arrival-based misses {row.actual_arrival_deadline_misses}/{row.messages}; '
                     f'queued backlog maximum {row.max_backlog}.\n')
    (ROOT / 'results/REPORT.md').write_text(text)


def main():
    cfg = config()
    candidates = read_json(ROOT / 'experiments/candidates.json')
    library = configuration_library(candidates, cfg)
    resources = pd.read_csv(ROOT / 'results/tables/resources.csv')
    if 'config_id' not in resources:
        raise ValueError('Legacy candidate-only resource table is unsupported; rerun per-configuration benchmark')
    info = read_table(ROOT / 'results/tables/information_clock_development_metrics.csv')
    if info.empty:
        raise ValueError('Information-clock replay is required to define the fixed development cohort')
    eligible = set(info.loc[boolean(info.eligible_episode), 'session_id'])
    expected_keys = set(zip(info.session_id, info.condition))
    realtime_path = ROOT / 'experiments/realtime_run.json'
    realtime_metadata = read_json(realtime_path) if realtime_path.exists() else {}
    completed_runs = current_completed_runs(ROOT / 'results/tables/realtime_runs.jsonl')
    realtime = accepted_realtime(read_table(ROOT / 'results/tables/realtime_metrics.csv'), realtime_metadata, completed_runs)
    if not realtime.empty:
        realtime_metadata = {'workload': ISOLATED_WORKLOAD, 'completed_trials': len(set(realtime.run_id))}
    scenarios = pd.concat([build_scenarios(library, frame, resources, cfg, mode, eligible, expected_keys)
                           for mode, frame in [('information_clock_development', info), ('realtime', realtime)]], ignore_index=True)
    scenarios.to_csv(ROOT / 'results/tables/scenarios.csv', index=False)
    keys = ['mode', 'causal', 'requirement_X', 'deadline_T_s', 'false_alarm_Y_per_h', 'budget']
    fronts = [pareto(part) for _, part in scenarios[scenarios.empirical == 'PASS'].groupby(keys)]
    (pd.concat(fronts, ignore_index=True) if fronts else pd.DataFrame(columns=scenarios.columns)).to_csv(ROOT / 'results/tables/pareto.csv', index=False)
    plot = resources.merge(library[['config_id', 'algorithm']], on='config_id', validate='one_to_one')
    plot = plot.groupby(['candidate_id', 'algorithm'], as_index=False).agg(model_bytes=('model_bytes', 'max'), pipeline_p95_ms=('pipeline_p95_ms', 'max'))
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, part in plot.groupby('algorithm'):
        ax.scatter(part.model_bytes, part.pipeline_p95_ms, label=label, alpha=.7)
    ax.set(xscale='log', yscale='log', xlabel='Serialized model size (bytes)', ylabel='Maximum condition/calibration P95 (ms)',
           title='Mac isolated full pipeline — maximum across candidate configurations')
    ax.legend(); fig.tight_layout(); fig.savefig(ROOT / 'results/figures/resources.png', dpi=180); plt.close(fig)
    data = pd.read_csv(ROOT / 'data/derived/development.csv')
    jam_sessions = [s for s in sessions() if s['attack_type'] == 'jamming' and s['onset_us'] is not None]
    if jam_sessions:
        fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
        for session in jam_sessions:
            part = data[data.session_id == session['session_id']]
            onset = (session['onset_us'] - int(part.timestamp.iloc[0])) / 1e6
            for ax, feature in zip(axes, ['noise_per_ms', 'eph']):
                ax.plot(part.elapsed_s - onset, part[feature], label=session['session_id'])
                ax.axvline(0, color='red', linestyle='--'); ax.set_ylabel(feature); ax.grid(alpha=.2)
        axes[0].legend(); axes[-1].set_xlabel('Seconds from annotated onset (physical jammer-on unknown)')
        fig.tight_layout(); fig.savefig(ROOT / 'results/figures/jamming_timeline.png', dpi=180); plt.close(fig)
    selected = cfg.get('primary_scenario', {})
    primary = scenarios[(scenarios['mode'] == 'realtime') & (scenarios.deadline_T_s == selected.get('T_s', max(cfg['detection_deadlines_s'])))
                        & (scenarios.requirement_X == selected.get('X', max(cfg['detection_fraction_requirements'])))
                        & (scenarios.false_alarm_Y_per_h == selected.get('Y_per_h', min(cfg['false_alarm_per_hour_requirements'])))
                        & (scenarios.budget == selected.get('budget', cfg['resource_budgets'][-1]['name']))]
    primary.to_csv(ROOT / 'results/tables/primary_scenario.csv', index=False)
    measured_ids = set(realtime.config_id) if not realtime.empty else set()
    primary_measured = primary[primary.config_id.isin(measured_ids) & boolean(primary.causal)
                               & (primary.confirmation == cfg['primary_confirmation'])]
    declared_sessions = sessions()
    summary = dict(candidate_count=len(candidates), detector_config_count=len(library),
                   information_clock_config_count=int(info.config_id.nunique()), realtime_measured_config_count=len(measured_ids),
                   measured_primary_configurations=primary_measured.config_id.tolist(),
                   primary_causal_empirical_passes=int((primary_measured.empirical == 'PASS').sum()),
                   all_evidence='INSUFFICIENT EVIDENCE',
                   independent_jamming_sessions=sum(s['attack_type'] == 'jamming' and s.get('independence_established', False) and s.get('role') == 'independent_validation' for s in declared_sessions),
                   eligible_jamming_sessions=len(eligible),
                   nonjamming_exposure_s={condition: float(part.exposure_s.sum()) for condition, part in info[info.config_id == library.config_id.iloc[0]].groupby('condition')},
                   development_jamming_sessions=sum(s['attack_type'] == 'jamming' for s in declared_sessions),
                   development_spoofing_sessions=sum(s['attack_type'] == 'spoofing' for s in declared_sessions),
                   supplementary_benign_sessions=sum(s['attack_type'] == 'benign' for s in declared_sessions))
    write_json(ROOT / 'results/summary.json', summary)
    resource_path = ROOT / 'experiments/resource_run.json'
    resource_metadata = read_json(resource_path) if resource_path.exists() else {}
    events = read_table(ROOT / 'results/tables/realtime_events.csv')
    timings = read_table(ROOT / 'results/tables/realtime_timings.csv')
    diagnostics = []
    if not events.empty and not timings.empty and not realtime.empty:
        ids = set(realtime.run_id)
        events = events[events.run_id.isin(ids)]
        for session in declared_sessions:
            if session['session_id'] not in eligible:
                continue
            part = data[data.session_id == session['session_id']]
            onset = (session['onset_us'] - int(part.timestamp.iloc[0])) / 1e6
            selected_events = events[(events.session_id == session['session_id']) & (events.start_s >= onset)]
            for cid, group in selected_events.groupby('config_id'):
                event = group.sort_values('ready_s').iloc[0]
                trigger = timings[(timings.run_id == event.run_id) & np.isclose(timings.elapsed_s, event.start_s, atol=1e-8, rtol=0)]
                if not trigger.empty:
                    row = trigger.iloc[0]
                    diagnostics.append(dict(config_id=cid, session_id=session['session_id'],
                        information_delay_s=event.start_s-onset, confirmed_delay_s=event.ready_s-onset,
                        producer_lateness_ms=row.producer_lateness_ms, queue_ms=row.queue_ms, processing_ms=row.processing_ms))
    event_timing = pd.DataFrame(diagnostics)
    event_timing.to_csv(ROOT / 'results/tables/triggering_message_timing.csv', index=False)
    write_report(primary_measured, summary, cfg, resource_metadata, realtime_metadata,
                 read_table(ROOT / 'results/tables/stress.csv'), event_timing)
    print(summary)


if __name__ == '__main__':
    main()
