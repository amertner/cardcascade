"""Writing a component 3MF in the shape Onshape's exports have.

`individual/<Game>/*.3mf` is the interface the rest of the toolchain reads and
three readers assume its shape, `make_cascade.load_export` REFUSING a build
item that carries a transform. So the rebuild writes that shape:

    [Content_Types].xml, _rels/.rels, 3D/3dmodel.model
    unit="meter"                      -- so every coordinate is mm / 1000
    <object id="N" name="Pusher" ...> -- id FIRST; parse_meshes' regex requires it
    <build><item objectid="N" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build>

Meshing is the last step and the only lossy one. `TOLERANCE` / `ANGULAR` put
roughly Onshape's triangle count on a pusher, so `verify.py`'s sampling checks
see the density they were tuned on. NB `TOLERANCE` is a RELATIVE deflection —
a fraction of each edge's own size, as build123d's `Shape.mesh` calls OCCT —
and NOT 0.01 mm of chord. Vertices are welded on a 1e-6 mm key
(`_drop_flaps`), and the archive carries a FIXED timestamp, so rebuilding
unchanged source gives a byte-identical file.
"""
import re
import sys
import zipfile

TOLERANCE = 0.01        # RELATIVE deflection, see above
# OCCT meshes a shape's faces on its own thread pool, which inside cad.build's
# process pool is one shape's threads per worker on every core at once, so
# `build.run_jobs` turns it off in each worker (`serial_meshing`).
PARALLEL = True
ANGULAR = 0.2           # radians
_EPOCH = (1980, 1, 1, 0, 0, 0)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-'
    'package.relationships+xml"/><Default Extension="model" ContentType='
    '"application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')

RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    '</Relationships>')


def _drop_flaps(tris):
    """Remove back-to-back coincident triangle PAIRS left by the weld.

    Where two faces are TANGENT the same three vertices can come out twice,
    wound opposite ways: a zero-thickness flap, so dropping both leaves the
    solid untouched and the surface closed. Same-winding duplicates are NOT
    dropped — a doubled surface is a bug worth seeing. `spec/HOLDER.md`.
    """
    where = {}
    for i, t in enumerate(tris):
        where.setdefault(tuple(sorted(t)), []).append(i)
    drop = set()
    for same_verts in where.values():
        if len(same_verts) != 2:
            continue
        a, b = (tris[i] for i in same_verts)
        # Opposite winding: b traverses one of a's edges backwards.
        if (a[1], a[0]) in ((b[0], b[1]), (b[1], b[2]), (b[2], b[0])):
            drop.update(same_verts)
    return [t for i, t in enumerate(tris) if i not in drop]


class MeshFault(Exception):
    """A body that is not a closed surface — see `faults`."""


def faults(tris):
    """`(unpaired, doubled)` directed-edge counts for a triangle list.

    A closed orientable surface traverses every directed edge exactly once and
    its reverse exactly once. `unpaired` counts an edge whose reverse is
    missing — an OPEN BOUNDARY; `doubled` one walked more than once, material
    touching along a LINE: not a hole, but non-manifold all the same.
    """
    seen = {}
    for a, b, c in tris:
        for e in ((a, b), (b, c), (c, a)):
            seen[e] = seen.get(e, 0) + 1
    unpaired = sum(1 for e, n in seen.items() if seen.get((e[1], e[0]), 0) != n)
    doubled = sum(1 for n in seen.values() if n > 1)
    return unpaired, doubled


def triangulate(shape, tolerance=TOLERANCE, angular=ANGULAR):
    """(vertices in mm, triangles) for a build123d shape, vertices welded.

    Any triangulation the shape already carries is thrown away FIRST: OCCT
    keeps one it finds fine enough, so a face meshed earlier keeps old
    vertices while new faces get fresh ones and the two disagree along their
    shared edges. `BRepTools.Clean` prevents it.
    """
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_Orientation
    from OCP.TopLoc import TopLoc_Location
    BRepTools.Clean_s(shape.wrapped)
    # The same call build123d's `Shape.mesh` makes — RELATIVE deflection. The
    # walk below is `Shape.tessellate` with ONE change: triangles are read by
    # INDEX, never by iterating `poly.Triangles()`, which costs 250x in OCP.
    BRepMesh_IncrementalMesh(shape.wrapped, tolerance, True, angular, PARALLEL)
    index, out_v, out_t = {}, [], []
    for face in shape.faces():
        loc = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(face.wrapped, loc)
        if poly is None:
            continue
        trsf = loc.Transformation()
        remap = []
        for i in range(1, poly.NbNodes() + 1):
            pnt = poly.Node(i).Transformed(trsf)
            key = (round(pnt.X(), 6), round(pnt.Y(), 6), round(pnt.Z(), 6))
            j = index.get(key)
            if j is None:
                j = index[key] = len(out_v)
                out_v.append(key)
            remap.append(j)
        reverse = face.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
        for i in range(1, poly.NbTriangles() + 1):
            a, b, c = poly.Triangle(i).Get()
            if reverse:
                b, c = c, b
            t = (remap[a - 1], remap[b - 1], remap[c - 1])
            if len(set(t)) == 3:            # welding can collapse a sliver
                out_t.append(t)
    return out_v, _drop_flaps(out_t)


def serial_meshing():
    global PARALLEL
    PARALLEL = False


def _mesh_object(i, name, verts, tris):
    body = "".join(                     # one `<object>`, coordinates in METRES
        f'     <vertex x="{x / 1000:.8f}" y="{y / 1000:.8f}" '
        f'z="{z / 1000:.8f}"/>\n' for x, y, z in verts)
    body += "    </vertices>\n    <triangles>\n"
    body += "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                    for a, b, c in tris)
    return (f'  <object id="{i}" name="{name}" type="model">\n'
            f'   <mesh>\n    <vertices>\n{body}'
            f'    </triangles>\n   </mesh>\n  </object>\n')


# Our own metadata namespace. 3MF reserves the unprefixed metadata names and
# requires anything else to carry a declared prefix, so a custom key needs
# both halves.
NS_PREFIX = "CardCascade"
NS_URI = "urn:cardcascade:3mf:2026"
# The metadata names this writes and `verify.version_metadata` reads back.
VERSION_KEY = f"{NS_PREFIX}:Version"


def _xesc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _model(objects, build, metadata=None):
    """A 3dmodel.model document round `objects` and `build`, both XML.
    `metadata` is {name: value}, written as `<metadata>` children of `<model>`
    BEFORE `<resources>`, the order the spec requires. Every reader here takes
    its meshes by regex and ignores them, so this is additive."""
    meta = "".join(f' <metadata name="{_xesc(k)}">{_xesc(v)}</metadata>\n'
                   for k, v in (metadata or {}).items() if v is not None)
    ns = (f' xmlns:{NS_PREFIX}="{NS_URI}"'
          if any(k.startswith(f"{NS_PREFIX}:") for k in (metadata or {})) else "")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="meter" xml:lang="en-US" xmlns="http://schemas.'
            f'microsoft.com/3dmanufacturing/core/2015/02"{ns}>\n'
            + meta
            + ' <resources>\n' + objects + ' </resources>\n'
            ' <build>' + build + '</build>\n</model>\n')


def model_xml(parts, metadata=None):
    """[(name, verts_mm, tris)] as one object per part, each a build item at
    the identity."""
    objects = "".join(_mesh_object(i, name, verts, tris)
                      for i, (name, verts, tris) in enumerate(parts, start=1))
    items = "".join(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
                    for i in range(1, len(parts) + 1))
    return _model(objects, items, metadata)


def _write_zip(path, xml):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS),
                           ("3D/3dmodel.model", xml)):
            info = zipfile.ZipInfo(name, _EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)


def write(path, parts, tolerance=TOLERANCE, angular=ANGULAR, strict=True,
          metadata=None):
    """Write [(name, shape)] to `path` as a component 3MF. Returns the meshes.

    Every body is checked with `faults` first: an open boundary raises
    `MeshFault` and NOTHING is written; a doubled edge is reported and written.
    `metadata` states the RELEASE in the file itself.
    """
    meshed = [(name, *triangulate(shape, tolerance, angular))
              for name, shape in parts]
    for name, _verts, tris in meshed:
        unpaired, doubled = faults(tris)
        if unpaired and strict:
            raise MeshFault(f"{path.name} {name}: {unpaired} unpaired edges "
                            f"(an open boundary) — not written")
        if doubled or unpaired:
            print(f"  WARNING {path.name} {name}: {unpaired} unpaired, "
                  f"{doubled} doubled edges", file=sys.stderr)
    _write_zip(path, model_xml(meshed, metadata))
    return meshed


def _objects(path):
    """{id: (name, verts in mm, tris, [(component id, transform)])} for every
    `<object>` in a 3MF's model, plus the file's unit scale."""
    with zipfile.ZipFile(path) as z:
        text = z.read("3D/3dmodel.model").decode()
    scale = {"meter": 1000.0, "millimeter": 1.0}[
        re.search(r'unit="(\w+)"', text).group(1)]
    out = {}
    for om in re.finditer(r'<object id="(\d+)"([^>]*)>(.*?)</object>', text, re.S):
        oid, attrs, body = om.groups()
        name = re.search(r'name="([^"]*)"', attrs)
        verts = [(float(a) * scale, float(b) * scale, float(c) * scale)
                 for a, b, c in re.findall(
                     r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body)]
        tris = [(int(a), int(b), int(c)) for a, b, c in re.findall(
            r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body)]
        comps = [(int(c), [float(n) for n in t.split()]) for c, t in
                 re.findall(r'<component objectid="(\d+)" transform="([^"]+)"', body)]
        out[int(oid)] = (name.group(1) if name else None, verts, tris, comps)
    return out, scale


def read(path):
    """[(name, verts in mm, tris)] from a component 3MF — `write`'s inverse, so
    nothing re-derives the unit scale."""
    objects, _scale = _objects(path)
    return [(name, verts, tris) for name, verts, tris, _comps in objects.values()
            if verts and tris]


# An assembly is written the way Onshape's own `_raw` assemblies are: the
# component meshes as plain objects, then ONE object carrying a `<components>`
# list that instances them with a transform each; eight holders cost one mesh.
# The transform is 3MF's twelve numbers, `m00 ... m22 tx ty tz`, applied as a
# ROW vector: `v' = v * M + t`. The matrix's rows are the images of the part's
# own axes; the translation is in METRES, which is why it alone gets scaled.
# NB NOT a component 3MF, and it must never be written into `individual/`.


def assembly_xml(parts, instances, name="Assembly"):
    objects = "".join(_mesh_object(i, part_name, verts, tris)
                      for i, (part_name, verts, tris) in enumerate(parts, start=1))
    top = len(parts) + 1
    comps = "".join(
        f'    <component objectid="{k + 1}" transform="{pl.as_3mf()}"/>\n'
        for k, pl in instances)
    objects += (f'  <object id="{top}" name="{name}" type="model">\n'
                f'   <components>\n{comps}   </components>\n  </object>\n')
    return _model(objects, f'<item objectid="{top}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')


def write_assembly(path, parts, instances, name="Assembly",
                   tolerance=TOLERANCE, angular=ANGULAR):
    """Write an assembly 3MF. `parts` is [(name, shape_or_mesh)] — a build123d
    shape is meshed, a `(verts, tris)` pair taken as it is, which is how a
    cached component gets in."""
    meshed = []
    for part_name, shape in parts:
        if isinstance(shape, tuple):
            meshed.append((part_name, *shape))
        else:
            meshed.append((part_name, *triangulate(shape, tolerance, angular)))
    _write_zip(path, assembly_xml(meshed, instances, name))
    return meshed


def read_assembly(path):
    """[(name, verts in mm, tris)] with every instance PLACED. A file with no
    `<components>` reads as its own objects, so this works on a component 3MF
    too."""
    meshes, scale = _objects(path)

    # A mesh that something instances is emitted through its instances, NEVER
    # also on its own, or every component renders twice.
    instanced = {target for _n, _v, _t, comps in meshes.values()
                 for target, _m in comps}
    out = []
    for oid, (nm, verts, tris, comps) in meshes.items():
        if verts and tris and oid not in instanced:
            out.append((nm, verts, tris))
    for oid, (nm, _v, _t, comps) in meshes.items():
        for target, m in comps:
            cn, cv, ct, _ = meshes[target]
            tx, ty, tz = (n * scale for n in m[9:12])
            out.append((cn, [(x * m[0] + y * m[3] + z * m[6] + tx,
                              x * m[1] + y * m[4] + z * m[7] + ty,
                              x * m[2] + y * m[5] + z * m[8] + tz)
                             for x, y, z in cv], ct))
    return out
