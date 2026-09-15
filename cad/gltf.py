#!/usr/bin/env python3
"""An assembly as a binary glTF, for a renderer that can light it properly.

    .venv/bin/python -m cad.gltf "build/assemblies/Innovation/S5.15.15.45-Un play.3mf"
    .venv/bin/python -m cad.gltf <assembly.3mf> --project <cascade.3mf> \
        --filaments '#1B6CA8,#FFFFFF'

`cad/render.py` is the DIAGNOSTIC renderer and stays that way — flat colours,
no shadows, one part one hue. Imagery goes out to a path tracer, and this is
the handoff (`spec/RENDER.md`); glTF because it is the one interchange format
carrying per-object NAMES and MATERIALS as well as geometry.

**Which colour a part is**: NOT the part's kind. Every part BODY is the first
filament and every INLAY the second, an inlay being any object whose name
contains `Part `. Reading the object-level extruder alone gets the Lid exactly
BACKWARDS, its body overriding to 1 under an object on 2.

**Units**: glTF is metres by convention and our meshes are mm, so positions
are scaled by 1/1000 and a cascade imports at real-world scale.

**Normals are deliberately absent.** The meshes are welded, so Blender
computes them from the topology and smooths by angle; flat per-face normals
would need the topology split, and nothing could then smooth the fillets.
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

# An INLAY is any object an assembly names after a body — the Lid's logo
# regions, a Topper's lettering. They are the second filament; every body is
# the first.
INLAY = "Part "
DEFAULT_FILAMENTS = ("#FFFFFF", "#000000")

# A printed part is satin, not gloss and not chalk. Measured off nothing; the
# Blender side is where they are tuned.
ROUGHNESS = 0.38
METALLIC = 0.0


def project_slots(path):
    """{sub-part name: effective extruder} from a cascade project. Parsed
    sub-part by sub-part, the object-level extruder NOT being the answer; one
    without an extruder of its own inherits the object's. Only used to CHECK
    the built-in rule (`--check-project`)."""
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
    with zipfile.ZipFile(path) as z:
        ps = json.loads(z.read("Metadata/project_settings.config"))
    return tuple(ps.get("filament_colour") or DEFAULT_FILAMENTS)


def slot_for(name):
    return 2 if INLAY in (name or "") else 1


def _hex(colour):
    """`#RRGGBB` as glTF's `baseColorFactor` — which is LINEAR, not sRGB.
    Handing the bytes over unconverted lifts every DARK colour to a mid grey;
    white survives it, which is why a cascade of white parts never showed the
    fault."""
    c = colour.lstrip("#")
    return [_linear(int(c[i:i + 2], 16) / 255.0) for i in (0, 2, 4)] + [1.0]


def _linear(u):
    # IEC 61966-2-1, verbatim
    return u / 12.92 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4


# The cards `cad.assemble --cards` places are not printed and have no
# filament: a stack is coloured by its EXPANSION and its set number lettered
# in the light one. Any other game's stacks get the neutral;
# `--part 'Cards Cities=#hex'` still overrides.
CARD_COLOURS = {
    "Innovation": "#7D3C98", "Artifacts": "#C0392B", "Cities": "#2E86C1",
    "Echoes": "#27AE60", "Figures": "#E67E22", "Unseen": "#17A589",
}
CARD_NEUTRAL = "#B5A98C"
CARD_LABEL = "#F4F4F2"


def colour_of(name, filaments, parts):
    """The colour a component is rendered in: a `--part` override on the
    longest component-name prefix, else a card stack's expansion colour, else
    the filament in the slot the body/inlay rule gives."""
    for key in sorted(parts or {}, key=len, reverse=True):
        if (name or "").startswith(key):
            return parts[key]
    if (name or "").startswith("Cards Label"):
        return CARD_LABEL
    if (name or "").startswith("Cards "):
        return CARD_COLOURS.get(name.split()[1], CARD_NEUTRAL)
    slot = slot_for(name)
    return filaments[slot - 1] if slot - 1 < len(filaments) else filaments[0]


def build(objects, filaments, parts=None):
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
    # -90 degrees about X in the ROOT node, not in every mesh. Blender is +Z up
    # too and its importer undoes this, so a cascade lands upright there.
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
