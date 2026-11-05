# Recovered experiment map — 2026-10-25

Archive note: references to inventory, backups, legacy recovery and `history/` describe the preserved local research archive; those private or duplicate files are intentionally omitted from the publication snapshot. Public state is a concise derivative. See [reproduction boundaries](REPRODUCIBILITY.md).

## Inventory and preservation
`inventory.csv` inventories 283 files (593,228,228 bytes) under the original
working folder, excluding virtual environments and Git metadata. It records
paths, byte sizes and SHA256. The original directory is preserved in place. All 280 research/code/data/document
files match both the archive and original hashes. Three mutable Finder
`.DS_Store` metadata files changed during inventory/archiving; these exceptions
are disclosed in `preservation_verification.json`.
`backup.json` describes a separate pre-change compressed archive containing
these inventoried files. It does not contain virtual environments or Git object
history. The upstream dataset checkout was clean; its commit is pinned in the
session manifest. The enclosing legacy experiment was not a Git repository.

`gnss_validation.py` was not found. Existing source notebooks and PDFs are
inventoried; the new experiment does not depend on notebooks or extract claims
from the papers. The three unrelated network-data ZIP archives remain untouched.

## File lineage
- `build_dynamic_gnss_dataset.py` → `dynamic_gnss_dataset.csv`: processed merged
  features, rejected for final ML input because interpolated physical fields
  can be fractional. Historical exploratory outputs only.
- `build_raw_dynamic_dataset.py` + raw GPS jamming/spoofing sessions →
  `raw_dynamic_gnss_dataset.csv`: six relative baseline and delta features;
  drops first row/session because deltas are NaN; uses a hidden denominator
  floor `max(abs(b),1e-6)`, which the new pipeline removes.
- `raw_gnss_model_experiment.py`: per-session/per-state temporal splits.
  Attack prefixes enter training, so this does not test onset detection.
- `early_attack_detection.py`: first 70% benign for training and later attack
  (>10 s) for training; early attack for test; uses first attack sample as onset.
- `stable_detection_delay.py`: same future-informed split with annotated onset;
  confirmation counts 1/2/3 evaluated only on attack rows, not a full state machine.
- `resource_benchmark.py`: historical timing output retained; new pipeline
  measures the complete software path and a separate model-only diagnostic.

## Exact ≈5.98 s recovery
Re-running the copied, unmodified `stable_detection_delay.py` with the original
`raw_dynamic_gnss_dataset.csv` reproduces its CSV byte-for-byte (see
`legacy_recovery.json`). Noise-only DT/KNN/RF give 4.979947 s for one positive,
5.982160 s for two, and 6.984160 s for three. Noise+eph is not uniformly 5.98 s:
KNN two-positive delay is 7.984150 s, RF is 8.984151 s.

The models explicitly see later attack rows from the same episode. Therefore
these values are **development-contaminated, future-informed illustrations**.
They do not establish causal early detection or physical jammer response time.
The original output and hashes are retained, and discrepancy is not concealed.

## New repository plan, implemented
- `src/gnss_jamming/`: calibration/state logic, preparation, candidate training,
  replay, resources, requirement screening and Pareto summaries.
- `scripts/`: five user-facing stages and an end-to-end runner.
- `configs/`: immutable input records, finite protocol/library, local path example.
- `data/manifest.csv`: audited raw provenance; raw and derived files excluded.
- `experiments/`: run metadata and ignored generated local model files.
- `results/tables`, `results/figures`: article-oriented outputs.
- `tests/`: meaningful checks of confirmation, missingness and calibration.
- `PROJECT_STATE.md`, `README.md`: decisions, limitations and reproduction.

## Causality decision
With only one jamming episode, supervised training on positive samples before
that episode is impossible. No synthetic independence is created. All 60 ML
models are fit to the two development attack sessions after calibration and
replayed as a diagnostic in-sample experiment. Their full fit-row membership
is saved locally, and `causal=false` accompanies all reported configurations.
Six fixed threshold rules use only online clean calibration. Their replay is
causal in time, but their threshold library was selected after viewing legacy
data and cannot be called blind validation. They are reported separately.
