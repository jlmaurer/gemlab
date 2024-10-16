import rasterio
import os
import glob
import math
import shutil

import numpy as np

from pathlib import Path
from rasterio.warp import reproject, Resampling,calculate_from_transform
from rasterio import windows


def run_resampling(data_dir='DATA'):
    '''Resamples a set of raster to ahve the same bounds'''
    glob_path = Path(os.getcwd())
    amp_files =[str(pp) for pp in glob_path.glob('**/*amp.tif')]
    unw_files =[str(pp) for pp in glob_path.glob('**/*unw_phase.tif')]
    ph_files = [str(pp) for pp in glob_path.glob('**/*wrapped_phase.tif')]
    cor_files = [str(pp) for pp in glob_path.glob('**/*corr.tif')]
    dem_files = [str(pp) for pp in glob_path.glob('**/*dem.tif')]
    lv_theta_files = [str(pp) for pp in glob_path.glob('**/*lv_theta.tif')]
    lv_phi_files = [str(pp) for pp in glob_path.glob('**/*lv_phi.tif')]
    inc_files = [str(pp) for pp in glob_path.glob('**/*inc_map.tif')]
    inc_ell_files = [str(pp) for pp in glob_path.glob('**/*inc_map_ell.tif')]
    mask_files = [str(pp) for pp in glob_path.glob('**/*water_mask.tif')]
    vert_disp_files = [str(pp) for pp in glob_path.glob('**/*vert_disp.tif')]
    los_disp_files = [str(pp) for pp in glob_path.glob('**/*los_disp.tif')]

    ref_file = 1
    with rasterio.open(unw_files[ref_file], 'r') as f:
        ref_crs = f.crs
        ref_bounds = f.bounds
        ref_width = f.width
        ref_height = f.height
        ref_ndv = f.nodata
        new_transform = f.transform


    for k, f in enumerate(unw_files):
        af = find_matching_file(amp_files, f)
        ph = find_matching_file(ph_files, f)
        cf = find_matching_file(cor_files, f)
        df = find_matching_file(dem_files, f)
        lvf = find_matching_file(lv_theta_files, f)
        lpf= find_matching_file(lv_phi_files, f)
        incf = find_matching_file(inc_files, f)
        ief = find_matching_file(inc_ell_files, f)
        mf = find_matching_file(mask_files, f)
        vf = find_matching_file(vert_disp_files, f)
        lf = find_matching_file(los_disp_files, f)

        kwupdate = {
            'crs': ref_crs,
            'bounds': ref_bounds,
            'width': ref_width,
            'height': ref_height,
            'nodata': ref_ndv,
            }

        update_file(af, new_transform, kwupdate)
        update_file(f,  new_transform, kwupdate)
        update_file(ph, new_transform, kwupdate)
        update_file(cf, new_transform, kwupdate)
        update_file(df, new_transform, kwupdate)
        update_file(lvf, new_transform, kwupdate)
        update_file(lpf, new_transform, kwupdate)
        update_file(incf,new_transform, kwupdate)
        update_file(ief,new_transform, kwupdate)
        update_file(mf, new_transform,kwupdate)
        update_file(vf, new_transform,kwupdate)
        update_file(lf, new_transform,kwupdate)

        del kwupdate


def update_file(orig_file, new_bounds, kwupdate):
    # See here: https://hatarilabs.com/ih-en/how-to-reproject-single-and-multiple-rasters-with-python-and-rasterio-tutorial
    # and here: https://gis.stackexchange.com/questions/476382/how-to-change-the-extent-of-an-existing-tiff-given-shapefile-bounding-extent-usi
    if orig_file is None:
        return

    # first open the original file
    src = rasterio.open(orig_file)
    options = src.meta.copy()
    data, resampled_transform = expand_extent(src, kwupdate['bounds'], src.nodata)
    kwupdate['transform'] = resampled_transform
    options.update(kwupdate)

    # Now create a temporary new file
    tmp_file = 'tmp.tif'
    dstRst = rasterio.open(tmp_file, 'w', **options)

    # write each band in the old file to the new file
    for i in range(1, src.count + 1):
        reproject(
            source=rasterio.band(src, i),
            destination=rasterio.band(dstRst, i),
            src_crs=src.crs,
            dst_crs=dstRst.crs,
            resampling=Resampling.nearest,
        )

    # close both files
    dstRst.close()
    src.close()

    # Copy the new file to the old file location
    os.replace('tmp.tif', orig_file)


def find_matching_file(flist, f):
    # format: S1AA_20200920T001203_20201002T001203_***
    parts1 = os.path.basename(f).split('_')
    for f2 in flist:
        parts = os.path.basename(f2).split('_')
        if (parts1[1] == parts[1]) & (parts1[2] == parts[2]):
            return f2
    return None


def plot_extents(data_dir):
    unw_files = glob.glob(data_dir + os.sep + '*' + os.sep + '*unw_phase.tif')
    NS_bounds = []
    for f in unw_files:
        with rasterio.open(f) as F:
            NS_bounds.append(F.bounds[:2])

    de = np.array(NS_bounds).mean(axis=0)

    for k, pair in enumerate(NS_bounds):
        plt.plot([k,k], [pair[0]-de[0], pair[1]-de[1]], '-k')
    plt.ylim([de[0] - 100, de[1] + 100])

    plt.savefig('Network_extents.png')
    plt.close('all')


def snap(window):
    """ Handle rasterio's floating point precision (sub pixel) windows """
    # Adding the offset differences to the dimensions will handle case where width/heights can 1 pixel too small
    # after the offsets are shifted. 
    # This ensures pixel contains the bounds that were originally passed to windows.from_bounds()
    col_off, row_off = math.floor(window.col_off), math.floor(window.row_off)
    col_diff, row_diff = window.col_off - col_off, window.row_off - row_off
    width, height = math.ceil(window.width + col_diff), math.ceil(window.height + row_diff)

    return windows.Window(
        col_off=col_off, row_off=row_off, width=width, height=height
    )


def expand_extent(raster, extent, fill_value=None):
    window = snap(windows.from_bounds(*extent, raster.transform))
    data = raster.read(window=window, boundless=True, fill_value=fill_value)
    return data, windows.transform(window, raster.transform)



if __name__=='__main__':
    run_resampling(data_dir='.')
