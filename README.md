# Resource-aware GNSS jamming detector selection

Final article code snapshot **v1.0.1 · 5 November 2026**. Python research code for selecting configurations from a finite detector library using event deadlines, false-alarm events and measured computational resources. A configuration includes its input adapter, features, calibration, fitted model, thresholds, confirmation/recovery rules and execution platform.

## Results included in this version

| Experiment | Completed | Source-schedule-valid | Interpretation |
|---|---:|---:|---|
| Development baseline | 60 | 60 | Five variants × four resource profiles × three recordings |
| Development technical repeat | 60 | 59 | Timing variability on the same inputs; one source-invalid run retained |
| IGASPIN resource extension | 80 | 79 | Five unchanged variants × four profiles × two recordings × two ordinal RF positions |

The IGASPIN extension processed **29,600 messages with no drops or OOM**. Trial 017 is excluded from timing because maximum source lateness exceeded 250 ms. For Random Forest, whole-stream processing P95 ranged from 33.62–35.72 ms at 1 CPU and 79.03–96.54 ms at 0.25 CPU. This is a range of per-run quantiles, not a confidence interval or pooled quantile.

The selected DT variant produced a new event at an information delay of 10.999723103 s from the conditional provider reference; execution added approximately 3–15 ms in seven valid jamming replays. The other four selected variants produced no fresh post-reference event. An SVM alarm already active before the reference is counted separately. These outcomes do not establish physical-onset detection or operational false-alarm rates.

- [Final results and limits](docs/FINAL_RESULTS.md)
- [IGASPIN aggregate tables](results/igaspin_resource_20261105/README.md)
- [Development repeat](results/development_repeat_20261104/README.md)
- [Data-free selection example](results/article_selection/README.md)

## Reconstruct reports without data

Python 3.12 was used for the scientific environment. These commands need only the standard library; they neither download data nor execute models:

```sh
python3 scripts/verify_release.py
python3 scripts/check_publication.py
python3 scripts/reconstruct_final_results.py --output build/final-results.md
python3 results/article_selection/reproduce_selection.py
python3 scripts/reconstruct_pilot_report.py --archive results/docker_pilot_repeat_20261027 --output build/development-baseline
```

Reconstruction checks supplied tables; it does not revalidate withheld raw traces. [Reproduction levels](docs/REPRODUCIBILITY.md) distinguish arithmetic reconstruction, model recomputation and new hardware measurements.

## Obtain data separately

**No datasets, receiver recordings, prepared feature rows, fitted models, provider documents or correspondence are distributed.** Obtain inputs from their original providers under their applicable terms. Repository access and citation do not grant third-party data rights.

| Source | Use | Local integration |
|---|---|---|
| UAV Attack Dataset / pinned benchmark mirror | Three development recordings; two attack recordings also used for fitting | Raw CSV paths and hashes in `configs/sessions.json` |
| IGASPIN ZED-F9P | Static chirp-jamming and separate expected-clean recordings | Byte-exact ordinal adapter and acquisition/hash instructions in `validation/igaspin/` |

See [data acquisition](data/README.md).

## Run the development pipeline

Use a separate checkout to preserve the archived result snapshot. First obtain the pinned upstream recordings described in the data guide.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
cp configs/local_paths.example.json configs/local_paths.json
# Set source_root to the separately obtained upstream checkout.
.venv/bin/python scripts/check_data_inputs.py
.venv/bin/python scripts/record_environment.py --output experiments/environment.json --replace
.venv/bin/python scripts/run_all.py
```

Preparation, fitting and generated outputs remain local and ignored. Rebuilding models can change serialized bytes and timing; it is a new run, not guaranteed reconstruction of historical hardware measurements. The native original-rate path covers two rules across three recordings; the five-variant experiment is the separate Docker pilot.

## Docker profiles actually used

The source/collector and detector are separate containers. The source/collector has 512 MiB outside the detector budget. Swap is disabled and numerical libraries use one thread.

| Profile | CPU quota per 100 ms | Detector memory |
|---|---:|---:|
| R0 guarded reference | Unrestricted | 1536 MiB |
| R1 cpu1_ram512 | 100 ms | 512 MiB |
| R2 cpu05_ram512 | 50 ms | 512 MiB |
| R3 cpu025_ram512 | 25 ms | 512 MiB |

- [Development Compose](docker/pilot/compose.yaml) and [new-run instructions](docs/REPRODUCIBILITY.md#docker-pilot-on-a-mac-with-arm64-docker).
- [IGASPIN Compose](docker/igaspin/compose.yaml), runtime bridge, fixed scope and [measurement boundary](docker/igaspin/README.md).

The IGASPIN measured path starts at availability of a prepared NAV-trigger message. **UBX decoding and RF/NAV association happen offline and are excluded from its timing.** The Compose export replaces a personal bind mount with an explicit environment variable; it is not a new historical freeze or a turnkey 80-run controller. Exact historical reruns require the retained trusted model/input/image/trace bundle. A new resource run requires its own provenance and preflight.

## Evidence boundaries

The development evaluation includes the same attack episode used for fitting. It is not an independent estimate of detection performance. IGASPIN contributes one static jamming recording and one expected-clean recording; ordinal RF positions and resource repetitions do not create independent sessions. Clean conditions, RF epoch/band semantics and physical-onset uncertainty remain unresolved. A Mac/Linux VM under Docker quotas is not a validated emulation of a particular UAV processor. Sampled memory maxima are not intrinsic model memory or proven minimum RAM requirements.

## Citation, rights and project records

- [Protocol](docs/PROTOCOL.md), [external evidence](docs/EXTERNAL_VALIDATION.md), [repository layout](docs/REPOSITORY_LAYOUT.md).
- [Release notes](CHANGELOG.md), [publication scope](docs/PUBLICATION.md), [citation](CITATION.cff), [rights](RIGHTS.md).

Cite the software version used and the original data providers separately. No general code reuse licence has been granted in this version. The repository is public. The article snapshot is v1.0.0; v1.0.1 updates publication metadata and documentation without changing scientific results. The public history and tags were rebuilt on 5 November 2026; use the current commit identifiers and download checksums.
