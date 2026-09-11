# The parametric cascade model — THE design record

The cascade geometry as build123d source, so that a cascade is generated from
`parts.csv` with **zero API calls** and the design is in git.

**This is the authoritative pipeline as of 2026-09-06** (Allan). It began as a
rebuild of the Onshape model and is now the model: new work, changed geometry
and releases go through `cad.build` / `cad.cascade`, and this file and `spec/`
are where the design lives. `automation/PIPELINE.md` describes the Onshape
pipeline it replaced, which is LEGACY — kept runnable, not used. It built
every 7.0 project, now `spec/reference/shipped-7.0/` (it was `cascades/` until
the 7.1 release took that tree over), and `individual/` plus `spec/reference/`
are the corpus that keeps a 7.0 build honest. `cad.cascade` writes a project
without `make_cascade.py` or `refresh_cascades.py`; `verify.py`, `filaments.py`
and `towers.py` are not legacy, and check cad output as well.

**Every part is written: the Pusher, the Box, the Lid, the TokenHolder, the
Holder and the Topper** — the Lid including its logo pattern for all four
games, the TokenHolder in both its configurations, the Topper for all six
expansions. The first printed lids, Dominion's and Innovation's, settled a
question no render could (see "Assemblies" below). Since 2026-09-11 `cascades/` holds the
cad-built 7.1 release, copied from `build/cascades/` and tagged `v7.1`; what
the old pipeline shipped is `spec/reference/shipped-7.0/`, tagged `v7.0`.

The Lid's mark is the most visible place `cad/` deliberately differs from
Onshape (decision 6 lists the rest): it is FITTED to the lid — the biggest
mark that fits, sized to a proportion of the lid — where Onshape draws it at
one or two fixed sizes. `spec/LID.md`, "Sizing the mark", is the record, and
the three constants behind it — `LOGO_WIDTH_FRACTION`, `LOGO_DEPTH_FRACTION`
and `LOGO_CLEAR` — are in `cad/parts/lid.py`.

Fitting is why Innovation's plain mark is GENERATED rather than drawn
(`cad/marks.py`): scaling an outline scales its `0.600` strokes with it, and
Allan's sketch holds them absolute. It is built from Noto Serif and the
geometry hung off the letters — the annulus round the `I`, the five arms
through the `i`'s tittle — every number of it measured off the two drawings it
replaces, which stay in `logos/Innovation/` as its regression reference.

---

## Run it

```
.venv/bin/python -m cad.build                    # 34 pushers -> build/<Game>/
.venv/bin/python -m cad.build --list             # the catalogue, no writing

.venv/bin/python -m cad.build --part lid         # all 54, 4 of them Ultimate — 2.5 min pooled
.venv/bin/python -m cad.build --part box --model S2.40.12-30.45-Sl
.venv/bin/python -m cad.build --part box         # all 50 — 2 min pooled
.venv/bin/python -m cad.build --part tokenholder # 22, Dominion only, seconds
.venv/bin/python -m cad.build --part holder      # all 56 — 1 min pooled
.venv/bin/python -m cad.build --part all         # all 264 — 3 min; 0 s again
.venv/bin/python -m cad.build --part all --jobs 1 --force   # serial, everything

.venv/bin/python -m cad.assemble --model S4.16.10.32-Un --state all
.venv/bin/python -m cad.fit --model S4.16.10.32-Un --state play
.venv/bin/python -m cad.fit --model S4.16.10.32-Un --no-solids   # seconds
.venv/bin/python -m cad.render \
    "build/assemblies/Dominion/S4.16.10.32-Un play.3mf" --assembly
.venv/bin/python -m cad.assemble --game Innovation --state all      # then LOOK:
.venv/bin/python -m cad.render build/assemblies/Innovation/*play.3mf \
    --assembly --contact tmp/play.png --view hero --view bottom     # the lids' marks, as they print
.venv/bin/python -m cad.render "build/assemblies/Innovation/*closed-lid.3mf" \
    --assembly --contact tmp/closed.png                           # the closed product

.venv/bin/python -m cad.gltf "build/assemblies/<Game>/<model> play.3mf" \
    --filaments '#F4F4F2,#1B1B1B' --part 'Lid=#0E6BA8' -o tmp/cascade.glb
blender -b -P render/cascade.py -- tmp/cascade.glb --view hero --samples 256

.venv/bin/python -m cad.cascade --model S4.16.10.32-Un   # row -> build/cascades/<Game>/<title>.3mf
.venv/bin/python -m cad.cascade --game Dominion --sleeving un --slice   # ... and Studio slices each
.venv/bin/python -m cad.cascade --build                  # every cascade, parts built first if stale
.venv/bin/python -m cad.cascade --list                   # what would be made, and on which bed
.venv/bin/python -m cad.cascade --publish                # the set to UPLOAD: version in the file
                                                         # names, to build/dist/<version>/
.venv/bin/python -m cad.build --part all --version 7.0   # another release -> build/v7.0/,
                                                         # which cad.compare and test_parallel read

.venv/bin/python -m cad.promote --model S4.16.10.32-Un   # LEGACY route: build/ -> planner names ->
automation/refresh_cascades.py --game Dominion --name 168 --sleeving un \
    --components build/components --out build/cascades --auto   # make_cascade with a donor

.venv/bin/python tests/run_all.py                # every suite, concurrently; --quick, --only, --build, --jobs 1
.venv/bin/python tests/test_revisions.py         # any one suite runs alone; run_all.py's table lists them
.venv/bin/python -m cad.render build/*/*.3mf --contact tmp/contact.png
.venv/bin/python -m cad.render build/*/Box*.3mf --box --contact tmp/box.png
```

Builds run in a process pool, one part per job and every core by default
(`--jobs`), and every file gets a STAMP beside it — a digest of its Primary
and of every source file under `cad/`, `logos/` and `fonts/` — so a rerun
with nothing changed skips it in a fraction of a second and any edit
anywhere in `cad/` rebuilds everything that could depend on it. `--force`
ignores the stamps. `--model` matches on the filename and is how to build
one. `--box` on the renderer swaps the camera: its default is aimed at a
pusher lying flat and renders a 105 mm-tall box as a squashed ribbon.

`build/` is disposable and gitignored. Rebuilding unchanged source gives
byte-identical files — the pool included, proven by a pooled rebuild of the
serial catalogue changing nothing — so `cad.build` reports `changed` only
when something really moved. Six holders are two geometries under two names
each (the Mat twins); one is built and the other is its bytes.

## Layout

```
cad/
  params.py     Primary — the 10 inputs, frozen; loads a parts.csv row
  derive.py     Primary -> Derived. EVERY formula, once.
  tables.py     per-game lookups, transcribed from the variable studio
  lock.py       LOCK_STANDARD.md in code; shared by box, lid, pusher
  revisions.py  the release line and its named flags — the ONE place a release change lives
  text.py       fonts and the sizing rules
  marks.py      every lid mark, drawn or generated, behind one interface
  geom.py       slab, tray, text_solid — the three shapes every part drew itself
  art.py        imported 2D artwork: a DXF's loops -> filled regions
  mesh3mf.py    read/write a component 3MF in the shape Onshape's have
  build.py      the CLI: parts.csv -> build/<Game>/*.3mf
  render.py     shaded PNGs, for looking at a build without Studio
  assembly.py   WHERE each part goes — placements, and nothing else
  assemble.py   the CLI: parts.csv -> build/assemblies/<Game>/*.3mf
  fit.py        interference and margins — the reason the assemblies exist
  gltf.py       an assembly -> .glb, for a renderer that can light it
  lazy.py       a module imported on first use; keeps build123d out of --list
  refuse.py     Refused — the one exception every guard raises, caught once per CLI
  project.py    a Bambu Studio project written from parts and placements, no donor — spec/PROJECT.md
  layout.py     the plate scheme, bed, 45-degree packing and tower, lifted from make_cascade
  cascade.py    a parts.csv row -> its parts under build/ and its project title
  compare.py    the Onshape-shipped 7.0 projects vs their cad twins — a regression check
  promote.py    LEGACY: stages build/ under the planner's names for refresh_cascades
  parts/
    pusher.py   done
    box.py      done
    lid.py      done, logo pattern included — see spec/LID.md
    token_holder.py  done — FULL and HALF, Dominion only
    holder.py   done — see spec/HOLDER.md
    topper.py   done — the blank and all six expansions; see spec/TOPPER.md
render/
  cascade.py    Blender/Cycles. Runs in BLENDER's python, not the venv
spec/
  ASSEMBLY.md   where each part goes in a whole cascade, and what settled it
  RENDER.md     two renderers, and why they are two
  DERIVED.md    the Onshape variable studio, transcribed, and what it settled
  UNKNOWNS.md  every constant that holds but is not derived, and what would settle it
  PUSHER.md     the Pusher measured, and what the rebuild reproduces
  BOX.md        the same for the Box
  LID.md        the same for the Lid
  TOKENHOLDER.md the same for the TokenHolder, both configurations
  HOLDER.md     the same for the Holder, and where it diverges on purpose
  TOPPER.md     the same for the Topper, all six expansions
  PROJECT.md    the Bambu Studio project cad.cascade writes
  REVISIONS.md  the release line, and what changed at each release
  reference/    hand-exported STEPs — the ground truth, 0 API calls — and
                shipped-7.0/, the projects the Onshape pipeline shipped
tests/
  run_all.py    runs every suite; its table is the list of them
  reference.py  pins 7.0 for every test that compares against a reference
  probe.py      ray-casting a mesh: the corpus tests' instrument
  test_*.py     a suite per part (vs its STEPs), per corpus (vs individual/),
                and per rule (floors, meshes, releases, layout, project)
  holder_diff.py, box_diff.py   dev loops, band by band and lump by lump, not tests
```

## What this replaces, and what it does not

**Replaces** (~130 KB whose entire job is rationing and reconstructing API
calls): `plan_exports.py`, `export.py`, `onshape.py`, `onshape_config.py`,
`onshape_test.py`, `set_variables.py`, `provenance.py`, `mesh.py`,
`assembly_split.py`, `topper_split.py`.

**Leaves standing**: `individual/<Game>/`, as the regression corpus, and the
checks that read components — `verify.py`, `filaments.py`, `towers.py`. A
written component has the shape of a cached one, if not its bytes.

Two of the retired modules deserve a note, because they are good code solving a
problem that only exists upstream. `assembly_split.py` tells `Holder` from
`FirstHolder` **by height**, because an assembly export names both `Holder`.
`topper_split.py` identifies six same-named assembly instances by **glyph widths
as a fraction of word width**. Generated locally, both parts simply get named.

## Two typefaces, both identified rather than assumed

`fonts/Orbitron-Bold.ttf` — already used by `labelmaker.py` — sets the product
name and version. `fonts/OpenSans-Bold.ttf` sets the detail line, because
Orbitron is a wide geometric face and Open Sans fits more text in the same
space. Both are Google Fonts under the OFL.

The weight matters and was tested, not guessed: against the reference STEPs
Open Sans **Bold** lands within `0.0006 mm`, where SemiBold is out by `0.17`
and Regular by `0.34`. The thin `l` is what separates them.

## Text sizing is a rule, not a transcription, and it has a floor

Since 2026-09-04 every text placement is FLOORED (`cad/text.py`, "floors"):
text cut into a part is set no smaller than a `0.200` mm stroke and text that
stands proud — embossed, or a second-filament inlay — no smaller than `0.250`,
each face's thinnest stroke measured off a raster of the strings it sets. A
line under its floor is raised to it and gives up margin; one that would then
overrun the part raises `DoesNotFit` rather than write it. It raises
sixteen lines across the catalogue — four pusher version lines, one detail
line, nine box lines, and the 10-card unsleeved toppers' names, whose inlay
prints face down in a pocket and so takes the CUT floor (`spec/TOPPER.md`).
`tests/test_text_floors.py` asserts the set exactly.

Onshape can constrain sketch text in only one dimension, so a box that suits
one parameter set does not suit another — the same string comes out `3.85x`
bigger on one reference than the other. `cad/text.py` fits **both** dimensions
instead, and `tests/test_pusher.py` holds the result to its own bounds on all
34 pushers, not just the two references. `spec/PUSHER.md` has the numbers.

## Assemblies, and the one thing they found

`cad/assembly.py` places the parts into a whole cascade — **closed**, **closed
with the lid on**, and **cascaded** for play — and `cad/fit.py` measures the
result. This is the first thing in the repo that can check the MECHANISM rather
than a part: every clearance in the design is asserted one part at a time today,
against a reference that only ever shows that part.

It is a separate module for the reason `derive.py` is one: every formula once,
every placement once. `assembly.py` imports no build123d, so the mates are pure
arithmetic and testable on their own, and it introduces no constant of its own —
each placement is derived from `derive.py` and the part modules, and
`spec/ASSEMBLY.md` records what settled it.

On Dominion `S4.16.10.32-Un` every pair of source-built parts intersects in
**0.0000 mm3** in all three states, and every named margin lands on its nominal
to 0.001. Two findings came out of it:

* **A pusher's treads sit 0.150 forward of the box's slider ribs, on every
  cascade** — a constant, with every parameter cancelling — which leaves a
  holder on its tread with 0.350 at the front and 0.050 at the back. Nothing is
  broken by it, and nothing before now could see it.
* **Three of the four games' lid marks were 180 degrees from the fourth.** A
  closed lid can go on either way round — nothing geometric distinguishes the
  two, and both measure 0.0000 mm3 — so the only thing that can tell is the
  logo, and Dominion's disagreed with Compile's, FCM's and Innovation's. One
  game was upside down whichever way was chosen, on the shipped product as
  much as here: `cad/` rotates no artwork, and its inlays matched the cached
  Onshape lids to 0.001. Dominion's DXF was turned on 2026-09-04 from a
  photograph of the shipped Innovation boxes, and turned BACK on 2026-09-11
  when a printed Dominion lid came out upside down. A printed Innovation lid
  did too, and its generated mark now goes in turned
  (`tables.LID_LOGO_TURNED`); the photograph had been misread. Compile and
  FCM are predicted upside down as well and are open until printed
  (`spec/LID.md`).

`spec/ASSEMBLY.md` has both. The second is the case for treating renders as
part of the checking rather than its output: it is invisible to every number
`cad/fit.py` computes.

## Seven decisions

**1. Derived variables live in exactly one module, and a shared formula too.**
`derive.py` takes a `Primary` and returns a frozen `Derived`. Component modules
read from it and never recompute. The rule is narrower than "every formula":
the variable studio is transcribed in full, a sketch variable joins it when
more than one module reads it (`#BoxWidth`, `#calPusherSlots`), and a
part-studio formula two parts share is written once there (`cascade_slope`,
`back_slot_pitch`) — the Box's lip angle and the Holder's slant were the same
expression transcribed as reciprocals of each other until it was. A formula
one part uses stays in that part. This mirrors Onshape (variable studio → part
studios read the variables), makes the derived layer testable on its own, and is
the only way the same quantity — inner box width, say — stays identical across
Box, Lid and Holder. `Derived` is frozen so a part cannot write to it.

**2. `build()` returns B-rep, not mesh.**
Meshing is the last step, in `mesh3mf.py`. Tests assert on faces and edges at
exact coordinates. This is the upgrade over the Onshape pipeline, where a mesh is
all Onshape hands back: `verify.py` chains 2D section loops and probes a 900×300
grid to find a pusher tab, and `check_box`'s 1.2 mm depth tolerance is a
concession to that. From a B-rep you know where the tab is because you put it
there.

**3. Build to `build/`, never over `individual/`.**
`individual/` is 242 components and 68 raw assemblies — the only ground truth
there is, and unreproducible at any sane API cost. It is frozen and read-only
for good: every component type has passed regression against it, and it stays
the corpus a 7.0 build is held to.

**4. One lock: 7.0's.**
`lock.py` is the 7.0 catalogue and every release on the line keeps it
(`lock.SAME_LOCK`, 7.0 through 7.1); `pusher.build` **refuses** a `Primary` at
any version outside it rather than stamp `CC 6.6` on 7.0 tabs. The Lid is the same
story on its own half of the lock: a 7.0 lid is told from a pre-7.0 one by a
`1.700` recess step against the pre-7.0 `1.800`, and `tests/test_lid_corpus.py`
asserts the first group and reports the second — all 48 cached lids are 7.0
since the September refreshes, as are all 48 boxes (`tests/test_box_corpus.py`). A pre-7.0 pusher put
its tabs at a fixed inset from the two depth edges instead (4.20 front, 4.00
back, notch always — measured identical on all 14 still-6.6 pushers in
`individual/`), and nothing here reproduces that. `build/` was the migration
TARGET, not a mirror — it reproduces the 18 pushers Onshape had re-cut and
moves the other 14 onto the catalogue — and the 7.1 release completed the
migration: every cascade in `cascades/` is cad-built. `derive.py` keeps the pre-7.0 variables because it is a
transcription of the studio and they are still in it — nothing reads them.

**5. The Pusher name carries the first-riser axis.**
A pusher's depth depends on `FirstSlidingSlotCards`, but `plan_exports` keys it
`(risers, cards, sleeved)` — so Dominion `324 Card` and `290 Card (Mat)` collide
on `Pusher 6x10-*.3mf` and differ by 1.20 mm sleeved. `build.py` writes
`Pusher 6x10-12-Sl.3mf` for the override, following parts.csv's own model-code
convention (`M6.21.10/12`, with `/` folded to `-`). Four files are consequently
named differently from `individual/` and two are new. `pusher_file(d,
legacy=True)` gives the old name, which is how `tests/test_pusher_regression.py`
finds a pusher's cached twin, and the legacy `cad.promote` refuses where two
built files would land on one planner name.

**6. Where the rebuild diverges from Onshape, it says so and tests both sides.**
The Box's hanging holes are cut through the rear storage dividers in Onshape —
on `Box Dominion 244S` all three, at full width, so each is severed at every
hole row. `cad/` stops them at the slot band and leaves the dividers solid
(Allan). The Box's version line is the second: Onshape's sketches still read
`Rev <version>` and Allan wants `calVersion`, as the Lid has, so the build
engraves `CC 7.0` where every reference engraves `Rev 7.0`. The third is the
XS box's front label holder, which in Onshape carries no fastener at all — the
build puts one in the middle, the only place a `10.000` ridge fits on a
`65.600` holder. The Holder's slot mouth is a fourth — flared 45 degrees for
its bottom 0.300 so an elephant's foot closes the chamfer and not the groove
(`spec/HOLDER.md`) — and the Lid's fitted mark a fifth. The rule these set
is the point: a divergence is recorded in `spec/`, and asserted from both ends
— the build has the new behaviour, the reference still has the old one — so
re-converging fails the tests rather than passing quietly. Anything else that
differs from a reference is a bug.

**7. A RELEASE change is not a divergence, and it lives in one place.**
A divergence is `cad/` against Onshape at the SAME version, forever. A release
change is `cad/` 7.0 against `cad/` 7.1 — the Lid's one socket per pusher is
the first — and it lives in `cad/revisions.py`, reaching a part as a NAMED
flag on the Derived (`d.rev.lid_socket_per_pusher`), never as a version
comparison. A build at the older release must keep reproducing `individual/`
exactly, which is why every test that compares against a reference pins its
release through `tests/reference.py` rather than taking the default: the
default is 7.1 and will move again. `spec/REVISIONS.md` is the record and
`tests/test_revisions.py` asserts every flag at both releases.
A flag does not have to reach a PART: `both_lid_editions` (7.1d) is read by
`build.lid_editions_built` and `cascade.parts`, because what it changes is how
many lids a cascade has and not what any one of them is. The rule is the same
wherever it is read — a named question, never a version comparison.

## One record below `derive`

A `Primary` is the parts.csv row's ten inputs and nothing else; `derive`
turns it into a `Derived`, and the Derived carries those ten by name
beside everything computed from them — `d.HorizontalSlots` next to
`d.calSlotwidth`, as every Onshape part studio reads them. So every
function below `derive` — a part's features and its `build`, a placement
in `assembly`, a margin in `fit`, a file name in `build` — takes `d` and
nothing else. A Primary is handled only where rows come in: `params`, the
catalogues, the stamps. Until 2026-09-06 every feature took `(p, d)`, a
carry-over from Onshape's split between the variable studio's inputs and
its outputs that has no counterpart in one Python record.

## What each part is checked against

The Pusher and the Box have hand-exported STEPs and nothing else; the Lid has
both — four structural STEPs **and** 48 cached meshes in `individual/`. Both
are used, because they answer different questions. A STEP is exact and gives
faces, so it settles a section; four of them cannot tell a rule from a
coincidence across a 50-lid catalogue, which is what the meshes are for.

Neither settles WHY, and on the Lid that mattered twice. Two placements
reproduced all 48 lids exactly and were still attached to the wrong datum — the
engraving hung off the pusher sockets where the sketch hangs it off the wall,
and the socket set read as centred with a mysterious `-0.300` where the sketch
anchors its first socket and lets the margin fall where it falls. Both are
recorded in `spec/LID.md` under "What the fit got wrong", because the lesson
generalises: a rule that reproduces the whole catalogue can still be the wrong
rule, and the tell is a term no derived variable produces.

## Order of work

The **Pusher** first, and it is done. It is the simplest part;
`LOCK_STANDARD.md` already specifies its post-7.0 geometry completely;
`verify.py --pushers` is an existing pass/fail oracle; there are 32 cached
pushers to regress against; and the C1–C5 re-cut it is owed costs a real slice
of the API budget the moment it is done in Onshape instead.

Then the **Box**, which went first in the end because Allan had its feature
tree and five STEPs to hand, and then the **Lid**: shell, sockets, closing
grooves, outer rounds, the floor's engraving and the logo pattern, the artwork
for all four games and the rule behind the logo's scale.

Then the **TokenHolder**, which is done: it is the simplest part in the
catalogue after the Pusher, it has a STEP for each of its two configurations,
and — alone so far — its 18 cached components are a REGRESSION target rather
than a shape reference, because it did not change in 7.0.

Then the **Holder**, which is done, including the two features no kernel will
compute for itself — `Fillet 1`, whose two rounds meet exactly, and the chamfer
on `Lip Rest` — both modelled into their cuts and both measured. It is also the
part that found the one meshing bug in the writer (`spec/HOLDER.md`, "The mesh").

Then the **Topper**, which is done: the blank and all six expansions, the five
marks derived from `calLogoSidelength` rather than traced (`spec/TOPPER.md`).
