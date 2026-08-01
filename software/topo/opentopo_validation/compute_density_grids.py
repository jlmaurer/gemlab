"""Bin all delivered point clouds into per-site point-density grids for Fig. 5.

Counts all returns (the convention the OpenTopography portal uses for its
reported point densities) into 10 m cells; writes one npz per site.
Run with the `opentopo` env python (laspy + LAZ backends).
"""
import glob
import os
import sys
import time

import laspy
import numpy as np

BASE = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
        "My Drive/Guatemala/Spring_Campaign/OpenTopography_upload")
OUTDIR = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
          "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
          "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/density")
CELL = 10.0

SITES = ["La_Laguna", "Rio_Tambor", "Gualan", "Mellon_Farm", "Carillabas",
         "Finca_del_Eden", "La_Tinta", "Military_Base", "Quirigua_Museo",
         "Byrons_Ranch"]

os.makedirs(OUTDIR, exist_ok=True)

for site in SITES:
    out = f"{OUTDIR}/{site}.npz"
    if os.path.exists(out):
        print(f"{site}: exists, skipping", flush=True)
        continue
    files = sorted(glob.glob(f"{BASE}/{site}/*.laz"))
    if not files:
        print(f"{site}: no LAZ found", flush=True)
        continue

    # common grid from headers
    x0 = min(laspy.open(f).header.x_min for f in files)
    x1 = max(laspy.open(f).header.x_max for f in files)
    y0 = min(laspy.open(f).header.y_min for f in files)
    y1 = max(laspy.open(f).header.y_max for f in files)
    nx = int(np.ceil((x1 - x0) / CELL)) + 1
    ny = int(np.ceil((y1 - y0) / CELL)) + 1
    counts = np.zeros((ny, nx), dtype=np.int64)

    t0 = time.time()
    total = 0
    for f in files:
        with laspy.open(f) as r:
            for pts in r.chunk_iterator(20_000_000):
                ix = ((pts.x - x0) / CELL).astype(np.int32)
                iy = ((pts.y - y0) / CELL).astype(np.int32)
                np.add.at(counts, (iy, ix), 1)
                total += len(ix)
    np.savez_compressed(out, counts=counts, extent=np.array([x0, x0 + nx * CELL,
                                                             y0, y0 + ny * CELL]),
                        cell=CELL, total=total)
    print(f"{site}: {total/1e6:.1f} Mpts, grid {ny}x{nx}, "
          f"{time.time()-t0:.0f} s", flush=True)

print("DONE", flush=True)
