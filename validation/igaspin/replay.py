"""Offline conditional ordinal diagnostic. No training or operational endpoints."""
from pathlib import Path
import calendar,csv,datetime,hashlib,json,math,pickle,sys,platform
from adapter import observations,NS,new_event_delays_ns
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(path,digest):
 if sha(path)!=digest:raise RuntimeError('Hash mismatch: '+str(path))

def replay(core,rows,arm,features,cfg,model,threshold,confirmation):
 cal=core.Calibration(features,cfg);det=core.Detector(confirmation,cfg['recovery_negatives'],cfg['max_allowed_gap_s'])
 scores=[];traces=[];event_ns=[];events=[];current=None;previous_label=None
 # Call on every NAV including unavailable first observation; calibration origin never shifts.
 normalized=[];indices=[];availability=[];calstates=[]
 for i,row in enumerate(rows):
  a=row['arms'][arm];vals=[a.get(f,row.get(f)) for f in features]
  valid=a['available'] and row['tAcc_ns']!=0xffffffff and all(v is not None and math.isfinite(v) for v in vals)
  ready=cal.update(row['elapsed_s'],vals if valid else [float('nan')]*len(features))
  cs='FAILED' if cal.failed else ('READY' if cal.baseline is not None else 'CALIBRATING')
  availability.append(valid);calstates.append(cs)
  if ready and valid:
   indices.append(i);normalized.append(core.relative([vals],cal.baseline)[0])
 import numpy as np
 mapped={}
 if normalized:
  pred=core.score(model,np.asarray(normalized))
  mapped={i:float(v) if math.isfinite(float(v)) else None for i,v in zip(indices,pred)}
 for i,row in enumerate(rows):
  value=mapped.get(i);before=det.state;oldcurrent=det.current
  ev=None
  if calstates[i]!='CALIBRATING':ev=det.update(row['elapsed_s'],None if value is None else value>=threshold)
  if ev is not None:
   event_ns.append(row['utc_ns']);current={'start_ns':row['utc_ns'],'end_ns':None,'confirming_NAV_offset':row['nav_offset'],'confirming_RF_offset':row['arms'][arm]['rf_offset']};events.append(current)
  if oldcurrent is not None and det.current is None:
   current['end_ns']=row['utc_ns'];current=None
  label='CALIBRATING' if calstates[i]=='CALIBRATING' else det.state
  scores.append({'observation_index':i,'utc_ns':row['utc_ns'],'elapsed_s':row['elapsed_s'],'available':availability[i],'calibration':calstates[i],'score':value,'state':label,'NAV_offset':row['nav_offset'],'RF_offset':row['arms'][arm]['rf_offset']})
  if label!=previous_label:traces.append({'observation_index':i,'utc_ns':row['utc_ns'],'state':label})
  previous_label=label
 baseline=None if cal.baseline is None else cal.baseline.tolist()
 return {'readiness_success':cal.baseline is not None and not cal.failed,'calibration_failed':cal.failed,'valid_calibration_observations':len(cal.rows),'baseline':baseline,'events':events,'event_ns':event_ns,'unavailable_observations':sum(not x for x in availability),'scores':scores,'transitions':traces}

def writecsv(path,rows):
 with path.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['empty']);w.writeheader();w.writerows(rows)
