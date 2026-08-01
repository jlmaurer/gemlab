"""Extract the point cloud in a small neighbourhood of each GNSS base station.

Two purposes:
  1. a ground elevation taken straight from the ground-classified returns
     (independent of the delivered DTM, and available where the DTM has a gap);
  2. a look at whether the lidar imaged the tripod/antenna itself -- if it did,
     the top of that structure is a genuine control target.
Writes one npz of raw points per base station. Run with the `opentopo` env python.
"""
import glob
import os
import re
import time

import laspy
import numpy as np
from pyproj import Transformer

BASE = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
        "My Drive/Guatemala/Spring_Campaign/OpenTopography_upload")
OUTDIR = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
          "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
          "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/basepts")
RADIUS = 15.0

SITES = {
    "La_Laguna": 32615,
    "Rio_Tambor": 32616,
    "Gualan": 32616,
    "Mellon_Farm": 32616,
    "Carillabas": 32616,
    "Finca_del_Eden": 32616,
    "La_Tinta": 32616,
    "Quirigua_Museo": 32616,
}

os.makedirs(OUTDIR, exist_ok=True)


def dms2deg(d, m, s):
    sign = -1.0 if d.strip().startswith("-") else 1.0
    return sign * (abs(float(d)) + float(m) / 60 + float(s) / 3600)


def parse_sum(path):
    out = {}
    for line in open(path, errors="replace"):
        f = line.split()
        if line.startswith("POS LAT"):
            out["lat"] = dms2deg(f[7], f[8], f[9])
        elif line.startswith("POS LON"):
            out["lon"] = dms2deg(f[7], f[8], f[9])
        elif line.startswith("POS HGT"):
            out["h"] = float(f[5])
    return out


for sdir, epsg in SITES.items():
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    targets = []
    for sumf in sorted(glob.glob(f"{BASE}/{sdir}/base_station_*/*.sum")):
        p = parse_sum(sumf)
        if "h" not in p:
            continue
        x, y = tr.transform(p["lon"], p["lat"])
        targets.append((os.path.basename(sumf)[:-4], x, y, p["h"]))
    if not targets:
        continue

    files = sorted(glob.glob(f"{BASE}/{sdir}/*.laz"))
    keep = {t[0]: [] for t in targets}
    t0 = time.time()
    for fp in files:
        fid = re.search(r"(\d{6})(?=[._]|_aligned|$)", os.path.basename(fp))
        with laspy.open(fp) as r:
            h = r.header
            # skip files whose extent cannot contain any target
            if not any(h.x_min - RADIUS <= x <= h.x_max + RADIUS and
                       h.y_min - RADIUS <= y <= h.y_max + RADIUS
                       for _, x, y, _ in targets):
                continue
            for pts in r.chunk_iterator(20_000_000):
                px = np.asarray(pts.x)
                py = np.asarray(pts.y)
                for bid, x, y, _ in targets:
                    m = (np.abs(px - x) <= RADIUS) & (np.abs(py - y) <= RADIUS)
                    if m.any():
                        keep[bid].append(np.column_stack([
                            px[m], py[m], np.asarray(pts.z)[m],
                            np.asarray(pts.classification)[m]]))

    for bid, x, y, hppp in targets:
        arr = np.vstack(keep[bid]) if keep[bid] else np.empty((0, 4))
        np.savez_compressed(f"{OUTDIR}/{sdir}__{bid}.npz", pts=arr,
                            meta=np.array([x, y, hppp]))
        print(f"{sdir}/{bid}: {len(arr)} pts within {RADIUS} m "
              f"({time.time()-t0:.0f} s)", flush=True)

print("DONE", flush=True)
