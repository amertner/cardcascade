# Card Cascade

3D-printed card storage boxes ("cascades") for board games, plus the box
labels. Everything here generates printable 3MF projects.

## Three toolchains — work out which one you're in first

| | Labels | Cascades (the boxes) | The rebuild |
|---|---|---|---|
| Entry point | `labelmaker.py` | `automation/refresh_cascades.py` | `python -m cad.build` |
| Geometry from | build123d, generated locally | Onshape, exported via API | build123d, generated locally |
| Config | `cc.cfg` | `automation/parts.csv` | `automation/parts.csv` |
| Read first | `README.md` | `automation/PIPELINE.md` | `cad/README.md`, `spec/` |
| Output | `cascades/<Game>/labels/` | `cascades/<Game>/` | `build/<Game>/` (gitignored) |

**Read the relevant doc before editing any of them.** `PIPELINE.md` in
particular records decisions and their reasoning; it is the design record, not
a summary. `cad/README.md` and `spec/` are the same kind of thing for the
rebuild.

### The rebuild is partial — don't assume it covers a part

`cad/` replaces the Onshape geometry with build123d source, so a cascade can be
generated with **zero API calls**. **Pusher**, **Box**, **Lid**,
**TokenHolder**, **Topper** and **Holder** — **every part is now done**, the
Holder and the Topper having landed on separate branches at the same time. The
Lid includes the logo pattern in its underside for all four games
(`logos/<Game>/*.dxf`; `spec/LID.md`); the TokenHolder covers both its FULL and
HALF configurations (`spec/TOKENHOLDER.md`); the Topper covers all six
expansions, its five marks derived from `calLogoSidelength` rather than traced
(`spec/TOPPER.md`); the Holder reproduces all ten references to `+0.007%` once
its intended text divergence is set aside (`spec/HOLDER.md`).

So no component's GEOMETRY needs Onshape any more. That is not the same as
saying a cascade does not: `automation/` still assembles, verifies and packages
one, is what has actually shipped every cascade on disk, and stays
authoritative. One cascade has been built end to end from `build/`:
`python -m cad.promote` stages built parts under the planner's names, and
`refresh_cascades.py --components build/components --out build/cascades`
assembles from them without touching `cascades/` or `individual/`. Dominion
`168 Card Unsleeved` came through that, `filaments.py --check`, `towers.py`
and a Bambu Studio slice (`return_code` 0). Four token holders cannot be
staged that way — `spec/TOKENHOLDER.md`'s size-letter collision — and the
result has not been printed.

- The Lid's logo is the one place `cad/` **deliberately differs** from
  Onshape: the mark is fitted to the lid instead of drawn at one or two fixed
  sizes. Two constants in `cad/parts/lid.py` are the whole policy.
- A mark is either a DRAWING (`logos/<Game>/*.dxf`, scaled) or GENERATED
  (`cad/marks.py`, built from the font and the geometry hung off it, so its
  strokes do not scale). `cad/marks.py` is the one interface over both; only
  Innovation's plain mark is generated so far. A generated name starts `@`.

- The **TokenHolder** is Dominion-only and, alone so far, its 18 cached
  components ARE a regression target rather than a shape reference: the part
  did not change in 7.0, so only the engraved version string differs. FULL and
  HALF are one part at two depths, and "merged" means the mat merges two front
  slots so the tray gets both — `HorizontalSlots` cancels out of its width.
- `cad/derive.py` is a transcription of the Onshape variable studio and is the
  **only** place a formula lives. `#BoxWidth` is the one SKETCH variable in it,
  because `calTokenHolderSlotWidth` is written in terms of it;
  `parts/box.box_width` reads it back. Component modules read a frozen `Derived` and
  never recompute. `spec/DERIVED.md` is the record.
- `individual/<Game>/` is now also the **regression corpus** — 242 components
  and 68 raw assemblies that cannot be re-fetched at any sane budget. The
  rebuild writes to `build/`, never over it.
- Two holders have **no cached mesh at all** — `Holder M-21-r6-{Un,Sl} (first)`
  was never exported — so the two `M6.21.10-12` cascades are skipped by name
  unless you pass `--holder source`. Substituting the STANDARD holder would put
  a part of the wrong depth under the fit test, which is why it is not done.
- **`cad/` builds 7.0 geometry only** and `pusher.build` refuses any other
  version. `individual/` is a mixed catalogue — every pusher and lid is now
  7.0 after the September refreshes, but **30 of its 50 holders** and four
  toppers are still older — and those stay
  Onshape's until their cascades migrate; `build/` is the migration target, not
  a mirror. The holders are the awkward case: all 50 are RECORDED at 6.6 and
  the studio changed under them without a version bump, so provenance cannot
  see it — the two lengths coexist deliberately (`automation/PIPELINE.md`,
  "An unversioned CAD change"; `spec/HOLDER.md`).
- **Every text placement is floored** (`cad/text.py`, "floors"): no engraved
  stroke under 0.200 mm, nothing proud or inlaid under 0.250. A line under
  its floor is raised and gives up margin; `tests/test_text_floors.py` holds
  the whole catalogue to it and names the sixteen lines it raises. A
  second-filament inlay in a pocket printed face down is CUT text — the
  topper's names — however proud the sketch stands it (`spec/TOPPER.md`).
- **A written 3MF must be a closed, manifold mesh** — a slicer takes a hole or a
  doubled edge as far as a failed print, and OCCT will produce one where two
  faces meet tangentially. `mesh3mf._drop_flaps` is one guard; `mesh3mf.faults`
  is the other, and `mesh3mf.write` REFUSES a body with an open boundary.
  `tests/test_build_meshes.py` runs it over all of `build/`, and every body
  passes it. The two faults it found are both fixed: the twelve open lid
  inlays were a stale cached triangulation (`mesh3mf.triangulate`), and the
  three sleeved Innovation boxes' line contact — a hanging hole's edge landing
  on a divider face — is cleared by `box.HOLE_CLEAR` — `spec/HOLDER.md`, "Two
  faults it does NOT fix"; `spec/BOX.md`.
- Build one: `.venv/bin/python -m cad.build --part box --model <model code>`;
  every pusher is the bare `python -m cad.build`, and `--part all` does the
  lot in about FIVE MINUTES: builds run in a process pool (`--jobs`, every
  core by default) and a stamp beside each file skips it on a rerun when
  nothing it depends on changed (`--force` overrides). `--part tokenholder`
  is 22 files (22, not `individual/`'s 18: the old dedup key drops the size
  letter the tray has engraved on it, so two cascades ship a tray labelled
  for the other — `spec/TOKENHOLDER.md`). Serially a box builds in 5-7 s, a
  holder in 1.5, a pusher in 3, and a LID costs whatever its mark costs —
  2 s for Dominion's 459 edges, 13 for Compile's 1885 — with meshing at
  0.01 mm adding 3-12 s to each of them.
  Artwork lifted from a STEP has far fewer edges than the same mark lifted
  from a cached mesh, so a STEP is worth asking for.
- Tests: `.venv/bin/python tests/run_all.py` runs every suite below in order
  and says which failed (`--quick` skips the slow ones, `--only holder,lock`
  picks). One at a time: `python3 tests/test_derive.py` and
  `python3 tests/test_lock.py` (pure arithmetic, system python is fine; the
  second holds the three copies of the C1-C5 table to each other),
  `.venv/bin/python tests/test_pusher.py` (source vs the hand-exported
  STEPs — a missing reference is a FAILURE, not a skip),
  `.venv/bin/python tests/test_pusher_regression.py` (the written 3MFs vs
  `individual/`; run `python -m cad.build` first),
  `.venv/bin/python tests/test_box.py`, `.venv/bin/python tests/test_lid.py`,
  `.venv/bin/python tests/test_token_holder.py` and
  `.venv/bin/python tests/test_topper.py` and
  `.venv/bin/python tests/test_holder.py` (source vs their STEPs), and
  `.venv/bin/python tests/test_lid_corpus.py`,
  `.venv/bin/python tests/test_box_corpus.py` (all 48 cached boxes AND the 50
  written ones against the placement rules, by ray — `tests/probe.py` — with
  the three deliberate divergences asserted from both ends; needs `--part
  box` built),
  `.venv/bin/python tests/test_token_holder_corpus.py`,
  `.venv/bin/python tests/test_topper_corpus.py` and
  `.venv/bin/python tests/test_holder_corpus.py` (against all 44 cached lids,
  all 18 cached token holders, all 48 cached toppers and all 50 cached holders;
  the last one needs `--part holder` built first and takes about a minute,
  pooled: it builds each holder once blank and prices the `CC 6.6` engraving
  by intersection to compare like for like), and
  `.venv/bin/python tests/test_build_meshes.py` (every body in `build/` is a
  closed surface; line contacts listed, open boundaries fail).
- `.venv/bin/python -m cad.render build/*/*.3mf --contact tmp/contact.png`
  draws the lot on one sheet when you want to LOOK at a build.
- **Assemblies** put the parts into a whole cascade — `closed`, `closed-lid`,
  `play` — and are the only thing that checks the MECHANISM rather than a part.
  `python -m cad.assemble --model <code> --state all` writes
  `build/assemblies/<Game>/`; `python -m cad.fit --model <code>` measures
  interference and margins (`--no-solids` for the margin tier, which is
  seconds); `python -m cad.render <assembly>.3mf --assembly` draws the six
  named views plus a perspective hero. `tests/test_assembly.py` runs the margin
  tier over all 50 cascades. `cad/assembly.py` is the ONLY place a placement
  lives, as `derive.py` is for formulae; `spec/ASSEMBLY.md` is the record.
- **Two renderers, and they are not a before and an after.** `cad/render.py` is
  DIAGNOSTIC — flat colours, no shadows, because that is what shows a tab in a
  cutout. `render/cascade.py` is photoreal, runs in **Blender 5.x's own python**
  (so it cannot import `cad`; the handoff is a `.glb` from `cad/gltf.py`), and
  is for imagery. Cycles on Metal for an M1. `spec/RENDER.md` is the record, and
  it holds the colour rule: bodies are filament 1, inlays filament 2, and a
  plate-level filament change is `--part NAME=#HEX` and not a slot. `bpy` is NOT
  in requirements.txt — it was installed once to test the script; the Blender
  app is what runs it.
- A **render is part of the checking, not the output of it.** A closed lid goes
  on EITHER WAY ROUND — both turns measure 0.0000 mm3 and both seat the closing
  bump — so only the logo can tell, and **three of the four games' lid marks
  WERE 180 degrees from the fourth** until Dominion's drawing was turned on
  2026-09-04 (`spec/LID.md`); the 24 cached Dominion lids still have the old
  turn. One game read upside down whichever way the lid went on, on the
  shipped product as much as in `cad/`. Look at the pictures; no number sees
  this.

## Ground rules

- **Use `.venv/bin/python`**, never system python (build123d + Onshape deps).
- **Onshape API budget is ~2500 calls per YEAR** (`automation/onshape_api_log.csv`
  has the running total). Every export path defaults to a 0-call dry run —
  keep it that way, and never re-fetch what `individual/<Game>/_raw/` can
  re-split. Deduplication is why the budget works, not an optimisation.
- **`cd` is blocked by a hook.** Use absolute paths, `git -C`, `PYTHONPATH=`.
- Paths contain spaces — quote them.
- Label generation takes minutes per game. Run it in the background.
- Commits go straight to `main`, with a message body that explains *why* and
  what was verified. Match the existing log's depth.

## Facts that are easy to get wrong

- `parts.csv` W/D columns are the **assembled, closed cascade** — the lid's
  outer size. The box is lid − 2.00 mm on both axes. `verify.check_lid` holds
  a lid to 0.2 mm of its row; `check_box`'s depth tolerance is 1.2 mm and
  proves much less.
- **The CAD is the authority on a box's model code**, not `parts.csv`.
- A **Lid 3MF carries more than the lid**: the logo pattern's inlays are
  separate objects in it (up to 31), and the lid body is the biggest one. The
  same is true of the hand-exported Lid STEPs, and `cad.build` writes them the
  same way — `Lid`, `Part 2`, `Part 3`, ...
- Every generated project carries exactly **two filament slots: white 1,
  black 2**, and `wall_generator: arachne` (forced by
  `make_cascade.PRINT_SETTINGS` on every path).
- **Never re-save a project in Bambu Studio to fix a MakerWorld rejection** —
  that converts a rejected upload into a failed verification. Use
  `automation/filaments.py --makerworld`.
- On the **dual-nozzle H2C the two extruders reach different parts of the bed**
  (only x 25..325 is common), and the prime tower is purged into by both — so a
  two-filament plate, i.e. any lid plate, can slice into unprintable space and
  be rejected on upload. `automation/towers.py` checks and repairs it. Studio's
  3D view shows nothing; only slicing does — `BambuStudio --slice 0 --outputdir
  <dir> <project.3mf>`, then `result.json` `return_code` must be 0.
- The big `.config` files are Studio JSON: sorted keys, 4-space indent. Edit
  values, don't re-dump with different formatting.
- `refresh_cascades.py` refreshes existing cascades; it **cannot first-build**
  one (both modes write in place). New cascade = `make_cascade.py` called
  directly with a donor project, and the donor needs at least as many
  instances of every object as the new box — `--count` only ever drops.
- FCM's project filenames are deliberately non-canonical. **Never run
  `--standardize-names` on FCM.**
- `Status` in `parts.csv` is informational except `Parked`, which skips the
  row. FCM records published rows as `Pub 6.5`, Dominion as `Published`.

## Verify, don't assume

Both toolchains have real guards (`automation/verify.py`,
`filaments.py --check`, `make_cascade`'s layout refusals). When something
passes, check what the tolerance actually proves before reporting it as
confirmation.
