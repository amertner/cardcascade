#!/usr/bin/env python3
"""Update a published Bambu Studio project 3MF for a new part revision.

Replaces named objects' meshes with new exports and/or removes label
plates, preserving every placement, rotation, colour (extruder) and
setting in the project. Alignment relies on replacement files being
exported from the SAME CAD origin as the original parts (this is
verified, not assumed).

Usage:
    python3 replace_parts.py PUBLISHED.3mf -o OUT.3mf \
        --replace "Box=Box_560s.3mf" --replace "Lid-3=Lid_560s.3mf" \
        --remove-plates label

  --replace NAME=FILE   replace the meshes of the object called NAME
                        (as shown in Bambu's object list) with the
                        bodies in FILE. Single- and multi-part objects
                        are supported; parts are matched by CAD-centre
                        fingerprint and keep their extruders/matrices.
  --remove-plates TEXT  remove every plate whose name contains TEXT
                        (case-insensitive), including its objects, and
                        re-position remaining objects for Bambu's
                        changed plate grid.
  --allow-resize        accept a replacement whose bounding box differs
                        from the original by more than TOLERANCE_MM
                        (default: refuse - a size change usually means
                        a wrong export).

The script refuses on any ambiguity; it never guesses.
"""

import argparse
import json
import math
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

TOLERANCE_MM = 1.0       # bbox gate for replacements
MATCH_MM = 0.5           # CAD-centre part matching tolerance


def fail(msg):
    sys.exit(f"REFUSING: {msg}")


def parse_meshes(text, scale=1.0):
    """{object id: (verts, tris)} for every mesh-bearing object."""
    meshes = {}
    for om in re.finditer(r'<object id="(\d+)"[^>]*>(.*?)</object>', text, re.S):
        verts = [(float(a) * scale, float(b) * scale, float(c) * scale)
                 for a, b, c in re.findall(
                     r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', om.group(2))]
        tris = re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', om.group(2))
        if verts:
            meshes[int(om.group(1))] = (verts, tris)
    return meshes


def bbox(verts):
    xs, ys, zs = zip(*verts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def centre(verts):
    lo, hi = bbox(verts)
    return tuple((a + b) / 2 for a, b in zip(lo, hi))


def dims(verts):
    lo, hi = bbox(verts)
    return tuple(b - a for a, b in zip(lo, hi))


def mesh_xml(verts, tris):
    return ("\n   <mesh>\n    <vertices>\n"
            + "".join(f'     <vertex x="{x:.9g}" y="{y:.9g}" z="{z:.9g}"/>\n'
                      for x, y, z in verts)
            + "    </vertices>\n    <triangles>\n"
            + "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                      for a, b, c in tris)
            + "    </triangles>\n   </mesh>\n  ")


def load_replacement(path):
    zf = zipfile.ZipFile(path)
    text = zf.read("3D/3dmodel.model").decode()
    unit = re.search(r'unit="(\w+)"', text).group(1)
    scale = {"meter": 1000.0, "millimeter": 1.0}.get(unit)
    if scale is None:
        fail(f"{path}: unsupported unit {unit!r}")
    meshes = parse_meshes(text, scale)
    if meshes:
        return meshes
    # Bambu Studio re-export: root only references components in sub-model
    # files; part meshes are centred and the CAD position lives in the
    # upload's own model_settings source_offset (matching the fingerprint
    # convention of the published projects).
    comps = re.findall(r'<component p:path="([^"]+)" objectid="(\d+)"', text)
    try:
        ms = zf.read("Metadata/model_settings.config").decode()
    except KeyError:
        fail(f"{path}: no meshes in root model and no model_settings")
    offs = []
    for pm in re.finditer(r'<part id="\d+"[^>]*>(.*?)</part>', ms, re.S):
        offs.append(tuple(
            float(re.search(rf'key="source_offset_{a}" value="([^"]*)"',
                            pm.group(1)).group(1)) for a in "xyz"))
    if len(offs) != len(comps):
        fail(f"{path}: {len(comps)} components but {len(offs)} parts "
             f"in its model_settings")
    subs = {}
    out = {}
    for i, ((p, oid), off) in enumerate(zip(comps, offs), 1):
        p = p.lstrip("/")
        if p not in subs:
            st = zf.read(p).decode()
            su = re.search(r'unit="(\w+)"', st)
            sscale = {"meter": 1000.0, "millimeter": 1.0}.get(
                su.group(1) if su else "millimeter")
            subs[p] = parse_meshes(st, sscale)
        verts, tris = subs[p][int(oid)]
        out[i] = ([(x + off[0], y + off[1], z + off[2])
                   for x, y, z in verts], tris)
    return out


def plate_columns(n):
    value = math.sqrt(n)
    return round(value) + 1 if value > round(value) else round(value)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("published")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--replace", action="append", default=[],
                    metavar="NAME=FILE")
    ap.add_argument("--remove-plates", default=None, metavar="TEXT")
    ap.add_argument("--remove-objects", action="append", default=[],
                    metavar="PLATE:NAME1,NAME2",
                    help="remove objects with these names from the plate "
                         "whose name contains PLATE (the plate itself stays)")
    ap.add_argument("--plate-name", action="append", default=[],
                    metavar="OLD=NEW", help="rename a plate (exact match)")
    ap.add_argument("--rename-object", action="append", default=[],
                    metavar="OLD=NEW", help="rename an object (exact match)")
    ap.add_argument("--allow-resize", action="store_true")
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="swap_"))
    with zipfile.ZipFile(args.published) as zf:
        zf.extractall(work)
    root_p = work / "3D/3dmodel.model"
    cfg_p = work / "Metadata/model_settings.config"
    xml = root_p.read_text()
    cfg = cfg_p.read_text()

    # ---- project geometry facts ----
    ps = json.loads((work / "Metadata/project_settings.config").read_text())
    area = [tuple(map(float, p.split("x"))) for p in ps["printable_area"]]
    bed_w = max(p[0] for p in area)
    bed_d = max(p[1] for p in area)
    stride_x, stride_y = bed_w * 1.2, bed_d * 1.2
    print(f"printer: {ps.get('printer_model')} bed {bed_w:g}x{bed_d:g}")

    # objects: id -> (name, [(part id, part block)]), part meshes via components
    objects = {}
    for om in re.finditer(r'<object id="(\d+)">(.*?)</object>', cfg, re.S):
        name = re.search(r'key="name" value="([^"]*)"', om.group(2)).group(1)
        parts = re.findall(r'<part id="(\d+)"', om.group(2))
        objects[om.group(1)] = (name, parts)
    comps = {}   # object id -> [(path, component id)]
    for om in re.finditer(
            r'<object id="(\d+)"[^>]*>\s*<components>(.*?)</components>', xml, re.S):
        comps[om.group(1)] = re.findall(
            r'p:path="([^"]+)" objectid="(\d+)"', om.group(2))
    plates = []  # (plater_id, name, [object ids])
    for pm in re.finditer(r'<plate>(.*?)</plate>', cfg, re.S):
        pid = int(re.search(r'plater_id" value="(\d+)"', pm.group(1)).group(1))
        pname = re.search(r'plater_name" value="([^"]*)"', pm.group(1))
        objs = re.findall(r'object_id" value="(\d+)"', pm.group(1))
        plates.append((pid, pname.group(1) if pname else "", objs))

    # ---------------- replacements ----------------
    for spec in args.replace:
        name, _, file = spec.partition("=")
        if not _:
            fail(f"--replace needs NAME=FILE, got {spec!r}")
        targets = [oid for oid, (n, _) in objects.items() if n == name]
        if len(targets) != 1:
            fail(f"object named {name!r}: found {len(targets)}, need exactly 1 "
                 f"(names: {sorted(set(n for n, _ in objects.values()))})")
        oid = targets[0]
        new_meshes = load_replacement(file)
        part_ids = [int(cid) for _, cid in comps[oid]]
        if len(new_meshes) != len(part_ids):
            fail(f"{name}: original has {len(part_ids)} parts, "
                 f"{file} has {len(new_meshes)} bodies")

        # source offsets = original CAD centres per part
        blk = re.search(rf'<object id="{oid}">.*?</object>', cfg, re.S).group(0)
        src, old_stats = {}, {}
        for pm in re.finditer(r'<part id="(\d+)"[^>]*>(.*?)</part>', blk, re.S):
            so = [re.search(rf'key="source_offset_{a}" value="([^"]*)"',
                            pm.group(2)) for a in "xyz"]
            if not all(so):
                fail(f"{name} part {pm.group(1)}: no source_offset recorded; "
                     "cannot align safely")
            src[int(pm.group(1))] = tuple(float(m.group(1)) for m in so)

        # old meshes per part (for K and the dimension gate)
        files = {p for p, _ in comps[oid]}
        old_meshes = {}
        for f in files:
            old_meshes.update(parse_meshes((work / f.lstrip("/")).read_text()))

        # match new bodies to parts by CAD centre; dimension gate
        mapping, used = {}, set()
        for pid in part_ids:
            best, bd = None, 1e9
            for nid, (verts, _) in new_meshes.items():
                if nid in used:
                    continue
                d = math.dist(centre(verts), src[pid])
                if d < bd:
                    best, bd = nid, d
            if bd > MATCH_MM:
                fail(f"{name} part {pid}: no new body within {MATCH_MM}mm of "
                     f"CAD centre {src[pid]} (closest: {bd:.2f}mm). Was the "
                     "replacement exported from the same CAD origin?")
            do = dims(old_meshes[pid][0])
            dn = dims(new_meshes[best][0])
            delta = max(abs(a - b) for a, b in zip(do, dn))
            if delta > TOLERANCE_MM and not args.allow_resize:
                fail(f"{name} part {pid}: size changed "
                     f"{tuple(round(x,2) for x in do)} -> "
                     f"{tuple(round(x,2) for x in dn)} (max {delta:.2f}mm). "
                     "Wrong export? Check the embossed model number. "
                     "(--allow-resize to override)")
            mapping[pid] = best
            used.add(best)
            print(f"  {name} part {pid} <- body {best} "
                  f"(centre delta {bd:.3f}mm, size delta {delta:.3f}mm, "
                  f"{len(new_meshes[best][1])} tris)")

        # write new meshes in the original file-coordinate convention
        counts = {}
        for f in files:
            fp = work / f.lstrip("/")
            s = fp.read_text()
            def repl(m):
                pid = int(m.group(2))
                if pid not in mapping:
                    return m.group(0)
                verts, tris = new_meshes[mapping[pid]]
                k = tuple(s0 - m0 for s0, m0 in
                          zip(src[pid], centre(old_meshes[pid][0])))
                shifted = [(x - k[0], y - k[1], z - k[2]) for x, y, z in verts]
                counts[pid] = len(tris)
                return m.group(1) + mesh_xml(shifted, tris) + m.group(3)
            s = re.sub(r'(<object id="(\d+)"[^>]*>).*?(</object>)',
                       repl, s, flags=re.S)
            fp.write_text(s)

        # face counts in model_settings
        nblk = blk
        for pid, fc in counts.items():
            nblk = re.sub(
                rf'(<part id="{pid}".*?mesh_stat face_count=")\d+',
                rf'\g<1>{fc}', nblk, flags=re.S)
        nblk = re.sub(r'<metadata face_count="\d+"/>',
                      f'<metadata face_count="{sum(counts.values())}"/>',
                      nblk, count=1)
        cfg = cfg.replace(blk, nblk)

    # ---------------- object/plate removal ----------------
    def purge_object(oid):
        """Remove an object entirely: meshes (if exclusively owned), root
        entries, settings, assemble and plate-instance references."""
        nonlocal xml, cfg
        for f, _cid in comps.get(oid, []):
            if sum(1 for c in comps.values() for ff, _ in c if ff == f) == 1:
                (work / f.lstrip("/")).unlink()
                rp = work / "3D/_rels/3dmodel.model.rels"
                rp.write_text(re.sub(
                    rf'\s*<Relationship Target="{re.escape(f)}"[^>]*/>',
                    "", rp.read_text()))
        comps.pop(oid, None)
        xml = re.sub(rf'\s*<object id="{oid}" .*?</object>', "",
                     xml, count=1, flags=re.S)
        xml = re.sub(rf'\s*<item objectid="{oid}" [^>]*/>', "", xml, count=1)
        cfg = re.sub(rf'\s*<object id="{oid}">.*?</object>', "",
                     cfg, count=1, flags=re.S)
        cfg = re.sub(rf'\s*<assemble_item object_id="{oid}" [^>]*/>',
                     "", cfg, count=1)
        cfg = re.sub(rf'\s*<model_instance>\s*<metadata key="object_id" '
                     rf'value="{oid}"/>.*?</model_instance>', "",
                     cfg, count=1, flags=re.S)

    removed = set()
    for spec in args.remove_objects:
        plate_pat, sep, namelist = spec.partition(":")
        if not sep:
            fail(f"--remove-objects needs PLATE:NAMES, got {spec!r}")
        wanted = [n.strip() for n in namelist.split(",")]
        target = [p for p in plates if plate_pat.lower() in p[1].lower()]
        if len(target) != 1:
            fail(f"plate matching {plate_pat!r}: found {len(target)}, need 1")
        victims = [oid for oid in target[0][2]
                   if objects[oid][0] in wanted]
        if not victims:
            fail(f"no objects named {wanted} on plate {target[0][1]!r}")
        for oid in victims:
            purge_object(oid)
            removed.add(oid)
        print(f"removed {len(victims)} object(s) {wanted} from "
              f"plate {target[0][1]!r}")
    if removed:
        plates = [(pid, nm, [o for o in objs if o not in removed])
                  for pid, nm, objs in plates]

    if args.remove_plates:
        pat = args.remove_plates.lower()
        doomed = [(pid, nm, objs) for pid, nm, objs in plates
                  if pat in nm.lower()]
        if not doomed:
            fail(f"no plate name contains {args.remove_plates!r} "
                 f"(plates: {[nm for _, nm, _ in plates]})")
        keep = [(pid, nm, objs) for pid, nm, objs in plates
                if pat not in nm.lower()]
        cols_old = plate_columns(len(plates))
        cols_new = plate_columns(len(keep))
        print(f"removing plates: {[nm for _, nm, _ in doomed]}")

        # remove doomed plates' objects everywhere
        for _, _, objs in doomed:
            for oid in objs:
                purge_object(oid)

        # drop plate blocks, renumber survivors, move their objects to the
        # origin of their new grid slot
        for pid, nm, _ in doomed:
            m = [pm for pm in re.finditer(r'\s*<plate>.*?</plate>', cfg, re.S)
                 if f'plater_id" value="{pid}"' in pm.group(0)]
            cfg = cfg.replace(m[0].group(0), "", 1)
            for f in list((work / "Metadata").glob(f"*_{pid}.*")) + \
                     list((work / "Metadata").glob(f"plate_{pid}*")):
                f.unlink(missing_ok=True)
        fs_p = work / "Metadata/filament_sequence.json"
        if fs_p.exists():
            d = json.load(open(fs_p))
            for pid, _, _ in doomed:
                d.pop(f"plate_{pid}", None)
            d = {f"plate_{i}": v for i, (k, v) in enumerate(sorted(
                d.items(), key=lambda kv: int(kv[0].split("_")[1])), 1)}
            fs_p.write_text(json.dumps(d, separators=(",", ":")))

        for new_no, (pid, nm, objs) in enumerate(keep, 1):
            old_org = ((pid - 1) % cols_old * stride_x,
                       -((pid - 1) // cols_old) * stride_y)
            new_org = ((new_no - 1) % cols_new * stride_x,
                       -((new_no - 1) // cols_new) * stride_y)
            if pid != new_no:
                cfg = re.sub(rf'(plater_id" value=")({pid})(")',
                             rf'\g<1>{new_no}\g<3>', cfg, count=1)
                renames = set((work / "Metadata").glob(f"*_{pid}.*")) | \
                          set((work / "Metadata").glob(f"plate_{pid}_*"))
                for f in renames:
                    f.rename(f.with_name(f.name.replace(f"_{pid}", f"_{new_no}")))
                cfg = cfg.replace(f"Metadata/plate_{pid}.png",
                                  f"Metadata/plate_{new_no}.png")
                cfg = cfg.replace(f"Metadata/plate_no_light_{pid}.png",
                                  f"Metadata/plate_no_light_{new_no}.png")
                cfg = cfg.replace(f"Metadata/top_{pid}.png",
                                  f"Metadata/top_{new_no}.png")
                cfg = cfg.replace(f"Metadata/pick_{pid}.png",
                                  f"Metadata/pick_{new_no}.png")
            delta = (new_org[0] - old_org[0], new_org[1] - old_org[1])
            if delta != (0, 0):
                for oid in objs:
                    m = re.search(
                        rf'(<item objectid="{oid}"[^>]*transform=")([^"]+)(")',
                        xml)
                    t = m.group(2).split()
                    t[9] = f"{float(t[9]) + delta[0]:.9g}"
                    t[10] = f"{float(t[10]) + delta[1]:.9g}"
                    xml = xml[:m.start(2)] + " ".join(t) + xml[m.end(2):]

    # ---------------- renames ----------------
    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    for spec in args.plate_name:
        old, _, new = spec.partition("=")
        if not _:
            fail(f"--plate-name needs OLD=NEW, got {spec!r}")
        needle = f'plater_name" value="{esc(old)}"'
        if needle not in cfg:
            fail(f"no plate named {old!r}")
        cfg = cfg.replace(needle, f'plater_name" value="{esc(new)}"')
        print(f"plate renamed: {old!r} -> {new!r}")
    for spec in args.rename_object:
        old, _, new = spec.partition("=")
        if not _:
            fail(f"--rename-object needs OLD=NEW, got {spec!r}")
        pattern = (r'(<object id="\d+">\s*<metadata key="name" value=")'
                   + re.escape(esc(old)) + '(")')
        cfg, n = re.subn(pattern, rf'\g<1>{esc(new)}\g<2>', cfg)
        if n != 1:
            fail(f"object rename {old!r}: matched {n} objects, need exactly 1")
        print(f"object renamed: {old!r} -> {new!r}")

    # -------- wipe towers: keep each plate's tower clear of its objects ----
    final_plates = []
    for pm in re.finditer(r'<plate>(.*?)</plate>', cfg, re.S):
        pid = int(re.search(r'plater_id" value="(\d+)"', pm.group(1)).group(1))
        final_plates.append((pid, re.findall(r'object_id" value="(\d+)"',
                                             pm.group(1))))
    cols = plate_columns(len(final_plates))
    tower_w = float(ps.get("prime_tower_width", 35))
    margin = 0.0        # detection: only true body overlap counts
    place_margin = 5.0  # placement: moved towers get real clearance
    wx = [float(v) for v in ps.get("wipe_tower_x", [])]
    wy = [float(v) for v in ps.get("wipe_tower_y", [])]
    while len(wx) < len(final_plates):
        wx.append(165.0)
    while len(wy) < len(final_plates):
        wy.append(bed_d * 0.86)
    ex = [tuple(map(float, p.split("x")))
          for p in ps.get("bed_exclude_area", [])]
    ex_rect = ((min(p[0] for p in ex), min(p[1] for p in ex),
                max(p[0] for p in ex), max(p[1] for p in ex)) if ex else None)

    items_tf = {m.group(1): [float(v) for v in m.group(2).split()]
                for m in re.finditer(
                    r'<item objectid="(\d+)"[^>]*transform="([^"]+)"', xml)}
    CELL = 2.0
    gw, gh = int(bed_w / CELL) + 2, int(bed_d / CELL) + 2
    mesh_cache = {}

    def plate_grid(objs, origin):
        """cell-bucketed plate-local vertices for exact rectangle tests."""
        cells = {}
        for oid in objs:
            t = items_tf.get(oid)
            if not t:
                continue
            for path, cid in comps.get(oid, []):
                path = path.lstrip("/")
                if path not in mesh_cache:
                    mesh_cache[path] = parse_meshes((work / path).read_text())
                verts, _ = mesh_cache[path][int(cid)]
                for x, y, z in verts:
                    lx = x * t[0] + y * t[3] + z * t[6] + t[9] - origin[0]
                    ly = x * t[1] + y * t[4] + z * t[7] + t[10] - origin[1]
                    if -CELL <= lx <= bed_w + CELL and \
                            -CELL <= ly <= bed_d + CELL:
                        cells.setdefault(
                            (int(lx // CELL), int(ly // CELL)),
                            []).append((lx, ly))
        return cells

    def rect_free(cells, x0, y0, x1, y1):
        if ex_rect and not (x1 < ex_rect[0] or x0 > ex_rect[2]
                            or y1 < ex_rect[1] or y0 > ex_rect[3]):
            return False
        for gx in range(int(x0 // CELL) - 1, int(x1 // CELL) + 2):
            for gy in range(int(y0 // CELL) - 1, int(y1 // CELL) + 2):
                for px, py in cells.get((gx, gy), ()):
                    if x0 <= px <= x1 and y0 <= py <= y1:
                        return False
        return True

    def tower_ok(pre, x, y, m):
        # tower body must sit on the bed (Bambu's own default is flush to
        # the back edge); the clearance margin applies to objects only
        if x < 0 or y < 0 or x + tower_w > bed_w or y + tower_w > bed_d:
            return False
        return rect_free(pre, x - m, y - m,
                         x + tower_w + m, y + tower_w + m)

    moved = False
    for idx, (pid, objs) in enumerate(final_plates):
        if not objs:
            continue
        origin = ((pid - 1) % cols * stride_x,
                  -((pid - 1) // cols) * stride_y)
        pre = plate_grid(objs, origin)
        x, y = wx[idx], wy[idx]
        if tower_ok(pre, x, y, margin):
            continue
        best = None
        for m in (place_margin, margin):
            step = CELL
            gx = 0.0
            while gx + tower_w <= bed_w:
                gy = 0.0
                while gy + tower_w <= bed_d:
                    if tower_ok(pre, gx, gy, m):
                        d2 = (gx - x) ** 2 + (gy - y) ** 2
                        if best is None or d2 < best[0]:
                            best = (d2, gx, gy)
                    gy += step
                gx += step
            if best:
                break
        if best is None:
            print(f"plate {pid}: wipe tower collides but no free spot found "
                  f"- left at ({x:g},{y:g})")
            continue
        wx[idx], wy[idx] = round(best[1], 3), round(best[2], 3)
        moved = True
        print(f"plate {pid}: wipe tower ({x:g},{y:g}) collides -> "
              f"moved to ({wx[idx]:g},{wy[idx]:g})")
    if moved:
        ps["wipe_tower_x"] = [f"{v:g}" for v in wx]
        ps["wipe_tower_y"] = [f"{v:g}" for v in wy]
        (work / "Metadata/project_settings.config").write_text(
            json.dumps(ps, ensure_ascii=False, indent=4))

    root_p.write_text(xml)
    cfg_p.write_text(cfg)

    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(work.rglob("*")):
            if p.is_file():
                zf.write(p, str(p.relative_to(work)))
    shutil.rmtree(work)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
