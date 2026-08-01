"""Fig 3: Rio Tambor point-cloud visualization.

(a) oblique 3-D view of a 700 x 700 m block (flight 220845), ground colored
by elevation, non-ground (vegetation) green.
(b) 6-m-wide classified cross-section through vegetated floodplain.
"""
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

SCRATCH = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
           "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
           "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad")
OUT = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
       "My Drive/Guatemala/Spring_Campaign/SITES/figures/fig3_riotambor_pointcloud.png")

d = np.load(f"{SCRATCH}/rt_subsets.npz")
A, B = d["A"], d["B"]

rng = np.random.default_rng(42)

# UTM coords for the approximate fault location:
# 841771.1E,1652811.4N (UTM 16N, WGS84)
# look direction should be roughly from the northeast looking southwest.
# NOTE: that easting can only be UTM 15N at this longitude (the LAZ is 16N,
# easting ~196 km); converted 15N -> 16N it is 196250.9 E, 1652298.1 N
# (lon -89.82344, lat 14.92806). Subsets in rt_subsets.npz are extracted
# centered there: block A 700 x 700 m, swath B 600 m W-E x 6 m through it.
FAULT_LONLAT = (-89.82344, 14.92806)

# Motagua Fault trace through this area from the GEM Global Active Faults
# Database (Styron & Pagani, 2020). Locally the GEM trace is a single straight
# segment; endpoints below are its two vertices nearest the block, reprojected
# EPSG:4326 -> EPSG:32616. Note the GEM trace is digitized at regional scale
# and may be locally offset from the true scarp by tens of metres.
FAULT_SEG = np.array([[195307.0, 1652057.9], [198457.0, 1653108.5]])

ground = A[A[:, 3] == 2]
canopy = A[A[:, 3] == 1]
ground = ground[rng.random(len(ground)) < 4_000_000 / len(ground)]
canopy = canopy[rng.random(len(canopy)) < 1_200_000 / len(canopy)]

fig = plt.figure(figsize=(7.09, 7.6), dpi=300)

# ---------------- (a) oblique 3-D ----------------
ax = fig.add_axes([0.0, 0.24, 1.0, 0.76], projection="3d", computed_zorder=False)
x0, y0 = ground[:, 0].min(), ground[:, 1].min()
zmin, zmax = np.percentile(ground[:, 2], [1, 99.5])

sc = ax.scatter(ground[:, 0] - x0, ground[:, 1] - y0, ground[:, 2], c=ground[:, 2],
                cmap="viridis", vmin=zmin, vmax=zmax, s=0.06, linewidths=0,
                rasterized=True, zorder=1)
ax.scatter(canopy[:, 0] - x0, canopy[:, 1] - y0, canopy[:, 2], color="#1F5A24",
           s=0.05, linewidths=0, alpha=0.55, rasterized=True, zorder=2)

ax.set_box_aspect((1, 1, 0.30))
ax.view_init(elev=38, azim=45)   # camera in the NE, looking SW
ax.set_axis_off()
ax.set_xlim(0, 700)
ax.set_ylim(0, 700)

# --- draped overlay lines: fault trace (solid) and profile location (dashed) ---
# coarse ground-elevation grid (10 m bins of the decimated ground points)
CELL = 10.0
gx = ((ground[:, 0] - x0) / CELL).astype(int)
gy = ((ground[:, 1] - y0) / CELL).astype(int)
nxc, nyc = gx.max() + 1, gy.max() + 1
zsum = np.zeros((nxc, nyc)); zcnt = np.zeros((nxc, nyc))
np.add.at(zsum, (gx, gy), ground[:, 2]); np.add.at(zcnt, (gx, gy), 1)
zgrid = np.divide(zsum, zcnt, out=np.full_like(zsum, np.nan), where=zcnt > 0)

def drape(xs, ys, lift=4.0):
    """Ground elevation (+lift) at block-local coords, NaN outside coverage."""
    ix = np.clip((xs / CELL).astype(int), 0, nxc - 1)
    iy = np.clip((ys / CELL).astype(int), 0, nyc - 1)
    return zgrid[ix, iy] + lift

# fault trace clipped to the block, sampled every 5 m
(fx0, fy0), (fx1, fy1) = FAULT_SEG
tt = np.linspace(0, 1, 800)
fx = fx0 + tt * (fx1 - fx0) - x0
fy = fy0 + tt * (fy1 - fy0) - y0
inb = (fx >= 0) & (fx <= 700) & (fy >= 0) & (fy <= 700)
fz = drape(fx[inb], fy[inb])
ax.plot(fx[inb], fy[inb], fz, color="#B2182B", lw=2.0, zorder=6,
        solid_capstyle="round")

# profile line (the (b) swath): W-E at the fault y, use swath ground medians
gswath = B[B[:, 3] == 2]
order = np.argsort(gswath[:, 0])
xs_b = gswath[order, 0] - x0
bins = np.arange(xs_b.min(), xs_b.max() + 5, 5.0)
ib = np.digitize(xs_b, bins)
px_line = np.array([xs_b[ib == k].mean() for k in np.unique(ib)])
pz_line = np.array([np.median(gswath[order, 2][ib == k]) for k in np.unique(ib)])
py_line = np.full_like(px_line, gswath[:, 1].mean() - y0)
ax.plot(px_line, py_line, pz_line + 4.0, color="0.1", lw=1.6, zorder=7,
        linestyle=(0, (5, 3)))

cax = fig.add_axes([0.88, 0.30, 0.018, 0.20])
cb = fig.colorbar(sc, cax=cax)
cb.set_label("Ground elevation (m, ellipsoidal)", fontsize=6.5)
cb.ax.tick_params(labelsize=6)

leg = fig.legend(handles=[
    Line2D([], [], marker="o", ls="none", ms=5, mfc="#1F5A24", mec="none",
           label="Vegetation / non-ground returns"),
    Line2D([], [], marker="o", ls="none", ms=5, mfc="#3B7BB8", mec="none",
           label="Ground returns (colored by elevation)"),
    Line2D([], [], color="#B2182B", lw=2.0,
           label="Motagua Fault trace (GEM database)"),
    Line2D([], [], color="0.1", lw=1.6, linestyle=(0, (5, 3)),
           label="Profile shown in (b)")],
    loc="upper left", bbox_to_anchor=(0.06, 0.985), fontsize=6.5, frameon=False)

fig.text(0.06, 0.975, "(a)", fontsize=10, fontweight="bold")
fig.text(0.30, 0.28, "700 m × 700 m block\nview toward SW", fontsize=6.5,
         color="0.25", ha="center")

# ---------------- location inset ----------------
import cartopy.crs as ccrs
import cartopy.feature as cfeature

axi = fig.add_axes([0.71, 0.775, 0.25, 0.185], projection=ccrs.PlateCarree())
axi.set_extent([-93.3, -87.6, 12.9, 18.3], crs=ccrs.PlateCarree())
axi.add_feature(cfeature.LAND.with_scale("50m"), facecolor="0.90")
axi.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#D0E0E9")
axi.coastlines("50m", linewidth=0.35, color="0.45")
axi.add_feature(cfeature.NaturalEarthFeature(
    "cultural", "admin_0_boundary_lines_land", "50m"),
    facecolor="none", edgecolor="0.5", linewidth=0.35)
axi.plot(*FAULT_LONLAT, marker="o", ms=4.5, mfc="#B2182B", mec="white",
         mew=0.7, transform=ccrs.PlateCarree(), zorder=5)
axi.text(FAULT_LONLAT[0], FAULT_LONLAT[1] - 0.45, "Rio Tambor", fontsize=5.5,
         ha="center", va="top", color="#B2182B", transform=ccrs.PlateCarree())
axi.text(-90.4, 15.9, "Guatemala", fontsize=5.5, ha="center", color="0.35",
         transform=ccrs.PlateCarree())
for spine in axi.spines.values():
    spine.set_linewidth(0.6)

# ---------------- (b) cross-section ----------------
axb = fig.add_axes([0.09, 0.055, 0.88, 0.16])
gB = B[B[:, 3] == 2]
cB = B[B[:, 3] == 1]
dist_g = gB[:, 0] - B[:, 0].min()
dist_c = cB[:, 0] - B[:, 0].min()
axb.scatter(dist_c, cB[:, 2], s=0.15, color="#2C2CD8", linewidths=0, alpha=0.5,
            rasterized=True, label="Vegetation")
axb.scatter(dist_g, gB[:, 2], s=0.15, color="#FFCC00", linewidths=0, alpha=0.8,
            rasterized=True, label="Ground")
axb.set_xlabel("Distance along profile (m, W–E)", fontsize=7)
axb.set_ylabel("Elevation (m)", fontsize=7)
axb.tick_params(labelsize=8)
axb.set_xlim(0, 600)
for s in ["top", "right"]:
    axb.spines[s].set_visible(False)
axb.legend(fontsize=8, frameon=False, markerscale=30, loc="upper right", ncol=2)
fig.text(0.06, 0.215, "(b)", fontsize=10, fontweight="bold")

fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT, "| ground", len(ground), "| canopy", len(canopy), "| B", len(B))
