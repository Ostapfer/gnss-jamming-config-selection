# Completed IGASPIN resource results

80 completed; 79 source-schedule-valid; 29,600 offered/accepted/processed messages; 0 drops/OOM/nonzero container exits. Trial 017 is retained but timing-invalid. See experiment_manifest.json for the historical freeze identity, resource boundary and accepted continuation.

- trial_metrics.csv: all 80 trial summaries, including 017.
- processing_p95_ranges.csv: 20 configuration/profile rows based on 79 valid trials; DT/R1 contains 3 valid streams, others 4.
- event_results.csv: events and carry-in for each replay; no physical detection label is implied.
- parity.csv: 20 same-stream semantic comparisons across profiles.
- report.json: independent read-only audit summary.

These are aggregate outputs, not receiver observation rows or complete traces. `python3 scripts/reconstruct_final_results.py` reconciles shipped tables without data, models, network or a new experiment. Raw-trace re-audit and exact historical execution additionally require retained trusted artifacts, which are not distributed. Physical onset, FAR, RF semantics and hardware fidelity remain outside the verified claims.
