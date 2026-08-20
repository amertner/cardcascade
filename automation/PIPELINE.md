# Card Cascade Onshape export pipeline

Goal: from a spreadsheet of cascade parameters, scripted-export the CAD
components each cascade needs from Onshape as `.3mf`, **deduplicating** shared
components so the tiny Onshape API budget is spent only on parts that are
actually new or changed, then assemble the printable projects with the
existing `make_cascade.py`.

## Hard constraint: the API budget

The Onshape Free plan bills **~2500 API calls per YEAR** (see
`onshape_api_log.csv` for the live year-to-date total; 4xx client errors are
free). One component export costs ~3–4 calls (translate + poll + download).
Deduplication is therefore not an optimisation but the thing that makes this
viable: `M4.21.10` drives two Dominion rows, `M6.21.10` drives six — their
holders/boxes/pushers must be exported **once**, not per cascade.

## Three stages — only the middle one spends calls

```
parts.csv ─┐
           ├─▶ [1 PLAN]  plan_exports.py   → worklist + manifest.json   (0 API calls, offline)
components ─┘        │
  spec (components.py)├─▶ [2 EXPORT] (uses onshape_test.py's recipe) → individual/<Game>/*.3mf  (budget-gated)
                     │
                     └─▶ [3 ASSEMBLE] make_cascade.py driven by manifest → cascades/<Game>/*.3mf (0 API)
```

Planning and assembly are free and offline-testable; the API surface is one
small, gated stage that only fetches the deduped, missing/changed set.

## Inputs

### `parts.csv` — one row per cascade *size*
Columns (the `Horizontal … 3D printer` block are the geometry inputs):
`Short name, Base model, Unsl Model, Sleeved model, Game, Set/Extension,
Status, Horizontal, Risers, Cards/Riser slot, Cards/First Riser,
Front capacity, Box Height / mm, Merged-slot, TokenHolder, 3D printer, Notes,
Unsleeved W/mm, Unsleeved D/mm, Sleeved W/mm, Sleeved D/mm`.

**The W/D columns are the ASSEMBLED, CLOSED cascade** — i.e. the LID's outer
size, because the box fits inside the lid. Across the 33 built cascades the
relationship holds without exception: lid = parts.csv (to 0.02 mm in depth;
width rounds 270.90 up to 271.0), box = lid − 2.00 mm on both axes, the lid
wrapping the box by 1 mm a side. `verify.WALL` is that 2.00 plus the 0.1
rounding. A row that has never been built carries ESTIMATED W/D; replace them
with the lid's measurements once its CAD exists, because `check_box`'s depth
tolerance is 1.2 mm and will not tell you the estimate was off.

Decoded model code: **`<Size><Risers>.<FrontCapacity>.<Cards/RiserSlot>[/<Cards/FirstRiser>]`**;
`Unsl/Sleeved model` append `.<labelWidth>-Un` / `-Sl`. `Horizontal` = size class
(S=3, M=4, L=5). Each row yields **two cascades** (`-Un` and `-Sl`).

**The box itself is the authority on its model code** — the CAD embosses it on
the inside, and parts.csv is a transcription that can be wrong. FCM's 180
sleeved was recorded as `L3.18.6.32-Sl` when the box reads `L3.18.6.20-Sl`;
the geometry agrees with the box, since a label must sit ~14 mm narrower than
the lid's depth and the sleeved 180 lid is only 44.9 mm deep, so 32 could
never have fitted. The trailing number is a LABEL width and drives no Onshape
input, so correcting one is a rename of the Box/Lid files plus their
provenance rows — never a re-export.

### `components.py` — per-game component spec
Because naming/holder-geometry differs per game, each game declares how its
components are keyed and composed. **Components are never shared across games**
(different card dimensions/thickness), so every identity is namespaced by game
and files live under `individual/<Game>/`.

## Component composition (per cascade)

Every cascade has: **Box** ×1, **Lid** ×1, **Pusher** ×(2 or 3, identical),
and **Holders**:

- Normally `Risers` identical standard holders, each holding `Cards/Riser slot`
  cards.
- If `Cards/First Riser` is set: `Risers − 1` standard holders **plus one**
  first-riser holder of that larger capacity (replaces one standard).

**Merged-slot (Dominion mat boxes):** `TRUE` merges two of a Medium box's four
front slots into one larger pocket (for mats or the TokenHolder). This changes
the **Box** geometry only — Lid, holders and pushers are unaffected.

Game-specific additions:

| Game | Extra components | Labels |
|---|---|---|
| Dominion | Token holders per-row (`TokenHolder` column: `full`/`none`) — only sets whose expansions need them. Full holder always; every **merged-slot (Mat)** cascade also gets a HalfTokenHolder (the mat pocket always splits into full + half) | via `labelmaker.py` (not Onshape) |
| Innovation | **6 Toppers** — same dims, different embedded text (one per expansion + a blank); one whole-studio Onshape export per sleeving yields all 6 | via `labelmaker.py` |
| Compile | — | **special label with logo → from Onshape**, only when `--labels` given |
| Food Chain Magnate | — | via `labelmaker.py` |

## Dedup identity keys (what makes a component unique within a game)

`key` is the tuple of parameters a component's geometry depends on — and (will
be) the set of Onshape configuration inputs to `--set`, so it does double duty.

| Component | Key | Notes |
|---|---|---|
| Box | `(model, merged)` | merged-slot changes the box, so 202 vs 244 Card (same model) are DIFFERENT boxes |
| Lid | `model` | same footprint as box (box + 2 mm); merged doesn't change outer size |
| Pusher | `(risers, cards, sleeved)` | depends only on #risers, #cards, sleeved |
| Holder (per-slot: Dominion/FCM) | `(size, front_capacity, sleeved, first=False)` | sized by the box's front pocket — 202 (M-21) ≠ 400 (M-40) even at equal cards/slot; `(size, front cap)` fixes cards/slot within a game; file `Holder <size>-<cap>-<slv>`. NB Mat (`merged`) is NOT an axis: the merge combines the two rightmost FRONT-pocket slots (resizing box + token holder), but the sliding-slot holder is byte-identical Mat vs plain (verified) |
| Holder (spanning: Compile, Innovation) | `(horizontal, cards_per_slot, sleeved)` | spans HorizontalSlots — Compile 3×7/5×7, Innovation 3×15 (S) / 4×15 (M) |
| Holder (first-riser) | `(size, front_capacity, sleeved, first=True)` | deeper sibling of the standard holder in the same box; replaces one standard holder; file `Holder <size>-<cap>-<slv> (first)` |
| TokenHolder (Dominion) | `(front capacity, merged, sleeved)` | fits the box's front pocket, so it varies by capacity, Mat-ness and sleeving; file `TokenHolder <cap>-<slv>[ merged]` |
| HalfTokenHolder (Dominion) | `(front capacity, merged, sleeved)` | Mat-only; same key as the full holder |
| Toppers (Innovation) | `(sleeved,)` | one export → 6 files; shared across all Innovation cascades of that sleeving |
| Label (Compile) | `(model,)` | logo label; TODO confirm dependency |

## Incremental / change detection

- **`--changed Holder,Pusher`**: force re-export of those component types even
  if their file exists.
- Default: export only components missing from `individual/<Game>/`.
- **Freshness is opt-in.** Detecting upstream CAD changes needs one API call
  per element (read microversion); a future `--check-updates` mode does that.
  Default spends **zero** calls on anything already cached.
- A sidecar `individual/<Game>/.export_state.json` will record, per file, the
  Onshape element + configuration + document microversion it came from
  (idempotency + audit). *(Stage 2.)*

### `_raw/` — what a cached download is for

`individual/<Game>/_raw/` keeps downloads that hold **more than the component
file does**, so a part that was dropped or re-keyed is recovered by re-splitting
locally instead of re-fetching:

- **Assemblies** always qualify — one download carries Box, Pushers, Holders and
  the token holders, and `--use-cache` re-splits it for 0 calls.
- **Studio exports** (Lid, Topper, Label) qualify only when stripping imports
  actually removed something, e.g. the Topper studio's imported Holder. A Lid
  studio strips nothing, so its raw *is* the component — `export_studio` caches
  the download before the write (a refused export never costs its bytes) and
  deletes it after a clean write when nothing was stripped. The 16 lid raws that
  predated this rule were the same 3MF stored twice, 9.8 MB, and are gone.

### Updating a component by hand

Onshape's UI export sometimes beats the scripted path — a part re-downloaded
manually is updated by **overwriting `individual/<Game>/<component>.3mf` in
place**, then:

```
export.py <Game> --adopt          # re-record provenance from disk (0 calls)
refresh_cascades.py --game <Game> --name '<Short name>' --sleeving un|sl
```

`--adopt` re-records a component whose version is stale **or whose bytes changed
under it** — the `sha` is what the identity guard reads, so a silent
disagreement between disk and provenance would disarm it. Staging the download
in `_raw/` under the component's filename and running `export.py --use-cache`
does the same thing through the normal export path (it also re-strips imports),
which is the better route for a studio whose export carries parts to strip.

**Scope `--adopt` with `--types`.** Adopting a whole game blesses *every*
version-stale component as current, including ones whose geometry really is out
of date — Dominion's boxes and holders are still 6.4 awaiting a real upgrade, so
a bare `export.py Dominion --adopt` would record them as 6.5 and they would
never be re-exported. `--types Lid` restricts it to what you actually verified.

`--name` and `--sleeving` narrow it further, to the components of ONE cascade,
and they mean the same thing on the adopt path as on the export path (one
`selected()` helper serves both). Type alone is too coarse when a type is
mid-upgrade: after the 6.5 token-holder change, `--types TokenHolder` would have
blessed all 14 Dominion token holders when exactly one — the 168 sleeved, split
from the updated assembly — had earned it.

The version a component should carry — `VERSIONS` plus per-file exemptions like
Innovation's Blank topper — comes from `onshape_config.expected_version()`, and
both the staleness check and every provenance write must go through it. When
they disagree, a component is recorded at a version the check never expects and
goes stale the moment it is written.

The element a component is recorded against comes from
`onshape_config.source_element()`, for the same reason: `ELEMENTS` carries a
standalone part studio for Box/Holder/Pusher/TokenHolder as well as the
assembly, so reading it directly attributes an assembly-split part to a studio
it never came from. Only `--adopt` ever got this wrong, and only for
assembly-sourced types — its previous callers were all `--types Lid`, which
`ELEMENTS` answers correctly.

### Verifying a bulk re-export — diff the mesh, don't trust the version

`individual/` is committed, so `git show HEAD:<component>` is a free before-image
and the only honest way to check that a sweeping re-export did what was
intended. Measure per-FACE (min and max of each axis), not the span: a span
folds a real design move together with tessellation drift and hides both.

Two numbers make the check readable. A **design change lands on exactly one
face, at a round value** — the 6.6 holder fix moved `Y-min` by −0.4000 mm on 31
of 35 holders, to four decimals, every time. **Tessellation drift is 0.01–0.07
mm and sits on curved faces**, recognisable because the coordinate is non-round
both before and after (a holder's `Y-max` fillet reads 0.8867 → 0.9486). That is
why the holders' Y SPAN reads +0.446 rather than +0.400 and why the span alone
would have looked wrong.

For a part that should NOT have changed shape, the vertex-set difference
localises what did: the 6.6 box's entire change was 155 vertices inside a
0.97 × 1.18 × 0.40 mm box — one embossed version glyph — with every face
identical to 0.0000 mm.

**Embossing is not confined to the Box and Lid.** The Pusher carries a raised
version string too, in a ~2.5 × 15.6 × 0.4 mm strip; `VERSIONS` had pinned
Pusher at 6.3 on the belief that it embossed nothing, so pushers were never
re-fetched and every one on disk still read 6.4 while its box read 6.5. If a
component is monochrome, assume it may carry the version until a vertex diff
says otherwise — it rides the assembly export anyway, so re-exporting it costs
nothing beyond the parameter set.

**The first-riser holder is separate geometry, so a holder change need not
apply to it.** `(first)` holders are driven by `FirstSlidingSlot`; a change to
the standard holder reaches them only if the CAD edit covers both. At 6.6 it
deliberately did not — the defect was in the DEFAULT holder alone, so all 31
standard holders moved 0.4 mm while all four `(first)` holders were already
correct and stayed put (`Holder M-60-Sl (first)` came back byte-identical to its
6.5 export). Expect a holder change to split along this line, and establish
which side it was meant to land on before reading an unchanged `(first)` holder
as a missed fix — the two first-riser rows (Dominion 246 `S2.40.12/30` and 472
`M2.60.18/40`) are where the distinction shows up.

### `--keep-layout` does not re-check clearance between objects

`make_cascade --keep-layout` guards a plate's total SPAN against the bed, so a
swapped mesh that outgrew its slot cannot overhang. It does not test whether
neighbouring objects still clear each other — positions are fixed, so a part
that grows eats the gap to its neighbour silently. After any dimensional change
to a repeated part, slice the affected projects: the same Studio CLI MakerWorld
runs is the ground truth, and it is cheap (~11 s for a whole project, all
plates, not the ~20 s per plate an H2C tower check costs).

```
BambuStudio --slice 0 --outputdir <dir> <project.3mf>   # 0 = every plate
```

## Build policies (decided)

- **Incomplete rows are skipped and reported** (never silently dropped). A row
  is "ready" only if `Box Height` and the four W/D dimensions are present. The
  Speculation row (`290 Card`) is currently skipped.
- **Status is informational, except `Parked`** — naming a game builds all its
  rows regardless of `Status` (Innovation is `Drafting` and still builds), but
  rows with `Status = Parked` are skipped and reported.

## Output: `manifest.json` for `make_cascade.py`

Per cascade: template, the object→file part map, and per-object counts —
translating directly to `make_cascade.py`'s `--part NAME=FILE` / `--count
NAME=N`. A first-riser holder maps to a `Holder#N=FILE` instance override
(make_cascade already supports `NAME#2=FILE` for differently-sized holders).
A thin `assemble.py` (Stage 3) turns the manifest into `make_cascade` calls.

## CLI

```
plan_exports.py <Game> [--csv parts.csv] [--changed Box,Holder,...]
                        [--labels] [--out manifest.json]
# dry-run only in Stage 1: prints cascades, the unique export worklist,
# the projected API-call budget, and skipped rows. Makes 0 API calls.
```

## Assembly plate scheme (Stage 3)

There is **no single make_cascade template per game**. Instead the assembler
builds a standard set of plates per cascade:

1. Box + Pushers
2. Lid
3. Holders
4. Toppers (Innovation only)
5. TokenHolders (Dominion only)

Each plate is sized to fit a **P1 build plate (256×256 mm)**, rotating parts to
fit where needed; if a plate still won't fit, it goes to an **H2C-size** plate.
This means Stage 3 generates the plate layout rather than reusing a fixed
template — `make_cascade.py` currently *requires* a template, so this stage will
either supply a standard per-scheme template or extend the layout code.

## Resolved (confirmed by Allan)

- Topper names = `Cities, Echoes, Artifacts, Figures, Unseen, Blank` (6, all on
  every Innovation cascade). Existing `individual/Innovation/` files use noisy
  names (`Art`/`Arti`→Artifacts, `Fig`→Figures, `unseen`→Unseen) — **git-rename
  queued.**
- Holder identity: **per-slot** holders (Dominion/FCM) are keyed `(size, front
  capacity, sleeved, first)` — the front pocket sets the holder's depth, so equal
  cards/slot boxes with different front capacity (202 M-21 vs 400 M-40) are
  DIFFERENT holders (~0.3 mm apart). Mat (`merged`) is NOT an axis: the merge
  combines the two rightmost front-pocket slots (resizing box + token holder),
  but the sliding-slot holder is byte-identical Mat vs plain. **Spanning** holders
  (Compile/Innovation) key on `(horizontal, cards_per_slot, sleeved)`.
- Pusher count = `S→2, M/L→3`, **except Innovation** where M→2 (per-game
  override `pushers` in components.py).
- Merged-slot changes the **Box** only.

## Open questions

1. **TokenHolder / Compile-label** dependencies — which Onshape config inputs
   drive them (current keys `(size, sleeved)` / `(model,)` are guesses).
2. **Onshape element ids** per component part studio (one cached `--list`
   each) — Stage 2 only.
3. `individual/Compile/` currently has **no pusher files** — assumed
   not-yet-exported, not "Compile has no pushers" (every cascade has pushers).

## Build order

1. Refactor `onshape_test.py`'s HTTP/ledger/translate layer into `onshape.py`
   (reusable `export_part(...)`). *(no API)* **← built.**
2. **Stage 1 planner** `plan_exports.py` + `components.py` — this document's
   composition + dedup, offline. **← built.**
3. Stage 2 exporter `export.py` — consume worklist, fetch misses, write state
   file. **← built.**
4. Stage 3 assembler — `make_cascade --keep-layout`, driven by
   `refresh_cascades.py`. **← built.**

## Interactive refresh — `refresh_cascades.py`

Chains all three stages for a filtered set of cascades, prompting between steps:

```
refresh_cascades.py [--game G] [--size S,M,L] [--sleeving un/sl] [--name STR]
                    [--changed Lid,Box,...]
                    [--auto] [--dry-run] [--rebuild] [--standardize-names]
```

- **PLAN** (offline) → **EXPORT** (only stale/missing; **always** confirms the
  API spend, even under `--auto`) → **ASSEMBLE** (`make_cascade --keep-layout`,
  in place, preserving each project's hand-tuned plates). `--auto` skips only the
  two offline prompts.
- **`--changed Lid`** forces a component type to re-export even though
  provenance calls it current — the only route to a component whose recorded
  version is right but whose FILE is not what you want. The adopted lids are
  exactly that: recorded 6.5, still **embossing 6.4**, because adoption blessed
  the bytes rather than re-fetching them. The selection filters bound the spend
  (`stale_keys` intersects the plan with the selected cascades), so
  `--changed Lid --name 168 --sleeving sl` re-exports one lid, not Dominion's
  twenty. An unknown type is rejected rather than silently matching nothing.
- **`--rebuild`** switches ASSEMBLE to `make_cascade --auto-plates`: regenerate
  the plate layout from the box's own project as donor (swap every mesh by role,
  normalise the token-holder object name — donors often leave it `Part 1`), with
  the bed chosen from parts.csv's `3D printer` column (**Standard→P1, Large→H2C,
  Mixed→P1 unsleeved / H2C sleeved**). This is the general "auto-build" for
  first-building a box whose only project is stale/mislabeled — it replaces the
  old per-box shell scripts.
- **A cascade with no project at all** is outside `refresh_cascades`: both its
  modes write *in place* into a project found by model code. Call
  `make_cascade` directly, donor project in, `-o` the new name out. The donor
  must carry **at least as many instances of every object** as the new cascade
  needs — `--count` only ever drops instances (`--count TokenHolder=0` sheds a
  role the new box doesn't have), and nothing can add one. FCM Milestones needs
  5 holders where FCM's own projects top out at 4, so it was built from
  **Dominion 324**, cross-game. That is safe: plate titles are regenerated from
  the `-o` name, and a project's settings carry nothing game-specific. Where the
  donor's lid has fewer lettering bodies than the new one (Dominion embosses a
  shorter model code — 7 bodies against FCM's 11), `add_body_part` clones the
  missing parts onto the lid object's default extruder, which is the lettering
  colour; check the built lid reads `{'2': 10, '1': 1}` before trusting it.
- Cascade projects are named canonically — `<Game> <Short name>
  <Sleeved|Unsleeved> (<model>).3mf` (`components.cascade_filename`, `/`→`-`);
  Innovation/Compile/Dominion match. `--standardize-names` git-renames legacy
  projects (e.g. Dominion's old `CC 400S …`) to this form.
- **The canonical name is not required.** `find_project` takes it when it
  exists and otherwise matches the **model code** the filename carries, with
  `.` folded to `-`. FCM keeps its own scheme deliberately — `FCM Occ 2S (180
  Card L3-18-6-20-Sl).3mf` is *the 2nd box for Occupations, sleeved*, which is
  how those boxes are thought about and which the canonical form can't say.
  Since a model code is unique per cascade, any naming that embeds it works
  with no per-game rule; an ambiguous or absent match is reported, never
  guessed. Do NOT run `--standardize-names` over FCM.
- ASSEMBLE maps a component to its template slot by **role**, not exact name
  (templates suffix objects: `Lid 400S`, `Topper Cities S-Un`, `TokenHolder
  Full`/`Half`, bare `Topper` = Blank). It refuses (skips + diagnoses) rather
  than half-swapping when the mapping isn't a clean bijection, when a component
  isn't on disk, or for first-riser cascades (need a `Holder#N` override).
  keep-layout cannot ADD an object, so a cascade missing a new object's slot
  (e.g. a pre-HalfTokenHolder Mat template) is skipped for manual layout.

## Process settings — `make_cascade.PRINT_SETTINGS`

Every project this repo writes uses the **Arachne** wall generator
(`wall_generator: arachne`). It varies wall width to fill the space it is
given; classic lays fixed-width walls and leaves the remainder to gap fill,
which on these boxes is precisely where the thin slot dividers and the lid
lettering are.

Setting it in `profiles/*.config` alone is not enough — a project inherits its
whole config from its donor, and the profile is only consulted when
`--auto-plates` actually *swaps* the bed. That is why the four Innovation
projects (built from an arachne donor) carried it while every other project
carried classic. `make_cascade.force_print_settings` therefore applies
`PRINT_SETTINGS` on **every** path, including `--keep-layout`, and records each
override in `different_settings_to_system[0]` — the process entry, where Studio
lists (semicolon-separated) the keys a project changed from its stock preset.
A changed key missing from that list makes Studio show the stock value while
the project prints its own.

Existing projects pick this up the next time they pass through `make_cascade`,
i.e. on any `refresh_cascades.py` run; two keys change and nothing else.

## Filament slots — `filaments.py`

Every cascade project should carry exactly **two** filament slots: **white in
slot 1, black in slot 2**. Objects name their filament by 1-based slot, so the
bodies (box, holders, pushers, token holders, lid body) sit on slot 1 and the
lid's embossed lettering on slot 2.

Projects drift from this because a project inherits its whole
`project_settings.config` from whatever donor built it. `make_cascade` now
trims **trailing unused slots on every path** (including `--keep-layout`) —
that alone can't change a colour, since it never reorders. The rest needs
`filaments.py`:

```
filaments.py --check <project.3mf>...          # report slots + slots in use
filaments.py --white-first <project.3mf>...    # reorder to white, black
filaments.py --drop-unused <project.3mf>...    # shed trailing unused slots
filaments.py --order 3,1 --extruder-map 3=1,2=1,1=2 <project.3mf>
```

Reordering slots **must** move every object's extruder reference with them, or
the print comes out in the wrong colours — `--white-first` derives both
together. It refuses rather than guessing when a project doesn't reduce to two
(no white slot, or two colours genuinely in use); `--order/--extruder-map` is
the explicit escape hatch, and the only way to express a **merge** of two
slots into one.

### MakerWorld uploads

MakerWorld rejects a project carrying non-stock printer or filament presets —
*"Uploading a 3mf file that contains custom printer types or filament types is
not allowed"*. `filaments.py --check` reports the causes, `--makerworld` fixes
them:

- **`printer_settings_id` must be `<model> <variant> nozzle`.** `h2c.config`
  was written as `Bambu Lab H2C 0.4`, missing ` nozzle`, so every project built
  on the H2C bed inherited an id MakerWorld can't match to a stock preset. The
  P1 profiles were always correct, which is why only H2C projects failed — and
  why Dominion 560/650, built before that profile, upload fine. (Confirmed:
  FCM Occ 2S passed MakerWorld verification once corrected.)
- **A filament flagged as deviating from its system preset** (a non-empty
  filament entry in `different_settings_to_system` / `inherits_group`) is the
  seed Bambu Studio promotes, on save, into a project-LOCAL preset named
  `<preset>(<project>.3mf)`. That gets past upload and then fails
  verification. In this repo the deviation is phantom: the flagged setting
  (`support_air_filtration`) already holds the stock value.

So do NOT "fix" a rejected upload by re-saving in Studio — that converts a
rejected upload into a failed verification. Clear the deviation instead.

The same two corrections also clear MakerWorld's long-standing warning *"It is
detected that the printer settings has been changed in the 3mf, these change
will reset to system values when printing by Bambu Handy App"* — that warning
is what a non-stock `printer_settings_id` plus the deviation markers look like
from MakerWorld's side, so a clean upload and a warning-free listing are the
same fix.

Stale `filament_nozzle_map` / `filament_volume_map` lengths (9 or 7 entries for
2 filaments) are reported but deliberately NOT changed: Dominion 560/650 carry
them and upload fine, so they are drift from an older Studio, not a gate.

### The prime tower has to clear BOTH nozzles (`towers.py`)

A second, unrelated upload rejection:

> [Plate 3]: Found G-code in unprintable area of multi-extruder printers after
> slicing.

The H2C is dual-nozzle and its nozzles do not reach the same bed —
`extruder_printable_area` is `x 0..325` for extruder 1 and `x 25..330` for
extruder 2, so only **x 25..325 is reachable by both**. Objects are unaffected
(each is printed by one extruder and only has to fit that one's area), but every
filament in use purges into the **prime tower**, so on a two-filament plate the
tower must sit in the intersection. Only lid plates carry two filaments — the
lid's lettering is the sole black geometry — so this is a lid-plate defect
exclusively.

`make_cascade` seeds every plate's tower at (15, 200) and moves it only when it
*collides* with an object, and both its bounds test and `replace_parts`' allowed
the whole bed. A lid big enough to need the 45° rotation lies as a diagonal band
and leaves the bottom-left corner empty, so (15, 200) never collided and the
illegal seed survived on exactly the plates where it was illegal. Both placers
now bound the tower by `make_cascade.tower_bounds(ps)`, which is the intersection
of the extruder areas (and the plain bed on single-nozzle printers, so P1 output
is unchanged).

Nothing upstream catches this: Studio's 3D view shows the plate as fine, and it
surfaces only after slicing. Ground truth is Studio's own CLI, which is what
MakerWorld runs:

```
/Applications/BambuStudio.app/Contents/MacOS/BambuStudio \
    --slice 0 --outputdir <dir> <project.3mf>     # 0 = every plate
```

then read `return_code` from `result.json` — `0`, not `-102`. Worth running on
any H2C project before upload; it takes about 20 s a plate and it is the same
check that rejected the upload.

Found on Dominion 560S and repaired with `towers.py --fix`, which relocates by
`make_cascade`'s own rule (4 mm grid, 15 mm clearance, furthest from the bed
centre) and writes back through `filaments.write_settings` — so every other zip
member is copied byte-for-byte and, as above, nothing goes near Studio. Four
published projects were affected, all H2C: **Dominion 560S/560U** (plate 3),
**Dominion 472S** (plate 2) and **Innovation 360S** (plates 2 and 4), each tower
moved to (265, 0) and each project then verified to slice clean on every plate.
The single-filament plates of those projects still carry x=0/15 towers; they are
inert (no tower is generated) and were left alone to keep the diff to the
setting that was actually wrong.

The bound is ~2 mm stricter than the slicer — on 560S plate 3, x=22 is rejected
and x=24 slices clean, the tower's purge geometry sitting slightly inside its
nominal origin. Holding the nominal rectangle to the declared area keeps that
difference as margin rather than depending on it.

### Identifying per-filament keys

Identifying which of the ~500 settings keys are per-filament is the subtle
part, and shape alone cannot do it: `filament_nozzle_map` is 9 entries at any
filament count, and on the dual-nozzle H2C `nozzle_diameter` and
`extruder_printable_area` are 2 entries for reasons unrelated to filaments —
indistinguishable, in a 2-filament project, from a real per-filament array.
`filaments.PER_FILAMENT` is therefore an explicit list, derived as the exact
set of keys whose length differed between the 9-slot and 2-slot halves of one
project. Anything unlisted is left alone; a listed key whose shape disagrees
is reported rather than reshaped. `flush_volumes_matrix` is `n x n` per
nozzle (4 on a P1S, 8 on an H2C) and is permuted as a matrix.
