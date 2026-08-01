#!/usr/bin/env python
"""Build the merged 0.5 m Gualan DTM from ground returns of all three flights.

Reads the two original LAS files directly (both are cached locally) and applies
the co-registration shift to YS-211849 on the fly, so the DTM does not depend on
the LAZ products having been written yet.

Cells hold the mean Z of class-2 returns. No interpolation across voids.
"""
import sys
import time

import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin

SRC = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/My Drive/"
       "Guatemala/Spring_Campaign/SITES/Gualan/Updated_data")
EXPORT = f"{SRC}/export/Gualan.las"
YS = f"{SRC}/YS-20240123-211849-20240207-082517-F001.las"
DX, DY, DZ = -4.460, -0.920, -13.307

RES = 0.5
NODATA = -99999.0
CHUNK = 20_000_000

# union of the export extent and the shifted YS extent, snapped out to 0.5 m
MINX, MAXX = 248044.0, 251754.0
MINY, MAXY = 1672317.0, 1675507.0


def accumulate(path, ssum, cnt, nx, ny, shift):
    dx, dy, dz = shift
    t0 = time.time()
    n = 0
    with laspy.open(path) as f:
        for pts in f.chunk_iterator(CHUNK):
            n += len(pts)
            g = np.asarray(pts.classification) == 2
            if not g.any():
                continue
            x = np.asarray(pts.x)[g] + dx
            y = np.asarray(pts.y)[g] + dy
            z = np.asarray(pts.z)[g] + dz
            col = np.floor((x - MINX) / RES).astype(np.int64)
            row = np.floor((MAXY - y) / RES).astype(np.int64)
            ok = (col >= 0) & (col < nx) & (row >= 0) & (row < ny)
            idx = row[ok] * nx + col[ok]
            np.add.at(ssum.reshape(-1), idx, z[ok])
            np.add.at(cnt.reshape(-1), idx, 1)
    print(f"    {path.split('/')[-1]}: {n:,} pts in {time.time() - t0:.0f}s", flush=True)


def main(out_tif):
    nx = int(round((MAXX - MINX) / RES))
    ny = int(round((MAXY - MINY) / RES))
    print(f"[dtm] grid {ny} x {nx} @ {RES} m", flush=True)
    ssum = np.zeros((ny, nx), dtype=np.float64)
    cnt = np.zeros((ny, nx), dtype=np.int64)

    accumulate(EXPORT, ssum, cnt, nx, ny, (0.0, 0.0, 0.0))
    accumulate(YS, ssum, cnt, nx, ny, (DX, DY, DZ))

    dem = np.full((ny, nx), NODATA, dtype=np.float32)
    nz = cnt > 0
    dem[nz] = (ssum[nz] / cnt[nz]).astype(np.float32)
    print(f"[dtm] {nz.sum():,} populated cells of {ny*nx:,} ({100*nz.mean():.1f}% of bbox)",
          flush=True)
    v = dem[nz]
    print(f"[dtm] Z {v.min():.2f} .. {v.max():.2f} m", flush=True)

    prof = dict(driver="GTiff", height=ny, width=nx, count=1, dtype="float32",
                crs="EPSG:32616", transform=from_origin(MINX, MAXY, RES, RES),
                nodata=NODATA, compress="deflate", tiled=True,
                blockxsize=512, blockysize=512)
    with rasterio.open(out_tif, "w", **prof) as ds:
        ds.write(dem, 1)
    print(f"[dtm] wrote {out_tif}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
