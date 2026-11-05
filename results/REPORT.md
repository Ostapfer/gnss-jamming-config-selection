# Development results

- candidate_count: 66
- detector_config_count: 378
- information_clock_config_count: 378
- realtime_measured_config_count: 2
- measured_primary_configurations: ['RULE_noise_t2_d0.5_c2', 'RULE_noise_eph_t2_d0.5_c2']
- primary_causal_empirical_passes: 2
- all_evidence: INSUFFICIENT EVIDENCE
- independent_jamming_sessions: 0
- eligible_jamming_sessions: 1
- nonjamming_exposure_s: {'benign': 445.046782, 'spoofing': 18.983951999999988}
- development_jamming_sessions: 1
- development_spoofing_sessions: 1
- supplementary_benign_sessions: 1

ML uses post-calibration development attack/spoofing rows for fitting and replay. Its information-clock results are diagnostic, in-sample and future-informed; they do not support causal detection claims. Rule thresholds use no attack labels for fitting but were specified after inspecting legacy data. Their execution-clock replay remains development exploration.

All scenario evidence is INSUFFICIENT EVIDENCE. No independent validation, sample-level confidence bound, simultaneous confidence guarantee or general onboard sufficiency is claimed.

## Cohorts and sensitivity grid

Information-clock configurations: 378; isolated execution-clock configurations actually measured: 2. Unmeasured configurations remain NOT EVALUABLE for operational scenarios; resource measurements alone do not establish execution-clock detection.

Fixed common-deadline jamming cohort: 1 sessions/episodes. X requirements: [0.8, 0.9, 1.0]; deadlines: [3, 5, 10] s; Y requirements: [0, 0.5, 1.0] events/hour separately for benign and spoofing. These grids illustrate selection mechanics; they do not add independent evidence.

A single eligible episode permits only zero or one observed timely fraction, so the declared positive X grid values are nondiscriminating.

benign: recorded exposure 445.047 s; one observed false event corresponds to 8.08904 events/hour. This exceeds every declared Y, so zero versus at least one event gives the same decision throughout this Y grid.

spoofing: recorded exposure 18.984 s; one observed false event corresponds to 189.634 events/hour. This exceeds every declared Y, so zero versus at least one event gives the same decision throughout this Y grid.

## Measured primary configurations

Scenario X=1, T=10 s, Y=0/hour; budget mac_experimental_10: pipeline P95 ≤ 10 ms, model ≤ 1000000 bytes.

- RULE_noise_t2_d0.5_c2: maximum eligible-episode delay 7.98889 s; tested/eligible 1/1; benign FA/h 0, exposure 445.047 s; spoofing FA/h 0, exposure 18.984 s; empirical PASS; INSUFFICIENT EVIDENCE.
- RULE_noise_eph_t2_d0.5_c2: maximum eligible-episode delay 8.08501 s; tested/eligible 1/1; benign FA/h 0, exposure 445.047 s; spoofing FA/h 0, exposure 18.984 s; empirical PASS; INSUFFICIENT EVIDENCE.

Worst-episode delay is infinite if any eligible episode has no detection, fails readiness, or was not measured. Readiness failures remain in the end-to-end denominator. Entirely missing replay sessions make a scenario NOT EVALUABLE.

The historical 5.982160 s value is documented in docs/legacy_recovery.json; its ML fit used later samples of the same attack. It is a historical development-contaminated diagnostic, not a new measured result.

## Resource and timing boundary

Resource workload: one isolated complete configuration sequentially; every chronological raw-derived row in all 3 sessions; fresh causal calibration per session/pass; batch=1 Runner.step; per-message timing excludes model load/file I/O. Percentile method: numpy percentile linear; descriptive, not confidence bounds. resources.csv is keyed by full detector configuration; pipeline_p95_ms is the maximum of condition-specific and calibration P95 values, not a pooled percentile. The resource plot collapses configurations to each candidate’s largest measured P95.

Execution workload: isolated_single_configuration. Execution delay uses event-ready time relative to mapped annotated onset. False-active durations and exposure use recording time. Physical receiver/transport latency is outside the measured boundary. Pareto fronts are conditional empirical development fronts per requirement, budget, clock mode and causal status on this platform.

## Triggering-message scheduling diagnostics

Execution-clock delay includes replay-producer schedule lateness and IPC/processing. Differences between separate trials cannot be interpreted as intrinsic algorithm cost. Components below describe the triggering message; processing completion can be slightly later than the event-ready instant.

- RULE_noise_eph_t2_d0.5_c2, jamming: information delay 7.98415 s; execution delay 8.08501 s; producer lateness 91.7423 ms; IPC/queue 2.57925 ms; processing 6.54908 ms.
- RULE_noise_t2_d0.5_c2, jamming: information delay 7.98415 s; execution delay 7.98889 s; producer lateness 2.43808 ms; IPC/queue 0.425958 ms; processing 1.88154 ms.

## Short synthetic stress windows

Offered-rate validity: 10/10 trials met the frozen scheduling criteria. Messages per trial: [300]. These finite bursts are not a sustained operational capacity guarantee; stress is not attack validation. Scheduled misses include source lateness; arrival-based misses begin at actual IPC availability.

- DT_f3_p2_d0.5_c2: requested 100/s, actual offered 100.086/s; VALID_OFFERED_RATE; scheduled misses 1/300; arrival-based misses 0/300; queued backlog maximum 0.
- DT_f3_p2_d0.5_c2: requested 1000/s, actual offered 1002.51/s; VALID_OFFERED_RATE; scheduled misses 2/300; arrival-based misses 2/300; queued backlog maximum 1.
- KNN_f3_p1_d0.5_c2: requested 100/s, actual offered 100.092/s; VALID_OFFERED_RATE; scheduled misses 1/300; arrival-based misses 1/300; queued backlog maximum 0.
- KNN_f3_p1_d0.5_c2: requested 1000/s, actual offered 1016.38/s; VALID_OFFERED_RATE; scheduled misses 21/300; arrival-based misses 15/300; queued backlog maximum 6.
- SVM_f3_p2_d0_c2: requested 100/s, actual offered 100.142/s; VALID_OFFERED_RATE; scheduled misses 1/300; arrival-based misses 0/300; queued backlog maximum 0.
- SVM_f3_p2_d0_c2: requested 1000/s, actual offered 1015.62/s; VALID_OFFERED_RATE; scheduled misses 11/300; arrival-based misses 10/300; queued backlog maximum 5.
- RF_f3_p3_d0.5_c2: requested 100/s, actual offered 100.101/s; VALID_OFFERED_RATE; scheduled misses 3/300; arrival-based misses 3/300; queued backlog maximum 0.
- RF_f3_p3_d0.5_c2: requested 1000/s, actual offered 1013.53/s; VALID_OFFERED_RATE; scheduled misses 300/300; arrival-based misses 300/300; queued backlog maximum 248.
- RULE_noise_t2_d0.5_c2: requested 100/s, actual offered 100.165/s; VALID_OFFERED_RATE; scheduled misses 1/300; arrival-based misses 0/300; queued backlog maximum 1.
- RULE_noise_t2_d0.5_c2: requested 1000/s, actual offered 1012.59/s; VALID_OFFERED_RATE; scheduled misses 9/300; arrival-based misses 1/300; queued backlog maximum 4.
