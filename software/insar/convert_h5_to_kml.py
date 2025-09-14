from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pyproj
import rasterio as rio
from pyproj import CRS
from rasterio import warp as riow


DEFAULT_DICT = {
    'driver': 'GTiff',
    'dtype': 'float64',
    'nodata': 0,
    'width': 6,
    'height': 6,
    'count': 1,
    'crs': CRS.from_epsg(4326),
    'transform': rio.Affine(30.0, 0.0, -105.0, 0.0, -30.0, 105.0),
    'blockysize': 6,
    'tiled': False,
    'interleave': 'band',
    'compress': 'lzw',
}


def read_h5(path: Path) -> tuple[Any, dict[str, Any]]:
    with h5py.File(path) as f:
        vel = f['velocity'][()]
        width = int(f.attrs['WIDTH'])
        hgt = int(f.attrs['FILE_LENGTH'])
        R = f.attrs['EARTH_RADIUS']
        crs = f.attrs['EPSG']
        ndv = f.attrs['NO_DATA_VALUE']
        xstep = f.attrs['X_STEP']
        ystep = f.attrs['Y_STEP']
        xf = float(f.attrs['X_FIRST'])
        yf = float(f.attrs['Y_FIRST'])

    profile = DEFAULT_DICT
    profile['nodata'] = float(ndv)
    profile['width'] = width
    profile['height'] = hgt
    profile['crs'] = CRS.from_user_input(crs)
    profile['dtype'] = vel[0, 0].dtype
    profile['transform'] = rio.Affine(float(xstep), 0, xf, 0, float(ystep), yf)

    return vel, profile


def write_gtiff(input_path: Path, output_path: Path | None = None) -> None:
    """Read an HDF5 velocity file and write the velocity out to a GeoTiff"""
    output_path = output_path or input_path.with_suffix('.tif')
    vel, profile = read_h5(input_path)
    with rio.open(output_path, 'w', **profile) as ds:
        ds.write(vel, 1)


def reproject_geotiff(
    input_path: Path,
    output_path: Path,
    src_epsg: int,
    dst_epsg: int,
    resampling: riow.Resampling = riow.Resampling.nearest,
) -> None:
    """
    Reprojects a GeoTIFF from one coordinate system to another.

    Args:
        input_filename: Path to the input GeoTIFF file.
        output_filename: Path to the output GeoTIFF file.
        src_epsg: EPSG code of the source coordinate system.
        dst_epsg: EPSG code of the destination coordinate system.
        resampling: Resampling method to use during reprojection (default: nearest).
    """
    # Define source and destination CRS objects using pyproj
    dst_crs_obj = pyproj.CRS.from_epsg(dst_epsg)

    # Open the source GeoTIFF
    with rio.open(input_path) as src:
        # Get source data, transform, and CRS
        src.read(1)
        src_transform = src.transform
        transform, width, height = riow.calculate_default_transform(src.crs, dst_crs_obj, src.width, src.height, *src.bounds)

        dst_profile = src.meta.copy()
        dst_profile.update({'crs': dst_crs_obj, 'transform': transform, 'width': width, 'height': height})

        # Perform reprojection using rasterio.warp.reproject
        with rio.open(output_path, 'w', **dst_profile) as dst:
            for i in range(1, src.count + 1):
                riow.reproject(
                    source=rio.band(src, i),
                    destination=rio.band(dst, i),
                    src_transform=src_transform,
                    src_crs=src.crs,
                    dst_crs=dst_crs_obj,
                    resampling=resampling,
                )


def single_band_to_rgb(input_path: Path, output_path: Path) -> None:
    """
    Converts a single-band GeoTIFF to a 3-band grayscale RGB image.

    Args:
        input_path: Path to the single-band GeoTIFF file.
        output_path: Path to the output 3-band RGB GeoTIFF file.
    """
    # Open the single-band GeoTIFF
    with rio.open(input_path) as src:
        data = src.read(1)
        profile = src.meta.copy()

    # Create a 3-band array by replicating the single band
    rgb_data = np.stack([data, data, data], axis=0)
    profile['count'] = 3

    # Write the replicated data as a 3-band GeoTIFF
    with rio.open(output_path, 'w', **profile) as dst:
        dst.write(rgb_data)


if __name__ == '__main__':
    cwd = Path.cwd()
    write_gtiff(cwd / 'velocity.h5', cwd / 'velocity.tif')
    reproject_geotiff(cwd / 'velocity.tif', cwd / 'velocity_geo.tif', 32615, 4326)
    single_band_to_rgb(cwd / 'velocity_geo.tif', cwd / 'velocity_visual.tif')
