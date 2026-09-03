#!/usr/bin/env python3
"""A cascade, path-traced in Cycles. Runs inside Blender, not in the venv.

    blender -b -P render/cascade.py -- tmp/cascade.glb --view hero
    blender -b -P render/cascade.py -- tmp/cascade.glb --view all --samples 512

`cad/gltf.py` writes the `.glb` this reads; `cad/render.py` stays the
DIAGNOSTIC renderer and is not replaced. The two have opposite jobs: flat
colours and no shadows are what let you see a pusher's tab in the box's rim
cutout, and photoreal lighting would hide exactly the interfaces the fit test is
about. `spec/RENDER.md` is the record.

This file cannot import `cad`: Blender ships its own interpreter with no
build123d in it. That is why the handoff is a file and not a function call, and
it is a feature — the exporter is testable without Blender installed.

## Why Cycles

It is the only free, scriptable, genuinely path-traced renderer with a
first-class Apple Silicon GPU backend (Metal, since Blender 3.1). LuxCore,
Mitsuba, appleseed and PBRT have no Metal path and would be CPU-only on an M1.
`--device` picks; the default tries Metal and falls back to CPU, which is how
this gets tested on a machine that has neither.

Written against **Blender 5.x** (tested on `bpy` 5.0.1, the nearest wheel to
Allan's Homebrew 5.2.1). Every call that moved between 4.x and 5.x is guarded
rather than pinned — the glTF importer's name, the smooth-by-angle operator and
the Principled BSDF's socket names — so it should also run on 4.5 LTS.

## What makes it read as a 3D print rather than as CAD

1. **Soft shadows.** Nothing in a flat render says two parts touch.
2. **Layer lines.** `LAYER_HEIGHT` 0.200 mm — the shipped projects' own
   `layer_height` — as a sine in WORLD Z driving a bump. World and not object
   space on purpose: it is immune to however the glTF import orients a mesh,
   and the cascade's Z is the print's Z for the box and the lid. Holders and
   toppers actually print on a plate turned 45 degrees (`PIPELINE.md`), so
   their lines run the wrong way here; at 0.200 mm that is invisible at
   listing resolution and `spec/RENDER.md` records it as the known gap.
3. **Satin, slightly translucent plastic.** PLA is neither gloss nor chalk, and
   it passes a little light at thin edges — a Principled BSDF with some
   subsurface, not a flat diffuse.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

LAYER_HEIGHT = 0.0002       # 0.200 mm, in metres — the projects' layer_height
LAYER_BUMP = 0.15           # how much of a layer height the bump stands
# The key light's power at the distance it is placed, as watts per square
# metre of the inverse-square falloff — so `energy = KEY * distance**2` keeps
# the exposure the same on an XS cascade and an L one. Calibrated by rendering,
# not derived: at 900 the frame was pure white.
KEY = 55.0
FILL = 0.30                 # of the key
RIM = 0.55                  # of the key
AMBIENT = 0.30              # world background strength

ROUGHNESS = 0.38            # satin: not gloss, not chalk
SUBSURFACE = 0.06           # PLA passes a little light at a thin edge
SUBSURFACE_RADIUS = (0.0012, 0.0009, 0.0007)

# The same cameras `cad/render.py` names, in the same (azimuth, elevation)
# convention, so a photoreal frame and a diagnostic one correspond.
#
# The hero is at 36 degrees and not the 24 it started at, because the TOPPER
# LABELS lie on the holders' slant and 24 foreshortens them to nothing. 48
# reads them better still and loses the lid and the whole product-on-a-shelf
# read, so 36 is where both survive. `--aim AZ,EL` overrides it.
VIEWS = {
    "front": (180, 0), "back": (0, 0), "left": (90, 0), "right": (270, 0),
    "top": (0, 90), "bottom": (0, -90), "hero": (206, 36),
}
HERO = "hero"
HERO_LENS = 85.0            # mm — a portrait lens, so the perspective is gentle


def forward(az, el):
    """`cad/render._basis`'s view direction, verbatim."""
    a, e = math.radians(az), math.radians(el)
    v = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e),
                -math.sin(e)))
    v.normalize()
    return v


def reset():
    """An empty scene, with the glTF importer put back.

    `read_factory_settings` drops enabled add-ons, and the glTF importer IS an
    add-on (`io_scene_gltf2`) — so resetting first and importing after fails
    with "could not be found", which is what it did.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    for module in ("io_scene_gltf2",):
        addon_utils.enable(module, default_set=False, persistent=True)


def import_glb(path):
    """Import the glTF, whichever name this Blender gives the operator.

    5.0 still has `import_scene.gltf`; the name is DISCOVERED rather than
    guarded with getattr, because `bpy.ops` resolves any attribute lazily —
    every candidate looks present and only fails when called. `dir()` on the
    operator group is what actually says.
    """
    for group, name in (("import_scene", "gltf"), ("wm", "gltf_import")):
        ops = getattr(bpy.ops, group, None)
        if ops is None or name not in dir(ops):
            continue
        getattr(ops, name)(filepath=str(path))
        break
    else:
        sys.exit("REFUSING: this Blender has no glTF importer I recognise. "
                 "Checked bpy.ops.import_scene.gltf and "
                 "bpy.ops.wm.gltf_import; is io_scene_gltf2 available?")
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def smooth(objects, degrees=30.0):
    """Normals from the topology, smoothed by angle: a flat face stays flat and
    a fillet goes smooth. This is why `cad/gltf.py` ships no normals."""
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(degrees))
    except (AttributeError, RuntimeError):
        bpy.ops.object.shade_smooth()          # older API: no angle split
    bpy.ops.object.select_all(action="DESELECT")


def bounds(objects):
    lo = Vector((1e9,) * 3)
    hi = Vector((-1e9,) * 3)
    for o in objects:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def plastic(material):
    """Rebuild one imported glTF material as printed filament.

    The base colour is taken from what the glTF carried, so the filament
    choice stays `cad/gltf.py --filaments` and is not duplicated here.
    """
    # `use_nodes` is deprecated (gone in Blender 6.0) and node trees are the
    # only kind of material in 5.x, so it is neither read nor set.
    colour = (0.8, 0.8, 0.8, 1.0)
    if material.node_tree:
        for n in material.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                colour = tuple(n.inputs["Base Color"].default_value)
    nt = material.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    # Socket names moved in 4.0 ("Subsurface" became "Subsurface Weight") and
    # may again, so every one is set only if this Blender has it.
    for name, value in (("Base Color", colour),
                        ("Roughness", ROUGHNESS),
                        ("Subsurface Weight", SUBSURFACE),
                        ("Subsurface", SUBSURFACE),
                        ("Metallic", 0.0),
                        ("IOR", 1.46),
                        ("Subsurface Radius", SUBSURFACE_RADIUS)):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value

    # Layer lines: a sine in WORLD Z, bumped. Position rather than Object
    # coordinates so the import's orientation cannot rotate them.
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 2 * math.pi / LAYER_HEIGHT
    sine = nt.nodes.new("ShaderNodeMath")
    sine.operation = "SINE"
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = LAYER_HEIGHT * LAYER_BUMP
    nt.links.new(geo.outputs["Position"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mul.inputs[0])
    nt.links.new(mul.outputs["Value"], sine.inputs[0])
    nt.links.new(sine.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])


def studio(lo, hi, floor=True):
    """A softbox key, a fill, a rim and a floor, all sized to the scene.

    Every distance and power is a multiple of the scene's own radius, so the
    lighting does not have to be retuned for an XS cascade against an L one.
    """
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-4)

    world = bpy.data.worlds.new("studio")
    bpy.context.scene.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1.0)
    bg.inputs["Strength"].default_value = AMBIENT

    if floor:
        bpy.ops.mesh.primitive_plane_add(size=radius * 24,
                                         location=(centre.x, centre.y, lo.z))
        mat = bpy.data.materials.new("floor")
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.55, 0.55, 0.56, 1.0)
        b.inputs["Roughness"].default_value = 0.65
        bpy.context.active_object.data.materials.append(mat)

    for name, offset, size, power in (
            ("key", (-1.5, -1.9, 1.7), 2.6, KEY),
            ("fill", (2.0, -1.4, 0.7), 3.2, KEY * FILL),
            ("rim", (0.4, 2.2, 1.6), 2.0, KEY * RIM)):
        light = bpy.data.lights.new(name, type="AREA")
        light.shape = "RECTANGLE"
        light.size = radius * size
        light.size_y = radius * size * 0.7
        pos = centre + Vector(offset) * radius
        # Power goes as distance squared, so the exposure is scale-free.
        light.energy = power * (pos - centre).length ** 2
        obj = bpy.data.objects.new(name, light)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = pos
        direction = (centre - pos).normalized()
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def camera(view, lo, hi, margin=1.06, aim=None):
    """The named view, framed on the scene.

    The six axis views are ORTHOGRAPHIC, as `cad/render.py`'s are, because a
    straight-on elevation is what they are for. The hero is perspective, at a
    portrait lens so the cascade does not look wide-angled.
    """
    centre = (lo + hi) / 2
    span = hi - lo
    cam = bpy.data.cameras.new(view)
    obj = bpy.data.objects.new(view, cam)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.scene.camera = obj

    fwd = forward(*(aim or VIEWS[view]))
    up = Vector((0, 0, 1))
    if abs(fwd.dot(up)) > 0.85:
        up = Vector((0, 1, 0))
    radius = span.length / 2
    if view == HERO:
        cam.type = "PERSP"
        cam.lens = HERO_LENS
        half = math.atan(cam.sensor_width / 2 / cam.lens)
        distance = radius / math.tan(half) * margin
    else:
        cam.type = "ORTHO"
        right = fwd.cross(up).normalized()
        upv = right.cross(fwd).normalized()
        w = sum(abs(getattr(right, a)) * getattr(span, a) for a in "xyz")
        h = sum(abs(getattr(upv, a)) * getattr(span, a) for a in "xyz")
        cam.ortho_scale = max(w, h) * margin
        distance = radius * 4
    obj.location = centre - fwd * distance
    obj.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    return obj


def device(prefer="metal"):
    """Cycles on the GPU where there is one. Returns what it settled on."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons.get("cycles")
    if prefer == "cpu" or prefs is None:
        scene.cycles.device = "CPU"
        return "CPU"
    cp = prefs.preferences
    for backend in (prefer.upper(), "METAL", "CUDA", "HIP", "ONEAPI"):
        try:
            cp.compute_device_type = backend
        except TypeError:
            continue
        cp.get_devices()
        if any(d.type == backend for d in cp.devices):
            for d in cp.devices:
                d.use = d.type == backend
            scene.cycles.device = "GPU"
            return backend
    scene.cycles.device = "CPU"
    return "CPU"


def render(out, view, samples, width, transparent):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = width
    scene.render.resolution_y = int(width * 0.75)
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out / f"{view}.png")
    bpy.ops.render.render(write_still=True)
    return Path(scene.render.filepath)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("glb", type=Path)
    ap.add_argument("--out", type=Path, default=Path("tmp/photo"))
    ap.add_argument("--view", default=HERO,
                    choices=tuple(VIEWS) + ("all",))
    ap.add_argument("--samples", type=int, default=256)
    ap.add_argument("--width", type=int, default=1800)
    ap.add_argument("--device", default="metal",
                    choices=("metal", "cuda", "hip", "oneapi", "cpu"))
    ap.add_argument("--aim", metavar="AZ,EL",
                    help="override the view's camera, e.g. 206,38. The topper "
                         "labels lie on the holders' slant, so the elevation "
                         "that reads them is not the one that frames the box")
    ap.add_argument("--exposure", type=float, default=0.0,
                    help="stops, on top of the calibrated lighting")
    ap.add_argument("--transparent", action="store_true",
                    help="no floor and an alpha background, for a listing")
    args = ap.parse_args(argv)

    reset()
    objects = import_glb(args.glb)
    if not objects:
        sys.exit("REFUSING: no meshes in the glTF")
    smooth(objects)
    for mat in bpy.data.materials:
        plastic(mat)
    lo, hi = bounds(objects)
    studio(lo, hi, floor=not args.transparent)
    bpy.context.scene.view_settings.exposure = args.exposure
    used = device(args.device)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"  {len(objects)} objects, "
          f"{sum(len(o.data.polygons) for o in objects):,} faces, "
          f"Cycles on {used}, {args.samples} samples")
    aim = (tuple(float(n) for n in args.aim.split(",")) if args.aim else None)
    for view in (tuple(VIEWS) if args.view == "all" else (args.view,)):
        camera(view, lo, hi, aim=aim)
        print(f"  {render(args.out, view, args.samples, args.width, args.transparent)}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
