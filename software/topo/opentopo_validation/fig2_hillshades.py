"""Fig 2: 2-col x 5-row hillshade panels of the site DTMs (orthophoto for Byron's Ranch)."""
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LightSource
import rasterio
from rasterio.enums import Resampling

BASE = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
        "My Drive/Guatemala/Spring_Campaign/OpenTopography_upload")
OUT = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
       "My Drive/Guatemala/Spring_Campaign/SITES/figures/fig2_dtm_hillshades.png")

PANELS = [  # (number, label, path, kind)
    (1, "La Laguna", f"{BASE}/La_Laguna/la_laguna_dtm_cog.tif", "dtm"),
    (2, "Rio Tambor", f"{BASE}/Rio_Tambor/rio_tambor_dtm_cog.tif", "dtm"),
    (3, "Gualán", f"{BASE}/Gualan/gualan_dtm_cog.tif", "dtm"),
    (4, "Mellon Farm", f"{BASE}/Mellon_Farm/mellon_farm_dtm_cog.tif", "dtm"),
    (5, "Carillabas", f"{BASE}/Carillabas/carillabas_dtm_cog.tif", "dtm"),
    (6, "Finca del Eden", f"{BASE}/Finca_del_Eden/finca_del_eden_dtm_cog.tif", "dtm"),
    (7, "La Tinta", f"{BASE}/La_Tinta/la_tinta_dtm_cog.tif", "dtm"),
    (8, "Military Base", f"{BASE}/Military_Base/military_base_dtm_cog.tif", "dtm"),
    (9, "Museo Quirigua", f"{BASE}/Quirigua_Museo/quirigua_museo_dtm_cog.tif", "dtm"),
    (10, "Byron's Ranch (SfM orthophoto)",
     f"{BASE}/Byrons_Ranch/byrons_ranch_orthophoto_cog.tif", "ortho"),
]

MAXDIM = 1600  # decimated read target


def nice_scalebar(width_m):
    for L in (5000, 2000, 1000, 500, 250, 100, 50):
        if L <= width_m / 3.5:
            return L
    return 50


def read_decimated(path, bands=1):
    with rasterio.open(path) as src:
        scale = max(src.width, src.height) / MAXDIM
        out_w = max(1, int(src.width / max(scale, 1)))
        out_h = max(1, int(src.height / max(scale, 1)))
        idx = 1 if bands == 1 else list(range(1, bands + 1))
        data = src.read(idx, out_shape=(out_h, out_w) if bands == 1 else (bands, out_h, out_w),
                        resampling=Resampling.average, masked=True)
        px = src.transform.a * (src.width / out_w)
        extent_km = (src.bounds.right - src.bounds.left,
                     src.bounds.top - src.bounds.bottom)
    return data, px, extent_km


halo = [pe.withStroke(linewidth=2.2, foreground="white")]
ls = LightSource(azdeg=315, altdeg=45)

fig, axes = plt.subplots(5, 2, figsize=(7.09, 9.0), dpi=300)

for (num, label, path, kind), ax in zip(PANELS, axes.ravel()):
    if kind == "dtm":
        z, px, (wm, hm) = read_decimated(path, 1)
        zf = z.filled(np.nan).astype(float)
        zf[zf < -9000] = np.nan
        valid = np.isfinite(zf)
        zfill = np.where(valid, zf, np.nanmedian(zf))
        hs = ls.hillshade(zfill, vert_exag=2.5, dx=px, dy=px)
        p2, p98 = np.percentile(hs[valid], [2, 98])
        img = np.clip((hs - p2) / (p98 - p2), 0, 1)
        img = 0.05 + 0.95 * img
        rgba = np.repeat(img[:, :, None], 3, axis=2)
        rgba = np.dstack([rgba, valid.astype(float)])
        ax.imshow(rgba, interpolation="bilinear")
    else:
        rgb, px, (wm, hm) = read_decimated(path, 3)
        arr = np.moveaxis(rgb.filled(255), 0, -1)
        ax.imshow(arr, interpolation="bilinear")

    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.5)
        s.set_color("0.4")

    ax.text(0.02, 0.965, f"{num}. {label}", transform=ax.transAxes, fontsize=7.5,
            fontweight="bold", color="0.1", ha="left", va="top", path_effects=halo)

    # scale bar in axes coords: panel spans wm metres horizontally over the image width
    ny, nx = (zf.shape if kind == "dtm" else arr.shape[:2])
    L = nice_scalebar(wm)
    frac = L / wm
    x0, y0 = 0.03, 0.045
    ax.plot([x0, x0 + frac], [y0, y0], transform=ax.transAxes, color="0.05",
            lw=2.0, solid_capstyle="butt",
            path_effects=[pe.withStroke(linewidth=3.4, foreground="white")])
    ax.text(x0 + frac / 2, y0 + 0.03, f"{L} m" if L < 1000 else f"{L//1000} km",
            transform=ax.transAxes, fontsize=6, ha="center", va="bottom",
            color="0.05", path_effects=halo)

fig.subplots_adjust(left=0.01, right=0.99, top=0.995, bottom=0.005,
                    wspace=0.03, hspace=0.04)
fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
