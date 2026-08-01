#!/usr/bin/env python
"""Grid class-2 (ground) returns of a LAS file to a mean-Z raster on a fixed grid.

Exact per-cell binning (a point contributes to the one cell that contains it),
done in numpy over chunked laspy reads -- PDAL's writers.gdal always smears each
point over every cell centre within `radius`, which we do not want here.

Writes <outstem>.tif (mean ground Z, nodata -9999) and <outstem>_count.tif.
"""
import sys
import time

import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin

# Overlap window of YS-211849 and export/Gualan, snapped to whole metres.
MINX, MAXX = 248163.0, 250644.0
MINY, MAXY = 1672912.0, 1674898.0
RES = 1.0
NODATA = -9999.0
CHUNK = 20_000_000


def main(infile, outstem, res=RES):
    nx = int(round((MAXX - MINX) / res))
    ny = int(round((MAXY - MINY) / res))
    ssum = np.zeros((ny, nx), dtype=np.float64)
    cnt = np.zeros((ny, nx), dtype=np.int64)

    t0 = time.time()
    total = kept = 0
    with laspy.open(infile) as f:
        print(f"[grid] {infile}\n[grid] {f.header.point_count:,} pts -> {ny}x{nx} @ {res} m", flush=True)
        for pts in f.chunk_iterator(CHUNK):
            total += len(pts)
            g = np.asarray(pts.classification) == 2
            if not g.any():
                continue
            x = np.asarray(pts.x)[g]
            y = np.asarray(pts.y)[g]
            z = np.asarray(pts.z)[g]
            col = np.floor((x - MINX) / res).astype(np.int64)
            row = np.floor((MAXY - y) / res).astype(np.int64)
            ok = (col >= 0) & (col < nx) & (row >= 0) & (row < ny)
            if not ok.any():
                continue
            idx = row[ok] * nx + col[ok]
            zz = z[ok]
            kept += idx.size
            np.add.at(ssum.reshape(-1), idx, zz)
            np.add.at(cnt.reshape(-1), idx, 1)
            print(f"    {total:,} read, {kept:,} binned, {time.time() - t0:.0f}s", flush=True)

    mean = np.full((ny, nx), NODATA, dtype=np.float32)
    nz = cnt > 0
    mean[nz] = (ssum[nz] / cnt[nz]).astype(np.float32)
    print(f"[grid] {nz.sum():,} populated cells of {ny * nx:,} ({100 * nz.mean():.1f}%)", flush=True)

    tr = from_origin(MINX, MAXY, res, res)
    prof = dict(driver="GTiff", height=ny, width=nx, count=1, crs="EPSG:32616",
                transform=tr, compress="deflate", tiled=True)
    with rasterio.open(f"{outstem}.tif", "w", dtype="float32", nodata=NODATA, **prof) as ds:
        ds.write(mean, 1)
    with rasterio.open(f"{outstem}_count.tif", "w", dtype="int32", nodata=0, **prof) as ds:
        ds.write(cnt.astype(np.int32), 1)
    print(f"[grid] wrote {outstem}.tif in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
