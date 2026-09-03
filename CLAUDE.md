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
**TokenHolder** and **Holder** are done — the Lid including the logo pattern in
its underside for all four games (`logos/<Game>/*.dxf`; `spec/LID.md`), the
TokenHolder in both its FULL and HALF configurations (`spec/TOKENHOLDER.md`),
the Holder to `+0.007%` of all ten references once its intended text
divergence is set aside (`spec/HOLDER.md`). Only the **Topper** still comes from
Onshape, and the whole `automation/` pipeline is still live and authoritative
for a cascade.

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
- **`cad/` builds 7.0 geometry only** and `pusher.build` refuses any other
  version. `individual/` is a mixed catalogue — 14 of its 32 pushers, 19 of its
  44 lids and **30 of its 50 holders** are still older — and those stay
  Onshape's until their cascades migrate; `build/` is the migration target, not
  a mirror. The holders are the awkward case: all 50 are RECORDED at 6.6 and
  the studio changed under them without a version bump, so provenance cannot
  see it — the two lengths coexist deliberately (`automation/PIPELINE.md`,
  "An unversioned CAD change"; `spec/HOLDER.md`).
- **A written 3MF must be a closed, manifold mesh** — a slicer takes a hole or a
  doubled edge as far as a failed print, and OCCT will produce one where two
  faces meet tangentially. `mesh3mf._drop_flaps` is the guard and
  `tests/test_holder_corpus.py` checks it, but only over the holders, which are
  clean. **Three Innovation boxes and twelve Innovation lid inlays are NOT** —
  see `spec/HOLDER.md`, "Two faults it does NOT fix". Onshape's own 850 bodies
  have none of it, so it is the writer's to fix.
- Build one: `.venv/bin/python -m cad.build --part box --model <model code>`;
  every pusher is the bare `python -m cad.build`, and `--part all` does the
  lot. `--part holder` is 56 files at about three seconds each. `--part tokenholder`
  is 22 files in seconds (22, not `individual/`'s 18: the old dedup key drops
  the size letter the tray has engraved on it, so two cascades ship a tray
  labelled for the other — `spec/TOKENHOLDER.md`). A box takes about
  ten seconds and a pusher under one; a LID costs whatever its logo artwork
  costs, because every region of the mark is its own boolean — 17 s for
  Dominion's 459 edges, 57 s for Compile's 1885. Run all 50 in the background.
  Artwork lifted from a STEP has far fewer edges than the same mark lifted
  from a cached mesh, so a STEP is worth asking for.
- Tests: `python3 tests/test_derive.py` (pure arithmetic, system python is
  fine), `.venv/bin/python tests/test_pusher.py` (source vs the hand-exported
  STEPs — it skips a reference that is absent),
  `.venv/bin/python tests/test_pusher_regression.py` (the written 3MFs vs
  `individual/`; run `python -m cad.build` first),
  `.venv/bin/python tests/test_box.py`, `.venv/bin/python tests/test_lid.py`,
  `.venv/bin/python tests/test_token_holder.py` and
  `.venv/bin/python tests/test_holder.py` (source vs their STEPs),
  and `.venv/bin/python tests/test_lid_corpus.py` /
  `.venv/bin/python tests/test_token_holder_corpus.py` /
  `.venv/bin/python tests/test_holder_corpus.py` (against all 44 cached lids,
  all 18 cached token holders and all 50 cached holders; the last one needs
  `--part holder` built first and takes about four minutes).
- `.venv/bin/python -m cad.render build/*/*.3mf --contact tmp/contact.png`
  draws the lot on one sheet when you want to LOOK at a build.

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
