# Card Cascade

3D-printed card storage boxes ("cascades") for board games, plus the box
labels. Everything here generates printable 3MF projects.

## Three toolchains — work out which one you're in first

| | Labels | Cascades (the boxes) | The rebuild |
|---|---|---|---|
| Entry point | `labelmaker.py` | `automation/refresh_cascades.py` | `python -m cad.build`, then `python -m cad.cascade` |
| Geometry from | build123d, generated locally | Onshape, exported via API | build123d, generated locally |
| Config | `cc.cfg` | `automation/parts.csv` | `automation/parts.csv` |
| Read first | `README.md` | `automation/PIPELINE.md` | `cad/README.md`, `spec/` |
| Output | `cascades/<Game>/labels/` | `cascades/<Game>/` | `build/<Game>/` parts, `build/cascades/<Game>/` projects (gitignored) |

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

So no component's GEOMETRY needs Onshape any more, and since 2026-09-05 a
whole cascade does not either: **`python -m cad.cascade`** takes a parts.csv
row to a Bambu Studio project with no donor, no plan and no API —
`cad/cascade.py` composes the parts from `build/` by their engraved names,
`cad/layout.py` lays them out (make_cascade's rules, lifted; `spec/PROJECT.md`),
`cad/project.py` writes the file from the bed profile, and `filaments`,
`towers` and (with `--slice`) a Studio slice check it. Every cascade
comes through, Dominion 650 Sleeved at the H2C's limit included (its lid
fits only at 44 degrees; `layout.fit_angle`). It writes to
`build/cascades/<Game>/`, beside and not over `cascades/`: the two pipelines
run in PARALLEL, and **`python -m cad.compare`** is the scorecard — all 46
shipped projects print the same parts as their cad twins
(`tests/test_parallel.py`) — while `automation/` remains what has shipped
every cascade on disk. **Everything is 7.0 going forward** (Allan,
2026-09-05): a twin's 7.0 holders and pushers supersede the 6.6 and pre-7.0
ones in a shipped project. **7.1 is the cad-built release**: the same 7.0
geometry under a `CC 7.1` stamp (`lock.SAME_GEOMETRY`), so a cad-built
cascade can be told from an Onshape-exported one on the shelf — and, since the
version went into the project name, in the file too (`... Sleeved v7.1 (...)`).
A set at a version goes in its own tree — `cad.build --version 7.1 --out build/v7.1`,
then `cad.cascade --version 7.1 --components build/v7.1 --out
build/v7.1/cascades` — and the defaults stay 7.0, which is what every
reference STEP and cached mesh is stamped. `verify.py --stamps` does not
know 7.1's glyph signature yet and reads a 7.1 part as unreadable. The older route — `python -m cad.promote` staging built parts under
the planner's names for `refresh_cascades.py --components` — still works for
all but four token holders (`spec/TOKENHOLDER.md`'s size-letter collision)
and is what the layout module was checked against. Nothing from `build/` has
been printed yet.

- The Lid's logo is the one place `cad/` **deliberately differs** from
  Onshape: the mark is fitted to the lid instead of drawn at one or two fixed
  sizes. Two constants in `cad/parts/lid.py` are the whole policy.
- A mark is either a DRAWING (`logos/<Game>/*.dxf`, or `*.brep` where it is
  lifted from a STEP and a DXF would re-fit its splines; scaled) or GENERATED
  (`cad/marks.py`, built from the font and the geometry hung off it, so its
  strokes do not scale). `cad/marks.py` is the one interface over both; both
  Innovation marks are generated, the Ultimate one at its two published sizes
  (`spec/LID.md`). A generated name starts `@`.

- The **TokenHolder** is Dominion-only and, alone so far, its 18 cached
  components ARE a regression target rather than a shape reference: the part
  did not change in 7.0, so only the engraved version string differs. FULL and
  HALF are one part at two depths, and "merged" means the mat merges two front
  slots so the tray gets both — `HorizontalSlots` cancels out of its width.
- `cad/derive.py` is a transcription of the Onshape variable studio and is the
  **only** place a VARIABLE-STUDIO formula lives. Two SKETCH variables live
  there too — `#BoxWidth`, because `calTokenHolderSlotWidth` is written in
  terms of it, and `#calPusherSlots`, because three modules read it — and so
  do the two part-studio formulas two parts share (`cascade_slope`,
  `back_slot_pitch`). A part-studio formula one part uses stays in that part,
  once. Component modules read a frozen `Derived` and never recompute.
  `spec/DERIVED.md` is the record.
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
  lot in about THREE MINUTES on this laptop and 97 s on a quiet 14-core
  machine: every kind's jobs go through ONE process pool, longest first, one
  worker per core (`--jobs`), each meshing single-threaded, and a stamp
  beside each file skips it on a rerun when nothing it depends on changed
  (`--force` overrides). `--part tokenholder`
  is 22 files (22, not `individual/`'s 18: the old dedup key drops the size
  letter the tray has engraved on it, so two cascades ship a tray labelled
  for the other — `spec/TOKENHOLDER.md`). Serially a box builds in 6-9 s, a
  holder in 1.5, a pusher in 3, and a LID costs whatever its mark costs —
  2 s for Dominion's 459 edges, 11-13 for Compile's 1885. Meshing adds under
  a second to any of them since 2026-09-05; it used to add 3-17 s, all of it
  spent iterating OCCT's triangle array through OCP (`mesh3mf.triangulate`).
  The booleans are the cost now: a box's 16 cuts, a lid's mark pocket.
  Artwork lifted from a STEP has far fewer edges than the same mark lifted
  from a cached mesh, so a STEP is worth asking for.
- Tests: `.venv/bin/python tests/run_all.py` runs every suite below — several
  at a time within a core budget, longest first, so 33 minutes of suites take
  about 8 — and says which failed (`--quick` skips the slow ones, `--only
  holder,lock` picks, `--jobs 1` runs them one at a time in table order). One at a time: `python3 tests/test_derive.py` and
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
  `.venv/bin/python tests/test_lid_marks.py` (every drawn lid mark's thinnest
  stroke at every scale the fit picks, held to the cut floor — Compile's is
  0.250 mm at its drawn size),
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
- **A component's ENGRAVED version and its RECORDED version come from different
  places** — Onshape's `Version` primary (`set_variables.build_primary`) against
  `onshape_config.expected_version()` — and they drifted once: 36 of the 128 boxes,
  lids and pushers carried 7.0 lock geometry under a `CC 6.6` stamp, which is
  how a 7.0 pusher gets printed for a 6.6 lid it cannot enter. All 14 cascades
  were re-exported on 2026-09-05 and the catalogue now reads clean. The stamp is the
  only thing a person holding the part can read, so it is not cosmetic.
  `python3 automation/verify.py --stamps` reads the engraving off every box, lid
  and pusher and checks it against the cascade's generation (~50 s for all 128);
  `export._write` refuses a mismatch. A box engraves its version down the depth, so the reader
  turns the plane — with ROTATIONS, never a transpose, which reads the line
  backwards and turns `7.0` into `0.7`. `automation/PIPELINE.md`, "The engraved version is not the
  recorded version".
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
- **A project's name carries its VERSION** — `Dominion 168 Card Sleeved v7.0
  (S4.16.10.32-Sl).3mf` (`components.cascade_filename`, the one place the rule
  lives; the argument is required, not optional). On the Onshape path it is the
  cascade's GENERATION (parts.csv `Build`, blank = CURRENT), which does NOT mean
  every part reads it: `7.0` is Box/Lid/Pusher 7.0 and Holder/Topper/TokenHolder
  6.6, and `290 Card (Mat)` is pinned `6.6` and named so. On the cad path it is
  `p.Version` and every part really is at it. The name is also the 3MF `Title`
  and the tail of every plate name.
- FCM's filenames are its own scheme — `FCM Occ 2S v7.0 (180 Card
  L3-18-6-20-Sl).3mf`, *the 2nd box for Occupations, sleeved* — but they are
  GENERATED now, from parts.csv's `Project label` column (`Occ 2`,
  `Milestones 1`, `Alt`), so `--standardize-names` covers FCM too. The label is
  a column and not a rule read off `Set/Extension`, because `Occupations 3` is
  the alternative single-box split and ships as `Alt`.
- `Status` in `parts.csv` is informational except `Parked`, which skips the
  row. FCM records published rows as `Pub 6.5`, Dominion as `Published`.

## Verify, don't assume

Both toolchains have real guards (`automation/verify.py`,
`filaments.py --check`, `make_cascade`'s layout refusals). When something
passes, check what the tolerance actually proves before reporting it as
confirmation.
