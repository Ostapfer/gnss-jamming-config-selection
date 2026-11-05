"""Run using the current Python interpreter; realtime replay is mandatory."""
import os, subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR',str(root/'experiments/matplotlib-cache'))
for script,args in [('prepare_data',[]),('train_candidates',[]),('replay_evaluate',[]),('benchmark_resources',[]),('replay_evaluate',['--realtime']),('summarize_results',[]),('verify_results',[])]:
    subprocess.run([sys.executable,str(root/'scripts'/f'{script}.py'),*args],cwd=root,check=True)
