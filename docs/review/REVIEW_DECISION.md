# Rationale and agreed next stage

26 October 2026. The selected option is “Pilot approximately 3.4 hours (recommended).” This is a scope decision after preparation fixes; no measured pilot was launched during this review.

## Scientific rationale

Investigate whether a frozen detector configuration retains declared properties under actual limits on available CPU and total container memory. This is a controlled sensitivity experiment in a specified Linux ARM64 environment, not SBC emulation or proof of a universal resource minimum. Distinguish startup/readiness, message processing, execution-clock confirmed delay and resource-only feasibility. Rules/DT may be sufficient; no bottleneck at 1 Hz is a valid outcome.

Sources support the constraint mechanisms and reproducible measurement, but **do not establish our numerical profiles as a standard**. See RESOURCE_METHOD_EVIDENCE.md and resource_method_sources.json. All nine profiles remain a documented planned grid; the first pilot does not cover it completely.

## Agreed pilot scope

- Five previously specified development-informed configurations: `RULE_noise_t2_d0.5_c2`, `DT_f3_p2_d0.5_c2`, `KNN_f3_p1_d0.5_c2`, `SVM_f3_p2_d0_c2`, `RF_f3_p3_d0.5_c2`. These are representatives, not independently selected winners or the whole 378-configuration library.
- Four profiles: guarded reference without a container CPU quota and with 1536 MiB; 1 CPU/512 MiB; 0.5 CPU/512 MiB; 0.25 CPU/512 MiB. A 100 ms period, swap disabled and one math-library thread for all.
- Comparing three quotas at the same 512 MiB supports investigation of the CPU factor. The reference has a different RAM limit, so its contrast with restricted profiles does not establish a separate causal CPU effect. The 256/1024 MiB RAM factor belongs to a later stage.
- Three unchanged development recordings and one technical trial per combination: 60 configuration/profile/session pairs. A fresh detector container per trial, sequential execution; record seed-42 order before launch.
- The three recording durations total 604.024883 s; 20 configuration/profile combinations give 12080.49766 s, approximately 3.356 h, excluding startup/validation/cleanup. This is a planning lower bound, not a completion-time promise.
- ML models were fitted using later rows from the same development episodes. The pilot can investigate execution/resource effects on frozen inputs, but its detection results are not independent validation. Statistical evidence remains insufficient. One trial does not establish repeatability or latency tails across many independent runs.

## Three mandatory corrections before launch

1. **Complete workload and paths.** The measured Runner must explicitly receive the actual read-only input root; checking must exercise real calibration, prediction, state machine and events. The current probe bypasses Runner and did not verify the mount contract.
2. **Independent source.** Place the producer outside the detector cgroup with a verified clock domain; retain source lateness/actual offered rate/sequence and IPC backpressure in logs. Do not directly subtract Mac/Linux perf_counter values. Define queue/drop policies and workload-validity criteria before measured runs.
3. **Memory and instrumentation.** Use bounded buffers/an external collector; do not accumulate arbitrarily long timing/prediction histories inside the detector budget. Record lifecycle memory, peak/sampling limits, actual thread pools, CPU-throttling deltas, final OOM/exit and each attempt before starting.

The approximately 17 MiB value in the earlier tested_readiness record is a **pre-import snapshot**; it is not runtime RAM and does not justify the limits. The earlier successful smoke result is unchanged, but its interpretation is limited.

## Pilot admission

After implementing corrections: load/prediction parity for all 66 trusted models; a full-pipeline functional check; a synthetic known-delay/backlog case; verified clock/cgroup membership; startup/OOM/timeout/partial-completion journaling; a matched Linux baseline and actual source validity. Freeze the complete trial manifest/image ID/input/adapter/instrumentation hashes only after successful integration. A selected scope is not an already frozen executable protocol.

## Review status

This document records a preparation-stage review and scope decision, not completed constrained measurements.
