import datetime as dt
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from osgeo import gdal

from gemlab.types import FloatArray1D, FloatArray2D, FloatArray3D, Transform


def main(
    ifg_paths: list[Path],
    ref_center: tuple[int, int] | None = None,
    ref_size: int | None = None,
) -> None:
    """
    Read in a list of interferograms and create a time-series and velocity map.
    """
    date_pairs, unique_dates = get_dates(ifg_paths)
    year_fracs: FloatArray1D = np.array([get_year_frac(d) for d in unique_dates])
    g_matrix = make_g_matrix(date_pairs, unique_dates)
    ifgs = get_data(ifg_paths, band_num=1)
    dereference(ifgs, ref_center=ref_center, ref_size=ref_size)
    ts_array = make_ts(g_matrix, ifgs)
    vel = find_mean_vel(ts_array, year_fracs)
    radians_to_meters(vel)
    write_ts_to_hdf5(ts_array, year_fracs, vel, Path.cwd())


def get_dates(
    ifg_paths: list[Path],
) -> tuple[list[tuple[dt.date, dt.date]], list[dt.date]]:
    """Read the dates from a list of interferogram filenames.
    
    Returns a list of date pairs parsed from the filenames, and a version of
    the list with no duplicates.
    """
    date_pairs: list[tuple[dt.date, dt.date]] = []
    unique_dates: set[dt.date] = set()

    for path in ifg_paths:
        # Get the date/time range from the ifg filename
        result = re.search(r'\d{8}T*\d*_\d{8}T*\d*', str(path))
        if result is None:
            raise ValueError(f'Invalid ifg path {path}')

        # Separate the two date/times out
        ds1, ds2 = result.group().split('_')

        # Remove the time information
        d1 = dt.datetime.strptime(re.sub(r'T\d{6}', '', ds1), '%Y%m%d').date()
        d2 = dt.datetime.strptime(re.sub(r'T\d{6}', '', ds2), '%Y%m%d').date()

        unique_dates.add(d1)
        unique_dates.add(d2)
        date_pairs.append((d1, d2))

    return date_pairs, sorted(unique_dates)


def timestamp(date: dt.date) -> float:
    """Seconds since the Unix Epoch for a dt.date."""
    return time.mktime(date.timetuple())


def get_year_frac(date: dt.date) -> float:
    """The year + the proportion the date is through the year.

    Example:
    >>> get_year_frac(dt.date(year=2025, month=7, day=11))
    2025.5231735159816
    """
    start_of_this_year = dt.date(year=date.year, month=1, day=1)
    start_of_next_year = dt.date(year=date.year + 1, month=1, day=1)

    seconds_elapsed = timestamp(date) - timestamp(start_of_this_year)
    seconds_in_this_year = (
        timestamp(start_of_next_year) - timestamp(start_of_this_year)
    )
    fraction = seconds_elapsed / seconds_in_this_year
    year_frac = date.year + fraction

    return year_frac


def make_g_matrix(
    date_pairs: Sequence[tuple[dt.date, dt.date]],
    unique_dates: Sequence[dt.date],
) -> FloatArray2D:
    """Create a time-series G-matrix.
    
    @pre: unique_dates must be sorted and in ascending order.
    """
    dates_arr = np.array(unique_dates)
    g_matrix = np.zeros((len(date_pairs), len(dates_arr)))
    for k, (d1, d2) in enumerate(date_pairs):
        index1 = dates_arr == d1
        index2 = dates_arr == d2
        g_matrix[k, index1] = -1
        g_matrix[k, index2] = 1
    return g_matrix


def read_ifg(
    ifg: Path,
    *,
    band_num: int = 1,
    x_start: float = 0,
    y_start: float = 0,
    x_size: float | None = None,
    y_size: float | None = None,
) -> FloatArray2D:
    ds: gdal.Dataset | None = gdal.Open(ifg)
    assert ds is not None
    return (
        ds.GetRasterBand(band_num).ReadAsArray(x_start, y_start, x_size, y_size)
    )


def get_raster_metadata(
    path: Path,
    *,
    band_num: int | None = None,
) -> tuple[int, int, Any, str, Transform, float, int]:
    """Get the attributes of a GDAL VRT file"""
    try:
        ds: gdal.Dataset | None = gdal.Open(str(path), gdal.GA_ReadOnly)
        if ds is None:
            raise RuntimeError(f'cannot find file {path}')
    except Exception as e:
        print(e)
        raise RuntimeError(f'cannot find file {path}')

    x_size: int = ds.RasterXSize
    y_size: int = ds.RasterYSize
    geo_proj: str = ds.GetProjection()
    transform: Transform = ds.GetGeoTransform()

    if x_size == 0:
        raise RuntimeError('raster X size is zero, cannot continue')
    if y_size == 0:
        raise RuntimeError('raster Y size is zero, cannot continue')

    band_count: int = ds.RasterCount
    if band_num is None:
        band_num = 1
        print('Using band one for data type')

    data_type: Any = ds.GetRasterBand(band_num).DataType
    nodata_val: float = ds.GetRasterBand(band_num).GetNoDataValue()

    return (
        x_size, y_size, data_type, geo_proj, transform, nodata_val, band_count
    )


def get_data(ifg_paths: list[Path], *, band_num: int) -> FloatArray3D:
    """Read one band from a list of interferograms into a 3D array.
    
    axis 0: interferogram index
    axis 1: band row index
    axis 2: band column index

    @pre: all interferograms must be the same shape/resolution. This is NOT
          automatically the case with data received from ASF Data Search. Use
          resample_data.py to fit interferograms to one shape.
    """
    last = read_ifg(ifg_paths.pop(), band_num=band_num)
    # Read one outside of the loop in order to calculate the output array's size
    ifgs: FloatArray3D = np.zeros((len(ifg_paths), *last.shape))
    ifgs[-1] = last
    for k, ifg in enumerate(ifg_paths):
        ifgs[k] = read_ifg(ifg, band_num=band_num)
    return ifgs


def dereference(
    ifgs: FloatArray3D,
    *,
    ref_center: tuple[int, int] | None = None,
    ref_size: int | None = None,
) -> None:
    """Normalize a set of interferogram rasters with respect to a reference region.
    
    Offsets the values of each interferogram downward to set "0" as relative
    to a reference region, the expectation being the region you pick be one
    where you know no deformation has occurred.

    (0, 0) is the top-left/north-west corner of the rasters.  
    +X is right/east, Y+ is down/south.

    Modifies the `ifgs` array in-place.
    """
    if ref_center is None:
        ifg_shape = ifgs.shape[1:]
        ref_center = (ifg_shape[0] // 2, ifg_shape[1] // 2)
        print(
            'No reference region center provided; '
            f'defaulting to the center of the image: {ref_center[0]}/{ref_center[1]}'
        )
    if ref_size is None:
        ref_size = 10
        print(f'No reference region size provided; defaulting to {ref_size} sq. pixels')

    s, n, w, e = (
        ref_center[0] - ref_size // 2,
        ref_center[0] + ref_size // 2,
        ref_center[1] - ref_size // 2,
        ref_center[1] + ref_size // 2,
    )
    for k in range(len(ifgs)):
        ifgs[k] -= np.nanmean(
            ifgs[k, list(range(row1, row2)), list(range(col1, col2))]
        )


def make_ts(g_matrix: FloatArray2D, ifgs: FloatArray3D) -> FloatArray3D:
    ifg_shape = ifgs.shape[1:]
    ifg_count = ifgs.shape[0]
    flat_array: FloatArray2D = ifgs.reshape((ifg_count, np.prod(ifg_shape)))

    d_hat, res, rank, s = np.linalg.lstsq(g_matrix, flat_array, rcond=None)
    ts_count = g_matrix.shape[-1]
    ts = d_hat.reshape((ts_count, *ifg_shape))
    return ts


def find_mean_vel(ts_array: FloatArray3D, year_fracs: FloatArray1D) -> FloatArray2D:
    ts_shape = ts_array.shape[1:]
    ts_count = ts_array.shape[0]
    flat_array: FloatArray2D = ts_array.reshape((ts_count, np.prod(ts_shape)))

    NUM_VARIABLES = 2
    g_matrix = np.ones((ts_count, NUM_VARIABLES))
    g_matrix[:, 1] = year_fracs - year_fracs[0]

    d_hat, res, rank, s = np.linalg.lstsq(g_matrix, flat_array, rcond=None)
    vel = d_hat.reshape((NUM_VARIABLES, *ts_shape))
    return vel[1, ...]


def radians_to_meters(vel: np.ndarray, *, wavelength_m: float = 0.056) -> None:
    """Modifies in place"""
    vel /= (4 * np.pi / wavelength_m)


def write_ts_to_hdf5(
    ts_array: FloatArray3D,
    year_fracs: FloatArray1D,
    vel: FloatArray2D,
    path: Path,
) -> None:
    with h5py.File(path, 'w') as fout:
        fout['ts'] = ts_array
        fout['dates'] = year_fracs
        fout['vel'] = vel
    print(f'Wrote {path} to disk')


# def gdal_open(
#     path: Path,
#     return_proj: bool = False,
#     user_ndv: float | None = None,
#     band_num: int | None = None,
# ) -> tuple[list | np.ndarray, dict[str, Any] | None]:
#     """
#     Reads a rasterio-compatible raster file and returns the data and profile
#     """
#     if path.with_suffix(path.name + '.vrt').exists():
#         path = path.with_suffix(path.name + '.vrt')

#     with rio.open(path) as src:
#         profile: dict[str, Any] = src.profile

#         # For all bands
#         ndvs: tuple[float, ...] = src.nodatavals

#         # If user requests a band
#         if band_num is not None:
#             data = cast(np.ndarray, src.read(band_num)).squeeze()
#             nodata_to_nan(data, (user_ndv, ndvs[band_num - 1]))

#         else:
#             data = cast(np.ndarray, src.read()).squeeze()
#             if data.ndim > 2:
#                 for bnd in range(data.shape[0]):
#                     val = data[bnd, ...]
#                     nodata_to_nan(val, (user_ndv, ndvs[bnd]))
#             else:
#                 nodata_to_nan(data, (user_ndv, *ndvs))

#         if data.ndim > 2:
#             dlist: list[np.ndarray] = []
#             for k in range(data.shape[0]):
#                 dlist.append(data[k, ...].copy())
#             data = dlist

#     if not return_proj:
#         return data, None

#     return data, profile


# def nodata_to_nan[T: np.floating](
#     array: np.ndarray[tuple[int, ...], np.dtype[T]],
#     ndvs: Iterable[T],
# ) -> None:
#     """Setting values to NaN as needed"""
#     array = array.astype(float)  # NaNs cannot be integers (i.e. in DEM)
#     for val in ndvs:
#         if val is not None:
#             array[array == val] = np.nan


# def get_ts_from_ifgs(i: float, j: float, ifg_path: Path, band_num: int = 1) -> FloatArray1D:
#     ds: gdal.Dataset | None = gdal.Open(str(ifg_path))
#     assert ds is not None
#     array = ds.GetRasterBand(band_num).ReadAsArray(i, j, 1, 1)
#     pixel: FloatArray1D = array[0, 0]
#     return pixel


if __name__ == '__main__':
    ifg_paths = list(Path.cwd().glob('*_unw.vrt'))
    main(ifg_paths)
