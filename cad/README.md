# The parametric cascade model — design record

Rebuilding the Onshape cascade geometry as build123d source, so that a cascade
is generated from `parts.csv` with **zero API calls** and the design is in git.

`automation/PIPELINE.md` describes the toolchain this replaces. Everything
downstream of a component `.3mf` — `make_cascade.py`, `verify.py`,
`filaments.py`, `towers.py`, `refresh_cascades.py` — is unchanged and unaware.

**Done so far: the Pusher, the Box, the Lid and the TokenHolder**, the Lid
including its logo pattern for all four games and the TokenHolder in both its
configurations. The Holder is most of the way there and writes 3MFs, but is
about 2% heavy and not printable yet (`spec/HOLDER.md`); the Topper is not
written at all. The Onshape path is still the one that builds a cascade.

The Lid's mark is the one place `cad/` deliberately differs from Onshape: it
is FITTED to the lid — the biggest mark that fits, sized to a proportion of
the lid — where Onshape draws it at one or two fixed sizes. `spec/LID.md`,
"Sizing the mark", is the record, and the two constants behind it are two
lines in `cad/parts/lid.py`.

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

.venv/bin/python -m cad.build --part lid         # all 50 — under a minute
.venv/bin/python -m cad.build --part box --model S2.40.12-30.45-Sl
.venv/bin/python -m cad.build --part box         # all 50 — MINUTES
.venv/bin/python -m cad.build --part tokenholder # 22, Dominion only, seconds
.venv/bin/python -m cad.build --part all         # all of them

.venv/bin/python -m cad.assemble --model S4.16.10.32-Un --state all
.venv/bin/python -m cad.fit --model S4.16.10.32-Un --state play
.venv/bin/python -m cad.fit --model S4.16.10.32-Un --no-solids   # seconds
.venv/bin/python -m cad.render \
    "build/assemblies/Dominion/S4.16.10.32-Un play.3mf" --assembly

.venv/bin/python tests/test_pusher.py            # source vs the two STEPs
.venv/bin/python tests/test_pusher_regression.py # build/ vs individual/
.venv/bin/python tests/test_box.py               # source vs the nine STEPs
.venv/bin/python tests/test_lid.py               # source vs the four STEPs
.venv/bin/python tests/test_lid_corpus.py        # the rules vs 44 cached lids
.venv/bin/python tests/test_token_holder.py      # source vs both STEPs
.venv/bin/python tests/test_token_holder_corpus.py  # the rules vs all 18
.venv/bin/python -m cad.render build/*/*.3mf --contact tmp/contact.png
.venv/bin/python -m cad.render build/*/Box*.3mf --box --contact tmp/box.png
```

Pushers are the default because they take under a second each, as a lid does. A
box is about ten, so `--part box` on the whole catalogue is minutes — `--model`
matches on the model code and is how to build one. `--box` on the renderer swaps the
camera: its default is aimed at a pusher lying flat and renders a 105 mm-tall
box as a squashed ribbon.

`build/` is disposable and gitignored. Rebuilding unchanged source gives
byte-identical files, so `cad.build` reports `changed` only when something
really moved.

## Layout

```
cad/
  params.py     Primary — the 10 inputs, frozen; loads a parts.csv row
  derive.py     Primary -> Derived. EVERY formula, once.
  tables.py     per-game lookups, transcribed from the variable studio
  lock.py       LOCK_STANDARD.md in code; shared by box, lid, pusher
  text.py       fonts and the sizing rules
  art.py        imported 2D artwork: a DXF's loops -> filled regions
  mesh3mf.py    read/write a component 3MF in the shape Onshape's have
  build.py      the CLI: parts.csv -> build/<Game>/*.3mf
  render.py     shaded PNGs, for looking at a build without Studio
  assembly.py   WHERE each part goes — placements, and nothing else
  assemble.py   the CLI: parts.csv -> build/assemblies/<Game>/*.3mf
  fit.py        interference and margins — the reason the assemblies exist
  parts/
    pusher.py   done
    box.py      done
    lid.py      done, logo pattern included — see spec/LID.md
    token_holder.py  done — FULL and HALF, Dominion only
    holder.py   INCOMPLETE — see spec/HOLDER.md; topper.py to come
spec/
  ASSEMBLY.md   where each part goes in a whole cascade, and what settled it
  DERIVED.md    the Onshape variable studio, transcribed, and what it settled
  PUSHER.md     the Pusher measured, and what the rebuild reproduces
  BOX.md        the same for the Box
  LID.md        the same for the Lid
  TOKENHOLDER.md the same for the TokenHolder, both configurations
  reference/    hand-exported STEPs — the ground truth, 0 API calls
tests/
  test_derive.py            formulae vs every measured anchor on record
  test_pusher.py            the part vs both reference STEPs
  test_pusher_regression.py the 34 written 3MFs vs the 32 in individual/
  test_box.py               the part vs the nine Box STEPs
  test_lid.py               the part vs the four structural Lid STEPs
  test_lid_corpus.py        the Lid's placement rules vs 44 cached meshes
  test_token_holder.py      the part vs both TokenHolder STEPs
  test_token_holder_corpus.py  its rules vs all 18 cached token holders
```

## What this replaces, and what it does not

**Replaces** (~130 KB whose entire job is rationing and reconstructing API
calls): `plan_exports.py`, `export.py`, `onshape.py`, `onshape_config.py`,
`onshape_test.py`, `set_variables.py`, `provenance.py`, `mesh.py`,
`assembly_split.py`, `topper_split.py`.

**Keeps**: everything that consumes components. `individual/<Game>/*.3mf` stays
the interface, byte-compatible in shape if not in bytes.

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

## Text sizing is a rule, not a transcription

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
to 0.001. The one finding is that **a pusher's treads sit 0.150 forward of the
box's slider ribs, on every cascade** — a constant, with every parameter
cancelling — which leaves a holder on its tread with 0.350 at the front and
0.050 at the back. Nothing is broken by it, and nothing before now could see it.
`spec/ASSEMBLY.md` has the arithmetic.

## Six decisions

**1. Derived variables live in exactly one module.**
`derive.py` takes a `Primary` and returns a frozen `Derived`. Component modules
read from it and never recompute. This mirrors Onshape (variable studio → part
studios read the variables), makes the derived layer testable on its own, and is
the only way the same quantity — inner box width, say — stays identical across
Box, Lid and Holder. `Derived` is frozen so a part cannot write to it.

**2. `build()` returns B-rep, not mesh.**
Meshing is the last step, in `mesh3mf.py`. Tests assert on faces and edges at
exact coordinates. This is the upgrade over the current pipeline, where a mesh is
all Onshape hands back: `verify.py` chains 2D section loops and probes a 900×300
grid to find a pusher tab, and `check_box`'s 1.2 mm depth tolerance is a
concession to that. From a B-rep you know where the tab is because you put it
there.

**3. Build to `build/`, never over `individual/`.**
`individual/` is 242 components and 68 raw assemblies — the only ground truth
there is, and unreproducible at any sane API cost. It is frozen and read-only
until a component type has passed regression.

**4. One generation: 7.0.**
`lock.py` is the 7.0 catalogue, and `pusher.build` **refuses** a `Primary` at
any other version rather than stamp `CC 6.6` on 7.0 tabs. The Lid is the same
story on its own half of the lock: 25 of the 44 cached lids are 7.0 and 19 are
not, told apart by a `1.700` recess step against the pre-7.0 `1.800`, and
`tests/test_lid_corpus.py` asserts the first group and reports the second. A pre-7.0 pusher put
its tabs at a fixed inset from the two depth edges instead (4.20 front, 4.00
back, notch always — measured identical on all 14 still-6.6 pushers in
`individual/`), and nothing here reproduces that. So `build/` is the migration
TARGET, not a mirror: it reproduces the 18 pushers Onshape has already re-cut
and moves the other 14 onto the catalogue. Those 14 stay Onshape's until their
cascades migrate. `derive.py` keeps the pre-7.0 variables because it is a
transcription of the studio and they are still in it — nothing reads them.

**5. The Pusher name carries the first-riser axis.**
A pusher's depth depends on `FirstSlidingSlotCards`, but `plan_exports` keys it
`(risers, cards, sleeved)` — so Dominion `324 Card` and `290 Card (Mat)` collide
on `Pusher 6x10-*.3mf` and differ by 1.20 mm sleeved. `build.py` writes
`Pusher 6x10-12-Sl.3mf` for the override, following parts.csv's own model-code
convention (`M6.21.10/12`, with `/` folded to `-`). Four files are consequently
named differently from `individual/` and two are new; `--legacy-names` writes
the old names and refuses when two geometries would land on one. Promotion needs
the planner's key to gain the axis first.

**6. Where the rebuild diverges from Onshape, it says so and tests both sides.**
The Box's hanging holes are cut through the rear storage dividers in Onshape —
on `Box Dominion 244S` all three, at full width, so each is severed at every
hole row. `cad/` stops them at the slot band and leaves the dividers solid
(Allan). The Box's version line is the second: Onshape's sketches still read
`Rev <version>` and Allan wants `calVersion`, as the Lid has, so the build
engraves `CC 7.0` where every reference engraves `Rev 7.0`. The third is the
XS box's front label holder, which in Onshape carries no fastener at all — the
build puts one in the middle, the only place a `10.000` ridge fits on a
`65.600` holder. The rule these set
is the point: a divergence is recorded in `spec/`, and asserted from both ends
— the build has the new behaviour, the reference still has the old one — so
re-converging fails the tests rather than passing quietly. Anything else that
differs from a reference is a bug.

## What each part is checked against

The Pusher and the Box have hand-exported STEPs and nothing else; the Lid has
both — four structural STEPs **and** 46 cached meshes in `individual/`. Both
are used, because they answer different questions. A STEP is exact and gives
faces, so it settles a section; four of them cannot tell a rule from a
coincidence across a 50-lid catalogue, which is what the meshes are for.

Neither settles WHY, and on the Lid that mattered twice. Two placements
reproduced all 46 lids exactly and were still attached to the wrong datum — the
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
grooves, outer rounds, the floor's engraving and the logo pattern. What is left
there is DATA rather than shape — the artwork for two games, and the rule
behind the logo's scale.

Then the **TokenHolder**, which is done: it is the simplest part in the
catalogue after the Pusher, it has a STEP for each of its two configurations,
and — alone so far — its 18 cached components are a REGRESSION target rather
than a shape reference, because it did not change in 7.0.

Then the Holder, and then the Topper.
