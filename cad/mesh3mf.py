"""Writing a component 3MF in the shape Onshape's exports have.

`individual/<Game>/*.3mf` is the interface the rest of the toolchain reads, and
three separate readers assume its shape: `make_cascade.load_export` (which
*refuses* a build item carrying a transform), `verify._meshes`, and
`mesh.strip_objects`. So the rebuild writes that shape rather than build123d's
own `Mesher` output:

    [Content_Types].xml, _rels/.rels, 3D/3dmodel.model
    unit="meter"                      -- so every coordinate is mm / 1000
    <object id="N" name="Pusher" ...> -- id FIRST; parse_meshes' regex requires it
    <build><item objectid="N" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build>

Meshing is the last step and the only lossy one. `TOLERANCE` / `ANGULAR` are set
to put roughly Onshape's triangle count on a pusher (10286 against 9984), so the
sampling checks in `verify.py` — which probe sections on an 80x80 lattice — see
the same density they were tuned on. NB `TOLERANCE` is a RELATIVE deflection —
a fraction of each edge's own size, which is how build123d's `Shape.mesh`
calls OCCT — and not 0.01 mm of chord as its comment once said. The same box
at an absolute 0.01 would carry 74 000 triangles against these 59 000.

Vertices are welded on a 1e-6 mm key, which OCCT's per-face tessellation does
not do for itself; it halves the file for free and leaves no degenerate
triangles (checked on every pusher). Where two faces meet TANGENTIALLY the weld
can also fuse their two triangulations into a back-to-back pair, which is what
`_drop_flaps` is for — see it.

The archive is written with a fixed timestamp so that rebuilding unchanged
source gives a byte-identical file, and `build.py` can tell a real change from a
re-run.
"""
import re
import sys
import zipfile

TOLERANCE = 0.01        # RELATIVE deflection, see above
# OCCT meshes a shape's faces on its own thread pool. Inside cad.build's
# process pool that is one shape's threads per worker on every core at once,
# and the load average reached 118 on a 10-core laptop; `build.run_jobs`
# turns it off in each worker (`serial_meshing`), where the workers are the
# parallelism. Measured on a quiet 14-core machine: the catalogue in 97 s
# against 113 with it on, and only with a worker per core — at 8 workers the
# serial run took 111. A part built on its own keeps it.
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

    Where two faces are tangent, the weld can fuse their triangulations: OCCT
    meshes each face separately, and near the tangency the two land within the
    1e-6 key, so the same three vertices come out twice — once from each face,
    and necessarily wound OPPOSITE ways, since the two faces look at that patch
    from opposite sides. The pair is a zero-thickness flap. It encloses nothing,
    so dropping BOTH members leaves the solid and its volume untouched (checked:
    identical to 1e-11), and leaves the surface closed.

    It is worth doing because a flap is exactly what a slicer calls
    non-manifold: two triangles sharing an edge in the same direction. The
    Holder is where it showed up — the finger scallop's modelled fillet is
    tangent to the rear face, and on the two shallowest FCM holders the slant
    passes through that tangent point as well, which is enough to trip it: 32
    and 40 flaps there, and none on the other 54.

    Same-winding duplicates are NOT dropped: those would be a real doubled
    surface and a bug worth seeing rather than hiding. None has ever appeared.

    This is NOT a general mesh repair. Scanning all 800 written bodies found
    two other faults, neither of them a flap: twelve logo inlays across four
    Innovation lids with an open boundary each — a stale cached triangulation,
    fixed in `triangulate` — and three sleeved Innovation boxes with six edges
    apiece carrying four triangles, a line contact where a hanging hole's edge
    landed on a divider face, cleared by `box.HOLE_CLEAR`. `write` still
    reports a doubled edge and writes it, and refuses a hole. `faults` is the
    scan and `tests/test_build_meshes.py` runs it over all of build/. Recorded
    in spec/HOLDER.md, "The mesh".
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

    A closed orientable surface traverses every directed edge `(a, b)` exactly
    once and its reverse `(b, a)` exactly once, in the neighbouring triangle.
    `unpaired` counts an edge whose reverse is missing or does not match it —
    an OPEN BOUNDARY, a missing face, which a slicer has to guess its way
    across and can take as far as a failed print. `doubled` counts one walked
    more than once — two faces on the same side of it, which is what two
    pieces of material touching along a LINE look like: not a hole, and a
    slicer's layer polygons survive it, but non-manifold all the same.

    Lifted from `tests/test_holder_corpus.py`, where it ran over holders only
    while the two known faults were in boxes and lids.
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

    Any triangulation the shape already carries is thrown away first. OCCT
    stores a mesh ON the faces, and `BRepMesh_IncrementalMesh` keeps one it
    finds fine enough rather than redoing it — so a face that was meshed once
    before (a bounding box does it, and so does a boolean) and then reused as
    the cap of an extrusion keeps its old vertices while the new side faces
    get fresh ones, and the two do not agree along their shared edges. That
    was the twelve open inlays on the four generated-mark Innovation lids: 24
    unpaired edges apiece on their three largest regions, and only when the
    lid body had been built first. `BRepTools.Clean` makes every face mesh
    together, once, at this tolerance.
    """
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepTools import BRepTools
    from OCP.TopAbs import TopAbs_Orientation
    from OCP.TopLoc import TopLoc_Location
    BRepTools.Clean_s(shape.wrapped)
    # The same call build123d's `Shape.mesh` makes — RELATIVE deflection (the
    # third argument), in parallel — so the mesh is the one every file on disk
    # was written with; OCCT does it in 0.3 to 0.6 s for any part here. The
    # walk below is `Shape.tessellate` with ONE change: the triangles are read
    # by index, `poly.Triangle(i)`, and not by iterating `poly.Triangles()`.
    # That iterator costs 0.18 ms a triangle through OCP — 250 times the
    # indexed read — and was the whole of the meshing time: 6 s of a box's 15
    # and 17 of a Compile lid's 31, all of it in a for-loop header.
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
    """Turn OCCT's per-shape meshing threads off — for a process-pool worker,
    which is one of many."""
    global PARALLEL
    PARALLEL = False


def _mesh_object(i, name, verts, tris):
    """One `<object>` carrying a mesh, its coordinates in metres."""
    body = "".join(
        f'     <vertex x="{x / 1000:.8f}" y="{y / 1000:.8f}" '
        f'z="{z / 1000:.8f}"/>\n' for x, y, z in verts)
    body += "    </vertices>\n    <triangles>\n"
    body += "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                    for a, b, c in tris)
    return (f'  <object id="{i}" name="{name}" type="model">\n'
            f'   <mesh>\n    <vertices>\n{body}'
            f'    </triangles>\n   </mesh>\n  </object>\n')


# Our own metadata namespace, declared the way Bambu Studio declares its
# `BambuStudio:` one in a project's root model. 3MF reserves the unprefixed
# metadata names (Title, Description, Application, ...) and requires anything
# else to carry a declared prefix, so a custom key needs both halves of this.
NS_PREFIX = "CardCascade"
NS_URI = "urn:cardcascade:3mf:2026"
# The metadata names this writes and `verify.version_metadata` reads back.
VERSION_KEY = f"{NS_PREFIX}:Version"


def _xesc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _model(objects, build, metadata=None):
    """A 3dmodel.model document round `objects` and `build`, both XML.

    `metadata` is {name: value}, written as `<metadata>` children of `<model>`,
    which is where the spec puts them and BEFORE `<resources>`, which is the
    order it requires. Every reader in this repo takes its meshes by regex and
    ignores them (`mesh3mf.read`, `verify._meshes`), so this is additive.
    """
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
    """The 3dmodel.model for [(name, verts_mm, tris)], one object per part,
    each a build item at the identity."""
    objects = "".join(_mesh_object(i, name, verts, tris)
                      for i, (name, verts, tris) in enumerate(parts, start=1))
    items = "".join(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
                    for i in range(1, len(parts) + 1))
    return _model(objects, items, metadata)


def _write_zip(path, xml):
    """The three-member archive every 3MF here is, with a fixed timestamp."""
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

    Every body is checked with `faults` first. An open boundary raises
    `MeshFault` and nothing is written — a file with a hole in it is not a
    component, and the one place it would be found otherwise is a slicer.
    A doubled edge (a line contact) is reported on stderr and written, since
    it prints; `tests/test_build_meshes.py` lists both over all of `build/`.
    `strict=False` writes regardless, for looking at a broken body.

    `metadata` is {name: value} written into the model element — what
    `cad.build` uses to state the RELEASE in the file itself, so the engraved
    stamp has a second, independent witness (`verify.version_metadata`).
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
    `<object>` in a 3MF's model, and the file's unit scale — the one parser
    under `read` and `read_assembly`."""
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
    """[(name, verts in mm, tris)] from a component 3MF — the inverse of
    `write`, and the same shape `verify._meshes` reads. Used by `cad/render.py`
    and by the regression test, so nothing has to re-derive the unit scale."""
    objects, _scale = _objects(path)
    return [(name, verts, tris) for name, verts, tris, _comps in objects.values()
            if verts and tris]


# --- assemblies -----------------------------------------------------------
#
# An assembly is written the way Onshape's own `individual/<Game>/_raw/
# Assembly *.3mf` are: the component meshes as plain objects, then ONE object
# carrying a `<components>` list that instances them with a transform each, and
# a build item pointing at that. Eight holders therefore cost one mesh.
#
# The transform is 3MF's twelve numbers, `m00 m01 m02 m10 m11 m12 m20 m21 m22
# tx ty tz`, applied as a ROW vector: `v' = v * M + t`. So the matrix's rows are
# the images of the part's own axes, and the translation is in the file's unit —
# metres here, like every other coordinate, which is why it is the only part of
# the transform that gets scaled.
#
# NB this shape is NOT a component 3MF and must never be written into
# `individual/`: `make_cascade.load_export` refuses a build item that carries a
# transform, which is exactly what these are made of.


def assembly_xml(parts, instances, name="Assembly"):
    """`parts` is [(name, verts_mm, tris)]; `instances` is
    [(part_index, placement)], placement having `.as_3mf()`."""
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
    shape is meshed, a `(verts, tris)` pair is taken as it is, which is how a
    cached component from `individual/` gets in. Returns the meshed parts."""
    meshed = []
    for part_name, shape in parts:
        if isinstance(shape, tuple):
            meshed.append((part_name, *shape))
        else:
            meshed.append((part_name, *triangulate(shape, tolerance, angular)))
    _write_zip(path, assembly_xml(meshed, instances, name))
    return meshed


def read_assembly(path):
    """[(name, verts in mm, tris)] with every instance PLACED — the shape the
    renderer wants. A file with no `<components>` reads as its own objects, so
    this works on a component 3MF too."""
    meshes, scale = _objects(path)

    # A mesh that something instances is emitted through its instances, never
    # also on its own: otherwise every component would render twice, once at
    # its part-studio origin.
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
