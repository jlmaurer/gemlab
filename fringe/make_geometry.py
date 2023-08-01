#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on TUE Aug 01 2023

@ Author:: Yi-Chieh Lee
"""
import sys
import os
import argparse

parser = argparse.ArgumentParser(description='create geometry')
parser.add_argument('-r', '--rangelooks', type=int, metavar='', required=True, help='multilook factor for SAR range direction')
parser.add_argument('-a', '--azimuthlooks', type=int, metavar='', required=True, help='multilook factor for SAR azimuth direction')
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

os.system("multilook.py hgt.rdr -r rangelooks -a azimuthlooks -o 'hgt' + output_name")
os.system("multilook.py lon.rdr -r rangelooks -a azimuthlooks -o 'lon' + output_name")
os.system("multilook.py lat.rdr -r rangelooks -a azimuthlooks -o 'lat' + output_name")
os.system("multilook.py los.rdr -r rangelooks -a azimuthlooks -o 'los' + output_name")
os.system("multilook.py shadowMask.rdr -r rangelooks -a azimuthlooks -o 'shadowMask' + output_name")
os.system("multilook.py incLocal.rdr -r rangelooks -a azimuthlooks -o 'incLocal' + output_name")
    
folder_name = 'multi_rlks' + args.rangelooks + '_alks' + args.azimuthlooks
    
cmdline1 = "mkdir "+ folder_name 
os.system(cmdline1)
    
cmdline2 = "mv "+ '*rlks' + args.rangelooks + '_alks*' + args.azimuthlooks + ' ' + folder_name + '/.'
os.system(cmdline2)
