#!/usr/bin/env python3
"""
Created on Mon Jun 20 15:01:35 2022

@author: duttar
"""

import argparse
import glob
import os
import sys

import numpy as np
from osgeo import gdal


def cmdLineParse():
    parser = argparse.ArgumentParser(
        description='Runs Fringe software to create multilooked timeseries.',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=INTRODUCTION + '\n' + EXAMPLE,
    )

    parser.add_argument('-sf', '--stackfolder', type=str, metavar='', required=True, help='path to stack folder')
    parser.add_argument('-fn', '--foldername', type=str, metavar='', required=False, help='Fringe folder name')
    parser.add_argument('-bbox', '--boundingbox', type=str, metavar='', required=True, help='bounding box in S N W E')
    parser.add_argument('-ssize', '--stacksize', type=int, metavar='', required=True, help='stack size for fringe')
    parser.add_argument(
        '-sn',
        '--stepnumber',
        type=int,
        metavar='',
        required=False,
        help='1 for step1, 2 for step2, 3 for step 3, 4 for step4',
    )
    parser.add_argument(
        '-rlks', '--rangelooks', type=int, metavar='', required=True, help='multilook factor for SAR range direction'
    )
    parser.add_argument(
        '-alks',
        '--azimuthlooks',
        type=int,
        metavar='',
        required=True,
        help='multilook factor for SAR azimuth direction',
    )

    inps = parser.parse_args()
    return inps


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
  
  python make_fringe.py -sf /mnt/stor/geob/jlmd9g/Rishabh/northslope/Sentinel/Descending/DT73/stack -fn fringe_sub1 -bbox '70.56 71.43 -157.86 -151.95' -ssize 35 -sn 3 -rlks 12 -alks 3
  
  ###################################################################################
"""


def step1(fringefolder, stackfolder, S, N, W, E, stacksize):
    """
    In this step, creates bsub file to run fringe steps until Sequential.py

    Parameters
    ----------
    fringefolder : TYPE
        DESCRIPTION.
    stackfolder : TYPE
        DESCRIPTION.
    S : TYPE
        DESCRIPTION.
    N : TYPE
        DESCRIPTION.
    W : TYPE
        DESCRIPTION.
    E : TYPE
        DESCRIPTION.
    stacksize : TYPE
        DESCRIPTION.

    Returns:
    -------
    None.

    """
    # copy the combine_SLCs script to the fringe folder
    cmdline1 = 'cd ' + fringefolder + ' && cp ~/softwares/InSAR_utils/isce_mst/combine_SLCs.py .'
    os.system(cmdline1)

    # create the bsub file
    mergedfolder = stackfolder + '/merged'
    bsubfn = fringefolder + '/fringerun1.bsub'
    bsub_file = open(bsubfn, 'w')
    linetowrite1 = '#!/bin/bash\n#SBATCH --job-name=fringe1\n#SBATCH -N 1\n#SBATCH --ntasks=64\n'
    linetowrite2 = '#SBATCH --time=12-02:00:00\n#SBATCH --mail-type=begin,end,fail,requeue\n'
    linetowrite3 = '#SBATCH --mail-user=yl3mz@mst.edu\n#SBATCH --export=all\n#SBATCH --out=Foundry-%j.out\n'
    linetowrite4 = '#SBATCH --mem-per-cpu=4000\n#SBATCH -p general\n\n'
    linetowrite5 = 'python combine_SLCs.py -p ' + mergedfolder + '\n\n'
    linetowrite6 = (
        'tops2vrt.py -i ../merged/ -s coreg_stack -g geometry -c slcs -B ' + S + ' ' + N + ' ' + W + ' ' + E + '\n\n'
    )
    linetowrite7 = 'nmap.py -i coreg_stack/slcs_base.vrt -o KS2/nmap -c KS2/count -x 11 -y 5\n\n'
    linetowrite8 = (
        'sequential.py -i ../merged/SLC -s '
        + np.str(stacksize)
        + ' -o Sequential -w KS2/nmap -b coreg_stack/slcs_base.vrt -x 11 -y 5\n\n'
    )
    linetowrite9 = "echo 'job finished'"

    bsub_file.writelines(linetowrite1)
    bsub_file.writelines(linetowrite2)
    bsub_file.writelines(linetowrite3)
    bsub_file.writelines(linetowrite4)
    bsub_file.writelines(linetowrite5)
    bsub_file.writelines(linetowrite6)
    bsub_file.writelines(linetowrite7)
    bsub_file.writelines(linetowrite8)
    bsub_file.writelines(linetowrite9)
    bsub_file.close()

    # now run the bsub file
    cmdline2 = 'cd ' + fringefolder + ' && sbatch fringerun1.bsub'
    os.system(cmdline2)


def step2(fringefolder, stacksize):
    """
    In this step, all fringe steps are run after Sequential.py

    Parameters
    ----------
    fringefolder : TYPE
        DESCRIPTION.
    stacksize : TYPE
        DESCRIPTION.

    Returns:
    -------
    None.

    """
    bsubfn = fringefolder + '/fringerun2.bsub'
    bsub_file = open(bsubfn, 'w')
    linetowrite1 = '#!/bin/bash\n#SBATCH --job-name=fringe2\n#SBATCH -N 1\n#SBATCH --ntasks=64\n'
    linetowrite2 = '#SBATCH --time=12-02:00:00\n#SBATCH --mail-type=begin,end,fail,requeue\n'
    linetowrite3 = '#SBATCH --mail-user=yl3mz@mst.edu\n#SBATCH --export=all\n#SBATCH --out=Foundry-%j.out\n'
    linetowrite4 = '#SBATCH --mem-per-cpu=4000\n#SBATCH -p general\n\n'
    linetowrite5 = (
        'adjustMiniStacks.py -s slcs/ -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M '
        + np.str(stacksize)
        + ' -o adjusted_wrapped_DS\n\n'
    )
    linetowrite6 = (
        'ampdispersion.py -i coreg_stack/slcs_base.vrt -o ampDispersion/ampdispersion -m ampDispersion/mean\n\n'
    )
    linetowrite7 = 'cd ampDispersion\ngdal2isce_xml.py -i ampdispersion\ngdal2isce_xml.py -i mean\ncd ..\n\n'
    linetowrite8 = 'imageMath.py -e="a<0.4" --a=ampDispersion/ampdispersion  -o ampDispersion/ps_pixels -t byte\n\n'
    linetowrite9 = 'integratePS.py -s coreg_stack/slcs_base.vrt -d adjusted_wrapped_DS/ -t Sequential/Datum_connection/EVD/tcorr.bin -p ampDispersion/ps_pixels -o PS_DS --unwrap_method snaphu\n\n'
    linetowrite10 = (
        'unwrapStack.py -s slcs -m Sequential/miniStacks/ -d Sequential/Datum_connection/ -M '
        + np.str(stacksize)
        + " -u 'unwrap_fringe.py' --unw_method snaphu\n\n"
    )
    linetowrite11 = "echo 'job finished'"

    bsub_file.writelines(linetowrite1)
    bsub_file.writelines(linetowrite2)
    bsub_file.writelines(linetowrite3)
    bsub_file.writelines(linetowrite4)
    bsub_file.writelines(linetowrite5)
    bsub_file.writelines(linetowrite6)
    bsub_file.writelines(linetowrite7)
    bsub_file.writelines(linetowrite8)
    bsub_file.writelines(linetowrite9)
    bsub_file.writelines(linetowrite10)
    bsub_file.writelines(linetowrite11)
    bsub_file.close()

    # now run the bsub file
    cmdline1 = 'cd ' + fringefolder + ' && sbatch fringerun2.bsub'
    os.system(cmdline1)


def step3(fringefolder, rlks, alks):
    """
    In this step, the wrapped timeseries is multilooked and unwrapped

    Returns:
    -------
    None.

    """
    PSDSfolder = fringefolder + '/PS_DS'

    # create a bsub file in PS_DS folder
    bsubfn = PSDSfolder + '/fringerun3.bsub'
    bsub_file = open(bsubfn, 'w')
    linetowrite1 = '#!/bin/bash\n#SBATCH --job-name=fringe3\n#SBATCH -N 1\n#SBATCH --ntasks=64\n'
    linetowrite2 = '#SBATCH --time=6-02:00:00\n#SBATCH --mail-type=begin,end,fail,requeue\n'
    linetowrite3 = '#SBATCH --mail-user=yl3mz@mst.edu\n#SBATCH --export=all\n#SBATCH --out=Foundry-%j.out\n'
    linetowrite4 = '#SBATCH --mem-per-cpu=4000\n##SBATCH -p general\n\n'
    linetowrite5 = 'rm *rlks' + str(rlks) + '*alks' + str(alks) + '*int\n'
    linetowrite6 = 'ls *int >  list_int.txt\n\n'
    awk1 = "awk '{print "
    awk2 = (
        '"multilook.py "substr($1,1,17)".int -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o "substr($1,1,17)"_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.int"}'
    )
    awk3 = "' list_int.txt > multilook.txt\n\n"
    linetowrite7 = awk1 + awk2 + awk3
    linetowrite8 = 'chmod +x multilook.txt\n'
    linetowrite9 = './multilook.txt\n\n'
    linetowrite10 = 'gdal2isce_xml.py -i tcorr_ds_ps.bin\n'
    linetowrite11 = (
        'multilook.py  tcorr_ds_ps.bin -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o tcorr_ds_ps_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.bin\n\n'
    )
    linetowrite12 = 'ls *rlks' + str(rlks) + '*alks' + str(alks) + '*int > multilook_int.txt\n\n'
    awk1 = "awk '{print "
    awk2 = (
        '"unwrap_fringe.py -m snaphu -i "$1" -c tcorr_ds_ps_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.bin -o unwrap/"substr($1,1,17)".unw"}'
    )
    awk3 = "' multilook_int.txt > run_unwrap.txt\n\n"
    linetowrite13 = awk1 + awk2 + awk3
    linetowrite14 = 'chmod +x run_unwrap.txt\n'
    linetowrite15 = 'parallel -j+0 < run_unwrap.txt\n\n\n'
    linetowrite16 = 'echo "finished job"'

    bsub_file.writelines(linetowrite1)
    bsub_file.writelines(linetowrite2)
    bsub_file.writelines(linetowrite3)
    bsub_file.writelines(linetowrite4)
    bsub_file.writelines(linetowrite5)
    bsub_file.writelines(linetowrite6)
    bsub_file.writelines(linetowrite7)
    bsub_file.writelines(linetowrite8)
    bsub_file.writelines(linetowrite9)
    bsub_file.writelines(linetowrite10)
    bsub_file.writelines(linetowrite11)
    bsub_file.writelines(linetowrite12)
    bsub_file.writelines(linetowrite13)
    bsub_file.writelines(linetowrite14)
    bsub_file.writelines(linetowrite15)
    bsub_file.writelines(linetowrite16)
    bsub_file.close()

    # now run the bsub file
    cmdline1 = 'cd ' + PSDSfolder + ' && sbatch fringerun3.bsub'
    os.system(cmdline1)


def radarGeometryTransformer(latfile, lonfile, epsg=4326):
    """
    Create a coordinate transformer to convert map coordinates to radar image line/pixels.
    """
    driver = gdal.GetDriverByName('VRT')
    inds = gdal.OpenShared(latfile, gdal.GA_ReadOnly)
    tempds = driver.Create('', inds.RasterXSize, inds.RasterYSize, 0)
    inds = None
    tempds.SetMetadata(
        {
            'SRS': f'EPSG:{epsg}',
            'X_DATASET': lonfile,
            'X_BAND': '1',
            'Y_DATASET': latfile,
            'Y_BAND': '1',
            'PIXEL_OFFSET': '0',
            'LINE_OFFSET': '0',
            'PIXEL_STEP': '1',
            'LINE_STEP': '1',
        },
        'GEOLOCATION',
    )
    trans = gdal.Transformer(tempds, None, ['METHOD=GEOLOC_ARRAY'])
    return trans


def lonlat2pixeline(lonFile, latFile, lon, lat):
    trans = radarGeometryTransformer(latFile, lonFile)
    ###Checkour our location of interest
    success, location = trans.TransformPoint(1, lon, lat, 0.0)
    if not success:
        print('Location outside the geolocation array range')
    return location


def step4(fringefolder, stackfolder, rlks, alks, S, N, W, E):
    """

    Parameters
    ----------
    fringefolder : TYPE
        DESCRIPTION.

    Returns:
    -------
    None.

    """
    # generate full reso geometry files and then multilook them in merged folder
    geomref_folder = stackfolder + '/merged/geom_reference'

    # create a bsub file in geom_reference folder
    bsubfn = geomref_folder + '/geomrun1.bsub'
    bsub_file = open(bsubfn, 'w')
    linetowrite1 = '#!/bin/bash\n#SBATCH --job-name=fringe4\n#SBATCH -N 1\n#SBATCH --ntasks=64\n'
    linetowrite2 = '#SBATCH --time=6-02:00:00\n#SBATCH --mail-type=begin,end,fail,requeue\n'
    linetowrite3 = '#SBATCH --mail-user=yl3mz@mst.edu\n#SBATCH --export=all\n#SBATCH --out=Foundry-%j.out\n'
    linetowrite4 = '#SBATCH --mem-per-cpu=4000\n##SBATCH -p general\n\n'
    linetowrite5 = 'gdal_translate -of ENVI hgt.rdr.full.vrt hgt.rdr.full\n'
    linetowrite6 = 'gdal_translate -of ENVI lat.rdr.full.vrt lat.rdr.full\n'
    linetowrite7 = 'gdal_translate -of ENVI lon.rdr.full.vrt lon.rdr.full\n'
    linetowrite8 = 'gdal_translate -of ENVI los.rdr.full.vrt los.rdr.full\n'
    linetowrite9 = 'gdal_translate -of ENVI incLocal.rdr.full.vrt incLocal.rdr.full\n'
    linetowrite10 = 'gdal_translate -of ENVI shadowMask.rdr.full.vrt shadowMask.rdr.full\n\n'
    linetowrite11 = (
        'multilook.py hgt.rdr.full -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o hgt_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.rdr\n'
    )
    linetowrite12 = (
        'multilook.py lon.rdr.full -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o lon_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.rdr\n'
    )
    linetowrite13 = (
        'multilook.py lat.rdr.full -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o lat_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.rdr\n'
    )
    linetowrite14 = (
        'multilook.py los.rdr.full -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o los_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.rdr\n'
    )
    linetowrite15 = (
        'multilook.py incLocal.rdr.full -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o incLocal_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.rdr\n'
    )
    linetowrite16 = (
        'multilook.py shadowMask.rdr.full -r '
        + str(rlks)
        + ' -a '
        + str(alks)
        + ' -o shadowMask_rlks'
        + str(rlks)
        + '_alks'
        + str(alks)
        + '.rdr\n\n'
    )

    bsub_file.writelines(linetowrite1)
    bsub_file.writelines(linetowrite2)
    bsub_file.writelines(linetowrite3)
    bsub_file.writelines(linetowrite4)
    bsub_file.writelines(linetowrite5)
    bsub_file.writelines(linetowrite6)
    bsub_file.writelines(linetowrite7)
    bsub_file.writelines(linetowrite8)
    bsub_file.writelines(linetowrite9)
    bsub_file.writelines(linetowrite10)
    bsub_file.writelines(linetowrite11)
    bsub_file.writelines(linetowrite12)
    bsub_file.writelines(linetowrite13)
    bsub_file.writelines(linetowrite14)
    bsub_file.writelines(linetowrite15)
    bsub_file.writelines(linetowrite16)
    bsub_file.close()

    # now run the bsub file
    cmdline1 = 'cd ' + geomref_folder + ' && sbatch geomrun1.bsub'
    os.system(cmdline1)

    ################
    # then multilook the fringe geometry files
    geomfringefolder = fringefolder + '/geometry'
    cmdline2 = 'cd ' + geomfringefolder + ' && mkdir multi_rlks' + str(rlks) + '_alks' + str(alks)
    os.system(cmdline2)

    slclist = glob.glob(os.path.join(stackfolder, 'merged', 'SLC', '*', '*.slc.full'))
    num_slc = len(slclist)

    # ************************************************************************
    # write a script to wait for certain files to create
    # ************************************************************************

    print('number of SLCs discovered: ', num_slc)
    print('we assume that the SLCs and the vrt files are sorted in the same order')

    slclist.sort()

    # get width and height of hgt_multilooked
    fname1 = 'hgt_rlks' + str(rlks) + '_alks' + str(alks) + '.rdr'
    filename1 = os.path.join(stackfolder, 'merged', 'geom_reference', fname1)
    rds = gdal.Open(filename1)
    width, height = rds.RasterXSize, rds.RasterYSize

    latfilename = 'lat_rlks' + str(rlks) + '_alks' + str(alks) + '.rdr.vrt'
    latFile = os.path.join(stackfolder, 'merged', 'geom_reference', latfilename)
    lonfilename = 'lon_rlks' + str(rlks) + '_alks' + str(alks) + '.rdr.vrt'
    lonFile = os.path.join(stackfolder, 'merged', 'geom_reference', lonfilename)

    south = np.float64(S)
    north = np.float64(N)
    west = np.float64(W)
    east = np.float64(E)

    se = lonlat2pixeline(lonFile, latFile, east, south)
    nw = lonlat2pixeline(lonFile, latFile, west, north)
    ymin = np.int(np.round(np.min([se[1], nw[1]])))
    # ymax = np.int(np.round(np.max([se[1], nw[1]])))
    xmin = np.int(np.round(np.min([se[0], nw[0]])))
    # xmax = np.int(np.round(np.max([se[0], nw[0]])))

    fname2 = 'tcorr_ds_ps_rlks' + str(rlks) + '_alks' + str(alks) + '.bin'
    filename2 = os.path.join(fringefolder, 'PS_DS', fname2)
    rds = gdal.Open(filename2)
    xsize, ysize = rds.RasterXSize, rds.RasterYSize

    print('write vrt file for geometry dataset')

    fname3 = '_rlks' + str(rlks) + '_alks' + str(alks) + '.rdr'
    outfilename = geomfringefolder + '/multi_rlks' + str(rlks) + '_alks' + str(alks)

    vrttmpl = """<VRTDataset rasterXSize="{xsize}" rasterYSize="{ysize}">
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
    layers = ['lat', 'lon', 'hgt', 'incLocal', 'shadowMask']
    for ind, val in enumerate(layers):
        with open(os.path.join(outfilename, val + '.vrt'), 'w') as fid:
            fid.write(
                vrttmpl.format(
                    xsize=xsize,
                    ysize=ysize,
                    xmin=xmin,
                    ymin=ymin,
                    width=width,
                    height=height,
                    PATH=os.path.abspath(os.path.join(stackfolder, 'merged', 'geom_reference', val + fname3)),
                )
            )
    vrttmpl2 = """<VRTDataset rasterXSize="{xsize}" rasterYSize="{ysize}">
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
    layers = ['los']
    for ind, val in enumerate(layers):
        with open(os.path.join(outfilename, val + '.vrt'), 'w') as fid:
            fid.write(
                vrttmpl2.format(
                    xsize=xsize,
                    ysize=ysize,
                    xmin=xmin,
                    ymin=ymin,
                    width=width,
                    height=height,
                    PATH=os.path.abspath(os.path.join(stackfolder, 'merged', 'geom_reference', val + fname3)),
                )
            )

    geomfringefolder2 = geomfringefolder + '/multi_rlks' + str(rlks) + '_alks' + str(alks)

    cmdline1 = 'cd ' + geomfringefolder2 + ' && gdal_translate -of ENVI lat.vrt lat.rdr'
    cmdline2 = 'cd ' + geomfringefolder2 + ' && gdal_translate -of ENVI lon.vrt lon.rdr'
    cmdline3 = 'cd ' + geomfringefolder2 + ' && gdal_translate -of ENVI hgt.vrt hgt.rdr'
    cmdline4 = 'cd ' + geomfringefolder2 + ' && gdal_translate -of ENVI los.vrt los.rdr'
    cmdline5 = 'cd ' + geomfringefolder2 + ' && gdal_translate -of ENVI incLocal.vrt incLocal.rdr'
    cmdline6 = 'cd ' + geomfringefolder2 + ' && gdal_translate -of ENVI shadowMask.vrt shadowMask.rdr'

    os.system(cmdline1)
    os.system(cmdline2)
    os.system(cmdline3)
    os.system(cmdline4)
    os.system(cmdline5)
    os.system(cmdline6)


def main(argv):
    inps = cmdLineParse()

    if inps.foldername:
        foldername = inps.foldername
    else:
        foldername = 'fringe'

    if inps.stepnumber:
        stepnumber = inps.stepnumber
    else:
        stepnumber = 5

    S, N, W, E = inps.boundingbox.split(' ')

    fringefolder = inps.stackfolder + '/' + foldername
    rlks = inps.rangelooks
    alks = inps.azimuthlooks

    if stepnumber == 1:
        # in the fringe folder, run step1
        # creates the fringe folder
        cmdline1 = 'cd ' + inps.stackfolder + ' && mkdir ' + foldername
        os.system(cmdline1)

        step1(fringefolder, inps.stackfolder, S, N, W, E, inps.stacksize)
        print('------step 1 finished------')
    elif stepnumber == 2:
        # run step2
        step2(fringefolder, inps.stacksize)
        print('------step 2 finished------')

    elif stepnumber == 3:
        step3(fringefolder, rlks, alks)
        print('------step 3 finished------')
    elif stepnumber == 4:
        step4(fringefolder, inps.stackfolder, rlks, alks, S, N, W, E)
        print('------step 4 finished------')


if __name__ == '__main__':
    main(sys.argv[:])
