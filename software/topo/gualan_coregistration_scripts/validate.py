#!/usr/bin/env python
"""Validate the YS-211849 -> export/Gualan translation.

1. Solve the shift independently in spatial blocks. A true rigid translation gives
   the same answer everywhere; a spread means the offset is not a pure translation.
2. Fit a plane to the post-alignment residuals to expose any remaining tilt.
3. Report residual distribution and how it varies with slope.
4. Diagnose merged_Gualan.tif (ground surface or canopy?).
"""
import json
import sys

import numpy as np
import rasterio

sys.path.insert(0, "/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/db3b07b4-fdbc-4d8c-bfa1-1a844edbe582/scratchpad/coreg")
from coreg import bilinear, load, load_count, nmad, sample_shifted  # noqa: E402

S = "/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/db3b07b4-fdbc-4d8c-bfa1-1a844edbe582/scratchpad/coreg"


def solve_block(ref, src, rows, cols, ref_v, res, lo=-8.0, hi=8.0):
    best = (np.inf, 0.0, 0.0, 0.0)
    for step, span in [(1.0, None), (0.2, 6), (0.02, 6)]:
        if span is None:
            xs = np.arange(lo, hi + step / 2, step)
            ys = xs
        else:
            xs = np.arange(best[1] - span * step, best[1] + span * step + step / 2, step)
            ys = np.arange(best[2] - span * step, best[2] + span * step + step / 2, step)
        for dx in xs:
            for dy in ys:
                d = ref_v - sample_shifted(src, rows, cols, dx, dy, res)
                d = d[np.isfinite(d)]
                if d.size < 500:
                    continue
                med = np.median(d)
                s = nmad(d - med)
                if s < best[0]:
                    best = (s, float(dx), float(dy), float(med))
    return best


def main():
    ref, tr = load(f"{S}/export_ground.tif")
    src, _ = load(f"{S}/ys211849_ground.tif")
    rc = load_count(f"{S}/export_ground_count.tif")
    sc = load_count(f"{S}/ys211849_ground_count.tif")
    res = tr.a

    dzdy, dzdx = np.gradient(ref, res)
    dzdy = -dzdy
    slope = np.arctan(np.hypot(dzdx, dzdy))

    valid = np.isfinite(ref) & np.isfinite(src) & (rc >= 3) & (sc >= 3)
    fit = valid & (slope > np.deg2rad(3)) & (slope < np.deg2rad(45))

    with open(f"{S}/coreg_result.json") as fh:
        adopted = json.load(fh)["adopted"]
    DX, DY, DZ = adopted["dx"], adopted["dy"], adopted["dz"]
    print(f"adopted global shift: dx={DX:+.3f} dy={DY:+.3f} dz={DZ:+.3f}\n")

    # ---- 1. block-wise independent solutions ----
    ny, nx = ref.shape
    nb = 3
    print(f"--- independent solutions in {nb}x{nb} spatial blocks ---")
    print(f"{'block':<8}{'n':>9}{'dx':>9}{'dy':>9}{'dz':>10}{'NMAD':>9}")
    rows_b = np.linspace(0, ny, nb + 1).astype(int)
    cols_b = np.linspace(0, nx, nb + 1).astype(int)
    blocks = []
    for i in range(nb):
        for j in range(nb):
            m = np.zeros_like(fit)
            m[rows_b[i]:rows_b[i + 1], cols_b[j]:cols_b[j + 1]] = True
            m &= fit
            r, c = np.nonzero(m)
            if r.size < 5000:
                print(f"{i},{j:<6}{r.size:>9}   (too few cells)")
                continue
            b = solve_block(ref, src, r.astype(float), c.astype(float), ref[m], res)
            blocks.append(dict(block=f"{i},{j}", n=int(r.size), dx=b[1], dy=b[2],
                               dz=b[3], nmad=b[0]))
            print(f"{i},{j:<6}{r.size:>9}{b[1]:>9.2f}{b[2]:>9.2f}{b[3]:>10.3f}{b[0]:>9.3f}")
    if blocks:
        arr = np.array([[b["dx"], b["dy"], b["dz"]] for b in blocks])
        print(f"\nblock spread (std):  dx={arr[:,0].std():.3f}  dy={arr[:,1].std():.3f}  "
              f"dz={arr[:,2].std():.3f} m")
        print(f"block range:         dx={np.ptp(arr[:,0]):.3f}  dy={np.ptp(arr[:,1]):.3f}  "
              f"dz={np.ptp(arr[:,2]):.3f} m")

    # ---- 2. residual plane fit ----
    vr, vc = np.nonzero(valid)
    d = ref[valid] - (sample_shifted(src, vr.astype(float), vc.astype(float), DX, DY, res) + DZ)
    good = np.isfinite(d)
    # trim blunders (vegetation/water/edges) before the tilt fit
    m0, s0 = np.median(d[good]), nmad(d[good])
    keep = good & (np.abs(d - m0) < 5 * s0)
    X = (vc[keep] * res) / 1000.0   # km east of grid origin
    Y = (-vr[keep] * res) / 1000.0  # km north
    A = np.column_stack([X, Y, np.ones(X.size)])
    coef, *_ = np.linalg.lstsq(A, d[keep], rcond=None)
    print(f"\n--- residual tilt (after trimming |r| > 5*NMAD; {keep.sum():,} cells) ---")
    print(f"  dZ/dX = {coef[0]*100:+.2f} cm/km   dZ/dY = {coef[1]*100:+.2f} cm/km   "
          f"intercept = {coef[2]*100:+.2f} cm")
    detr = d[keep] - A @ coef
    print(f"  NMAD before detrend {nmad(d[keep])*100:.2f} cm -> after {nmad(detr)*100:.2f} cm")

    # ---- 3. residuals vs slope ----
    sl = np.rad2deg(slope[valid])[keep]
    print("\n--- residual vs terrain slope ---")
    print(f"{'slope bin':<14}{'n':>10}{'median cm':>12}{'NMAD cm':>10}")
    for lo, hi in [(0, 5), (5, 10), (10, 20), (20, 30), (30, 45), (45, 90)]:
        m = (sl >= lo) & (sl < hi)
        if m.sum() > 200:
            print(f"{lo}-{hi} deg{'':<6}{m.sum():>10,}{np.median(d[keep][m])*100:>12.2f}"
                  f"{nmad(d[keep][m])*100:>10.2f}")

    # ---- 4. what is merged_Gualan.tif? ----
    mg, _ = load(f"{S}/mergeddtm_ref.tif")
    both = np.isfinite(mg) & np.isfinite(ref) & (rc >= 3)
    diff = mg[both] - ref[both]
    print(f"\n--- merged_Gualan.tif minus export ground surface ({both.sum():,} cells) ---")
    print(f"  median {np.median(diff):+.2f} m | NMAD {nmad(diff):.2f} m | "
          f"p5 {np.percentile(diff,5):+.2f} | p95 {np.percentile(diff,95):+.2f} m")


if __name__ == "__main__":
    main()
