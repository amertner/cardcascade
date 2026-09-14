# Card Cascade

3D-printed card storage boxes ("cascades") for board games, plus the box
labels. Everything here generates printable 3MF projects.

## Where things are

| | Labels | **Cascades — `cad/`** | Onshape — LEGACY |
|---|---|---|---|
| Entry point | `labelmaker.py` | `python -m cad.build`, then `python -m cad.cascade` | `automation/refresh_cascades.py` |
| Geometry from | build123d | build123d, locally, zero API calls | Onshape, exported via API |
| Config | `cc.cfg` | `automation/parts.csv` | `automation/parts.csv` |
| Read first | `README.md` | `cad/README.md`, `spec/` | `automation/PIPELINE.md` |
| Output | `cascades/<Game>/labels/` | `build/` (gitignored); a release is copied into `cascades/<Game>/` | `spec/reference/shipped-7.0/` (frozen) |

**Posters** (the MakerWorld description PNG beside every project):
`make_posters.py`, spec `posters.json`, photos `photos/<Game>/` (see its
README), Dominion set glyphs `logos/Dominion/sets/` (`fetch_set_icons.py`).
Every number is the CAD's; the layout is data in the spec, not code. Output
`build/cascades/<Game>/<tracked name>.png`; `--render` gives an unphotographed
cascade a Blender render (~30 s each, cached in `build/posters/`) of the scene
`cad.scene` dresses: lid colour per row, a label in the holder, and the game's
cards in the slots when `render.stacks` is on (`posters.json`, `render`; off
since 2026-09-13). Figma
(`figma-plugin/`, `figma_export.py`) is LEGACY, replaced 2026-09-13.

**`cad/` is the authority for all work** (Allan, 2026-09-06). Every part is
written there — Pusher, Box, Lid, TokenHolder, Topper, Holder — and
`cad.cascade` takes a parts.csv row to a Bambu Studio project with no donor and
no API. A geometry question is answered by building it. `cascades/` holds the
cad-built **7.1** release (tag `v7.1`, 2026-09-11).

**The Onshape pipeline is LEGACY: kept runnable, not used.** Do no new work in
`automation/refresh_cascades.py` / `make_cascade.py` and do not change it to
follow `cad/`. It stays because what it produced is the regression corpus:
`individual/<Game>/` (cached components that cannot be re-fetched at any sane
budget) and `spec/reference/` (hand-exported STEPs, and `shipped-7.0/`, the
projects Onshape shipped). `tests/reference.py`, `cad.compare` and
`tests/test_parallel.py` hold a 7.0 build to them. **Never delete or write over
either.** `PIPELINE.md` is that pipeline's design record; some of its sections
(process settings, engraved versions) still govern cad output.
`automation/verify.py`, `filaments.py` and `towers.py` are NOT legacy — they
check cad output.

## Releases — `cad/revisions.py`, `spec/REVISIONS.md`

- `RELEASES` is an ordered line: `7.0` (the Onshape generation), `7.1a`..`7.1d`,
  `7.1` (locked 2026-09-10, the release in `cascades/`), `7.2a`, `7.2b`,
  `7.2c`, `7.2d`, `7.2e`, `7.2f` (open 2026-09-14, `CURRENT`, what `build/` is). A version is an opaque STRING —
  nothing parses one; order is position in `RELEASES`.
- A release change reaches a part as a **named flag** —
  `if d.rev.thick_floor:` — never as a version comparison. Each flag has a
  `since`; `tests/test_revisions.py` needs a case for every flag.
- **7.2f is open** with two flags, `ribs_forward` and `shorter_box`,
  PROTOTYPES iterated on Allan's prints of `cad.testkit`'s kits (may be
  revised or withdrawn);
  `7.2e` carries `seated_lips`, `7.2d` `plain_box_plate`, `7.2c`
  `larger_lid_text`, `7.2b` `unmarked_lid` and `7.2a` `rear_holder` (the
  `low_profile` change it was opened for was withdrawn, 2026-09-13). **The
  next design change opens `7.2g`.** Steps:
  `spec/REVISIONS.md`, "Adding the next release". `7.2` stays off the line
  until its lock, and letters are never removed — a version that was printed
  must stay buildable.
- A row whose parts.csv `Plain box` is TRUE (Compile's three) ships a
  **second box without label holders** on the LAST plate from 7.2d
  (`build.ships_plain_box`, the only place the flag is asked;
  `build.plain_box_twin` for its Derived; object `PlainBox`, plate `Box
  without label holders`). An alternative to plate 1's box, not a part of
  the assembly.
- **Every lip seats** from 7.2e (`spec/HOLDER.md`, "Lips that seat"): the
  slant is the diagonal `calHeightIncrement / sliderDistance`
  (`derive.cascade_slope`), a lip reaches the gap plus one wall in Y
  (`holder.lip_reach_y` 1.200; the box's 2.050), and the rest is notched
  through the whole front wall, `holder.rest_depth` deep — read
  `assembly.front_holder_gap` / `box_lip_seat`, never 1.250 or 85.5. `cad.fit
  --state play` intersects every holder and reports each lip's seat.
- **From 7.2f the front holder is 0.400 from the panel** (`box.rib_shift`,
  derived from the depth), **the box and lid are `calRearTrim` 1.400
  shallower** (parts.csv's D columns follow) with the rearmost holder 0.400
  from the back wall, and **the lid's sockets follow the ribs**
  (`lid.socket_back`) so a holder is centred on its tread. The box lip is a
  tapered block biting the front holder's wall by `box.LIP_BITE` (0.150,
  inside the rib slack), its tip `LIP_SINK` under the holder's slant, on a
  post at `box.lip_z` — read the functions, never the constants. **A holder
  goes in straight down its ribs, so no fixed lip may fill its wall's
  footprint**: `cad.fit --state closed` sweeps the front holder onto its
  seat. `spec/BOX.md`, "The ribs move forward" and "The box loses the room
  behind the last holder". Test prints: `python -m cad.testkit` writes
  one-slot kits to `build/testkits/`.
- Every cascade ships an **unmarked lid** on a plate of its own from 7.2b: no
  mark in the underside and `(C) Mertner` (`lid.CREDIT`) where the game's
  name is. A lid is one of three `tables.LID_VARIANTS`; `build.lid_variants_built`
  says which a release ships, and it is the only place the flags are asked.
- The Lid's three-line text block is **scaled up where the lid has room**
  from 7.2c (`lid.text_scale`, at most `TEXT_SCALE_MAX` 1.5): anchored at
  its cap top and right edge, a line gap from the Card Cascade block, which
  does NOT scale. Read `lid.text_anchor`/`text_room`, never the constants.
- Every cascade's rearmost holder is a **`RearHolder`** from 7.2a: the same
  holder without rear lips (`holder.build(..., rear=True)`), replacing one
  plain Holder, or the FirstHolder itself where `Deep slot` = back. Which
  riser: `assembly.rear_of`; the kinds a cascade is built from:
  `assembly.holder_kinds`.
- **A row can carry its own options** without a flag: parts.csv's `Deep
  slot`, `Sleeved card width` and `Toppers` columns (below). 7.2a holds
  the `Three Expansions` row and those.
- A release change is not a **divergence** (cad against Onshape at the same
  version). The deliberate divergences: the Lid logo is fitted to the lid
  (`LOGO_*` in `cad/parts/lid.py`, `spec/LID.md`), and the Holder's slot mouth
  is chamfered (`spec/HOLDER.md`).
- Parts go in a tree per release: `build/` is `CURRENT`, `build/v7.0/` any
  other (`cad.build --version 7.0` needs no `--out`).
- **Every test that compares against a reference pins 7.0**, including
  `cad.compare` and `test_parallel.py` — from 7.1 a twin is MEANT to differ.
  They need `cad.build --part all --version 7.0`.
- A part states its release twice: engraved `CC 7.1` and `CardCascade:Version`
  metadata (the glyph cannot show a letter). `automation/verify.py --stamps
  --tree build` checks both; run it before publishing.

## Build, test, release

- `.venv/bin/python -m cad.build --part all` — every part, ~3 min, skips what
  is unchanged (`--force`). One part: `--part box --model <code>`. Full command
  list: `cad/README.md`, "Run it".
- `.venv/bin/python tests/run_all.py` — every suite, concurrently (`--quick`,
  `--only holder,lock`, `--build` builds `build/` first, which the corpus
  suites need).
- `python -m cad.cascade` writes `build/cascades/<Game>/` (`--slice` runs a
  Studio slice); `--publish` writes `build/dist/<version>/` with the version in
  the file names, for the GitHub Release.
- Releasing: regenerate, `verify.py --stamps --tree build`, copy
  `build/cascades/` into `cascades/<Game>/`, tag `v<version>` (see `c1c5130`).
- `cad.assemble` / `cad.fit` / `cad.render` check the MECHANISM, not a part
  (`spec/ASSEMBLY.md`). `render/cascade.py` is the photoreal renderer and runs
  in Blender's python, so it cannot import `cad` (`spec/RENDER.md`).

## Geometry that is easy to get wrong

- **The Box's FLOOR is not its WALL**: any Z datum on the floor reads
  `box.floor_top(d)` (2.000 from 7.1), not `WallThickness` (1.600). The Lid's
  floor stays 1.600.
- Read `box.rear_thumbs_x`, `box.hole_w`/`hole_rows` and
  `holder.window_w`/`window_rows` — never the constants, never re-derived.
- `cad/derive.py` is the ONLY place a studio formula lives (parts read the
  frozen `Derived`); `cad/assembly.py` is the only place a placement lives.
- Every text placement is floored (`cad/text.py`): no engraved stroke under
  0.200, nothing proud or inlaid under 0.250.
- A written 3MF must be a closed manifold mesh; `mesh3mf.write` refuses an open
  boundary, and `tests/test_build_meshes.py` checks all of `build/`.
- A Lid 3MF carries its logo inlays as separate objects (`Lid`, `Part 2`, ...);
  the body is the biggest.
- A mark is DRAWN (`logos/<Game>/*.dxf` or `*.brep`) or GENERATED
  (`cad/marks.py`, name starts `@`); `cad/marks.py` is the interface to both.
- **A printed lid is the authority on the logo's orientation, not a render** —
  a closed lid fits either way round. Dominion's DXF is Onshape's original and
  Innovation's mark is turned (`tables.LID_LOGO_TURNED`), both checked on
  printed lids; Compile and FCM are open until printed (`spec/LID.md`).

## Ground rules

- **Use `.venv/bin/python`**, never system python.
- **`cd` is blocked by a hook.** Use absolute paths, `git -C`, `PYTHONPATH=`.
  Paths contain spaces — quote them.
- **Onshape API budget is ~2500 calls per YEAR** (`automation/onshape_api_log.csv`).
  Exports default to a 0-call dry run; there is no routine reason to spend a
  call now, so ask first.
- Label generation takes minutes per game. Run it in the background.
- Commits go straight to `main`, with a body that explains *why* and what was
  verified. Match the existing log's depth.

## Facts that are easy to get wrong

- `parts.csv` W/D is the **assembled, closed cascade** (the lid's outer size);
  the box is lid − 2.00 mm on both axes. `Status` is informational except
  `Parked`, which skips the row.
- **The CAD is the authority on a box's model code** (`derive.calModelName`),
  not `parts.csv`.
- A topper's cached name is Onshape's three-key (size, cards per slot,
  sleeving), NOT the model, while its slant follows the rise: a row that
  shares the key with another but not the rise sets parts.csv's `Toppers`
  column to `none` (`build.ships_toppers`) or it builds over the other's
  toppers. `M8.16.10-16` against `M5.10.10` is the case.
- parts.csv's `Sleeved card width` states one row's sleeved card width
  outright where the studio adds 2 to the game's (`derive`, `calCardwidth`);
  `Three Expansions` uses 64 so its sleeved twin is 286.9 wide like its
  unsleeved one. A row property, not a release flag.
- parts.csv's `Deep slot` = `back` puts a row's deeper first-riser slot at
  the BACK instead of the studio's front: the back rib, the pusher's last
  drop, a standard holder at the lip (`derive.isDeepSlotAtBack`; read
  `assembly.holder_rib` for which rib the deep holder rides), and the deep
  holder itself loses its rear lips, takes the plain slant with a taller
  rear (`holder.deep_at_back`, `slant_rear`) and centres its thumb scallop on
  that taller rear (`finger_cutouts`). `Three Expansions` uses it. A row
  property, not a release flag.
- `cad.assemble --cards` draws numbered, per-expansion card stacks in every
  slot for a render (`spec/RENDER.md`, "Cards in the slots"); they go to a
  separate `... cards.3mf` and are never parts.
- Every project has exactly **two filament slots, white 1 and black 2**, and
  three forced process settings (`cad/project.py`, held equal to
  `make_cascade.PRINT_SETTINGS` by `tests/test_project.py`): `arachne`,
  `seam_position: back`, no ironing. The seam is a **FIT**: `aligned` runs it
  up the rearmost slider rib, which has no slack (`PIPELINE.md`, "Process
  settings").
- On the **dual-nozzle H2C** only x 25..325 is reachable by both extruders, so
  a lid plate can slice into unprintable space. `automation/towers.py` checks
  and repairs it; only a slice shows it — `BambuStudio --slice 0 --outputdir
  <dir> <project.3mf>`, then `result.json` `return_code` must be 0.
- **Never re-save a project in Bambu Studio to fix a MakerWorld rejection**;
  use `automation/filaments.py --makerworld`.
- Studio `.config` files are JSON with sorted keys and a 4-space indent. Edit
  values; don't re-dump.
- **A NAME is an identity, a VERSION is a release**: tracked projects carry no
  version in the file name (`components.tracked_name`), so git follows a path
  across releases. The version is in the 3MF `Title`, on the parts and in the
  tag; only `--publish` puts it in the name. `components.cascade_filename`
  holds the rule. FCM's names come from parts.csv's `Project label`.
- A box engraves its version down its depth: read it with ROTATIONS, never a
  transpose, which turns `7.0` into `0.7`.

## Verify, don't assume

`verify.py`, `filaments.py --check` and the layout refusals are real guards.
When something passes, check what the tolerance actually proves before
reporting it as confirmation.
