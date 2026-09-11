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
  `7.1` (locked 2026-09-10, `CURRENT`). A version is an opaque STRING — nothing
  parses one; order is position in `RELEASES`.
- A release change reaches a part as a **named flag** —
  `if d.rev.thick_floor:` — never as a version comparison. Each flag has a
  `since`; `tests/test_revisions.py` needs a case for every flag.
- **The next design change opens `7.2a`**, not `7.1e`. Steps: `spec/REVISIONS.md`,
  "Adding the next release". `7.2` stays off the line until its lock, and
  letters are never removed — a version that was printed must stay buildable.
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
- The two `M6.21.10-12` cascades have no cached holder mesh: `cad.assemble`
  skips them unless `--holder source`.

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
