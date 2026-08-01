#!/usr/bin/env python
"""Resample an existing DTM onto the 1 m co-registration grid.

Used to bring Results-DEMs/Gualan/merged_Gualan.tif (the DTM built from the two
good flights during the ORIGINAL processing) onto the same grid as the ground
rasters, so it can serve as an independent reference.
"""
import sys

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject

import grid_ground as gg

NODATA = -9999.0


def main(src_tif, out_stem):
    nx = int(round((gg.MAXX - gg.MINX) / gg.RES))
    ny = int(round((gg.MAXY - gg.MINY) / gg.RES))
    dst_tr = from_origin(gg.MINX, gg.MAXY, gg.RES, gg.RES)
    dst = np.full((ny, nx), np.nan, dtype=np.float64)

    with rasterio.open(src_tif) as ds:
        print(f"[resample] {src_tif}\n  {ds.width}x{ds.height} res {ds.transform.a} "
              f"nodata {ds.nodata} crs {ds.crs.to_string()}")
        a = ds.read(1).astype(np.float64)
        if ds.nodata is not None:
            a[a == ds.nodata] = np.nan
        # the per-flight DTMs were written with nodata undefined; -99999 and
        # extreme values are still sentinels in practice
        a[a < -1000] = np.nan
        reproject(a, dst, src_transform=ds.transform, src_crs=ds.crs,
                  dst_transform=dst_tr, dst_crs=ds.crs,
                  src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=Resampling.bilinear)

    ok = np.isfinite(dst)
    print(f"[resample] {ok.sum():,} valid cells of {dst.size:,} ({100 * ok.mean():.1f}%)")
    out = np.where(ok, dst, NODATA).astype(np.float32)
    cnt = np.where(ok, 99, 0).astype(np.int32)  # synthetic count: DTM has no point counts

    prof = dict(driver="GTiff", height=ny, width=nx, count=1, crs="EPSG:32616",
                transform=dst_tr, compress="deflate", tiled=True)
    with rasterio.open(f"{out_stem}.tif", "w", dtype="float32", nodata=NODATA, **prof) as d:
        d.write(out, 1)
    with rasterio.open(f"{out_stem}_count.tif", "w", dtype="int32", nodata=0, **prof) as d:
        d.write(cnt, 1)
    print(f"[resample] wrote {out_stem}.tif")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
