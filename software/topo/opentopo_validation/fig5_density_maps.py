"""Fig 5: per-site point-density maps (all returns, 10 m cells).

Same 2 x 5 panel layout as Fig. 2, so panels can be compared site-by-site.
Requires compute_density_grids.py to have been run.
"""
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MaxNLocator

SCRATCH = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
           "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
           "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/density")
OUT = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
       "My Drive/Guatemala/Spring_Campaign/SITES/figures/fig5_point_density.png")

PANELS = [
    (1, "La Laguna", "La_Laguna"),
    (2, "Rio Tambor", "Rio_Tambor"),
    (3, "Gualán", "Gualan"),
    (4, "Mellon Farm", "Mellon_Farm"),
    (5, "Carillabas", "Carillabas"),
    (6, "Finca del Eden", "Finca_del_Eden"),
    (7, "La Tinta", "La_Tinta"),
    (8, "Military Base", "Military_Base"),
    (9, "Museo Quirigua", "Quirigua_Museo"),
    (10, "Byron's Ranch (SfM)", "Byrons_Ranch"),
]


def nice_scalebar(width_m):
    for L in (5000, 2000, 1000, 500, 250, 100, 50):
        if L <= width_m / 3.5:
            return L
    return 50


halo = [pe.withStroke(linewidth=2.2, foreground="white")]
fig, axes = plt.subplots(5, 2, figsize=(7.09, 9.4), dpi=300)

for (num, label, key), ax in zip(PANELS, axes.ravel()):
    d = np.load(f"{SCRATCH}/{key}.npz")
    counts = d["counts"].astype(float)
    cell = float(d["cell"])
    ext = d["extent"]

    dens = counts / (cell * cell)
    dens[dens == 0] = np.nan

    # crop to data footprint
    rows = np.where(np.any(np.isfinite(dens), axis=1))[0]
    cols = np.where(np.any(np.isfinite(dens), axis=0))[0]
    dens = dens[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    wm = dens.shape[1] * cell

    vmax = float(np.nanpercentile(dens, 98))
    im = ax.imshow(dens, origin="lower", cmap="magma", vmin=0, vmax=vmax,
                   interpolation="nearest", rasterized=True)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.5)
        s.set_color("0.4")

    # titles above the panel: several footprints are too narrow to hold a label
    med = np.nanmedian(dens)
    mtxt = f"{med:.1f}" if med < 10 else f"{med:.0f}"
    ax.set_title(f"{num}. {label}\nmedian {mtxt} pts m$^{{-2}}$",
                 fontsize=7.5, fontweight="bold", color="0.1", loc="left",
                 pad=3, linespacing=1.45)

    L = nice_scalebar(wm)
    frac = L / wm
    ax.plot([0.04, 0.04 + frac], [0.05, 0.05], transform=ax.transAxes,
            color="0.95", lw=2.0, solid_capstyle="butt",
            path_effects=[pe.withStroke(linewidth=3.4, foreground="0.15")])
    ax.text(0.04 + frac / 2, 0.085, f"{L} m" if L < 1000 else f"{L//1000} km",
            transform=ax.transAxes, fontsize=6, ha="center", va="bottom",
            color="0.98", path_effects=[pe.withStroke(linewidth=1.8,
                                                      foreground="0.15")])

    # inset colourbar tracks the (aspect-shrunk) panel box
    cax = ax.inset_axes([0.55, 0.055, 0.40, 0.032])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_ticks([0, vmax])
    cb.set_ticklabels(["0", f"{vmax:.0f}"])
    cb.ax.tick_params(labelsize=5.2, length=0, pad=1, colors="0.98")
    for t in cb.ax.get_xticklabels():
        t.set_path_effects([pe.withStroke(linewidth=1.8, foreground="0.15")])
    cb.outline.set_edgecolor("0.85")
    cb.outline.set_linewidth(0.4)
    cax.set_title("pts m$^{-2}$", fontsize=5.2, color="0.98", pad=1.5,
                  path_effects=[pe.withStroke(linewidth=1.8, foreground="0.15")])

fig.subplots_adjust(left=0.012, right=0.988, top=0.955, bottom=0.008,
                    wspace=0.07, hspace=0.30)
fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
