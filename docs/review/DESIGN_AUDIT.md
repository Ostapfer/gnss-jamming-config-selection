# Methodology review: Docker preparation audit

26 October 2026. Reviewed commit `932ced3` and the existing repeated resource run. This is an adversarial review of the code, Compose definitions, protocols and previously saved results. No containers, inference, tests or benchmarks were run. Runtime code was unchanged.

## Verdict

**The image and smoke-readiness checks are correctly prepared within their declared narrow scope. The full resource-constrained experiment is not yet ready to execute without adapting the harness.** Five finite predictions and actual cgroup ceilings establish only that five representatives start under 1 CPU/512 MiB. They do not verify 30 s calibration, full-pipeline latency, long-running memory use, all nine profiles or compliance with a detection deadline.

## Specific findings

| Severity | Location | Issue and consequence | Closure criterion before measurement |
|---|---|---|---|
| P1 — primary timing blocker | `src/gnss_jamming/replay.py:85–87`, `benchmark.py:65–68` | The producer is a child process. Inside a container it inherits the same cgroup quota, so CPU scarcity can reduce the offered workload and conceal queue buildup | Put the producer in a separate cgroup/container; retain its due/arrival/lateness/sequence records. A separate PID alone is insufficient |
| P1 — pipeline execution blocker | `src/gnss_jamming/core.py:6`, `replay.py:11`, `docker/compose.yaml:21–25`, `docker/image/probe.py:38–48` | `ROOT=/opt/research`, while data/models are mounted under `/inputs`. The probe loads pickle files directly and bypasses Runner. Existing Runner/main expects `/opt/research/experiments/models`, configurations and derived data that this mount does not provide | Introduce an explicit configurable input root/adapter for the measured workload; perform an end-to-end functional replay smoke check with the real row schema before making timing claims |
| P1 — memory attribution blocker | `src/gnss_jamming/replay.py:16,36–42`, `benchmark.py:134–135,143–165` | Runner accumulates predictions/timings without bound; the benchmark also retains row dictionaries and all timings. Measurement machinery therefore consumes duration-dependent memory and can cause OOM instead of the deployed detector | Declare the memory scope in advance; use bounded instrumentation/buffers or an external collector and record detector/controller/logging separately. If trace retention remains part of the pipeline, include it honestly in the declared implementation |
| P2 — misleading memory snapshot | `docker/image/probe.py:23–27,42–48` | `memory.current`/`memory.events` are read before importing numpy/sklearn and loading models. The approximately 17 MiB record is a pre-import snapshot, not runtime/model/peak memory | Name the timestamped lifecycle stage; measure post-import, post-load, post-calibration and peak memory; retain external OOM/exit inspection after the run. Do not use this snapshot to justify 256 MiB |
| P2 — queue/clock design pending | `replay.py:74–75,99`, `benchmark.py:51–52,80–90` | A timestamp before `Pipe.send`/`Queue.put` represents sender-side availability. Blocking IPC can stop the schedule; the timestamp alone does not establish receiver arrival. Cross-container/host timestamps have not yet been compared | Freeze the boundary and queue capacity/drop/backpressure policy; retain scheduled_due, before/after send, receiver arrival/start/ready and sequence records; verify the clock domain. Do not assume a shared Linux monotonic clock across macOS host and Linux VM |
| P2 — quota-period/VM confounding | `docker/compose.yaml:15–18`, `docker/profiles.json:4–9` | A 100 ms quota is a ceiling with periodic throttling, not a slower CPU. The four-CPU VM and unrelated workloads can also constrain the reference | Keep the period fixed and declared; record cpu.stat throttling and VM/host workload. Use the same image/VM for the baseline, fresh trials and predefined order/repetitions. Do not describe 0.25 CPU as equivalent to an SBC |
| P2 — failure retention not implemented | `docker/profiles.json:13`, `docker/README.md:34–38` | A startup/OOM/drop policy is described, but the grid controller/journal is absent. The policy therefore does not guarantee that failed measured cases enter the results | Record each attempt before starting; retain timeout, Docker state, exit code/OOMKilled, cgroup memory.events/cpu.stat and completion/partial traces; inspect before removal; do not exclude failed eligible cases |
| P2 — thread fairness requires observation | `docker/image/Dockerfile:2–4`, `probe.py:27` | ENV threads=1 is a specified control, but the smoke check records only ENV, not actual native thread pools after imports. The prior native Mac run is not a Linux baseline with matched thread settings | Record actual thread-pool configuration and library/build versions after import/load; use the same controls for all compared profiles |

Here P1 means a blocker to a **future claim of constrained operational feasibility**, not a rejection of the honestly labelled readiness smoke check. Docker documentation already warns about most major limitations; summarizing it as “everything is ready for the full experiment” would be incorrect.

## Existing strengths

- CPU period/quota, total RAM, disabled swap, read-only inputs, ARM64 and pinned base digest are explicit. `tested_readiness.json` records actual limits/image ID/exit 0/no OOM.
- Original-rate operational replay and accelerated stress are separate; input models were not retrained.
- Actual source files in `docker/image/src/gnss_jamming/*.py` match the current root package files by SHA256. The two source copies have not diverged at this stage, but future changes require a freeze check.
- Nine resource profiles are not presented as completed measurements; the guarded reference is explicitly not an unrestricted physical machine.
- There is no need to “prove” that all models fail: no resource bottleneck at 1 Hz is a valid result.

## Interpretation of the earlier Mac run

It already covered 378 configurations. Repeating three passes means technical repetitions of 610 rows from three recordings, not new independent sessions. The conservative `pipeline_p95_ms` is the maximum of separate condition/calibration P95 values. P50/P99 in the earlier table pool post-calibration observations and must not be described as quantiles of the same distribution as the gate P95. The microbenchmark boundary excludes queue wait/model loading/file I/O/instrumentation append. Busy-loop CPU does not predict utilization at 1 Hz. RSS includes the process, runtime and caches, not intrinsic model RAM. Fifteen changes in 10 ms-budget status between runs show sensitivity of measured feasibility to conditions; selecting only the favorable run would be inappropriate.

## Established decisions and open scope

Previously settled: a finite detector library, 30 s calibration, original-rate primary workload, 3/5/10 s sensitivity deadlines, no universal-best claim, permission for partial external validation, acceptance of a no-bottleneck result, and an exploratory CPU/RAM grid rather than an operational standard.

Facts and routine engineering choices to establish through inspection: IPC transport, actual clock domain, actual cgroup membership/values, input-root adapter, bounded-logging overhead, actual native thread pools, OOM journal, source overload detection and workload counts. These technical facts do not require user preference questions.

Memory/timing boundaries can be specified as routine protocol choices without reopening the research question: a primary streaming detector with 30 s clean calibration and bounded buffers; startup/loading reported separately; all detector-container RAM included; producer/controller outside that budget. Cold-start failure remains deployment-readiness failure rather than an implicitly excluded latency observation. Record these definitions before measurement; the root glossary `CONTEXT.md` records resolved terminology.

The actual open scope is **original-rate execution-clock grid coverage and the number of technical repetitions**, because their product substantially changes campaign duration. A protocol can be proposed without execution: processing/resource screening of the full frozen library; an original-rate subset chosen by a declared metadata/resource-based rule with other configurations honestly labelled NOT_EVALUATED; or a full original-rate grid with explicit duration. Do not call subset selection independent if it already uses prior development results. The CPU/RAM grid, Mac scope and finite-library research question are settled.

## Minimum admission gates for a full run

1. Preserve the old frozen library and outputs; freeze the new workload/protocol version and hashes.
2. Enforce the matched Linux reference and individual profiles; give each trial its own lifecycle and failure journal.
3. Put controller/producer outside the detector quota; establish receiver timing and source scheduling through a synthetic known-delay/backlog sanity case.
4. Pass functional calibration/prediction/state-transition checks on admitted inputs before measurement; do not conceal source-rate slowdown.
5. Declare memory/runtime/instrumentation boundaries; correctly record memory.current stage, peak, throttling and OOM.
6. Define repetitions/order/warmup/failure aggregation and complete reporting; do not choose profiles/repetitions to obtain a preferred winner.
