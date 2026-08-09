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
import math
import re
import shutil
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

GAP_DEFAULT = 12.0
CLEARANCE = 1.0          # validation: min distance between objects

# Candidate print beds for --auto-plates bed selection, smallest first. Each
# carries a reference printer profile (a full project_settings.config under
# profiles/) that the output is switched to when that bed is chosen.
PROFILES = Path(__file__).parent / "profiles"
BED_TABLE = [
    ("P1",  256.0, 256.0, "p1p", "Bambu Lab P1P"),
    ("H2C", 330.0, 320.0, "h2c", "Bambu Lab H2C"),
]
BED_MARGIN = 8.0         # bed-fit slack: an object's 45°-rotated span must clear this


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


# ---- auto plate scheme (Stage 3): group objects into the standard plates ----
# One plate per role group, in this order. Pushers ride with the Box.
PLATE_SCHEME = [
    ("Box + pushers", ("Box", "Pusher")),
    ("Lid", ("Lid",)),
    ("Holders", ("Holder",)),
    ("Toppers", ("Topper",)),
    ("Token holders", ("TokenHolder",)),
    ("Half token holders", ("HalfTokenHolder",)),
    ("Labels", ("Label",)),
]


def _role(name):
    for r in ("HalfTokenHolder", "TokenHolder", "Box", "Lid", "Holder",
              "Topper", "Pusher", "Label"):
        if name.startswith(r):
            return r
    return "Other"


def _xesc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _plate_safe(name):
    r"""Bambu forbids <>:/\|?*" in plate names; replace each with '-'."""
    for c in '<>:/\\|?*"':
        name = name.replace(c, "-")
    return name


def auto_plate_groups(objects, plates, title):
    """The standard plate scheme: [(plate name, [object ids]), ...] in
    PLATE_SCHEME order; empty groups skipped. Auto-plates regenerates the layout
    from scratch, so EVERY object is placed — including any the template left off
    a plate (orphans, e.g. a token holder imported loose)."""
    on_plates = [o for _, _, objs in sorted(plates) for o in objs]
    order = on_plates + [o for o in objects if o not in on_plates]
    groups = []
    for label, roles in PLATE_SCHEME:
        oids = [o for o in order if _role(objects[o]) in roles]
        if oids:
            groups.append((f"{label} — {title}", oids))
    return groups


def regroup_cfg(cfg, ps, groups):
    """Rewrite the model_settings <plate> blocks and the project_settings wipe
    towers to `groups`, moving each object's <model_instance> to its new plate."""
    inst = {re.search(r'object_id" value="(\d+)"', b).group(1): b
            for b in re.findall(r'<model_instance>.*?</model_instance>',
                                cfg, re.S)}
    hdr = re.search(r'<plate>.*?plater_name"[^>]*/>(.*?)<model_instance>',
                    cfg, re.S).group(1)          # locked + filament metadata
    hdr = re.sub(r'\s*<metadata key="(?:thumbnail_file|thumbnail_no_light_file|'
                 r'top_file|pick_file)"[^>]*/>', '', hdr)
    blocks = []
    for i, (name, oids) in enumerate(groups, 1):
        insts = "".join(inst[o] for o in oids if o in inst)
        blocks.append(f'<plate>\n<metadata key="plater_id" value="{i}"/>\n'
                      f'<metadata key="plater_name" '
                      f'value="{_xesc(_plate_safe(name))}"/>'
                      f'{hdr}{insts}</plate>')
    cfg = re.sub(r'<plate>.*</plate>', "\n".join(blocks), cfg, flags=re.S)
    ps["wipe_tower_x"] = ["15"] * len(groups)    # layout relocates per plate
    ps["wipe_tower_y"] = ["200"] * len(groups)
    return cfg


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
    ap.add_argument("--gap-override", action="append", default=[],
                    metavar="NAME=MM",
                    help="gap between adjacent objects whose name starts with "
                         "NAME (e.g. Topper=2); --gap is used otherwise")
    ap.add_argument("--auto-plates", action="store_true",
                    help="ignore the template's plate layout; generate the "
                         "standard scheme (Box+Pushers / Lid / Holders / "
                         "Toppers / TokenHolders) and lay each out on the bed")
    ap.add_argument("--keep-layout", action="store_true",
                    help="in-place swap: replace meshes but KEEP the template's "
                         "object positions, plates and wipe towers (for updating "
                         "a hand-crafted layout with same-design components); "
                         "refuses a swapped mesh that outgrew its slot")
    ap.add_argument("--bed", choices=["auto", "p1", "h2c", "template"],
                    help="with --auto-plates, the print bed: 'auto' (default) "
                         "picks the smallest that fits parts rotated 45° (P1 "
                         "256mm, else H2C 330mm) and swaps the printer profile "
                         "to match; 'p1'/'h2c' force one; 'template' keeps the "
                         "template's bed")
    args = ap.parse_args()
    if args.keep_layout and args.auto_plates:
        fail("--keep-layout and --auto-plates are mutually exclusive")
    # Auto-plates regenerates the layout, so default to auto bed selection;
    # keep-layout must never move the bed under a hand-tuned layout.
    bed_mode = args.bed or ("auto" if args.auto_plates else "template")

    gap_over = {}
    for spec in args.gap_override:
        name, _, mm = spec.partition("=")
        if not _:
            fail(f"--gap-override needs NAME=MM, got {spec!r}")
        gap_over[name] = float(mm)

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
    part_ext = {}       # object id -> {part id: extruder (object default applied)}
    obj_default = {}    # object id -> object's default extruder (added parts use it)
    for om in re.finditer(r'<object id="(\d+)">(.*?)</object>', cfg, re.S):
        oid = om.group(1)
        objects[oid] = re.search(r'key="name" value="([^"]*)"',
                                 om.group(2)).group(1)
        head = om.group(2).split("<part", 1)[0]
        objdef = re.search(r'key="extruder" value="([^"]*)"', head)
        objdef = objdef.group(1) if objdef else "1"
        obj_default[oid] = objdef
        parts[oid] = []
        part_ext[oid] = {}
        for pm in re.finditer(r'<part id="(\d+)"[^>]*>(.*?)</part>',
                              om.group(2), re.S):
            pid_ = pm.group(1)
            pname = re.search(r'key="name" value="([^"]*)"',
                              pm.group(2)).group(1)
            pex = re.search(r'key="extruder" value="([^"]*)"', pm.group(2))
            parts[oid].append((pid_, pname))
            part_ext[oid][pid_] = pex.group(1) if pex else objdef
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
    # Fresh ids for parts a component gained vs the template must be unique
    # across the main model, the config, and every sub-model mesh file.
    def _max_id():
        ids = [int(x) for x in re.findall(r'\bid="(\d+)"', xml + cfg)]
        ids += [int(x) for x in re.findall(r'objectid="(\d+)"', xml)]
        for p in (work / "3D/Objects").glob("object_*.model"):
            ids += [int(x) for x in re.findall(r'<object id="(\d+)"',
                                               p.read_text())]
        return max(ids)
    next_id = _max_id() + 1

    def _esc(s):
        return (s.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    def add_body_part(oid, targets, body_name):
        """Append a brand-new part for a body the component GAINED relative to
        the template (e.g. a v6.4 topper's logo, which renumbered the letters
        so one body has no template slot). The part is cloned from an existing
        sibling on the object's default extruder — so it inherits the accent
        colour — and its mesh/position are filled by the shared replacement
        pass below. Keeps the template's part-id == component-id invariant.
        Returns the new (shared) id."""
        nonlocal xml, cfg, next_id
        newid = str(next_id)
        next_id += 1
        for t in targets:
            donor = next((pid for pid, _ in parts[t]
                          if part_ext[t].get(pid) == obj_default[t]), None)
            if donor is None:
                fail(f"{objects[t]}: no default-extruder part to model the new "
                     f"part {body_name!r} on")
            donor_path = {c: f for f, c in comps[t]}[donor]
            # 1) sub-model mesh file: an empty object the replacement pass fills
            smp = work / donor_path.lstrip("/")
            ph = (f'  <object id="{newid}" p:UUID="{uuid.uuid4()}" '
                  f'type="model">\n   <mesh>\n    <vertices>\n    </vertices>\n'
                  f'    <triangles>\n    </triangles>\n   </mesh>\n  </object>\n')
            smp.write_text(smp.read_text().replace(
                "</resources>", ph + " </resources>", 1))
            # 2) main model: a new component at the end of this object's list
            comp = (f'<component p:path="{donor_path}" objectid="{newid}" '
                    f'p:UUID="{uuid.uuid4()}" '
                    f'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
            om = re.search(rf'(<object id="{t}"[^>]*>\s*<components>.*?)'
                           rf'(\s*</components>)', xml, re.S)
            xml = (xml[:om.start()] + om.group(1) + "\n    " + comp
                   + om.group(2) + xml[om.end():])
            # 3) config: clone the donor <part>, renaming id + name
            cm = re.search(rf'<object id="{t}">.*?</object>', cfg, re.S)
            blk = cm.group(0)
            donor_blk = re.search(rf'<part id="{donor}".*?</part>',
                                  blk, re.S).group(0)
            npart = re.sub(r'<part id="\d+"', f'<part id="{newid}"',
                           donor_blk, count=1)
            npart = re.sub(r'(key="name" value=")[^"]*(")',
                           rf'\g<1>{_esc(body_name)}\g<2>', npart, count=1)
            nblk = blk.replace("</object>", "    " + npart + "\n  </object>", 1)
            cfg = cfg[:cm.start()] + nblk + cfg[cm.end():]
            # 4) register so the mapping / replacement passes see the new part
            comps[t].append((donor_path, newid))
            parts[t].append((newid, body_name))
            part_ext[t][newid] = obj_default[t]
        return newid

    # --keep-layout guard: an object's world-space XY bounding box AT ITS KEPT
    # template position (item ∘ component ∘ mesh, using real transformed verts so
    # rotation is handled exactly). Used to refuse a swapped mesh that outgrew
    # its slot enough to overhang the bed.
    def _world_xy_aabb(oid):
        it = re.search(rf'<item objectid="{oid}" [^>]*transform="([^"]+)"', xml)
        if not it:
            return None
        v = [float(x) for x in it.group(1).split()]
        xs, ys = [], []
        for f, cid in comps.get(oid, []):
            got = parse_meshes((work / f.lstrip("/")).read_text()).get(int(cid))
            if not got:
                continue
            _, verts, _ = got
            cm = re.search(rf'<object id="{oid}"[^>]*>\s*<components>.*?'
                           rf'objectid="{cid}"[^>]*transform="([^"]+)"', xml, re.S)
            c = [float(x) for x in cm.group(1).split()]
            for x, y, z in verts:
                px = x*c[0] + y*c[3] + z*c[6] + c[9]
                py = x*c[1] + y*c[4] + z*c[7] + c[10]
                pz = x*c[2] + y*c[5] + z*c[8] + c[11]
                xs.append(px*v[0] + py*v[3] + pz*v[6] + v[9])
                ys.append(px*v[1] + py*v[4] + pz*v[7] + v[10])
        return (min(xs), min(ys), max(xs), max(ys)) if xs else None

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
        if len(plist) == 1:
            if len(bodies) != 1:
                fail(f"{name}: {file} has {len(bodies)} bodies but the "
                     f"single-part template object has one slot")
            mapping = {plist[0][0]: bodies[0]}
        else:
            by_name = {}
            for b in bodies:
                if b[0] in by_name:
                    fail(f"{file}: duplicate body name {b[0]!r}")
                by_name[b[0]] = b
            mapping = {}
            unmatched_parts = []            # template parts with no same-named body
            used = set()
            for pid_, pname in plist:
                if pname in by_name:
                    mapping[pid_] = by_name[pname]
                    used.add(pname)
                else:
                    unmatched_parts.append((pid_, pname))
            leftover = sorted((b for n, b in by_name.items()
                               if n not in used), key=lambda x: x[0])
            # A revision may rename some bodies (e.g. a v6.4 topper inserts a
            # logo body and renumbers the letters). Pair leftover bodies onto
            # leftover template slots first, but only when those slots share one
            # extruder - then which slot a body lands in cannot change its
            # colour, so there is nothing to guess. Positions are recomputed
            # from each body's own geometry below, so slot identity is cosmetic.
            if unmatched_parts:
                exs = {part_ext[oid][pid_] for pid_, _ in unmatched_parts}
                if len(exs) > 1:
                    fail(f"{name}: {len(unmatched_parts)} template part(s) have "
                         f"no same-named body in {file} and use mixed extruders "
                         f"{sorted(exs)} - cannot reconcile unambiguously "
                         f"(template-only: {sorted(p for _, p in unmatched_parts)}, "
                         f"body-only: {sorted(b[0] for b in leftover)})")
                for (pid_, pname), b in zip(sorted(unmatched_parts), leftover):
                    mapping[pid_] = b
                    print(f"  {name}: reconciled body {b[0]!r} -> part {pname!r} "
                          f"(extruder {part_ext[oid][pid_]})")
            # Bodies still unplaced were GAINED vs the template — add a part for
            # each at the object's default extruder (accent). The base body
            # always name-matches, so a surplus body is never the base colour.
            for b in leftover[len(unmatched_parts):]:
                newid = add_body_part(oid, targets, b[0])
                mapping[newid] = b
                print(f"  {name}: added part {b[0]!r} "
                      f"(extruder {obj_default[oid]}) — gained vs template")
            plist = parts[oid]

        # Component simplified: fewer bodies than the template object has parts.
        # Drop the excess parts (allowed only if they share one extruder, so
        # removing them can't change any colour). Kept parts are unaffected.
        extra = [p for p, _ in plist if p not in mapping]
        if extra:
            exs = {part_ext[oid][p] for p in extra}
            if len(exs) > 1:
                fail(f"{name}: {len(extra)} excess template part(s) use mixed "
                     f"extruders {sorted(exs)} - cannot drop unambiguously")
            drop = set(extra)                    # part id == component id here
            for t in targets:
                for f, cid in comps[t]:
                    if cid in drop:
                        fp = work / f.lstrip("/")
                        fp.write_text(re.sub(
                            rf'\s*<object id="{cid}"[^>]*>.*?</object>', "",
                            fp.read_text(), count=1, flags=re.S))
                bm = re.search(rf'<object id="{t}".*?</object>', xml, re.S)
                nb = bm.group(0)
                for cid in drop:
                    nb = re.sub(rf'\s*<component [^>]*objectid="{cid}"[^>]*/>',
                                "", nb, count=1)
                xml = xml[:bm.start()] + nb + xml[bm.end():]
                cb = re.search(rf'<object id="{t}">.*?</object>', cfg, re.S)
                ncb = cb.group(0)
                for cid in drop:
                    ncb = re.sub(rf'\s*<part id="{cid}".*?</part>', "",
                                 ncb, count=1, flags=re.S)
                cfg = cfg.replace(cb.group(0), ncb)
                comps[t] = [(f, c) for f, c in comps[t] if c not in drop]
            for p in extra:
                part_ext[oid].pop(p, None)
            parts[oid] = [(p, n) for p, n in parts[oid] if p not in drop]
            plist = parts[oid]
            print(f"  {name}: dropped {len(extra)} excess part(s) "
                  f"(extruder {next(iter(exs))})")

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
        pattern = (r'(<object id="(\d+)">\s*<metadata key="name" value=")'
                   + re.escape(esc(old)) + '(")')
        matches = list(re.finditer(pattern, cfg))
        if len(matches) != 1:
            fail(f"object rename {old!r}: matched {len(matches)} objects, need 1")
        cfg = re.sub(pattern, rf'\g<1>{esc(new)}\g<3>', cfg)
        objects[matches[0].group(2)] = new   # keep in-memory name in sync so
        print(f"object renamed: {old!r} -> {new!r}")   # role/layout see it
    for spec in args.plate_sub:
        old, _, new = spec.partition("=")
        if not _:
            fail(f"--plate-sub needs OLD=NEW, got {spec!r}")
        hits = [nm for nm in re.findall(r'plater_name" value="([^"]*)"',
                                        cfg) if esc(old) in nm]
        if not hits:
            fail(f"no plate name contains {old!r}")
        cfg = re.sub(r'(plater_name" value=")([^"]*)(")',
                     lambda m: m.group(1) + m.group(2).replace(
                         esc(old), esc(new)) + m.group(3), cfg)
        print(f"plate names: {old!r} -> {new!r} ({len(hits)} plates)")

    # ---------------- layout ----------------
    if args.keep_layout:
        # In-place update: keep the template's item transforms, plate groups and
        # wipe towers untouched (only the meshes were swapped). Guard per plate
        # that its objects' combined footprint still fits a bed — a swapped mesh
        # that outgrew its slot pushes the plate's span past the bed. This is
        # measured as an extent (max-min), so it is independent of where the
        # plate sits in Bambu's multi-plate grid. Then skip the re-layout.
        for pm in re.finditer(r'<plate>(.*?)</plate>', cfg, re.S):
            oids = re.findall(r'object_id" value="(\d+)"', pm.group(1))
            xs, ys = [], []
            for oid in oids:
                bb = _world_xy_aabb(oid)
                if bb:
                    xs += [bb[0], bb[2]]; ys += [bb[1], bb[3]]
            if not xs:
                continue
            dx, dy = max(xs) - min(xs), max(ys) - min(ys)
            if dx > bed_w + 0.5 or dy > bed_d + 0.5:
                nm = re.search(r'plater_name" value="([^"]*)"', pm.group(1))
                fail(f"keep-layout: plate {nm.group(1) if nm else '?'!r} content "
                     f"spans {dx:.0f}x{dy:.0f} mm, over the {bed_w:g}x{bed_d:g} "
                     f"bed — a swapped mesh outgrew its slot; drop --keep-layout "
                     f"to re-pack")
        # Re-rest each object on z=0: keep the template's x/y and rotation, but
        # set the item transform's Z so the object sits on the plate. A swapped
        # mesh of a different height would otherwise sink through or float, since
        # the template's Z was chosen for the old mesh.
        def _frame_zmin(oid):
            zs = []
            for f, cid in comps.get(oid, []):
                got = parse_meshes((work / f.lstrip("/")).read_text()).get(int(cid))
                if not got:
                    continue
                _, verts, _ = got
                cm = re.search(rf'<object id="{oid}"[^>]*>\s*<components>.*?'
                               rf'objectid="{cid}"[^>]*transform="([^"]+)"', xml, re.S)
                c = [float(x) for x in cm.group(1).split()]
                zs += [x*c[2] + y*c[5] + z*c[8] + c[11] for x, y, z in verts]
            return min(zs) if zs else 0.0

        def _set_tz(m, zmin):
            v = m.group(2).split()
            v[11] = f"{-zmin:.9g}"
            return m.group(1) + " ".join(v) + m.group(3)

        for oid in comps:
            zmin = _frame_zmin(oid)
            xml = re.sub(rf'(<item objectid="{oid}" [^>]*transform=")([^"]+)(")',
                         lambda m: _set_tz(m, zmin), xml, count=1)
            cfg = re.sub(rf'(<assemble_item object_id="{oid}"[^>]*transform=")'
                         r'([^"]+)(")', lambda m: _set_tz(m, zmin), cfg, count=1)
        print("keep-layout: kept x/y + rotation, re-rested every object on z=0")
    else:
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

        # oriented-box collision tests (rotated placements need more than AABBs)
        def _proj(o, ax):
            c, s = math.cos(o[4]), math.sin(o[4])
            mid = o[0] * ax[0] + o[1] * ax[1]
            r = o[2] * abs(c * ax[0] + s * ax[1]) \
                + o[3] * abs(-s * ax[0] + c * ax[1])
            return mid - r, mid + r

        def sat_overlap(a, b, gap=0.0):
            """a, b: (cx, cy, hx, hy, theta) oriented boxes."""
            for o in (a, b):
                c, s = math.cos(o[4]), math.sin(o[4])
                for ax in ((c, s), (-s, c)):
                    a0, a1 = _proj(a, ax)
                    b0, b1 = _proj(b, ax)
                    if a1 + gap <= b0 or b1 + gap <= a0:
                        return False
            return True

        def rect_obb(x0, y0, x1, y1):
            return ((x0 + x1) / 2, (y0 + y1) / 2,
                    (x1 - x0) / 2, (y1 - y0) / 2, 0.0)

        def obb_aabb(o):
            c, s = math.cos(o[4]), math.sin(o[4])
            rx = o[2] * abs(c) + o[3] * abs(s)
            ry = o[2] * abs(s) + o[3] * abs(c)
            return o[0] - rx, o[1] - ry, o[0] + rx, o[1] + ry

        # ---- auto-plates bed selection: smallest bed that fits (rotated) ----
        profile_swapped = False
        if args.auto_plates and bed_mode != "template":
            dims = {}
            for oid in objects:
                lo, hi = obj_bbox(oid)
                dims[oid] = (hi[0] - lo[0], hi[1] - lo[1])

            def _fits(bw, bd):
                # every object must clear the bed once turned 45° (its rotated
                # span is the diagonal of its footprint), leaving BED_MARGIN
                m = min(bw, bd) - BED_MARGIN
                return all((w + d) / math.sqrt(2) <= m for w, d in dims.values())

            if bed_mode == "auto":
                choice = next((b for b in BED_TABLE if _fits(b[1], b[2])), None)
                if choice is None:
                    fail("no candidate bed fits every part even rotated 45 deg")
            else:
                want = "p1p" if bed_mode == "p1" else "h2c"
                choice = next(b for b in BED_TABLE if b[3] == want)
                if not _fits(choice[1], choice[2]):
                    print(f"  warning: forced bed {choice[0]} may not fit all parts")
            name, bw, bd, pkey, model = choice
            if ps.get("printer_model") != model:
                colour = ps.get("filament_colour")
                ps = json.loads((PROFILES / f"{pkey}.config").read_text())
                if colour:
                    ps["filament_colour"] = colour       # keep black/white order
                profile_swapped = True
                print(f"auto-bed: {name} — switched printer profile to {model}")
            else:
                print(f"auto-bed: {name} (template already {model})")
            # recompute every bed-derived local from the (possibly new) profile
            area = [tuple(map(float, p.split("x"))) for p in ps["printable_area"]]
            bed_w = max(p[0] for p in area)
            bed_d = max(p[1] for p in area)
            stride_x, stride_y = bed_w * 1.2, bed_d * 1.2
            tower_w = float(ps.get("prime_tower_width", 35))
            wx[:] = [float(v) for v in ps.get("wipe_tower_x", [])]
            wy[:] = [float(v) for v in ps.get("wipe_tower_y", [])]

        ex = [tuple(map(float, p.split("x")))
              for p in ps.get("bed_exclude_area", [])]
        ex_obb = (rect_obb(min(p[0] for p in ex), min(p[1] for p in ex),
                           max(p[0] for p in ex), max(p[1] for p in ex))
                  if ex else None)

        def obj_gap(oid):                    # per-object gap override, else --gap
            nm = objects.get(oid, "")
            return next((g for p, g in gap_over.items() if nm.startswith(p)),
                        args.gap)

        # ---- auto plate scheme: regroup by role, split thin-strip plates to fit --
        if args.auto_plates:
            gap_over.setdefault("Holder", 2.0)     # thin strips pack tight so they
            gap_over.setdefault("Topper", 2.0)     # fit one plate (overridable)

            def _dims(oid):
                lo, hi = obj_bbox(oid)
                return hi[0] - lo[0], hi[1] - lo[1]
            bed = min(bed_w, bed_d)
            groups = []
            for name, oids in auto_plate_groups(objects, plates, Path(args.out).stem):
                # A big object that must rotate 45° fills its plate diagonally,
                # leaving no room for flat companions (e.g. the box's pushers on
                # a P1 bed). Give those companions their own plate.
                rot = [o for o in oids if max(_dims(o)) > bed - 20]
                flat = [o for o in oids if o not in rot]
                if rot and flat:
                    base, _, title = name.partition(" — ")
                    groups.append((f"{_role(objects[rot[0]])} — {title}", rot))
                    groups.append((f"{_role(objects[flat[0]])}s — {title}", flat))
                    continue
                longest = max(max(_dims(o)) for o in oids)
                depth = max(min(_dims(o)) for o in oids)
                # thin strips (holders/toppers) get rotated 45° and packed in a
                # diagonal band; if too many for one bed, split across plates.
                thin = depth < 30 and all(max(_dims(o)) > bed - 20 for o in oids)
                if thin and len(oids) > 1:
                    g = obj_gap(oids[0])
                    band = (bed - 20) * math.sqrt(2) - longest
                    per = max(1, int((band + g) / (depth + g)))
                else:
                    per = len(oids)
                if per >= len(oids):
                    groups.append((name, oids))
                else:
                    base, _, title = name.partition(" — ")
                    chunks = [oids[i:i + per] for i in range(0, len(oids), per)]
                    for k, ch in enumerate(chunks, 1):
                        groups.append((f"{base} {k} of {len(chunks)} — {title}", ch))
            cfg = regroup_cfg(cfg, ps, groups)
            plates = [(i, nm, oids) for i, (nm, oids) in enumerate(groups, 1)]
            wx[:] = [15.0] * len(groups)
            wy[:] = [200.0] * len(groups)
            print("auto-plates: " + ", ".join(
                f"{nm.partition(' — ')[0]} ({len(o)})" for nm, o in groups))

        ROT = math.pi / 4
        cols = plate_columns(len(plates))
        placements = {}     # object id -> (theta, x, y, z) build transform
        towers_moved = False
        for idx, (pid, pname, objs) in enumerate(sorted(plates)):
            if not objs:
                continue
            org = ((pid - 1) % cols * stride_x,
                   -((pid - 1) // cols) * stride_y)
            boxes = {oid: obj_bbox(oid) for oid in objs}

            def dims2(oid):
                lo, hi = boxes[oid]
                return hi[0] - lo[0], hi[1] - lo[1]

            rot_ids = [oid for oid in objs
                       if max(dims2(oid)) > min(bed_w, bed_d) - 20]
            for oid in rot_ids:
                need = sum(dims2(oid)) / math.sqrt(2)
                if need > min(bed_w, bed_d):
                    fail(f"plate {pid}: {objects[oid]} cannot fit the "
                         f"{bed_w:g}x{bed_d:g} bed even rotated 45 deg "
                         f"(diagonal bounding box {need:.1f} mm)")
            placed = []     # (object id, obb)
            if rot_ids:
                # 45-deg strips along the bed diagonal, centred as a band,
                # then everything else grid-searched into the free corners
                n_hat = (-1 / math.sqrt(2), 1 / math.sqrt(2))
                _sr = sorted(rot_ids, key=lambda o: -dims2(o)[1])
                _rg = [obj_gap(o) for o in _sr[:-1]]      # per-strip gaps
                band = sum(dims2(o)[1] for o in _sr) + sum(_rg)
                off = -band / 2
                for _i, oid in enumerate(_sr):
                    w, d = dims2(oid)
                    cn = off + d / 2
                    off += d + (_rg[_i] if _i < len(_rg) else 0.0)
                    cx = bed_w / 2 + n_hat[0] * cn
                    cy = bed_d / 2 + n_hat[1] * cn
                    placements[oid] = (ROT, cx, cy)
                    placed.append((oid, (cx, cy, w / 2, d / 2, ROT)))
                flat = sorted((o for o in objs if o not in rot_ids),
                              key=lambda o: -dims2(o)[0] * dims2(o)[1])
                for oid in flat:
                    w, d = dims2(oid)
                    spot = None
                    cy = bed_d - 10 - d / 2
                    while spot is None and cy >= 10 + d / 2:
                        cx = 10 + w / 2
                        while cx <= bed_w - 10 - w / 2:
                            cand = (cx, cy, w / 2, d / 2, 0.0)
                            if not (ex_obb and sat_overlap(cand, ex_obb,
                                                           args.gap)) \
                               and not any(sat_overlap(cand, ob, args.gap)
                                           for _, ob in placed):
                                spot = cand
                                break
                            cx += 4.0
                        cy -= 4.0
                    if spot is None:
                        fail(f"plate {pid}: no room left for {objects[oid]}")
                    placements[oid] = (0.0, spot[0], spot[1])
                    placed.append((oid, spot))
                print(f"plate {pid}: {len(rot_ids)} object(s) rotated 45 deg, "
                      f"{len(flat)} flat")
            else:
                # shelf rows, widest-first
                order = sorted(objs, key=lambda o: -dims2(o)[0] * dims2(o)[1])
                rows, cur, cur_w = [], [], 0.0
                for oid in order:
                    w = dims2(oid)[0]
                    if cur and cur_w + args.gap + w > bed_w - 20:
                        rows.append(cur)
                        cur, cur_w = [], 0.0
                    cur.append(oid)
                    cur_w += (args.gap if cur_w else 0.0) + w
                if cur:
                    rows.append(cur)
                def _row_prefix(row):        # the gap-override key common to a row
                    ps = {next((p for p in gap_over
                                if objects.get(o, "").startswith(p)), None)
                          for o in row}
                    return ps.pop() if len(ps) == 1 else None
                # gap between two adjacent rows: the override only when BOTH rows are
                # the same overridden type (e.g. topper-to-topper), else --gap.
                rgaps = []
                for a, b in zip(rows, rows[1:]):
                    pa, pb = _row_prefix(a), _row_prefix(b)
                    rgaps.append(gap_over[pa] if pa and pa == pb else args.gap)
                depths = [max(dims2(o)[1] for o in r) for r in rows]
                total_d = sum(depths) + sum(rgaps)
                y0 = (bed_d - total_d) / 2
                for j, (row, depth) in enumerate(zip(rows, depths)):
                    widths = [dims2(o)[0] for o in row]
                    total_w = sum(widths) + args.gap * (len(row) - 1)
                    x0 = (bed_w - total_w) / 2
                    for oid, w in zip(row, widths):
                        d = dims2(oid)[1]
                        cx, cy = x0 + w / 2, y0 + depth / 2
                        placements[oid] = (0.0, cx, cy)
                        placed.append((oid, (cx, cy, w / 2, d / 2, 0.0)))
                        x0 += w + args.gap
                    y0 += depth + (rgaps[j] if j < len(rgaps) else 0.0)
                print(f"plate {pid}: {len(objs)} object(s) in "
                      f"{len(rows)} row(s)")

            # nudge the whole plate off a corner exclude area if centring
            # clipped it (e.g. a near-bed-width box on a P1P, whose 18x28 mm
            # bottom-left corner is reserved). Shift in x away from the exclude
            # by just enough to clear it, provided everything stays on the bed.
            if ex_obb and placed:
                ex_x0, ex_y0, ex_x1, ex_y1 = obb_aabb(ex_obb)
                min_x0 = min(obb_aabb(ob)[0] for _, ob in placed)
                max_x1 = max(obb_aabb(ob)[2] for _, ob in placed)
                left = (ex_x0 + ex_x1) / 2 < bed_w / 2   # exclude on the left?
                dx = 0.0
                for _, ob in placed:
                    x0, y0, x1, y1 = obb_aabb(ob)
                    if y0 >= ex_y1 + CLEARANCE or y1 <= ex_y0 - CLEARANCE:
                        continue                          # clears it in y already
                    if left and x0 < ex_x1 + CLEARANCE and x1 > ex_x0:
                        dx = max(dx, ex_x1 + CLEARANCE - x0 + 0.5)
                    elif not left and x1 > ex_x0 - CLEARANCE and x0 < ex_x1:
                        dx = min(dx, ex_x0 - CLEARANCE - x1 - 0.5)
                if dx and 0 <= min_x0 + dx and max_x1 + dx <= bed_w:
                    placed = [(oid, (ob[0] + dx,) + ob[1:]) for oid, ob in placed]
                    for oid, _ in placed:
                        th, x, y = placements[oid]
                        placements[oid] = (th, x + dx, y)
                    print(f"plate {pid}: shifted {dx:+.1f} mm in x to clear the "
                          "bed exclude area")

            # validation: bed bounds, exclude area, mutual clearance
            for i, (oid, ob) in enumerate(placed):
                x0, y0, x1, y1 = obb_aabb(ob)
                if x0 < 0 or y0 < 0 or x1 > bed_w or y1 > bed_d:
                    fail(f"plate {pid}: {objects[oid]} does not fit the bed "
                         f"({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f})")
                if ex_obb and sat_overlap(ob, ex_obb, CLEARANCE):
                    fail(f"plate {pid}: {objects[oid]} enters the bed's "
                         f"exclude area")
                for oid2, ob2 in placed[:i]:
                    if sat_overlap(ob, ob2, CLEARANCE):
                        fail(f"plate {pid}: {objects[oid]} overlaps "
                             f"{objects[oid2]}")

            # wipe tower: relocate to the nearest free spot if it collides
            if idx < len(wx):
                def tower_free(x, y, gap):
                    if x < 0 or y < 0 or x + tower_w > bed_w \
                            or y + tower_w > bed_d:
                        return False
                    t_obb = rect_obb(x, y, x + tower_w, y + tower_w)
                    if ex_obb and sat_overlap(t_obb, ex_obb, gap):
                        return False
                    return not any(sat_overlap(t_obb, ob, gap)
                                   for _, ob in placed)
                WIPE_GAP = 15.0                      # clearance from printed parts
                if not tower_free(wx[idx], wy[idx], WIPE_GAP):
                    best = None
                    for gap in (WIPE_GAP, 5.0):      # prefer clearance, then any fit
                        gy = 0.0
                        while gy + tower_w <= bed_d:
                            gx = 0.0
                            while gx + tower_w <= bed_w:
                                if tower_free(gx, gy, gap):
                                    # emptiest spot: furthest from centre (parts are
                                    # centred) so the tower sits in a free corner
                                    cx_t = gx + tower_w / 2 - bed_w / 2
                                    cy_t = gy + tower_w / 2 - bed_d / 2
                                    d2 = cx_t * cx_t + cy_t * cy_t
                                    if best is None or d2 > best[0]:
                                        best = (d2, gx, gy)
                                gx += 4.0
                            gy += 4.0
                        if best is not None:
                            break
                    if best is None:
                        print(f"plate {pid}: wipe tower collides and no free "
                              f"spot exists - left at ({wx[idx]:g},{wy[idx]:g})")
                    else:
                        print(f"plate {pid}: wipe tower moved "
                              f"({wx[idx]:g},{wy[idx]:g}) -> "
                              f"({best[1]:g},{best[2]:g})")
                        wx[idx], wy[idx] = best[1], best[2]
                        towers_moved = True

            # to world coordinates: rotate about z, then translate
            for oid, ob in placed:
                th, cx, cy = placements[oid][0], ob[0], ob[1]
                lo, hi = boxes[oid]
                c, s = math.cos(th), math.sin(th)
                bcx, bcy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
                placements[oid] = (th,
                                   org[0] + cx - (bcx * c - bcy * s),
                                   org[1] + cy - (bcx * s + bcy * c),
                                   -lo[2])

        if towers_moved or profile_swapped:
            if towers_moved:
                ps["wipe_tower_x"] = [f"{v:g}" for v in wx]
                ps["wipe_tower_y"] = [f"{v:g}" for v in wy]
            (work / "Metadata/project_settings.config").write_text(
                json.dumps(ps, ensure_ascii=False, indent=4))

        for oid, (th, tx, ty, tz) in placements.items():
            c, s = math.cos(th), math.sin(th)
            xml, n = re.subn(
                rf'(<item objectid="{oid}" [^>]*transform=")[^"]+(")',
                lambda m: m.group(1)
                + f"{c:.9g} {s:.9g} 0 {-s:.9g} {c:.9g} 0 0 0 1 "
                  f"{tx:.9g} {ty:.9g} {tz:.9g}"
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
