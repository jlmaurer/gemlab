"""Fig 1: study-area map for the PMFS data descriptor.

Main panel: GMRT shaded relief, GEM active faults (PMFS highlighted),
numbered survey sites. Inset: Central America plate context.
"""
import json

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LightSource
from matplotlib.patches import Rectangle
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import rasterio

SCRATCH = ("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-"
           "jlmd9g-umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
           "b7fdd7cc-b0ba-44e1-8a1c-4965a7a238ea/scratchpad")
OUT = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/"
       "My Drive/Guatemala/Spring_Campaign/SITES/figures/fig1_study_area.png")

# Sites from Table 1 (number, name, lat, lon, method)
SITES = [
    (1, "La Laguna", 14.8420, -90.3046, "lidar"),
    (2, "Rio Tambor", 14.9285, -89.8198, "lidar"),
    (3, "Gualán", 15.1289, -89.3272, "lidar"),
    (4, "Mellon Farm", 15.0103, -89.5941, "lidar"),
    (5, "Carillabas", 15.4205, -88.7789, "lidar"),
    (6, "Finca del Eden", 15.5565, -88.8935, "lidar"),
    (7, "La Tinta", 15.3222, -89.8641, "lidar"),
    (8, "Military Base", 15.3146, -89.9103, "lidar"),
    (9, "Museo Quirigua", 15.2705, -89.0399, "lidar"),
    (10, "Byron's Ranch", 15.6193, -89.0524, "sfm"),
]

EXTENT = [-91.4, -88.2, 14.0, 16.2]  # W, E, S, N

# ---------------- topography ----------------
with rasterio.open(f"{SCRATCH}/mapdata/gmrt_topo.tif") as src:
    z = src.read(1).astype(float)
    b = src.bounds
topo_extent = [b.left, b.right, b.bottom, b.top]

ls = LightSource(azdeg=315, altdeg=45)
zpos = np.where(z < 0, 0, z)
hs = ls.hillshade(zpos, vert_exag=0.00002, dx=1, dy=1)  # degrees grid; exaggeration tuned below
# recompute with metric-ish scaling: 1 px ~ 170 m
hs = ls.hillshade(zpos, vert_exag=1.0, dx=170.0, dy=170.0)

# grayscale land relief, flat pale ocean
rgb = np.repeat(hs[:, :, None], 3, axis=2)
rgb = 0.35 + 0.65 * rgb  # brighten
ocean_color = np.array([0.816, 0.878, 0.914])
mask = z < 0
rgb[mask] = ocean_color

# ---------------- faults ----------------
gj = json.load(open(f"{SCRATCH}/mapdata/gem_active_faults.geojson"))

def segments(feat):
    g = feat["geometry"]
    parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
    return [np.array([(p[0], p[1]) for p in part]) for part in parts]

pmfs_names = {"Polochic Fault", "Polochic Fault-Cuilco Segment",
              "Motagua Fault", "Western Motagua Fault", "Swan Islands Transform"}
pmfs, others = [], []
for f in gj["features"]:
    name = f["properties"].get("name") or ""
    for seg in segments(f):
        x, y = seg[:, 0], seg[:, 1]
        if (x.max() < EXTENT[0] - 1 or x.min() > EXTENT[1] + 1 or
                y.max() < EXTENT[2] - 1 or y.min() > EXTENT[3] + 1):
            continue
        (pmfs if name in pmfs_names else others).append(seg)

# ---------------- figure ----------------
proj = ccrs.PlateCarree()
fig = plt.figure(figsize=(7.09, 5.6), dpi=300)
ax = fig.add_axes([0.07, 0.06, 0.90, 0.90], projection=proj)
ax.set_extent(EXTENT, crs=proj)

ax.imshow(rgb, extent=topo_extent, transform=proj, origin="upper",
          interpolation="bilinear", zorder=0)

ax.add_feature(cfeature.NaturalEarthFeature("physical", "lakes", "10m"),
               facecolor=ocean_color, edgecolor="0.45", linewidth=0.4, zorder=1)
ax.add_feature(cfeature.NaturalEarthFeature("cultural", "admin_0_boundary_lines_land", "10m"),
               facecolor="none", edgecolor="0.25", linewidth=0.7,
               linestyle=(0, (4, 2)), zorder=3)
ax.coastlines("10m", linewidth=0.5, color="0.35", zorder=2)

for seg in others:
    ax.plot(seg[:, 0], seg[:, 1], color="0.45", lw=0.6, transform=proj, zorder=4)
for seg in pmfs:
    ax.plot(seg[:, 0], seg[:, 1], color="#B2182B", lw=1.6,
            transform=proj, zorder=5, solid_capstyle="round")

halo = [pe.withStroke(linewidth=2.5, foreground="white")]
fault_labels = [
    ("Polochic Fault", -90.55, 15.47, -8),
    ("Motagua Fault", -90.05, 14.98, 22),
    ("Swan Islands Transform", -88.55, 16.02, 3),
]
for txt, x, y, rot in fault_labels:
    ax.text(x, y, txt, transform=proj, fontsize=7.5, style="italic",
            color="#B2182B", rotation=rot, ha="center", va="center",
            path_effects=halo, zorder=6)

# Lake Izabal + Guatemala City labels
ax.text(-89.15, 15.48, "Lake\nIzabal", transform=proj, fontsize=7,
        color="0.30", ha="center", va="center", style="italic", path_effects=halo, zorder=6)
ax.plot(-90.535, 14.613, marker="s", ms=4, mfc="0.2", mec="white", mew=0.5,
        transform=proj, zorder=6)
ax.text(-90.50, 14.575, "Guatemala City", transform=proj, fontsize=7,
        color="0.15", ha="left", va="top", path_effects=halo, zorder=6)

# relative plate-motion arrow (Caribbean moving E rel. North America)
ax.annotate("", xy=(-88.95, 16.05), xytext=(-89.55, 16.05),
            xycoords=proj._as_mpl_transform(ax), textcoords=proj._as_mpl_transform(ax),
            arrowprops=dict(arrowstyle="-|>", color="0.15", lw=1.4), zorder=6)
ax.text(-89.25, 16.10, "Caribbean plate motion\n~20 mm/yr", transform=proj,
        fontsize=6.5, ha="center", va="bottom", color="0.15", path_effects=halo, zorder=6)

# ---------------- sites ----------------
label_offsets = {  # per-site nudges (dx, dy in degrees) to avoid collisions
    1: (0.05, -0.10), 2: (-0.05, -0.11), 3: (0.07, -0.09), 4: (0.02, -0.11),
    5: (0.13, -0.07), 6: (0.16, 0.085), 7: (0.02, 0.09), 8: (-0.24, -0.02),
    9: (0.05, -0.11), 10: (-0.16, 0.09),
}
for num, name, lat, lon, method in SITES:
    marker = "o" if method == "lidar" else "D"
    ax.plot(lon, lat, marker=marker, ms=9 if method == "lidar" else 10.5,
            mfc="#2166AC", mec="white", mew=1.0, transform=proj, zorder=7)
    ax.text(lon, lat, str(num), transform=proj,
            fontsize=5.5 if num < 10 else 4.8, color="white",
            ha="center", va="center", zorder=8, fontweight="bold")
    dx, dy = label_offsets[num]
    ax.text(lon + dx, lat + dy, name, transform=proj, fontsize=6.5,
            color="#1A3E6E", ha="center", va="center", path_effects=halo, zorder=7)

# marker-type legend (upper left)
ax.plot(-91.28, 16.05, marker="o", ms=8, mfc="#2166AC", mec="white", mew=1.0,
        transform=proj, zorder=7)
ax.text(-91.21, 16.05, "UAV lidar site", transform=proj, fontsize=6.5,
        va="center", color="0.15", path_effects=halo, zorder=7)
ax.plot(-91.28, 15.93, marker="D", ms=7.5, mfc="#2166AC", mec="white", mew=1.0,
        transform=proj, zorder=7)
ax.text(-91.21, 15.93, "UAV SfM site", transform=proj, fontsize=6.5,
        va="center", color="0.15", path_effects=halo, zorder=7)

# graticule
gl = ax.gridlines(draw_labels=True, linewidth=0.3, color="0.7", alpha=0.6,
                  xlocs=np.arange(-92, -87, 1), ylocs=np.arange(13, 17, 0.5))
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {"size": 7}
gl.ylabel_style = {"size": 7}

# scale bar (100 km at ~15N: 1 deg lon ~ 107.6 km)
lat0 = 14.17
x0 = -91.25
dlon = 50 / 107.6
ax.plot([x0, x0 + dlon], [lat0, lat0], color="0.1", lw=2.2, transform=proj, zorder=7,
        solid_capstyle="butt")
ax.text(x0 + dlon / 2, lat0 + 0.04, "50 km", transform=proj, fontsize=6.5,
        ha="center", color="0.1", path_effects=halo, zorder=7)

# ---------------- inset ----------------
axi = fig.add_axes([0.703, 0.085, 0.26, 0.26], projection=proj)
axi.set_extent([-95.5, -82, 10.0, 20.5], crs=proj)
axi.add_feature(cfeature.LAND.with_scale("50m"), facecolor="0.88")
axi.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor=ocean_color)
axi.coastlines("50m", linewidth=0.35, color="0.4")
axi.add_feature(cfeature.NaturalEarthFeature("cultural", "admin_0_boundary_lines_land", "50m"),
                facecolor="none", edgecolor="0.55", linewidth=0.3)
for seg in pmfs:
    axi.plot(seg[:, 0], seg[:, 1], color="#B2182B", lw=0.9, transform=proj)
axi.add_patch(Rectangle((EXTENT[0], EXTENT[2]), EXTENT[1] - EXTENT[0],
                        EXTENT[3] - EXTENT[2], fill=False, edgecolor="#2166AC",
                        lw=1.2, transform=proj, zorder=5))
axi.text(-90.6, 17.9, "North American\nplate", fontsize=5.5, ha="center",
         transform=proj, color="0.2")
axi.text(-85.6, 13.4, "Caribbean\nplate", fontsize=5.5, ha="center",
         transform=proj, color="0.2")
axi.text(-93.2, 11.7, "Cocos\nplate", fontsize=5.5, ha="center",
         transform=proj, color="0.2")
for spine in axi.spines.values():
    spine.set_linewidth(0.8)

fig.savefig(OUT, dpi=300, facecolor="white")
print("wrote", OUT)
