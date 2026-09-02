# The parametric cascade model — design record

Rebuilding the Onshape cascade geometry as build123d source, so that a cascade
is generated from `parts.csv` with **zero API calls** and the design is in git.

`automation/PIPELINE.md` describes the toolchain this replaces. Everything
downstream of a component `.3mf` — `make_cascade.py`, `verify.py`,
`filaments.py`, `towers.py`, `refresh_cascades.py` — is unchanged and unaware.

**Done so far: the Pusher, the Box and the Lid** — the Lid but for its logo
pattern, a per-game motif in a second filament. Holder, TokenHolder and Topper
are not written yet, so the Onshape path is still the one that builds a
cascade.

---

## Run it

```
.venv/bin/python -m cad.build                    # 34 pushers -> build/<Game>/
.venv/bin/python -m cad.build --list             # the catalogue, no writing

.venv/bin/python -m cad.build --part lid         # all 50 — under a minute
.venv/bin/python -m cad.build --part box --model S2.40.12-30.45-Sl
.venv/bin/python -m cad.build --part box         # all 50 — MINUTES
.venv/bin/python -m cad.build --part all         # all three

.venv/bin/python tests/test_pusher.py            # source vs the two STEPs
.venv/bin/python tests/test_pusher_regression.py # build/ vs individual/
.venv/bin/python tests/test_box.py               # source vs the six STEPs
.venv/bin/python tests/test_lid.py               # source vs the four STEPs
.venv/bin/python tests/test_lid_corpus.py        # the rules vs 44 cached lids
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
  mesh3mf.py    read/write a component 3MF in the shape Onshape's have
  build.py      the CLI: parts.csv -> build/<Game>/*.3mf
  render.py     shaded PNGs, for looking at a build without Studio
  parts/
    pusher.py   done
    box.py      done
    lid.py      done but for the logo PATTERN — see spec/LID.md
                holder.py token_holder.py topper.py — to come
spec/
  DERIVED.md    the Onshape variable studio, transcribed, and what it settled
  PUSHER.md     the Pusher measured, and what the rebuild reproduces
  BOX.md        the same for the Box
  LID.md        the same for the Lid
  reference/    hand-exported STEPs — the ground truth, 0 API calls
tests/
  test_derive.py            formulae vs every measured anchor on record
  test_pusher.py            the part vs both reference STEPs
  test_pusher_regression.py the 34 written 3MFs vs the 32 in individual/
  test_box.py               the part vs the six Box STEPs
  test_lid.py               the part vs the four structural Lid STEPs
  test_lid_corpus.py        the Lid's placement rules vs 44 cached meshes
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
engraves `CC 7.0` where every reference engraves `Rev 7.0`. The rule these set
is the point: a divergence is recorded in `spec/`, and asserted from both ends
— the build has the new behaviour, the reference still has the old one — so
re-converging fails the tests rather than passing quietly. Anything else that
differs from a reference is a bug.

## What each part is checked against

The Pusher and the Box have hand-exported STEPs and nothing else; the Lid has
both — four structural STEPs **and** 46 cached meshes in `individual/`. Both
are used, because they answer different questions. A STEP is exact and gives
faces, so it settles a section; four of them cannot tell a rule from a
coincidence across a 50-lid catalogue, which is what the meshes are for. The
`x = -0.300` the socket set sits on and the `9.000` its back edge is inset by
are constants on all 46 — that is what makes them rules rather than readings.

## Order of work

The **Pusher** first, and it is done. It is the simplest part;
`LOCK_STANDARD.md` already specifies its post-7.0 geometry completely;
`verify.py --pushers` is an existing pass/fail oracle; there are 32 cached
pushers to regress against; and the C1–C5 re-cut it is owed costs a real slice
of the API budget the moment it is done in Onshape instead.

Then the **Box**, which went first in the end because Allan had its feature
tree and five STEPs to hand, and then the **Lid**: shell, sockets, closing
grooves, outer rounds and the floor's engraving. What is left on it is the logo
PATTERN alone — a per-game motif printed in the second filament, which nothing
else on the part interacts with.

Then Holder, then TokenHolder, then Topper.
