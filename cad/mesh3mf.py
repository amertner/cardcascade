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
the same density they were tuned on.

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
import zipfile

TOLERANCE = 0.01        # mm, chordal
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

    This is NOT a general mesh repair, and the written catalogue is not yet
    clean. Scanning all 800 written bodies finds two other faults, neither of
    them a flap and neither of them addressed here: three Innovation boxes have
    six edges apiece with four triangles on them (a line contact, not a hole),
    and twelve logo inlays across four Innovation lids each carry 24 UNPAIRED
    edges — an open boundary, i.e. a missing face. Onshape's own meshes have
    none of the three. Recorded in spec/HOLDER.md, "The mesh".
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


def triangulate(shape, tolerance=TOLERANCE, angular=ANGULAR):
    """(vertices in mm, triangles) for a build123d shape, vertices welded."""
    verts, tris = shape.tessellate(tolerance, angular)
    index, out_v, remap = {}, [], []
    for v in verts:
        key = (round(v.X, 6), round(v.Y, 6), round(v.Z, 6))
        if key not in index:
            index[key] = len(out_v)
            out_v.append(key)
        remap.append(index[key])
    out_t = []
    for a, b, c in tris:
        t = (remap[a], remap[b], remap[c])
        if len(set(t)) == 3:            # welding can collapse a sliver
            out_t.append(t)
    return out_v, _drop_flaps(out_t)


def model_xml(parts):
    """The 3dmodel.model for [(name, verts_mm, tris)], one object per part."""
    objects, items = [], []
    for i, (name, verts, tris) in enumerate(parts, start=1):
        body = "".join(
            f'     <vertex x="{x / 1000:.8f}" y="{y / 1000:.8f}" '
            f'z="{z / 1000:.8f}"/>\n' for x, y, z in verts)
        body += "    </vertices>\n    <triangles>\n"
        body += "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                        for a, b, c in tris)
        objects.append(f'  <object id="{i}" name="{name}" type="model">\n'
                       f'   <mesh>\n    <vertices>\n{body}'
                       f'    </triangles>\n   </mesh>\n  </object>\n')
        items.append(f'<item objectid="{i}" '
                     f'transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="meter" xml:lang="en-US" xmlns="http://schemas.'
            'microsoft.com/3dmanufacturing/core/2015/02">\n'
            ' <resources>\n' + "".join(objects) + ' </resources>\n'
            ' <build>' + "".join(items) + '</build>\n</model>\n')


def write(path, parts, tolerance=TOLERANCE, angular=ANGULAR):
    """Write [(name, shape)] to `path` as a component 3MF. Returns its bytes."""
    meshed = [(name, *triangulate(shape, tolerance, angular))
              for name, shape in parts]
    xml = model_xml(meshed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in (("[Content_Types].xml", CONTENT_TYPES),
                           ("_rels/.rels", RELS),
                           ("3D/3dmodel.model", xml)):
            info = zipfile.ZipInfo(name, _EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)
    return meshed


def read(path):
    """[(name, verts in mm, tris)] from a component 3MF — the inverse of
    `write`, and the same shape `verify._meshes` reads. Used by `cad/render.py`
    and by the regression test, so nothing has to re-derive the unit scale."""
    with zipfile.ZipFile(path) as z:
        text = z.read("3D/3dmodel.model").decode()
    scale = {"meter": 1000.0, "millimeter": 1.0}[
        re.search(r'unit="(\w+)"', text).group(1)]
    out = []
    for om in re.finditer(r'<object id="\d+"([^>]*)>(.*?)</object>', text, re.S):
        attrs, body = om.groups()
        name = re.search(r'name="([^"]*)"', attrs)
        verts = [(float(a) * scale, float(b) * scale, float(c) * scale)
                 for a, b, c in re.findall(
                     r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body)]
        tris = [(int(a), int(b), int(c)) for a, b, c in re.findall(
            r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body)]
        if verts and tris:
            out.append((name.group(1) if name else None, verts, tris))
    return out


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
    objects = []
    for i, (part_name, verts, tris) in enumerate(parts, start=1):
        body = "".join(
            f'     <vertex x="{x / 1000:.8f}" y="{y / 1000:.8f}" '
            f'z="{z / 1000:.8f}"/>\n' for x, y, z in verts)
        body += "    </vertices>\n    <triangles>\n"
        body += "".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                        for a, b, c in tris)
        objects.append(f'  <object id="{i}" name="{part_name}" type="model">\n'
                       f'   <mesh>\n    <vertices>\n{body}'
                       f'    </triangles>\n   </mesh>\n  </object>\n')
    top = len(parts) + 1
    comps = "".join(
        f'    <component objectid="{k + 1}" transform="{pl.as_3mf()}"/>\n'
        for k, pl in instances)
    objects.append(f'  <object id="{top}" name="{name}" type="model">\n'
                   f'   <components>\n{comps}   </components>\n  </object>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<model unit="meter" xml:lang="en-US" xmlns="http://schemas.'
            'microsoft.com/3dmanufacturing/core/2015/02">\n'
            ' <resources>\n' + "".join(objects) + ' </resources>\n'
            f' <build><item objectid="{top}" '
            'transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build>\n</model>\n')


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for fn, text in (("[Content_Types].xml", CONTENT_TYPES),
                         ("_rels/.rels", RELS),
                         ("3D/3dmodel.model",
                          assembly_xml(meshed, instances, name))):
            info = zipfile.ZipInfo(fn, _EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text)
    return meshed


def read_assembly(path):
    """[(name, verts in mm, tris)] with every instance PLACED — the shape the
    renderer wants. A file with no `<components>` reads as its own objects, so
    this works on a component 3MF too."""
    with zipfile.ZipFile(path) as z:
        text = z.read("3D/3dmodel.model").decode()
    scale = {"meter": 1000.0, "millimeter": 1.0}[
        re.search(r'unit="(\w+)"', text).group(1)]
    meshes = {}
    for om in re.finditer(r'<object id="(\d+)"([^>]*)>(.*?)</object>',
                          text, re.S):
        oid, attrs, body = om.groups()
        nm = re.search(r'name="([^"]*)"', attrs)
        verts = [(float(a) * scale, float(b) * scale, float(c) * scale)
                 for a, b, c in re.findall(
                     r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', body)]
        tris = [(int(a), int(b), int(c)) for a, b, c in re.findall(
            r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', body)]
        comps = [(int(c), [float(n) for n in t.split()]) for c, t in
                 re.findall(r'<component objectid="(\d+)" transform="([^"]+)"',
                            body)]
        meshes[int(oid)] = (nm.group(1) if nm else None, verts, tris, comps)

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
