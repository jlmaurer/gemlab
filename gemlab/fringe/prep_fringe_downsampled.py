#!/usr/bin/env python3
############################################################
# Program is part of MintPy                                #
# Copyright (c) 2013, Zhang Yunjun, Heresh Fattahi         #
# Author: Zhang Yunjun, Forrest Williams, Apr 2020         #
############################################################


import argparse
import sys

# import defusedxml.ElementTree as ET
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

import h5py
import numpy as np
from mintpy import subset
from mintpy.utils import (
    arg_utils,
    isce_utils,
    ptime,
    readfile,
    writefile,
)
from mintpy.utils import (
    attribute as attr,
)
from mintpy.utils import (
    utils as ut,
)
from osgeo import gdal


####################################################################################
EXAMPLE = """example:
  prep_fringe.py -u './PS_DS/unwrap/*.unw' -c ./PS_DS/tcorr_ds_ps.bin -g ./geometry -m '../reference/IW*.xml' -b ../baselines -o ./mintpy

  cd ~/data/SanAndreasSenDT42/fringe
  prep_fringe.py

  ## example commands after prep_fringe.py
  reference_point.py timeseries.h5 -y 500 -x 1150
  generate_mask.py temporalCoherence.h5 -m 0.7 -o maskTempCoh.h5
  tropo_pyaps3.py -f timeseries.h5 -g inputs/geometryRadar.h5
  remove_ramp.py timeseries_ERA5.h5 -m maskTempCoh.h5 -s linear
  dem_error.py timeseries_ERA5_ramp.h5 -g inputs/geometryRadar.h5
  timeseries2velocity.py timeseries_ERA5_ramp_demErr.h5
  geocode.py velocity.h5 -l inputs/geometryRadar.h5
"""


type WSEN = tuple[float, float, float, float]


class Args(argparse.Namespace):
    unwFile: str
    coh_file: Path
    ps_mask_file: Path
    geom_dir: Path
    meta_file: Path
    baseline_dir: Path
    out_dir: Path
    lks_x: int
    lks_y: int
    geom_only: bool


def cmd_line_parse(iargs: Sequence[str] | None = None) -> Args:
    SYNOPSIS = 'Prepare FRInGE products for MintPy'
    name = __name__.split('.')[-1]
    parser = arg_utils.create_argument_parser(
        name,
        synopsis=SYNOPSIS,
        description=SYNOPSIS,
        epilog=EXAMPLE,
    )

    parser.add_argument(
        '-u',
        '--unw-file',
        dest='unwFile',
        type=str,
        default='PS_DS/unwrap/*.unw',
        help='path pattern of unwrapped interferograms (default: %(default)s).',
    )
    parser.add_argument(
        '-c',
        '--coh-file',
        type=lambda s: Path(s).absolute(),
        default='PS_DS/tcorr_ds_ps.bin',
        help='temporal coherence file (default: %(default)s).',
    )
    parser.add_argument(
        '--ps-mask',
        dest='ps_mask_file',
        type=lambda s: Path(s).absolute(),
        default='ampDispersion/ps_pixels',
        help='PS pixels file (default: %(default)s).',
    )
    parser.add_argument(
        '-g',
        '--geom-dir',
        type=lambda s: Path(s).absolute(),
        default='geometry',
        help='FRInGE geometry directory (default: %(default)s).\n'
        'This is used to grab 1) bounding box\n'
        '                 AND 2) geometry source directory where the binary files are.',
    )

    parser.add_argument(
        '-m',
        '--meta-file',
        type=lambda s: sorted(Path.cwd().glob(s))[0].absolute(),
        default='../reference/IW*.xml',
        help='metadata file (default: %(default)s).\n'
        'e.g.: ./reference/IW1.xml        for ISCE/topsStack OR\n'
        '      ./referenceShelve/data.dat for ISCE/stripmapStack',
    )
    parser.add_argument(
        '-b',
        '--baseline-dir',
        type=lambda s: Path(s).absolute(),
        default='../baselines',
        help='baseline directory (default: %(default)s).',
    )

    parser.add_argument(
        '-o',
        '--out-dir',
        type=lambda s: Path(s).absolute(),
        default='mintpy',
        help='output directory (default: %(default)s).',
    )

    parser.add_argument(
        '-r',
        '--range',
        dest='lks_x',
        type=int,
        default=1,
        help='number of looks in range direction, for multilooking applied after fringe processing.\n'
        'Only impacts metadata. (default: %(default)s).',
    )
    parser.add_argument(
        '-a',
        '--azimuth',
        dest='lks_y',
        type=int,
        default=1,
        help='number of looks in azimuth direction, for multilooking applied after fringe processing.\n'
        'Only impacts metadata. (default: %(default)s).',
    )

    parser.add_argument(
        '--geom-only',
        action='store_true',
        help='Only create the geometry file (useful for geocoding a watermask).',
    )

    parser = arg_utils.add_subset_argument(parser, geo=False)
    return parser.parse_args(args=iargs, namespace=Args())


####################################################################################
def read_vrt_info(vrt_path: Path) -> tuple[WSEN, Path]:
    """Read info from VRT file.
    Parameters: vrt_path - Path, geometry vrt file path
    Returns:    src_box  - tuple of 4 int, bounding box in (x0, y0, x1, y1)
                           indicating the area processed by FRInGE.
                src_dir  - str, path of geometry directory with binary data files
    """
    root = ET.parse(vrt_path).getroot()

    # get VRT tag structure
    prefix_cand = ('VRTRasterBand/SimpleSource', 'VRTRasterBand')
    prefix_list = [prefix for prefix in prefix_cand if root.find(prefix + '/SourceFilename') is not None]
    if len(prefix_list) > 0:
        prefix = prefix_list[0]
    else:
        msg = f'No pre-defined tag structure found in file: {vrt_path}!\nPre-defined tag structure candidates:'
        for prefix in prefix_cand:
            msg += f'\n    {prefix}/SourceFilename'
        raise ValueError(msg)

    # src_box
    type_tag = root.find(prefix + '/SrcRect')
    assert type_tag is not None
    xmin = float(type_tag.get('xOff'))
    ymin = float(type_tag.get('yOff'))
    xsize = float(type_tag.get('xSize'))
    ysize = float(type_tag.get('ySize'))
    xmax = xmin + xsize
    ymax = ymin + ysize
    src_box = (xmin, ymin, xmax, ymax)
    print(f'read bounding box from VRT file: {vrt_path} as (x0, y0, x1, y1): {src_box}')

    # source dir
    type_tag = root.find(prefix + '/SourceFilename')
    assert type_tag is not None
    src_dir = Path(type_tag.text).parent

    # in case of a (usually multilooked) vrt file missing SourceFilename field
    if not src_dir:
        src_dir = vrt_path.parent

    return src_box, src_dir


def prepare_metadata(
    meta_file: Path,
    geom_src_dir: Path,
    bbox: WSEN | None = None,
    nlks_x: int = 1,
    nlks_y: int = 1,
) -> dict[str, str]:
    print('-' * 50)

    # extract metadata from ISCE to MintPy (ROIPAC) format
    meta = isce_utils.extract_isce_metadata(str(meta_file), update_mode=False)[0]

    if 'Y_FIRST' in meta.keys():
        geom_ext = '.geo.full'
    else:
        geom_ext = '_rlks9_alks3.rdr'

    # add LAT/LON_REF1/2/3/4, HEADING, A/RLOOKS
    meta = isce_utils.extract_geometry_metadata(str(geom_src_dir), meta=meta, box=bbox, fext_list=[geom_ext])

    # apply optional user multilooking
    if nlks_x > 1:
        meta['RANGE_PIXEL_SIZE'] = str(float(meta['RANGE_PIXEL_SIZE']) * nlks_x)
        meta['RLOOKS'] = str(float(meta['RLOOKS']) * nlks_x)

    if nlks_y > 1:
        meta['AZIMUTH_PIXEL_SIZE'] = str(float(meta['AZIMUTH_PIXEL_SIZE']) * nlks_y)
        meta['ALOOKS'] = str(float(meta['ALOOKS']) * nlks_y)

    return meta


def prepare_timeseries(
    out_path: Path,
    unw_pattern: str,
    metadata: dict[str, str],
    processor_name: str,
    baseline_dir: Path,
    bbox: WSEN | None = None,
) -> None:
    print('-' * 50)
    print(f'preparing timeseries file: {out_path}')

    # Copy to modify without altering original
    meta = metadata.copy()
    phase2range = float(meta['WAVELENGTH']) / (4.0 * np.pi)

    # grab date list from the filename
    unw_paths = sorted(Path.cwd().glob(unw_pattern))
    date12_list = [path.stem for path in unw_paths]
    num_file = len(unw_paths)
    print(f'number of unwrapped interferograms: {num_file}')

    ref_date = date12_list[0].split('_')[0]
    dates = [ref_date] + [date12.split('_')[1] for date12 in date12_list]
    num_dates = len(dates)
    print(f'number of acquisitions: {num_dates}\n{dates}')

    ## baseline info
    # read baseline data
    baseline_dict: dict[str, list[float]] | None = isce_utils.read_baseline_timeseries(
        baseline_dir,
        processor=processor_name,
        ref_date=ref_date,
    )
    assert baseline_dict is not None
    # dict to array
    pbase = np.zeros(num_dates, dtype=np.float32)
    for i in range(num_dates):
        pbase_top, pbase_bottom = baseline_dict[dates[i]]
        pbase[i] = (pbase_top + pbase_bottom) / 2.0

    # size info
    w, s, e, n = bbox or (0, 0, int(meta['WIDTH']), int(meta['LENGTH']))
    kwargs = {
        'xoff': w,
        'yoff': s,
        'win_xsize': e - w,
        'win_ysize': n - s,
    }

    # define dataset structure
    dates_array = np.array(dates, dtype=np.bytes_)
    ds_name_dict = {
        'date': [dates_array.dtype, (num_dates,), dates_array],
        'bperp': [np.float32, (num_dates,), pbase],
        'timeseries': [np.float32, (num_dates, n - s, e - w), None],
    }

    # initiate HDF5 file
    meta['FILE_TYPE'] = 'timeseries'
    meta['UNIT'] = 'm'
    meta['REF_DATE'] = ref_date
    writefile.layout_hdf5(str(out_path), ds_name_dict, metadata=meta)

    # writing data to HDF5 file
    print(f'writing data to HDF5 file {out_path} with a mode ...')
    with h5py.File(out_path, 'a') as fout:
        prog_bar = ptime.progressBar(maxValue=num_file)
        for i, unw_path in enumerate(unw_paths):
            # read data using gdal
            ds: gdal.Dataset | None = gdal.Open(unw_path, gdal.GA_ReadOnly)
            assert ds is not None
            data = np.array(ds.GetRasterBand(2).ReadAsArray(**kwargs), dtype=np.float32)

            fout['timeseries'][i + 1] = data * phase2range
            prog_bar.update(i + 1, suffix=date12_list[i])
        prog_bar.close()

        print('set value at the first acquisition to ZERO.')
        fout['timeseries'][0] = 0.0

    print(f'finished writing to HDF5 file: {out_path}')


def prepare_temporal_coherence(
    out_path: Path,
    in_path: Path,
    metadata: dict[str, str],
    bbox: WSEN | None = None,
) -> None:
    print('-' * 50)
    print(f'preparing temporal coherence file: {out_path}')

    # copy metadata to meta
    meta = metadata.copy()
    meta['FILE_TYPE'] = 'temporalCoherence'
    meta['UNIT'] = '1'

    # size info
    w, s, e, n = bbox or (0, 0, int(meta['WIDTH']), int(meta['LENGTH']))
    kwargs = {
        'xoff': w,
        'yoff': s,
        'win_xsize': e - w,
        'win_ysize': n - s,
    }

    # read data using gdal
    ds: gdal.Dataset | None = gdal.Open(str(in_path), gdal.GA_ReadOnly)
    assert ds is not None
    data = np.array(ds.GetRasterBand(1).ReadAsArray(**kwargs), dtype=np.float32)

    print('set all data less than 0 to 0.')
    data[data < 0] = 0

    # write to HDF5 file
    writefile.write(data, str(out_path), metadata=meta)


def prepare_ps_mask(
    out_path: Path,
    in_path: Path,
    metadata: dict[str, str],
    bbox: WSEN | None = None,
) -> None:
    print('-' * 50)
    print(f'preparing PS mask file: {out_path}')

    # copy metadata to meta
    meta = {key: value for key, value in metadata.items()}
    meta['FILE_TYPE'] = 'mask'
    meta['UNIT'] = '1'

    # size info
    w, s, e, n = bbox or (0, 0, int(meta['WIDTH']), int(meta['LENGTH']))
    kwargs = {
        'xoff': w,
        'yoff': s,
        'win_xsize': e - w,
        'win_ysize': n - s,
    }

    # read data using gdal
    ds: gdal.Dataset | None = gdal.Open(str(in_path), gdal.GA_ReadOnly)
    assert ds is not None
    data = np.array(ds.GetRasterBand(1).ReadAsArray(**kwargs), dtype=np.float32)

    # write to HDF5 file
    writefile.write(data, str(out_path), metadata=meta)


def prepare_geometry(out_path: Path, geom_dir: Path, bbox: WSEN, metadata: dict[str, str]) -> None:
    print('-' * 50)
    print(f'preparing geometry file: {out_path}')

    # copy metadata to meta
    meta = metadata.copy()
    meta['FILE_TYPE'] = 'temporalCoherence'

    files = {
        'height': geom_dir / 'hgt_rlks9_alks3.rdr',
        'latitude': geom_dir / 'lat_rlks9_alks3.rdr',
        'longitude': geom_dir / 'lon_rlks9_alks3.rdr',
        'incidenceAngle': geom_dir / 'los_rlks9_alks3.rdr',
        'azimuthAngle': geom_dir / 'los_rlks9_alks3.rdr',
        'shadowMask': geom_dir / 'shadowMask_rlks9_alks3.rdr',
    }

    # initiate dsDict
    datasets = {}
    for ds_name, path in files.items():
        datasets[ds_name] = readfile.read(str(path), datasetName=ds_name, box=bbox)[0]

    datasets['slantRangeDistance'] = ut.range_distance(meta, dimension=2)

    # write data to HDF5 file
    writefile.write(datasets, str(out_path), metadata=meta)


def prepare_stack(
    out_path: Path,
    unw_pattern: str,
    metadata: dict[str, str],
    processor_name: str,
    baseline_dir: Path,
    bbox: WSEN | None = None,
) -> None:
    print('-' * 50)
    print(f'preparing ifgramStack file: {out_path}')
    # copy metadata to meta
    meta = metadata.copy()

    # get list of *.unw file
    unw_paths = sorted(Path.cwd().glob(unw_pattern))
    num_paths = len(unw_paths)
    print('number of interferograms:', num_paths)

    # get list of *.unw.conncomp file
    cc_paths = [path.with_suffix(path.suffix + '.conccomp') for path in unw_paths if path.is_file()]
    print(f'number of connected components files: {len(cc_paths)}')

    if len(cc_paths) != len(unw_paths):
        print('The number of *.unw and *.unw.conncomp files are NOT consistent;')
        print('Skipping creating ifgramStack.h5 file.')
        return

    # get date info: date12_list
    date12_list = ptime.yyyymmdd_date12([path.stem for path in unw_paths])

    ## prepare baseline info
    # read baseline timeseries
    baseline_dict: dict[str, list[float]] | None = isce_utils.read_baseline_timeseries(
        baseline_dir, processor=processor_name
    )
    assert baseline_dict is not None

    # calc baseline for each pair
    print('calc perp baseline pairs from time-series')
    pbase = np.zeros(num_paths, dtype=np.float32)
    for i, date12 in enumerate(date12_list):
        [date1, date2] = date12.split('_')
        pbase[i] = np.subtract(baseline_dict[date2], baseline_dict[date1]).mean()

    # size info
    w, s, e, n = bbox or (0, 0, int(meta['WIDTH']), int(meta['LENGTH']))
    kwargs = {
        'xoff': w,
        'yoff': s,
        'win_xsize': e - w,
        'win_ysize': n - s,
    }

    # define (and fill out some) dataset structure
    date12_arr = np.array([date12.split('_') for date12 in date12_list], dtype=np.bytes_)
    drop_ifgram = np.ones(num_paths, dtype=np.bool_)
    ds_name_dict = {
        'date': [date12_arr.dtype, (num_paths, 2), date12_arr],
        'bperp': [np.float32, (num_paths,), pbase],
        'dropIfgram': [np.bool_, (num_paths,), drop_ifgram],
        'unwrapPhase': [np.float32, (num_paths, n - s, e - w), None],
        'connectComponent': [np.float32, (num_paths, n - s, e - w), None],
    }

    # initiate HDF5 file
    meta['FILE_TYPE'] = 'ifgramStack'
    writefile.layout_hdf5(str(out_path), ds_name_dict, metadata=meta)

    # writing data to HDF5 file
    print(f'writing data to HDF5 file {out_path} with a mode ...')
    with h5py.File(out_path, 'a') as fout:
        prog_bar = ptime.progressBar(maxValue=num_paths)
        for i, (unw_path, cc_path) in enumerate(zip(unw_paths, cc_paths)):
            # read/write *.unw file
            ds: gdal.Dataset | None = gdal.Open(unw_paths, gdal.GA_ReadOnly)
            assert ds is not None
            data = np.array(ds.GetRasterBand(2).ReadAsArray(**kwargs), dtype=np.float32)
            fout['unwrapPhase'][i] = data

            # read/write *.unw.conncomp file
            ds: gdal.Dataset | None = gdal.Open(cc_file, gdal.GA_ReadOnly)
            assert ds is not None
            data = np.array(ds.GetRasterBand(1).ReadAsArray(**kwargs), dtype=np.float32)
            fout['connectComponent'][i] = data

            prog_bar.update(i + 1, suffix=date12_list[i])
        prog_bar.close()

    print(f'finished writing to HDF5 file: {out_path}')


####################################################################################
def main(iargs: list[str] | None = None) -> tuple[Path, Path, Path, Path] | None:
    args = cmd_line_parse(iargs)

    # translate input options
    processor = isce_utils.get_processor(args.meta_file)
    src_box, geom_src_dir = read_vrt_info(args.geom_dir / 'lat.vrt')

    # metadata
    meta = prepare_metadata(args.meta_file, geom_src_dir, src_box, nlks_x=args.lks_x, nlks_y=args.lks_y)

    # subset - read pix_box for fringe file
    pix_box = subset.subset_input_dict2box(vars(args), meta)[0]
    pix_box = ut.coordinate(meta).check_box_within_data_coverage(pix_box)
    print(f'input subset in y/x: {pix_box}')

    # subset - update src_box for isce file and meta
    src_box = (pix_box[0] + src_box[0], pix_box[1] + src_box[1], pix_box[2] + src_box[0], pix_box[3] + src_box[1])
    meta = attr.update_attribute4subset(meta, pix_box)
    print(f'input subset in y/x with respect to the VRT file: {src_box}')

    # output directory
    (args.out_dir / 'inputs').mkdir(parents=True, exist_ok=True)

    ## output filename
    ts_path = args.out_dir / 'timeseries.h5'
    tcoh_path = args.out_dir / 'temporalCoherence.h5'
    ps_mask_path = args.out_dir / 'maskPS.h5'
    stack_path = args.out_dir / 'inputs/ifgramStack.h5'
    if 'Y_FIRST' in meta.keys():
        geom_path = args.out_dir / 'inputs/geometryGeo.h5'
    else:
        geom_path = args.out_dir / 'inputs/geometryRadar.h5'

    ## 1 - geometry (from SLC stacks before fringe, e.g. ISCE2)
    prepare_geometry(out_path=geom_path, geom_dir=geom_src_dir, bbox=src_box, metadata=meta)

    if args.geom_only:
        return ts_path, tcoh_path, ps_mask_path, geom_path

    ## 2 - time-series (from fringe)
    prepare_timeseries(
        out_path=ts_path,
        unw_pattern=args.unwFile,
        metadata=meta,
        processor_name=processor,
        baseline_dir=args.baseline_dir,
        bbox=pix_box,
    )

    ## 3 - temporal coherence and mask for PS (from fringe)
    prepare_temporal_coherence(out_path=tcoh_path, in_path=args.coh_file, metadata=meta, bbox=pix_box)

    prepare_ps_mask(out_path=ps_mask_path, in_path=args.ps_mask_file, metadata=meta, bbox=pix_box)

    ## 4 - ifgramStack for unwrapped phase and connected components
    prepare_stack(
        out_path=stack_path,
        unw_pattern=args.unwFile,
        metadata=meta,
        processor_name=processor,
        baseline_dir=args.baseline_dir,
        bbox=pix_box,
    )

    print('Done.')


####################################################################################
if __name__ == '__main__':
    main(sys.argv[1:])
