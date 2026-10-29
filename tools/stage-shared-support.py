#!/usr/bin/env python3
"""Stage shared-library support without mutating the active installation."""
import argparse
from pathlib import Path
import shutil
from shared_support import install
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,default=ROOT/'work/build/shared-tools')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.output.exists():p.error('Use a fresh staging directory')
shutil.copytree((ROOT/'install/current').resolve(),a.output,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
install(a.output,a.build)
print('Staged shared-library support; test before promoting')
