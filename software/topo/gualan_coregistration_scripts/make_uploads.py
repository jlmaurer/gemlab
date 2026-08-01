#!/usr/bin/env python
"""Write the three Gualan per-flight LAZ files for the OpenTopography submission.

  1. flight 204440  -- from export/Gualan.las, point_source_id 1001-1006
  2. flight 220238  -- from export/Gualan.las, point_source_id 2001-2013
  3. flight 211849  -- from YS-*.las, translated onto the other two and
                       renumbered 1001-1013 -> 3001-3013 so the three files can
                       be merged without a point_source_id collision

All are written as LAS 1.4 point format 7 with a 3-D projected CRS
(EPSG:32616 promoted to 3D) so the ellipsoidal height axis is explicit.
"""
import json
import subprocess
import sys

PDAL = "/Users/jlmd9g/software/miniforge3/envs/opentopo/bin/pdal"
SRC = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/My Drive/"
       "Guatemala/Spring_Campaign/SITES/Gualan/Updated_data")
OUT = ("/Users/jlmd9g/Library/CloudStorage/GoogleDrive-jlmd9g@umsystem.edu/My Drive/"
       "Guatemala/Spring_Campaign/OpenTopography_upload/Gualan")

EXPORT = f"{SRC}/export/Gualan.las"
YS = f"{SRC}/YS-20240123-211849-20240207-082517-F001.las"

# Solved by coreg.py: translation applied to YS-211849 to bring it onto the
# reprocessed export surface.
DX, DY, DZ = -4.460, -0.920, -13.307


def crs_wkt(path):
    with open(path) as fh:
        return " ".join(line.strip() for line in fh if line.strip())


def writer(filename, wkt):
    return {
        "type": "writers.las",
        "filename": filename,
        "compression": True,
        "minor_version": 4,
        "dataformat_id": 7,
        "a_srs": wkt,
        "scale_x": 0.001, "scale_y": 0.001, "scale_z": 0.001,
        "offset_x": "auto", "offset_y": "auto", "offset_z": "auto",
        "software_id": "PDAL - coregistered",
    }


def pipelines(wkt, count=None):
    def reader(fn):
        r = {"type": "readers.las", "filename": fn}
        if count:
            r["count"] = count
        return r

    suffix = "_TEST" if count else ""
    return {
        f"gualan_lidar_pointcloud_20240123-204440{suffix}.laz": [
            reader(EXPORT),
            {"type": "filters.range", "limits": "PointSourceId[1001:1999]"},
        ],
        f"gualan_lidar_pointcloud_20240123-220238{suffix}.laz": [
            reader(EXPORT),
            {"type": "filters.range", "limits": "PointSourceId[2001:2999]"},
        ],
        f"gualan_lidar_pointcloud_20240123-211849_aligned{suffix}.laz": [
            reader(YS),
            {"type": "filters.transformation",
             "matrix": f"1 0 0 {DX}  0 1 0 {DY}  0 0 1 {DZ}  0 0 0 1"},
            {"type": "filters.assign",
             "value": "PointSourceId = PointSourceId + 2000"},
        ],
    }


def main():
    wkt = crs_wkt(sys.argv[1])
    outdir = sys.argv[2]
    count = int(sys.argv[3]) if len(sys.argv) > 3 else None
    for name, stages in pipelines(wkt, count).items():
        target = f"{outdir}/{name}"
        pl = {"pipeline": stages + [writer(target, wkt)]}
        pj = f"/tmp/pl_{name}.json".replace(".laz", "")
        with open(pj, "w") as fh:
            json.dump(pl, fh, indent=2)
        print(f"\n=== {name} ===", flush=True)
        subprocess.run([PDAL, "pipeline", pj], check=True)
        print(f"    wrote {target}", flush=True)


if __name__ == "__main__":
    main()
