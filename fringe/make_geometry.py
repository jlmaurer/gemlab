#!/usr/bin/env python3
"""
Created on TUE Aug 01 2023
Last modified: Sep 24, 2023

@ Author:: Yi-Chieh Lee
"""
import argparse
import os


parser = argparse.ArgumentParser(description='create geometry')
parser.add_argument('-r', '--rangelooks', type=str, metavar='', required=True, help='multilook factor for SAR range direction')
parser.add_argument('-a', '--azimuthlooks', type=str, metavar='', required=True, help='multilook factor for SAR azimuth direction')
args = parser.parse_args()


os.system('gdal_translate -of ENVI hgt.vrt hgt.rdr')
os.system('gdal_translate -of ENVI lon.vrt lon.rdr')
os.system('gdal_translate -of ENVI los.vrt los.rdr')
os.system('gdal_translate -of ENVI lat.vrt lat.rdr')
os.system('gdal_translate -of ENVI shadowMask.vrt shadowMask.rdr')
os.system('gdal_translate -of ENVI incLocal.vrt incLocal.rdr')

os.system('gdal2isce_xml.py -i hgt.rdr')
os.system('gdal2isce_xml.py -i lon.rdr')
os.system('gdal2isce_xml.py -i lat.rdr')
os.system('gdal2isce_xml.py -i los.rdr')
os.system('gdal2isce_xml.py -i shadowMask.rdr')
os.system('gdal2isce_xml.py -i incLocal.rdr')
    
output_name = '_rlks' + args.rangelooks + '_alks' + args.azimuthlooks + '.rdr'

awk1 = 'multilook.py hgt.rdr -r ' + args.rangelooks + ' -a ' + args.azimuthlooks + ' -o hgt' + output_name
awk2 = 'multilook.py lon.rdr -r ' + args.rangelooks + ' -a ' + args.azimuthlooks + ' -o lon' + output_name
awk3 = 'multilook.py lat.rdr -r ' + args.rangelooks + ' -a ' + args.azimuthlooks + ' -o lat' + output_name
awk4 = 'multilook.py los.rdr -r ' + args.rangelooks + ' -a ' + args.azimuthlooks + ' -o los' + output_name
awk5 = 'multilook.py shadowMask.rdr -r ' + args.rangelooks + ' -a ' + args.azimuthlooks + ' -o shadowMask' + output_name
awk6 = 'multilook.py incLocal.rdr -r ' + args.rangelooks + ' -a ' + args.azimuthlooks + ' -o incLocal' + output_name

os.system(awk1)
os.system(awk2)
os.system(awk3)
os.system(awk4)
os.system(awk5)
os.system(awk6)
    
folder_name = 'multi_rlks' + args.rangelooks + '_alks' + args.azimuthlooks
    
cmdline1 = "mkdir "+ folder_name 
os.system(cmdline1)
    
cmdline2 = "mv "+ '*rlks' + args.rangelooks + '_alks' + args.azimuthlooks + '* ' + folder_name + '/.'
os.system(cmdline2)
