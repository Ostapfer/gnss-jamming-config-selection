"""Readiness only: verify cgroup limits and frozen-model loading, never run a benchmark."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import pickle
import platform
from pathlib import Path


def cgroup(name):
    p = Path('/sys/fs/cgroup') / name
    return p.read_text().strip() if p.exists() else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-root', type=Path, default=Path('/inputs'))
    parser.add_argument('--expected-cpu', type=float, default=1)
    parser.add_argument('--expected-memory-mib', type=int, default=512)
    args = parser.parse_args()
    report = {'kind': 'READINESS_ONLY_NOT_MEASUREMENT', 'platform': platform.platform(),
              'machine': platform.machine(), 'python': platform.python_version(),
              'versions': {p: importlib.metadata.version(p) for p in ['numpy', 'scipy', 'pandas', 'scikit-learn', 'psutil']},
              'cgroups': {n: cgroup(n) for n in ['cpu.max', 'memory.max', 'memory.swap.max', 'memory.current', 'memory.events']},
              'threads': {n: os.environ.get(n) for n in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']}}
    cpu = report['cgroups']['cpu.max']
    if not cpu:
        raise RuntimeError('cgroup v2 cpu.max unavailable; cannot verify CPU ceiling')
    quota, period = cpu.split()
    if args.expected_cpu == 0:
        assert quota == 'max', 'Reference must not have a container CPU quota'
    else:
        assert quota != 'max' and abs(int(quota)/int(period) - args.expected_cpu) < 1e-9
    assert int(report['cgroups']['memory.max']) == args.expected_memory_mib * 2**20
    assert report['cgroups']['memory.swap.max'] == '0', 'Swap must be disabled'
    root = args.input_root
    candidates = json.loads((root/'experiments/candidates.json').read_text())
    results = []
    # Only trusted local models whose hashes were verified against the frozen input manifest.
    for cid in ['RULE_noise_t2', 'DT_f3_p2', 'SVM_f3_p2', 'KNN_f3_p1', 'RF_f3_p3']:
        c = next(c for c in candidates if c['candidate_id'] == cid)
        path = root/'experiments/models'/f'{cid}.pkl'
        model = pickle.loads(path.read_bytes())
        from gnss_jamming.core import score
        import numpy as np
        value = score(model, np.zeros((1, len(c['features']))))
        assert np.isfinite(value).all()
        results.append({'candidate_id': cid, 'model_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'smoke_prediction_finite': True})
    report['model_smoke'] = results
    report['status'] = 'READY_SMOKE_PASSED'
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
