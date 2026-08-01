#!/usr/bin/env python
"""Replace the 3-D 'promoted' CRS in the Gualan/Rio Tambor LAZ with plain EPSG:32616.

Why: the promoted-to-3D projected CRS has no EPSG code of its own (EPSG defines no
UTM-16N-with-ellipsoidal-height), so consumers that scrape an authority code out of
the WKT find only the axis LENGTHUNIT code 9001 (metre). OpenTopography ingested
that as the horizontal datum. A WKT1 COMPD_CS does not help - it also exposes 9001
as its last authority code. Plain 2-D EPSG:32616 resolves to 32616 by every route.

How: the replacement WKT is shorter than the original, and the LAS spec allows the
WKT VLR payload to be null-padded, so the payload is overwritten in place at the
same declared length. No VLR length changes => no byte offsets move => the
compressed point data is untouched. That avoids decompressing and recompressing
~18 GB, and is verified byte-for-byte below.
"""
import glob
import hashlib
import os
import shutil
import struct
import sys

WKT_2D = open("/private/tmp/claude-502/-Users-jlmd9g-Library-CloudStorage-GoogleDrive-jlmd9g-"
              "umsystem-edu-My-Drive-Guatemala-Spring-Campaign/"
              "db3b07b4-fdbc-4d8c-bfa1-1a844edbe582/scratchpad/coreg/crs_2d.wkt").read().strip()


def find_wkt_vlrs(buf):
    """Every WKT-bearing VLR (record_id 2112), as (user_id, payload_offset, payload_len).

    PDAL writes two: the standard LASF_Projection one and a 'liblas' OGR-variant
    copy. Both carry WKT and either could be what a consumer reads, so both are
    patched.
    """
    header_size = struct.unpack_from("<H", buf, 94)[0]
    n_vlr = struct.unpack_from("<I", buf, 100)[0]
    off = header_size
    found = []
    for _ in range(n_vlr):
        user_id = buf[off + 2:off + 18].split(b"\0")[0].decode("ascii", "replace")
        record_id = struct.unpack_from("<H", buf, off + 18)[0]
        rec_len = struct.unpack_from("<H", buf, off + 20)[0]
        payload = off + 54
        if record_id == 2112:
            found.append((user_id, payload, rec_len))
        off = payload + rec_len
    return found


def resolves_to_32616(wkt):
    """True only if the WKT's own top-level authority code is 32616.

    A compound or promoted-3D CRS has no top-level code, so a consumer scraping
    the string finds the trailing axis-unit code 9001 instead - the bug being fixed.
    """
    from osgeo import osr
    osr.UseExceptions()
    sr = osr.SpatialReference()
    try:
        sr.SetFromUserInput(wkt)
    except Exception:
        return False
    return sr.GetAuthorityCode(None) == "32616"


def point_data_digest(path):
    """SHA-256 of everything from offset_to_point_data onward."""
    with open(path, "rb") as fh:
        head = fh.read(256)
        start = struct.unpack_from("<I", head, 96)[0]
        fh.seek(start)
        h = hashlib.sha256()
        while True:
            b = fh.read(1 << 22)
            if not b:
                break
            h.update(b)
        return h.hexdigest(), start


def patch(path, dry_run=False):
    name = os.path.basename(path)
    with open(path, "rb") as fh:
        head = fh.read(1 << 16)
    vlrs = find_wkt_vlrs(head)
    if not vlrs:
        return f"{name}: NO WKT VLR - skipped"
    new = WKT_2D.encode("utf-8")
    todo, notes = [], []
    for user_id, off, rec_len in vlrs:
        old = head[off:off + rec_len].split(b"\0")[0].decode("utf-8", "replace")
        if resolves_to_32616(old):
            notes.append(f"{user_id}=already-32616")
            continue
        if len(new) + 1 > rec_len:
            notes.append(f"{user_id}=TOO-LONG({len(new)}>{rec_len})")
            continue
        todo.append((user_id, off, rec_len, len(old)))
    if not todo:
        return f"{name}: nothing to do [{', '.join(notes)}]"
    if dry_run:
        d = ", ".join(f"{u}: {ol}->{len(new)} in {rl}B" for u, _, rl, ol in todo)
        return f"{name}: would patch {len(todo)} VLR(s) [{d}]"
    before, start = point_data_digest(path)
    with open(path, "r+b") as fh:
        for _, off, rec_len, _ in todo:
            fh.seek(off)
            fh.write(new + b"\0" * (rec_len - len(new)))
    after, start2 = point_data_digest(path)
    ok = (before == after) and (start == start2)
    return (f"{name}: patched {len(todo)} VLR(s) | point data byte-identical: {ok}"
            + (f" [{', '.join(notes)}]" if notes else ""))


def main():
    dry = "--dry-run" in sys.argv
    targets = [a for a in sys.argv[1:] if not a.startswith("--")]
    for t in targets:
        for f in sorted(glob.glob(t)):
            print("  " + patch(f, dry_run=dry), flush=True)


if __name__ == "__main__":
    main()
