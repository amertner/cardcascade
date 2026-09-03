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
| Innovation | **6 Toppers** — same plate, different embedded text (one per expansion + a blank); ONE assembly export per parameter set yields all 6 (see "The topper assembly") | via `labelmaker.py` |
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
| Toppers (Innovation) | `(expansion, size, cards/slot, sleeved)` | one assembly export → 6 files; shared across Innovation cascades matching all four |
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

### The topper assembly — and why cards/slot is part of a topper's identity

Toppers were six part-studio exports per parameter set, one per value of the
studio's Expansion configuration input. `onshape_config.TOPPER_ASSEMBLY` holds
all six instead, so a parameter set's toppers cost **one** translate op, not six
— ~15 calls saved per set, which made toppers the largest single consumer of
Innovation's budget.

`assembly_split.py` cannot do this split. The monochrome assembly names its parts
after their component type (`Box`, `Pusher`), so that splitter maps object→role
BY NAME. A topper assembly is six instances of ONE part studio at six
configuration values, so every instance carries the SAME body names (`Topper`,
plus `Part 3`…`Part 12`). What separates the instances is the assembly component
transform — grouping components by their translation recovers exactly six groups
— but which group is which EXPANSION has to come from the geometry.
`topper_split.py` owns that:

- the **count of lettering solids** is a property of the word (Echoes 6, Cities 8
  — two dotted i's — Unseen 6, Artifacts 10, Figures 8, Blank 0). It narrows but
  does not decide: it ties {Echoes, Unseen} and {Cities, Figures};
- each glyph's width **as a fraction of the whole word's width** decides. That
  ratio is a property of the word and the font and nothing else, so it survives a
  change of scale — which is exactly what happens here, and is what makes the
  fingerprints reusable rather than per-size tables.

A correct match measures 0.0000; the nearest wrong one with the same solid count
measures 0.034. `identify()` requires a unique match inside `TOL` with the
runner-up at least `MARGIN` worse AND a clean bijection onto all six, and raises
otherwise — the topper counterpart of `check_box`, catching a translation cached
from the previous parameter set before anything reaches disk or provenance. The
assignment was cross-checked against glyph POSITIONS, a feature the matcher never
uses; all five agree to ~1e-5. Assembly ROW ORDER is not usable: the six sit in a
row, but Blank and Figures are swapped relative to `TOPPER_OPTIONS`.

**Cards per sliding slot is part of a topper's identity**, and was missing until
the 10-card boxes were designed. The embossed name sits in the topper's depth,
and that depth is `2.00 mm + one card thickness per card` — 8.00 mm at 15
unsleeved cards, 6.00 at 10 (exact on all three measured points, Un and Sl), with
the text scaling to precisely 65%. A 15-card topper is 2 mm too thick for a
10-card slot, so the old `(expansion, size, sleeved)` key would have handed the
10-card boxes toppers that cannot fit. Files carry the count for the same reason:
`Topper Cities S15-Un.3mf`. The 24 pre-existing files were git-renamed to the
`S15`/`M15` form and their provenance rows re-keyed; nothing was re-exported,
because the rename does not change what they are.

The 6.6 topper is a real geometry change, not an embossed string, and
`VERSIONS["Topper"]` is 6.6 accordingly: the expansion name is no longer preceded
by a **logo body** (the 6.4 toppers lead with one — six solids in Unseen's case),
so body counts drop by one across the board; the plate's depth tracks
CardsPerSlidingSlot; and **Blank is no longer 6 mm taller** than its siblings.
That last point is what the `expected_version()` exemption pinning Blank to 6.3
existed for — the 6.4 change was "add an expansion logo" and Blank had no
expansion to name — so at 6.6 the exemption is gone and the function is a plain
lookup. Every 6.4 topper on disk is genuinely stale, which is why the bump pulls
the four 15-card cascades back into the worklist for one topper op each.

**A re-exported topper changes a built project.** `individual/` is only half of
it: the four 3/4 Ages projects still embed their 6.4 topper meshes, logos and
all, until `refresh_cascades.py --game Innovation` swaps them in. Bumping a
component that a published project already carries is a two-step job.

`no_toppers` lists parts.csv **Short names** and must track that column. The XS
row was listed as `Inno 130` while parts.csv called it `Single Mini`, so the
entry never matched and both XS cascades composed 12 toppers that do not exist
and that their projects have no slot for — ~38 calls on any full-game export.

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

### An unversioned CAD change is invisible to provenance — date the geometry

A holder change landed in Onshape between 2026-08-20 and 2026-08-24 with no
`VERSIONS["Holder"]` bump: the spanning holder's `X-min` moved from -38.5000 to
-38.4000 (and `X-max` the same 0.1 mm the other way, so the strip is 0.2 mm
shorter, centred). It is Allan's fix for holders that users reported sticking,
and it is deliberately rolled out **without fanfare** — folded into whatever gets
re-exported next rather than swept across the repo. So expect holders of both
lengths to coexist for a while; that is intended, not drift to chase.

What is NOT intended is that provenance cannot see it. Because the version did
not move, `PROV.is_current` kept calling every Aug-20 holder current and none
were re-fetched. That is the failure mode `--changed` exists for, but nothing
tells you to reach for it.

**Do not read a component's mtime or its provenance date as its geometry.** Date
the GEOMETRY instead: a round coordinate shared by every file exported after some
day, and a different round coordinate shared by every file before it, is an
unversioned CAD change. Sorting every spanning holder by `X-min` splits them
exactly on the export date:

| X-min (Un / Sl) | files | exported |
|---|---|---|
| -38.5000 / -39.5000 | `Holder 3x15`, `Holder 4x15` | 2026-08-20 |
| -38.4000 / -39.4000 | `Holder 2x10`, `Holder 3x10`, `Holder 4x10` | 2026-08-24 onward |

**It is all 50 holders, not just the spanning ones**, confirmed since against
the whole cached set (`tests/test_holder_corpus.py`): overall width is
`calSlotwidth * HorizontalSlots` plus a constant, and that constant is `+10.000`
on the 30 exported up to Aug 20 and `+9.800` on the 20 exported from Aug 24 —
per-slot games included, and `0.100` in at each end exactly as here. Everything
else about those 30 — depth, height, the rear lip's reach, where the part sits —
matches the current geometry to the micron, so the end block is the whole of the
change. The 20 include one half of a first-riser PAIR (`Holder S-40-r2-Sl` was
re-exported, `Holder S-40-r2-Sl (first)` was not), which is the split the
section above predicts.

**A confound sits on top of that split.** The Aug-20 group is also exactly the
15-card group, so the shift reads equally well as a `Cards/Riser slot` axis. The
old `Holder 3x10-Un` refutes that: it is a **10-card** holder exported Aug 20 and
it reads -38.5000, where a cards axis wants -38.4000. Length tracks the date and
nothing else.

### A holder's tab protrusion DOES depend on RisingSliders

Separately from the length change, and easy to conflate with it: the 6 wedges
along the holder's top edge (the top 2 mm, ~11.2 mm wide, two per card slot)
stand proud of the back face by an amount that varies with the RISER COUNT.
Nothing else in the part varies with it — slot depth, height and length are
identical.

Isolating it needs care, because the obvious Innovation pair (Single Set vs
3 Later Ages) differs in TWO Primary inputs, `RisingSliders` 3->5 AND
`FrontPocketCardCapacity` 15->10, and proves nothing on its own. Two comparisons
do isolate it, both at 0 API calls:

| game | comparison | result |
|---|---|---|
| Innovation | horizontal 2/3/4 at 5 risers | all 0.6347 — horizontal is not a factor |
| Innovation | front pocket 15 vs 10 at 5 risers | both 0.6347 — front pocket is not a factor |
| Innovation | Single Set (3 risers) vs Single Mini (5), same 10 cards and 15 front pocket | 0.5048 vs 0.6347 |
| Compile | 105 Card vs 126 Card — `RisingSliders` is the ONLY differing input | 0.4810 vs 0.4976 |

Compile settles it: 4 vs 5 risers, everything else equal, and the 210 Card holder
(horizontal 5, risers 5) reads 0.4976 too. The effect is small — 0.13 mm across
Innovation's 3->5, 0.017 mm across Compile's 4->5 — but it is reproducible, not
tessellation: the Aug-24 CAD edit RETESSELLATED `Holder 3x15-Sl` (7896 -> 7929
vertices) and its `Y-max` still came back bit-identical. Tessellation reproduces
exactly for fixed inputs, so a `Y-max` that moves means an input moved.

**RESOLVED — the dependence is intended, and the key now carries `risers`**
(Allan, after this section left it open). Two design reasons, both his: the
diagonal edge has to form ONE continuous line across the open cascade, and how
far a riser may rise is capped by the box height — so at 5 risers a 22 mm rise
may have to come down to 20 to leave the rearmost riser enough hold, and the
angle changes with it. The ~2 mm lip behind each pocket is extended along that
same diagonal, so it stands proud further when the angle is shallower. All of
that is deliberate, for usability.

The `Y-max` wedge above is therefore a symptom, not the effect. At 7.0 the real
magnitude is far larger than the 0.13 mm recorded here: the leaves' taper on
Innovation `3x10-Un` measures `2.299` at 3 risers against `1.795` at 5 — 0.5 mm,
and the two-thickness structure at z 25 collapses to one. **The "nothing printed
is wrong either way" conclusion above does not survive 7.0.**

**The key gained RISERS, not rise height,** though rise is the real design
parameter. Rise IS measurable — the pusher is cut as a staircase, one tread per
riser, each dropping the plate width by `D/risers`, and the tread LENGTH is the
rise: `22.000` on Innovation at 3 risers, `17.400` at 5, dead flat across treads.
Two things rule it out as the key anyway:

- **It cannot be assigned, only checked.** `plan_exports.holder()` computes the
  filename from parts.csv BEFORE the export exists — the name is what decides
  what to fetch and where to write it. A mesh-derived key is circular, and the
  pusher is no escape: it comes out of the same assembly.
- **It is strictly coarser than riser count.** FCM rises 20.0 at BOTH 3 and 4
  risers. Keying by rise could merge holders that must stay apart; keying by
  risers can at worst emit two byte-identical files.

Riser count is not a lossy proxy: measured over all 32 pushers, **rise is a
function of riser count within a game**, and the game is already implied by the
folder. That is an assumption about the CAD, so it is checked rather than
trusted — `verify.py --rises` prints the table and exits 1 if any
`(game, risers)` pair ever yields two rises. It reads 12 pairs, 0 inconsistent.

Rise by game and riser count, for reference:

| | 2 | 3 | 4 | 5 | 6 | 8 | 9 |
|---|---|---|---|---|---|---|---|
| Innovation | | 22.0 | | 17.4 | | | |
| Compile | | | 18.0 | 17.4 | | | |
| FCM | | 20.0 | 20.0 | 17.4 | | | |
| Dominion | n/a | | 16.0 | 16.0 | 14.5 | 10.875 | 9.667 |

Dominion at 2 risers has a single tread and no gap, so rise is not measurable
there at all — another reason the key could not have been mesh-derived, since
`S-40` `[2, 5]` was one of the collisions that needed resolving.

The four files that each held two meshes, and which mesh each turned out to hold
— settled from provenance (components sharing an `exported_at` came from one
parameter set, and the boxes in that batch name the cascade) and, where a batch
held both consumers, from the mesh against an unambiguous same-game reference:

| game | file | rows (risers) | held | how |
|---|---|---|---|---|
| Innovation | `Holder 3x10-{Un,Sl}` | Single Set (3), 3 Later Ages (5) | **5** | provenance |
| Compile | `Holder 3x7-Un` | 105 Card (4), 126 Card (5) | **4** | provenance |
| Compile | `Holder 3x7-Sl` | as above | **4** | mesh: 0.7799 ≠ 5-riser 0.8043 |
| Dominion | `Holder M-21-{Un,Sl}` | 202/244 Card (4), 324 Card (6) | **4** | mesh: matches 4-riser `S-16` exactly |
| Dominion | `Holder S-40-{Un,Sl}` | 246 Card (2), 300 Card (5) | **5** | mesh: cap-40 trend predicts 19.296@5 vs 25.263@2; measured 19.044 |

FCM is clean. Note the previous paragraph had this backwards for Innovation:
Single Set's project embedded the **5**-riser mesh, not the 3-riser one — it had
been getting the wrong holder, which is exactly the failure the key now prevents.

**State of the rename, and what is left.** The key change renamed all 42 holder
files to carry `-r<N>-` (`Holder 3x10-Un` -> `Holder 3x10-r5-Un`,
`Holder M-21-Sl` -> `Holder M-21-r4-Sl`), with `git mv` and the provenance `key`
column widened to match. Every project was then audited by matching the holder
mesh it embeds against the file it should now use: **45 of 45 carry the right
holder.** Only Innovation Single Set Un did not, and it was rebuilt from the
3-riser holder split out of its own cached assembly — 0 calls.

Nine holder files have no mesh on disk, because no cascade with that riser count
was ever exported. Seven cascades need them, and the exports are NOT extra work:
one assembly export supplies Box + Holder + Pusher together, and all three are
stale at 7.0 anyway, so the holder fix and the 7.0 lock migration are the same
operation at the same price.

| cascade | missing holder | ~calls |
|---|---|---|
| Innovation Single Set Sl | `Holder 3x10-r3-Sl` | ~7 |
| Compile 126 Card Un / Sl | `Holder 3x7-r5-{Un,Sl}` | ~14 |
| Dominion 324 Card Un / Sl | `Holder M-21-r6-{Un,Sl}` | ~14 |
| Dominion 246 Card Un / Sl | `Holder S-40-r2-{Un,Sl}` | ~14 |

~49 calls for all seven, which also brings each to 7.0. `Holder M-21-r6-{Un,Sl}
(first)` is wanted only by the Speculation row (`290 Card`), which is skipped for
an incomplete parts.csv row, so it costs nothing until that row is finished.

Three of the seven are already on the broken-eleven list (`246 Card Un`, and both
sleevings ride the same assembly), so those calls were owed regardless.

**`_raw/` is what makes all of this checkable for free.** Any question of the
form "does component C depend on input I" is answered by splitting two cached
assemblies that differ only in I — `assembly_split.split()` on
`mesh.unwrap(raw)`, 0 calls. Every pair named in the table above is already
cached. Reach for that before spending a call on a hypothesis, and before writing
a conclusion down: the riser finding above was asserted, retracted and reinstated
across three commits because the confounds were not separated first.

### Packing 45° strips — two arms, not one band

Holders and toppers are long thin strips that only fit a plate turned 45°.
`--auto-plates` used to stack them as a single diagonal BAND through the plate
centre, with capacity estimated as `(bed - 20)·√2 - longest`. That estimate drops
the strip's own depth and hard-codes a 10 mm margin, and it split five Innovation
M holders (285.80 × 9.39 on a P1) across two plates when they fit one — Allan
rearranged them by hand and both plates sliced, which is what exposed it.

The geometry: a `w × d` strip turned 45° has a SQUARE bounding box of side
`(w + d)/√2`, so its centre must stay in a square inset from the bed by half of
that. Stepping along a bed AXIS by `(d + gap)·√2` moves a strip exactly
`(d + gap)` across its own width — the separation neighbours need — while also
sliding it along its own length, which is free because the strips are parallel.
So a column down one edge plus a row along the next packs them at the right
pitch, the two arms sharing their corner strip. The arrangement is built around
a local origin and then CENTRED on the plate: anchoring it to a bed corner pushes
a single wide strip (a Box, a Lid) off-centre and into the P1's excluded corner,
which `make_cascade` then refuses.

**Two arms is not universally better, so the code takes whichever holds more.**
An arm advances by `(d + gap)·√2` along a bed axis, where the band advances by
`(d + gap)` across the strip only; once a strip is thick relative to the bed, one
arm holds a single strip while the band still holds several. Dominion's
270 × 27.80 mm first-riser holder is exactly that (arms 1, band 2), and it is why
`strip_capacity()` is a `max` of the two and the placement picks its arrangement
to match. Measured over every holder and topper on disk against every candidate
bed: 89 capacities up, 55 unchanged, 0 reduced.

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

### The pusher's second tab collides with the end notch on narrow pushers

*(Open CAD defect — found from a print, measured off the meshes, not yet fixed
in Onshape.)*

**What the features are for — two jobs, not one.** In use, the pusher's leading
end slides into a socket in the LID — one per pusher, `9.20` wide × `D − 0.40`
across × `5.0` deep, whose inner wall steps between `3.27` and `5.11` mm of free
channel. The two raised tabs drop into the two wide steps (the recesses) and
hold the pusher in; the U-notch straddles a rib that blocks the channel
outright, so the pusher can only enter where its notch is and bottoms on the
rib, which sets insertion depth.

Out of use, **the same two tabs hang the pusher in a slot in the BOX's back
wall** — one slot per pusher, `D + 4.00` wide for the first (it absorbs the end
wall's margin) and `D + 2.40` for the rest, `3.20` deep, running `z 24` to
`84.75`. Measured on four boxes across three games, including a three-pusher
Dominion box with three slots:

| box | pusher `D` | slots | slot widths |
|---|---|---|---|
| `Innovation S3.15.10.20-Un` | 19.20 | 2 | 23.20 / 21.60 |
| `Dominion S2.40.12-30.32-Un` | 20.76 | 2 | 24.76 / 23.16 |
| `Dominion M6.21.10.45-Un` | 37.20 | 3 | 41.20 / 39.60 / 39.60 |
| `Innovation S5.15.15.45-Un` | 42.00 | 2 | 46.00 / 44.40 |

`3.20` takes the pusher's 3 mm plate but not its 4.5 mm tab section, so the tabs
have to pass through **cutouts in the top rim of the slot's inner lip**: the top
`5.25` mm of that lip (`z 99.75 → 105.00`) is cut away `4.40` wide, twice per
pusher, and the pair sits **at exactly that pusher's tab pitch**. Verified on 14
boxes across the four games — `L6.40.12.45-Un`'s cutouts are 29.76 apart against
a 29.76 tab pitch, `M4.21.10.32-Un`'s 12.77–12.82 against 12.80, and so on — with
16.00 between one pusher's outer cutout and its neighbour's inner one. The outer
wall is uncut, which is why the cutouts are invisible from behind and why an
earlier probe of the slot's FACES found nothing: they are in the rim, above the
`z ≤ 92` the probe covered.

Every mating feature — lid socket and box slot alike — is therefore sized from
the same `D` the pusher's features are.

A Pusher is a flat 4.5 mm plate printed FACE DOWN, and its leading end carries
three features that the CAD sizes from the pusher's own depth `D` — the
card-stack dimension, i.e. the width of the leading end the features are cut
into (not necessarily the plate's shorter axis: `Pusher 2x18-Sl` is 39.6 across
a 32 mm long plate):

| feature | size | placed |
|---|---|---|
| tab A | 3.8 wide × 5.0 deep, 1.5 mm proud of the top face | 4.0 mm in from the `D = 0` edge |
| tab B | the same | 4.2 mm in from the `D` edge |
| notch | 5.4 × 5.2 mm, cut clean THROUGH the plate from the leading end | centred 2.5 mm off the plate's mid-line — edges at `D/2 − 0.2` and `D/2 + 5.2` |

Tab A is placed from an edge and the notch from the mid-line, and the CAD
already clamps the notch so it can never reach tab A (below `D ≈ 16` the notch
stops dead at tab A's edge, −7.8: `Pusher 3x6-Un` is the one case on disk).
**Tab B has no such clamp**, so as `D` shrinks the notch walks straight into it.
Tab B is fully backed only while

```
D − 8.0  ≥  D/2 + 5.2      i.e.   D ≥ 26.4 mm
```

and below that it loses `13.2 − D/2` mm of its 3.8 mm root, left cantilevered
over a 3 mm void the slicer has to start in mid-air. Everything ≥ 26.4 mm is
backed to the full 3.8 mm, so this is invisible on all but the narrowest boxes —
`D` is a card-stack thickness, so it is the UNSLEEVED pushers that are narrow.

Measured over the 32 pushers in `individual/` (`verify.py --pushers`):

| pusher | `D` | tab B backed | root |
|---|---|---|---|
| `Innovation/Pusher 3x10-Un` | 19.20 | 5 % | **0.19 mm** |
| `Dominion/Pusher 2x12-Un` | 20.76 | 26 % | **0.98 mm** |
| `Compile/Pusher 4x7-Un` | 20.80 | 26 % | **1.01 mm** |
| `FCM/Pusher 5x6-Un` | 23.40 | 60 % | 2.31 mm |
| `Dominion/Pusher 4x10-Un` | 24.80 | 79 % | 3.01 mm |
| `Compile/Pusher 5x7-Un` | 26.00 | 95 % | 3.61 mm |
| `FCM/Pusher 3x6-Un` | 14.04 | 65 % | 3.80 mm (tabs fused) |
| `FCM/Pusher 3x6-Sl` | 18.00 | — | **tab B absent** |

`Pusher 3x10-Un` — Innovation "Single Set" unsleeved, the narrowest two-tab
pusher in the catalogue — is the one that fails in the hand: 0.2 mm of root
under a 3.8 mm tab, and it prints as a loose flag that snaps off. It is also
the only one where the tab is a pure cantilever rather than a partial one: the
notch's far side is 1.8 mm past the tab, so nothing bridges.

**The lid loses the same millimetres, on two features.** The rib eats into tab
B's recess and the recess eats into the rib, by the same `13.2 − D/2`. On
Innovation's unsleeved Single Set lid the recess measures `0.56` long instead of
`3.97` and the key rib `1.58` wide instead of `4.96`; Compile's 105 unsleeved
lid (`D = 20.80`) reads `1.36` and `2.35` against a predicted `1.15` and `2.15`.
So a narrow cascade has no working lock at that end even if the pusher's tab
were intact, and any fix has to land on both parts.

**Two further stages of the same collision, which a support check alone misses.**
At `D = 18.00` (`FCM/Pusher 3x6-Sl`) tab B's whole footprint falls inside the
notch and the CAD emits NO tab there — one tab survives, perfectly backed, so
`check_pusher` counts tabs before it measures support. At `D = 14.04`
(`Pusher 3x6-Un`) the two tabs overlap and fuse into one 5.84 mm boss; the
notch's own clamp lands its edge mid-boss, so 2.04 mm hangs over the notch while
3.80 mm stays rooted — an overhang, not a flag. **Eight of the 32 pushers have a
defective lock, not seven.**

A pusher's dedup key is `(risers, cards, sleeved)`, so those eight files reach
**eleven built projects**: Innovation Single Set Un; Dominion 246, 168,
202 (Mat), 244 Un; Compile 105, 126, 210 Un; FCM 144 Un, and FCM 180 in BOTH
sleevings (the sleeved one is the missing-tab case, which is why it is the only
sleeved row on the list). The audit reads `individual/` only — a project
instances one pusher 2-3 times, so walking `cascades/` re-reports the same
meshes under project names.

The fix belongs in Onshape — give tab B the same clamp against the notch that
tab A has, or drive both tabs off the mid-line so they track the notch. Until
then `verify.check_pusher` WARNS on every affected export rather than refusing
it: unlike `check_box`/`check_lid` the bytes are not wrong, the CAD is, and
refusing would only block the rest of the assembly.

### The five-design lock catalogue

*The standard itself lives in [`LOCK_STANDARD.md`](LOCK_STANDARD.md) — the rule,
the class table and the constants, without the history. This section is the
reasoning that produced it and the record of what it cost.*

*(CUT IN CAD and measured — see "Verifying the cut catalogue" below.
`verify.LOCK_CLASSES` holds the catalogue; `verify.py --catalogue` prints the
per-pusher worksheet. Nothing in code enforces it; the conformance test is to
measure an export against `target_lock()`.)*

The collision is a symptom: the three lock features are placed from three
different datums (two plate edges and the mid-line), so nothing guarantees they
stay apart, and 32 pushers carry **30 distinct lock geometries**. Allan asked for
at most five designs covering the range, with backwards compatibility a
nice-to-have.

**Every lock dimension is already a constant** — measured across all 32 exported
pushers, not assumed: overall thickness `4.500`, plate `3.000`, tab proudness
`1.500` (one face only), tab `3.800 × 5.000` flush with the leading edge, notch
`5.400 × 5.200` (to 0.07 of tessellation drift), lid recess step `1.840` as
recorded here but `1.800` when measured on the FCM lids — and `1.700` from 7.0,
see the test-print note below — box
slot depth `3.200`. The only two parts that deviate are the known defects:
`3x6-Un`'s tabs have fused into one 5.84 boss and `3x6-Sl` has lost one
altogether. **So the catalogue moves positions and keeps every size**, with three
exceptions: the edge inset shrinks from 4.00/4.20 to as little as 2.00; C1 and C2
carry no notch at all; and C1's two tabs sit 2.40 apart, tight enough that a
single 10.00 tab — same outer span, more material — is worth considering instead.

**A design is one number** — `s`, the distance from the pusher's centreline to
each tab's centre. Tabs and notch keep today's sizes and sit symmetrically about
that centreline, so a design is legal on a pusher of depth `D` when there is at
least `EDGE_MIN` of plate outboard of each tab, and can carry the notch when the
land between tab and notch holds up:

```
fits when   D >= 2 * (s + 1.90 + EDGE_MIN)          EDGE_MIN = 2.00
hang base   = 2s
notch when  s >= 1.90 + 2.70 + LAND_MIN             LAND_MIN = 1.20, so s >= 5.80
```

| design | `s` | covers `D` | parts | hang base | notch | worst in band |
|---|---|---|---|---|---|---|
| C1 | ±3.10 | 14.00–17.99 | 1 | 6.20 | none (2.40 between the tabs) | exact fit |
| C2 | ±5.10 | 18.00–24.79 | 5 | 10.20 | none at 5.40; 4.00 would fit at a 1.20 land | 65 % at 23.40 |
| C3 | ±8.50 | 24.80–34.79 | 10 | 17.00 | 5.40 on the centreline | 63 % at 33.60 |
| C4 | ±13.50 | 34.80–55.79 | 11 | 27.00 | 5.40 on the centreline | 63 % at 50.40 |
| C5 | ±24.00 | 55.80 and up | 5 | 48.00 | 5.40 on the centreline | 71 % at 75.60 |

The offsets were chosen to maximise the WORST hang base as a fraction of the
widest the plate could give (`D − 2·EDGE_MIN − 3.80`). All 32 covered, worst case
**63 %**, and **15 of the 32 end up with a wider base than they have today** —
today's 4.00 mm inset is more generous than the 2.00 the catalogue allows at the
bottom of a band. **Today's base is `D − 12.00`, not `D − 11.80`**: the CAD sets
tab A 4.00 in from one edge and tab B 4.20 in from the other, so the centres are
`6.10` and `D − 5.90` and their separation carries tab B's extra 0.20. Confirmed
against the old boxes' cutout pitch — 11.400 at D 23.40, 6.000 at D 18.00, both
exactly `D − 12.00`. The parts that lose are the wide ones at the top of a band;
the worst is `Pusher 9x10-Sl`, 48.00 against 63.80.

**The boxes do NOT survive, and a catalogue cannot make them.** The box's rim
cutouts are `4.50` wide for a `3.80` tab (measured to 0.002 on six FCM boxes,
old and new — the `4.40` this used to say was a coarse reading), so a tab may
shift `±0.35` and still drop in. The old tab centres are `6.10` and `D − 5.90`,
so a class of offset `s` stays box-compatible only while
`D ∈ [2s + 11.50, 2s + 12.90]` — a 1.40 mm window per class, which just two of
the 32 depths land in: `D = 39.60` under C4 and `D = 60.75` under C5.
Making every pusher land in its window means `s = D/2 − 6.00`, which IS today's
parametric rule. **A fixed catalogue and box compatibility are mutually
exclusive.** The lids all change too — the recesses move on every one, and six
lose the rib.

**Three things to settle before this is cut.**

1. **Is a 2.00 mm edge inset acceptable?** It is half today's 4.00 and it lands on
   the narrowest pusher in every band. 2.50 costs about a point of worst case;
   3.00 costs three points and 8 mm more on the largest loss.
2. **C1 serves one pusher** — `FCM/Pusher 3x6-Un` at `D = 14.04`, the only part
   below 18 mm, and the only depth where two 3.80 tabs will not fit at a 4.00
   inset at all. Spending a fifth of the catalogue on it costs the other 31 about
   7 points: five designs for `D ≥ 18` alone would run
   ±5.10 / 7.80 / 11.10 / 15.30 / 24.00 and reach 71 % worst case.
3. **C1 and C2 have no notch**, so on those six sizes the lid loses its key rib
   and needs its depth stop on the socket floor. A 4.00 mm notch fits C2 at a
   1.20 mm land if a second rib width is preferable to a second lid family.

**Validating the hang needs a re-cut BOX as well as a re-cut pusher**, because
the rim cutouts move with the tabs — this paragraph used to say the opposite and
was wrong; see the box-compatibility note above. So a hang test costs the long
print. Two pairs cover the range: `Pusher 6x10-Sl` (D 50.40, C4, tabs
9.80–13.60 / 36.80–40.60 — the catalogue's worst hang base and a 9.80 inset) and
`Pusher 3x6-Un` (D 14.04, C1, tabs 2.02–5.82 / 8.22–12.02 — the tightest
geometry in it). If both hang solidly, the only mechanical question left is the
lid's depth stop for C1 and C2.

**Cost.** 32 pushers and 46 lids re-cut — a full re-export, real API budget — and
printed pushers stop matching printed lids, so a cascade is re-made as a pair.
Eleven published projects carry the defect and need re-cutting anyway.

**Rejected on the way here.** A ladder is only worth its price because the tabs
do double duty: they hold the pusher in the lid socket AND hang it in the box
slot, and a fixed design pulls them inboard of the plate edges on everything but
the narrowest member of its band. Measured against the achievable base that costs
about 12 points per class you decline to add, with no knee — 4 / 19 / 34 / 47 /
57 / 69 % worst case for 1 to 6 classes at a 4.00 inset. Flaring the leading end
OUT to a class width would have removed the cost entirely and made the slot and
socket class-constant too; **the pusher cannot be made wider than `D`**, so that
is closed. What makes five designs viable at all is dropping the edge inset from
4.00 to 2.00, which buys back most of what the fixed positions cost.

### Cutting the catalogue in CAD

*(DONE — Allan cut this in Onshape and exported three FCM cascades by hand;
measured in "Verifying the cut catalogue" below. This is the recipe that was
followed.)*

Add a **`LockClass`** configuration input (C1–C5) and drive all three parts from
it. Pick the largest class whose minimum depth fits; nothing else about the lock
changes — tab `3.80 × 5.00` standing `1.50` proud, plate `3.00`, notch
`5.40 × 5.20`, box slot depth `3.20` all stay. The lid recess step is the ONE
running clearance that does change, to `1.700` — set on a test print, not
calculated.

| class | tab centres | use when D ≥ | hang base | notch | parts |
|---|---|---|---|---|---|
| C1 | ±3.10 | 14.00 | 6.20 | no | 1 |
| C2 | ±5.10 | 18.00 | 10.20 | no | 5 |
| C3 | ±8.50 | 24.80 | 17.00 | yes | 10 |
| C4 | ±13.50 | 34.80 | 27.00 | yes | 11 |
| C5 | ±24.00 | 55.80 | 48.00 | yes | 5 |

Three edits, one per part, all in the same frame:

1. **Pusher** — replace both tab insets (`4.00` from one edge, `4.20` from the
   other) with `centreline ± s`. Move the notch from `D/2 − 2.50` **onto the
   centreline**, and suppress it for C1 and C2.
2. **Lid** — mirror it: socket recesses to `centreline ± s`, key rib onto the
   centreline, rib suppressed for C1/C2 (six lids lose it).
3. **Box** — the two rim cutouts per pusher move to `centreline ± s`. Same
   `4.40` wide × `5.25` deep, same position in the top of the slot's inner lip.

**Putting the notch on the centreline is the actual fix**, not a tidy-up: it
collapses three datums into one, so the tab-into-notch collision cannot recur at
any `D`. C1 and C2 have no room for a `5.40` notch between tabs `6.20`/`10.20`
apart — the lands would be `−1.50` and `0.50` — so those lock by tabs alone.

**Guard when adding a new box size:** a tab must keep `EDGE_MIN` of plate
outboard, i.e. `s <= D/2 - 3.90`. A size that violates it takes the next class
down; it never takes a tweaked `s`, or the catalogue stops being a catalogue.

Then `verify.py --pushers` on the re-exported parts: it checks tab count, width
and root, and exits 1 while any lock is defective.

### Verifying the cut catalogue

*(Done, on three hand-exported FCM cascades — 0 API calls, the files were
exported from Onshape by hand into `tmp/`. Assemblies split with
`assembly_split.split()`; every figure below is measured off the meshes.)*

The three cover C1 and C2 — the two classes with no notch, and the tightest
geometry in the catalogue — and all three are on the broken-five list:

| cascade | pusher | D | class | old fault |
|---|---|---|---|---|
| FCM 180 Card Un | `3x6-Un` | 14.040 | C1 | tabs fused into one 5.84 boss |
| FCM 180 Card Sl | `3x6-Sl` | 18.000 | C2 | second tab absent altogether |
| FCM 144 Card Un | `5x6-Un` | 23.400 | C2 | 2.31 mm of root |

**The pushers land on `target_lock()` exactly** — not to a tolerance, to 0.00 on
every edge:

| pusher | tabs, from the D=0 edge | inset | root | backed |
|---|---|---|---|---|
| `3x6-Un` | 2.02–5.82 / 8.22–12.02 | 2.02 | 5.00 | 100 % |
| `3x6-Sl` | 2.00–5.80 / 12.20–16.00 | 2.00 | 5.00 | 100 % |
| `5x6-Un` | 4.70–8.50 / 14.90–18.70 | 4.70 | 5.00 | 100 % |

Every size the catalogue promised to keep is kept: overall thickness `4.500`,
plate `3.000`, tabs `1.500` proud, and a tab footprint of exactly `38.00` mm² =
2 × 3.80 × 5.00 on all three. No through-notch on any of them, which is right for
C1 and C2. `check_pusher` returns clean on all three; it flagged all three before.

**The boxes' rim cutouts moved to `2s`**, measured on all nine pairs:

| box | old pitch | new pitch | target | land between the pair |
|---|---|---|---|---|
| `L3.18.6.20-Un` | *merged* | 6.199 / 6.201 / 6.199 | 6.20 | 1.701 |
| `L3.18.6.20-Sl` | 6.000 | 10.200 / 10.199 / 10.200 | 10.20 | 5.701 |
| `M5.6.6.20-Un` | 11.400 | 10.200 / 10.200 / 10.200 | 10.20 | 5.701 |

Cutout width is `4.499` new and `4.497–4.499` old — unchanged, and 4.50 rather
than the 4.40 recorded above. **The old `L3.18.6.20-Un` box has only THREE
cutouts, each 6.538 wide**: at D 14.04 the two 4.50 cutouts overlap and merge,
exactly as the pusher's two tabs merge into one 5.84 boss. The defect reached the
box as well as the pusher, which is worth knowing — it is independent evidence
that box and pusher are cut from the same numbers.

C1's `1.701` land is the narrowest bridge anywhere in the new set: a
1.70 × 1.26 × 5.25 post standing between the two cutouts. It is not a new risk —
the old `L3.18.6.20-Sl` box already ships a `1.501` land at the same place — but
it is the thing to look at first on a test print, and it is the direct
consequence of C1 keeping two tabs rather than the single 10.00 tab the
catalogue offered as an alternative.

**The lids mirror it, and the key rib is gone.** Recess centres sit at the socket
centreline ± `s` to within 0.010; recess length is `3.994–3.998` for a `3.80`
tab; the socket's own span is `D − 0.40` exactly. No lid carries a key rib, which
is right for C1 and C2. Changes are confined to `z 1.60–6.60` — the three sockets
and the version string, nothing else.

**One change the catalogue did not ask for, and it stays: the lid recess step is
`1.700`, was `1.800`.** The plain channel is unchanged at `3.300` for a `3.000`
plate, but a recess now opens to `5.000` instead of `5.100`, so the tab's play
against its `1.500` proudness falls from `0.300` to `0.200`.

**Decided on a test print, which is why it holds.** It arrived as an eyeballed
value and was queried here on exactly that ground; Allan then fitted a printed
pusher and lid and found `1.800` gave too much gap. So `1.700` is the measured
answer to a question the catalogue never asked — the catalogue fixed *positions*
and assumed the running clearances were already right, and on this one they were
not. A mesh could not have found it: `1.800` clears, and clearing is all a
measurement can see. **Do not "restore" it to `1.800`.**

**Mind the name.** In the CAD this dimension is *tab depth*: the room the recess
gives the tab. In this file `tab depth` is the tab's `5.000` along the insertion
direction (`tab 3.800 × 5.000`). Two dimensions, one name — say **recess step**
for the `1.700`.

The three lids in `tmp/` already carry it, so nothing needs re-exporting.

**All three parts emboss `7.0`.** Read off the meshes: the box goes `6.6 → 7.0`
and the lid `6.5 → 7.0`. The lid moving means the adopted-lid discrepancy
recorded under `--changed Lid` closes at 7.0 — a refreshed cascade will no longer
carry a box and a lid reading different versions.

**What this does NOT establish.** Nothing here is a print. The 2.00 mm edge inset
appears on `3x6-Un` and `3x6-Sl` and cannot be judged from a mesh: the tab root
is now the full 5.00 (against 0.19–2.31 on the worst parts today) so the load
path is sound, but 2.00 mm of plate outboard of a tab is about five 0.4 mm
extrusions and is the part most likely to be knocked off in handling. C1 and C2
also have no notch, so their lids need the depth stop on the socket floor, and
whether that stop exists is a fit question a mesh measurement does not answer.

### Migrating to the lock catalogue — 7.0

*(CAD done, pipeline not started. The CAD already embosses `7.0` on Box, Lid and
Pusher; `onshape_config.VERSIONS` still reads `Box 6.6, Lid 6.5, Pusher 6.6` and
must be bumped before any export run, or provenance records a version the parts
do not carry.)*

**Bump `VERSIONS` for `Pusher`, `Lid` AND `Box`.** All three carry lock
geometry: the pusher's tabs and notch, the lid's recesses and key rib, and the
box's rim cutouts. Only holders, toppers, token holders and labels are untouched.
`run_export` writes just the components a cascade needs, so those four come back
byte-identical even though the assembly is re-fetched.

| component | 7.0 | why |
|---|---|---|
| Pusher | **changes** | new tab and notch positions |
| Lid | **changes** | socket recesses move; six lose the key rib |
| Box | **changes** | the rim cutouts sit at the old tab pitch |
| Holder, first-riser holder | unchanged | no lock features |
| Topper, TokenHolder, HalfTokenHolder, Label | unchanged | no lock features |

So 7.0 is a whole-cascade change: a pusher, a lid and a box must all come from
the same version. Only the holders and toppers carry over.

Cost, from the planner with all three bumped (0 API calls to measure):
Innovation ~84, Dominion ~148, Compile ~42, FCM ~56 — **~330 calls** for the
whole migration, against 2500 a year.

Adding the Box costs ~50 over Pusher + Lid alone, and it is worth being precise
about why, because the Box is ASSEMBLY_SOURCED and so rides the same translate
that already brings the pusher, holders and token holders:

| change set | sets | assembly translates | lid studio translates | est. |
|---|---|---|---|---|
| `Pusher,Lid` | 46 | 32 | 46 | ~280 |
| `Pusher,Lid,Box` | 48 | 48 | 46 | ~330 |

The increment is 16 assembly translates, not 48 — riding the assembly is real
and is already priced in. What it does not cover is that **pushers dedup across
cascades and boxes do not**: a pusher key is `(risers, cards/slot, sleeving)`, so
Dominion's 20 sets share 16 assembly fetches, but a box key is `(model, merged)`,
unique per cascade, so every set must fetch its own. The Mat split accounts only
for the 46 → 48 sets.

Note where the bill actually is: 46 lid studio translates ≈ 138 calls, the
largest single item and the one that cannot ride anything, because Lid is
STUDIO_SOURCED and keyed per model. Half the assembly cost (96 of 144) was
already owed to the pushers. If the lid could ever be sourced from the assembly
it would take ~140 off any future migration.

**Do the broken five first.** Their lock does not work now, so nothing is lost by
re-cutting them, and it is ~35 calls (5 parameter sets, 5 assemblies, 5 lids):

| project | status | pusher | fault |
|---|---|---|---|
| FCM 180 Card Sl | Pub 6.5 | `3x6-Sl` | no second tab at all |
| FCM 180 Card Un | Pub 6.5 | `3x6-Un` | tabs fused, 2.04 over the notch |
| Innovation Single Set Un | Drafting | `3x10-Un` | 0.19 mm of root |
| Dominion 246 Card Un | Published | `2x12-Un` | 0.98 mm of root |
| Compile 105 Card Un | Pub 6.5 | `4x7-Un` | 1.01 mm of root |

Six more are under-rooted but usable and can ride the general migration:
Dominion 168, 202 (Mat), 244 Un (3.01 mm), FCM 144 Un (2.31), Compile 126 and
210 Un (3.61, 0.19 overhang).

**Depth, not size class, is the theme — and box depth is a publishable proxy.**
The defect is set by the PUSHER's depth (under-rooted below `D = 26.4`), which is
the card stack's thickness, so it is orthogonal to the S/M/L in a model code —
that letter is WIDTH. The affected set spans `L3.18.6` (334 wide, 35 deep) to
`S2.40.12/30` (208 wide, 50 deep), which is why "small cascades" reads as wrong
even though the intuition behind it is right.

Correlated against each row's assembled depth (`parts.csv` D, the closed
cascade), the split is clean enough to publish:

- every affected cascade is **50.0 mm deep or less** (range 35.0–50.0);
- the shallowest unaffected one is **47.7**.

So "roughly 50 mm and under" catches all 11 with three false positives and no
misses — the safe direction. State it as *roughly*, not a cutoff: it is a proxy
for the pusher, and a future box size could land in the 47.7–50.0 overlap on the
other side. The exact criterion stays `pusher D < 26.4`, which
`verify.py --pushers` tests directly.

**Choosing the first wave.** Each affected cascade needs its own parameter set
(the box key is unique per cascade), so a wave costs about 7 calls per cascade —
1 set + 1 assembly + 1 lid.

| scope | cascades | calls | leaves behind |
|---|---|---|---|
| broken only | 11 | ~77 | 9 split rows |
| ≤ 50 mm | 14 | ~98 | 8 split rows |
| whole rows | 20 | ~140 | nothing split |
| everything | 50 | ~350 | — |

The ≤ 50 mm sweep adds `FCM 264 Un`, `198 Un` (hang base 16.04 → 17.00) and
`FCM 144 Sl` (18.20 → **17.00**, a loss). None has a defect, so it buys only that
the published rule matches what shipped.

**DECIDED: the broken 11, and nothing else** (Allan, after the analysis below).

The argument for going wider was split rows: 9 of the 11 affected cascades are
the UNSLEEVED half of a row whose sleeved half is fine, so a broken-only wave
leaves 9 boxes whose two sleevings lock differently under the same name — e.g.
`Dominion 244 Un` at 7.0 beside `244 Sl` at 6.x. That only matters if one person
holds both, and **they do not: a user picks a sleeving and stays there**, so the
two halves are never compared or interchanged. The concern is an artefact of
reading the catalogue by row rather than by user, and it is dropped.

Two things follow, worth keeping because they are the reason not to revisit this:

- The `≤ 50 mm` sweep buys nothing at all now. Its only merit was making the
  published rule match what shipped, and a broken-only wave can simply NAME its
  11 cascades instead of stating a rule.
- Not touching the 9 partners is a saving, not a debt. 7 of them would have LOST
  hang base under the catalogue — `Compile 105 Sl` −3.20, the Dominion sleeved
  trio −4.80 — because their generous depth currently buys a wider spread than a
  fixed class gives. That is the catalogue's known trade (the 63 % worst case
  above), so re-cutting them would have handed those users a slightly less stable
  hang for no visible gain. They keep what they have until the general migration.

Sequence: implement and validate the CAD first (a printed part, not just a
`--pushers` pass), then the 11.

**A backwards-compatible pusher is not possible**, on three counts now. The lid
socket's key rib blocks the channel outright, so the notch position is a hard key
rather than a preference. Away from a recess the socket wall leaves `3.27` of
free channel against the `4.50` a tab needs, so a tab anywhere but a recess jams.
And the box's rim cutouts are cut at the old tab pitch, so a re-pitched pusher
will not drop into an old box either. A pusher that works with old parts must
carry the old notch AND the old tab positions — it must be the old pusher. Tabs
at both old and new positions jam; a notch wide enough to clear both ribs would
take 8 mm of plate and still not lock.

The one partial part that IS possible: a **tabless, notch-only pusher** slides
into either lid (the 3.00 plate passes everywhere) and drops to the bottom of the
box slot instead of hanging. It never locks, so it is a worse part than either
version and a third variant per size to explain — not recommended, but recorded
because it is the only geometry that spans both.

So compatibility lives in distribution, not geometry: **keep the 6.x downloads
available**, and publish one rule — *a pusher, a lid and a box must all come from
the same version; holders and toppers carry over.*

## Generations — holding cascades back from the current version

*(In use, and the 7.0 wave is COMPLETE. 20 cascades build at 7.0, 28 stay at 6.6,
0 conflicts — Allan's call, the set below. Every one of the 20 is exported,
assembled and sliced; `export.py` wants 0 calls in all four games, and
`verify.py --pushers` reads 0 of 32 defective.)*

`VERSIONS` is one global table, so bumping it to 7.0 makes EVERY cascade in
every game stale at once. That is wrong: 7.0 is a whole-cascade change with a
real print cost, and most cascades should stay where they are until their owner
is ready. What was needed is a way to say *these* cascades are v7 and the rest
are v6 — per cascade, not by reading a rule off box depth.

**A GENERATION is one self-consistent set of per-type versions**
(`onshape_config.GENERATIONS`), and `CURRENT` names the default. `7.0` is the
lock catalogue; `6.6` is everything as it stood before it. `VERSIONS` is now just
`GENERATIONS[CURRENT]`, so every existing reader is unaffected.

**parts.csv's `Build` column names a row's generation**, blank meaning `CURRENT`.
It is per SLEEVING, because a row's two sleevings are separate cascades that move
independently — the broken-eleven wave is mostly the unsleeved halves:

```
(blank)          both sleevings at CURRENT
6.6              both at 6.6
Un:6.6           unsleeved held at 6.6, sleeved at CURRENT
Un:6.6 Sl:7.0    each named explicitly
```

An unknown name fails at planning time, not after calls have been spent.
`expected_version(type, files, gen)` is still the ONE place the rule lives, and
the generation is threaded through every provenance write — assembly, studio and
topper paths alike — so a component is recorded at the version the staleness
check will expect.

**Rebuilding a pinned cascade offline falls out of this rather than needing new
machinery.** Its components are current AT ITS generation, so the planner asks
for nothing, and `refresh_cascades` reports `components: all current` and goes
straight to a keep-layout assemble from `individual/`. Where a component IS
wanted, `export.py --use-cache` re-splits it from `_raw/` for 0 calls. Both paths
already existed; the generation is what stops the planner dragging the cascade
forward.

**The one real constraint: components dedup ACROSS cascades, and a file exists
once.** A pusher's key is `(risers, cards, sleeved)`, so one file serves up to
three cascades. If one builds at 7.0 and another is pinned to 6.6, the file
cannot be both, and whichever exported last would win silently. `export.py` now
reports those instead:

```
⚠ 1 component(s) wanted at more than one generation — one file cannot be both:
    Pusher 5x10-Sl.3mf
        6.6: 3 Later Ages 5 Expansions Sl, Single Mini Sl
        7.0: 4 Later Ages 5 Expansions Sl
```

Measured against reality — pin everything to 6.6 except the two Innovation
cascades actually built at 7.0 — that is the **only** conflict in the catalogue.
Box and Lid are keyed per model so they never conflict; only the shared types
can. The fix is to move the conflicting cascades together, or to leave the pinned
one unrefreshed on the project it already has.

**DECIDED — the 7.0 set is 14 cascades** (Allan). It is the broken eleven, plus
`Innovation 4 Later Ages 5 Expansions Sl` (hand-exported and already built), plus
the two the closure pulls in:

| pulled in | via | shared with |
|---|---|---|
| `Innovation 3 Later Ages 5 Expansions Sl` | `Pusher 5x10-Sl` | `4 Later Ages Sl` |
| `Innovation Single Mini Sl` | `Pusher 5x10-Sl` | `4 Later Ages Sl` |

Growing the set over shared components until no conflict remains is the general
move, and it converges in two rounds here. Note the closure must be taken over
components whose VERSION actually differs between the two generations, not over
shared components generally: an earlier cut compared generation names and dragged
in three Dominion cascades over a shared `TokenHolder` that reads `6.6` in both.
Only Box, Lid and Pusher move at 7.0, and Box and Lid are keyed per model, so in
practice the closure only ever follows a shared Pusher.

**Then five more, because a 6.6 export is no longer possible.** The first pass
left five cascades pinned at 6.6 that still needed a holder — `Compile 126 Sl`,
`Dominion 246 Sl`, `Dominion 324 Un/Sl`, `Innovation Single Set Sl` — because the
riser axis is orthogonal to the generation and those files never existed at any
version. Allan's point: those are exactly the ones to promote, and there are
three reasons rather than one.

- The parameter-set call is spent either way, and ONE assembly export carries
  Box + Holder + Pusher together, so the 7.0 box and pusher come down in the same
  download the holder does. Only the Lid studio export is extra, ~3 calls.
- **The CAD has moved.** Onshape holds one model, and it is at 7.0. Exporting a
  "6.6" holder today writes 7.0 geometry and records it as 6.6 — a provenance row
  that is simply false. Confirmed on the 4 Later Ages holder, which differs from
  its 6.6 predecessor only in a 0.2 mm version-stamp band.
- A cascade whose box, lid and pusher read 6.6 under a holder stamped 7.0 is the
  mixed-version state the whole `Build` column exists to prevent.

Promoting those five pulls in `Compile 210 Card Sl` (shared `Pusher 5x7-Sl`) and
nothing else. `Dominion 290 Card (Mat)` looks like it should be dragged in too,
and is not: the planner skips it for an incomplete parts.csv row, so it is never
built and cannot conflict. Take the closure over the cascades the PLANNER builds,
not over every row.

What the pinning bought, measured: the planner's whole-catalogue estimate falls
from **~316 calls to ~123** with 20 cascades at 7.0 (it was ~101 with 14, so the
six extra cost ~22), and **30 of the 48 buildable cascades need nothing at all** —
`refresh_cascades` reports `components: all current` for each and assembles from
`individual/` with no Onshape at all. Of the ~123, FCM's ~21 can be 0: its three
7.0 cascades were hand-exported and the assemblies and lids are still in `tmp/`,
so `--use-cache` re-splits them for nothing.

**Pinning does not remove the nine missing holders.** The riser axis is
orthogonal to the generation: `Holder 3x7-r5-Un` was never exported at ANY
version, because no 5-riser Compile cascade was ever the one that wrote the file.
Under a full 6.6 pinning the planner still asks for 7 components (Compile 2,
Dominion 4, Innovation 1); FCM asks for none, so its pinned cascades are already
fully rebuildable offline.

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

Each plate is sized to fit the smallest candidate bed, rotating parts to fit
where needed: **A1 mini (180×180 mm)**, else **P1 (256×256)**, else **H2C
(330×320)** — `make_cascade.BED_TABLE`, smallest first.
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
  the bed chosen from parts.csv's `3D printer` column (**Mini→A1 mini,
  Standard→P1, Large→H2C, Mixed→P1 unsleeved / H2C sleeved**). This is the
  general "auto-build" for
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

### The `Mini` bed class (A1 mini)

Innovation's XS boxes are the only cascades small enough for the 180 mm A1 mini,
so `parts.csv` gained a **`Mini`** value in the `3D printer` column and
`profiles/a1mini.config` the matching reference profile.

Adding a bed SMALLER than P1 changes what `--bed auto` picks, since it takes the
first entry in `BED_TABLE` that fits — so it was checked before landing rather
than assumed: against make_cascade's rule (an object's 45°-rotated span
`(w+d)/√2` must clear `min(bed) - BED_MARGIN` = 172 mm) the smallest box or lid
in every other game is 176.0 mm (Dominion `S4.16.10`), 178.7 (FCM `S4.18.12`)
and 181.4 (Compile `S4.7.7`). All are above the bar, so no existing cascade can
be re-routed onto the Mini bed; `XS5.15.10` reaches 142.1 and does fit. Only one
row uses `auto` at all (Dominion's blank `290 Card (Mat)`), and it is a Mat box,
larger still.

The profile was taken from the A1 mini cascade project itself rather than hand
written, with two corrections: `wipe_tower_x`/`wipe_tower_y` dropped (make_cascade
sets those per plate, and neither sibling profile carries them) and
`filament_nozzle_map`/`filament_volume_map` cut from Studio's 9 entries to the
2 that `p1p`/`h2c` carry. A profile REPLACES a project's whole settings on a bed
swap, so leaving the 9-entry drift in would have propagated it to every future
Mini rebuild instead of just the projects that already inherited it.

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
