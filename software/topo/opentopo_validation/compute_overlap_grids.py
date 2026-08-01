"""Grid each Gualan / Rio Tambor flight separately for the Fig. 4 overlap analysis.

Per-flight bare-earth grids (ground-classified returns only, class 2) are binned
exactly in numpy on a shared per-site grid -- PDAL's writers.gdal smears points
across neighbouring cells, which would bias a flight-to-flight difference.
Run with the `opentopo` env python.
"""
import glob
import os
import re
import time
from collections import defaultdict

import laspy
import numpy as np

BASE = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
        "My Drive/Guatemala/Spring_Campaign/OpenTopography_upload")
OUTDIR = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
          "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
          "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/overlap")
CELL = 1.0
GROUND = 2

os.makedirs(OUTDIR, exist_ok=True)


def flight_id(path):
    """Flight timestamp shared by all tiles of one acquisition."""
    b = os.path.basename(path)
    m = re.search(r"(\d{8})-(\d{6})", b)
    if m:
        return m.group(2)
    m = re.search(r"pointcloud_(\d{6})", b)
    return m.group(1) if m else b


for site in ["Gualan", "Rio_Tambor"]:
    out = f"{OUTDIR}/{site}_flights.npz"
    if os.path.exists(out):
        print(f"{site}: exists, skipping", flush=True)
        continue

    groups = defaultdict(list)
    for f in sorted(glob.glob(f"{BASE}/{site}/*.laz")):
        groups[flight_id(f)].append(f)

    allf = [f for fs in groups.values() for f in fs]
    x0 = min(laspy.open(f).header.x_min for f in allf)
    x1 = max(laspy.open(f).header.x_max for f in allf)
    y0 = min(laspy.open(f).header.y_min for f in allf)
    y1 = max(laspy.open(f).header.y_max for f in allf)
    nx = int(np.ceil((x1 - x0) / CELL)) + 1
    ny = int(np.ceil((y1 - y0) / CELL)) + 1
    print(f"{site}: grid {ny} x {nx}, flights {sorted(groups)}", flush=True)

    store = {"extent": np.array([x0, x0 + nx * CELL, y0, y0 + ny * CELL]),
             "cell": CELL}
    for fid in sorted(groups):
        zsum = np.zeros((ny, nx), dtype=np.float64)
        zcnt = np.zeros((ny, nx), dtype=np.int32)
        t0 = time.time()
        n = 0
        for f in groups[fid]:
            with laspy.open(f) as r:
                for pts in r.chunk_iterator(20_000_000):
                    cls = np.asarray(pts.classification)
                    keep = cls == GROUND
                    if not keep.any():
                        continue
                    # np.asarray: laspy's scaled views don't dispatch np.add.at
                    ix = ((np.asarray(pts.x)[keep] - x0) / CELL).astype(np.int32)
                    iy = ((np.asarray(pts.y)[keep] - y0) / CELL).astype(np.int32)
                    np.add.at(zsum, (iy, ix), np.asarray(pts.z)[keep])
                    np.add.at(zcnt, (iy, ix), 1)
                    n += keep.sum()
        store[f"zsum_{fid}"] = zsum.astype(np.float32)
        store[f"zcnt_{fid}"] = zcnt
        print(f"  flight {fid}: {n/1e6:.1f} M ground pts, {time.time()-t0:.0f} s",
              flush=True)

    np.savez_compressed(out, **store)
    print(f"{site}: wrote {out}", flush=True)

print("DONE", flush=True)
