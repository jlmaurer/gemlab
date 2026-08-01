"""Compare delivered DTM elevations with the CSRS-PPP base-station heights.

The base station is the only independent geodetic control available for the
campaign. Its CSRS-PPP solution gives the ellipsoidal height of the ANTENNA:
every .sum reports `ARP 0.000 0.000 0.000` (no antenna-height reduction was
entered) and `ANT NOT FOUND` (no phase-centre model applied), so the reported
height sits one mount height above the bare-earth surface the lidar sees.

The difference h_PPP - z_DTM at the base coordinates is therefore
    (antenna height above ground) + (vertical error of the lidar surface).
The mount height is unrecorded but was nominally the same tripod setup at every
site, so the SCATTER of that difference across sites -- not its absolute value --
is the accuracy metric. Run with the `insarhub_dev` env python.
"""
import glob
import os


import numpy as np
import rasterio
from pyproj import Transformer

BASE = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
        "My Drive/Guatemala/Spring_Campaign/OpenTopography_upload")
OUTCSV = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
          "My Drive/Guatemala/Spring_Campaign/SITES/figures/base_station_check.csv")

# site dir -> (pretty name, EPSG of delivered products, dtm filename)
SITES = {
    "La_Laguna": ("La Laguna", 32615, "la_laguna_dtm_cog.tif"),
    "Rio_Tambor": ("Rio Tambor", 32616, "rio_tambor_dtm_cog.tif"),
    "Gualan": ("Gualán", 32616, "gualan_dtm_cog.tif"),
    "Mellon_Farm": ("Mellon Farm", 32616, "mellon_farm_dtm_cog.tif"),
    "Carillabas": ("Carillabas", 32616, "carillabas_dtm_cog.tif"),
    "Finca_del_Eden": ("Finca del Eden", 32616, "finca_del_eden_dtm_cog.tif"),
    "La_Tinta": ("La Tinta", 32616, "la_tinta_dtm_cog.tif"),
    "Quirigua_Museo": ("Museo Quirigua", 32616, "quirigua_museo_dtm_cog.tif"),
}

def dms2deg(d, m, s):
    """Signed degrees from separate D M S fields (the sign lives on D)."""
    sign = -1.0 if d.strip().startswith("-") else 1.0
    return sign * (abs(float(d)) + float(m) / 60 + float(s) / 3600)


def parse_sum(path):
    """Return the ESTIMATED lat/lon/ellipsoidal height + 95% sigmas.

    Field layout (whitespace-separated), for both POS LAT and POS LON:
        0:POS 1:LAT 2:frame 3:epoch  4-6:A_PRIORI d m s  7-9:ESTIMATED d m s
        10:DIFF 11:SIGMA95 ...
    Parse by field index, not by column slice: the leading minus sign of a
    western longitude sits outside a fixed slice and gets silently dropped.
    """
    out = {}
    for line in open(path, errors="replace"):
        f = line.split()
        if line.startswith("POS LAT"):
            out["lat"] = dms2deg(f[7], f[8], f[9])
            out["lat_s"] = float(f[11])
        elif line.startswith("POS LON"):
            out["lon"] = dms2deg(f[7], f[8], f[9])
            out["lon_s"] = float(f[11])
        elif line.startswith("POS HGT"):
            out["h"] = float(f[5])          # ESTIMATED column
            out["h_s"] = float(f[7])        # SIGMA(95%)
        elif line.startswith("IAR"):
            out["iar"] = float(f[1].rstrip("%"))
        elif line.startswith("BEG"):
            out["beg"] = " ".join(f[1:3])
    return out


def sample_dtm(dtm_path, x, y, radius=5.0):
    """Median / spread of DTM cells within `radius` m of (x, y)."""
    with rasterio.open(dtm_path) as src:
        res = abs(src.transform.a)
        n = max(1, int(np.ceil(radius / res)))
        row, col = src.index(x, y)
        r0, r1 = max(0, row - n), min(src.height, row + n + 1)
        c0, c1 = max(0, col - n), min(src.width, col + n + 1)
        if r0 >= r1 or c0 >= c1:
            return None
        win = rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0)
        a = src.read(1, window=win, masked=True).filled(np.nan).astype(float)
    a[a < -9000] = np.nan
    if not np.isfinite(a).any():
        return None
    return {"z_med": float(np.nanmedian(a)), "z_std": float(np.nanstd(a)),
            "z_min": float(np.nanmin(a)), "z_max": float(np.nanmax(a)),
            "n": int(np.isfinite(a).sum())}


rows = []
for sdir, (name, epsg, dtm) in SITES.items():
    dtm_path = f"{BASE}/{sdir}/{dtm}"
    if not os.path.exists(dtm_path):
        print(f"{name}: no DTM"); continue
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    for sumf in sorted(glob.glob(f"{BASE}/{sdir}/base_station_*/*.sum")):
        p = parse_sum(sumf)
        if "h" not in p:
            print(f"{name}: could not parse {os.path.basename(sumf)}"); continue
        x, y = tr.transform(p["lon"], p["lat"])
        s = sample_dtm(dtm_path, x, y)
        base = os.path.basename(sumf).replace(".sum", "")
        if s is None:
            print(f"{name} / {base}: base station outside DTM coverage")
            rows.append(dict(site=name, base=base, x=x, y=y, h=p["h"],
                             h_s=p["h_s"], iar=p.get("iar"), z_med=np.nan,
                             z_std=np.nan, dh=np.nan, n=0))
            continue
        rows.append(dict(site=name, base=base, x=x, y=y, h=p["h"], h_s=p["h_s"],
                         iar=p.get("iar"), z_med=s["z_med"], z_std=s["z_std"],
                         dh=p["h"] - s["z_med"], n=s["n"]))

hdr = (f"{'site':16s} {'base':10s} {'IAR%':>6s} {'h_PPP':>10s} {'sig95':>6s} "
       f"{'z_DTM':>10s} {'roughness':>9s} {'h-z':>7s}")
print(hdr)
print("-" * len(hdr))
for r in rows:
    print(f"{r['site']:16s} {r['base']:10s} {r['iar'] or 0:6.1f} "
          f"{r['h']:10.3f} {r['h_s']:6.3f} {r['z_med']:10.3f} "
          f"{r['z_std']:9.3f} {r['dh']:7.3f}")

dh = np.array([r["dh"] for r in rows if np.isfinite(r["dh"])])
print(f"\nn = {len(dh)}   mean {dh.mean():.3f} m   median {np.median(dh):.3f} m"
      f"   std {dh.std(ddof=1):.3f} m")
print(f"spread about the median: NMAD "
      f"{1.4826*np.median(np.abs(dh-np.median(dh))):.3f} m, "
      f"range {dh.min():.3f} to {dh.max():.3f} m")

with open(OUTCSV, "w") as f:
    f.write("site,base,utm_x,utm_y,h_ppp_m,h_sigma95_m,iar_pct,"
            "z_dtm_m,dtm_roughness_m,h_minus_z_m,n_cells\n")
    for r in rows:
        f.write(f"{r['site']},{r['base']},{r['x']:.3f},{r['y']:.3f},"
                f"{r['h']:.4f},{r['h_s']:.4f},{r['iar']},{r['z_med']:.4f},"
                f"{r['z_std']:.4f},{r['dh']:.4f},{r['n']}\n")
print("wrote", OUTCSV)
