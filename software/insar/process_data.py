import glob
import math
import os
import rasterio
import shutil

import numpy as np
import rioxarray as rio

from pathlib import Path


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

        update_file(af, unw_files[ref_file])
        update_file(f,  unw_files[ref_file])
        update_file(ph, unw_files[ref_file])
        update_file(cf, unw_files[ref_file])
        update_file(df, unw_files[ref_file])
        update_file(lvf, unw_files[ref_file])
        update_file(lpf, unw_files[ref_file])
        update_file(incf,unw_files[ref_file])
        update_file(ief,unw_files[ref_file])
        update_file(mf, unw_files[ref_file])
        update_file(vf, unw_files[ref_file])
        update_file(lf, unw_files[ref_file])


def update_file(orig_file, ref_file):
    if orig_file is None:
        return

    src = rio.open_rasterio(orig_file)
    ref = rio.open_rasterio(ref_file)
    src.rio.reproject_match(ref)


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
