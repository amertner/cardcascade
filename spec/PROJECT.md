# The project file, written from scratch

`cad/project.py` writes a Bambu Studio project 3MF from parts, plates and
placements, with no donor. This is the record of what such a file has to
contain, read off the 46 shipped cascade projects under `cascades/` and off
`automation/make_cascade.py`, which has mutated donors into every one of
them since 6.x. Where the two disagree the shipped files win; where a rule
was learned the hard way `make_cascade.py`'s comments say so and the rule is
repeated here with its reason.

The point of writing rather than mutating is recorded in the design review of
2026-09-05 (`automation/PIPELINE.md`, "Interactive refresh", and `CLAUDE.md`):
`make_cascade` cannot create a project, only change one, so a cascade with no
project needed a donor with at least as many instances of every object, which
for FCM Milestones meant a Dominion project. A writer needs a bed profile and
the parts.

## What a project is made of

```
[Content_Types].xml                 rels, model, png, gcode
_rels/.rels                         -> /3D/3dmodel.model (thumbnails optional)
3D/3dmodel.model                    the OBJECTS: one <object> per printed thing,
                                    each a <components> list pointing into a
                                    sub-model file; the <build> places instances
3D/_rels/3dmodel.model.rels         one relationship per sub-model file
3D/Objects/object_<N>.model         the MESHES: one <object><mesh> per part,
                                    vertices in mm, stored bbox-centred
Metadata/model_settings.config      names, extruders, part matrices, plates,
                                    the assemble view
Metadata/project_settings.config    the printer/process/filament settings: the
                                    bed profile, plus wipe_tower_x/y per plate
Metadata/cut_information.xml        one empty entry per object
Metadata/filament_sequence.json     one empty entry per plate
Metadata/slice_info.config          a header naming the client
```

Thumbnails (`Metadata/plate_*.png`) are optional; Studio regenerates them on
save. `make_cascade` deletes them for the same reason.

## `project_settings.config` is the bed profile

A shipped P1P project's settings differ from `automation/profiles/p1p.config`
in exactly three things: `wipe_tower_x` and `wipe_tower_y`, one entry per
plate, and the filament colour order (the profile is black then white; every
cascade is white in slot 1, black in slot 2, with `flush_volumes_matrix`
swapped to match). Every other key of the 568 is the profile's. The A1 mini
and H2C projects differ by a handful of hand edits besides (`curr_bed_type`,
`ironing_type`, `filament_nozzle_map` lengths) that PIPELINE.md records as
stale or cosmetic; the profile is the reference and the writer writes it.

So the writer takes the profile whole, sets the colours through
`filaments.remap` (which turns the flush matrix with them), forces
`PRINT_SETTINGS` (`wall_generator: arachne`, and the key added to the process
entry of `different_settings_to_system`, or Studio shows the stock value while
the project prints its own — `make_cascade.force_print_settings`), and writes
one tower coordinate per plate.

Ten shipped projects are on a **P1S**, for which there is no profile:
Compile 105 and 126, Dominion 300 and 333, FCM Occupations 1. parts.csv's
`3D printer` column says `Standard`, which the refresh tool maps to the P1P
profile — the same 256 x 256 bed, the open-frame variant. A regenerated one
will be a P1P project unless a P1S profile is extracted the way `a1mini` was
(PIPELINE.md, "The Mini bed class"). Allan's call.

## Ids and frames

- Every `<object id>` is unique across the whole package — the top-level
  objects in `3dmodel.model` AND the mesh objects in every sub-model file share
  one id space. Studio resolves a duplicate to a single mesh, silently.
- A printed thing is a top-level object whose `<components>` each reference
  one mesh object in a sub-model file by `objectid`, with a `transform` that
  is the part's offset inside the object.
- Each mesh is stored **centred on its own bounding box**. The object's frame
  is the centre of the union of its parts' boxes, so a component transform
  is `part centre - object centre` and a single-part object's is the
  identity. `source_offset_x/y/z` in `model_settings.config` records the
  part's centre in the frame it came from, which is how a part can be put
  back where the CAD had it.
- The `<build>` `<item>` transform is a row-vector 4x3 (`m00 m01 m02 m10 m11
  m12 m20 m21 m22 tx ty tz`); a rotation about Z is `c s 0 -s c 0 0 0 1`. Its
  `tz` is half the object's height, so the object sits on the bed.
- Plates share **one coordinate space**, a two-column grid at a stride of
  1.2 x the plate dimension: plate 1 at the origin, 2 at `(1.2 W, 0)`, 3 at
  `(0, -1.2 D)`, 4 at `(1.2 W, -1.2 D)`. Which plate an instance is on is
  ALSO written in `model_settings.config` (`<plate><model_instance>`); the two
  must agree. On a P1's 256 mm plate the stride is 307.2; on an H2C's 330 x
  320 it is 396 x 384.
- A rotated instance is rotated about its own bbox centre and then that
  centre is placed; `make_cascade` works the same way.

## Extruders

The rule is `cad/gltf.slot_for`'s: bodies print in slot 1, a mark's inlays
in slot 2, and there is no third. In the file an object carries an
`extruder` and each part may carry its own; a part without one inherits the
object's. The writer sets every object to 1 and every inlay part — a part
named `Part N`, which is what `cad.build` writes a lid's or a topper's
regions as — to 2 explicitly. The shipped lids do it the other way round
(object 2, body part 1), an accident of how Onshape's exports were imported;
both slice the same and `filaments.used_extruders` reads both.

## Naming

- Objects are named by ROLE — `Box`, `Pusher`, `Holder`, `FirstHolder`,
  `TokenHolder`, `HalfTokenHolder`, `Topper <Expansion>` — except the Lid,
  which carries the card capacity and the sleeving, `Lid 168U`, as every
  shipped project has it: with several projects open it is the lid that says
  which cascade a plate belongs to (Allan, 2026-09-05; `project.object_name`).
  The other legacy suffixes (`TokenHolder Full`) are dropped.
- Parts keep the names the component file gives them (`Lid`, `Part 2`, ...).
- Plates are `<scheme name> — <project title>`, as `make_cascade` writes them;
  Bambu forbids `<>:/\|?*"` in a plate name.
- The project file is `<Game> <Short name> <Sleeved|Unsleeved> (<model>).3mf`
  (`components.cascade_filename`); FCM's own scheme is exempt.

## What the writer does not decide

Placements, plate membership, the bed and the tower position are inputs:
the writer draws what it is given and refuses nothing about layout. The
layout — the plate scheme, the bed ladder, the 45 degree strip packing, the
tower inside both nozzles' reach, the clearance checks — is the next section
of this work and lives beside it. Until then a layout can be READ off an
existing project (`project.read`), which is also what a keep-layout mode
would use.

## Verified

`tests/test_project.py` regenerates Dominion 168 Card Unsleeved from the
parts under `build/` in the shipped project's own layout, and holds the
result to the shipped file: the same objects with the same parts on the same
plates at the same positions, the same slots and extruders, `filaments
--check` clean, `towers` clean, and — where BambuStudio.app is installed — a
CLI slice of every plate with `return_code` 0.
