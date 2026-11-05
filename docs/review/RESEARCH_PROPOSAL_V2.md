# Research proposal v2: evidence-based resource-pilot architecture

26 October 2026. Status: **PROPOSED_FOR_REVIEW, NOT_IMPLEMENTED, NOT_VALIDATED**. This proposes a decision following review; it does not describe an already completed constrained experiment. Runtime, Compose, models and data sources were unchanged in this task; no measurements were run.

## 1. Question addressed by the pilot

For five frozen detector configurations, investigate whether readiness, queues, confirmed delay and software failures change under declared CPU/RAM ceilings in the local Linux ARM64 Docker VM. This is **resource sensitivity of a particular implementation**. Equivalence between a CPU quota and a real UAV processor is outside this question and requires separate evidence.

The scientific basis for mechanisms and measurement is [RESOURCE_METHOD_EVIDENCE.md](RESOURCE_METHOD_EVIDENCE.md) and the source-to-claim map `resource_method_sources.json`. Source verification covers existing solutions, alternatives and evidence limits, separately from executing a local prototype. Its materials are `docs/evidence/CONTAINER_METHOD_EVIDENCE.md` and `citation_ledger.json`. A source does not close local technical blockers: implementation must address and verify them **only after the design gate**. Source-supported design acceptance is not measurement readiness.

## 2. Alternatives

| Alternative | Permitted claim | Requirements | Limits and decision for the first article |
|---|---|---|---|
| **A. Container resource sensitivity** | “The configuration met/did not meet requirements in the tested Linux VM under specified enforced limits and workload” | Same-image reference, independent producer, bounded instrumentation, failure accounting and actual resource/clock evidence | Does not emulate an SBC. Smallest extension of existing work; **recommended for design acceptance** if the second methodology review accepts the literature rationale and implementation conditions. Implementation must then close the three local blockers before measurement |
| **B. Calibrated virtual approximation of a target device** | Only after validation: “For specified workloads, this model approximates specified metrics of a particular device within a declared error” | Named target; measurements of its CPU/memory/cache/I/O/runtime; a calibration procedure and untouched workloads for error validation | A quota alone does not establish this mapping. No calibration hardware evidence is currently available; **not recommended as a shortcut**. Suitability requires separate supporting evidence |
| **C. Physical board / hardware-in-the-loop** | “The result was obtained on the named board, firmware/runtime, workload and operating mode” | Available board, deployment, controlled message delivery, actual memory/clock/power conditions and logs | Most direct route to a conclusion about that board, but availability is unestablished. Optional extension; new RF transmission is unnecessary because resource replay can deliver recorded telemetry |

Higher accuracy of another model or a different popular dataset does not establish hardware equivalence for B. Docker enables operational resource control, but A's scientific value depends on correct endpoints and failure accounting, not the tool's name.

## 3. Agreed parameters — not reopened

Authoritative scope: `PILOT_SCOPE.json` and `REVIEW_DECISION.md`.

- Configurations: `RULE_noise_t2_d0.5_c2`, `DT_f3_p2_d0.5_c2`, `KNN_f3_p1_d0.5_c2`, `SVM_f3_p2_d0_c2`, `RF_f3_p3_d0.5_c2`.
- Profiles: guarded reference without a container CPU quota and with 1536 MiB; 1/0.5/0.25 CPU at 512 MiB. Period 100 ms; swap disabled; one math-library thread.
- Three unchanged development recordings and one technical trial per combination; 60 trials, with the seed-42 order already recorded. Original-rate playback totals at least 12080.49766 s, approximately 3.356 h without overhead. This is not a trial-repeatability study.
- Comparing 1/0.5/0.25 CPU at the same 512 MiB supports a CPU-factor analysis with other conditions held constant. The guarded reference has a different RAM ceiling; its contrast with restricted profiles is not a pure CPU effect. This pilot establishes neither a RAM minimum nor the 256/1024 MiB factor.
- Selection of the five configurations is development-informed; ML fitting included later rows from the same episodes. No independence/generalization claims. The remaining library does not automatically receive operational evaluation.

## 4. Proposed architecture A

### Controller and independent source

Before launch, a separate controller records each attempt: configuration/profile/session/trial, seed/order, image/source/input/model hashes and planned duration. It starts the producer and detector in **different cgroups within the same Linux VM**. The producer is not a child workload inside the detector cgroup, does not use inference outcomes to regulate cadence and does not adjust the next due time to the preceding send.

Scheduling follows original timestamps. The producer records sequence, scheduled_due, send_attempt, send_completion/source lateness and transport state. Separate detector limits do not guarantee CPU availability to the producer: any mismatch between actual delivery and the declared workload must remain visible.

### Clock and transport — local implementation checks after the design gate

A Linux monotonic clock is proposed for both components, with verification of clock implementation and time namespace. Native macOS `perf_counter` is not subtracted from a Linux clock. Establish the shared-clock property before calculating queue or event delay; an identical Python API name does not establish it.

The IPC candidate is local message transport with explicitly bounded socket/buffer capacities and sequence IDs; Unix-domain sockets in a shared Linux volume are a design candidate. This is **not yet selected or verified transport**. Local TCP in a private Docker network is an alternative if UDS is unsuitable; overhead/clock/failure semantics must be checked equally. After design acceptance, select the transport from local integration results, not from which makes the detector appear fastest. Literature does not replace these engineering checks.

**Declared arrival boundary: the message has been accepted by the declared bounded ingress and is available to the detector pipeline** (`accepted_ingress_available`). A before-send timestamp is diagnostic evidence of sending intent, not receiver arrival. The actual transport must implement and verify an observable acceptance/availability event; if none exists, before-send time cannot substitute for it. Retain due, attempt, send_done, accepted_ingress_available, received, processing_start, event_ready and sequences. Queue measurement covers every buffer in the declared path; a hidden broker cannot remove backlog from accounting. The primary attack endpoint remains **`event_ready_time − mapped_annotated_onset_time`**; ingress time supports correct decomposition rather than moving the attack start.

Queue capacity, drop/backpressure policy, send/startup/completion timeouts, source-validity criteria and evidence-loss policy are not yet numerical. They may remain pending at design acceptance, but **must** be selected, tested and frozen before `VERIFIED_FOR_MEASUREMENT` and measured runs. No unrecorded drops, unbounded queues or retry loops that silently alter source rate. Ingress overflow caused by a slow detector or its backpressure cannot automatically be labelled “source-invalid”: it is an in-scope pipeline failure/drop outcome retained in accounting. A genuine producer clock/scheduler failure requires separate evidence.

### Detector with an explicit input root

Separate code root, read-only input root and output/transport endpoints. The measured Runner receives paths/configuration/model explicitly, rather than through changes to module-global ROOT after import. A failed mount/hash/schema check is an explicit startup failure before the trial.

The new wrapper must execute **the same** calibration, relative normalization, scoring, confirmation and recovery rules. Porting code is not a new fit or a new library. Full-pipeline functional parity **for the five selected pilot configurations** is mandatory before timing runs; direct pickle-prediction probes do not replace it. Admission of the other 61 models is an optional broader-coverage check, not a blocker to this pilot. Declare numerical score tolerance before checking; it **cannot permit** changes in threshold crossings, positive decisions, states or events. Investigate near-threshold discrepancies instead of ignoring them within tolerance.

### Bounded instrumentation and an external collector

The detector budget includes runtime, the selected model, calibration/state and explicitly bounded input/output/log buffers. Full prediction/timing/event histories go to an external collector; internal lists must not grow with the complete recording duration. Reconstruct event history needed for offline metrics externally; retain the current alarm state and counters inside the detector.

This proposed memory scope requires methodology review. Moving queues/logging outside does not justify claiming that the **whole** system pipeline consumes only detector-container RAM. Report detector cgroup memory, producer/collector overhead and the declared total architecture separately. An independent collector does not reduce recorded end-to-end delay.

The collector can also create backpressure, requiring bounded transport, a dropped-log counter and an evidence-loss policy. A trial must not silently pass when its endpoint requires a full trace that is missing. The final distinction between evidence-invalid and operational failure depends on the declared deployed logging role and must be frozen before execution.

Lifecycle markers: beforeimports, afterimports, aftermodelload, aftercalibration, streaming, final. An external monitor gathers available cpu.stat/memory counters and inspect output before cleanup. Check availability of newer kernel fields such as peak counters; unavailable values are not zero. Sampling and overhead remain visible. The approximately 17 MiB snapshot from the previous probe is before-import only.

### Failure journal

Create the attempt journal before container start and append even after startup timeout, exit, OOM, missing completion marker or partial trace. Records include validity gate, source schedule, detector deadline outcomes, final exit/OOM evidence, missing sequences and collector completeness. If the controller is interrupted, recovery labels the pending attempt incomplete rather than removing it.

Mandatory distinctions: demonstrated infrastructure-invalid workload; detector startup/readiness failure; in-scope queue/drop/operational miss; completed run. A slow detector/backpressure does not justify automatic exclusion as an invalid source. Exit 137 alone does not prove OOM. Count eligible episodes and failures under a predefined policy; zero successful trials cannot become a zero-delay result.

## 5. Evidence versus assumptions

**Resolved facts:** Docker enforced ceilings were verified in one smoke check; the current probe bypasses Runner; the native replay producer belongs to the detector process tree; current timing/prediction lists grow; common environment controls do not establish SBC equivalence; the selected 60-pair pilot is already defined.

**Assumptions, not facts:** shared monotonic clock between the future containers; a non-overloaded source; acceptable bounded-logging overhead; 512 MiB sufficient for the full runtime; quotas may or may not cause throttling at 1 Hz. Check these through local integration tests and the pilot, not literature alone; absence of a smoke error establishes none of them.

**Scientific evidence required:** any option-B mapping to target hardware, if claimed; causal interpretation of the joint CPU/RAM reference contrast; sufficient repetitions for strong resource-tail claims. The present single-trial scope supports a descriptive pilot.

**Engineering evidence required:** actual cgroup separation/limits, full Runner paths, clock domain/transport, queue policy, bounded instrumentation, counter collection and failure journaling. Resolve these through implementation tests rather than user questions about technical facts.

## 6. Separate gates: design acceptance and measurement authorization

### DESIGN_ACCEPTED_FOR_IMPLEMENTATION

Proposal → critical review → verification of source precedents, alternatives and counterevidence → decision reassessment. This gate accepts claim scope, architecture and sufficient local acceptance criteria. `ACCEPT_FOR_IMPLEMENTATION` permits implementation of the agreed design; it neither establishes closure of technical blockers nor permits the full pilot before the next gate. Numerical engineering policies may remain pending if their mandatory freeze before measured runs is explicit.

| Design criterion | Required outcome | Status in this document |
|---|---|---|
| G1 scientificclaims | Evidence review distinguishes resource sensitivity from hardware emulation and identifies supported/unsupported claims | Rationale and independent materials available; final verdict belongs to the second methodology review |
| G7 scoped_design_acceptance | No unresolved design P1 issues for agreed claims; G2–G6 implementation conditions explicit; transition recorded as `ACCEPT_FOR_IMPLEMENTATION`/`REVISE`/`BLOCKED` | Second review decision pending |

### VERIFIED_FOR_MEASUREMENT

This separate gate is established **after implementation** and local checks; it does not replace the literature evidence review. No full pilot before this gate.

| Gate | Evidence to produce after implementation | Current state |
|---|---|---|
| G2 workloadpaths | Actual input schemas/hashes; **five selected pilot configurations** with full calibration/score/state/event parity; score tolerance cannot change crossings/states/events. The 66-model check is optional for broader claims | Not completed |
| G3 arrival/clock | Producer/detector cgroup IDs; clock/time-namespace evidence; known-delay/backlog sanity case; consistent accepted_ingress_available boundary/timestamps; primary event-ready minus mapped onset unchanged | Not completed |
| G4 boundedinstrumentation | Detector storage growth not proportional to run length; queue/drop counters; external-collector completeness; overhead and lifecycle memory | Not completed |
| G5 failurejournal | Tested startup failure, controlled failure/timeout and incomplete attempts; inspect/counters preserved before cleanup; no silent exclusion. Slow-detector queue overflow not excluded as source-invalid | Not completed |
| G6 freeze | Image/code/input/adapter hashes, authoritative 60-pair manifest; **numerical** capacity/drop/backpressure/timeout/source-validity/evidence-loss policies, boundary and actual thread pools | Final freeze pending |

G3–G5 may first be tested with small synthetic infrastructure cases without scientific attack claims. These neither replace the 3.4 h pilot nor select a winner from observed performance. “It works because the container exits” is insufficient.

## 7. Recommendation for the first article

Choose A while retaining the agreed 60-trial scope and endpoint limits. Frame conclusions around the software pipeline on the tested platform under declared quotas. Valid outcomes include no behavior change at 1 Hz under some limits, failure of some configurations, or insufficient functional evidence for any configuration. Do not artificially degrade profiles to obtain a desired curve.

Sequence: **proposal → critical review → literature verification → reassessment → DESIGN_ACCEPTED_FOR_IMPLEMENTATION → implementation, local integration checks and freeze → VERIFIED_FOR_MEASUREMENT → full pilot**. This document is not evidence that any gate has passed. All previous outputs/claims remain unchanged.
