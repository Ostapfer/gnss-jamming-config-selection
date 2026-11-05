# IGASPIN measured resource configuration

compose.yaml exports the two-container configuration actually used on Apple M2/Linux ARM64 Docker Desktop. Only the personal scope bind mount has been replaced by IGASPIN_SCOPE_ROOT. runtime_bridge.py and policy.json are unchanged study sources; scope.json retains the 80-trial order and four profiles. The source/collector has 512 MiB outside the detector allocation. Detector R0 has no CPU quota and 1536 MiB; R1–R3 use 1/0.5/0.25 CPU with 512 MiB, a 100 ms period, no swap and one numerical thread. Networking is disabled, mounts are read-only except declared outputs and IPC.

The scope root must contain runtime_bridge.py, policy.json and reference_subset.json for the optional historical parity entry point. The latter contains private score-level reference material and is not supplied. Workload specifications and trusted model/input bundles must be prepared separately. The file is a resource-parameter record, not an 80-run launcher, fresh preflight acceptance or promise of historical image availability.

To inspect interpolation without starting containers:

```sh
IGASPIN_SCOPE_ROOT="$PWD/docker/igaspin" GNSS_INPUT_ROOT=/path/to/private-inputs PILOT_TRANSPORT_ROOT=/path/to/private-transport PILOT_OUTPUT_ROOT=/path/to/private-output docker compose -f docker/igaspin/compose.yaml config
```

Do not launch a measurement merely because Compose parses. A new run must freeze inputs, image, code, policies, scope and actual cgroup/source-clock proofs. The historical image ID and original manifest hashes are recorded in results/igaspin_resource_20261105/experiment_manifest.json. Raw/model/trace bundles are excluded. UBX decoding and RF/NAV association occur offline before the measured prepared-message-to-event-ready path. No validated UAV-processor equivalence follows from these quotas.
