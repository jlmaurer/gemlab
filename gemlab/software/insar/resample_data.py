import argparse
import concurrent.futures
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import rasterio as rio
from rasterio import mask as riom
from rasterio import warp as rio_warp
from tqdm import tqdm


# import math
# import rioxarray as riox
# from matplotlib import pyplot as plt
# from rasterio import windows as rio_windows


def main(shapefile_path: Path, ref_file: int = 100, data_dir: Path = Path.cwd(), out_dir: Path = Path.cwd()) -> None:
    """Resamples a set of raster to have the same bounds"""
    unw_paths = list(data_dir.glob('**/*unw_phase.tif'))
    path_groups: list[list[Path]] = [
        unw_paths,
        list(data_dir.glob('**/*amp.tif')),
        list(data_dir.glob('**/*wrapped_phase.tif')),
        list(data_dir.glob('**/*corr.tif')),
        list(data_dir.glob('**/*dem.tif')),
        list(data_dir.glob('**/*lv_theta.tif')),
        list(data_dir.glob('**/*lv_phi.tif')),
        list(data_dir.glob('**/*inc_map.tif')),
        list(data_dir.glob('**/*inc_map_ell.tif')),
        list(data_dir.glob('**/*water_mask.tif')),
        list(data_dir.glob('**/*vert_disp.tif')),
        list(data_dir.glob('**/*los_disp.tif')),
    ]

    # Get basic info from the reference file
    with rio.open(unw_paths[ref_file]) as r_int:
        r_int.crs.to_epsg()
        crs = r_int.crs
        xres = r_int.transform[0]
        yres = r_int.transform[4]

    # get the transform
    shape = gpd.read_file(shapefile_path)
    if shape.crs != crs:
        shape = shape.to_crs(crs)
    w, s, e, n = shape.total_bounds

    # Create the transform and dimensions for the destination raster
    dst_transform = rio.Affine(xres, 0.0, w, 0.0, yres, n)
    dst_width = int((e - w) / xres)
    dst_height = int((n - s) / -yres)
    transform_kwargs = {
        'transform': dst_transform,
        'width': dst_width,
        'height': dst_height,
        'crs': crs,
        'bounds': shape.total_bounds,
        'proj': shape,
        'out_dir': out_dir,
    }

    with (
        tqdm(total=len(path_groups) * len(unw_paths)) as pbar,
        concurrent.futures.ThreadPoolExecutor() as executor
    ):
        futures: list[concurrent.futures.Future] = []
        for unw_path in unw_paths:
            for path_group in path_groups:
                futures.append(
                    executor.submit(
                        transform_from_group_with_shapefile,
                        path_group, unw_path, transform_kwargs
                    )
                )
        for _ in concurrent.futures.as_completed(futures):
            pbar.update(1)


# def update_file(orig_path: Path | None, ref_path: Path) -> None:
#     if orig_path is None:
#         return

#     src = riox.open_rasterio(orig_path)
#     ref = riox.open_rasterio(ref_path)
#     assert not isinstance(src, list)
#     assert not isinstance(ref, list)
#     if src.shape != ref.shape:
#         ds_out = src.interp_like(ref)
#         del src
#         ds_out.rio.to_raster(orig_path)


def transform_from_group_with_shapefile(
    path_group: list[Path],
    unw_path: Path,
    transform_kwargs: dict[str, Any],
) -> None:
    path = find_matching_file(path_group, unw_path)
    assert path is not None
    transform_with_shapefile(path, **transform_kwargs)


def find_matching_file(haystack: Iterable[Path], needle: Path) -> Path | None:
    # format: S1AA_20200920T001203_20201002T001203_***
    needle_parts = needle.name.split('_')
    for candidate in haystack:
        candidate_parts = candidate.name.split('_')
        if (
            needle_parts[1] == candidate_parts[1]
            and needle_parts[2] == candidate_parts[2]
            and needle_parts[7] == candidate_parts[7]
        ):
            return candidate
    return None


# def plot_extents(data_dir: Path) -> None:
#     unw_paths = data_dir.glob('*/*unw_phase.tif')
#     ns_bounds = []
#     for path in unw_paths:
#         with rio.open(path) as f:
#             ns_bounds.append(f.bounds[:2])

#     de = np.array(ns_bounds).mean(axis=0)

#     for k, pair in enumerate(ns_bounds):
#         plt.plot([k, k], [pair[0] - de[0], pair[1] - de[1]], '-k')
#     plt.ylim([de[0] - 100, de[1] + 100])

#     plt.savefig('Network_extents.png')
#     plt.close('all')


# def snap(window: rio_windows.Window) -> rio_windows.Window:
#     """Handle rasterio's floating point precision (sub pixel) windows"""
#     # Adding the offset differences to the dimensions will handle case where width/heights can 1 pixel too small
#     # after the offsets are shifted.
#     # This ensures pixel contains the bounds that were originally passed to rio_windows.from_bounds()
#     col_off, row_off = math.floor(window.col_off), math.floor(window.row_off)
#     col_diff, row_diff = window.col_off - col_off, window.row_off - row_off
#     width, height = math.ceil(window.width + col_diff), math.ceil(window.height + row_diff)

#     return rio_windows.Window(col_off=col_off, row_off=row_off, width=width, height=height)  # type: ignore


# def expand_extent(raster, extent_bbox: WSEN, fill_value: Any | None = None) -> tuple[Any, rio.Affine]:
#     window = snap(rio_windows.from_bounds(*extent_bbox, raster.transform))
#     data = raster.read(window=window, boundless=True, fill_value=fill_value)
#     return data, rio_windows.transform(window, raster.transform)


def save_raster_with_transform(
    data: np.ndarray | rio.Band,
    path: Path,
    src_transform: rio.Affine | None,
    dst_transform: rio.Affine | None,
    src_crs: rio.CRS | str = '',
    dst_crs: rio.CRS | str = '',
    driver_name: str = 'GTiff',
    epsg: int | str = '',
    dtype: str = rio.float32,
    num_bands: int = 1,
    dst_height: int | None = None,
    dst_width: int | None = None,
    ndv: float = 0.0,
) -> None:
    # get default file size
    if dst_height is None:
        dst_height, dst_width = data.shape

    # data_new=np.reshape(data,(bands,data.shape[0],data.shape[1]))
    if src_crs != '':
        try:
            src_crs = rio.CRS.from_proj4(src_crs)
        except TypeError:
            src_crs = src_crs
    elif epsg != '':
        src_crs = rio.CRS.from_epsg(epsg)
    else:
        src_crs = rio.CRS.from_epsg('4326')

    with rio.open(
        path,
        'w',
        driver=driver_name,
        height=dst_height,
        width=dst_width,
        count=num_bands,
        dtype=dtype,
        crs=src_crs,
        transform=dst_transform,
    ) as dst:
        rio_warp.reproject(
            source=data,
            destination=rio.band(dst, 1),
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=rio_warp.Resampling.nearest,  # Or other resampling method if needed
        )
        # dst.write(np.array(data,datatype),bands)


def transform_with_shapefile(
    raster_path: Path,
    *,
    transform: rio.Affine | None,
    crs: rio.CRS | str,
    width: int | None,
    height: int | None,
    proj: gpd.GeoDataFrame,
    out_dir: Path = Path.cwd(),
) -> None:
    """
    Function to transform a raster to match the bounds of a shapefile
    """
    # during first iteration of loop, reproject shapefile to same projection as interferograms
    try:
        with rio.open(raster_path) as r_int:
            int_mask, out_transform = riom.mask(r_int, proj['geometry'], crop=True)
            r_crs = r_int.crs
            src_transform = r_int.transform

        # Create the new file
        save_raster_with_transform(
            np.squeeze(int_mask),
            out_dir / raster_path.with_name(raster_path.stem + '_int.tif'),
            src_transform,
            transform,
            src_crs=crs,
            dst_crs=r_crs,
            dst_width=width,
            dst_height=height,
        )
    except ValueError:
        # if the raster does not overlap, just skip it
        return


# def transform_all_files(shapefile_path: Path, in_dir: Path=Path.cwd(), out_dir: Path=Path.cwd()) -> None:
#     # get list of interferograms
#     unwrapped_file_paths = list(in_dir.glob('*/*unw_phase.tif'))
#     coh_paths = list(in_dir.glob('*/*corr.tif'))

#     # get the transform
#     shp = gpd.read_file(shapefile_path)
#     with rio.open(unwrapped_file_paths[0]) as r_int:
#         with rio.open(coh_paths[0]):
#             shp_proj = shp.to_crs(r_int.crs)
#             crs = r_int.crs

#     # loop through all interferograms and coherence rasters, clip to area of interest
#     print('clipping files')
#     for i, path in enumerate(unwrapped_file_paths):
#         print(f'{i + 1} out of {len(unwrapped_file_paths)}')
#         transform_with_shapefile(path, coh_paths[i], proj=shp_proj, crs=crs, out_dir=out_dir)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--shapefile-path', type=lambda s: Path(s).absolute())
    p.add_argument('--ref-file', type=int, default=100)
    p.add_argument('--data-dir', type=lambda s: Path(s).absolute(), default='')
    p.add_argument('--out-dir', type=lambda s: Path(s).absolute(), default='')
    args = p.parse_args()
    main(**args.__dict__)
