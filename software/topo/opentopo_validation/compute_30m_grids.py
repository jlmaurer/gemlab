"""Bin every delivered point cloud to 30 m cells for the Copernicus GLO-30 check.

GLO-30 is a DSM (TanDEM-X derived), so a bare-earth DTM is not the right thing to
difference against it. Per 30 m cell this stores enough to build both surfaces and
a canopy proxy:
    n_all, n_ground, sum_ground_z, max_z   (class 7 noise excluded throughout)
so that  ground = sum_ground/n_ground  (DTM proxy)
         max_z                          (DSM proxy)
         max_z - ground                 (vegetation/structure height proxy)
Run with the `opentopo` env python.
"""
import glob
import os
import time

import laspy
import numpy as np

BASE = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
        "My Drive/Guatemala/Spring_Campaign/OpenTopography_upload")
OUTDIR = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
          "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
          "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/grid30")
CELL = 30.0
NOISE = 7
GROUND = 2

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
        print(f"{site}: no LAZ", flush=True)
        continue

    x0 = min(laspy.open(f).header.x_min for f in files)
    x1 = max(laspy.open(f).header.x_max for f in files)
    y0 = min(laspy.open(f).header.y_min for f in files)
    y1 = max(laspy.open(f).header.y_max for f in files)
    nx = int(np.ceil((x1 - x0) / CELL)) + 1
    ny = int(np.ceil((y1 - y0) / CELL)) + 1

    n_all = np.zeros((ny, nx), np.int64)
    n_gnd = np.zeros((ny, nx), np.int64)
    s_gnd = np.zeros((ny, nx), np.float64)
    z_max = np.full((ny, nx), -np.inf)

    t0 = time.time()
    for fp in files:
        with laspy.open(fp) as r:
            for pts in r.chunk_iterator(20_000_000):
                cls = np.asarray(pts.classification)
                ok = cls != NOISE
                if not ok.any():
                    continue
                px = np.asarray(pts.x)[ok]
                py = np.asarray(pts.y)[ok]
                pz = np.asarray(pts.z)[ok]
                cls = cls[ok]
                ix = ((px - x0) / CELL).astype(np.int32)
                iy = ((py - y0) / CELL).astype(np.int32)
                np.add.at(n_all, (iy, ix), 1)
                np.maximum.at(z_max, (iy, ix), pz)
                g = cls == GROUND
                if g.any():
                    np.add.at(n_gnd, (iy[g], ix[g]), 1)
                    np.add.at(s_gnd, (iy[g], ix[g]), pz[g])

    z_max[~np.isfinite(z_max)] = np.nan
    np.savez_compressed(out, n_all=n_all, n_gnd=n_gnd, s_gnd=s_gnd,
                        z_max=z_max.astype(np.float32),
                        extent=np.array([x0, x0 + nx * CELL, y0, y0 + ny * CELL]),
                        cell=CELL)
    print(f"{site}: {ny}x{nx} cells, {time.time()-t0:.0f} s", flush=True)

print("DONE", flush=True)
