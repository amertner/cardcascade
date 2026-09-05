"""A Bambu Studio project 3MF, written from parts and placements — no donor.

`automation/make_cascade.py` mutates a donor project into a new one, and so
cannot make a project where none exists. This writes one: the bed profile from
`automation/profiles/` is the settings, the parts come from `build/` (or
anywhere `mesh3mf.read` reads), and the caller says which plate each object is
on and where. Nothing here decides a layout — that is the next module's job —
but a layout can be READ off an existing project (`read`), which is how the
first cascade written this way was checked against its shipped twin.

The file format is recorded in `spec/PROJECT.md`; the rules below that are
not obvious from the format carry the reason in place.

    from cad import project as PJ
    objs = [PJ.Obj.from_file("Box", Path("build/Dominion/Box S4.16.10.32-Un.3mf")), ...]
    plates = [PJ.Plate("Box + pushers", tower=(15, 200)), ...]
    places = [PJ.Placement(obj=0, plate=1, x=128, y=128, angle=0), ...]
    PJ.write(out, "p1", objs, plates, places, title="Dominion 168 Card Unsleeved v7.0 (S4.16.10.32-Un)")
"""
import json
import math
import re
import sys
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import mesh3mf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "automation"))
import filaments as FIL                                  # noqa: E402

PROFILES = ROOT / "automation" / "profiles"

# The print beds, smallest first, each with the profile that IS a project's
# settings on it (spec/PROJECT.md). A copy of make_cascade.BED_TABLE for as
# long as both exist; tests/test_project.py holds the two equal.
BEDS = {
    "mini": (180.0, 180.0, "a1mini", "Bambu Lab A1 mini"),
    "p1":   (256.0, 256.0, "p1p", "Bambu Lab P1P"),
    "h2c":  (330.0, 320.0, "h2c", "Bambu Lab H2C"),
}
PLATE_STRIDE = 1.2          # plates sit on a grid at 1.2 x the plate size

# Every cascade: white in slot 1, black in slot 2 (PIPELINE.md, "Filament slots").
FILAMENTS = ("#FFFFFF", "#000000")
BODY, INLAY = 1, 2          # the only two slots: bodies, and a mark's inlays

# Process settings this repo insists on, whatever the profile says. Arachne
# varies the wall width to fill what it is given; classic leaves the remainder
# of a thin wall as gap fill, which on these boxes is exactly where the slot
# dividers and the lid lettering are. A copy of make_cascade.PRINT_SETTINGS.
PRINT_SETTINGS = {"wall_generator": "arachne"}

# What Studio wrote the shipped files with. Kept as the Application string
# because it is a FORMAT marker — Studio reads it to decide how to interpret
# the rest — and the generator is named beside it in its own metadata.
APPLICATION = "BambuStudio-02.07.01.62"
GENERATOR = "cardcascade cad.project"

NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
      'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
      'requiredextensions="p"')
PLATE_SAFE = re.compile(r'[<>:/\\|?*"]')


def fail(msg):
    raise SystemExit(f"REFUSING: {msg}")


# --- the inputs -------------------------------------------------------------


@dataclass
class Part:
    """One mesh of an object, in the object's (the component file's) frame."""
    name: str
    verts: list
    tris: list
    extruder: int = BODY

    @property
    def bbox(self):
        xs, ys, zs = zip(*self.verts)
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    @property
    def centre(self):
        lo, hi = self.bbox
        return tuple((a + b) / 2 for a, b in zip(lo, hi))


@dataclass
class Obj:
    """A printed thing: one or more parts sharing a frame, and a role name."""
    name: str
    parts: list

    @classmethod
    def from_file(cls, name, path):
        """The object a component 3MF holds. Its inlays — `Part N`, the regions
        of a lid's or a topper's mark — go to the INLAY slot; the body and any
        other part to BODY (`cad/gltf.slot_for`'s rule)."""
        parts = [Part(n, v, t, INLAY if n.startswith("Part ") else BODY)
                 for n, v, t in mesh3mf.read(Path(path))]
        if not parts:
            fail(f"{path}: no mesh")
        return cls(name, parts)

    @property
    def bbox(self):
        boxes = [p.bbox for p in self.parts]
        return (tuple(min(b[0][i] for b in boxes) for i in range(3)),
                tuple(max(b[1][i] for b in boxes) for i in range(3)))

    @property
    def centre(self):
        lo, hi = self.bbox
        return tuple((a + b) / 2 for a, b in zip(lo, hi))

    @property
    def size(self):
        lo, hi = self.bbox
        return tuple(b - a for a, b in zip(lo, hi))


@dataclass
class Plate:
    """One plate: its name (the scheme's, e.g. `Lid`; the title is appended)
    and the prime tower's corner in PLATE coordinates."""
    name: str
    tower: tuple = (15.0, 200.0)


@dataclass
class Placement:
    """Object `obj` (an index into the objects list) on plate `plate`
    (1-based), its bbox centre at (`x`, `y`) in PLATE coordinates, turned
    `angle` degrees about Z. Every object is placed exactly once."""
    obj: int
    plate: int
    x: float
    y: float
    angle: float = 0.0


# --- geometry ---------------------------------------------------------------


def plate_columns(n):
    """How many columns Studio lays `n` plates in: the ceiling of sqrt(n) —
    two for 2 to 4 plates, three for 5 to 9. make_cascade.plate_columns."""
    root = n ** 0.5
    return round(root) + 1 if root > round(root) else round(root)


def plate_origin(bed, plate, n_plates):
    """Where plate `plate` (1-based, of `n_plates`) sits in the project's one
    coordinate space: a grid of `plate_columns` columns at PLATE_STRIDE x the
    plate size, filled row by row, rows going -Y. Studio assigns an object to
    the plate whose cell it sits in — a five-plate project written on a
    two-column grid puts plate 3 where Studio has plate 4, and the slice
    stops with "no object fully inside" (found on Dominion 560 Sleeved)."""
    w, d = BEDS[bed][0], BEDS[bed][1]
    cols = plate_columns(n_plates)
    col, row = (plate - 1) % cols, (plate - 1) // cols
    return col * PLATE_STRIDE * w, -row * PLATE_STRIDE * d


def item_transform(obj, place, origin):
    """The build item's 4x3 row-vector transform for a bbox-centred object:
    a rotation about Z, then the centre to (origin + x, origin + y, h/2), so
    the object turns about its own centre and sits on the bed."""
    th = math.radians(place.angle)
    c, s = math.cos(th), math.sin(th)
    h = obj.size[2]
    return (f"{c:.9g} {s:.9g} 0 {-s:.9g} {c:.9g} 0 0 0 1 "
            f"{origin[0] + place.x:.9g} {origin[1] + place.y:.9g} {h / 2:.9g}")


def _g(v):
    return f"{v:.9g}"


def _xesc(s):
    return (s.replace("&", "&amp;").replace('"', "&quot;")
             .replace("<", "&lt;").replace(">", "&gt;"))


def _uuid():
    return str(uuid.uuid4())


# --- the members ------------------------------------------------------------


def mesh_model(mesh_id, part):
    """One sub-model file: the part's mesh, stored centred on its bbox."""
    cx, cy, cz = part.centre
    body = "".join(f'     <vertex x="{x - cx:.6f}" y="{y - cy:.6f}" z="{z - cz:.6f}"/>\n'
                   for x, y, z in part.verts)
    body += "    </vertices>\n    <triangles>\n"
    body += "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                    for a, b, c in part.tris)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<model unit="millimeter" xml:lang="en-US" {NS}>\n'
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
            ' <resources>\n'
            f'  <object id="{mesh_id}" p:UUID="{_uuid()}" type="model">\n'
            '   <mesh>\n    <vertices>\n' + body +
            '    </triangles>\n   </mesh>\n  </object>\n'
            ' </resources>\n <build/>\n</model>\n')


def settings(bed, n_plates, towers, filaments=FILAMENTS):
    """`project_settings.config`: the bed's profile, the colours in cascade
    order, PRINT_SETTINGS forced, one tower coordinate per plate."""
    ps = json.loads((PROFILES / f"{BEDS[bed][2]}.config").read_text())
    have = [c.upper() for c in ps.get("filament_colour", [])]
    want = [c.upper() for c in filaments]
    if sorted(have) != sorted(want):
        fail(f"profile {BEDS[bed][2]} carries filaments {have}, not {want}")
    order = [have.index(c) for c in want]
    if order != list(range(len(order))):
        # `remap` turns every per-filament array with the colours, the flush
        # matrix included — the profile is black-first, a cascade white-first.
        ps, _notes = FIL.remap(ps, order)
    ps = force_print_settings(ps)
    if len(towers) != n_plates:
        fail(f"{len(towers)} tower positions for {n_plates} plates")
    ps["wipe_tower_x"] = [_g(x) for x, _y in towers]
    ps["wipe_tower_y"] = [_g(y) for _x, y in towers]
    return ps


def force_print_settings(ps):
    """PRINT_SETTINGS applied, and each key listed in the PROCESS entry of
    `different_settings_to_system` — a changed key missing from that list is
    what makes Studio display the stock value while the project prints its
    own. A copy of make_cascade.force_print_settings."""
    out = dict(ps)
    out.update(PRINT_SETTINGS)
    dev = list(out.get("different_settings_to_system")
               or [""] * (2 + FIL.slots(out)))
    keys = [k for k in dev[0].split(";") if k]
    dev[0] = ";".join(sorted(set(keys) | set(PRINT_SETTINGS)))
    out["different_settings_to_system"] = dev
    return out


def plate_title(scheme, title):
    return PLATE_SAFE.sub("-", f"{scheme} — {title}")


def object_name(role, p, d):
    """What Studio's object list shows. Every role is its own name except the
    Lid, which carries the card capacity and the sleeving — `Lid 168U` — as
    every shipped project has it (Allan, 2026-09-05): with several projects
    open it is the lid that says which cascade a plate belongs to."""
    if role == "Lid":
        return f"Lid {d.calTotalCards}{'S' if p.isSleeved else 'U'}"
    return role


def write(path, bed, objects, plates, placements, title, filaments=FILAMENTS,
          metadata=None):
    """Write the project. `objects` [Obj], `plates` [Plate] (plate 1 first),
    `placements` [Placement], one per object. `metadata` is extra
    name -> value pairs for `3dmodel.model` — the source hash, say."""
    path = Path(path)
    if bed not in BEDS:
        fail(f"unknown bed {bed!r}; one of {sorted(BEDS)}")
    placed = sorted(p.obj for p in placements)
    if placed != list(range(len(objects))):
        fail(f"every object must be placed exactly once; got {placed}")
    for p in placements:
        if not 1 <= p.plate <= len(plates):
            fail(f"placement on plate {p.plate}; there are {len(plates)}")

    # Ids: one space for objects and meshes. Objects take 1..n, meshes follow.
    n = len(objects)
    next_id = n + 1
    resources, build_items, cfg_objects, meshes = [], [], [], {}
    identify = 100
    for oi, obj in enumerate(objects):
        oid = oi + 1
        ocx, ocy, ocz = obj.centre
        comps, parts_cfg = [], []
        fname = f"/3D/Objects/object_{oid}.model"
        chunks = []
        for part in obj.parts:
            mid = next_id
            next_id += 1
            chunks.append(mesh_model(mid, part))
            cx, cy, cz = part.centre
            if len(obj.parts) == 1:
                tr = (0.0, 0.0, 0.0)
            else:
                tr = (cx - ocx, cy - ocy, cz - ocz)
            comps.append(f'    <component p:path="{fname}" objectid="{mid}" '
                         f'p:UUID="{_uuid()}" transform="1 0 0 0 1 0 0 0 1 '
                         f'{_g(tr[0])} {_g(tr[1])} {_g(tr[2])}"/>\n')
            ext = (f'      <metadata key="extruder" value="{part.extruder}"/>\n'
                   if part.extruder != BODY else "")
            parts_cfg.append(
                f'    <part id="{mid}" subtype="normal_part">\n'
                f'      <metadata key="name" value="{_xesc(part.name)}"/>\n'
                f'      <metadata key="matrix" value="1 0 0 {_g(tr[0])} 0 1 0 '
                f'{_g(tr[1])} 0 0 1 {_g(tr[2])} 0 0 0 1"/>\n'
                f'      <metadata key="source_file" value="{_xesc(obj.name)}"/>\n'
                f'      <metadata key="source_object_id" value="0"/>\n'
                f'      <metadata key="source_volume_id" value="0"/>\n'
                f'      <metadata key="source_offset_x" value="{_g(cx)}"/>\n'
                f'      <metadata key="source_offset_y" value="{_g(cy)}"/>\n'
                f'      <metadata key="source_offset_z" value="{_g(cz)}"/>\n'
                + ext +
                f'      <mesh_stat face_count="{len(part.tris)}" edges_fixed="0" '
                f'degenerate_facets="0" facets_removed="0" facets_reversed="0" '
                f'backwards_edges="0"/>\n'
                f'    </part>\n')
        # every mesh of an object in ONE sub-model file, as Studio writes them
        meshes[fname.lstrip("/")] = _merge_models(chunks)
        resources.append(f'  <object id="{oid}" p:UUID="{_uuid()}" type="model">\n'
                         '   <components>\n' + "".join(comps) +
                         '   </components>\n  </object>\n')
        cfg_objects.append(
            f'  <object id="{oid}">\n'
            f'    <metadata key="name" value="{_xesc(obj.name)}"/>\n'
            f'    <metadata key="extruder" value="{BODY}"/>\n'
            f'    <metadata face_count="{sum(len(p.tris) for p in obj.parts)}"/>\n'
            + "".join(parts_cfg) + '  </object>\n')

    by_plate = {i + 1: [] for i in range(len(plates))}
    assemble = []
    for place in placements:
        obj = objects[place.obj]
        oid = place.obj + 1
        origin = plate_origin(bed, place.plate, len(plates))
        tr = item_transform(obj, place, origin)
        build_items.append(f'  <item objectid="{oid}" p:UUID="{_uuid()}" '
                           f'transform="{tr}" printable="1"/>\n')
        identify += 11
        by_plate[place.plate].append(
            '    <model_instance>\n'
            f'      <metadata key="object_id" value="{oid}"/>\n'
            '      <metadata key="instance_id" value="0"/>\n'
            f'      <metadata key="identify_id" value="{identify}"/>\n'
            '    </model_instance>\n')
        tx, ty = origin[0] + place.x, origin[1] + place.y
        assemble.append(f'   <assemble_item object_id="{oid}" instance_id="0" '
                        f'transform="1 0 0 0 1 0 0 0 1 {_g(tx)} {_g(ty)} '
                        f'{_g(obj.size[2] / 2)}" offset="0 0 0" />\n')

    cfg_plates = []
    for i, plate in enumerate(plates, start=1):
        if not by_plate[i]:
            fail(f"plate {i} ({plate.name}) has no object on it")
        cfg_plates.append(
            '  <plate>\n'
            f'    <metadata key="plater_id" value="{i}"/>\n'
            f'    <metadata key="plater_name" value="{_xesc(plate_title(plate.name, title))}"/>\n'
            '    <metadata key="locked" value="false"/>\n'
            '    <metadata key="filament_map_mode" value="Auto For Flush"/>\n'
            + "".join(by_plate[i]) + '  </plate>\n')

    meta = {"Application": APPLICATION, "BambuStudio:3mfVersion": "1",
            "Title": title, "cardcascade:generator": GENERATOR}
    meta.update(metadata or {})
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             f'<model unit="millimeter" xml:lang="en-US" {NS}>\n'
             + "".join(f' <metadata name="{_xesc(k)}">{_xesc(str(v))}</metadata>\n'
                       for k, v in meta.items())
             + ' <resources>\n' + "".join(resources) + ' </resources>\n'
             f' <build p:UUID="{_uuid()}">\n' + "".join(build_items) + ' </build>\n'
             '</model>\n')
    cfg = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
           + "".join(cfg_objects) + "".join(cfg_plates)
           + '  <assemble>\n' + "".join(assemble) + '  </assemble>\n</config>\n')
    ps = settings(bed, len(plates), [p.tower for p in plates], filaments)
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            + "".join(f' <Relationship Target="/{f}" Id="rel-{i}" Type="http://schemas.'
                      'microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
                      for i, f in enumerate(meshes, start=1))
            + '</Relationships>\n')
    members = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": RELS,
        "3D/3dmodel.model": model,
        "3D/_rels/3dmodel.model.rels": rels,
        "Metadata/model_settings.config": cfg,
        "Metadata/project_settings.config": json.dumps(ps, ensure_ascii=False, indent=4),
        "Metadata/cut_information.xml": (
            '<?xml version="1.0" encoding="utf-8"?>\n<objects>\n'
            + "".join(f' <object id="{i}">\n  <cut_id id="0" check_sum="1" '
                      f'connectors_cnt="0"/>\n </object>\n' for i in range(1, n + 1))
            + '</objects>\n'),
        "Metadata/filament_sequence.json": json.dumps(
            {f"plate_{i}": {"nozzle_sequence": [], "optimal_assignment": [], "sequence": []}
             for i in range(1, len(plates) + 1)}),
        "Metadata/slice_info.config": SLICE_INFO,
    }
    members.update(meshes)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in members.items():
            z.writestr(zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0)), text)
    return path


def _merge_models(chunks):
    """Several one-object sub-model documents into one document."""
    head, sep, _ = chunks[0].partition(" <resources>\n")
    objs = "".join(c.split(" <resources>\n", 1)[1].split(" </resources>", 1)[0]
                   for c in chunks)
    return head + sep + objs + " </resources>\n <build/>\n</model>\n"


CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
    ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
    ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
    ' <Default Extension="png" ContentType="image/png"/>\n'
    ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n'
    '</Types>\n')
RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
    ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
    '</Relationships>\n')
SLICE_INFO = (
    '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
    '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
    f'    <header_item key="X-BBL-Client-Version" value="{APPLICATION.split("-")[1]}"/>\n'
    '  </header>\n</config>\n')


# --- reading a project's layout ---------------------------------------------


@dataclass
class Layout:
    """What `read` recovers from a project: enough to write it again."""
    bed: str
    title: str
    objects: list = field(default_factory=list)     # (id, name, [(part name, extruder)])
    plates: list = field(default_factory=list)      # Plate
    placements: dict = field(default_factory=dict)  # object id -> Placement (obj = id)
    sizes: dict = field(default_factory=dict)       # object id -> (w, d, h) in its own frame


def read(path):
    """The layout of an existing project: its bed, plates, towers and where
    each object sits, in PLATE coordinates. The mesh sizes come with it so a
    caller can tell whether a replacement part still fits the slot."""
    zf = zipfile.ZipFile(path)
    ps = json.loads(zf.read("Metadata/project_settings.config"))
    bed = next((k for k, v in BEDS.items() if v[3] == ps.get("printer_model")), None)
    if bed is None:
        # the P1S is a P1P's bed with a lid on it
        area = ps.get("printable_area", [])
        bed = {("256x256",): "p1", ("330x320",): "h2c", ("180x180",): "mini"}.get(
            (area[2],) if len(area) > 2 else (), None)
    if bed is None:
        fail(f"{path}: unknown printer {ps.get('printer_model')!r}")
    cfg = zf.read("Metadata/model_settings.config").decode()
    xml = zf.read("3D/3dmodel.model").decode()
    title = ""
    m = re.search(r'<metadata name="Title">([^<]*)</metadata>', xml)
    if m and m.group(1):
        title = m.group(1)
    else:
        title = Path(path).stem
    out = Layout(bed=bed, title=title)
    # object names, extruders, parts
    for ob in re.finditer(r'<object id="(\d+)">(.*?)</object>', cfg, re.S):
        oid, body = int(ob.group(1)), ob.group(2)
        name = re.search(r'key="name" value="([^"]*)"', body).group(1)
        oext = int(re.search(r'key="extruder" value="(\d+)"', body).group(1))
        parts = []
        for pb in re.finditer(r'<part id="\d+"[^>]*>(.*?)</part>', body, re.S):
            pname = re.search(r'key="name" value="([^"]*)"', pb.group(1)).group(1)
            pe = re.search(r'key="extruder" value="(\d+)"', pb.group(1))
            parts.append((pname, int(pe.group(1)) if pe else oext))
        out.objects.append((oid, name, parts))
    # sizes: mesh bboxes through the component transforms
    mesh_box = {}
    for rel in re.findall(r'Target="/(3D/Objects/[^"]+)"', zf.read("3D/_rels/3dmodel.model.rels").decode()):
        txt = zf.read(rel).decode()
        for mo in re.finditer(r'<object id="(\d+)".*?<mesh>(.*?)</mesh>', txt, re.S):
            xs = [float(v) for v in re.findall(r'<vertex x="([^"]+)"', mo.group(2))]
            ys = [float(v) for v in re.findall(r'y="([^"]+)" z=', mo.group(2))]
            zs = [float(v) for v in re.findall(r'z="([^"]+)"/>', mo.group(2))]
            mesh_box[(rel, int(mo.group(1)))] = ((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))
    for ob in re.finditer(r'<object id="(\d+)"[^>]*>\s*<components>(.*?)</components>', xml, re.S):
        oid = int(ob.group(1))
        lo = [float("inf")] * 3
        hi = [-float("inf")] * 3
        for c in re.finditer(r'<component p:path="/([^"]+)" objectid="(\d+)"[^>]*transform="([^"]+)"', ob.group(2)):
            t = [float(v) for v in c.group(3).split()]
            box = mesh_box[(c.group(1), int(c.group(2)))]
            for i in range(3):
                lo[i] = min(lo[i], box[0][i] + t[9 + i])
                hi[i] = max(hi[i], box[1][i] + t[9 + i])
        out.sizes[oid] = tuple(h - l for l, h in zip(lo, hi))
    # plates and towers
    wx = [float(v) for v in ps.get("wipe_tower_x", [])]
    wy = [float(v) for v in ps.get("wipe_tower_y", [])]
    plate_of = {}
    for i, pb in enumerate(re.finditer(r'<plate>(.*?)</plate>', cfg, re.S), start=1):
        name = re.search(r'key="plater_name" value="([^"]*)"', pb.group(1)).group(1)
        scheme = name.split(" — ")[0] if " — " in name else name
        out.plates.append(Plate(scheme, (wx[i - 1], wy[i - 1]) if i <= len(wx) else (15.0, 200.0)))
        for oid in re.findall(r'key="object_id" value="(\d+)"', pb.group(1)):
            plate_of[int(oid)] = i
    # placements, back into plate coordinates
    for it in re.finditer(r'<item objectid="(\d+)"[^>]*transform="([^"]+)"', xml):
        oid = int(it.group(1))
        t = [float(v) for v in it.group(2).split()]
        plate = plate_of.get(oid)
        if plate is None:
            fail(f"{path}: object {oid} is on no plate")
        ox, oy = plate_origin(bed, plate, len(out.plates))
        angle = math.degrees(math.atan2(t[1], t[0]))
        out.placements[oid] = Placement(oid, plate, t[9] - ox, t[10] - oy, angle)
    return out
