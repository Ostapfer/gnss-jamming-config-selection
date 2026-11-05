# Audit of five abnormal exits in the Docker pilot

## Finding

All 60 attempts contain complete workloads: exact message/result sequences, final/complete markers after the last row, successful readiness, a valid source schedule, no missing messages and no driver errors. Fifty-five processes exited with code 0 and five with code 137. Original statuses and raw artifacts remain unchanged. A separate check of saved artifacts confirmed the integrity of all five affected recordings.

| Trial | Detector | Recording | Rows | Profile |
|---|---|---|---:|---|
|002|DT|benign|248|0.25 CPU /512 MiB|
|008|RF|spoofing|138|0.25 CPU /512 MiB|
|009|KNN|jamming|224|0.25 CPU /512 MiB|
|023|RF|benign|248|0.25 CPU /512 MiB|
|024|DT|spoofing|138|0.25 CPU /512 MiB|

## Cause and limits of attribution

The historical controller waited only for the driver. If the detector remained alive after collection finished, the controller called docker stop with a 1 s grace period and then classified any nonzero exit as DETECTOR_EXIT_FAILURE. This conflated workload outcomes with cleanup intervention. In all five cases, driver exit 0 preceded detector exit 137; complete had already been received, stderr was empty and no host timeout/error was recorded. OOMKilled=false and recorded memory.events.oom/oom_kill were zero. These observations do not establish OOM or an inability to process the stream at 0.25 CPU.

The exact signal and its sender were not journaled in the original run. Querying historical Docker events returned zero events, so the exact cause of SIGKILL cannot be reconstructed. The strongest defensible status is WORKLOAD_COMPLETE + ABNORMAL_OR_CLEANUP_AFFECTED_EXIT. Cleanup as the cause is strongly supported, but is not proved for every historical attempt.

Two separate synthetic engineering tests used the same frozen image: the original cleanup path exited with code 0 on this occasion; with passive waiting, the still-running detector naturally exited with code 0 after 1.5663 s. This demonstrates a need for shutdown grace longer than 1 s, but does not exactly reproduce historical exit 137. These tests do not enter the scientific sample.

## Permitted use

Recording-window detection, false-alarm and inference/processing/queue/event-ready metrics may be analyzed for all 60 attempts in an additional adjudicated layer, with an explicit caveat about the five abnormal exits and unchanged original statuses. This is not 60/60 successful lifecycles. RAM/CPU metrics cover the actually observed interval before the driver monitor stopped; 100 ms sampled maxima are not kernel peaks or guarantees of complete shutdown coverage. Independent validation is absent; the statistical status remains INSUFFICIENT EVIDENCE.

## Correction for subsequent runs

The controller now gives the detector a separate bounded natural-exit wait (shutdown_grace_s, falling back to completion_grace_s=30 s), saves the pre-cleanup state and journals forced-stop requests and results. Workload status, shutdown observation and cleanup intervention are recorded separately. Exceeding shutdown grace has a distinct DETECTOR_SHUTDOWN_TIMEOUT status; genuine OOM and midstream exits are not concealed. Ten transport/lifecycle regression tests PASS. A separate integration test of the corrected controller on the frozen image completed with COMPLETE, natural exit 0 after 1.4325 s and cleanup_intervened=false. The new controller requires a new build/preflight/freeze before further measurements; do not resume an old manifest with changed code. No 60-trial repeat was launched as part of this audit.

## Reproduce the audit

```sh
python3 scripts/audit_pilot_completion.py --run-root docker/artifacts/pilot-v1/run_20261026_r3 --output results/NEW_EXIT_AUDIT
```

Machine-readable report: results/pilot_exit_audit_20261027/audit.json; table: trials.csv. The report includes SHA256 values for primary artifacts and separate checks for each attempt. Raw diagnostics remain ignored under docker/artifacts/pilot-v1/exit_diagnostics_20261027*. The original controller can be recovered from Git commit 4f08de6 and is also preserved beside the local artifacts.
