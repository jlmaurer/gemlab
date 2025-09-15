#!/usr/bin/env python3
"""
Created on Fri Mar 11 16:07:12 2022
@author: duttar
"""

import argparse
import os
from pathlib import Path


class Args(argparse.Namespace):
    path: Path


parser = argparse.ArgumentParser(
    description='goes to SLC folder in merged and creates .slc.full files from .slc.full.vrt files'
)
parser.add_argument(
    '-p',
    '--path',
    type=lambda s: Path(s).absolute(),
    metavar='',
    required=True,
    help='enter path to merged folder',
)

args = parser.parse_args(namespace=Args())

merged_dir = args.path
os.system(f'cd {merged_dir}')

slc_dir = merged_dir / 'SLC'

for path in slc_dir.glob('*'):
    print(f'Moving SLC {path.name}')
    sys_comm1 = f'cd {slc_dir / path.name} && '
    sys_comm2 = f'gdal_translate -of ENVI {path.name}.slc.full.vrt {path.name}.slc.full'
    sys_comm3 = sys_comm1 + sys_comm2
    print(sys_comm3)
    os.system(sys_comm3)
