# Data acquisition and local integration

No raw recordings, processed feature rows or fitted models are supplied. `manifest.csv` and `configs/sessions.json` contain identifiers, hashes and provenance metadata, not receiver observations. Acquire inputs directly from their providers and review their terms. Do not upload purchased or third-party records to this repository.

## 1. Supported development data

The development pipeline expects the raw `vehicle_gps_position_0.csv` files from the pinned benchmark source:

```sh
git clone https://github.com/mrtckr05/Addressing-Data-Leakage-in-UAV-Cyberattack-Detection-A-Realistic-Machine-Learning-Benchmark.git ../gnss-source
git -C ../gnss-source checkout 12b2bff3bf1192cc9348e748bf1d910e2bd2e891
cp configs/local_paths.example.json configs/local_paths.json
```

Set `source_root` in the local JSON to the absolute path of `../gnss-source`. `legacy_root` is optional and unused by the normal pipeline. The three session entries in `configs/sessions.json` specify exact relative paths and SHA256 hashes. They correspond to jamming, spoofing and supplementary benign recordings. The upstream source attributes the recordings to the UAV Attack Dataset: [IEEE DataPort record](https://ieee-dataport.org/open-access/uav-attack-dataset). This ancestry does not establish two independent datasets or permission to redistribute either copy.

Verify before preparation:

```sh
.venv/bin/python scripts/check_data_inputs.py
.venv/bin/python scripts/prepare_data.py
```

The check is read-only and reports missing files or hash mismatches. Preparation also validates feature schema, duplicate timestamps and integer satellite counts. It creates ignored `data/derived/development.csv`; it never turns processed/interpolated upstream rows into additional independent samples.

Required columns are `timestamp`, `noise_per_ms`, `eph`, `epv`, `hdop`, `vdop`, `satellites_used`. The timestamp is recording time in microseconds, not automatically UTC. `eph` is horizontal position-accuracy/error estimate in metres; HDOP is a different quantity. Feature values are not interpolated. The experiment uses a 30-second clean calibration; readiness failures and missing observations follow [the protocol](../docs/PROTOCOL.md).

Preparation regenerates `data/manifest.csv` and count tables. Use a separate working checkout when reproducing results, retaining the release snapshot for comparison. Attack onsets are annotated transitions; physical jammer-on offsets and attack end remain uncertain. The supplementary benign recording is development evidence, not a blind test.

## 2. Local storage and Docker

Keep source downloads outside the checkout where possible. `data/raw/`, `data/derived/`, `data/external/`, `validation/**/incoming/`, `experiments/models/` and Docker runtime artifacts are ignored. Ignore rules do not remove files already committed: run `scripts/check_publication.py` before any push.

After preparing and training your development checkout, follow [input packaging and Docker reproduction](../docs/REPRODUCIBILITY.md#docker-pilot-on-a-mac-with-arm64-docker). `package_pilot_inputs.py` creates a local hashed workspace and sibling `frozen_run_protocol.json`. Docker mounts this workspace read-only via `GNSS_INPUT_ROOT`. This input bundle contains data and models and must not be published. Each changed source, model, image or policy requires a new frozen run and preflight.

## 3. IGASPIN UBX recordings

Obtain the [ZED-F9P chirp-jamming recording](https://www.igaspin.at/product/u-blox-zed-f9p-5-minute-jamming-chirp-scenario-l1-e1/) and the separate [clean recording](https://www.igaspin.at/product/ublox-zed-f9p-01b-01-5-minute-clean-scenario/) from IGASPIN. Preserve acquisition and provider documents privately; this repository does not grant redistribution rights. The expected-clean file's independent acquisition path and clean conditions require provider confirmation.

[The input manifest](../validation/igaspin/data_manifest.json) records the two filenames, raw SHA256, NAV counts and conditional reference. [The adapter guide](../validation/igaspin/README.md) documents exact wire-order association and units.

```sh
python3 scripts/prepare_igaspin_inputs.py --raw-root /path/to/records --output build/igaspin-inputs-NEW
```

Only an ignored local output under build/ is accepted. Input hash mismatch and an existing output directory are rejected. The prepared four streams contain receiver observations: never commit them. This preparation performs no inference or resource measurement. Missing NAV/RF pairs remain unavailable; physical timing and clean exposure are not inferred from continuity. Use only trusted local models and a separately frozen evaluation for any new predictions.

Docker profiles and the historical measurement boundary are described in [docker/igaspin](../docker/igaspin/README.md). Offline UBX decoding is excluded from that latency. Original model/input/image/trace artifacts remain required for exact historical execution; a new fit or hardware run is a distinct experiment. Development and IGASPINsession manifests must stay separate.

## 4. New datasets

Record source/version, terms, hashes, receiver, campaign/day/session/episode hierarchy, units, sampling/gaps, clean calibration, onset/end evidence, uncertainty and evaluation role. Admit only compatible feature sets. Validate the adapter before using a new source. More rows or technical repeats are not additional independent sessions.

Only aggregate scientific outputs are retained in this release. Receiver calibration values and telemetry plots omitted during publication cleanup are preserved in the private research archive. The full feature-level diagnostic traces and trained artifacts must be rebuilt locally from separately obtained inputs.
