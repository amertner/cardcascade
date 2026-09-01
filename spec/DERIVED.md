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
  the CAD had already made and the transcription dropped.
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

## Loose ends in the studio itself

Transcribed as written; none blocks the rebuild.

- **`calFrontDividerLeftSpacing` tests `GameName == "None"`**, which no game is,
  so it is always `calSliderSpaceLeftRight`. Its description ("Dominion needs
  the right pocket to be big; all other games want the front pockets to align")
  describes a branch that cannot be taken.
- **Two games the rest of the toolchain does not know**: `Colours` (the only
  user of the `115 mm` box and `55 mm` lid) and `CraftGutermann` (the only user
  of the `58 mm` card height and of `ProductName = "Craft Cascade"`).
  `components.py` has neither.
- **`game10SleevedCardThickness` has no `CraftGutermann` row**, so a sleeved
  CraftGutermann cascade fails the lookup. `derive.py` fails there too, rather
  than defaulting.
- **`isOnlyTwoPusherSlots` is Innovation-wide**, but `components.py` gives
  Innovation `{"S": 2, "M": 2, "L": 3}`. No Innovation row is `L`, so the
  entry is unreachable and nothing is wrong today; if one is ever added the two
  disagree.
- **Dead or vestigial**: `LeanAngle = 0` (so `calAngleDelta` is always `0`),
  `calPocketHeight` is a plain alias of `calMaxPocketHeight`, and
  `PocketHeight` / `FrontPocketHeight` (`75`) appear unused next to
  `calPocketHeight`.
- **`calNumTabs` / `calTabDistance` / `calTabToTapDistance` /
  `calPusherMarginToRight` are the pre-7.0 lock**, superseded by
  `calTabCentreDistance`. Kept because they are what a 6.6 cascade builds, and
  generations are a parameter (`cad/README.md`).

## Still needed

The derived layer is complete. What the geometry still needs is **shape**, not
numbers — which feature is cut from which face, in what order. For the Pusher
that is nearly covered by `LOCK_STANDARD.md`; a hand-exported STEP (0 API calls,
as in the last three commits on `main`) would settle the rest.
