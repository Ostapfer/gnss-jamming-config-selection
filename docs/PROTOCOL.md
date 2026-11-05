# Protocol v2 — frozen development experiment

Archive note: references to inventory, backups, legacy recovery and `history/` describe the preserved local research archive; those private or duplicate files are intentionally omitted from the publication snapshot. Public state is a concise derivative. See [reproduction boundaries](REPRODUCIBILITY.md).

The numeric contract is `configs/experiment.json`. Choices used earlier exploratory evidence; this is not preregistered independent validation. Historical v1 artifacts are preserved in `history/v1_shared_run/`, with corrections in `docs/ERRATUM_V1.md`.

## Calibration and operating conditions

Raw rows retain timestamp order. Duplicate timestamps abort preparation; no interpolation or semantic substitution is permitted. Calibration uses complete finite selected-feature observations in elapsed [0,30] seconds, with at least 25 observations. The median baseline freezes at the first post-calibration message. Normalization is exactly `(x-b)/b`; a zero/nonfinite baseline fails readiness, without epsilon. Attack during the declared clean calibration window is outside operating conditions and aborts preparation explicitly.

## Library and events

The library contains 60 ML candidates (four algorithms, five feature sets, three profiles each) plus six noise/noise+eph rules. DT/KNN/RF positive-class thresholds are {0.5,0.75}; SVM signed margin thresholds are {0,0.5}. Rules use relative thresholds {0.25,0.5,1}, with binary decision-score threshold 0.5. Confirmation counts are {1,2,3}, primary 2; recovery requires two negative observations. Maximum observation-timestamp gap is 1.5 seconds. ML fitting uses all declared post-calibration development attack/spoofing rows; its onset replay is diagnostic and future-informed. Rules have no supervised attack fitting, but their constants were selected with access to development evidence.

Event states are CALIBRATING, IDLE, CONFIRMING, ACTIVE, RECOVERY, and UNAVAILABLE. Invalid input or gaps break confirmation/recovery runs and never recover an open alarm. One closed-alarm entry into ACTIVE is one event. A pre-onset ACTIVE event is not a fresh onset detection. Missing observations do not imply jamming. Open alarms through missingness contribute conservative false-active time. False-event counts belong to the condition at alarm start; durations are truncated at condition/record end, with censoring flags. Attack end is unknown, so terminal alarms are right-censored.

## Cohort, execution and clocks

A fixed cohort requires recording coverage through onset+10 seconds for all T={3,5,10}. Eligibility never depends on predictions. Readiness failures stay in the eligible denominator. Optional `recording_end_us` supplies independent recording coverage; without it, coverage ends at the last GNSS sample and cannot establish continued recording after total GNSS dropout. All present recordings cover the deadline window. Worst eligible-session delay includes infinity for missed/readiness-failed episodes. An entirely unmeasured required session makes an operational scenario NOT EVALUABLE.

Information-clock replay covers all 378 configurations. The execution-clock subset contains exactly the two primary rules in `realtime_config_ids`, selected using v1 development results. The other 376 configurations are NOT EVALUATED operationally. Each selected configuration/session pair uses a fresh spawned detector process, an independent producer process, original timestamps, a common OS monotonic clock, and a readiness handshake. Pairs execute sequentially, with no competing candidate benchmark.

Producer message availability before IPC send defines arrival; IPC/queue waiting belongs to full software latency. Confirmed delay is event-ready time minus mapped annotated onset. Producer scheduling lateness is retained separately and may contribute to this delay; separate trial differences are not intrinsic algorithm costs. No physical receiver/FC/transport latency is included. False-active duration and exposure retain recording clock.

A completion journal is written after result artifacts. Only completed trials whose detector/core, dependency lock, recorded environment, data, configurations and model hashes still match are accepted. The latest matching trial per pair is used. Incomplete/orphaned rows and historical shared-workload trials are rejected.

## Resource workload and budget quantity

Measure one complete threshold/confirmation configuration at a time, sequentially over all 378 configurations. Ten warmup messages use a separate Runner. One full chronological pass through each of the three sessions restarts calibration per session. Each configuration covers all 610 rows: 94 calibration and 516 post-calibration observations, including 447 benign, 50 jamming and 19 spoofing observations. Per-condition counts, empirical state transitions and calibration timing are retained. Synthetic probes are excluded from empirical percentiles. No verified jammer-off recovery ground truth exists; unobserved paths, including UNAVAILABLE when absent, are not claimed measured.

The budget quantity is `max(P95_benign, P95_jamming, P95_spoofing, P95_calibration)`, using linear empirical percentiles. Pooled P50/P99 diagnostics describe a different distribution and are labelled accordingly. Total process RSS includes Python, libraries, the current model, measurement objects and allocator caches; incremental model RSS is unavailable. CPU is process CPU/wall, including initialization/bookkeeping, as percent of one core. Serialized model size excludes runtime code and libraries. These are descriptive finite-workload measurements, not deadline guarantees.

## Stress workload

Five representatives receive requested rates of 100 and 1000 messages/s, with 300 synthetic compressed original observations per trial. An independent producer and readiness handshake isolate offered scheduling from consumer inference. Traces retain scheduled due, actual enqueue, receipt, processing start/end and event-ready clocks. A nominal rate is marked VALID only when actual offered rate is within 5% and producer-lateness P95 is no greater than one nominal interarrival interval. Otherwise it is INVALID_OFFERED_RATE. Report scheduled-to-ready and actual-arrival misses separately. Actual/scheduled queued backlog excludes the in-service message. These short bursts do not establish sustained operational capacity or attack detection performance.

## Screening and evidence

Requirements are X={0.8,0.9,1}, T={3,5,10}s, and Y={0,0.5,1} events/hour, separately for benign and spoofing. Illustrative Mac budgets are condition/calibration P95≤1ms/model≤20KB, or ≤10ms/≤1MB. Filter functional and resource feasibility first; construct Pareto sets over measured resource P95, serialized bytes and worst eligible-episode delay, separately per clock mode, causal status, scenario and budget. Operational fronts contain only configurations with all required isolated-session replays completed.

One eligible episode gives only 0/1 observed timely fraction. One false event in the present benign or spoofing exposure exceeds every declared Y. The 27-grid therefore demonstrates mechanics rather than 27 independent or fully discriminating tests. Every statistical status remains INSUFFICIENT EVIDENCE. No sample-level confidence bound, rare-false-alarm reliability, simultaneous 95% guarantee, independent validation or SBC sufficiency is claimed. Future inferential bounds require independently characterized sessions and explicit assumptions.
