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
generated with **zero API calls**. Only the **Pusher** exists so far
(`cad/parts/pusher.py`); Box, Lid, Holder, TokenHolder and Topper still come
from Onshape, and the whole `automation/` pipeline is still live and
authoritative for them.

- `cad/derive.py` is a transcription of the Onshape variable studio and is the
  **only** place a formula lives. Component modules read a frozen `Derived` and
  never recompute. `spec/DERIVED.md` is the record.
- `individual/<Game>/` is now also the **regression corpus** — 242 components
  and 68 raw assemblies that cannot be re-fetched at any sane budget. The
  rebuild writes to `build/`, never over it.
- **`cad/` builds 7.0 geometry only** and `pusher.build` refuses any other
  version. The 14 pushers in `individual/` still at 6.6 stay Onshape's until
  their cascades migrate; `build/` is the migration target, not a mirror.
- Build one: `.venv/bin/python -m cad.build --part box --model <model code>`;
  every pusher is the bare `python -m cad.build`, and `--part all` does both.
  A box takes about ten seconds, a pusher under one.
- Tests: `python3 tests/test_derive.py` (pure arithmetic, system python is
  fine), `.venv/bin/python tests/test_pusher.py` (source vs the hand-exported
  STEPs — it skips a reference that is absent), and
  `.venv/bin/python tests/test_pusher_regression.py` (the written 3MFs vs
  `individual/`; run `python -m cad.build` first).
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
