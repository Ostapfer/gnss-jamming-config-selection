import pickle
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from .core import ROOT, config, relative, Rule, write_json

def normalized_training(features):
    d = pd.read_csv(ROOT/'data/derived/development.csv')
    cfg = config()
    parts=[]
    for sid,p in d.groupby('session_id',sort=False):
        if sid=='benign': continue # supplementary dev non-jamming recording, not fit
        cal=p[p.elapsed_s<=cfg['calibration_s']][features]
        good=np.isfinite(cal.to_numpy()).all(axis=1)
        if good.sum()<cfg['minimum_calibration_observations']: continue
        b=cal.loc[good].median().to_numpy()
        p=p[p.elapsed_s>cfg['calibration_s']].copy()
        try: x=relative(p[features].to_numpy(),b)
        except ValueError: continue
        good=np.isfinite(x).all(axis=1)
        parts.append((x[good],p.target_jamming.to_numpy()[good],p.loc[good,['session_id','timestamp','state']]))
    return np.concatenate([a[0] for a in parts]), np.concatenate([a[1] for a in parts]),pd.concat([a[2] for a in parts])

def main():
    cfg=config(); entries=[]; out=ROOT/'experiments/models';out.mkdir(exist_ok=True)
    for fi,features in enumerate(cfg['feature_sets']):
        x,y,fitrows=normalized_training(features)
        if len(np.unique(y))<2: raise ValueError('Cannot train binary model without attack observations')
        for algorithm,profiles in cfg['profiles'].items():
            for pi,params in enumerate(profiles):
                if algorithm=='DT': model=DecisionTreeClassifier(**params,class_weight='balanced',random_state=cfg['seed'])
                elif algorithm=='KNN': model=make_pipeline(StandardScaler(),KNeighborsClassifier(**params))
                elif algorithm=='SVM': model=make_pipeline(StandardScaler(),SVC(**params,kernel='rbf',gamma='scale',class_weight='balanced'))
                else: model=RandomForestClassifier(**params,class_weight='balanced_subsample',random_state=cfg['seed'],n_jobs=1)
                model.fit(x,y)
                cid=f'{algorithm}_f{fi+1}_p{pi+1}'
                path=out/f'{cid}.pkl';path.write_bytes(pickle.dumps(model,protocol=5))
                base=model.steps[-1][1] if hasattr(model,'steps') else model
                complexity={}
                if algorithm=='DT': complexity=dict(nodes=base.tree_.node_count,depth=base.tree_.max_depth)
                if algorithm=='RF': complexity=dict(trees=len(base.estimators_),nodes=sum(t.tree_.node_count for t in base.estimators_),depth=max(t.tree_.max_depth for t in base.estimators_))
                if algorithm=='SVM': complexity=dict(support_vectors=len(base.support_))
                if algorithm=='KNN': complexity=dict(stored_samples=len(base._fit_X),stored_array_bytes=base._fit_X.nbytes+base._y.nbytes)
                entries.append(dict(candidate_id=cid,algorithm=algorithm,features=features,profile=params,thresholds=cfg['svm_margin_thresholds'] if algorithm=='SVM' else cfg['probability_thresholds'],training='development in-sample; future attack rows included',causal=False,model_bytes=path.stat().st_size,fit_rows=len(y),**complexity))
                fitrows.to_csv(out/f'{cid}_fit_rows.csv',index=False)
    for combo in [False,True]:
        for ti,threshold in enumerate(cfg['rule_relative_thresholds']):
            cid=f'RULE_{"noise_eph" if combo else "noise"}_t{ti+1}'
            model=Rule(threshold,combo)
            path=out/f'{cid}.pkl';path.write_bytes(pickle.dumps(model,protocol=5))
            entries.append(dict(candidate_id=cid,algorithm='RULE',features=['noise_per_ms','eph'] if combo else ['noise_per_ms'],profile={'relative_threshold':threshold,'combination':'AND' if combo else 'single'},thresholds=[0.5],training='no supervised fit; calibration-only online; exploratory preselected constants',causal=True,model_bytes=path.stat().st_size,fit_rows=0))
    write_json(ROOT/'experiments/candidates.json',entries)
    pd.DataFrame(entries).to_csv(ROOT/'results/tables/candidates.csv',index=False)
    print('Trained',len(entries),'candidates')
if __name__=='__main__': main()
