"""Rebuild a compact Docker report/figures from shipped tables, without raw data.

This is rendering of archived evidence, not fresh raw-trace verification.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from analyze_docker_pilot import report, plot


def read_table(path):
    def value(text):
        if text=='':return None
        if text in ['True','False']:return text=='True'
        try:return int(text)
        except ValueError:
            try:return float(text)
            except ValueError:return text
    with path.open() as f:
        return [{key:value(text) for key,text in row.items()} for row in csv.DictReader(f)]


def reconstruct(archive, output, figures=False):
    if output.exists():raise FileExistsError('Use a new reconstruction output directory')
    summary=json.loads((archive/'summary.json').read_text())
    names=['trials','config_profiles','pareto_descriptive','events']
    paths=[archive/'tables'/(name+'.csv') for name in names]
    tables={name:read_table(path) for name,path in zip(names,paths)}
    if len(tables['trials'])!=summary['attempts']:raise ValueError('Trial table does not match archived summary')
    output.mkdir(parents=True)
    report(output,summary,tables['config_profiles'],tables['pareto_descriptive'],tables['trials'])
    p=output/'REPORT.md';text=p.read_text();heading,body=text.split('\n',1)
    p.write_text(heading+'\n\nReconstructed from archived tables; original raw traces were not rechecked by this command.\n'+body)
    if figures:plot(output,tables['trials'],tables['config_profiles'],tables['events'])
    hashes={str(path.relative_to(archive)):hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [archive/'summary.json',*paths]}
    (output/'reconstruction_provenance.json').write_text(json.dumps({
        'source_artifact_sha256':hashes,'raw_traces_reverified':False,'new_measurements':False,
        'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'analysis_module_sha256':hashlib.sha256((Path(__file__).parent/'analyze_docker_pilot.py').read_bytes()).hexdigest()},indent=2)+'\n')
    print('Reconstructed archived report'+(' and figures' if figures else '')+': '+str(output))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--figures',action='store_true');args=parser.parse_args()
    reconstruct(args.archive.resolve(),args.output.resolve(),args.figures)
