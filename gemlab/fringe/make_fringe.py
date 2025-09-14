#!/usr/bin/env python3
"""
Created on Mon Jun 20 15:01:35 2022

@author: duttar
"""

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from osgeo import gdal

import gemlab.types import SNWE


INTRODUCTION = """
##################################################################################
   Copy Right(c): 2022, Rishabh Dutta  @fringetotimesseries 

   Runs Fringe software to create multilooked timeseries 
   Step 1: Fringe processing until sequential.py
   Step 2: Fringe processing until PS_DS wrapped timeseries
   Step 3: Multilook wrapped timeseries and unwrap 
   Step 4: create files for multilooked timeseries and run mintpy processing 
"""

EXAMPLE = """example:

  python make_fringe.py -sf /mnt/stor/geob/jlmd9g/Rishabh/northslope/Sentinel/Descending/DT73/stack -fn fringe_sub1 \
    -bbox '70.56 71.43 -157.86 -151.95' -ssize 35 -sn 3 -rlks 12 -alks 3 -e your@emailaddresshere.com

  ###################################################################################
"""


def bbox_unserialize(text: str) -> SNWE:
    tokens = [int(token) for token in text.split(' ')]
    assert len(tokens) == 4, 'Invalid bounding box input'
    s, n, w, e = tokens
    return s, n, w, e


def bbox_serialize(bbox: SNWE) -> str:
    tokens = [str(token) for token in bbox]
    return ' '.join(tokens)


class Args(argparse.Namespace):
    stackfolder: Path
    foldername: str
    boundingbox: SNWE
    stacksize: int
    stepnumber: int
    rangelooks: int
    azimuthlooks: int
    email: str


def cmd_line_parse(argv: Sequence[str]) -> Args:
    parser = argparse.ArgumentParser(
        description='Runs Fringe software to create multilooked timeseries.',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=INTRODUCTION + '\n' + EXAMPLE,
    )

    parser.add_argument(
        '-sf',
        '--stackfolder',
        type=lambda s: Path(s).absolute(),
        metavar='',
        required=True,
        help='path to stack folder',
    )
    parser.add_argument(
        '-fn',
        '--foldername',
        type=str,
        metavar='',
        required=False,
        default='fringe',
        help='Fringe folder name',
    )
    parser.add_argument(
        '-bbox',
        '--boundingbox',
        type=bbox_unserialize,
        metavar='',
        required=True,
        help='bounding box in S N W E',
    )
    parser.add_argument(
        '-ssize',
        '--stacksize',
        type=int,
        metavar='',
        required=True,
        help='stack size for fringe',
    )
    parser.add_argument(
        '-sn',
        '--stepnumber',
        type=int,
        metavar='',
        required=False,
        default=5,
        help='1 for step1, 2 for step2, 3 for step 3, 4 for step4',
    )
    parser.add_argument(
        '-rlks',
        '--rangelooks',
        type=int,
        metavar='',
        required=True,
        help='multilook factor for SAR range direction',
    )
    parser.add_argument(
        '-alks',
        '--azimuthlooks',
        type=int,
        metavar='',
        required=True,
        help='multilook factor for SAR azimuth direction',
    )
    parser.add_argument(
        '-e',
        '--email',
        type=str,
        metavar='',
        required=False,
        default='',
        help='Email address to send Slurm job updates to',
    )

    args = parser.parse_args(argv, namespace=Args())
    return args


def step1(fringe_folder: Path, stack_folder: Path, bounding_box: SNWE, stack_size: int, email: str) -> None:
    """
    Creates bsub file to run fringe steps until sequential.py.
    Must run in a Slurm environment, or otherwise have `sbatch` available.
    """
    # copy the combine_SLCs script to the fringe folder
    os.system(f'cd {fringe_folder} && cp ~/softwares/InSAR_utils/isce_mst/combine_SLCs.py .')

    merged_folder = stack_folder / 'merged'
    bsub_path = fringe_folder / 'fringerun1.bsub'
    with bsub_path.open('w') as bsub_file:
        bsub_file.writelines([
            '#!/bin/bash',
            '#SBATCH --job-name=fringe1',
            '#SBATCH -N 1',
            '#SBATCH --ntasks=64',
            '#SBATCH --time=12-02:00:00',
            '#SBATCH --mail-type=begin,end,fail,requeue',
            f'#SBATCH --mail-user={email}',
            '#SBATCH --export=all',
            '#SBATCH --out=Foundry-%j.out',
            '#SBATCH --mem-per-cpu=4000',
            '#SBATCH -p general',
            f'python combine_SLCs.py -p {merged_folder}',
            f'tops2vrt.py -i ../merged/ -s coreg_stack -g geometry -c slcs -B {bbox_serialize(bounding_box)}',
            'nmap.py -i coreg_stack/slcs_base.vrt -o KS2/nmap -c KS2/count -x 11 -y 5',
            (
                f'sequential.py -i ../merged/SLC -s {stack_size} -o Sequential -w KS2/nmap '
                '-b coreg_stack/slcs_base.vrt -x 11 -y 5'
            ),
            "echo 'job finished'",
        ])
    os.system(f'cd {fringe_folder} && sbatch fringerun1.bsub')


def step2(fringe_folder: Path, stack_size: int, email: str) -> None:
    """All fringe steps are run after sequential.py."""
    bsub_path = fringe_folder / 'fringerun2.bsub'
    with bsub_path.open('w') as bsub_file:
        bsub_file.writelines([
            '#!/bin/bash',
            '#SBATCH --job-name=fringe2',
            '#SBATCH -N 1',
            '#SBATCH --ntasks=64',
            '#SBATCH --time=12-02:00:00',
            '#SBATCH --mail-type=begin,end,fail,requeue',
            f'#SBATCH --mail-user={email}',
            '#SBATCH --export=all',
            '#SBATCH --out=Foundry-%j.out',
            '#SBATCH --mem-per-cpu=4000',
            '#SBATCH -p general',
            '',
            (
                'adjustMiniStacks.py -s slcs/ -m Sequential/miniStacks/ -d Sequential/Datum_connection/ '
                f'-M {stack_size} -o adjusted_wrapped_DS'
            ),
            'ampdispersion.py -i coreg_stack/slcs_base.vrt -o ampDispersion/ampdispersion -m ampDispersion/mean',
            '',
            'cd ampDispersion',
            'gdal2isce_xml.py -i ampdispersion',
            'gdal2isce_xml.py -i mean',
            'cd ..',
            '',
            'imageMath.py -e="a<0.4" --a=ampDispersion/ampdispersion  -o ampDispersion/ps_pixels -t byte',
            (
                'integratePS.py -s coreg_stack/slcs_base.vrt -d adjusted_wrapped_DS/ '
                '-t Sequential/Datum_connection/EVD/tcorr.bin -p ampDispersion/ps_pixels -o PS_DS '
                '--unwrap_method snaphu'
            ),
            (
                f'unwrapStack.py -s slcs -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M {stack_size} '
                '-u "unwrap_fringe.py" --unw_method snaphu'
            ),
            '',
            "echo 'job finished'",
        ])
    os.system(f'cd {fringe_folder} && sbatch fringerun2.bsub')


def step3(fringe_folder: Path, range_looks: int, azimuth_looks: int, email: str) -> None:
    """The wrapped timeseries is multilooked and unwrapped."""
    ps_ds_folder = fringe_folder / 'PS_DS'
    bsub_path = ps_ds_folder / 'fringerun3.bsub'
    with bsub_path.open('w') as bsub_file:
        bsub_file.writelines([
            '#!/bin/bash',
            '#SBATCH --job-name=fringe3',
            '#SBATCH -N 1',
            '#SBATCH --ntasks=64',
            '#SBATCH --time=6-02:00:00',
            '#SBATCH --mail-type=begin,end,fail,requeue',
            f'#SBATCH --mail-user={email}',
            '#SBATCH --export=all',
            '#SBATCH --out=Foundry-%j.out',
            '#SBATCH --mem-per-cpu=4000',
            '##SBATCH -p general',
            f'rm *rlks{range_looks}*alks{azimuth_looks}*int',
            'ls *int >  list_int.txt',
            (
                'awk \'{{'
                    f'print "multilook.py "substr($1,1,17)".int -r {range_looks} -a {azimuth_looks} '
                    f'-o "substr($1,1,17)"_rlks{range_looks}_alks{azimuth_looks}.int"'
                '}}\' list_int.txt > multilook.sh'
            ),
            'chmod +x multilook.sh',
            './multilook.sh',
            'gdal2isce_xml.py -i tcorr_ds_ps.bin',
            (
                f'multilook.py tcorr_ds_ps.bin -r {range_looks} -a {azimuth_looks} '
                f'-o tcorr_ds_ps_rlks{range_looks}_alks{azimuth_looks}.bin'
            ),
            f'ls *rlks{range_looks}*alks{azimuth_looks}*int > multilook_int.txt',
            (
                'awk \'{{'
                    'print "unwrap_fringe.py -m snaphu -i "$1" '
                    f'-c tcorr_ds_ps_rlks{range_looks}_alks{azimuth_looks}.bin '
                    '-o unwrap/"substr($1,1,17)".unw"'
                '}}\' multilook_int.txt > run_unwrap.sh'
            ),
            'chmod +x run_unwrap.sh',
            'parallel -j+0 < run_unwrap.sh',
            '',
            'echo "finished job"',
        ])
    os.system(f'cd {ps_ds_folder} && sbatch fringerun3.bsub')


def radarGeometryTransformer(lat_path: Path, lon_path: Path, epsg: int = 4326) -> gdal.GDALTransformerInfoShadow:
    """Create a coordinate transformer to convert map coordinates to radar image line/pixels."""
    driver: gdal.Driver | None = gdal.GetDriverByName('VRT')
    assert driver is not None
    in_ds: gdal.Dataset | None = gdal.OpenShared(lat_path, gdal.GA_ReadOnly)
    assert in_ds is not None
    temp_ds: gdal.Dataset = driver.Create('', in_ds.RasterXSize, in_ds.RasterYSize, 0)
    del in_ds
    temp_ds.SetMetadata(
        {
            'SRS': f'EPSG:{epsg}',
            'X_DATASET': str(lon_path),
            'X_BAND': '1',
            'Y_DATASET': str(lat_path),
            'Y_BAND': '1',
            'PIXEL_OFFSET': '0',
            'LINE_OFFSET': '0',
            'PIXEL_STEP': '1',
            'LINE_STEP': '1',
        },
        'GEOLOCATION',
    )
    transformer = gdal.Transformer(temp_ds, None, ['METHOD=GEOLOC_ARRAY'])
    return transformer


def lonlat2pixeline(lon_path: Path, lat_path: Path, lon: float, lat: float):
    transformer = radarGeometryTransformer(lat_path, lon_path)
    # Checkout our location of interest
    success, location = transformer.TransformPoint(1, lon, lat, 0.0)
    if not success:
        print('Location outside the geolocation array range')
    return location


def step4(fringe_folder: Path, stack_folder: Path, range_looks: int, azimuth_looks: int, bounding_box: SNWE, email: str) -> None:
    # generate full reso geometry files and then multilook them in merged folder
    geomref_folder = stack_folder / 'merged/geom_reference'
    bsub_path = geomref_folder / 'geomrun1.bsub'
    with bsub_path.open('w') as bsub_file:
        bsub_file.writelines([
            '#!/bin/bash',
            '#SBATCH --job-name=fringe4',
            '#SBATCH -N 1',
            '#SBATCH --ntasks=64',
            '#SBATCH --time=6-02:00:00',
            '#SBATCH --mail-type=begin,end,fail,requeue',
            f'#SBATCH --mail-user={email}',
            '#SBATCH --export=all',
            '#SBATCH --out=Foundry-%j.out',
            '#SBATCH --mem-per-cpu=4000',
            '##SBATCH -p general',
            'gdal_translate -of ENVI hgt.rdr.full.vrt hgt.rdr.full',
            'gdal_translate -of ENVI lat.rdr.full.vrt lat.rdr.full',
            'gdal_translate -of ENVI lon.rdr.full.vrt lon.rdr.full',
            'gdal_translate -of ENVI los.rdr.full.vrt los.rdr.full',
            'gdal_translate -of ENVI incLocal.rdr.full.vrt incLocal.rdr.full',
            'gdal_translate -of ENVI shadowMask.rdr.full.vrt shadowMask.rdr.full',
            f'multilook.py hgt.rdr.full -r {range_looks} -a {azimuth_looks} -o hgt_rlks{range_looks}_alks{azimuth_looks}.rdr',
            f'multilook.py lon.rdr.full -r {range_looks} -a {azimuth_looks} -o lon_rlks{range_looks}_alks{azimuth_looks}.rdr',
            f'multilook.py lat.rdr.full -r {range_looks} -a {azimuth_looks} -o lat_rlks{range_looks}_alks{azimuth_looks}.rdr',
            f'multilook.py los.rdr.full -r {range_looks} -a {azimuth_looks} -o los_rlks{range_looks}_alks{azimuth_looks}.rdr',
            f'multilook.py incLocal.rdr.full -r {range_looks} -a {azimuth_looks} -o incLocal_rlks{range_looks}_alks{azimuth_looks}.rdr',
            f'multilook.py shadowMask.rdr.full -r {range_looks} -a {azimuth_looks} -o shadowMask_rlks{range_looks}_alks{azimuth_looks}.rdr',
        ])
    os.system(f'cd {geomref_folder} && sbatch geomrun1.bsub')

    geom_fringe_folder_1 = fringe_folder / 'geometry'
    (geom_fringe_folder_1 / f'multi_rlks{range_looks}_alks{azimuth_looks}').mkdir(exist_ok=True)

    slc_list = list(stack_folder.glob('merged/SLC/*/*.slc.full'))
    num_slc = len(slc_list)
    print(f'number of SLCs discovered: {num_slc}')
    print('we assume that the SLCs and the vrt files are sorted in the same order')
    slc_list.sort()

    rdr_filename_1 = f'hgt_rlks{range_looks}_alks{azimuth_looks}.rdr'
    rdr_path_1 = stack_folder / 'merged/geom_reference' / rdr_filename_1
    rds: gdal.Dataset | None = gdal.Open(str(rdr_path_1))
    assert rds is not None
    width, height = rds.RasterXSize, rds.RasterYSize

    lat_filename = f'lat_rlks{range_looks}_alks{azimuth_looks}.rdr.vrt'
    lat_path = stack_folder / 'merged/geom_reference' / lat_filename
    lon_filename = f'lon_rlks{range_looks}_alks{azimuth_looks}.rdr.vrt'
    lon_path = stack_folder / 'merged/geom_reference' / lon_filename

    s, n, w, e = bounding_box

    se = lonlat2pixeline(lon_path, lat_path, e, s)
    nw = lonlat2pixeline(lon_path, lat_path, w, n)
    ymin = int(np.round(np.min([se[1], nw[1]])))
    xmin = int(np.round(np.min([se[0], nw[0]])))

    bin_filename = f'tcorr_ds_ps_rlks{range_looks}_alks{azimuth_looks}.bin'
    bin_path = fringe_folder / 'PS_DS' / bin_filename
    rds: gdal.Dataset | None = gdal.Open(str(bin_path))
    assert rds is not None
    xsize, ysize = rds.RasterXSize, rds.RasterYSize

    print('write vrt file for geometry dataset')

    rdr_filename_3 = f'_rlks{range_looks}_alks{azimuth_looks}.rdr'
    out_path = geom_fringe_folder_1 / f'multi_rlks{range_looks}_alks{azimuth_looks}'

    vrt_template_1 = """<VRTDataset rasterXSize="{xsize}" rasterYSize="{ysize}">
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>{PATH}</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="{width}" RasterYSize="{height}" DataType="Float64"/>
        <SrcRect xOff="{xmin}" yOff="{ymin}" xSize="{xsize}" ySize="{ysize}"/>
        <DstRect xOff="0" yOff="0" xSize="{xsize}" ySize="{ysize}"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>"""
    for val in ('lat', 'lon', 'hgt', 'incLocal', 'shadowMask'):
        with (out_path / f'{val}.vrt').open('w') as fout:
            fout.write(
                vrt_template_1.format(
                    xsize=xsize,
                    ysize=ysize,
                    xmin=xmin,
                    ymin=ymin,
                    width=width,
                    height=height,
                    PATH=str((stack_folder / 'merged/geom_reference' / f'{val}{rdr_filename_3}').resolve()),
                )
            )
    vrt_template_2 = """<VRTDataset rasterXSize="{xsize}" rasterYSize="{ysize}">
    <VRTRasterBand dataType="Float64" band="1">
      <SimpleSource>
        <SourceFilename>{PATH}</SourceFilename>
        <SourceBand>1</SourceBand>
        <SourceProperties RasterXSize="{width}" RasterYSize="{height}" DataType="Float64"/>
        <SrcRect xOff="{xmin}" yOff="{ymin}" xSize="{xsize}" ySize="{ysize}"/>
        <DstRect xOff="0" yOff="0" xSize="{xsize}" ySize="{ysize}"/>
      </SimpleSource>
    </VRTRasterBand>
    <VRTRasterBand dataType="Float64" band="2">
      <SimpleSource>
        <SourceFilename>{PATH}</SourceFilename>
        <SourceBand>2</SourceBand>
        <SourceProperties RasterXSize="{width}" RasterYSize="{height}" DataType="Float64"/>
        <SrcRect xOff="{xmin}" yOff="{ymin}" xSize="{xsize}" ySize="{ysize}"/>
        <DstRect xOff="0" yOff="0" xSize="{xsize}" ySize="{ysize}"/>
      </SimpleSource>
    </VRTRasterBand>
</VRTDataset>"""
    for val in ('los'):
        with (out_path / f'{val}.vrt').open('w') as fout:
            fout.write(
                vrt_template_2.format(
                    xsize=xsize,
                    ysize=ysize,
                    xmin=xmin,
                    ymin=ymin,
                    width=width,
                    height=height,
                    PATH=str((stack_folder / 'merged/geom_reference' / f'{val}{rdr_filename_3}').resolve()),
                )
            )

    geom_fringe_folder_2 = geom_fringe_folder_1 / f'multi_rlks{range_looks}_alks{azimuth_looks}'

    os.system(f'cd {geom_fringe_folder_2} && gdal_translate -of ENVI lat.vrt lat.rdr')
    os.system(f'cd {geom_fringe_folder_2} && gdal_translate -of ENVI lon.vrt lon.rdr')
    os.system(f'cd {geom_fringe_folder_2} && gdal_translate -of ENVI hgt.vrt hgt.rdr')
    os.system(f'cd {geom_fringe_folder_2} && gdal_translate -of ENVI los.vrt los.rdr')
    os.system(f'cd {geom_fringe_folder_2} && gdal_translate -of ENVI incLocal.vrt incLocal.rdr')
    os.system(f'cd {geom_fringe_folder_2} && gdal_translate -of ENVI shadowMask.vrt shadowMask.rdr')


def main(argv: list[str]) -> None:
    args = cmd_line_parse(argv)

    fringe_folder = args.stackfolder / args.foldername

    match args.stepnumber:
        case 1:
            # in the fringe folder, run step1
            fringe_folder.mkdir(exist_ok=True)
            step1(fringe_folder, args.stackfolder, args.boundingbox, args.stacksize, args.email)
            print('------step 1 finished------')
        case 2:
            # run step2
            step2(fringe_folder, args.stacksize, args.email)
            print('------step 2 finished------')
        case 3:
            step3(fringe_folder, args.rangelooks, args.azimuthlooks, args.email)
            print('------step 3 finished------')
        case 4:
            step4(fringe_folder, args.stackfolder, args.rangelooks, args.azimuthlooks, args.boundingbox, args.email)
            print('------step 4 finished------')


if __name__ == '__main__':
    main(sys.argv[:])
