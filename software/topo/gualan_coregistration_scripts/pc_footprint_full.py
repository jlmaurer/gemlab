#!/usr/bin/env python
"""True point-cloud footprint area per site, from a full read of every delivered file.

Sampling was tried first and rejected: LAZ points are stored in acquisition order, so
any contiguous sample is spatially clustered and the measured area grows with sample
size instead of saturating. This reads every point.

Footprint = area of occupied cells on a regular grid. Cell size is a real choice --
too small and canopy gaps/scan-line spacing punch holes, too large and the edges
inflate -- so the area is reported at 5, 10 and 20 m. Carillabas has a published
OpenTopography footprint (5.56 km2), which calibrates the choice.
"""
import glob
import json
import os
import time

import laspy
import numpy as np

U = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/My Drive/"
     "Guatemala/Spring_Campaign/OpenTopography_upload")

SITES = [
    ("La Laguna", "La_Laguna"),
    ("Rio Tambor", "Rio_Tambor"),
    ("Gualan", "Gualan"),
    ("Mellon Farm", "Mellon_Farm"),
    ("Carillabas", "Carillabas"),
    ("Finca del Eden", "Finca_del_Eden"),
    ("La Tinta", "La_Tinta"),
    ("Military Base", "Military_Base"),
    ("Museo Quirigua", "Quirigua_Museo"),
    ("Byron's Ranch", "Byrons_Ranch"),
]
CELLS = [5.0, 10.0, 20.0]
CHUNK = 20_000_000


def main():
    results = {}
    for name, folder in SITES:
        files = sorted(glob.glob(f"{U}/{folder}/*.laz"))
        # site bounds from headers (cheap)
        lo = np.array([np.inf, np.inf])
        hi = np.array([-np.inf, -np.inf])
        npts = 0
        for f in files:
            with laspy.open(f) as fh:
                h = fh.header
                lo = np.minimum(lo, [h.mins[0], h.mins[1]])
                hi = np.maximum(hi, [h.maxs[0], h.maxs[1]])
                npts += h.point_count
        grids = {c: np.zeros((int((hi[1] - lo[1]) / c) + 2,
                              int((hi[0] - lo[0]) / c) + 2), dtype=bool) for c in CELLS}
        t0 = time.time()
        seen = 0
        for f in files:
            with laspy.open(f) as fh:
                for pts in fh.chunk_iterator(CHUNK):
                    x = np.asarray(pts.x)
                    y = np.asarray(pts.y)
                    seen += x.size
                    for c, g in grids.items():
                        g[((y - lo[1]) / c).astype(np.int64),
                          ((x - lo[0]) / c).astype(np.int64)] = True
        areas = {c: float(g.sum() * c * c) for c, g in grids.items()}
        results[name] = dict(points=npts, areas_km2={c: a / 1e6 for c, a in areas.items()},
                             files=len(files))
        print(f"{name:<16} " + "  ".join(f"{c:g}m {areas[c]/1e6:6.2f}" for c in CELLS)
              + f"  km2 | {npts:>13,} pts | {seen/1e6:.0f} M read in {time.time()-t0:.0f}s",
              flush=True)

    print()
    for c in CELLS:
        tot = sum(r["areas_km2"][c] for r in results.values())
        lid = tot - results["Byron's Ranch"]["areas_km2"][c]
        print(f"TOTAL @{c:g} m: {tot:6.2f} km2   (lidar only {lid:6.2f})")
    tot_n = sum(r["points"] for r in results.values())
    print(f"TOTAL points: {tot_n:,}")
    with open("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/db3b07b4-fdbc-4d8c-bfa1-1a844edbe582/scratchpad/coreg/pc_footprint_full.json", "w") as fh:
        json.dump(results, fh, indent=2)


if __name__ == "__main__":
    main()
