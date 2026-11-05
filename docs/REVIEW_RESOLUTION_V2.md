# Review resolution — protocol v2

Archive note: references to inventory, backups, legacy recovery and `history/` describe the preserved local research archive; those private or duplicate files are intentionally omitted from the publication snapshot. Public state is a concise derivative. See [reproduction boundaries](REPRODUCIBILITY.md).

Original review: 2026-10-25; original run commits `7dd51da`, `a0b6d0b`. V1 artifacts remain under `history/v1_shared_run/` with their original manifest and hashes. The corrected interpretation is in `ERRATUM_V1.md`.

| Review finding | Resolution | Evidence / remaining limit |
|---|---|---|
| Resource P95 used only benign prefix | Measure each complete configuration over all three chronological sessions; retain condition/calibration quantiles | `resources.csv`, `resources_by_condition.csv`, `resource_calibration.csv`: 378 configurations × 610 rows; no independent recovery ground truth |
| Shared workload confounded configuration latency | Fresh detector process and independent producer per configuration/session; sequential pairs | Six complete journal records for two primary rules, all three sessions; other 376 NOT EVALUATED operationally |
| Manifest contradicted execution | New versioned manifest describes isolated subset; historical manifest preserved with erratum | `configs/experiment.json`, `realtime_runs.jsonl` |
| Stress source could be delayed by inference | Independent process, readiness handshake, scheduled/arrival clocks, offered-rate validity and two deadline measures | Ten short 300-message trials met frozen offered-rate criteria; RF at 1000/s shows actual queued backlog 248 and300 misses; no sustained-capacity claim |
| Report narrative retained hardcoded outcomes | Generate counts, primary list, delay, exposures and stress figures from tables | Report consistency checked against trigger/stress tables; historical 5.982160 s explicitly marked historical |
| Pareto delay took first session | Worst eligible-episode delay, infinity for missed/readiness-failed episodes | Session-order and missed-episode fixture tests; current evidence still one episode |
| GNSS dropout could be excluded as incomplete record | Support independent `recording_end_us` coverage | Regression test keeps eligible episode after GNSS loss; absent independent coverage, fallback is explicitly last GNSS sample |
| Resume omitted detector-core hash | Include core/replay, dependency lock, recorded environment, data/config/model hashes | Every completed record includes them; acceptance verifies current hashes |

Validation covered isolated replay, resource protocols and stress, scenario/report regression checks, artifact hashes and consistency of the resulting tables. The final integrated test run passed 28 tests; see `experiments/test_run.json`. No claim is made that unit tests validate statistical generalization.

The two execution-clock observations differ partly because the producer was scheduled later in one trial. `triggering_message_timing.csv` exposes this component: measured end-to-end delay is not an intrinsic algorithm-cost ranking. The isolated resource benchmark is a separate recorded workload and should remain separately labelled.

Independent validation is still unavailable. ML remains in-sample/future-informed; rule and measured-subset selection used development evidence. Every evidence status remains INSUFFICIENT EVIDENCE. Only the stated finite workload/platform/library has been exercised. No remote was created or publication performed.
