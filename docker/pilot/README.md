# Docker development pilot v1

This is an environment-specific CPU/RAM sensitivity experiment on the declared Mac Docker Desktop Linux ARM64 VM. It does not emulate a validated UAV processor. Five frozen development configurations × four profiles × three chronological recordings × one technical trial = 60 sequential attempts. ML fits remain future-informed development fits. No independent validation or generalization claim follows.

## Reproduce

For a new checkout with a rebuilt dependency parent, use the [portable entry point and input packaging](../../docs/REPRODUCIBILITY.md#docker-pilot-on-a-mac-with-arm64-docker). The commands below describe the original trusted local-parent workflow.

Run from repository root with Docker available and the trusted frozen input workspace (raw/model redistribution rights remain unresolved):

```sh
python3 scripts/run_docker_pilot.py build
python3 scripts/run_docker_pilot.py preflight --run-root docker/artifacts/pilot-v1/NEW_RUN --input-root /absolute/frozen/workspace
python3 scripts/run_docker_pilot.py freeze --run-root docker/artifacts/pilot-v1/NEW_RUN --input-root /absolute/frozen/workspace
python3 scripts/run_docker_pilot.py run --run-root docker/artifacts/pilot-v1/NEW_RUN --input-root /absolute/frozen/workspace
```

Do not reuse an existing root with changed code, policies, inputs or image. The cached dependency parent image is checked by immutable ID. The offline image build copies current implementation and binds its source hash. The controller verifies actual image source bytes and all 75 trusted input hashes before model loading. See `Dockerfile`, `compose.yaml`, `policy.json`, `../../docs/review/PILOT_SCOPE.json` and the measurement gate record.

## Container parameters and boundaries

Detector profiles: guarded reference has no CPU quota and 1536 MiB; controlled CPU quotas are 100000, 50000 and 25000 microseconds per 100000 microsecond period, each with 512 MiB. Equal memory-swap limits disable swap. Driver/source/external collector is a separate container with 512 MiB and no CPU quota; it is outside the detector budget. Whole-pipeline RAM must include both processes. All numerical factors are author-defined, not operational standards. Both containers use network none, read-only roots, dropped capabilities, 128 PID limit and a 64 MiB /tmp; math library thread limits are one. A native Linux named volume carries sockets. Driver host cgroup namespace permits read-only monitoring without privileged mode or Docker socket exposure.

Original-rate replay uses unchanged timestamp order. Independent source attempts, ingress acceptance, send completion, queue, inference and event-ready timings are separate. Primary delay is execution event-ready time minus mapped annotated onset; no physical receiver/FC path is measured. Source lateness limits are P95 100 ms and maximum 250 ms. Application ingress holds 16 messages with drop-new failure accounting; kernel socket buffering is separately bounded/recorded, so total backlog is not claimed to be 16. Synthetic preflight overload uses capacity two, 160 messages and injected 80 ms processing; measured runs inject no delay.

External cgroup monitoring samples every 100 ms. Sampled memory maxima are not kernel peak guarantees; unavailable memory.peak is null. Lifecycle/cpu throttling, clock identity/pings, actual quota/memory/swap, exits/OOM counters, source completeness and failure evidence are saved. Missing evidence never passes. No detector watchdog semantics are added.

## Outputs and recovery

`run_status.json` carries heartbeat/current trial; `attempts.ndjson` is flushed before each create. Each trial retains effective Compose, inspect/logs, source and detector traces, external counters, summary and attempt result before cleanup. Failed attempts remain visible. Completed recorded attempts are not silently repeated; incomplete trial directories require adjudication. No unrelated containers are stopped. Run minimum is 12080.50 seconds plus startup/cleanup overhead. Foreground public commands need an explicit Mac `caffeinate -i` wrapper, as shown in the reproduction guide. The historical background launch uses a job-scoped idle-sleep inhibitor, without changing persistent settings.

Actual gate: `docs/review/PILOT_MEASUREMENT_GATE_20261026.json`; frozen manifest and detailed evidence are ignored local artifacts under `docker/artifacts/pilot-v1/run_20261026_r3`. All scientific evidence remains INSUFFICIENT EVIDENCE.

## Post-pilot lifecycle correction (2026-10-27)

The completed historical run has60complete recording workloads,55exit-zero processes and5abnormal/cleanup-affected exits. See `docs/review/PILOT_EXIT_AUDIT_20261027.md`. The host controller now waits for natural detector exit before any cleanup signal and records pre-cleanup states and intervention. This changes the code fingerprint; build/preflight/freeze a new run before any new measurements. Historical statuses remain unchanged.
