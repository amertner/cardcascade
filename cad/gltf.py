#!/usr/bin/env python3
"""An assembly as a binary glTF, for a renderer that can light it properly.

    .venv/bin/python -m cad.gltf "build/assemblies/Innovation/S5.15.15.45-Un play.3mf"
    .venv/bin/python -m cad.gltf <assembly.3mf> --project <cascade.3mf> \
        --filaments '#1B6CA8,#FFFFFF'

`cad/render.py` is the DIAGNOSTIC renderer and stays that way: flat colours, no
shadows, one part one hue, because that is what lets you see a pusher's tab
sitting in the box's rim cutout. Photoreal lighting would hide exactly the
interfaces the fit test is about. So imagery goes out to a path tracer instead,
and this is the handoff — see `spec/RENDER.md`.

glTF rather than STL or OBJ because it is the one interchange format that
carries **per-object names** and **materials** as well as geometry, so the
Blender side can be about light and nothing else. It is also read by Preview,
Xcode, three.js and every DCC tool, so a cascade can be looked at without any
of this pipeline.

## Which colour a part is

NOT from the part's kind, and the rule is one line: **every part BODY is the
first filament and every INLAY is the second.** An assembly names an inlay after
its body — `Lid Part 7`, `Topper Cities Part 7` — so the inlays are exactly the
objects whose name CONTAINS `Part `, and the two sets can be told apart, which
they have to be: a lid's logo is a contrast on a blue lid and a topper's
lettering is a contrast on a white one.

The project confirms it rather than being needed for it. `Lid 270S` is
object-extruder 2 with a `Lid Body` sub-part explicitly on 1, so its 30 logo
regions inherit 2; each labelled `Topper` is the same shape, body on 1 and its
lettering inheriting 2; and Box, Holders, Pushers and the blank Topper are
single parts on 1. Reading the object-level extruder alone gets the Lid exactly
backwards, which is what a first version of this file did.

Allan: "I sometimes change the filament for the lid and labels, so make that an
option. I tend to make the boxes white, though the shade might differ." That is
this split, and it is why `--filaments` takes BOTH colours: the bodies are a
white whose shade varies, and the inlays are whatever is loaded for them.

## Units

glTF is metres by convention and our meshes are mm, so positions are written
scaled by 1/1000 — the same convention `mesh3mf` already writes into a 3MF's
`unit="meter"`. A cascade therefore imports at real-world scale, which is what
makes a depth of field and a light's falloff behave.

## Normals are deliberately absent

The meshes are welded (`mesh3mf.triangulate` welds on a 1e-6 key), so Blender
can compute normals from the topology and smooth by angle: a flat face stays
flat and a fillet goes smooth, which is exactly right for a printed part.
Supplying flat per-face normals instead would need the topology split, and then
nothing could smooth the fillets at all.
"""
import argparse
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

from . import mesh3mf

ROOT = Path(__file__).resolve().parent.parent

# An INLAY is any object an assembly names after a body: `Lid Part 2`,
# `Topper Cities Part 3`, ... — the Lid's logo regions and a Topper's
# lettering. They are the second filament; every body is the first. See the
# module docstring for the project evidence.
INLAY = "Part "
DEFAULT_FILAMENTS = ("#FFFFFF", "#000000")

# A printed part is satin, not gloss and not chalk. Measured off nothing —
# these are the two numbers a Principled BSDF needs to stop looking like clay,
# and the Blender side is where they are tuned.
ROUGHNESS = 0.38
METALLIC = 0.0


def project_slots(path):
    """{sub-part name: effective extruder} from a cascade project.

    Parsed sub-part by sub-part, because the object-level extruder is not the
    answer: `Lid 270S` carries 2 and its `Lid Body` overrides to 1. A sub-part
    without an extruder of its own inherits the object's, which is how the 30
    logo regions end up on 2. Only used to CHECK the built-in rule
    (`--check-project`); nothing needs it to render.
    """
    with zipfile.ZipFile(path) as z:
        text = z.read("Metadata/model_settings.config").decode()

    def kv(s):
        return dict(re.findall(r'key="(\w+)" value="([^"]*)"', s))

    out = {}
    for m in re.finditer(r'<object id="\d+">(.*?)</object>', text, re.S):
        body = m.group(1)
        obj = kv(body.split("<part", 1)[0])
        for pb in re.findall(r'<part id="\d+"[^>]*>(.*?)</part>', body, re.S):
            part = kv(pb)
            name = part.get("name")
            slot = part.get("extruder") or obj.get("extruder") or "1"
            if name:
                out[name] = int(slot)
    return out


def project_filaments(path):
    """The two colours the project itself carries, as `#RRGGBB`."""
    with zipfile.ZipFile(path) as z:
        ps = json.loads(z.read("Metadata/project_settings.config"))
    return tuple(ps.get("filament_colour") or DEFAULT_FILAMENTS)


def slot_for(name):
    """Which filament slot a component is printed in."""
    return 2 if INLAY in (name or "") else 1


def _hex(colour):
    c = colour.lstrip("#")
    return [int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4)] + [1.0]


def colour_of(name, filaments, parts):
    """The colour a component is rendered in.

    A `--part` override wins, matched on the longest component-name prefix, so
    `Box` catches the box and `Holder` catches both the standard and the first
    one. Otherwise the filament in the slot the body/inlay rule gives.
    """
    for key in sorted(parts or {}, key=len, reverse=True):
        if (name or "").startswith(key):
            return parts[key]
    slot = slot_for(name)
    return filaments[slot - 1] if slot - 1 < len(filaments) else filaments[0]


def build(objects, filaments, parts=None):
    """(json dict, binary blob) for [(name, verts_mm, tris)]."""
    blob = bytearray()
    buffer_views, accessors, meshes, nodes = [], [], [], []
    palette = {}          # colour -> material index, so one material a colour

    def view(data, target):
        while len(blob) % 4:
            blob.append(0)
        buffer_views.append({"buffer": 0, "byteOffset": len(blob),
                             "byteLength": len(data), "target": target})
        blob.extend(data)
        return len(buffer_views) - 1

    for name, verts, tris in objects:
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        pos = struct.pack(f"<{len(verts) * 3}f",
                          *[c / 1000.0 for v in verts for c in v])
        idx = struct.pack(f"<{len(tris) * 3}I", *[i for t in tris for i in t])
        accessors.append({"bufferView": view(pos, 34962), "componentType": 5126,
                          "count": len(verts), "type": "VEC3",
                          "min": [min(xs) / 1000, min(ys) / 1000, min(zs) / 1000],
                          "max": [max(xs) / 1000, max(ys) / 1000, max(zs) / 1000]})
        accessors.append({"bufferView": view(idx, 34963), "componentType": 5125,
                          "count": len(tris) * 3, "type": "SCALAR"})
        meshes.append({"name": name or "part", "primitives": [{
            "attributes": {"POSITION": len(accessors) - 2},
            "indices": len(accessors) - 1,
            "material": palette.setdefault(
                colour_of(name, filaments, parts), len(palette))}]})
        nodes.append({"name": name or "part", "mesh": len(meshes) - 1})

    materials = [None] * len(palette)
    for colour, i in palette.items():
        materials[i] = {"name": f"Filament {colour}",
                        "pbrMetallicRoughness": {
                            "baseColorFactor": _hex(colour),
                            "metallicFactor": METALLIC,
                            "roughnessFactor": ROUGHNESS}}
    # +Z up is our convention and glTF's is +Y up, so the whole scene is turned
    # -90 degrees about X in the root node rather than in every mesh. Blender is
    # +Z up too and its importer undoes this, so a cascade lands upright there.
    root = {"name": "Cascade", "children": list(range(len(nodes))),
            "rotation": [-0.7071067811865476, 0.0, 0.0, 0.7071067811865476]}
    nodes.append(root)
    return {
        "asset": {"version": "2.0", "generator": "cad.gltf"},
        "scene": 0,
        "scenes": [{"nodes": [len(nodes) - 1]}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(blob)}],
    }, bytes(blob)


def write(path, objects, filaments=DEFAULT_FILAMENTS, parts=None):
    """Write a binary glTF. Returns its size in bytes."""
    doc, blob = build(objects, filaments, parts)
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    bl = blob + b"\0" * (-len(blob) % 4)
    total = 12 + 8 + len(js) + 8 + len(bl)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(bl), 0x004E4942))
        f.write(bl)
    return total


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("assembly", type=Path)
    ap.add_argument("-o", "--out", type=Path,
                    help="default: the assembly's name with a .glb suffix")
    ap.add_argument("--project", type=Path,
                    help="a cascade project: its own two filament colours "
                         "become the defaults")
    ap.add_argument("--part", action="append", metavar="NAME=#HEX", default=[],
                    help="override one component kind's colour, e.g. "
                         "Box=#1B6CA8. Repeatable; a plate-level filament "
                         "change is not a slot")
    ap.add_argument("--check-project", action="store_true",
                    help="hold the built-in body/inlay rule to the project's "
                         "own per-sub-part extruder map, and report")
    ap.add_argument("--filaments",
                    help="the two slot colours, e.g. '#1B6CA8,#FFFFFF'. "
                         "Defaults to the project's, or white and black")
    args = ap.parse_args(argv)

    if args.check_project:
        if not args.project:
            ap.error("--check-project needs --project")
        slots = project_slots(args.project)
        wrong = [(n, s, slot_for(n)) for n, s in slots.items()
                 if s != slot_for("x Part x" if n.startswith("Part") else n)]
        print(f"  project: {len(slots)} sub-parts, "
              f"{sum(1 for s in slots.values() if s == 2)} on slot 2")
        print("  rule agrees with the project" if not wrong
              else f"  DISAGREES on {wrong}")
    if args.filaments:
        filaments = tuple(c.strip() for c in args.filaments.split(","))
    elif args.project:
        filaments = project_filaments(args.project)
    else:
        filaments = DEFAULT_FILAMENTS

    parts = {}
    for spec in args.part:
        if "=" not in spec:
            ap.error(f"--part wants NAME=#HEX, got {spec!r}")
        key, _, colour = spec.partition("=")
        parts[key.strip()] = colour.strip()

    objects = mesh3mf.read_assembly(args.assembly)
    out = args.out or args.assembly.with_suffix(".glb")
    size = write(out, objects, filaments, parts)
    by_colour = {}
    for name, _v, _t in objects:
        by_colour.setdefault(colour_of(name, filaments, parts), []).append(name)
    print(f"  {out}  {size / 1024 / 1024:.1f} MB, {len(objects)} objects, "
          f"{sum(len(t) for _n, _v, t in objects):,} triangles")
    for colour, names in by_colour.items():
        kinds = sorted({n.split()[0] if n else "?" for n in names})
        print(f"    {colour}: {len(names):2d} objects  {', '.join(kinds[:6])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
