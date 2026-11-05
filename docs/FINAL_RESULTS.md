# Final article results

## Scientific scope

The contribution is a procedure for filtering complete detector configurations by functional requirements and then resource budgets, followed by Pareto comparison within the remaining finite library. It does not identify a universal best model or a universally minimal device. A threshold rule can be an acceptable alternative when the declared deadline permits it.

## Development experiments

The library contains 60 fitted ML models across 4 algorithms, 5 feature sets and 3 predefined profiles, expanded into 360 ML configurations by thresholds and confirmation rules; 18 rule configurations bring the finite library to 378. Only five fixed variants were selected for the Docker resource pilot.

The development baseline completed 60 trials. The separate complete technical repeat also completed 60, but 59 met the declared source-schedule gate. The paired timing comparison uses 59 records and 19 complete configuration/profile combinations; it does not claim three complete repeat passes. Both use development-fitted models on the same attack episode. The archived selection example is therefore descriptive and in-sample.

## IGASPIN resource experiment

Two static recordings × two ordinal RF positions × five fixed variants × four resource profiles produced 80 trials. All completed, with 29,600 messages, 0 drops, 0 OOM and complete traces. Trial 017 (DT/R1/jamming/ordinal 1) had maximum source lateness 341.331634 ms against a 250 ms gate. Retained timing evidence therefore contains 79 valid trials and 29,238 messages. A prospectively accepted continuation supervisor finished 018–080 without retrying 017.

All 20 configuration/recording/arm groups produced identical scores, threshold crossings, states and information-clock events across profiles. Execution-ready timestamps were compared separately, not required to be identical. Source-invalid 017 is included only in semantic parity, not timing comparisons.

Whole-stream RF processing P95 ranges are 33.623300–35.724209 ms at 1 CPU and 79.030975–96.539957 ms at 0.25 CPU. Each range spans four separate streams, not independent recordings or a confidence interval. The sampled detector cgroup peak range across 79 valid trials is 46.355469–107.679688 MiB. More frequent traffic and memory budgets below 512 MiB were not tested.

## Conditional event interpretation

The five resource variants are a subset of the separate 98-configuration offline diagnostic per RF position. Do not transfer the diagnostic 23/98 later-event result to all five resource variants.

DT produced a new post-reference event in all 7 valid jamming trials: information delay 10.999723103 s; execution-ready delay 11.002824–11.014832 s; arrival/execution overhead 3.100552–15.108553 ms. The information already needed for confirmation arrived beyond the conditional 10 s deadline; software overhead is not the main second-scale difference.

RULE, KNN, SVM and RF produced no fresh event after the reference through the end of the recording. SVM ordinal 0 has a carry-in alarm in all 4 profiles. No fresh event was ready within conditional 10 s in the 39 valid replays of the jamming recording. These are repeated executions of one recording, not 39 independent attacks.

The reference 2023-12-07T12:08:21Z is supplied timing with unverified physical onset/uncertainty and end. Physical deadline performance and operational FAR remain NOT EVALUABLE. The expected-clean recording is not independently verified as operational benign exposure.

## Measurement boundary

Prepared NAV-trigger availability → availability checks and normalization → inference → event-state update → event-ready. UBX framing/decoding and wire-order RF/NAV projection occur offline. The unmeasured receiver/flight-controller transport is excluded. The environment is Apple M2/Linux ARM64 Docker Desktop; target-UAV hardware equivalence was not established.

## Inspect evidence

Run `python3 scripts/reconstruct_final_results.py` for data-free aggregate reconciliation. Detailed files are under `results/igaspin_resource_20261105/`, `results/development_repeat_20261104/` and `results/article_selection/`. The supplied hashes bind release bytes and historical provenance references; they do not provide access to excluded input files or prove licence rights.
