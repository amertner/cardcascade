#!/usr/bin/env python3
"""Build a new Card Cascade project 3MF from CAD component exports.

Takes a published Bambu Studio project as the settings/structure template
and replaces every object's geometry with a new model's component
exports, keeping plate structure, filament/extruder assignments and
print settings. Unlike replace_parts.py (same-size revisions in place),
this recomputes every placement: parts may be any size, and surplus
duplicate instances (holders, pushers) can be dropped.

Usage:
    python3 make_cascade.py TEMPLATE.3mf -o OUT.3mf \
        --part "Box=CC6_Box.3mf" --part "Lid 560S=Lid_472S.3mf" ... \
        --count Holder=2 --count Pusher=2 \
        --rename "Lid 560S=Lid 472S" \
        --plate-sub "560 Card Sleeved (L6.40.12.62-Sl)=472 Card ..."

  --part NAME=FILE   replace the geometry of the object called NAME with
                     the bodies in FILE (multi-part objects are matched
                     body-to-part by name; single-part objects need a
                     single-body file). NAME#2=FILE targets only the 2nd
                     instance (in plate order), giving it its own mesh
                     file when the template shares one across instances —
                     use this for models with differently-sized holders.
  --count NAME=N     keep only the first N instances (in plate order) of
                     the objects called NAME.
  --rename OLD=NEW   rename an object (exact match).
  --plate-sub OLD=NEW  substring replacement applied to plate names.
  --gap MM           spacing between objects on a plate (default 12).

Objects stay on their template plates and are re-laid out axis-aligned
in centred rows (largest first), keeping clear of the wipe tower.
Thumbnails are removed (Bambu Studio regenerates them on save).
The script refuses on any ambiguity; it never guesses.
"""

import argparse
import datetime
import json
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

GAP_DEFAULT = 12.0
CLEARANCE = 1.0          # validation: min distance between objects


def fail(msg):
    sys.exit(f"REFUSING: {msg}")


def parse_meshes(text, scale=1.0):
    """{object id: (name, verts, tris)} for every mesh-bearing object."""
    meshes = {}
    for om in re.finditer(r'<object id="(\d+)"([^>]*)>(.*?)</object>',
                          text, re.S):
        oid, attrs, body = om.groups()
        name = re.search(r'name="([^"]*)"', attrs)
        verts = [(float(a) * scale, float(b) * scale, float(c) * scale)
                 for a, b, c in re.findall(
                     r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body)]
        tris = re.findall(
            r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body)
        if verts:
            meshes[int(oid)] = (name.group(1) if name else None, verts, tris)
    return meshes


def bbox(verts):
    xs, ys, zs = zip(*verts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def centre(verts):
    lo, hi = bbox(verts)
    return tuple((a + b) / 2 for a, b in zip(lo, hi))


def load_export(path):
    """[(body name, CAD-frame verts in mm, tris)] from a CAD export."""
    zf = zipfile.ZipFile(path)
    text = zf.read("3D/3dmodel.model").decode()
    unit = re.search(r'unit="(\w+)"', text).group(1)
    scale = {"meter": 1000.0, "millimeter": 1.0}.get(unit)
    if scale is None:
        fail(f"{path}: unsupported unit {unit!r}")
    for m in re.finditer(r'<item [^>]*transform="([^"]+)"', text):
        t = [float(v) for v in m.group(1).split()]
        if t[:9] != [1, 0, 0, 0, 1, 0, 0, 0, 1] or any(t[9:]):
            fail(f"{path}: build item carries a transform; export bodies "
                 "in place from CAD instead")
    meshes = parse_meshes(text, scale)
    if not meshes:
        fail(f"{path}: no meshes in root model")
    return [meshes[k] for k in sorted(meshes)]


def mesh_xml(verts, tris):
    return ("\n   <mesh>\n    <vertices>\n"
            + "".join(f'     <vertex x="{x:.9g}" y="{y:.9g}" z="{z:.9g}"/>\n'
                      for x, y, z in verts)
            + "    </vertices>\n    <triangles>\n"
            + "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                      for a, b, c in tris)
            + "    </triangles>\n   </mesh>\n  ")


def plate_columns(n):
    value = n ** 0.5
    return round(value) + 1 if value > round(value) else round(value)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("template")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--part", action="append", default=[],
                    metavar="NAME=FILE")
    ap.add_argument("--count", action="append", default=[],
                    metavar="NAME=N")
    ap.add_argument("--rename", action="append", default=[],
                    metavar="OLD=NEW")
    ap.add_argument("--plate-sub", action="append", default=[],
                    metavar="OLD=NEW")
    ap.add_argument("--gap", type=float, default=GAP_DEFAULT)
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="cascade_"))
    with zipfile.ZipFile(args.template) as zf:
        zf.extractall(work)
    root_p = work / "3D/3dmodel.model"
    cfg_p = work / "Metadata/model_settings.config"
    xml = root_p.read_text()
    cfg = cfg_p.read_text()

    ps = json.loads((work / "Metadata/project_settings.config").read_text())
    area = [tuple(map(float, p.split("x"))) for p in ps["printable_area"]]
    bed_w = max(p[0] for p in area)
    bed_d = max(p[1] for p in area)
    stride_x, stride_y = bed_w * 1.2, bed_d * 1.2
    tower_w = float(ps.get("prime_tower_width", 35))
    wx = [float(v) for v in ps.get("wipe_tower_x", [])]
    wy = [float(v) for v in ps.get("wipe_tower_y", [])]
    print(f"template: {args.template}")
    print(f"printer: {ps.get('printer_model')} bed {bed_w:g}x{bed_d:g}")

    # ---- template structure ----
    objects = {}        # object id -> name
    parts = {}          # object id -> [(part id, part name)]
    for om in re.finditer(r'<object id="(\d+)">(.*?)</object>', cfg, re.S):
        oid = om.group(1)
        objects[oid] = re.search(r'key="name" value="([^"]*)"',
                                 om.group(2)).group(1)
        parts[oid] = [
            (pm.group(1),
             re.search(r'key="name" value="([^"]*)"', pm.group(2)).group(1))
            for pm in re.finditer(r'<part id="(\d+)"[^>]*>(.*?)</part>',
                                  om.group(2), re.S)]
    comps = {}          # object id -> [(path, component id)]
    for om in re.finditer(
            r'<object id="(\d+)"[^>]*>\s*<components>(.*?)</components>',
            xml, re.S):
        comps[om.group(1)] = re.findall(
            r'p:path="([^"]+)" objectid="(\d+)"', om.group(2))
    plates = []         # (plater_id, name, [object ids])
    for pm in re.finditer(r'<plate>(.*?)</plate>', cfg, re.S):
        pid = int(re.search(r'plater_id" value="(\d+)"', pm.group(1)).group(1))
        pname = re.search(r'plater_name" value="([^"]*)"', pm.group(1))
        objs = re.findall(r'object_id" value="(\d+)"', pm.group(1))
        plates.append((pid, pname.group(1) if pname else "", objs))

    # ---------------- instance counts ----------------
    def purge_object(oid):
        nonlocal xml, cfg
        for f in dict.fromkeys(f for f, _cid in comps.get(oid, [])):
            if not any(ff == f for other, c in comps.items() if other != oid
                       for ff, _ in c):
                (work / f.lstrip("/")).unlink()
                rp = work / "3D/_rels/3dmodel.model.rels"
                rp.write_text(re.sub(
                    rf'\s*<Relationship Target="{re.escape(f)}"[^>]*/>',
                    "", rp.read_text()))
        comps.pop(oid, None)
        objects.pop(oid, None)
        parts.pop(oid, None)
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

    for spec in args.count:
        name, _, n = spec.partition("=")
        if not _ or not n.isdigit():
            fail(f"--count needs NAME=N, got {spec!r}")
        n = int(n)
        in_order = [oid for _, _, objs in sorted(plates) for oid in objs
                    if objects.get(oid) == name]
        if len(in_order) < n:
            fail(f"{name}: template has {len(in_order)} instances, "
                 f"need {n}")
        for oid in in_order[n:]:
            purge_object(oid)
        print(f"{name}: keeping {n} of {len(in_order)} instances")
    plates = [(pid, nm, [o for o in objs if o in objects])
              for pid, nm, objs in plates]

    # ---------------- geometry replacement ----------------
    for spec in args.part:
        name, _, file = spec.partition("=")
        if not _:
            fail(f"--part needs NAME=FILE, got {spec!r}")
        inst = None
        im = re.match(r'^(.*)#(\d+)$', name)
        if im:
            name, inst = im.group(1), int(im.group(2))
        in_order = [oid for _, _, objs in sorted(plates) for oid in objs
                    if objects.get(oid) == name]
        if not in_order:
            fail(f"no object named {name!r} "
                 f"(names: {sorted(set(objects.values()))})")
        if inst is not None:
            if not 1 <= inst <= len(in_order):
                fail(f"{name}#{inst}: only {len(in_order)} instance(s)")
            targets = [in_order[inst - 1]]
        else:
            targets = in_order

        # targeted instances get their own copy of a mesh file the
        # template shares with instances not replaced by this spec
        for t in targets:
            for pos, (f, cid) in enumerate(list(comps[t])):
                if not any(ff == f for other, cl in comps.items()
                           if other not in targets for ff, _ in cl):
                    continue
                nums = [int(nm.group(1))
                        for p in (work / "3D/Objects").glob("object_*.model")
                        for nm in [re.match(r'object_(\d+)\.model$', p.name)]
                        if nm]
                newf = f"/3D/Objects/object_{max(nums) + 1}.model"
                text = (work / f.lstrip("/")).read_text()
                text = re.sub(r'(p:UUID=")[^"]+(")',
                              lambda m: m.group(1) + str(uuid.uuid4())
                              + m.group(2), text)
                (work / newf.lstrip("/")).write_text(text)
                bm = re.search(rf'<object id="{t}"[^>]*>.*?</object>',
                               xml, re.S)
                nblk, n = re.subn(
                    rf'(p:path="){re.escape(f)}("[^>]*objectid="{cid}")',
                    rf'\g<1>{newf}\g<2>', bm.group(0), count=1)
                if n != 1:
                    fail(f"{name}: could not repoint component {cid} "
                         f"of object {t}")
                xml = xml[:bm.start()] + nblk + xml[bm.end():]
                comps[t][pos] = (newf, cid)
                print(f"  {name}: instance {t} split off into {newf}")
        for t in targets[1:]:
            if comps[t] != comps[targets[0]]:
                fail(f"{name}: instances use different mesh files; "
                     f"target them individually with {name}#N=FILE")

        bodies = load_export(file)
        src_name = re.sub(r'^[0-9a-f]{8}-', '', Path(file).name)

        # every instance shares the same mesh file(s); patch via the first
        oid = targets[0]
        plist = parts[oid]
        if len(bodies) != len(plist):
            fail(f"{name}: template object has {len(plist)} parts, "
                 f"{file} has {len(bodies)} bodies")
        if len(plist) == 1:
            mapping = {plist[0][0]: bodies[0]}
        else:
            by_name = {}
            for b in bodies:
                if b[0] in by_name:
                    fail(f"{file}: duplicate body name {b[0]!r}")
                by_name[b[0]] = b
            mapping = {}
            for pid_, pname in plist:
                if pname not in by_name:
                    fail(f"{name} part {pname!r}: no body of that name in "
                         f"{file} (bodies: {sorted(by_name)})")
                mapping[pid_] = by_name[pname]

        # object frame = centre of the whole assembly's CAD bbox
        all_verts = [v for _, verts, _ in mapping.values() for v in verts]
        origin = centre(all_verts)

        # centred meshes into the shared sub-model files
        centres, faces = {}, {}
        files = dict.fromkeys(f for f, _ in comps[oid])
        cid_of = {pid_: cid for (_, cid), (pid_, _) in
                  zip(comps[oid], plist)}
        for pid_, cid in ((p, c) for p, c in cid_of.items()):
            if pid_ != cid:
                fail(f"{name}: part id {pid_} != component id {cid}; "
                     "unexpected template structure")
        for f in files:
            fp = work / f.lstrip("/")
            s = fp.read_text()
            def repl(m):
                pid_ = m.group(2)
                if pid_ not in mapping:
                    return m.group(0)
                _, verts, tris = mapping[pid_]
                c = centre(verts)
                centres[pid_] = c
                faces[pid_] = len(tris)
                shifted = [(x - c[0], y - c[1], z - c[2])
                           for x, y, z in verts]
                return m.group(1) + mesh_xml(shifted, tris) + m.group(3)
            s = re.sub(r'(<object id="(\d+)"[^>]*>).*?(</object>)',
                       repl, s, flags=re.S)
            fp.write_text(s)
        if set(centres) != set(mapping):
            fail(f"{name}: parts {sorted(set(mapping) - set(centres))} "
                 "not found in the template's mesh files")

        # per-instance updates: component transforms, settings block
        for t in targets:
            for pid_, _ in parts[t]:
                c = centres[pid_]
                tr = tuple(a - b for a, b in zip(c, origin))
                if len(parts[t]) == 1:
                    tr = (0.0, 0.0, 0.0)   # single part: frame = its centre
                xml = re.sub(
                    rf'(<object id="{t}"[^>]*>\s*<components>.*?'
                    rf'objectid="{pid_}"[^>]*transform=")[^"]+(")',
                    lambda m: m.group(1)
                    + f"1 0 0 0 1 0 0 0 1 {tr[0]:.9g} {tr[1]:.9g} {tr[2]:.9g}"
                    + m.group(2), xml, count=1, flags=re.S)

            blk = re.search(rf'<object id="{t}">.*?</object>',
                            cfg, re.S).group(0)
            nblk = blk
            for pid_, _ in parts[t]:
                c = centres[pid_]
                tr = ((0.0, 0.0, 0.0) if len(parts[t]) == 1
                      else tuple(a - b for a, b in zip(c, origin)))
                pblk = re.search(rf'<part id="{pid_}".*?</part>',
                                 nblk, re.S).group(0)
                npblk = pblk
                npblk = re.sub(
                    r'(key="matrix" value=")[^"]+(")',
                    rf'\g<1>1 0 0 {tr[0]:.9g} 0 1 0 {tr[1]:.9g} '
                    rf'0 0 1 {tr[2]:.9g} 0 0 0 1\g<2>', npblk)
                npblk = re.sub(r'(key="source_file" value=")[^"]*(")',
                               rf'\g<1>{src_name}\g<2>', npblk)
                for axis, v in zip("xyz", c):
                    npblk = re.sub(
                        rf'(key="source_offset_{axis}" value=")[^"]*(")',
                        rf'\g<1>{v:.9g}\g<2>', npblk)
                npblk = re.sub(r'(<mesh_stat face_count=")\d+',
                               rf'\g<1>{faces[pid_]}', npblk)
                nblk = nblk.replace(pblk, npblk)
            nblk = re.sub(r'<metadata face_count="\d+"/>',
                          f'<metadata face_count="{sum(faces.values())}"/>',
                          nblk, count=1)
            cfg = cfg.replace(blk, nblk)
        dims = tuple(b - a for a, b in zip(*bbox(all_verts)))
        print(f"  {name}: {len(bodies)} bodies, "
              f"{sum(faces.values())} tris, "
              f"{dims[0]:.1f} x {dims[1]:.1f} x {dims[2]:.1f} mm "
              f"x{len(targets)}")

    # ---------------- renames ----------------
    def esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    for spec in args.rename:
        old, _, new = spec.partition("=")
        if not _:
            fail(f"--rename needs OLD=NEW, got {spec!r}")
        pattern = (r'(<object id="\d+">\s*<metadata key="name" value=")'
                   + re.escape(esc(old)) + '(")')
        cfg, n = re.subn(pattern, rf'\g<1>{esc(new)}\g<2>', cfg)
        if n != 1:
            fail(f"object rename {old!r}: matched {n} objects, need 1")
        print(f"object renamed: {old!r} -> {new!r}")
    for spec in args.plate_sub:
        old, _, new = spec.partition("=")
        if not _:
            fail(f"--plate-sub needs OLD=NEW, got {spec!r}")
        hits = [nm for _, nm, _ in plates if old in nm]
        if not hits:
            fail(f"no plate name contains {old!r}")
        cfg = re.sub(r'(plater_name" value=")([^"]*)(")',
                     lambda m: m.group(1) + m.group(2).replace(
                         esc(old), esc(new)) + m.group(3), cfg)
        print(f"plate names: {old!r} -> {new!r} ({len(hits)} plates)")

    # ---------------- layout ----------------
    # object-frame bounding boxes from the final meshes
    mesh_cache = {}
    def obj_bbox(oid):
        lo = [1e9] * 3
        hi = [-1e9] * 3
        for f, cid in comps[oid]:
            fp = f.lstrip("/")
            if fp not in mesh_cache:
                mesh_cache[fp] = parse_meshes((work / fp).read_text())
            _, verts, _ = mesh_cache[fp][int(cid)]
            m = re.search(
                rf'<object id="{oid}"[^>]*>\s*<components>.*?'
                rf'objectid="{cid}"[^>]*transform="([^"]+)"',
                xml, re.S)
            t = [float(v) for v in m.group(1).split()]
            (l0, l1, l2), (h0, h1, h2) = bbox(verts)
            for i, (l, h) in enumerate(((l0, h0), (l1, h1), (l2, h2))):
                lo[i] = min(lo[i], l + t[9 + i])
                hi[i] = max(hi[i], h + t[9 + i])
        return tuple(lo), tuple(hi)

    cols = plate_columns(len(plates))
    placements = {}     # object id -> (x, y, z) build translation
    for idx, (pid, pname, objs) in enumerate(sorted(plates)):
        if not objs:
            continue
        org = ((pid - 1) % cols * stride_x,
               -((pid - 1) // cols) * stride_y)
        boxes = {oid: obj_bbox(oid) for oid in objs}
        order = sorted(objs, key=lambda o: -(
            (boxes[o][1][0] - boxes[o][0][0])
            * (boxes[o][1][1] - boxes[o][0][1])))
        # shelf rows, widest-first
        rows, cur, cur_w = [], [], 0.0
        for oid in order:
            w = boxes[oid][1][0] - boxes[oid][0][0]
            if cur and cur_w + args.gap + w > bed_w - 20:
                rows.append(cur)
                cur, cur_w = [], 0.0
            cur.append(oid)
            cur_w += (args.gap if cur_w else 0.0) + w
        if cur:
            rows.append(cur)
        depths = [max(boxes[o][1][1] - boxes[o][0][1] for o in r)
                  for r in rows]
        total_d = sum(depths) + args.gap * (len(rows) - 1)
        y0 = (bed_d - total_d) / 2
        placed = []
        for row, depth in zip(rows, depths):
            widths = [boxes[o][1][0] - boxes[o][0][0] for o in row]
            total_w = sum(widths) + args.gap * (len(row) - 1)
            x0 = (bed_w - total_w) / 2
            for oid, w in zip(row, widths):
                lo, hi = boxes[oid]
                cx = x0 + w / 2
                cy = y0 + depth / 2
                placements[oid] = (
                    org[0] + cx - (lo[0] + hi[0]) / 2,
                    org[1] + cy - (lo[1] + hi[1]) / 2,
                    -lo[2])
                placed.append((oid, cx - w / 2, cy - (hi[1] - lo[1]) / 2,
                               cx + w / 2, cy + (hi[1] - lo[1]) / 2))
                x0 += w + args.gap
            y0 += depth + args.gap
        # validation: bed bounds, mutual clearance, wipe tower
        tower = None
        if idx < len(wx):
            tower = (wx[idx], wy[idx], wx[idx] + tower_w, wy[idx] + tower_w)
        for i, (oid, x0_, y0_, x1_, y1_) in enumerate(placed):
            if x0_ < 0 or y0_ < 0 or x1_ > bed_w or y1_ > bed_d:
                fail(f"plate {pid}: {objects[oid]} does not fit the bed "
                     f"({x0_:.1f},{y0_:.1f})-({x1_:.1f},{y1_:.1f})")
            for oid2, a0, b0, a1, b1 in placed[:i]:
                if not (x1_ + CLEARANCE < a0 or a1 + CLEARANCE < x0_
                        or y1_ + CLEARANCE < b0 or b1 + CLEARANCE < y0_):
                    fail(f"plate {pid}: {objects[oid]} overlaps "
                         f"{objects[oid2]}")
            if tower and not (x1_ + CLEARANCE < tower[0]
                              or tower[2] + CLEARANCE < x0_
                              or y1_ + CLEARANCE < tower[1]
                              or tower[3] + CLEARANCE < y0_):
                fail(f"plate {pid}: {objects[oid]} collides with the wipe "
                     f"tower at ({tower[0]:g},{tower[1]:g})")
        print(f"plate {pid}: {len(objs)} object(s) in {len(rows)} row(s)")

    for oid, (tx, ty, tz) in placements.items():
        xml, n = re.subn(
            rf'(<item objectid="{oid}" [^>]*transform=")[^"]+(")',
            lambda m: m.group(1)
            + f"1 0 0 0 1 0 0 0 1 {tx:.9g} {ty:.9g} {tz:.9g}"
            + m.group(2), xml, count=1)
        if n != 1:
            fail(f"object {oid}: no build item found")

    # assemble view: keep template x/y, rest the object on z=0
    for m in list(re.finditer(
            r'<assemble_item object_id="(\d+)"[^>]*transform="([^"]+)"',
            cfg)):
        oid = m.group(1)
        if oid not in objects:
            continue
        t = [float(v) for v in m.group(2).split()]
        lo, hi = obj_bbox(oid)
        new = (f"1 0 0 0 1 0 0 0 1 {t[9]:.9g} {t[10]:.9g} {-lo[2]:.9g}")
        cfg = cfg.replace(m.group(0),
                          m.group(0).replace(m.group(2), new), 1)

    # ---------------- thumbnails & bookkeeping ----------------
    for f in {*(work / "Metadata").glob("plate_*.png"),
              *(work / "Metadata").glob("top_*.png"),
              *(work / "Metadata").glob("pick_*.png")}:
        f.unlink()
    cfg = re.sub(r'\s*<metadata key="(?:thumbnail_file|'
                 r'thumbnail_no_light_file|top_file|pick_file)"'
                 r' value="[^"]*"/>', "", cfg)
    xml = re.sub(r'\s*<metadata name="Thumbnail_(?:Middle|Small)">'
                 r'[^<]*</metadata>', "", xml)
    xml = re.sub(r'(<metadata name="ModificationDate">)[^<]*(</metadata>)',
                 rf'\g<1>{datetime.date.today().isoformat()}\g<2>', xml)

    # sub-model housekeeping: drop unreferenced mesh files (including the
    # empty husks Bambu leaves behind) and rebuild the rels from scratch
    refs = []
    for cl in comps.values():
        for f, _ in cl:
            if f not in refs:
                refs.append(f)
    for p in (work / "3D/Objects").glob("*.model"):
        if f"/3D/Objects/{p.name}" not in refs:
            p.unlink()
    (work / "3D/_rels/3dmodel.model.rels").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/'
        'package/2006/relationships">\n'
        + "".join(f' <Relationship Target="{f}" Id="rel-{i}" Type='
                  '"http://schemas.microsoft.com/3dmanufacturing/2013/01/'
                  '3dmodel"/>\n' for i, f in enumerate(refs, 1))
        + '</Relationships>')

    cut_p = work / "Metadata/cut_information.xml"
    if cut_p.exists():
        cut_p.write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<objects>\n'
            + "".join(f' <object id="{i}">\n  <cut_id id="0" check_sum="1"'
                      f' connectors_cnt="0"/>\n </object>\n'
                      for i in range(1, len(objects) + 1))
            + "</objects>\n")

    root_p.write_text(xml)
    cfg_p.write_text(cfg)

    # ---------------- sanity: well-formed XML ----------------
    import xml.etree.ElementTree as ET
    for p in [root_p, cfg_p, cut_p] + list(work.glob("3D/Objects/*.model")):
        if p.exists():
            try:
                ET.parse(p)
            except ET.ParseError as e:
                fail(f"{p.name}: produced malformed XML ({e})")

    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(work.rglob("*")):
            if p.is_file():
                zf.write(p, str(p.relative_to(work)))
    shutil.rmtree(work)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
