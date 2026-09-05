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
- Plates share **one coordinate space**, a grid at a stride of 1.2 x the
  plate dimension with `ceil(sqrt(n))` columns for `n` plates — two for 2 to
  4, three for 5 to 9 — filled row by row, rows going -Y: plate 1 at the
  origin, 2 at `(1.2 W, 0)`, and with four plates 3 at `(0, -1.2 D)`, with
  five 3 at `(2.4 W, 0)`. Which plate an instance is on is ALSO written in
  `model_settings.config` (`<plate><model_instance>`), but Studio believes
  the POSITION: written on the wrong grid, a five-plate project's lid sat in
  no plate and the slice stopped with "no object fully inside". On a P1's
  256 mm plate the stride is 307.2; on an H2C's 330 x 320 it is 396 x 384.
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

## What the writer does not decide, and `cad/layout.py` does

Placements, plate membership, the bed and the tower position are inputs to
the writer: it draws what it is given and refuses nothing about layout. A
layout can be READ off an existing project (`project.read`), which is what a
keep-layout mode would use, or MADE by `cad/layout.py`, which is
`make_cascade --auto-plates` lifted whole — its rules, its numbers and its
refusals — so that a cascade needs no donor. `tests/test_layout.py` holds
the two to the same placements on Dominion 168 while both exist. In order:

1. **The bed** — the smallest of `project.BEDS` every object clears once
   turned 45 degrees, with 8 mm to spare, or the one the caller forces (a
   warning if something may not fit). parts.csv's `3D printer` column is the
   caller's business: `Mini`, `Standard`, `Large` name a bed, `Mixed` is P1
   unsleeved and H2C sleeved (`refresh_cascades.bed_for`). Left to the rule
   alone, 46 of the 48 shipped cascades land on the printer they shipped on;
   Dominion 324 Sleeved and Innovation 4 Later Ages Sleeved shipped on a P1P
   that the 8 mm margin refuses them, which is why the column decides and the
   rule is the fallback for a blank.
2. **The plates** — one per role group (box with its pushers, lid, holders,
   toppers, token holders, half token holders), split where a rotated box
   leaves no room for flat pushers, and where more thin strips than a plate
   holds need several. Shipped projects were laid out by hand and often
   differ here (Dominion's Mat boxes: five plates shipped, six by the rule).
3. **The packing** — thin strips at 45 degrees along two bed edges from a
   shared corner, or one centred diagonal band when that holds more; flat
   objects grid-searched into the free corners; a plate with nothing to
   rotate in centred shelf rows, widest first; the whole plate nudged off a
   corner exclude area; then every placement checked — on the bed, off the
   exclude area, 1 mm clear of its neighbours — and refused otherwise.
4. **The tower** — inside the intersection of every extruder's printable
   area, clear of the parts by 15 mm if any spot is, by 5 if not, furthest
   from the bed's centre. When nothing clears, the plate's contents are slid
   hard against each edge in turn (the slack a centred layout splits between
   two sides is enough for a tower on one), then the whole plate is packed a
   quarter turn round and tried again; a plate that still has no room is
   REFUSED (Allan, 2026-09-05: rotate the item or move the tower, never leave
   it colliding — make_cascade warned and left it). Dominion 333 Sleeved on
   a P1 is the case: its box and pushers in two centred shelf rows leave 34 mm
   above and below for a 35 mm tower; slid to the top they leave 68, and the
   tower goes to the bottom-right corner. `tests/test_layout.py` holds every
   written plate's tower clear of every object by the tight gap.

**One cascade the rules refuse, rightly.** Dominion 650 Sleeved's lid is
343.9 x 111.3: turned 45 degrees it spans 321.9 against an H2C's 330 x 320,
and the shipped project has it by hand at 44 degrees, 0.1 mm from one edge
and 0.3 mm OVER the other. No margin, so no rule; `tests/test_layout.py`
asserts it is the only refusal. Its shipped project stands, or a keep-layout
mode carries its placements forward.

**Two findings from writing 50 of them.** Studio's plate grid is not two
columns but `ceil(sqrt(n))`, above; and on the H2C both filaments ride
extruder 1 (`filament_map` 1,1 in the profile), so the usable width for a
two-colour object is 325 and not 330 — the 45 degree rule's 312 stays inside
it.

## Verified

`tests/test_project.py` regenerates Dominion 168 Card Unsleeved from the
parts under `build/` in the shipped project's own layout, and holds the
result to the shipped file: the same objects with the same parts on the same
plates at the same positions, the same slots and extruders, `filaments
--check` clean, `towers` clean, and — where BambuStudio.app is installed — a
CLI slice of every plate with `return_code` 0. Sliced side by side, the
shipped and the written project print in 3h48/3h52, 1h24/1h23, 4h55/4h59
and 1h06/1h06 per plate.

`tests/test_layout.py` holds `cad/layout.py` to `make_cascade
--auto-plates`'s own placements on the same parts, lays out and writes all
50 cascades (49, and the one refusal above) with towers and MakerWorld
checks clean, and slices a P1 and an H2C cascade — Dominion 168 Unsleeved
and 560 Sleeved — with every plate returning 0.

## The parallel run: `cad.cascade` and `cad.compare`

`python -m cad.cascade` is the pipeline as one command: row to project in
`build/cascades/<Game>/`, the bed from the row's `3D printer` column, the
source hash, row hash, model and version written into the file's metadata,
`filaments` and `towers` run on the result and `--slice` for Studio's
verdict. `python -m cad.compare` then holds every shipped project under
`cascades/` to its twin: the same roles in the same numbers, each object's
size within its role's known divergence (a 7.0 holder up to 1.6 longer than
a 6.6; the rest 0.05), both slots used the same way, the tower legal,
MakerWorld clean; the layout itself — where on a plate a part sits — is not
compared, because the shipped ones are hand-tuned and the cad ones the
rule's. Legacy object names are read for what they are (`TokenHolder Half`,
a token holder left as `Part 1`). `tests/test_parallel.py` runs both.

The scorecard on 2026-09-05: 45 shipped projects print the same parts as
their twins, none differ, and Dominion 650 Sleeved has no twin. The first
run of it found the topper defect above (every shipped topper prints in two
slots; the built ones in one), which is what the harness is for.
