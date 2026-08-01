"""Fig 4: flight-to-flight DTM difference maps and co-registration histograms.

One row per overlapping flight pair: the bare-earth difference map in the common
footprint (left) and the distribution of differences with robust statistics
(right). Requires compute_overlap_grids.py to have been run.

Statistics are computed on the native 1 m difference grid; the maps are block-
median aggregated to DISP_CELL purely so that sparse, ragged overlap zones are
legible in print.
"""
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MaxNLocator

SCRATCH = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
           "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
           "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad/overlap")
OUT = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
       "My Drive/Guatemala/Spring_Campaign/SITES/figures/fig4_overlap_validation.png")

MINPTS = 2        # minimum ground returns per cell, in BOTH flights
DISP_CELL = 5.0   # display aggregation (m)

# Only pairs with a usable common footprint are plotted. Of the six possible
# pairs at the two multi-flight sites, two are dropped: Gualan 204440-220238
# share no ground cells at all, and Gualan 204440-211849 share only 146 cells
# (~150 m^2) in one corner -- too few to map or to constrain a co-registration.
PAIRS = [
    ("Gualan", "211849", "220238", "Gualán"),
    ("Rio_Tambor", "201605", "211204", "Rio Tambor"),
    ("Rio_Tambor", "201605", "220845", "Rio Tambor"),
    ("Rio_Tambor", "211204", "220845", "Rio Tambor"),
]

cache = {}


def load(site):
    if site not in cache:
        cache[site] = np.load(f"{SCRATCH}/{site}_flights.npz")
    return cache[site]


def mean_grid(d, fid):
    zsum = d[f"zsum_{fid}"].astype(np.float64)
    zcnt = d[f"zcnt_{fid}"]
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(zcnt > 0, zsum / np.maximum(zcnt, 1), np.nan)
    return z, zcnt


def robust(d):
    med = np.median(d)
    nmad = 1.4826 * np.median(np.abs(d - med))
    rmse = np.sqrt(np.mean(d ** 2))
    return med, nmad, rmse


def block_median(a, k):
    """Median over k x k blocks, ignoring NaNs."""
    ny, nx = a.shape
    py, px = (-ny) % k, (-nx) % k
    if py or px:
        a = np.pad(a, ((0, py), (0, px)), constant_values=np.nan)
    b = a.reshape(a.shape[0] // k, k, a.shape[1] // k, k)
    import warnings
    with warnings.catch_warnings():   # empty blocks are expected -> NaN
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmedian(b, axis=(1, 3))


halo = [pe.withStroke(linewidth=2.2, foreground="white")]
nrow = len(PAIRS)
fig = plt.figure(figsize=(7.09, 1.85 * nrow), dpi=300)
gs = fig.add_gridspec(nrow, 2, width_ratios=[1.15, 1.0],
                      left=0.035, right=0.955, top=0.935, bottom=0.055,
                      wspace=0.42, hspace=0.55)

summary = []
for i, (site, fa, fb, label) in enumerate(PAIRS):
    d = load(site)
    za, ca = mean_grid(d, fa)
    zb, cb = mean_grid(d, fb)
    cell = float(d["cell"])

    ok = (ca >= MINPTS) & (cb >= MINPTS)
    dz = np.where(ok, za - zb, np.nan)

    rows = np.where(np.any(ok, axis=1))[0]
    cols = np.where(np.any(ok, axis=0))[0]
    r0, r1 = rows.min(), rows.max() + 1
    c0, c1 = cols.min(), cols.max() + 1
    sub = dz[r0:r1, c0:c1]

    vals = dz[np.isfinite(dz)]
    med, nmad, rmse = robust(vals)
    area = len(vals) * cell * cell / 1e6
    summary.append((label, fa, fb, len(vals), area, med, nmad, rmse))

    disp = block_median(sub, int(DISP_CELL / cell))
    vmax = max(0.10, float(np.percentile(np.abs(vals), 95)))

    # ---- difference map ----
    axm = fig.add_subplot(gs[i, 0])
    span_x = (c1 - c0) * cell
    span_y = (r1 - r0) * cell
    im = axm.imshow(disp, origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax,
                    extent=[0, span_x, 0, span_y], interpolation="nearest",
                    rasterized=True)
    axm.set_aspect("equal")
    axm.set_xticks([])
    axm.set_yticks([])
    for s in axm.spines.values():
        s.set_linewidth(0.5)
        s.set_color("0.45")
    # area goes in the title -- the narrow overlap strips have no room inside
    axm.set_title(f"({'abcde'[i]}) {label}: flight {fa} − {fb}\n"
                  f"{area:.2f} km² common footprint",
                  fontsize=7.5, fontweight="bold", color="0.1", loc="left",
                  pad=3.5, linespacing=1.4)

    L = next((v for v in (1000, 500, 250, 100) if v <= span_x / 2.5), 100)
    frac = L / span_x
    axm.plot([0.05, 0.05 + frac], [0.035, 0.035], transform=axm.transAxes,
             color="0.05", lw=1.8, solid_capstyle="butt",
             path_effects=[pe.withStroke(linewidth=3.2, foreground="white")])
    axm.text(0.05 + frac / 2, 0.065, f"{L} m", transform=axm.transAxes,
             fontsize=5.8, ha="center", va="bottom", color="0.05",
             path_effects=halo)

    cb = fig.colorbar(im, ax=axm, fraction=0.045, pad=0.03, aspect=14)
    cb.set_label("Δ elevation (m)", fontsize=5.8, labelpad=1.5)
    cb.ax.tick_params(labelsize=5.2, length=2, pad=1)
    cb.locator = MaxNLocator(5)
    cb.update_ticks()

    # ---- histogram ----
    axh = fig.add_subplot(gs[i, 1])
    lim = 1.1 * max(abs(np.percentile(vals, 1)), abs(np.percentile(vals, 99)))
    lim = max(lim, 0.12)
    axh.hist(vals, bins=np.linspace(-lim, lim, 101), color="#5B8FBF",
             edgecolor="none")
    axh.axvline(0, color="0.35", lw=0.9, ls=(0, (4, 2)), zorder=3)
    axh.axvline(med, color="#B2182B", lw=1.3, zorder=4)
    axh.set_xlim(-lim, lim)
    axh.set_xlabel("Δ elevation (m)", fontsize=6.5, labelpad=2)
    axh.set_ylabel("Cells (1 m)", fontsize=6.5, labelpad=2)
    axh.tick_params(labelsize=6, length=2.5, pad=1.5)
    axh.yaxis.set_major_locator(MaxNLocator(4))
    axh.xaxis.set_major_locator(MaxNLocator(5))
    for s in ["top", "right"]:
        axh.spines[s].set_visible(False)
    axh.text(0.975, 0.95,
             f"median {med*100:+.1f} cm\nNMAD {nmad*100:.1f} cm\n"
             f"RMSE {rmse*100:.1f} cm",
             transform=axh.transAxes, fontsize=6.2, va="top", ha="right",
             color="0.15", linespacing=1.55)

fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
print(f"{'pair':30s} {'cells':>9s} {'km2':>6s} {'median':>9s} {'NMAD':>8s} {'RMSE':>8s}")
for label, fa, fb, n, area, med, nmad, rmse in summary:
    print(f"{label+' '+fa+'-'+fb:30s} {n:9d} {area:6.3f} {med*100:+8.2f}c "
          f"{nmad*100:7.2f}c {rmse*100:7.2f}c")
