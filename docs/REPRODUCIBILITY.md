# Reproduction and reconstruction

Use a repository checkout, not a wheel-only installation. Keep an untouched copy of archived outputs: the scientific pipeline writes to `data/`, `experiments/` and `results/` within its checkout. Never run another benchmark while the active pilot is measuring.

## 1. Inspect the supplied archive

No data, packages, network or model loading are needed for these standard-library checks:

```sh
python3 scripts/verify_release.py
python3 scripts/render_archived_report.py --output build/archived-report.md
```

The compact report is reconstructed from `results/summary.json`, `raw_counts.csv` and `realtime_metrics.csv`; it includes their SHA256. This does not regenerate all historical tables/figures. Archived figures remain in `results/figures/`. The manifest verifies publication-snapshot bytes, not scientific validity or agreement with a new machine's timing.

## 2. Obtain development data

Source repository and pinned revision:

```sh
git clone https://github.com/mrtckr05/Addressing-Data-Leakage-in-UAV-Cyberattack-Detection-A-Realistic-Machine-Learning-Benchmark.git ../gnss-source
git -C ../gnss-source checkout 12b2bff3bf1192cc9348e748bf1d910e2bd2e891
```

Review upstream terms before acquiring or redistributing data. Raw data are not bundled. The source attributes its original recordings to the UAV Attack Dataset; these names do not establish two independent sources. `configs/sessions.json` specifies exact paths and SHA256. Preparation rejects mismatches and physically invalid fractional satellite counts.

## 3. Recompute development models, tables and figures

In a separate checkout of this repository:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
cp configs/local_paths.example.json configs/local_paths.json
```

Record the actual interpreter and exact installed dependency versions before recomputing; do not reuse the archived machine description:

```sh
.venv/bin/python scripts/record_environment.py --output experiments/environment.json --replace
```

Edit `source_root` in the local JSON to the **absolute** path of `../gnss-source`; `legacy_root` is optional forensic context and unused by the normal pipeline. Then run:

```sh
.venv/bin/python scripts/prepare_data.py
.venv/bin/python scripts/train_candidates.py
.venv/bin/python scripts/replay_evaluate.py
.venv/bin/python scripts/benchmark_resources.py --full-passes 1 --stress-messages 300
.venv/bin/python scripts/replay_evaluate.py --realtime
.venv/bin/python scripts/summarize_results.py
.venv/bin/python scripts/verify_results.py
```

Or use `scripts/run_all.py` for the ordered full sequence. Native original-rate replay covers two rules × three sessions and takes roughly 20 minutes plus fitting/benchmark overhead. The configured other candidates have diagnostic/resource results, not equivalent operational replay. A recomputation can change timing, environment provenance and figures; identical numerical hardware timings are not promised. Fresh installation/full rerun was not performed during publication cleanup.

Tests in the configured environment:

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_igaspin_*.py' -v
```

## Docker pilot on a Mac with ARM64 Docker

This protocol describes the tested Mac/Linux-VM architecture. It is not a cross-platform or target-UAV equivalence claim. Run the following only after any other benchmark finishes.

First record the actual environment and prepare/train the trusted development checkout as above. Make an immutable input copy; the script reads files as bytes and never unpickles arbitrary input:

```sh
.venv/bin/python scripts/package_pilot_inputs.py --destination build/pilot-inputs-NEW
```

This creates `build/pilot-inputs-NEW/workspace` plus its sibling `frozen_run_protocol.json`, with hashes for configs, prepared data, environment, source, lock and models. It is a **new** development snapshot, not a substitution for historical model bytes.

Build the dependency parent from the pinned Dockerfile and explicitly record the image ID:

```sh
docker build --platform linux/arm64 -t nulp-gnss:limits-v1 -f docker/image/Dockerfile docker/image
export GNSS_PARENT_IMAGE_ID="$(docker image inspect --format '{{.Id}}' nulp-gnss:limits-v1)"
python3 scripts/run_portable_pilot.py build
python3 scripts/run_portable_pilot.py preflight --run-root docker/artifacts/pilot-v1/NEW_RUN --input-root build/pilot-inputs-NEW/workspace
python3 scripts/run_portable_pilot.py freeze --run-root docker/artifacts/pilot-v1/NEW_RUN --input-root build/pilot-inputs-NEW/workspace
caffeinate -i python3 scripts/run_portable_pilot.py run --run-root docker/artifacts/pilot-v1/NEW_RUN --input-root build/pilot-inputs-NEW/workspace
```

The public wrapper explicitly pins the inspected local parent and includes itself in the frozen source hashes. The host still verifies actual parent identity, image source bytes, labels, input hashes, clock/cgroup isolation and preflight proofs. Use the same environment pin and entry point for every stage. A changed pin/image/source/input requires a new run root and preflight. Do not replace the historical parent pin or overwrite an existing manifest to make an old run appear reproducible. The portable wrapper/input packager have structural/fixture checks; a full new-platform Docker experiment has not been run during packaging.

The [Compose file](../docker/pilot/compose.yaml), [policy](../docker/pilot/policy.json) and [scope](review/PILOT_SCOPE.json) define five configurations, four profiles, three recordings and their fixed order. The measured repeat uses the original entry point and its original frozen inputs. New development training can change serialized bytes/results even with the same library.

Allow at least 3 hours 21 minutes for recording playback, plus container startup/cleanup (the first complete pilot took about 3 hours 28 minutes). `run_status.json` records progress; `attempts.ndjson` and each trial directory preserve failures, traces and actual limits. No automatic silent rerun of an incomplete trial is allowed. For a completed run:

```sh
python3 scripts/audit_pilot_completion.py --run-root docker/artifacts/pilot-v1/NEW_RUN --output build/NEW_RUN-audit
```

The workload-integrity audit is separate from shutdown/exit status and scientific conclusions. The publication snapshot contains no raw Docker trace bundle or fitted model weights. Exact historical Docker reconstruction requires the retained trusted model/input/image artifacts; rebuilding elsewhere is a new measurement.

## Final article archives and IGASPIN

```sh
python3 scripts/reconstruct_final_results.py --output build/final-results.md
python3 results/article_selection/reproduce_selection.py
```

The first command reconciles 80/79 IGASPIN trial counts and message totals and renders the resource ranges and event summary. The second reconstructs the descriptive development selection from 20 baseline vectors. Both are data-free aggregate reconstruction, not fresh inference or trace validation.

For separately obtained IGASPIN UBXfiles:

```sh
python3 scripts/prepare_igaspin_inputs.py --raw-root /path/to/records --output build/igaspin-inputs-NEW
```

This verifies exact raw hashes, checks NAV/RF wire order and prepares four private ordinal streams. It is offline preprocessing, outside the measured latency boundary. No model is loaded. [Adapter details](../validation/igaspin/README.md) and [resource Compose](../docker/igaspin/README.md) state supported operations and required excluded artifacts. The original machine-specific 80-run controller is not packaged as a turnkey historical rerun. Existing aggregate reports can be inspected immediately; an exact historical rerun additionally requires the retained trusted data/model/image/trace bundle. A new hardware run requires a fresh reviewed preflight and freeze.

The separate development technical-repeat archives now include one complete 60-trial pass with 59 source-valid records and 19 complete paired groups. The later partial pass and unexecuted third repeat are not promoted to full passes. No additional resource workload was launched to prepare this release.

## Completed Docker pilot results

The corrected repeat completed all 60 attempts. See [the report and tables](../results/docker_pilot_repeat_20261027/README.md). To rebuild its compact report from shipped CSV/JSON tables without raw data or model execution:

```sh
python3 scripts/reconstruct_pilot_report.py --archive results/docker_pilot_repeat_20261027 --output build/NEW_DOCKER_REPORT
# Add --figures in the pinned scientific environment to regenerate all four figures.
```

The report reconstruction is a rendering of archived evidence; it does not newly verify raw traces. For full raw-trace re-analysis, obtain the retained original run bundle and trusted frozen input workspace, then run:

```sh
python3 scripts/analyze_docker_pilot.py --run-root /path/to/completed-run --output build/NEW_DOCKER_ANALYSIS --figures
```

This command verifies input hashes, exact sequences, actual clock/cgroup identities and limits, and numerical latency quantiles; it reconstructs the continuous-time waiting queue without modifying trial artifacts. The accompanying provenance records source hashes. A one-message transient waiting maximum is distinct from the original zero-valued post-processing-start observation. The descriptive Pareto comparison stays within each enforced profile; native Mac latency/model-size budgets are not transferred.
