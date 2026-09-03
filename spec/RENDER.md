# Two renderers, and why they are two

`cad/render.py` is the **diagnostic** renderer and `render/cascade.py` is the
**photoreal** one. They are not a before and an after; they have opposite jobs
and the second does not replace the first.

The diagnostic renderer wants flat distinct colours, no shadows and no
translucency, because that is what lets you see a pusher's tab sitting in the
box's rim cutout or a holder's slot over its rib. Photoreal lighting hides
exactly the interfaces `cad/fit.py` is about: soft shadow in a 0.200 mm gap
reads the same as contact. So the fit work keeps a renderer that is deliberately
not trying to look real.

The photoreal one is for imagery — listings, and looking at a cascade that has
not been printed. There are 55 photographs in `cascades/*/Pictures` and
`Photos`, and a photograph beats a render every time for something that exists;
a render earns its keep on the ~45 catalogued cascades that have not been built.

## The pipeline

    .venv/bin/python -m cad.assemble --model S5.15.15.45-Un --state play
    .venv/bin/python -m cad.gltf "build/assemblies/Innovation/S5.15.15.45-Un play.3mf" \
        --filaments '#F4F4F2,#1B1B1B' --part 'Lid=#0E6BA8' --part 'Lid Part=#F4F4F2' \
        -o tmp/cascade.glb
    blender -b -P render/cascade.py -- tmp/cascade.glb --view hero --samples 256

Three steps and two interpreters, which is not an accident: **Blender ships its
own Python with no build123d in it**, so `render/cascade.py` cannot import
`cad`. The handoff has to be a file, and that turns out to be a feature —
`cad/gltf.py` is testable with no Blender installed, and the `.glb` opens in
Preview, Xcode, three.js and every DCC tool, so a cascade can be looked at
without any of this.

## Why Cycles

It is the only free, scriptable, genuinely path-traced renderer with a
first-class Apple Silicon GPU backend — Metal, since Blender 3.1. LuxCore,
Mitsuba, appleseed and PBRT have no Metal path and would be CPU-only on an M1:
slower AND harder to drive. KeyShot is excellent and native but commercial and
not scriptable as a reproducible repo step. SceneKit, RealityKit and
three.js/WebGPU are realtime rasterisers — right for an interactive spin on a
listing page, wrong for a still.

**The Blender app, not the `bpy` pip module.** Same Cycles, but the app gives
Metal on the well-trodden path, a `blender -b -P` CLI like our other tools,
and — the one that matters for imagery — you can open the scene and move a
light by hand. Written against Blender 5.x and tested on `bpy` 5.0.1; every
call that moved between 4.x and 5.x is guarded rather than pinned.

## glTF, and why not STL

It is the one interchange format that carries **per-object names** and
**materials** as well as geometry, so the Blender side is about light and
nothing else. Positions are written in metres (the meshes are mm, so scaled by
1/1000), which is the same convention `mesh3mf` already writes into a 3MF's
`unit="meter"` — and it matters, because a cascade at real-world scale is what
makes a light's falloff and a depth of field behave.

**Normals are deliberately absent.** The meshes are welded on a 1e-6 key by
`mesh3mf.triangulate`, so Blender computes normals from the topology and
smooths by angle: a flat face stays flat and a fillet goes smooth, which is
right for a printed part. Shipping flat per-face normals instead would need the
topology split, and then nothing could smooth the fillets at all.

## Colour: a slot is not a plate

Which colour a part is takes THREE facts, and the first version of this got two
of them wrong.

**1. Bodies are the first filament, inlays the second.** `Lid 270S` is
object-extruder 2 with a `Lid Body` sub-part explicitly on 1, so its 30 logo
regions inherit 2; a labelled `Topper` is the same shape, body on 1 and its
lettering inheriting 2; Box, Holders, Pushers and the blank Topper are single
parts on 1. **Reading the object-level extruder alone gets the Lid exactly
backwards.** `cad.gltf --check-project` holds the rule to the project's own map
and reports; it agrees on all 35 sub-parts.

**2. An inlay has to say which body it belongs to.** `cad/` writes a Lid's logo
regions and a Topper's lettering both as bare `Part 2`, `Part 3`, ..., which is
what the STEPs and `individual/` carry and is not changed there. But an
assembly holds a Lid's inlays and six Toppers' together, and on a real print
the lid's logo is a contrast on a BLUE lid while a topper's lettering is a
contrast on a WHITE topper. So `assemble._all` qualifies them — `Lid Part 7`,
`Topper Cities Part 7` — and `--part` can address the two sets separately.

**3. A slot is not the whole story.** In Allan's photographs the lid is blue and
the holders are white, and both are slot 1 — because they print on DIFFERENT
PLATES and the filament is whatever is loaded when that plate runs. A slot
distinction only exists WITHIN one plate, which is what makes the lid's logo
two-colour. `--part NAME=#HEX` is the plate-level override, and it is what a
render of the real thing needs.

The project's own colours are `#FFFFFF` and `#000000` — accurate, and a
white-on-white cascade. So the slot assignment comes from the geometry and the
colours from the command line.

## What makes it read as a print rather than as CAD

In the order each one buys something:

1. **Soft shadows and contact occlusion.** The biggest cue by a distance:
   nothing in a flat render says two parts touch.
2. **Layer lines.** `LAYER_HEIGHT` 0.200 mm — the shipped projects' own
   `layer_height`, not the 0.100 in `bambu_project_settings.config`, which is a
   template — as a sine in WORLD Z driving a bump. World and not object space
   on purpose: immune to however the glTF import orients a mesh.
3. **Satin, slightly translucent plastic.** PLA is neither gloss nor chalk and
   passes a little light at a thin edge: a Principled BSDF with some
   subsurface, not a flat diffuse.
4. **A studio.** A softbox key, a fill, a rim and a floor, every distance and
   power a multiple of the scene's own radius so an XS cascade and an L one
   need the same exposure. `KEY` was CALIBRATED by rendering, not derived — at
   900 the frame came out pure white.

## Known gaps

* **Layer lines run the wrong way on holders and toppers.** They print on a
  plate turned 45 degrees (`PIPELINE.md`) while the box and the lid print
  upright, so a per-part print orientation would be needed to get them right.
  At 0.200 mm the direction is invisible at listing resolution, and fixing it
  means the renderer needs the plate layout rather than just the assembly.
* **No cards.** The single biggest remaining realism lever: a cascade without
  cards looks like a CAD model however well lit, and Allan's photographs read
  as real largely BECAUSE of the card art. Card-shaped blocks with a
  stack-of-edges texture would be an honest stand-in; real card faces are a
  rights question, not a technical one.
* **No HDRI.** The studio is three area lights. An environment map would give
  better falloff and a little reflected colour, at the cost of a downloaded
  asset.
