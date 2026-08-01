#!/usr/bin/env python
"""End-to-end check of the delivered Gualan LAZ files.

Re-grids the written products themselves (not the solved shift) and measures the
residual between the aligned flight 211849 and each of the two trusted flights.
Also confirms counts, CRS, and that point_source_ids no longer collide.
"""
import json
import subprocess
import sys

import laspy
import numpy as np

sys.path.insert(0, "/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/db3b07b4-fdbc-4d8c-bfa1-1a844edbe582/scratchpad/coreg")
from coreg import nmad  # noqa: E402

PDAL = "/Users/jlmd9g/software/miniforge3/envs/opentopo/bin/pdal"
U = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/My Drive/"
     "Guatemala/Spring_Campaign/OpenTopography_upload/Gualan")
FILES = {
    "204440": f"{U}/gualan_lidar_pointcloud_20240123-204440.laz",
    "220238": f"{U}/gualan_lidar_pointcloud_20240123-220238.laz",
    "211849": f"{U}/gualan_lidar_pointcloud_20240123-211849_aligned.laz",
}

MINX, MAXX = 248044.0, 251754.0
MINY, MAXY = 1672317.0, 1675507.0
RES = 1.0


def grid(path):
    nx = int(round((MAXX - MINX) / RES))
    ny = int(round((MAXY - MINY) / RES))
    ssum = np.zeros(ny * nx)
    cnt = np.zeros(ny * nx, dtype=np.int64)
    psids = set()
    n = 0
    with laspy.open(path) as f:
        for pts in f.chunk_iterator(20_000_000):
            n += len(pts)
            psids.update(np.unique(np.asarray(pts.point_source_id)).tolist())
            g = np.asarray(pts.classification) == 2
            if not g.any():
                continue
            x, y, z = (np.asarray(pts.x)[g], np.asarray(pts.y)[g], np.asarray(pts.z)[g])
            col = np.floor((x - MINX) / RES).astype(np.int64)
            row = np.floor((MAXY - y) / RES).astype(np.int64)
            ok = (col >= 0) & (col < nx) & (row >= 0) & (row < ny)
            idx = row[ok] * nx + col[ok]
            np.add.at(ssum, idx, z[ok])
            np.add.at(cnt, idx, 1)
    m = cnt > 0
    out = np.full(ny * nx, np.nan)
    out[m] = ssum[m] / cnt[m]
    return out.reshape(ny, nx), cnt.reshape(ny, nx), n, sorted(psids)


def main():
    info = {}
    grids = {}
    for k, p in FILES.items():
        g, c, n, ps = grid(p)
        grids[k] = (g, c)
        meta = json.loads(subprocess.run(
            [PDAL, "info", "--metadata", p], capture_output=True, text=True).stdout)["metadata"]
        srs = meta.get("srs", {})
        info[k] = dict(points=n, psids=(min(ps), max(ps)), npsid=len(ps),
                       has3d="ellipsoidal height" in srs.get("wkt", ""),
                       vert=srs.get("vertical", "")[:40],
                       ver=f"{meta['major_version']}.{meta['minor_version']}",
                       fmt=meta["dataformat_id"],
                       z=(meta["minz"], meta["maxz"]))
        print(f"{k}: {n:,} pts | psid {min(ps)}-{max(ps)} ({len(ps)} strips) | "
              f"LAS {info[k]['ver']} fmt {meta['dataformat_id']} | 3D CRS {info[k]['has3d']} | "
              f"Z {meta['minz']:.2f}..{meta['maxz']:.2f}")

    allp = []
    for k in FILES:
        allp += list(range(info[k]["psids"][0], info[k]["psids"][1] + 1))
    print(f"\npoint_source_id collision across files: "
          f"{'YES' if len(allp) != len(set(allp)) else 'NO'}")
    print(f"total points: {sum(i['points'] for i in info.values()):,}")

    print("\n--- ground-surface residuals between delivered products (1 m cells) ---")
    print(f"{'pair':<22}{'cells':>10}{'median cm':>12}{'NMAD cm':>10}{'RMSE cm':>10}")
    res = {}
    for a, b in [("211849", "204440"), ("211849", "220238"), ("204440", "220238")]:
        ga, ca = grids[a]
        gb, cb = grids[b]
        m = np.isfinite(ga) & np.isfinite(gb) & (ca >= 3) & (cb >= 3)
        if m.sum() < 100:
            print(f"{a} vs {b:<12}{m.sum():>10}   (no usable overlap)")
            continue
        d = (ga[m] - gb[m])
        res[f"{a}_vs_{b}"] = dict(n=int(m.sum()), median=float(np.median(d)),
                                  nmad=float(nmad(d)), rmse=float(np.sqrt(np.mean(d ** 2))))
        print(f"{a} vs {b:<12}{m.sum():>10,}{np.median(d)*100:>12.2f}"
              f"{nmad(d)*100:>10.2f}{np.sqrt(np.mean(d**2))*100:>10.2f}")

    with open("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/db3b07b4-fdbc-4d8c-bfa1-1a844edbe582/scratchpad/coreg/verify_products.json", "w") as fh:
        json.dump(dict(files=info, residuals=res), fh, indent=2, default=str)


if __name__ == "__main__":
    main()
