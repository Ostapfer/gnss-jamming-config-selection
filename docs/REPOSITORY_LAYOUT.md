# Repository layout

| Path | Purpose |
|---|---|
| `src/gnss_jamming/` | Shared preprocessing, detector, replay, resource and summary code |
| `configs/` | Finite library, calibration/decision policies, sessions and a local-path example |
| `data/` | Provenance/units/hash manifest and data acquisition contract; no raw data |
| `scripts/` | Ordered workflow, integrity/report tools, Docker control and input packaging |
| `docker/igaspin/` | Measured external runtime bridge, exported Compose parameters and fixed scope |
| `docker/pilot/` | Actual two-container pilot Compose, image recipe and bounded policies |
| `docker/image/` | Pinned dependency parent and deliberately frozen readiness source snapshot |
| `tests/` | Protocol, replay, resource accounting, transport and lifecycle regression checks |
| `results/` | Selected archived summaries, representative tables and figures |
| `validation/` | IGASPIN ordinal adapter, diagnostic replay helper and input metadata |
| `docs/` | Method, evidence boundaries, reproduction guide, curated references and reviews |
| `release/` | Publication file hashes and source-export provenance |

Large generated timing/scenario ledgers, duplicate v1 history, source datasets, models, local paths, provider correspondence, internal working notes and browser/runtime logs remain in the original local research workspace. They are not needed to browse the public source or run a new experiment after separately obtaining data. Scientific caveats and the v1 erratum remain included.

The parent readiness source is an intentional provenance snapshot. It must not be deduplicated into the current package without a new image/protocol identity.

Receiver baseline diagnostics and telemetry plots are excluded from the publication release. See data/README.md for acquisition, local storage and adapter requirements.
