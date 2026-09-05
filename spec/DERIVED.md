# The Onshape variable studio, transcribed

Allan supplied the full derived-variable list on 2026-09-01. It is transcribed
in `cad/derive.py`, in studio order, keeping Onshape's names, so that reviewing
one against the other is a line-by-line read. The per-game lookups are in
`cad/tables.py`. This file records what the transcription is checked against
and what it settled.

**`tests/test_derive.py` is the check** — every independently measured number on
record, against the formula that should produce it. It passes.

---

## What it confirms

| anchor | measured, on record | from the formulae |
|---|---|---|
| rise at 8 risers | `10.875` (`verify.audit_rises`) | `10.875` |
| `FCM Pusher 3x6-Un` depth | `14.04` (`LOCK_STANDARD.md`) | `14.04` |
| `Pusher 9x10-Sl` depth | `75.60` | `75.60` |
| pre-7.0 tab pitch on `M4.21.10.32-Un` | `12.77–12.82`, nominal `12.80` | `12.80` |
| ... as a rule | `D − 12.00` | `D − 2·(4+4) + 4` |
| card thickness | `Un 0.40 / Sl 0.65` (`topper_split.CARD_MM`) | same |
| topper depth at 15 / 10 cards | `8.00 / 6.00` | `2.00 + calSlotDepth` |
| lid depth, all 48 rows with a figure | parts.csv W/D | within `0.1 mm` |
| pusher catalogue | 32 pushers, `C1:1 C2:5 C3:10 C4:11 C5:5` | identical |

The lid-depth check is the broad one: `calLidDepth` reproduces every recorded
depth in `parts.csv`, the two apparent misses being parts.csv rounding `50.06`
to `50` and `71.06` to `71`.

## What it settles

**The rise formula.** `calHeightIncrement = min(calDesiredHeightIncrement,
(BoxHeight − 18 mm) / RisingSliders)`. `verify.audit_rises` says of its own
subject: *"RISE IS A FUNCTION OF RISER COUNT WITHIN A GAME. That is an
assumption about the CAD, not a fact about the world."* It is now a fact about
the CAD — and the assumption was sound, because both terms depend only on the
game and the riser count. The `10.923 / 10.827` alternation it measures is the
staircase failing to divide evenly, not a second rise.

**The side label width is an OUTPUT, not an input.**
`calSideLabelWidth` is a ladder on `calLidDepth` — `>77 → 62`, `>59 → 45`,
`>44 → 32`, else `20`. `PIPELINE.md` has it that the model code's trailing
number "is a LABEL width and drives no Onshape input", which is true but
backwards: nothing drives it *into* Onshape because Onshape computes it. The
FCM 180 correction (`L3.18.6.32-Sl` → `.20-Sl`) is confirmed by the formula —
though its stated reason is wrong. That lid is `42.90` deep, not the `44.9`
recorded, so it lands under the `44` threshold with room to spare.

**`calModelName` is the authority CLAUDE.md says it is**, and reproduces every
model code in parts.csv, with two divergences that are parts.csv's:

- **Mat rows lose their `-M`.** The CAD emits `M4.21.10.32-M.Un`; parts.csv
  records `M4.21.10.32-Un`, the same string as the non-Mat `244 Card`. So the
  `(model, merged)` Box key in `components.py` exists to recover a distinction
  the CAD had already made and the transcription dropped. **The Lid needed the
  same key and did not have it** — `calModelName` is engraved in its floor, so
  the 244 shipped with the 202's lid until `plan_exports.lid_model` was added;
  see spec/LID.md. Any component whose geometry or engraving reads `MatPocket`
  wants the axis in its key.
- **`290 Card (Mat)` carries `.0` where the label width goes**, a placeholder
  from before it was built. The formula fills in `45` (Un) and `62` (Sl).

## What it found

**The Pusher dedup key is missing an axis.** `plan_exports` keys a pusher
`(risers, cards, sleeved)`, but

```
calPusherTotalDepth = (RisingSliders-1)*calSliderDistance + calFirstSliderDistance
```

also depends on `FirstSlidingSlotCards`. Two Dominion rows collide:

| | risers | cards/slot | first riser | D (Un) | D (Sl) |
|---|---|---|---|---|---|
| `324 Card` | 6 | 10 | — | `37.20` | `50.40` |
| `290 Card (Mat)` | 6 | 10 | 12 | `37.96` | `51.60` |

Both are named `Pusher 6x10-Un` / `-Sl`, so one file must serve both, and the
sleeved pair differ by `1.20 mm`.

**Latent, not live.** `290 Card` has no built project, and the two files in
`individual/Dominion/` are `324 Card`'s. But it is `Status: Published,
Build: 6.6` in parts.csv, so the next thing to build it gets a pusher `1.20 mm`
short in the sleeved case — silently, because the planner sees the file present
and asks for nothing. `verify.py --pushers` would not catch it either: both
depths fall in `C4`, so the tabs are where the catalogue wants them.

The Holder key already carries a `first` axis for exactly this reason. The
Pusher key needs the same, and the two files need distinguishing names.

**Decided, and done on the `cad/` side.** `cad/build.py` keys a pusher
`(game, risers, cards, first, sleeved)` — 34 entries against the planner's 32 —
and names the override one `Pusher 6x10-12-Sl.3mf`, following parts.csv's own
model-code convention (`M6.21.10/12`, `/` folded to `-` as
`components.cascade_filename` already does). `--legacy-names` writes the old
names and refuses when two geometries would land on one, so the collision is
now loud rather than latent. `plan_exports.compose` and the four affected files
in `individual/` still need the same change before anything can be promoted.

**And the reading above is confirmed.** Read the generation off each canonical
pusher's lock and it matches parts.csv's `Build` pinning on all 30 rows the
name can identify; the two it cannot are `Pusher 6x10-Un/Sl`, which read `7.0`
— `324 Card`'s pinning, not `290 Card (Mat)`'s `6.6`. See `spec/PUSHER.md`.

## Loose ends in the studio itself

Transcribed as written; none blocks the rebuild.

- **`calFrontDividerLeftSpacing` tests `GameName == "None"`**, which no game is,
  so it is always `calSliderSpaceLeftRight`. Its description ("Dominion needs
  the right pocket to be big; all other games want the front pockets to align")
  describes a branch that cannot be taken.
- **One game the rest of the toolchain does not know**: `Colours`, the only
  user of the `115 mm` box and `55 mm` lid. `components.py` has no entry for it.
  It is kept, because the studio has it and a one-off may yet want it (Allan).
- **`CraftGutermann` is REMOVED, and that is the one place `cad/` knowingly
  differs from the studio.** The design is deprecated (Allan). Onshape still
  carries it — as the only user of the `58 mm` card height, of
  `ProductName = "Craft Cascade"`, and the only game with no
  `game10SleevedCardThickness` row, so a sleeved one failed the lookup there
  too. `cad/tables.py` says so at the top; do not restore it when diffing the
  transcription against Onshape.
- ~~**`isOnlyTwoPusherSlots` is Innovation-wide**, but `components.py` gives
  Innovation `{"S": 2, "M": 2, "L": 3}`.~~ **Fixed.** The per-size map was the
  wrong shape and had a second, reachable hole: no `XS` key, so `Single Mini`
  fell through to the default `3` against a box with 2 slots. `components.py`
  now gives Innovation a flat `2`, matching the variable, and
  `verify.py --boxes` counts each box's rim cutouts to keep the table and the
  CAD from drifting again. See `spec/BOX.md`.
- **Dead or vestigial**: `LeanAngle = 0` (so `calAngleDelta` is always `0`),
  `calPocketHeight` is a plain alias of `calMaxPocketHeight`, and
  `PocketHeight` / `FrontPocketHeight` (`75`) appear unused next to
  `calPocketHeight`.
- **`calNumTabs` / `calTabDistance` / `calTabToTapDistance` /
  `calPusherMarginToRight` are the pre-7.0 lock**, superseded by
  `calTabCentreDistance`. Kept because they are still in the studio and this is
  a transcription of it — but **nothing in `cad/` reads them**: the rebuild
  builds 7.0 only (`cad/README.md`, decision 4). They do agree with the 14
  still-6.6 pushers on disk: `calTabDistance` is their measured tab-centre
  separation, `D - 12.00`, to the millimetre.

## Variables the parts added

- **`LabelHolders`** (2026-09-05) is an INPUT, not a variable — the eleventh
  field of `params.Primary`, from the parts.csv `Label holders` column, and
  the one input Onshape has nothing for. `derive.py` folds it into
  `isLabelHoldersOnBox`: the studio's `0 if Colours or HorizontalSlots <= 1`
  stands, and where that would give `1` the column decides. Blank is `1`, so
  every shipped row derives exactly what the studio does; `spec/BOX.md`.

The transcription was made from the variable studio; two more surfaced later,
in the Lid's own sketches (Allan, 2026-09-02), and are now in `derive.py`
beside their neighbours:

- **`#FootDistanceFromWall = 2*#WallThickness + #PusherThickness + 1.2mm`** —
  `7.400`. Where the Lid's pusher sockets sit in from its inner wall, and the
  datum both engraved blocks hang off. `lid.SOCKET_BACK` is it plus
  `WallThickness`. The expression reads as the box's two walls and the plate
  between them, plus clearance.
- **`#calLidTextOffset = #calSliderSpaceLeftRight`** — an alias, like
  `calPocketHeight`, and the base of both engraved blocks' horizontal offset.

`spec/LID.md` records what each was checked against.

## The one sketch variable in the studio's transcription

`#BoxWidth` is a SKETCH variable, not a studio one, and it is the single
exception in `derive.py`. It is there because **`#calTokenHolderSlotWidth`** IS
a studio variable and is written in terms of it:

    #BoxWidth - #calFrontSlotsExceptTokenHolderSlot * #calSlotwidth
              - 2*#WallThickness - #calFrontDividerLeftSpacing
              - #FrontPocketSidePaddingWidth

The alternative was a second copy of the box-width expression, which is the one
thing this module exists to prevent. `cad/parts/box.box_width` reads it back,
so Box, Lid and TokenHolder still share exactly one transcription of it.

`HorizontalSlots` cancels out of the result: it reduces to
`calSlotwidth - 0.600` on a plain box and `2*calSlotwidth - 0.600` on a Mat
one, because `MatPocket` drops one more from the slot count. That is what
"merged" means to a token holder — the mat merges two front slots and the tray
gets both. `spec/TOKENHOLDER.md` has the four widths it produces.

## Still needed

The derived layer is complete. What the geometry still needs is **shape**, not
numbers — which feature is cut from which face, in what order. Three parts are
settled: the Pusher from `LOCK_STANDARD.md` plus two hand-exported STEPs, the
Box from its feature tree plus six, the Lid from four plus its sketches, and
the TokenHolder from two plus all 18 of its cached components (0 API calls
throughout). Holder and Topper still want the same treatment — and, for the
Topper, a STEP exported by hand before its shape can be written down.

## Two additions of 2026-09-04: `#calPusherSlots`, and the shared formulas

`#calPusherSlots` — 2 for every Innovation box and for an S box, else 3 —
joins `#BoxWidth` as a sketch variable transcribed here, because three modules
read it (the Box, the assembly's pusher placement, the tests) and
`parts/box.pusher_slot_count` had been re-deriving it with its own `GameName
== "Innovation"`, a second copy of the rule `isOnlyTwoPusherSlots` states.
Checked against the old expression on all 50 rows.

Two part-studio formulas that TWO parts share are written here once, as
functions rather than variables (they take an argument the studio does not
have): `cascade_slope(d, slider_distance)`, the Holder's `Top slant angle` and,
inverted at `calFirstSliderDistance`, the Box's lip angle — transcribed as
reciprocals of each other in the two parts until now; and
`back_slot_pitch(d)`, `#dBackSlotWidth = calPusherTotalDepth + 4.0`, which the
Box had inline three times and the assembly once. A part-studio formula one
part uses (the Lid's text offsets, the Topper's `#LogoEdgeDist`) stays in that
part.
