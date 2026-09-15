#!/usr/bin/env python3
"""A cascade, path-traced in Cycles. Runs inside Blender, not in the venv.

    blender -b -P render/cascade.py -- tmp/cascade.glb --view hero
    blender -b -P render/cascade.py -- tmp/cascade.glb --view all --samples 512
    blender -P render/cascade.py -- tmp/cascade.glb --no-render  # tweak by hand

`--blend tmp/cascade.blend` saves the scene. A later run REBUILDS the lights
and materials, so tweaks live in the saved file, not in the script.

`cad/gltf.py` writes the `.glb` this reads; `cad/render.py` stays the
DIAGNOSTIC renderer. `spec/RENDER.md` is the record, including why Cycles and
the layer lines' known gap. This file CANNOT import `cad`: Blender ships its
own interpreter with no build123d in it, which is why the handoff is a file.

Written against **Blender 5.x**; every call that moved between 4.x and 5.x is
guarded rather than pinned (the glTF importer's name, the smooth-by-angle
operator, the Principled BSDF's socket names), so it should run on 4.5 LTS.
"""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

LAYER_HEIGHT = 0.0002       # 0.200 mm, in metres — the projects' layer_height
LAYER_BUMP = 0.15           # how much of a layer height the bump stands
# The key's power per square metre of the inverse-square falloff, so
# `energy = KEY * distance**2` holds the exposure across cascade sizes.
KEY = 55.0
FILL = 0.30                 # of the key
RIM = 0.55                  # of the key
AMBIENT = 0.30              # world background strength

ROUGHNESS = 0.38            # satin: not gloss, not chalk
SUBSURFACE = 0.06           # PLA passes a little light at a thin edge
SUBSURFACE_RADIUS = (0.0012, 0.0009, 0.0007)

# The same cameras `cad/render.py` names, in the same (azimuth, elevation)
# convention. The hero is at 36 and not 24 degrees because the TOPPER LABELS
# lie on the holders' slant and 24 foreshortens them away.
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
    """An empty scene, the glTF importer put back: read_factory_settings
    drops add-ons and the importer IS one (`io_scene_gltf2`)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    for module in ("io_scene_gltf2",):
        addon_utils.enable(module, default_set=False, persistent=True)


def import_glb(path):
    """Import the glTF, whichever name this Blender gives the operator.
    DISCOVERED rather than guarded with getattr, because `bpy.ops` resolves
    any attribute lazily — every candidate looks present and only fails when
    called."""
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
    """Normals from the topology, smoothed by angle: why `cad/gltf.py` ships
    none."""
    try:
        for o in objects:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(degrees))
        bpy.ops.object.select_all(action="DESELECT")
    except (AttributeError, RuntimeError, TypeError):
        # Restricted context (a `blender -P` startup script) or an older API.
        # Per-polygon flags need no operator; what is lost is the angle SPLIT.
        for o in objects:
            for poly in o.data.polygons:
                poly.use_smooth = True


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
    """Rebuild one imported glTF material as printed filament, keeping the
    glTF's base colour so the filament choice stays `cad/gltf.py`."""
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

    # Layer lines: a sine in WORLD Z, so the import cannot rotate them.
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
    """A softbox key, a fill, a rim and a floor, every distance and power a
    multiple of the scene's radius: no retuning per cascade size."""
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-4)

    world = bpy.data.worlds.new("studio")
    bpy.context.scene.world = world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.62, 0.64, 0.68, 1.0)
    bg.inputs["Strength"].default_value = AMBIENT

    if floor:
        # Built from data, not `bpy.ops.mesh.primitive_plane_add`: a script
        # run by `blender -P` WITHOUT `-b` is in a restricted context where
        # `bpy.context.active_object` does not exist, so the operator succeeds
        # and reading back the object it made raises.
        s = radius * 12
        mesh = bpy.data.meshes.new("floor")
        mesh.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)],
                         [], [(0, 1, 2, 3)])
        mesh.update()
        mat = bpy.data.materials.new("floor")
        b = mat.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.55, 0.55, 0.56, 1.0)
        b.inputs["Roughness"].default_value = 0.65
        mesh.materials.append(mat)
        obj = bpy.data.objects.new("floor", mesh)
        obj.location = (centre.x, centre.y, lo.z)
        bpy.context.scene.collection.objects.link(obj)

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
    """The named view, framed on the scene. The six axis views are
    ORTHOGRAPHIC, as `cad/render.py`'s are; the hero is perspective."""
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
        # `ortho_scale` spans the LARGER render dimension, not both — on a
        # 4:3 frame the width — so fitting a TALL subject to it crops the top
        # and bottom off, as a `play` cascade with its holders risen showed.
        scene = bpy.context.scene
        rx, ry = scene.render.resolution_x, scene.render.resolution_y
        cam.ortho_scale = (max(w, h * rx / ry) if rx >= ry
                           else max(h, w * ry / rx)) * margin
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


def settings(samples, width, transparent):
    """Sampling, resolution and film, applied during SETUP and not at render:
    `--no-render` skips render(), and a `.blend` saved for the GUI would
    otherwise carry Blender's default 4096 samples."""
    scene = bpy.context.scene
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = width
    scene.render.resolution_y = int(width * 0.75)
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent
    scene.render.image_settings.file_format = "PNG"


def render(out, view):
    bpy.context.scene.render.filepath = str(out / f"{view}.png")
    bpy.ops.render.render(write_still=True)
    return Path(bpy.context.scene.render.filepath)


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
    ap.add_argument("--blend", type=Path,
                    help="save the scene here as well, to open in the GUI")
    ap.add_argument("--no-render", dest="render", action="store_false",
                    help="build the scene and stop. With `blender -P` (no -b) "
                         "that leaves the GUI open on it")
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
    settings(args.samples, args.width, args.transparent)
    used = device(args.device)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"  {len(objects)} objects, "
          f"{sum(len(o.data.polygons) for o in objects):,} faces, "
          f"Cycles on {used}, {args.samples} samples")
    aim = (tuple(float(n) for n in args.aim.split(",")) if args.aim else None)
    views = tuple(VIEWS) if args.view == "all" else (args.view,)
    for view in views:
        camera(view, lo, hi, aim=aim)
        if args.render:
            print(f"  {render(args.out, view)}")
    # Saved last, so the file carries the settings and the LAST camera.
    if args.blend:
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        print(f"  {args.blend}")
    if not args.render:
        print(f"  scene built, {len(views)} camera(s), nothing rendered")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
