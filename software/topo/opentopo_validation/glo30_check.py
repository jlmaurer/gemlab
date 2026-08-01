"""Compare every delivered dataset with the Copernicus GLO-30 DEM.

GLO-30 is a TanDEM-X-derived surface model on the EGM2008 vertical datum, whereas
the lidar products are bare-earth ellipsoidal heights, so two conversions are
needed before any difference means anything:

  * GLO-30 orthometric -> ellipsoidal, by adding the EGM2008 geoid undulation
    (PROJ grid us_nga_egm08_25.tif);
  * the comparison is restricted to OPEN, LOW-SLOPE cells (lidar canopy height
    below CANOPY_MAX and slope below SLOPE_MAX), where a surface model and a
    bare-earth model should agree.

GLO-30's own vertical accuracy (~2 m LE90, ~1 m RMSE over flat open terrain) sets
the floor here: this test can detect metre-level datum or blunder problems, not
decimetre-level error. Run with the `insarhub_dev` env python.
"""
import glob
import os

import numpy as np
import rasterio
from rasterio.enums import Resampling
from pyproj import Transformer

SCRATCH = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
           "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
           "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad")
GRID = f"{SCRATCH}/grid30"
GLO = f"{SCRATCH}/glo30"
OUTCSV = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
          "My Drive/Guatemala/Spring_Campaign/SITES/figures/glo30_check.csv")

MIN_GND = 30       # ground returns needed in a 30 m cell
GND_FRAC = 0.90    # openness: fraction of returns in the cell classified ground
SLOPE_MAX = 5.0    # deg

# Openness is measured by ground fraction, NOT by (max_z - ground). The per-cell
# maximum is set by isolated stray high returns (classes 0/1 blunders survive the
# class-7 noise filter), which inflates an apparent canopy to 9-26 m even over
# bare farmland and would reject essentially every cell.

SITES = {
    "La_Laguna": ("La Laguna", 32615),
    "Rio_Tambor": ("Rio Tambor", 32616),
    "Gualan": ("Gualán", 32616),
    "Mellon_Farm": ("Mellon Farm", 32616),
    "Carillabas": ("Carillabas", 32616),
    "Finca_del_Eden": ("Finca del Eden", 32616),
    "La_Tinta": ("La Tinta", 32616),
    "Military_Base": ("Military Base", 32616),
    "Quirigua_Museo": ("Museo Quirigua", 32616),
    "Byrons_Ranch": ("Byron's Ranch", 32616),
}

tiles = [rasterio.open(f) for f in sorted(glob.glob(f"{GLO}/N*.tif"))]
geoid = rasterio.open(f"{GLO}/egm08_25.tif")


def sample(srcs, lon, lat):
    """Bilinear sample of the first raster covering each point."""
    out = np.full(len(lon), np.nan)
    for src in srcs:
        b = src.bounds
        m = (lon >= b.left) & (lon <= b.right) & (lat >= b.bottom) & (lat <= b.top)
        m &= ~np.isfinite(out)
        if not m.any():
            continue
        vals = np.array([v[0] for v in src.sample(
            np.column_stack([lon[m], lat[m]]), masked=False)], dtype=float)
        if src.nodata is not None:
            vals[vals == src.nodata] = np.nan
        vals[vals < -1000] = np.nan
        out[m] = vals
    return out


def robust(d):
    med = np.median(d)
    return med, 1.4826 * np.median(np.abs(d - med)), np.sqrt(np.mean(d ** 2))


def byrons_surface(ext, cell, shape):
    """Byron's Ranch surface grid: the SfM cloud carries no ground class at all
    (only class 0 plus class-7 noise), so its 'surface' is the photogrammetric
    surface itself -- effectively a DSM, and the one product here that is
    like-for-like with GLO-30. Pre-binned by compute_30m_grids-style code run
    under the `opentopo` env, since laspy is not installed alongside rasterio."""
    d = np.load(f"{GRID}/Byrons_Ranch_surface.npz")
    return d["n"], d["s"]


rows = []
for sdir, (name, epsg) in SITES.items():
    f = f"{GRID}/{sdir}.npz"
    if not os.path.exists(f):
        print(f"{name}: no 30 m grid yet"); continue
    d = np.load(f)
    n_all, n_gnd = d["n_all"], d["n_gnd"]
    s_gnd, z_max = d["s_gnd"], d["z_max"].astype(float)
    ext, cell = d["extent"], float(d["cell"])

    if sdir == "Byrons_Ranch":
        # SfM product carries no ground class (only class 0 + noise), so its
        # surface is the photogrammetric surface itself -- see notes below.
        n_gnd, s_gnd = byrons_surface(ext, cell, n_all.shape)

    with np.errstate(invalid="ignore", divide="ignore"):
        zg = np.where(n_gnd >= MIN_GND, s_gnd / np.maximum(n_gnd, 1), np.nan)
        gfrac = np.where(n_all > 0, n_gnd / np.maximum(n_all, 1), 0.0)
    canopy = z_max - zg

    gy, gx = np.gradient(zg, cell)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))

    ny, nx = zg.shape
    xs = ext[0] + (np.arange(nx) + 0.5) * cell
    ys = ext[2] + (np.arange(ny) + 0.5) * cell
    X, Y = np.meshgrid(xs, ys)

    ok = np.isfinite(zg)
    tr = Transformer.from_crs(epsg, 4326, always_xy=True)
    lon, lat = tr.transform(X[ok], Y[ok])

    H = sample(tiles, lon, lat)        # EGM2008 orthometric
    N = sample([geoid], lon, lat)      # geoid undulation
    h_glo = H + N                      # -> ellipsoidal (PROJ convention h = H + N)

    zg_ok, gf_ok, slp_ok = zg[ok], gfrac[ok], slope[ok]
    dz_all = h_glo - zg_ok

    open_m = (np.isfinite(dz_all) & (gf_ok >= GND_FRAC) & (slp_ok < SLOPE_MAX))
    n_open = int(open_m.sum())
    rec = dict(site=name, n_cells=int(ok.sum()), n_open=n_open,
               geoid_N=float(np.nanmedian(N)),
               canopy_med=float(np.nanmedian(gf_ok)))
    if n_open >= 20:
        med, nmad, rmse = robust(dz_all[open_m])
        rec.update(med=med, nmad=nmad, rmse=rmse)
    else:
        # fall back to all valid cells; flag it
        med, nmad, rmse = robust(dz_all[np.isfinite(dz_all)])
        rec.update(med=med, nmad=nmad, rmse=rmse)
    # difference against the lidar SURFACE model too (like-for-like with a DSM)
    dz_dsm = h_glo - z_max[ok]
    fin = np.isfinite(dz_dsm)
    rec["med_dsm"] = float(np.median(dz_dsm[fin])) if fin.any() else np.nan
    rows.append(rec)

hdr = (f"{'site':16s} {'cells':>6s} {'open':>6s} {'gndfrac':>7s} {'geoidN':>7s} "
       f"{'GLO-lidar':>10s} {'NMAD':>7s} {'RMSE':>7s} {'GLO-DSM':>8s}")
print(hdr); print("-" * len(hdr))
for r in rows:
    flag = "" if r["n_open"] >= 20 else "  (no open cells; all cells used)"
    print(f"{r['site']:16s} {r['n_cells']:6d} {r['n_open']:6d} "
          f"{r['canopy_med']:7.2f} {r['geoid_N']:7.2f} {r['med']:+10.2f} "
          f"{r['nmad']:7.2f} {r['rmse']:7.2f} {r['med_dsm']:+8.2f}{flag}")

good = [r for r in rows if r["n_open"] >= 20]
if good:
    m = np.array([r["med"] for r in good])
    print(f"\nopen-terrain median offset (GLO-30 minus lidar bare earth), "
          f"{len(good)} sites: {m.min():+.2f} to {m.max():+.2f} m, "
          f"mean {m.mean():+.2f}, std {m.std(ddof=1):.2f}")

with open(OUTCSV, "w") as fh:
    fh.write("site,n_cells_30m,n_open_cells,median_canopy_m,geoid_N_m,"
             "glo30_minus_lidar_median_m,nmad_m,rmse_m,glo30_minus_lidarDSM_median_m\n")
    for r in rows:
        fh.write(f"{r['site']},{r['n_cells']},{r['n_open']},{r['canopy_med']:.3f},"
                 f"{r['geoid_N']:.3f},{r['med']:.3f},{r['nmad']:.3f},"
                 f"{r['rmse']:.3f},{r['med_dsm']:.3f}\n")
print("\nwrote", OUTCSV)
