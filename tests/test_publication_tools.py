"""Small stdlib-only checks for input packaging and explicit parent pinning."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def module(name):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class PublicationTools(unittest.TestCase):
    def test_input_copy_hashes_and_no_overwrite(self):
        pack=module('package_pilot_inputs')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'source';root.mkdir()
            names=['configs/experiment.json','configs/sessions.json','data/derived/development.csv',
                   'src/gnss_jamming/core.py','src/gnss_jamming/replay.py','src/gnss_jamming/benchmark.py',
                   'requirements-lock.txt','experiments/environment.json','experiments/models/RULE_test.pkl']
            for n in names:
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture-not-unpickled')
            (root/'experiments/candidates.json').write_text('[{"candidate_id":"RULE_test"}]')
            dest=Path(temp)/'frozen';pack.package(root,dest)
            manifest=json.loads((dest/'frozen_run_protocol.json').read_text())
            self.assertEqual(len(manifest['input_hashes']),10)
            self.assertEqual((dest/'workspace/experiments/models/RULE_test.pkl').read_bytes(),b'fixture-not-unpickled')
            with self.assertRaises(FileExistsError):pack.package(root,dest)

    def test_missing_input_refuses_to_create_destination(self):
        pack=module('package_pilot_inputs')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'experiments').mkdir()
            (root/'experiments/candidates.json').write_text('[]')
            with self.assertRaises(ValueError):pack.package(root,root/'absent')
            self.assertFalse((root/'absent').exists())

    def test_portable_wrapper_requires_explicit_parent(self):
        wrapper=module('run_portable_pilot')
        with patch.dict('os.environ',{'GNSS_PARENT_IMAGE_ID':''}),patch.object(wrapper.pilot,'main') as run:
            with self.assertRaises(SystemExit):wrapper.main()
            run.assert_not_called()

    def test_wrapper_and_parent_join_provenance(self):
        wrapper=module('run_portable_pilot');pin='sha256:'+'a'*64;seen={}
        def inspect():
            seen['parent']=wrapper.pilot.EXPECTED_PARENT;seen['hashes']=wrapper.pilot.code_hashes()
        with patch.dict('os.environ',{'GNSS_PARENT_IMAGE_ID':pin}), \
             patch.object(wrapper.pilot,'code_hashes',return_value={'base':'hash'}), \
             patch.object(wrapper.pilot,'main',side_effect=inspect):wrapper.main()
        self.assertEqual(seen['parent'],pin)
        self.assertIn('scripts/run_portable_pilot.py',seen['hashes'])

if __name__=='__main__':unittest.main()
