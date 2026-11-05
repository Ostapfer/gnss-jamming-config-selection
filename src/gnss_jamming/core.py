import json
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FEATURES = ['noise_per_ms','eph','epv','hdop','vdop','satellites_used']
def read_json(path):
    return json.loads(Path(path).read_text())
def config(): return read_json(ROOT/'configs/experiment.json')
def sessions(): return read_json(ROOT/'configs/sessions.json')
def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str, allow_nan=False)+'\n')

def relative(values, baseline):
    b = np.asarray(baseline, dtype=float)
    x = np.asarray(values, dtype=float)
    if not np.isfinite(b).all() or np.any(b == 0):
        raise ValueError('Invalid/zero calibration baseline; no epsilon permitted')
    return (x-b)/b

@dataclass
class Calibration:
    features: list
    cfg: dict
    start: float = None
    rows: list = field(default_factory=list)
    baseline: object = None
    failed: bool = False
    def update(self, t, values):
        if self.start is None: self.start = t
        x = np.asarray(values, dtype=float)
        if t-self.start <= self.cfg['calibration_s']:
            if np.isfinite(x).all(): self.rows.append(x)
            return False
        if self.baseline is None and not self.failed:
            if len(self.rows) < self.cfg['minimum_calibration_observations']:
                self.failed = True
            else:
                self.baseline = np.median(self.rows, axis=0)
                if not np.isfinite(self.baseline).all() or np.any(self.baseline == 0):
                    self.failed = True
        return not self.failed

@dataclass
class Detector:
    count: int
    recovery: int
    max_gap: float
    state: str = 'IDLE'
    positives: int = 0
    negatives: int = 0
    last_t: float = None
    events: list = field(default_factory=list)
    current: dict = None
    def update(self, t, positive, ready_t=None):
        # A gap or missing observation breaks confirmation/recovery. An open
        # alarm survives UNAVAILABLE; missing data never recovers an alarm.
        if self.last_t is not None and t-self.last_t > self.max_gap:
            self.positives = self.negatives = 0
            self.state = 'UNAVAILABLE'
        self.last_t = t
        if positive is None:
            self.positives = self.negatives = 0
            self.state = 'UNAVAILABLE'
            return None
        if self.current is not None:
            if positive:
                self.negatives = 0
                self.state = 'ACTIVE'
            else:
                self.negatives += 1
                self.state = 'RECOVERY'
                if self.negatives >= self.recovery:
                    self.current['end_s'] = t
                    self.current = None
                    self.negatives = self.positives = 0
                    self.state = 'IDLE'
            return None
        if positive:
            self.positives += 1
            self.state = 'CONFIRMING'
            if self.positives >= self.count:
                event = {'start_s':t,'ready_s':t if ready_t is None else ready_t,'end_s':None}
                self.events.append(event)
                self.current = event
                self.state = 'ACTIVE'
                return event
        else:
            self.positives = 0
            self.state = 'IDLE'
        return None

class Rule:
    def __init__(self, threshold, combo=False):
        self.threshold, self.combo = threshold, combo
    def predict_score(self, x):
        a = np.asarray(x)
        return (a[:,0] >= self.threshold) & ((a[:,1] >= self.threshold) if self.combo else True)

def score(model, x):
    if isinstance(model, Rule): return np.asarray(model.predict_score(x), dtype=float)
    if hasattr(model, 'predict_proba'): return model.predict_proba(x)[:,1]
    return model.decision_function(x)

def interval_overlap(events, start, end):
    return sum(max(0., min(end, e['end_s'] if e['end_s'] is not None else end)-max(start,e['start_s'])) for e in events)
