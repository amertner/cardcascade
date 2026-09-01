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
triangles (checked on every pusher).

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
    return out_v, out_t


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
