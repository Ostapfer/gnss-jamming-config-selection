# Docker: current pilot and historical readiness

Current two-container resource experiments are described in [the reproduction guide](../docs/REPRODUCIBILITY.md#docker-pilot-on-a-mac-with-arm64-docker) and [pilot protocol](pilot/README.md). The parent source snapshot below is retained intentionally for provenance. Statements about pending harness work describe the earlier readiness stage, before the completed pilot; they are not the current execution status.

# Docker limits: preparation and test provenance

`compose.yaml` describes the readiness container actually checked locally. `compose.limits.yaml` describes the **planned** CPU/RAM matrix; its profiles are not measured performance results. Both start the readiness probe only. They do not run training, a resource benchmark, or constrained real-time replay.

## Reproduce readiness

From the repository root, copy `docker/.env.example` to the ignored `docker/.env.local` and set `GNSS_INPUT_ROOT` to a locally verified workspace containing `experiments/candidates.json` and `experiments/models/*.pkl`. Use only trusted local model pickles; first verify them against the frozen input manifest. Models and raw data are not shipped in the image or Git.

```sh
docker compose --env-file docker/.env.local -f docker/compose.yaml config
docker compose --env-file docker/.env.local -f docker/compose.yaml build readiness
docker compose --env-file docker/.env.local -f docker/compose.yaml run --rm --no-deps readiness
```

The build uses the official Python3.12.12 ARM64 image with a pinned base digest and exact Python dependencies. Source in `image/src` is the frozen package snapshot, not an automatically updated copy of the repository package. `image/probe.py` is the readiness entrypoint. Changes to the package require explicitly synchronizing and hashing that image source before rebuilding.

The probe verifies actual cgroupv2CPU/memory/swap values and one finite prediction for each of RULE/DT/SVM/KNN/RF. It is **not** a timing result. Record `docker inspect` before deleting an experimental container to retain exit code and OOMKilled. `tested_readiness.json` records the tested image and effective limits; machine-specific paths/full inspection stay in ignored `artifacts/`.

Review clarification: the saved `memory.current` and `memory.events` snapshot was taken **before numeric imports and model loading**. It is pre-import readiness metadata, not runtime or peak detector memory. The direct pickle probe also bypasses the full Runner input-root path; passing it does not establish that `/inputs` is connected to the existing Runner's `/opt/research` root. See [methodology review](../docs/review/REVIEW_DECISION.md) for the three remaining execution blockers and the user-selected pilot scope.

## Planned matrix

```sh
# Inspect the merged specification; does not start experiments.
docker compose --env-file docker/.env.local -f docker/compose.yaml -f docker/compose.limits.yaml --profile limits config
# Readiness check of ONE selected profile; not a benchmark:
docker compose --env-file docker/.env.local -f docker/compose.yaml -f docker/compose.limits.yaml run --rm --no-deps cpu025_ram256
```

Do not `up` the whole matrix in parallel for measurements. Profiles combine CPUquotas1/0.5/0.25 and totalcontainerRAM1024/512/256MiB, plus a guarded reference with no containerCPUquota and1536MiBRAM. Period100ms; swapoff (memory-swap equals memory); math-librarythreads1. CPU quota is a scheduling ceiling, not an emulation of a specific SBC.

Containers run without network, capabilities or writable root filesystem, with64MiB tmpfs andread-only inputs. Total memory includes runtime/libraries, not just the model. VMresources and unrelated containers are left unchanged; concurrent workloads must be recorded or controlled in a later measurement session.

## Before a measured experiment

Freeze imageID, actual cgroupvalues, inputs/models, selected configs, order, repetitions, cadence and failure policy. Reference and constrained runs must use the same LinuxVM/image; old macOS timings are not the reference.

The existing original-rate replay puts its producer in the detector's process tree. Do not run it unchanged under detectorlimits for primary timing claims. An independently scheduled producer outside the detectorcgroup, with verified shared clock mapping and due/arrival/start/ready logs, is still required. That constrained replay harness is pending; today's readiness preparation is complete, not the full constrained experiment.

Startup/OOM/exit failures remain recorded results rather than silently dropped cases. No purchase, remote publication, retraining or background experiment is started by these files.
