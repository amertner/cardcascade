# The parametric cascade model — design record

Rebuilding the Onshape cascade geometry as build123d source, so that a cascade
is generated from `parts.csv` with **zero API calls** and the design is in git.

`PIPELINE.md` describes the toolchain this replaces. Everything downstream of a
component `.3mf` — `make_cascade.py`, `verify.py`, `filaments.py`, `towers.py`,
`refresh_cascades.py` — is unchanged and unaware.

---

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

---

## Layout

```
cad/
  params.py     Primary — the 10 inputs, frozen; loads a parts.csv row
  derive.py     Primary -> Derived. EVERY formula, once.
  tables.py     per-game and depth-banded lookups (reads spec/tables/)
  lock.py       LOCK_STANDARD.md in code; shared by box, lid, pusher
  common.py     shared build123d: text solids, logo DXF, chamfer idioms
  parts/
    box.py  lid.py  holder.py  pusher.py  token_holder.py  topper.py
  mesh3mf.py    3MF writer, lifted from labelmaker.py
  build.py      CLI -> build/<Game>/*.3mf
spec/
  DERIVED.md    the Onshape variable studio, transcribed
  tables/       the lookups as CSV
tests/
  test_derive.py      formulae vs known anchors
  test_lock.py        catalogue conformance, analytic
  test_regression.py  generated vs the frozen individual/ corpus
```

## Four decisions

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
there. Tessellation non-determinism (`README.md`, on labels) stops mattering,
because the mesh stops being the thing under test.

**3. Build to `build/`, never over `individual/`.**
`individual/` is 242 components and 68 raw assemblies — the only ground truth
there is, and unreproducible at any sane API cost. It is frozen and read-only
until a component type passes regression. `build.py --promote` copies across.

**4. Generation is a parameter, not a git tag.**
20 cascades build at 7.0 and 28 stay at 6.6, and `refresh_cascades` must build
both **in one run**, so "check out the 6.6 tag" does not work. `Primary` carries
its generation and the geometry branches on it. 6.6 → 7.0 is exactly the lock
catalogue, which `lock.py` already isolates, so the branch is one module deep —
but a second such split landing somewhere less tidy is the thing to watch, and
the reason to keep generations few and short-lived.

## Order of work

The **Pusher** first. It is the simplest part; `LOCK_STANDARD.md` already
specifies its post-7.0 geometry completely; `verify.py --pushers` is an existing
pass/fail oracle; there are 32 cached pushers to regress against; and the C1–C5
re-cut it is owed costs a real slice of the API budget the moment it is done in
Onshape instead. Then Lid (same lock, plus embossed version text), then Box,
then Holder, then TokenHolder, then Topper.
