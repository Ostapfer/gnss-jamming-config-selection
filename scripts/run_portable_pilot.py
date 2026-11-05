"""Portable entry point: explicitly pin a locally rebuilt dependency parent.

All scientific execution remains in run_docker_pilot.py. This wrapper and its
parent choice join the frozen provenance; it never relaxes input/image checks.
Use this entry point consistently for build/preflight/freeze/run in a NEW run.
"""
import os
import re
from pathlib import Path
import run_docker_pilot as pilot


def main():
    parent = os.environ.get('GNSS_PARENT_IMAGE_ID', '')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', parent):
        raise SystemExit('Set GNSS_PARENT_IMAGE_ID to the explicitly inspected, trusted rebuilt parent image ID')
    pilot.EXPECTED_PARENT = parent
    original = pilot.code_hashes
    def hashes():
        values = original()
        values[str(Path(__file__).resolve().relative_to(pilot.ROOT))] = pilot.sha(__file__)
        return values
    pilot.code_hashes = hashes
    pilot.main()


if __name__ == '__main__':
    main()
