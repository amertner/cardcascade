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

Decoded model code: **`<Size><Risers>.<FrontCapacity>.<Cards/RiserSlot>[/<Cards/FirstRiser>]`**;
`Unsl/Sleeved model` append `.<boxWidth>-Un` / `-Sl`. `Horizontal` = size class
(S=3, M=4, L=5). Each row yields **two cascades** (`-Un` and `-Sl`).

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
                    [--auto] [--dry-run] [--rebuild] [--standardize-names]
```

- **PLAN** (offline) → **EXPORT** (only stale/missing; **always** confirms the
  API spend, even under `--auto`) → **ASSEMBLE** (`make_cascade --keep-layout`,
  in place, preserving each project's hand-tuned plates). `--auto` skips only the
  two offline prompts.
- **`--rebuild`** switches ASSEMBLE to `make_cascade --auto-plates`: regenerate
  the plate layout from the box's own project as donor (swap every mesh by role,
  normalise the token-holder object name — donors often leave it `Part 1`), with
  the bed chosen from parts.csv's `3D printer` column (**Standard→P1, Large→H2C,
  Mixed→P1 unsleeved / H2C sleeved**). This is the general "auto-build" for
  first-building a box whose only project is stale/mislabeled — it replaces the
  old per-box shell scripts.
- Cascade projects are named canonically — `<Game> <Short name>
  <Sleeved|Unsleeved> (<model>).3mf` (`components.cascade_filename`, `/`→`-`);
  Innovation/Compile already match. `--standardize-names` git-renames legacy
  projects (e.g. Dominion's old `CC 400S …`) to this form.
- ASSEMBLE maps a component to its template slot by **role**, not exact name
  (templates suffix objects: `Lid 400S`, `Topper Cities S-Un`, `TokenHolder
  Full`/`Half`, bare `Topper` = Blank). It refuses (skips + diagnoses) rather
  than half-swapping when the mapping isn't a clean bijection, when a component
  isn't on disk, or for first-riser cascades (need a `Holder#N` override).
  keep-layout cannot ADD an object, so a cascade missing a new object's slot
  (e.g. a pre-HalfTokenHolder Mat template) is skipped for manual layout.

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
