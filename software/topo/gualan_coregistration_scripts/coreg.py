#!/usr/bin/env python
"""Solve the 3-D translation that aligns a source ground surface to a reference one.

Primary solver is a three-stage brute-force search over (dx, dy) that minimises the
NMAD of the elevation difference, with dz taken as the median at each candidate.
It is free of slope/aspect sign conventions, so it cannot silently converge to a
mirrored solution.

Nuth & Kaeaeb (2011) slope/aspect regression is run afterwards as an *independent*
check, and is only adopted if it actually lowers the NMAD.

Usage: coreg.py ref.tif ref_count.tif src.tif src_count.tif out.json
"""
import json
import sys

import numpy as np
import rasterio


def nmad(x):
    return 1.4826 * np.median(np.abs(x - np.median(x)))


def load(path):
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float64)
        nd = ds.nodata
        if nd is not None:
            a[a == nd] = np.nan
        return a, ds.transform


def load_count(path):
    with rasterio.open(path) as ds:
        return ds.read(1)


def bilinear(arr, rows, cols):
    """Sample arr at float (row, col). NaN outside the grid or beside a NaN."""
    nr, nc = arr.shape
    r0 = np.floor(rows).astype(np.int64)
    c0 = np.floor(cols).astype(np.int64)
    ok = (r0 >= 0) & (r0 < nr - 1) & (c0 >= 0) & (c0 < nc - 1)
    out = np.full(rows.shape, np.nan)
    r, c = r0[ok], c0[ok]
    fr = rows[ok] - r
    fc = cols[ok] - c
    v00, v01 = arr[r, c], arr[r, c + 1]
    v10, v11 = arr[r + 1, c], arr[r + 1, c + 1]
    out[ok] = ((v00 * (1 - fc) + v01 * fc) * (1 - fr)
               + (v10 * (1 - fc) + v11 * fc) * fr)
    return out


def sample_shifted(src, rows, cols, dx, dy, res):
    """Source surface after translating the cloud by (dx, dy), read at (rows, cols)."""
    return bilinear(src, rows + dy / res, cols - dx / res)


def main(ref_tif, ref_cnt_tif, src_tif, src_cnt_tif, out_json):
    ref, tr = load(ref_tif)
    src, tr2 = load(src_tif)
    assert tr == tr2 and ref.shape == src.shape, "grids must be identical"
    res = tr.a
    rc = load_count(ref_cnt_tif)
    sc = load_count(src_cnt_tif)

    dzdy, dzdx = np.gradient(ref, res)
    dzdy = -dzdy  # raster rows increase southward
    slope = np.arctan(np.hypot(dzdx, dzdy))
    aspect = np.arctan2(-dzdx, dzdy)

    valid = np.isfinite(ref) & np.isfinite(src) & (rc >= 3) & (sc >= 3)
    # Cells used to solve the shift: well populated, and sloped enough to carry
    # horizontal information without being so steep that the mean-Z cell is noise.
    fit = valid & np.isfinite(slope) & (slope > np.deg2rad(3)) & (slope < np.deg2rad(45))

    fr, fc_ = np.nonzero(fit)
    print(f"[coreg] grid {ref.shape} @ {res} m | overlap cells {valid.sum():,} | fit cells {fr.size:,}")
    if fr.size < 5000:
        sys.exit("not enough usable overlap to co-register")

    rng = np.random.default_rng(0)
    sel = (rng.choice(fr.size, 600_000, replace=False) if fr.size > 600_000
           else np.arange(fr.size))
    rs = fr[sel].astype(np.float64)
    cs = fc_[sel].astype(np.float64)
    ref_s = ref[fr[sel], fc_[sel]]
    slope_s = slope[fr[sel], fc_[sel]]
    asp_s = aspect[fr[sel], fc_[sel]]

    def score(dx, dy):
        d = ref_s - sample_shifted(src, rs, cs, dx, dy, res)
        d = d[np.isfinite(d)]
        if d.size < 1000:
            return np.inf, np.nan
        med = np.median(d)
        return nmad(d - med), med

    # ---- brute force, three refinement stages ----
    best = (np.inf, 0.0, 0.0, 0.0)
    stages = [(-12.0, 12.0, 1.0), (None, None, 0.2), (None, None, 0.02)]
    for lo, hi, step in stages:
        if lo is None:
            lo_x, hi_x = best[1] - 6 * step, best[1] + 6 * step
            lo_y, hi_y = best[2] - 6 * step, best[2] + 6 * step
        else:
            lo_x, hi_x, lo_y, hi_y = lo, hi, lo, hi
        for dx in np.arange(lo_x, hi_x + step / 2, step):
            for dy in np.arange(lo_y, hi_y + step / 2, step):
                s, med = score(dx, dy)
                if s < best[0]:
                    best = (s, float(dx), float(dy), float(med))
        print(f"[coreg] brute step {step:>4}: dx={best[1]:+.3f} dy={best[2]:+.3f} "
              f"dz={best[3]:+.3f}  NMAD={best[0]:.4f}")

    bf = dict(dx=best[1], dy=best[2], dz=best[3], nmad=best[0])

    # ---- Nuth & Kaeaeb, independent check ----
    d0 = ref_s - sample_shifted(src, rs, cs, 0.0, 0.0, res)
    dx, dy, dz = 0.0, 0.0, float(np.median(d0[np.isfinite(d0)]))
    nk_hist = []
    nk_best = None
    for it in range(15):
        v = sample_shifted(src, rs, cs, dx, dy, res)
        dh = ref_s - (v + dz)
        good = np.isfinite(dh)
        d = dh[good]
        m, s = np.median(d), nmad(d)
        keep = good.copy()
        keep[good] = np.abs(d - m) < 3 * s
        cur = float(nmad(dh[keep]))
        nk_hist.append(dict(it=it, dx=dx, dy=dy, dz=dz, nmad=cur))
        if nk_best is None or cur < nk_best[0]:
            nk_best = (cur, dx, dy, dz)
        y = dh[keep] / np.tan(slope_s[keep])
        x = asp_s[keep]
        A = np.column_stack([np.cos(x), np.sin(x), np.ones(x.size)])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        a = np.hypot(coef[0], coef[1])
        b = np.arctan2(coef[1], coef[0])
        ddx, ddy = a * np.sin(b), a * np.cos(b)
        ddz = coef[2] * np.mean(np.tan(slope_s[keep]))
        dx, dy, dz = dx + ddx, dy + ddy, dz + ddz
        if np.hypot(ddx, ddy) < 0.01 and abs(ddz) < 0.005:
            break
    print(f"[coreg] N&K best:  dx={nk_best[1]:+.3f} dy={nk_best[2]:+.3f} "
          f"dz={nk_best[3]:+.3f}  NMAD={nk_best[0]:.4f}")

    # ---- adopt the better of the two, measured on all overlap cells ----
    vr, vc = np.nonzero(valid)
    vr = vr.astype(np.float64)
    vc = vc.astype(np.float64)
    ref_v = ref[valid]

    def stats(ddx, ddy, ddz):
        d = ref_v - (sample_shifted(src, vr, vc, ddx, ddy, res) + ddz)
        d = d[np.isfinite(d)]
        return dict(n=int(d.size), median=float(np.median(d)), mean=float(np.mean(d)),
                    nmad=float(nmad(d)), std=float(np.std(d)),
                    rmse=float(np.sqrt(np.mean(d ** 2))),
                    p16=float(np.percentile(d, 16)), p84=float(np.percentile(d, 84)),
                    absmax=float(np.max(np.abs(d))))

    before = stats(0.0, 0.0, 0.0)
    st_bf = stats(bf["dx"], bf["dy"], bf["dz"])
    st_nk = stats(nk_best[1], nk_best[2], nk_best[3])

    if st_nk["nmad"] < st_bf["nmad"]:
        adopted, which, st = (nk_best[1], nk_best[2], nk_best[3]), "nuth_kaab", st_nk
    else:
        adopted, which, st = (bf["dx"], bf["dy"], bf["dz"]), "brute_force", st_bf

    result = dict(
        reference=ref_tif, source=src_tif, resolution=res,
        brute_force=bf, brute_force_stats=st_bf,
        nuth_kaab=dict(dx=nk_best[1], dy=nk_best[2], dz=nk_best[3], nmad=nk_best[0]),
        nuth_kaab_stats=st_nk, nk_iterations=nk_hist,
        adopted_solver=which,
        adopted=dict(dx=adopted[0], dy=adopted[1], dz=adopted[2]),
        stats_before=before, stats_after=st,
        solver_disagreement=dict(dx=nk_best[1] - bf["dx"], dy=nk_best[2] - bf["dy"],
                                 dz=nk_best[3] - bf["dz"]),
    )
    with open(out_json, "w") as fh:
        json.dump(result, fh, indent=2)

    print("\n=== BEFORE ===");  print(json.dumps(before, indent=2))
    print("=== AFTER (%s) ===" % which); print(json.dumps(st, indent=2))
    print(f"\nadopted shift: dx={adopted[0]:+.3f}  dy={adopted[1]:+.3f}  dz={adopted[2]:+.3f} m")
    print(f"solver disagreement: dx={nk_best[1] - bf['dx']:+.3f} "
          f"dy={nk_best[2] - bf['dy']:+.3f} dz={nk_best[3] - bf['dz']:+.3f} m")


if __name__ == "__main__":
    main(*sys.argv[1:6])
