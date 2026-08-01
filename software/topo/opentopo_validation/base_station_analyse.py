"""Compare CSRS-PPP base-station heights with the lidar bare-earth surface.

The base station is the only independent geodetic observation of the campaign,
but it is a WEAK control, for two reasons established here:

  1. Every PPP run reports `ARP 0.000 0.000 0.000` and `ANT NOT FOUND`, so the
     solved height is the raw antenna height. The antenna height above the
     ground was never recorded, and it evidently varied between sites.
  2. The antenna/tripod is not resolvable in the point clouds. Compact clusters
     of non-ground returns do occur near some base coordinates, but in plan view
     they are metres-wide vegetation patches, not a mast, so there is no target
     whose top can be matched to the PPP height.

What remains is h_PPP - z_ground, which equals the (unknown) antenna mount
height plus the vertical error of the lidar surface. That cannot isolate the
error, but it does test for physical impossibility: the PPP height must lie
ABOVE the bare-earth surface, by no more than a plausible tripod height.

Ground elevation is taken from a robust plane fit to ground-classified returns
within 8 m, evaluated at the base coordinate, so that terrain slope does not
bias the comparison. Run with the `insarhub_dev` env python.
"""
import glob
import os

import numpy as np

SCRATCH = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
           "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
           "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/basepts")
OUTCSV = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
          "My Drive/Guatemala/Spring_Campaign/SITES/figures/base_station_check.csv")

FIT_R = 8.0     # m, radius of ground points used for the plane fit

PRETTY = {"La_Laguna": "La Laguna", "Rio_Tambor": "Rio Tambor", "Gualan": "Gualán",
          "Mellon_Farm": "Mellon Farm", "Carillabas": "Carillabas",
          "Finca_del_Eden": "Finca del Eden", "La_Tinta": "La Tinta",
          "Quirigua_Museo": "Museo Quirigua"}

# PPP quality from base_station_ppp.csv / the .sum files
IAR = {"QS021X00": 0.0, "QS022O00": 0.0, "QS022Q00": 0.0, "QS022T00": 69.5,
       "QS023T00": 92.1, "QS023U00": 27.6, "QS023P00": 70.4, "QS024V00": 72.4,
       "QS025S00": 99.7, "QS026R00": 0.0, "QS024Q00": 0.0}
SIGV = {"QS021X00": 0.156, "QS022O00": 0.102, "QS022Q00": 0.099, "QS022T00": 0.033,
        "QS023T00": 0.078, "QS023U00": 0.075, "QS023P00": 0.061, "QS024V00": 0.110,
        "QS025S00": 0.086, "QS026R00": 0.252, "QS024Q00": 0.306}


def robust_plane(pts, x0, y0, n_iter=3):
    """Least-squares plane through ground points, re-fit after 2.5-sigma clipping.

    Returns (z at x0,y0, residual NMAD, slope in degrees, n used).
    """
    X = pts[:, 0] - x0
    Y = pts[:, 1] - y0
    Z = pts[:, 2]
    keep = np.ones(len(Z), bool)
    for _ in range(n_iter):
        A = np.column_stack([np.ones(keep.sum()), X[keep], Y[keep]])
        coef, *_ = np.linalg.lstsq(A, Z[keep], rcond=None)
        res = Z - (coef[0] + coef[1] * X + coef[2] * Y)
        s = 1.4826 * np.median(np.abs(res[keep] - np.median(res[keep])))
        if s <= 0:
            break
        keep = np.abs(res - np.median(res[keep])) < 2.5 * s
        if keep.sum() < 50:
            break
    slope = np.degrees(np.arctan(np.hypot(coef[1], coef[2])))
    return float(coef[0]), float(s), float(slope), int(keep.sum())


rows = []
for f in sorted(glob.glob(f"{SCRATCH}/*.npz")):
    sdir, bid = os.path.basename(f)[:-4].split("__")
    d = np.load(f)
    pts, (x, y, h) = d["pts"], d["meta"]
    rec = dict(site=PRETTY.get(sdir, sdir), base=bid, x=x, y=y, h=h,
               iar=IAR.get(bid, np.nan), sigv=SIGV.get(bid, np.nan),
               z=np.nan, rough=np.nan, slope=np.nan, n=0, dh=np.nan)

    r = np.hypot(pts[:, 0] - x, pts[:, 1] - y) if len(pts) else np.array([])
    g = pts[(r <= FIT_R) & (pts[:, 3] == 2)] if len(pts) else np.empty((0, 4))
    rec["n"] = len(g)
    if len(g) >= 200:
        z0, rough, slope, nused = robust_plane(g, x, y)
        rec.update(z=z0, rough=rough, slope=slope, n=nused, dh=h - z0)
    rows.append(rec)

rows.sort(key=lambda r: (np.isnan(r["dh"]), -(r["iar"] if np.isfinite(r["iar"]) else -1)))

hdr = (f"{'site':16s} {'base':9s} {'IAR%':>5s} {'sigV':>6s} {'h_PPP':>9s} "
       f"{'z_grnd':>9s} {'h-z':>7s} {'rough':>6s} {'slope':>6s}")
print(hdr)
print("-" * len(hdr))
for r in rows:
    if np.isnan(r["dh"]):
        print(f"{r['site']:16s} {r['base']:9s} {r['iar']:5.0f} {r['sigv']:6.3f} "
              f"{r['h']:9.3f} {'—':>9s} {'—':>7s} {'—':>6s} {'—':>6s}   "
              f"(only {r['n']} ground returns within {FIT_R:.0f} m)")
    else:
        print(f"{r['site']:16s} {r['base']:9s} {r['iar']:5.0f} {r['sigv']:6.3f} "
              f"{r['h']:9.3f} {r['z']:9.3f} {r['dh']:+7.3f} {r['rough']:6.3f} "
              f"{r['slope']:6.1f}")

ok = [r for r in rows if np.isfinite(r["dh"])]
dh = np.array([r["dh"] for r in ok])
print(f"\n{len(ok)} of {len(rows)} base stations have usable lidar coverage")
print(f"  h_PPP - z_ground: {dh.min():+.3f} to {dh.max():+.3f} m "
       f"(median {np.median(dh):+.3f}, std {dh.std(ddof=1):.3f})")
print("  this difference IS the unrecorded antenna mount height plus any "
      "vertical error;\n  a physically valid setup requires it to be positive "
      "and < ~2 m.")
neg = [r for r in ok if r["dh"] < 0]
for r in neg:
    print(f"  !! {r['site']} ({r['base']}): PPP height is {abs(r['dh']):.3f} m "
          f"BELOW the lidar ground surface — physically impossible for an "
          f"antenna; local roughness {r['rough']:.2f} m, slope {r['slope']:.1f}°")

with open(OUTCSV, "w") as f:
    f.write("site,base,utm_x,utm_y,h_ppp_m,ppp_iar_pct,ppp_sigmaV95_m,"
            "z_ground_m,h_minus_z_m,ground_roughness_m,slope_deg,n_ground_pts\n")
    for r in rows:
        f.write(f"{r['site']},{r['base']},{r['x']:.3f},{r['y']:.3f},{r['h']:.4f},"
                f"{r['iar']},{r['sigv']},{r['z']:.4f},{r['dh']:.4f},"
                f"{r['rough']:.4f},{r['slope']:.2f},{r['n']}\n")
print("\nwrote", OUTCSV)
