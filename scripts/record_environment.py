"""Record actual interpreter/platform and installed pinned-package versions.

Only use in a new reproduction checkout, before generating experimental outputs.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys

ROOT=Path(__file__).resolve().parents[1]


def record(output, replace=False):
    if output.exists() and not replace:raise FileExistsError('Existing environment record: use --replace only in a new reproduction checkout')
    packages={}
    for line in (ROOT/'requirements-lock.txt').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            name,expected=line.strip().split('==',1)
            actual=importlib.metadata.version(name)
            if actual!=expected:raise ValueError(f'Pinned dependency mismatch: {name} requires {expected}, installed {actual}')
            packages[name]=actual
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'python':sys.version,'platform':platform.platform(),'packages':packages},indent=2)+'\n')
    print('Recorded actual environment:',output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--replace',action='store_true');args=parser.parse_args();record(args.output,args.replace)
