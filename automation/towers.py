"""Prime tower placement against the per-extruder printable area. ZERO API calls.

The H2C is a DUAL-NOZZLE printer and its two nozzles do not reach the same bed.
project_settings carries one printable area per extruder:

    extruder_printable_area = ["0x0,325x0,325x320,0x320",     # extruder 1
                               "25x0,330x0,330x320,25x320"]   # extruder 2

so only x in [25, 325] is reachable by BOTH. Objects are unaffected — each is
printed by one extruder and only has to fit that extruder's area — but EVERY
filament in use purges into the prime tower, so on a plate that uses more than
one filament the tower must sit inside the intersection. That makes this a
lid-plate problem exclusively: the lid is the only object carrying black
lettering, so lid plates are the only two-filament plates in the repo.

Bambu Studio does not flag it while laying out, and the plate looks right in
the 3D view. It surfaces only after slicing, as

    return_code -102
    "Found G-code in unprintable area of multi-extruder printers after slicing."

and MakerWorld slices on upload, so the first sign of it is a rejected upload.

Where the bad positions came from: make_cascade seeds every plate's tower at
(15, 200) and moves it only when it COLLIDES with an object, and both its bounds
test and replace_parts' allowed the whole bed instead of the intersection. A lid
big enough to need a 45 degree rotation lies as a diagonal band and leaves the
bottom-left corner empty, so (15, 200) never collided and the seed survived on
exactly the plates where it was illegal. Both placers now bound the tower by
make_cascade.tower_bounds(), which this module shares; here it is the check, and
the in-place repair for the projects already published.

The bound is the printer's declared area, which is about 2 mm stricter than the
slicer: on Dominion 560S plate 3, x=22 is rejected and x=24 slices clean, the
tower's purge geometry sitting slightly inside its nominal origin. Holding the
nominal rectangle to [25, 325] keeps that difference as margin rather than
depending on it.

    towers.py <project.3mf>...          # report; exit 1 if any plate is bad
    towers.py --fix <project.3mf>...    # relocate in place
    towers.py --fix --dry-run <...>     # report the move without writing

--fix relocates by make_cascade's rule (4 mm grid, 15 mm clearance from parts,
furthest from the bed centre) and writes the project back through
filaments.write_settings, so every other zip member is copied byte-for-byte and
nothing goes near Bambu Studio.

Verify a repair by slicing, which is what MakerWorld does:

    /Applications/BambuStudio.app/Contents/MacOS/BambuStudio \
        --slice <plate> --outputdir <dir> <project.3mf>

and reading return_code from result.json — 0, not -102.
"""
import argparse
import json
import math
import re
import sys
import zipfile
from pathlib import Path

import filaments
from make_cascade import plate_columns, tower_bounds

PS = "Metadata/project_settings.config"
MS = "Metadata/model_settings.config"
MODEL = "3D/3dmodel.model"

GRID = 4.0          # placement scan step, as in make_cascade
WIPE_GAP = 15.0     # preferred clearance from printed parts
TIGHT_GAP = 5.0     # fallback clearance when nothing clears WIPE_GAP


# ---- geometry -------------------------------------------------------------

def _proj(o, ax):
    c, s = math.cos(o[4]), math.sin(o[4])
    mid = o[0] * ax[0] + o[1] * ax[1]
    r = o[2] * abs(c * ax[0] + s * ax[1]) + o[3] * abs(-s * ax[0] + c * ax[1])
    return mid - r, mid + r


def sat_overlap(a, b, gap=0.0):
    """a, b: (cx, cy, hx, hy, theta) oriented boxes. Same test make_cascade
    validates its layouts with."""
    for o in (a, b):
        c, s = math.cos(o[4]), math.sin(o[4])
        for ax in ((c, s), (-s, c)):
            a0, a1 = _proj(a, ax)
            b0, b1 = _proj(b, ax)
            if a1 + gap <= b0 or b1 + gap <= a0:
                return False
    return True


def rect_obb(x0, y0, x1, y1):
    return ((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2, 0.0)


def _mesh_bboxes(zf):
    """{member path: {object id: (lo, hi) XYZ}} for every mesh in the project."""
    out = {}
    for name in zf.namelist():
        if not name.endswith(".model"):
            continue
        text = zf.read(name).decode("utf-8", "replace")
        per = {}
        for m in re.finditer(r'<object id="(\d+)".*?<vertices>(.*?)</vertices>',
                             text, re.S):
            vs = re.findall(r'x="([-\d.eE+]+)" y="([-\d.eE+]+)" '
                            r'z="([-\d.eE+]+)"', m.group(2))
            if not vs:
                continue
            xs = [float(v[0]) for v in vs]
            ys = [float(v[1]) for v in vs]
            zs = [float(v[2]) for v in vs]
            per[m.group(1)] = ((min(xs), min(ys), min(zs)),
                               (max(xs), max(ys), max(zs)))
        if per:
            out[name] = per
    return out


def _apply(t, p):
    """3MF transform (row-major 4x3, flattened) applied to a point."""
    x, y, z = p
    return (t[0] * x + t[3] * y + t[6] * z + t[9],
            t[1] * x + t[4] * y + t[7] * z + t[10],
            t[2] * x + t[5] * y + t[8] * z + t[11])


def _local_bbox(root_xml, meshes, oid):
    """An object's own bbox, before its build item is applied. A Bambu object is
    either a mesh or a set of <component> references into 3D/Objects/*.model."""
    m = re.search(rf'<object id="{oid}"[^>]*>(.*?)</object>', root_xml, re.S)
    if not m:
        return None
    lo = [1e9] * 3
    hi = [-1e9] * 3
    for cm in re.finditer(r'<component p:path="([^"]+)" objectid="(\d+)"'
                          r'[^>]*transform="([^"]+)"', m.group(1)):
        path = cm.group(1).lstrip("/")
        box = meshes.get(path, {}).get(cm.group(2))
        if box is None:
            continue
        t = [float(v) for v in cm.group(3).split()]
        # component transforms in these projects are translations, so the
        # corners map to corners and the bbox stays axis-aligned
        for corner in ((box[0][0], box[0][1], box[0][2]),
                       (box[1][0], box[1][1], box[1][2])):
            p = _apply(t, corner)
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    if lo[0] > hi[0]:
        box = meshes.get(MODEL, {}).get(str(oid))
        if box is None:
            return None
        lo, hi = list(box[0]), list(box[1])
    return tuple(lo), tuple(hi)


def plates(zf):
    """[(plate id, [(object id, obb) ...], {extruders used})] in plate-local
    coordinates, obb = (cx, cy, hx, hy, theta)."""
    ps = json.loads(zf.read(PS))
    cfg = zf.read(MS).decode()
    root_xml = zf.read(MODEL).decode()
    meshes = _mesh_bboxes(zf)

    ext = {}
    for om in re.finditer(r'<object id="(\d+)"(.*?)</object>', cfg, re.S):
        ext[om.group(1)] = {int(e) for e in
                            re.findall(r'key="extruder" value="(\d+)"',
                                       om.group(2))}

    items = {m.group(1): [float(v) for v in m.group(2).split()]
             for m in re.finditer(r'<item objectid="(\d+)"[^>]*'
                                  r'transform="([^"]+)"', root_xml)}

    area = [tuple(map(float, p.split("x"))) for p in ps["printable_area"]]
    bed_w = max(p[0] for p in area)
    bed_d = max(p[1] for p in area)

    blocks = re.findall(r'<plate>(.*?)</plate>', cfg, re.S)
    cols = plate_columns(len(blocks))
    out = []
    for i, block in enumerate(blocks):
        pid = i + 1
        ox = (pid - 1) % cols * bed_w * 1.2
        oy = -((pid - 1) // cols) * bed_d * 1.2
        obbs = []
        used = set()
        for oid in re.findall(r'key="object_id" value="(\d+)"', block):
            used |= ext.get(oid, set())
            t = items.get(oid)
            box = _local_bbox(root_xml, meshes, oid)
            if t is None or box is None:
                continue
            (lx0, ly0, lz0), (lx1, ly1, lz1) = box
            c = _apply(t, ((lx0 + lx1) / 2, (ly0 + ly1) / 2, (lz0 + lz1) / 2))
            obbs.append((oid, (c[0] - ox, c[1] - oy,
                               (lx1 - lx0) / 2, (ly1 - ly0) / 2,
                               math.atan2(t[1], t[0]))))
        out.append((pid, obbs, used))
    return out


# ---- check / fix ----------------------------------------------------------

def tower_size(ps):
    return float(ps.get("prime_tower_width", 35))


def problems(path):
    """[(plate id, x, y, reason)] for every multi-filament plate whose tower
    escapes the extruder intersection."""
    zf = zipfile.ZipFile(path)
    ps = json.loads(zf.read(PS))
    if not ps.get("enable_prime_tower", 1):
        return []
    bx0, by0, bx1, by1 = tower_bounds(ps)
    w = tower_size(ps)
    wx = [float(v) for v in ps.get("wipe_tower_x", [])]
    wy = [float(v) for v in ps.get("wipe_tower_y", [])]
    bad = []
    for pid, _obbs, used in plates(zf):
        if len(used) < 2 or pid > len(wx):
            continue
        x, y = wx[pid - 1], wy[pid - 1]
        why = []
        if x < bx0 or x + w > bx1:
            why.append(f"x {x:g}..{x + w:g} outside {bx0:g}..{bx1:g}")
        if y < by0 or y + w > by1:
            why.append(f"y {y:g}..{y + w:g} outside {by0:g}..{by1:g}")
        if why:
            bad.append((pid, x, y, "; ".join(why)))
    return bad


def place(ps, obbs):
    """A legal tower position for one plate, or None. make_cascade's rule:
    4 mm grid, prefer WIPE_GAP clearance, pick the spot furthest from the bed
    centre so the tower lands in a free corner."""
    bx0, by0, bx1, by1 = tower_bounds(ps)
    w = tower_size(ps)
    area = [tuple(map(float, p.split("x"))) for p in ps["printable_area"]]
    bed_w = max(p[0] for p in area)
    bed_d = max(p[1] for p in area)
    for gap in (WIPE_GAP, TIGHT_GAP):
        best = None
        gy = by0
        while gy + w <= by1:
            gx = bx0
            while gx + w <= bx1:
                t = rect_obb(gx, gy, gx + w, gy + w)
                if not any(sat_overlap(t, ob, gap) for _, ob in obbs):
                    cx = gx + w / 2 - bed_w / 2
                    cy = gy + w / 2 - bed_d / 2
                    d2 = cx * cx + cy * cy
                    if best is None or d2 > best[0]:
                        best = (d2, gx, gy)
                gx += GRID
            gy += GRID
        if best:
            return best[1], best[2]
    return None


def fix(path, dry=False):
    """Relocate every illegal tower. Returns the list of moves made."""
    zf = zipfile.ZipFile(path)
    ps = json.loads(zf.read(PS))
    bad = {p[0] for p in problems(path)}
    if not bad:
        return []
    wx = [float(v) for v in ps["wipe_tower_x"]]
    wy = [float(v) for v in ps["wipe_tower_y"]]
    moves = []
    for pid, obbs, _used in plates(zf):
        if pid not in bad:
            continue
        spot = place(ps, obbs)
        if spot is None:
            print(f"  plate {pid}: no legal tower position exists - left at "
                  f"({wx[pid - 1]:g},{wy[pid - 1]:g})")
            continue
        moves.append((pid, wx[pid - 1], wy[pid - 1], spot[0], spot[1]))
        wx[pid - 1], wy[pid - 1] = spot
    if moves and not dry:
        ps["wipe_tower_x"] = [f"{v:g}" for v in wx]
        ps["wipe_tower_y"] = [f"{v:g}" for v in wy]
        zf.close()
        filaments.write_settings(Path(path), ps)
    return moves


def main():
    ap = argparse.ArgumentParser(
        description="prime tower vs per-extruder printable area")
    ap.add_argument("projects", nargs="+")
    ap.add_argument("--fix", action="store_true",
                    help="relocate illegal towers in place")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --fix, report the move without writing")
    args = ap.parse_args()

    hit = 0
    for p in args.projects:
        bad = problems(p)
        if not bad:
            print(f"OK   {Path(p).name}")
            continue
        hit += 1
        print(f"BAD  {Path(p).name}")
        for pid, x, y, why in bad:
            print(f"  plate {pid}: tower at ({x:g},{y:g}) - {why}")
        if args.fix:
            for pid, ox, oy, nx, ny in fix(p, dry=args.dry_run):
                print(f"  plate {pid}: tower ({ox:g},{oy:g}) -> ({nx:g},{ny:g})"
                      + ("  [dry run]" if args.dry_run else ""))
    return 1 if hit and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
