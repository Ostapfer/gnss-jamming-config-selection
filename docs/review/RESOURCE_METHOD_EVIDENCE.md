# Research: rationale for the resource-constrained experiment

Date: 26 October 2026. Reviewed commit 932ced3, Docker Compose, the probe and existing replay. This is an evidence review and protocol proposal; runtime was unchanged and no containers or models were run.

## Conclusion

The idea is scientifically justified as a **controlled sensitivity analysis of frozen detector configurations under CPU/RAM limits in a specified Linux ARM64 environment**. The prepared smoke check establishes only that part of the software path executes. It does not yet establish reproducibility of full constrained replay, suitability of all 66 models or timely detection. The 0.25/0.5/1 CPU and 256/512/1024 MiB grid contains author-defined experimental factors, not an identified industry standard or emulated SBCs.

## Primary sources and supported interpretations

| Source | What it establishes | Application here |
|---|---|---|
| [Linux cgroupv2](https://docs.kernel.org/admin-guide/cgroup-v2.html), CPU Interface Files / Memory Interface Files | `cpu.max` specifies CPU time per period; `cpu.stat` contains utilization/throttling; `memory.events` records memory pressure/OOM. Cgroup accounting covers more than an individual model's RSS | Log actual limits and counter deltas. Limits do not reduce processor frequency. Check newer documentation fields against actual kernel 5.15; do not replace unavailable values with zero |
| [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/), CPU / Memory / memory-swap | Container CPU and memory limits enforce real constraints; equal memory and memory-swap limits disable swap | Verify actual cgroups; retain exit/OOM evidence before cleanup. The memory limit covers the software container, not just the serialized model |
| [Docker Desktop settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/), Resources / Advanced | The Docker VM has its own CPU and RAM limits | Record VM limits and neighboring workloads. Compare with a Linux reference in the same VM/image; native Mac results are not a matched baseline. This is a methodological consequence of the layered environment |
| [Google Benchmark guide](https://github.com/google/benchmark/blob/main/docs/user_guide.md), Random Interleaving / Timing and Repetition Control | Repetition and random interleaving help reduce effects of changing system state | Freeze configuration/profile block order through a seed and manifest. The guide does not establish exactly 3 or 10 repetitions as universally sufficient |
| [Sormayli et al., Scientific Reports 2025](https://www.nature.com/articles/s41598-025-10567-0), Implementation and comparison / Table 6 | The authors assess detector deployment on STM32H743 using FLASH/RAM/execution time | Supports separate evaluation of computational resources. Their 20 microseconds is an implementation-specific output-time measure, not our confirmed RF-on delay or proof of our requirements |
| [ACM SenSys2024 Artifact Evaluation](https://sensys.acm.org/2024/art/), Preparation guidelines | An artifact should describe hardware/software requirements and provide a minimal working example; evaluation is tied to claims | Compose/image IDs/hash manifest/smoke checks are preparation artifacts. A smoke check does not reproduce the article's main results; no ACM badge is claimed |

No separate publication establishing our particular 256 MiB or 0.25 CPU as onboard requirements was identified. Spoofing RF/IQ papers do not make constrained telemetry timing independently validated GNSS generalization.

## Controls and experimental factors

**Controls:** unchanged models/thresholds/state machine; identical image and math-library thread count; fresh detector process; cadence and dataset hashes; observation window; swap policy; CPU period; identical logging. Warmup occurs outside the measured attack session or reproduces the declared startup/calibration; do not warm a model using future attack rows.

**Experimental factors:** quota and memory cap; original-rate and stress workloads evaluated separately. Do not combine them in one operational claim. Freeze the 100 ms period as a scheduler parameter; quota effects may be uneven over time rather than a constant inference-latency multiplier.

**Observed outcomes:** startup success, OOM/exit failures, readiness, queue/backlog, P50/P95/P99 for an explicitly named distribution, confirmed event-ready delay, false events/active duration, CPU-throttling deltas, cgroup memory and RSS. Resource-only PASS differs from functional/empirical PASS. Low demand at 1 Hz may not activate throttling even at 0.25 CPU; no observed effect is a valid result.

## What preparation has not yet measured

- `docker/image/probe.py:23–27` reads `memory.current` and `memory.events` **before** model loading and numeric-stack imports at lines 45–48. Approximately 17 MiB cannot be called peak Python-detector RAM.
- Five zero-vector predictions do not verify all 66 models, calibration, transitions or the I/O/replay path. Actual cgroup verification is useful, but CPU throttling under workload has not been checked.
- The probe does not test memory-pressure/OOM behavior; successful exit at 512 MiB does not establish that 256 MiB or another candidate will work.
- `src/gnss_jamming/replay.py` starts the producer within the detector process tree. In one constrained container it inherits the same resource domain. Do not accept this unchanged replay as an independent arrival workload.
- A producer outside the detector cgroup is necessary but does not guarantee sufficient CPU from the VM. Verify actual offered rate/lateness, clock domain/mapping and scheduler contention.

## Minimum sufficient next program — a proposal, not an executed protocol

1. **Admission:** check all 66 models and the complete Runner pipeline in the same Linux image on trusted development inputs; distinguish cold startup from calibrated processing. Verify prediction/state parity against the reference under a predefined numerical tolerance, not merely finite predictions. Preserve read-only input/model/image hashes.
2. **Reference:** fresh process/container; the same 1536 MiB ceiling and no container CPU quota form a guarded reference, not a physically unrestricted host. Run all 378 configurations for processing/resource coverage. Log memory after imports, model loading, calibration and during workloads; record peak if supported by the kernel, otherwise disclose sampling limitations. Cgroup usage is not isolated model RAM.
3. **Small end-to-end pilot:** previously selected RULE_noise_t2, DT_f3_p2, SVM_f3_p2, KNN_f3_p1 and RF_f3_p3 with exact thresholds/confirmation in a new manifest. Selection is already development-informed, not independent. All nine profiles plus reference, three initial technical trials in seeded randomized block order: an exploratory plan, not statistical justification of detection reliability. Only this subset is evaluated, not all 378 configurations.
4. **Independent arrival:** establish source/receiver clock mapping before measurement and separate producer/detector cgroups. Prefer the same Linux VM with a verified shared monotonic clock; check separate time namespaces/offsets. Never directly subtract native Mac and Linux `perf_counter`. Use one defined message-arrival boundary and due/enqueued/received/start/ready timestamps. Declare I/O transport. Backpressure must not silently slow the source; retain scheduled and actual offered rates. Missing messages, sequence gaps and queue saturation are separate outcomes.
5. **Original-rate and stress:** the former preserves cadence/order/30 s calibration and establishes event delay; the latter studies throughput/backlog, not a new operational detection rate. Do not select rates post hoc to force failure; report no deficit if none occurs.
6. **Failure denominator:** define eligible pairs/trials in advance. Keep startup/OOM/readiness failures in accounting; an in-scope eligible episode without a confirmed alarm is a failure. An infrastructure-invalid source workload is protocol-invalid with a reason, not silently dropped. Preserve inspection before cleanup. Timeout and exit 137 alone do not prove OOM; OOM/state/counter evidence is required.
7. **Frozen expansion:** extend end-to-end coverage to remaining configurations only under a predefined plan. Repetitions are technical: repeated containers do not turn one jamming session into many independent episodes. Detection evidence remains insufficient for generalization claims.

Before approving such a pilot, calculate the actual elapsed-time budget from recording durations. Five configurations × 10 profiles × three technical trials × approximately 10 minutes across three recordings already gives approximately 25 hours of original-rate replay before startup; a full 378 × 9 matrix is much longer. **Infrastructure checking alone** can use a separately labelled integration run of two candidates chosen in advance as complexity extremes (a threshold rule and RF), reference plus one restricted profile, on one recording. This neither selects a Pareto winner nor substitutes for the measurement program. Declare both subset manifests before new outcome comparisons. Do not run the entire matrix concurrently to shorten elapsed time.

## Permitted contribution wording

A reproducible procedure is proposed for checking GNSS-detector configuration feasibility under simultaneous timing, false-alarm and resource constraints. CPU/RAM profiles form a declared sensitivity grid for a specified software/hardware environment. Readiness, resource and functional outcomes are separated; startup and memory failures are also retained. The method promises neither a single winner, universal minimality nor suitability of an untested SBC.

**Research verdict:** proceed after workload/clock/failure instrumentation is complete. “Docker is ready for smoke checks and preparation” is supported; “the complete constrained experiment is ready” is not yet supported.
