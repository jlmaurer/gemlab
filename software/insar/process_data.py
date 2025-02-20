import glob
import math
import os
import rasterio
import shutil
from tqdm import tqdm

import geopandas as gpd
import numpy as np
import rioxarray as rio

from pathlib import Path
from rasterio.mask import mask, raster_geometry_mask
from rasterio.warp import calculate_default_transform, reproject, Resampling



def run_resampling(path_to_shapefile, data_dir='DATA'):
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

    ref_file = 100

    # Get basic info from the reference file
    with rasterio.open(unw_files[ref_file]) as r_int:
        epsg = r_int.crs.to_epsg()
        crs = r_int.crs
        xres = r_int.transform[0]
        yres = r_int.transform[4]

    # get the transform 
    shp = gpd.read_file(path_to_shapefile)
    if shp.crs != crs:
        shp = shp.to_crs(crs)
    bounds = shp.total_bounds
    
    # Create the transform and dimensions for the destination raster
    dst_transform = rasterio.Affine(xres, 0.0, bounds[0], 0.0,yres, bounds[3])
    dst_width = int((bounds[2] - bounds[0]) / xres)
    dst_height = int((bounds[3] - bounds[1]) / -yres)
    out_dict = {'transform': dst_transform, 'width': dst_width, 'height': dst_height, 'crs': crs, 'bounds': bounds, 'proj': shp}

    for k, uf in tqdm(enumerate(unw_files), total=len(unw_files)):
        af = find_matching_file(amp_files, uf)
        ph = find_matching_file(ph_files, uf)
        cf = find_matching_file(cor_files, uf)
        df = find_matching_file(dem_files, uf)
        lvf = find_matching_file(lv_theta_files, uf)
        lpf= find_matching_file(lv_phi_files, uf)
        incf = find_matching_file(inc_files, uf)
        ief = find_matching_file(inc_ell_files, uf)
        mf = find_matching_file(mask_files, uf)
        vf = find_matching_file(vert_disp_files, uf)
        lf = find_matching_file(los_disp_files, uf)

        # loop through all interferograms and coherence rasters, clip to area of interest
        transform_with_shapefile(af,   out_dict)
        transform_with_shapefile(uf,   out_dict)
        transform_with_shapefile(ph,   out_dict)
        transform_with_shapefile(cf,   out_dict)
        transform_with_shapefile(df,   out_dict)
        transform_with_shapefile(lvf,  out_dict)
        transform_with_shapefile(lpf,  out_dict)
        transform_with_shapefile(incf, out_dict)
        transform_with_shapefile(ief,  out_dict)
        transform_with_shapefile(mf,   out_dict)
        transform_with_shapefile(vf,   out_dict)
        transform_with_shapefile(lf,   out_dict)

        if k % 10 == 0:
            print(f'Currently running file #{k} of {len(unw_files)}.')



def update_file(orig_file, ref_file):
    if orig_file is None:
        return

    with rio.open_rasterio(ref_file) as ref:
        src = rio.open_rasterio(orig_file)
        if src.shape != ref.shape:
            ds_out = src.interp_like(ref)
            del src
            ds_out.rio.to_raster(orig_file)


def find_matching_file(flist, f):
    # format: S1AA_20200920T001203_20201002T001203_***
    parts1 = os.path.basename(f).split('_')
    for f2 in flist:
        parts = os.path.basename(f2).split('_')
        if (parts1[1] == parts[1]) & (parts1[2] == parts[2]) & (parts1[7]==parts[7]):
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


def saveraster_with_transform(data,fname,in_transform, transform,crs='',r_crs='',drivername='GTiff',epsg='',datatype='float32',bands=1, dst_height=None,dst_width=None, nodata=0.):

    # get default file size
    if dst_height is None:
        dst_height,dst_width = data.shape

    # data_new=np.reshape(data,(bands,data.shape[0],data.shape[1]))
    if crs !='':
        try:
            crs = rasterio.crs.CRS.from_proj4(crs)
        except TypeError:
            crs = crs
    elif epsg !='':
        crs=rasterio.crs.CRS.from_epsg(epsg)
    else:
        crs = rasterio.crs.CRS.from_epsg('4326')

    with rasterio.open(
            fname,'w',
            driver=drivername,
            height=dst_height,
            width=dst_width,
            count=bands,
            dtype=datatype,
            crs=crs,
            transform=transform
        ) as dst:
        reproject(
            source=data,
            destination=rasterio.band(dst, 1),
            src_transform=in_transform,
            src_crs=crs,
            dst_transform=transform,
            dst_crs=r_crs,
            resampling=Resampling.nearest, # Or other resampling method if needed
        )
        #dst.write(np.array(data,datatype),bands)


def transform_with_shapefile(raster, param_dict):
    '''
    Function to transform a raster to match the bounds of a shapefile
    '''

    # during first iteration of loop, reproject shapefile to same projection as interferograms
    try:
        fname_stem = os.path.splitext(raster)[0]
    except TypeError:
        # if something other than a raster name is passed, just skip it
        return

    try:
        with rasterio.open(raster) as r_int:
            int_mask, out_transform = mask(r_int, param_dict['proj']['geometry'], crop=True)
            r_crs = r_int.crs
            in_transform = r_int.transform

        # Create the new file
        saveraster_with_transform(
            np.squeeze(int_mask), 
            fname_stem+'_int.tif', 
            in_transform,
            param_dict['transform'],
            crs=param_dict['crs'],
            r_crs=r_crs,
            dst_width=param_dict['width'],
            dst_height=param_dict['height'],
        )
    except ValueError:
        # if the raster does not overlap, just skip it
        return


def tranform_all_files(shape_file, in_dir=os.getcwd(), out_dir=os.getcwd()):
    # get list of interferograms
    unwrapped_files = glob.glob(in_dir + os.sep + '*/*unw_phase.tif')
    coh_files = glob.glob(in_dir + os.sep + '*/*corr.tif')

    # get the transform 
    shp = gpd.read_file(path_to_shapefile)
    with rasterio.open(unwrapped_files[0]) as r_int:
        with rasterio.open(coh_files[0]) as r_coh: 
            shp_proj = shp.to_crs(r_int.crs)
            epsg = r_int.crs.to_epsg()

    # loop through all interferograms and coherence rasters, clip to area of interest
    print('clipping files')
    for kk, file in enumerate(unwrapped_files):
        print(str(kk)+' out of '+str(len(unwrapped_files)-1))
        transform_with_shapefile(file, coh_files[kk], shp_proj, epsg)


if __name__=='__main__':
    run_resampling(path_to_shapefile = 'my_shapefile.shp', data_dir='.')
