# Erratum to v1 · 2026-10-25

Archive note: references to inventory, backups, legacy recovery and `history/` describe the preserved local research archive; those private or duplicate files are intentionally omitted from the publication snapshot. Public state is a concise derivative. See [reproduction boundaries](REPRODUCIBILITY.md).

The first development run, git a0b6d0b, is retained under history/v1_shared_run with original hashes and configuration.

1. Its manifest incorrectly said isolated workers. Actual replay used one consumer, 66 candidates and 3 aligned streams. Reported 8.070 s is a shared-workload measurement, not standalone latency.
2. Resource P95 used 100 benign observations; attack-dependent inference and alarm-state paths were not covered. Resulting resource/Pareto classifications remain historical diagnostics only.
3. Its nominal 1000 Hz stress source could be delayed by inference. RF producer lateness P95 reached 535 ms; queue/backlog metrics do not represent independent sustained 1000 Hz input.
4. Its report generator hardcoded conclusions and could retain stale narrative on rerun.

V2 freezes new boundaries and generates report text from current artifacts. Original outputs are not relabelled as v2. Two causal primary rule configurations receive sequential isolated full original-rate replay; the other 376 configurations have no operational execution-clock evaluation in this run. All 378 retain information-clock development diagnostics and complete per-configuration resource measurements. This explicit scope does not mean unmeasured configurations fail.

No independent attack sessions have been added. All statistical evidence remains INSUFFICIENT EVIDENCE.
